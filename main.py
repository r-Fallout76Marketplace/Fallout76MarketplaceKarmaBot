import sqlite3
import time
import traceback
from contextlib import closing
from functools import wraps
from threading import Thread, Lock

import praw
import prawcore
import requests
import schedule
import yaml

import common_functions
import database_manager


def post_to_pastebin(title, body):
    """
    Uploads the text to PasteBin and returns the url of the Paste
    :param title: Title of the Paste
    :param body: Body of Paste
    :return: url of Paste
    """
    login_data = {
        'api_dev_key': bot_config['pastebin_credentials']['api_key'],
        'api_user_name': bot_config['pastebin_credentials']['username'],
        'api_user_password': bot_config['pastebin_credentials']['password']
    }

    data = {
        'api_option': 'paste',
        'api_dev_key': bot_config['pastebin_credentials']['api_key'],
        'api_paste_code': body,
        'api_paste_name': title,
        'api_paste_expire_date': '1W',
        'api_user_key': None,
        'api_paste_format': 'python'
    }

    login = requests.post("https://pastebin.com/api/api_login.php", data=login_data)
    login.raise_for_status()
    data['api_user_key'] = login.text

    r = requests.post("https://pastebin.com/api/api_post.php", data=data)
    r.raise_for_status()
    return r.text


def catch_exceptions():
    def catch_exceptions_decorator(job_func):
        @wraps(job_func)
        def wrapper(*args, **kwargs):
            global failed_attempt
            try:
                job_func(*args, **kwargs)
                failed_attempt = 1
            except Exception as exp:
                tb = traceback.format_exc()
                try:
                    url = post_to_pastebin(f"{type(exp).__name__}: {exp}", tb)
                    common_functions.send_message_to_discord(bot_config['discord_webhooks']['err_channel'],
                                                             f"[{type(exp).__name__}: {exp}]({url})")
                except Exception as discord_exception:
                    print(tb)
                    print("\nError sending message to discord", str(discord_exception))
                # In case of server error pause for multiple of 5 minutes
                if isinstance(exp, prawcore.exceptions.ServerError):
                    print(f"Waiting {(300 * failed_attempt) / 60} minutes...")
                    time.sleep(300 * failed_attempt)
                    failed_attempt += 1

        return wrapper

    return catch_exceptions_decorator


@catch_exceptions()
def comment_listner(args):
    fallout76marketplace = args[0]
    legacy76 = args[1]
    db_conn = args[2]
    mod_channel_webhook = bot_config['discord_webhooks']['mod_channel']

    # Gets 100 historical comments
    comment_stream = fallout76marketplace.stream.comments(pause_after=-1, skip_existing=True)
    # Gets a continuous stream of comments
    for comment in comment_stream:
        if comment is None:
            break
        mutex = Lock()
        with mutex:
            database_manager.load_comment(comment, fallout76marketplace, legacy76, db_conn, mod_channel_webhook)


def listener_thread(*args):
    """
    Thread for comment_listner
    :param args:
    """
    while run_threads:
        comment_listner(args)


@catch_exceptions()
def delete_old_records():
    """
    Deletes the karma logs older than 6 months and posts karma transfer statistics of everyday
    """
    # Calculate what was unix time 6 months ago
    seconds_in_six_months = 180 * 60 * 60 * 24
    unix_time_now = time.time()
    unix_time_six_months_ago = unix_time_now - seconds_in_six_months
    mutex = Lock()
    with mutex:
        with closing(sqlite3.connect('karma_logs.db', check_same_thread=False)) as db_conn:
            with closing(db_conn.cursor()) as cursor:
                # delete the record of comments that are of older than 6 months
                # since by that time the submission is archived
                cursor.execute(
                    "DELETE FROM comments WHERE submission_created_utc <= '{}'".format(unix_time_six_months_ago))
            db_conn.commit()
    print("Old data deleted " + time.strftime('%I:%M %p %Z'))


def database_thread():
    """
    The secondary thread that runs to manage the database/memory and delete old items
    """
    # Run schedule every week at midnight
    schedule.every(1).weeks.do(delete_old_records)
    while run_threads:
        schedule.run_pending()
        time.sleep(1)


def main():
    global run_threads
    global bot_config

    with open('config.yaml') as stream:
        bot_config = yaml.safe_load(stream)

    # Logging into Reddit
    reddit = praw.Reddit(client_id=bot_config['reddit_credentials']['client_id'],
                         client_secret=bot_config['reddit_credentials']['client_secret'],
                         username=bot_config['reddit_credentials']['username'],
                         password=bot_config['reddit_credentials']['password'],
                         user_agent=bot_config['reddit_credentials']['user_agent'])
    fallout76marketplace = reddit.subreddit("Fallout76Marketplace")
    legacy76 = reddit.subreddit("legacy76")

    db_conn = sqlite3.connect('karma_logs.db', check_same_thread=False)
    # create table in karma logs db if it doesn't exist
    with closing(db_conn.cursor()) as cursor:
        cursor.execute("""CREATE TABLE IF NOT EXISTS comments (
                                                    comment_ID text,
                                                    submission_ID text,
                                                    submission_created_utc real,
                                                    from_author_name text,
                                                    to_author_name text,
                                                    time_created_utc real,
                                                    permalink text
                                                    )""")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS comment_ID_index ON comments (comment_ID)")
    db_conn.commit()

    # Create threads
    comment_listner_thread = Thread(target=listener_thread, args=(fallout76marketplace, legacy76, db_conn))
    database_manager_thread = Thread(target=database_thread)
    try:
        # run the threads
        comment_listner_thread.start()
        database_manager_thread.start()
        print("Bot is now live!", time.strftime('%I:%M %p %Z'))
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Backing up the data...")
        schedule.run_all()
        run_threads = False
        comment_listner_thread.join()
        database_manager_thread.join()
        db_conn.close()
        print("Bot has stopped!", time.strftime('%I:%M %p %Z'))
        quit()


# Entry point
if __name__ == '__main__':
    run_threads = True
    failed_attempt = 1
    bot_config = {}
    main()

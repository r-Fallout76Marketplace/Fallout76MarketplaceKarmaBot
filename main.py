import json
import sqlite3
import time
import traceback
from threading import Thread, Lock

import prawcore
import requests
import schedule

import CONFIG
import bot_database
import user_database

run_threads = True


# Send message to discord channel
def send_message_to_discord(message_param):
    data = {"content": message_param, "username": CONFIG.bot_name}
    output = requests.post(CONFIG.discord_webhooks, data=json.dumps(data), headers={"Content-Type": "application/json"})
    output.raise_for_status()


# main thread where the bot will run
def main():
    mutex = Lock()
    failed_attempt = 1
    # Gets 100 historical comments
    comment_stream = CONFIG.fallout76marketplace.stream.comments(skip_existing=True)
    while run_threads:
        try:
            # Gets a continuous stream of comments
            for comment in comment_stream:
                mutex.acquire()
                comment_database_obj.load_comment(comment, user_database_obj)
                mutex.release()

            # Resetting failed attempt counter in case the code doesn't throw exception
            failed_attempt = 1
        except Exception as exception:
            if mutex.locked():
                mutex.release()
            # Sends a message to mods in case of error
            tb = traceback.format_exc()
            try:
                send_message_to_discord(tb)
                print(tb)
                # Refreshing Streams
            except Exception as exception:
                print("Error sending message to discord", exception)

            # In case of server error pause for two minutes
            if isinstance(exception, prawcore.exceptions.ServerError):
                print("Waiting 2 minutes")
                # Try again after a pause
                time.sleep(120 * failed_attempt)
                failed_attempt = failed_attempt + 1

            # Refresh streams
            comment_stream = CONFIG.fallout76marketplace.stream.comments(skip_existing=True)


def manage_data():
    mutex = Lock()
    try:
        # Calculate what was unix time 6 months ago
        seconds_in_six_months = 180 * 60 * 60 * 24
        unix_time_now = time.time()
        unix_time_six_months_ago = unix_time_now - seconds_in_six_months
        karma_logs_db_conn = sqlite3.connect('karma_logs.db', check_same_thread=False)
        karma_logs_db_cursor = karma_logs_db_conn.cursor()

        mutex.acquire()
        # delete the record of comments that are of older than 6 months
        karma_logs_db_cursor.execute(
            "DELETE FROM comments WHERE submission_created_utc <= '{}'".format(unix_time_six_months_ago))
        # commit
        karma_logs_db_conn.commit()
        mutex.release()

        user_database_obj.archive_data()
        user_database_obj.erase_data()
        print("Old data deleted " + time.strftime('%I:%M %p %Z'))
    except Exception as exception:
        if mutex.locked():
            mutex.release()
        tb = traceback.format_exc()
        print(exception)
        try:
            send_message_to_discord(tb)
        except requests.exceptions.HTTPError:
            print("Error sending message to discord")


# The secondary thread that runs to manage the database/memory and delete old items
def database_manager():
    # Run schedule Everyday at 12 midnight
    schedule.every().day.at("00:00").do(manage_data)
    while run_threads:
        schedule.run_pending()
        time.sleep(1)


# Entry point
if __name__ == '__main__':
    main_thread = None
    database_manager_thread = None
    try:
        comment_database_obj = bot_database.BotDatabase()
        user_database_obj = user_database.UserDatabase()
        # logs karma logs of one day
        comment_database_obj.load_data_from_karma_logs(user_database_obj)
        # Create threads
        main_thread = Thread(target=main)
        database_manager_thread = Thread(target=database_manager)
        # run the threads
        main_thread.start()
        database_manager_thread.start()
        print("Bot is now live!", time.strftime('%I:%M %p %Z'))
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Backing up the data...")
        schedule.run_all()
        run_threads = False
        main_thread.join()
        database_manager_thread.join()
        print("Bot has stopped!", time.strftime('%I:%M %p %Z'))
        quit()

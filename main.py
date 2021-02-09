import json
import os
import sqlite3
import sys
import time
import traceback
from threading import Thread, Lock

import prawcore
import requests
import schedule

import CONFIG
import bot_database
import bot_responses
import flair_functions
import user_database


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
    comment_stream = CONFIG.fallout76marketplace_1.stream.comments(pause_after=-1, skip_existing=True)
    # Gets 100 historical submission
    submission_stream = CONFIG.fallout76marketplace_1.stream.submissions(pause_after=-1, skip_existing=True)
    while True:
        try:
            # Gets comments and if it receives None, it switches to posts
            for comment in comment_stream:
                if comment is None:
                    break
                mutex.acquire()
                submission_database_obj.load_comment(comment, user_database_obj)
                mutex.release()

            # Gets posts and if it receives None, it switches to comments
            for submission in submission_stream:
                if submission is None:
                    break
                mutex.acquire()
                submission_database_obj.load_submission(submission)
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
            except Exception:
                print("Error sending message to discord")

            # In case of server error pause for two minutes
            if isinstance(exception, prawcore.exceptions.ServerError):
                print("Waiting 2 minutes")
                # Try again after a pause
                time.sleep(120 * failed_attempt)
                failed_attempt = failed_attempt + 1

            # Refresh streams
            comment_stream = CONFIG.fallout76marketplace_1.stream.comments(pause_after=-1, skip_existing=True)
            submission_stream = CONFIG.fallout76marketplace_1.stream.submissions(pause_after=-1, skip_existing=True)


def manage_data(start_time_p):
    mutex = Lock()
    try:
        seconds_in_week = 604800
        time_now = time.time()
        unix_time_week_ago = time_now - seconds_in_week
        submission_db_conn = sqlite3.connect('submission_logs.db', check_same_thread=False)
        submission_logs_db_cursor = submission_db_conn.cursor()
        karma_logs_db_conn = sqlite3.connect('karma_logs.db', check_same_thread=False)
        karma_logs_db_cursor = karma_logs_db_conn.cursor()

        # Locking all submission the submission_logs_db_cursor
        submission_logs_db_cursor.execute(
            "SELECT * FROM submissions WHERE time_created_utc <= '{}'".format(unix_time_week_ago))
        table = submission_logs_db_cursor.fetchall()
        for row in table:
            submission = CONFIG.reddit_2.submission(row[0])
            flair_functions.close_post_trade(submission)
            bot_responses.close_submission_comment(submission, time_expired=True)

        mutex.acquire()
        submission_logs_db_cursor.execute(
            "DELETE FROM submissions WHERE time_created_utc <= '{}'".format(unix_time_week_ago))
        # commit
        submission_db_conn.commit()

        # delete the record of comments that are of deleted submissions
        karma_logs_db_cursor.execute(
            "DELETE FROM comments WHERE submission_created_utc <= '{}'".format(unix_time_week_ago))
        # commit
        karma_logs_db_conn.commit()
        mutex.release()

        time_now = time.localtime().tm_hour
        if time_now == start_time_p:
            user_database_obj.archive_data()
            user_database_obj.erase_data()
        print("Old data deleted " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    except Exception:
        if mutex.locked():
            mutex.release()
        tb = traceback.format_exc()
        print(tb)
        try:
            send_message_to_discord(tb)
        except Exception:
            print("Error sending message to discord")


# The secondary thread that runs to manage the database/memory and delete old items
def database_manager():
    # Schedule the backing up process to run after every 6 hours
    start_time = time.localtime().tm_hour
    schedule.every(6).hours.do(manage_data, start_time)
    while True:
        schedule.run_pending()
        time.sleep(1)


# Entry point
if __name__ == '__main__':
    try:
        submission_database_obj = bot_database.BotDatabase()
        user_database_obj = user_database.UserDatabase()
        # Check if the command line argument is provided
        # If the bot was down, loads all the submissions that were posted during downtime
        if len(sys.argv) >= 2:
            downtime_in_seconds = int(sys.argv[1]) * 3600
            submission_database_obj.load_submissions_from_downtime(downtime_in_seconds)
        submission_database_obj.load_data_from_karma_logs(user_database_obj)
        # Create threads
        main_thread = Thread(target=main)
        database_manager_thread = Thread(target=database_manager)
        # run the threads
        main_thread.start()
        database_manager_thread.start()
        print("Bot is now live!" + time.strftime('%I:%M %p'))
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Backing up the data...")
        schedule.run_all()
        print("Bot has stopped!" + time.strftime('%I:%M %p'))
        try:
            sys.exit(0)
        except SystemExit:
            os._exit()

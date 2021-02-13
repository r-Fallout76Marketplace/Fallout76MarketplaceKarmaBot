import re
import sqlite3
import time
from datetime import datetime

import praw

import CONFIG
import CONSTANTS
import bot_responses
import conversation_checks
import flair_functions


# Checks if submission is eligible for trading
# Checks that need to be passed are
# Submission must have right flair and trade should not be closed
def flair_checks(comment_or_submission):
    regex = re.compile('XBOX|PlayStation|PC', re.IGNORECASE)
    # Check if the object is of submission type otherwise get the submission from comment object
    if isinstance(comment_or_submission, praw.models.reddit.submission.Submission):
        submission = comment_or_submission
    else:
        submission = comment_or_submission.submission
    submission_flair_text = submission.link_flair_text
    match = re.match(regex, str(submission_flair_text))
    # If No match found match is None
    if match is None:
        return False
    else:
        return True


# Checks if the author is mod
def is_mod(author):
    moderators_list = CONFIG.fallout76marketplace.moderator()
    if author in moderators_list:
        return True
    else:
        return False


class BotDatabase:

    # Constructor
    def __init__(self):
        # create table in karma logs db if it doesn't exist
        self.karma_logs_db_conn = sqlite3.connect('karma_logs.db', check_same_thread=False)
        self.karma_logs_db_cursor = self.karma_logs_db_conn.cursor()
        self.karma_logs_db_cursor.execute("""CREATE TABLE IF NOT EXISTS comments (
                                            comment_ID text,
                                            submission_ID text,
                                            submission_created_utc real,
                                            from_author_name text,
                                            to_author_name text,
                                            time_created_utc real,
                                            permalink text
                                            )""")
        self.karma_logs_db_cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS comment_ID_index ON comments ("
                                          "comment_ID)")
        self.karma_logs_db_conn.commit()

    # loads the data from karma logs
    def load_data_from_karma_logs(self, user_database_obj):
        # Get how much time has past from midnight
        time_now = time.time()
        seconds_from_previous_midnight = time.localtime().tm_hour * 3600 + time.localtime().tm_min * 60 + time.localtime().tm_sec
        unix_time_at_previous_midnight = time_now - seconds_from_previous_midnight
        self.karma_logs_db_cursor.execute(
            "SELECT * FROM comments WHERE time_created_utc >= '{}'".format(unix_time_at_previous_midnight))
        table = self.karma_logs_db_cursor.fetchall()
        print("Loading " + str(len(table)) + " comments....")
        for row in table:
            comment = CONFIG.reddit_2.comment(id=row[0])
            user_database_obj.log_karma_command(comment)
        print("Loaded today's karma logs")

    def karma_plus_command_non_mod_users(self, comment, user_database_obj):
        # Checks if we have the submission in database otherwise assumes that the flair was changed
        submission = comment.submission
        if not flair_checks(comment):
            bot_responses.karma_trading_posts_only(comment)
            return CONSTANTS.INCORRECT_SUBMISSION_TYPE

            # Checks in karma logs to see if user has already rewarded the user
        self.karma_logs_db_cursor.execute("""SELECT * FROM comments WHERE 
                                                submission_id='{}'
                                                AND from_author_name='{}'
                                                AND to_author_name='{}'""".format(submission.id,
                                                                                  comment.author.name,
                                                                                  comment.parent().author.name))
        result = self.karma_logs_db_cursor.fetchone()
        if result is not None:
            bot_responses.already_rewarded_comment(comment, result[6])
            return CONSTANTS.ALREADY_REWARDED

        # If users has used all the karma he can give in a day
        if user_database_obj.awarder_karma_limit_reached(comment.author.name):
            # Get how much time has past from midnight
            time_now = time.time()
            seconds_from_previous_midnight = time.localtime().tm_hour * 3600 + time.localtime().tm_min * 60 + time.localtime().tm_sec
            unix_time_at_previous_midnight = time_now - seconds_from_previous_midnight

            self.karma_logs_db_cursor.execute(
                """SELECT * FROM comments WHERE from_author_name='{}' AND time_created_utc >= '{}'""".format(
                    comment.author.name, unix_time_at_previous_midnight))
            result = self.karma_logs_db_cursor.fetchall()
            bot_responses.karma_reward_limit_reached(comment, result)
            return CONSTANTS.KARMA_AWARDING_LIMIT_REACHED

        # checks rest of the conversation rules
        return conversation_checks.checks_for_karma_command(comment)

    # Process the commands for non mod users
    def process_command_non_mod_user(self, comment, user_database_obj):
        comment_body = comment.body.strip()
        if re.search(CONSTANTS.KARMA_PP, comment_body, re.IGNORECASE):
            output = self.karma_plus_command_non_mod_users(comment, user_database_obj)
            if output is CONSTANTS.KARMA_CHECKS_PASSED:
                # increment the karma in flair
                flair_functions.increment_karma(comment)
                # log comment in list
                user_database_obj.log_karma_command(comment)
                # store comment in karma logs database
                try:
                    self.karma_logs_db_cursor.execute("""INSERT INTO comments VALUES ('{}', '{}', '{}', '{}', 
                                                        '{}', '{}', '{}')""".format(comment.id, comment.submission.id,
                                                                                    comment.submission.created_utc,
                                                                                    comment.author.name,
                                                                                    comment.parent().author.name,
                                                                                    comment.created_utc,
                                                                                    comment.permalink))
                    self.karma_logs_db_conn.commit()
                except sqlite3.IntegrityError:
                    raise sqlite3.IntegrityError("Duplicate comment was received!")
                # reply to user
                bot_responses.karma_rewarded_comment(comment)
        # If comment says Karma--
        elif re.search(CONSTANTS.KARMA_MM, comment_body, re.IGNORECASE):
            bot_responses.karma_subtract_failed(comment)
        # Close submission
        elif re.search(CONSTANTS.CLOSE, comment_body, re.IGNORECASE):
            conversation_checks.checks_for_close_command(comment)

    # Posts the karma logs of a user on legacy76 subreddit
    def get_karma_logs(self, comment, comment_body):
        comment_body_split = comment_body.replace("\\", "").split()
        author_name = comment_body_split[1]
        days = 1
        if comment_body_split[-1].isdigit():
            days = min(int(comment_body_split[-1]), 180)
        unix_time_days_ago = time.time() - (days * 24 * 60 * 60)
        self.karma_logs_db_cursor.execute(
            """SELECT * FROM comments WHERE from_author_name='{}' COLLATE NOCASE AND time_created_utc >= '{}' ORDER BY 
            time_created_utc DESC""".format(author_name, unix_time_days_ago))
        karma_given = self.karma_logs_db_cursor.fetchall()
        self.karma_logs_db_cursor.execute(
            """SELECT * FROM comments WHERE to_author_name='{}' COLLATE NOCASE AND time_created_utc >= '{}' ORDER BY 
            time_created_utc DESC""".format(author_name, unix_time_days_ago))
        karma_received = self.karma_logs_db_cursor.fetchall()
        table = "# Awarder Karma\n\n"
        table += "|Comment Creation Date|From Author Name|To Author Name|Submission Creation Date|permalink|\n"
        table += "|:-|:-|:-|:-|:-|\n"
        for item in karma_given:
            row = list(item)
            row[2] = time.strftime("%D", time.localtime(int(row[2])))
            row[5] = time.strftime("%D", time.localtime(int(row[5])))
            table += "|{}|{}|{}|{}|https://www.reddit.com{}|\n".format(row[5], row[3], row[4], row[2], row[6])

        table += "\n# Awardee Karma\n\n"
        table += "|Comment Creation Date|From Author Name|To Author Name|Submission Creation Date|permalink|\n"
        table += "|:-|:-|:-|:-|:-|\n"
        for item in karma_received:
            row = list(item)
            row[2] = time.strftime("%D", time.localtime(int(row[2])))
            row[5] = time.strftime("%D", time.localtime(int(row[5])))
            table += "|{}|{}|{}|{}|https://www.reddit.com{}|\n".format(row[5], row[3], row[4], row[2], row[6])
        title = author_name + datetime.today().strftime(' %Y/%m/%d') + " karma logs"
        self_text = table
        submission = CONFIG.legacy76.submit(title=title, selftext=self_text, flair_id=CONSTANTS.KARMA_LOGS_PULL_REQUEST)
        comment.author.message(title, "https://www.reddit.com{}".format(submission.permalink))

    # Loads the comment to execute commands
    def load_comment(self, comment, user_database_obj):
        if comment.author.name == "AutoModerator":
            return None
        # If comment author is not mod
        if not is_mod(comment.author):
            self.process_command_non_mod_user(comment, user_database_obj)
        else:
            comment_body = comment.body.strip()
            # Mods commands will be executed without checks
            # Increase Karma
            if re.search(CONSTANTS.KARMA_PP, comment_body, re.IGNORECASE):
                flair_functions.increment_karma(comment)
                user_database_obj.log_karma_command(comment)
                bot_responses.karma_rewarded_comment(comment)
            # Decrease Karma
            elif re.search(CONSTANTS.KARMA_MM, comment_body, re.IGNORECASE):
                flair_functions.decrement_karma(comment)
                bot_responses.karma_subtract_comment(comment)
            # Close Submission
            elif re.search(CONSTANTS.CLOSE, comment_body, re.IGNORECASE):
                flair_functions.close_post_trade(comment)
                bot_responses.close_submission_comment(comment.submission)
            elif re.search(CONSTANTS.GET_KARMA_LOGS, comment_body, re.IGNORECASE):
                self.get_karma_logs(comment, comment_body)

import logging
import re
import sqlite3
import time
from contextlib import closing

import requests

import CONSTANTS
import bot_responses
import common_functions
import conversation_checks
import flair_functions

db_manager_logger = logging.getLogger('main')


def is_mod(author, fallout76marketplace) -> bool:
    """
    Checks if the author is moderator or not
    :param fallout76marketplace: The subreddit instance in which the moderators list is checked
    :param author: The reddit instance which will be checked in the list of mods
    :return: True if author is moderator otherwise False
    """
    moderators_list = fallout76marketplace.moderator()
    if author in moderators_list:
        return True
    else:
        return False


def karma_plus_command_non_mod_users(comment, fallout76marketplace, legacy76, db_conn, mod_channel_webhook) -> int:
    """
    Performs checks necessary to give karma to another user
    :param mod_channel_webhook: Discord mod channel webhook
    :param comment: The comment object that needs to be checked
    :param db_conn: The db connection to SQL database
    :param fallout76marketplace: The subreddit instance in which the commands are being checked
    :param legacy76: The subreddit instance in which the stats are published if karma limit is reached
    :return: returns the int value based on checks

    **PASS CODES**
    KARMA_CHECKS_PASSED = 0 (If all the checks passed)

    **FAIL CODES**
    CANNOT_REWARD_YOURSELF = 1 (If the user tried to reward themselves)
    MORE_THAN_TWO_USERS = 2 (If there are more than 2 users involved in the conversation)
    CONVERSATION_NOT_LONG_ENOUGH = 3 (If the conversation is not long enough)
    INCORRECT_SUBMISSION_TYPE = 4 (If the flair of submission is incorrect)
    ALREADY_REWARDED = 5 (If the user already rewarded that particular user in the submission)
    KARMA_AWARDING_LIMIT_REACHED = 6 (If user have reached the limit they can give karma)
    DELETED_OR_REMOVED = 7 (If the user tried to give karma to removed commented/submission)
    """
    # Checks if we have the submission in database otherwise assumes that the flair was changed
    submission = comment.submission
    if not common_functions.flair_checks(comment):
        db_manager_logger.info("Flair checks flair for the karma command.")
        bot_responses.karma_trading_posts_only(comment)
        return CONSTANTS.INCORRECT_SUBMISSION_TYPE

    with closing(db_conn.cursor()) as cursor:
        # Checks in karma logs to see if user has already rewarded the user
        cursor.execute(f"""SELECT * FROM comments WHERE submission_id='{submission.id}' AND from_author_name='{comment.author.name}' 
                                                                                        AND to_author_name='{comment.parent().author.name}'""")
        result = cursor.fetchone()

    if result is not None:
        db_manager_logger.info(f"{comment.author.name} has already reward to {comment.parent().author.name} at comment {result[0]}")
        bot_responses.already_rewarded_comment(comment, result[6])
        return CONSTANTS.ALREADY_REWARDED

    with closing(db_conn.cursor()) as cursor:
        # Get how much time has past from midnight
        time_now = time.time()
        seconds_from_previous_midnight = time.localtime().tm_hour * 3600 + time.localtime().tm_min * 60 + time.localtime().tm_sec
        unix_time_at_previous_midnight = time_now - seconds_from_previous_midnight

        cursor.execute(f"""SELECT * FROM comments WHERE from_author_name='{comment.author.name}' AND time_created_utc >= '{unix_time_at_previous_midnight}'""")
        result = cursor.fetchall()

        if len(result) >= 10:
            db_manager_logger.info(f"u/{comment.author.name} have reached their awarder karma limit.")
            link = bot_responses.karma_reward_limit_reached(comment, result, legacy76)
            try:
                common_functions.send_message_to_discord(mod_channel_webhook, f"{comment.author.name} has reached awarder karma limit. "
                                                                              f"Link to their awarder logs {link}")
            except requests.exceptions.HTTPError as http_err:
                db_manager_logger.warning(f"Message sending to Discord failed. {http_err}.")
            return CONSTANTS.KARMA_AWARDING_LIMIT_REACHED

    # checks rest of the conversation rules
    conv_check_result = conversation_checks.checks_for_karma_command(comment, fallout76marketplace)
    db_manager_logger.info(f"Result for the conversation check {conv_check_result}")
    return conv_check_result


def insert_karma_log(db_conn, comment):
    """
    Inserts the karma log into the database file.

    :param db_conn: Database connection object
    :param comment: Comment which triggered the karma command
    :return: None
    """
    try:
        with closing(db_conn.cursor()) as cursor:
            comment_dict = {'comment_id': comment.id,
                            'comment_submission_id': comment.submission.id,
                            'comment_submission_created_utc': comment.submission.created_utc,
                            'comment_author_name': comment.author.name,
                            'comment_parent_author_name': comment.parent().author.name,
                            'comment_created_utc': comment.created_utc,
                            'comment_permalink': comment.permalink
                            }
            cursor.execute("INSERT INTO comments VALUES ("
                           ":comment_id, "
                           ":comment_submission_id, "
                           ":comment_submission_created_utc, "
                           ":comment_author_name, "
                           ":comment_parent_author_name, "
                           ":comment_created_utc, "
                           ":comment_permalink)", comment_dict)
        db_conn.commit()
        db_manager_logger.info(f"Karma logs of comment id {comment.id} inserted successfully.")
    except sqlite3.IntegrityError:
        raise sqlite3.IntegrityError("Duplicate comment was received! {}".format(comment.permalink))


def process_command_non_mod_user(comment, fallout76marketplace, legacy76, db_conn, mod_channel_webhook):
    """
    Process the bot command for non moderator users
    :param mod_channel_webhook: Discord mod channel webhook
    :param comment: The comment object that needs to be checked
    :param db_conn: The db connection to SQL database
    :param fallout76marketplace: The subreddit instance in which the commands are being checked
    :param legacy76: The subreddit instance in which the stats are published if karma limit is reached
    """
    comment_body = comment.body.strip().replace("\\", "")
    if re.search(CONSTANTS.KARMA_PP, comment_body, re.IGNORECASE):
        db_manager_logger.info(f"Received karma plus comment (id={comment.id}) from u/{comment.author.name}.")
        output = karma_plus_command_non_mod_users(comment, fallout76marketplace, legacy76, db_conn, mod_channel_webhook)
        if output is CONSTANTS.KARMA_CHECKS_PASSED:
            insert_karma_log(db_conn, comment)
            # increment the karma in flair
            flair_functions.increment_karma(comment, fallout76marketplace)
            # reply to user
            bot_responses.karma_rewarded_comment(comment)
    # If comment says Karma--
    elif re.search(CONSTANTS.KARMA_MM, comment_body, re.IGNORECASE):
        db_manager_logger.info(f"Received karma minus comment (id={comment.id}) from u/{comment.author.name}.")
        bot_responses.karma_subtract_failed(comment)
    # Close submission
    elif re.search(CONSTANTS.CLOSE, comment_body, re.IGNORECASE):
        db_manager_logger.info(f"Received close comment (id={comment.id}) from u/{comment.author.name}.")
        conversation_checks.checks_for_close_command(comment)


def load_comment(comment, fallout76marketplace, legacy76, db_conn, mod_channel_webhook):
    """
    Loads the comment and if it a command, it executes the respective function
    :param mod_channel_webhook: Discord mod channel webhook
    :param comment: The comment object that needs to be checked
    :param db_conn: The db connection to SQL database
    :param fallout76marketplace: The subreddit instance in which the commands are being checked
    :param legacy76: The subreddit instance in which the stats are published if karma limit is reached
    """
    if comment.author.name == "AutoModerator":
        return None
    # If comment author is not mod
    if not is_mod(comment.author, fallout76marketplace):
        process_command_non_mod_user(comment, fallout76marketplace, legacy76, db_conn, mod_channel_webhook)
    else:
        comment_body = comment.body.strip().replace("\\", "")
        # Mods commands will be executed without checks
        # Increase Karma
        if re.search(CONSTANTS.KARMA_PP, comment_body, re.IGNORECASE):
            db_manager_logger.info(f"Received karma plus comment (id={comment.id}) from u/{comment.author.name}.")
            flair_functions.increment_karma(comment, fallout76marketplace)
            insert_karma_log(db_conn, comment)
            bot_responses.karma_rewarded_comment(comment)
        # Decrease Karma
        elif re.search(CONSTANTS.KARMA_MM, comment_body, re.IGNORECASE):
            db_manager_logger.info(f"Received karma minus comment (id={comment.id}) from u/{comment.author.name}.")
            flair_functions.decrement_karma(comment, fallout76marketplace)
            bot_responses.karma_subtract_comment(comment)
        # Close Submission
        elif re.search(CONSTANTS.CLOSE, comment_body, re.IGNORECASE):
            db_manager_logger.info(f"Received close comment (id={comment.id}) from u/{comment.author.name}.")
            flair_functions.close_post_trade(comment)
            bot_responses.close_submission_comment(comment.submission)

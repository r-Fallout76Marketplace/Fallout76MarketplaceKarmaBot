import logging

import yaml

import CONSTANTS
import bot_responses
from common_functions import get_subreddit_instance

flair_func_logger = logging.getLogger('main')


def is_mod_or_courier(author):
    """
    Checks if the author is mod.

    :param author: The redditor which will be checked.
    :return: True if the user is courier/moderator otherwise False
    """
    if author is None:
        return False

    fallout76marketplace = get_subreddit_instance("Fallout76Marketplace")
    moderators_list = fallout76marketplace.moderator()
    wiki = fallout76marketplace.wiki["custom_bot_config/courier_list"]
    yaml_format = yaml.safe_load(wiki.content_md)
    courier_list = [x.lower() for x in yaml_format['couriers']]
    if author in moderators_list:
        return True
    if author.name.lower() in courier_list:
        return True
    return False


def assign_karma(p_comment, user_flair):
    """
    Assigns flair to user based on karma value and mod/courier status.

    :param p_comment: The comment whose author flair will be updated.
    :param user_flair: The updated user flair text.
    :return: None
    """
    author_name = p_comment.author.name
    # Splits Flair into two
    user_flair_split = user_flair.split()
    fallout76marketplace = get_subreddit_instance("Fallout76Marketplace")

    # If user is mod assigns the green flair
    if is_mod_or_courier(p_comment.author):
        fallout76marketplace.flair.set(author_name, text=user_flair, flair_template_id=CONSTANTS.MODS_AND_COURIERS_FLAIR)
    else:
        # otherwise, assigns flair based on karma value
        karma_value = int(user_flair_split[-1])
        if karma_value < 49:
            fallout76marketplace.flair.set(author_name, text=user_flair, flair_template_id=CONSTANTS.ZERO_TO_FIFTY_FLAIR)
        elif 50 <= karma_value < 99:
            fallout76marketplace.flair.set(author_name, text=user_flair, flair_template_id=CONSTANTS.FIFTY_TO_HUNDRED_FLAIR)
        else:
            fallout76marketplace.flair.set(author_name, text=user_flair, flair_template_id=CONSTANTS.ABOVE_HUNDRED_FLAIR)
    flair_func_logger.info(f"Updated the user flair for {author_name} to {user_flair}")


def increment_karma(comment):
    """
    Increments the karma of parent comment author.

    :param comment: Comment that triggered the command.
    :return: None
    """
    try:
        p_comment = comment.parent()
        author_name = p_comment.author.name
    except AttributeError:
        bot_responses.karma_reward_failed(comment)
        return -1

    fallout76marketplace = get_subreddit_instance("Fallout76Marketplace")
    # if the author has no flair
    if not p_comment.author_flair_css_class:
        # sets the flair to one
        fallout76marketplace.flair.set(author_name, text='Karma: 1', flair_template_id=CONSTANTS.ZERO_TO_FIFTY_FLAIR)
        flair_func_logger.info(f"Setting the flair of u/{author_name} to Karma: 1.")
    else:
        # Getting the flair and adding the value
        user_flair = p_comment.author_flair_text
        # Splits Karma into two
        user_flair_split = user_flair.split()
        try:
            user_flair_split[-1] = int(user_flair_split[-1])
            user_flair_split[-1] += 1
            flair_func_logger.info(f"Incremented the karma of u/{author_name} to {user_flair_split[-1]}.")
        except ValueError:
            flair_func_logger.warning(f"The karma value for user u/{author_name} with flair {user_flair} could not be incremented.")
        # Combines back string and int part
        user_flair = ' '.join(map(str, user_flair_split))
        assign_karma(p_comment, user_flair)


def decrement_karma(comment):
    """
    Decrements the karma of parent comment author.

    :param comment: Comment that triggered the command.
    :return: None
    """
    try:
        p_comment = comment.parent()
        author_name = p_comment.author.name
    except AttributeError:
        bot_responses.karma_reward_failed(comment)
        return -1

    fallout76marketplace = get_subreddit_instance("Fallout76Marketplace")
    # if the author has no flair
    if not p_comment.author_flair_css_class:
        # sets the flair to one
        fallout76marketplace.flair.set(author_name, text='Karma: -1', flair_template_id=CONSTANTS.ZERO_TO_FIFTY_FLAIR)
        flair_func_logger.info(f"Setting the flair of u/{author_name} to Karma: -1.")
    else:
        # Getting the flair and adding the value
        user_flair = p_comment.author_flair_text

        # Splits Karma into two
        user_flair_split = user_flair.split()
        try:
            user_flair_split[-1] = int(user_flair_split[-1])
            user_flair_split[-1] -= 1
            flair_func_logger.info(f"Decremented the karma of u/{author_name} to {user_flair_split[-1]}.")
        except ValueError:
            flair_func_logger.warning(f"The karma value for user u/{author_name} with flair {user_flair} could not be decremented.")
        # Combines back string and int part
        user_flair = ' '.join(map(str, user_flair_split))
        assign_karma(p_comment, user_flair)


def close_post_trade(comment):
    """
    Changes the flair to Trade Closed and locks submission.

    :param comment: Comment that triggered the command.
    :return: None
    """
    submission = comment.submission
    submission.flair.select(CONSTANTS.TRADE_ENDED_ID)
    submission.mod.lock()
    flair_func_logger.info(f"Closed the submission with id {submission.id}")

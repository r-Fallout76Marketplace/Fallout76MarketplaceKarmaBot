import praw

import CONFIG
import CONSTANTS
import bot_responses


# Checks if the author is mod
def is_mod_or_courier(author):
    moderators_list = CONFIG.fallout76marketplace.moderator()
    courier_list = ['_juanv_', 'techybuffalo_279', 'wisck', 'babbbygirllchelss']
    if author in moderators_list:
        return True
    if author.name.lower() in courier_list:
        return True
    return False


# Assigns flair to user based on karma value and mod status
def assign_karma(p_comment, user_flair):
    author_name = p_comment.author.name
    # Splits Flair into two
    user_flair_split = user_flair.split()

    # If user is mod assigns the green flair
    if is_mod_or_courier(p_comment.author):
        CONFIG.fallout76marketplace.flair.set(author_name, text=str(user_flair),
                                              flair_template_id=CONSTANTS.MODS_AND_COURIERS_FLAIR)
    else:
        # otherwise assigns flair based on karma value
        karma_value = int(user_flair_split[-1])
        if karma_value < 49:
            CONFIG.fallout76marketplace.flair.set(author_name, text=str(user_flair),
                                                  flair_template_id=CONSTANTS.ZERO_TO_FIFTY_FLAIR)
        elif 50 <= karma_value < 99:
            CONFIG.fallout76marketplace.flair.set(author_name, text=str(user_flair),
                                                  flair_template_id=CONSTANTS.FIFTY_TO_HUNDRED_FLAIR)
        else:
            CONFIG.fallout76marketplace.flair.set(author_name, text=str(user_flair),
                                                  flair_template_id=CONSTANTS.ABOVE_HUNDRED_FLAIR)


# Increments karma by 1
def increment_karma(comment):
    try:
        p_comment = comment.parent()
        author_name = p_comment.author.name
    except AttributeError:
        bot_responses.karma_reward_failed(comment)
        return -1
    # if the author has no flair
    if p_comment.author_flair_css_class == '' or p_comment.author_flair_css_class is None:
        # sets the flair to one
        CONFIG.fallout76marketplace.flair.set(author_name, text='Karma: 1',
                                              flair_template_id=CONSTANTS.ZERO_TO_FIFTY_FLAIR)
    else:
        # Getting the flair and adding the value
        user_flair = p_comment.author_flair_text

        # Splits Karma into two
        user_flair_split = user_flair.split()
        try:
            user_flair_split[-1] = int(user_flair_split[-1])
            user_flair_split[-1] += 1
        except ValueError:
            pass
        # Combines back string and int part
        user_flair = ' '.join(map(str, user_flair_split))
        assign_karma(p_comment, user_flair)


# Decrements karma by 1
def decrement_karma(comment):
    try:
        p_comment = comment.parent()
        author_name = p_comment.author.name
    except AttributeError:
        bot_responses.karma_reward_failed(comment)
        return -1
    # if the author has no flair
    if p_comment.author_flair_css_class == '' or p_comment.author_flair_css_class is None:
        # sets the flair to one
        CONFIG.fallout76marketplace.flair.set(author_name, text='Karma: -1',
                                              flair_template_id=CONSTANTS.ZERO_TO_FIFTY_FLAIR)
    else:
        # Getting the flair and adding the value
        user_flair = p_comment.author_flair_text

        # Splits Karma into two
        user_flair_split = user_flair.split()
        try:
            user_flair_split[-1] = int(user_flair_split[-1])
            user_flair_split[-1] -= 1
        except ValueError:
            pass
        # Combines back string and int part
        user_flair = ' '.join(map(str, user_flair_split))
        assign_karma(p_comment, user_flair)


# Changes the flair to Trade Closed and locks submission
def close_post_trade(comment_or_submission):
    if isinstance(comment_or_submission, praw.models.reddit.submission.Submission):
        submission = comment_or_submission
    else:
        submission = comment_or_submission.submission
    submission.flair.select(CONSTANTS.TRADE_ENDED_ID)
    submission.mod.lock()

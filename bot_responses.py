import logging

import praw
import prawcore

import CONSTANTS
from common_functions import get_subreddit_instance

response_logger = logging.getLogger('main')


def reply(comment_or_submission, body):
    # Add disclaimer text
    response = body + "\n\n^(This action was performed by a bot, please contact the mods for any questions. "
    response += "[See disclaimer](https://www.reddit.com/user/Vault-TecTradingCo/comments/lkllre" \
                "/disclaimer_for_rfallout76marketplace/)) "
    try:
        new_comment = comment_or_submission.reply(response)
        response_logger.info(f"Bot replied to the {type(comment_or_submission).__name__} id {comment_or_submission.id}")
        new_comment.mod.distinguish(how="yes")
        new_comment.mod.lock()
    except prawcore.exceptions.Forbidden:
        raise prawcore.exceptions.Forbidden("Could not distinguish/lock comment")
    except praw.exceptions.APIException:
        new_comment = comment_or_submission.submission.reply(response)
        response_logger.warning(f"The comment with id {comment_or_submission.id} was deleted therefore the bot replied to submission "
                                f"{comment_or_submission.submission.id}.")
        new_comment.mod.distinguish(how="yes")
        new_comment.mod.lock()


def karma_rewarded_comment(comment):
    """
    Comment reply when karma is given successfully.

    :param comment: The comment that triggered the command.
    :return: None
    """
    p_comment = comment.parent()
    comment_body = f"Hi u/{comment.author.name}! You have successfully rewarded u/{p_comment.author.name} one karma point! Please note that karma may take " \
                   f"sometime to update. "
    reply(comment, comment_body)


def karma_reward_failed(comment):
    """
    Comment reply if the user tries to give deleted comment karma.

    :param comment: The comment that triggered the command.
    :return: None
    """
    comment_body = f"Hi u/{comment.author.name}! The bot cannot reward karma to deleted submissions or comments. Please reply to a submission/comment that " \
                   f"has not been deleted. "
    reply(comment, comment_body)


def cannot_reward_yourself_comment(comment):
    """
    Comment reply if the user try to reward themselves.

    :param comment: The comment that triggered the command.
    :return: None
    """
    comment_body = f"Hi u/{comment.author.name}! You cannot reward yourself karma. Sorry."
    reply(comment, comment_body)


def more_than_two_users_involved(comment):
    """
    Comment reply if more than two users are involved in the conversation.

    :param comment: The comment that triggered the command.
    :return: None
    """
    comment_body = f"Hi u/{comment.author.name}! It seems that you are trading under someone else's submission. Karma can only be given by " \
                   f"Original Poster (OP) to a user and vice versa. This restriction is placed to deter other people from hijacking someone else's post. " \
                   f"If you want to give karma, one of you needs to create a new submission, and once you are done, close the submission with !close command " \
                   f"rather than deleting it."
    reply(comment, comment_body)


def conversation_not_long_enough(comment):
    """
    Comment reply if conversation is not long enough.

    :param comment: The comment that triggered the command.
    :return: None
    """
    comment_body = f"Hi u/{comment.author.name}! You cannot award karma to a submission, you need to reply to a comment. Also, please negotiate and exchange " \
                   f"gamertags in comments rather than in chats/messages. If you are not sure you can look at an example of " \
                   f"[good karma exchange](https://www.reddit.com/r/Fallout76Marketplace/wiki/index/trading_karma). " \
                   f"This is the minimum conversation we expect from users before they can give karma."
    reply(comment, comment_body)


def deleted_or_removed(comment):
    """
    Comment reply if the comment itself is removed or the submission is deleted/removed.

    :param comment: The comment that triggered the command.
    :return: None
    """
    comment_body = f"Hi u/{comment.author.name}! It seems that either your comment has been removed by AutoModerator or most probably OP has deleted their " \
                   f"submission or has been removed by a Moderator. We don't allow users to trade karma on deleted/removed submissions. " \
                   f"Thank you for your understanding. "
    reply(comment, comment_body)


def already_rewarded_comment(comment, permalink):
    """
    Comment reply if the users is already awarded in a submission.

    :param permalink: The link to the comment where user gave karma.
    :param comment: The comment that triggered the command.
    :return: None
    """
    comment_body = f"Hi u/{comment.author.name} ! You have already rewarded {comment.parent().author.name} in this submission " \
                   f"[here](https://www.reddit.com{permalink})"
    reply(comment, comment_body)


def karma_reward_limit_reached(comment, karma_logs):
    """
    Comment reply if the user has reached their karma limit.

    :param comment: The comment that triggered the command.
    :param karma_logs: The user's karma logs for the day.
    :return: None
    """
    comment_body = f"Hi u/{comment.author.name}! You have reached the karma reward limit. You will not be able to reward karma until next " \
                   f"[midnight EST](https://time.is/EST). You can contact mods and they can give karma on your behalf. Thank you for your patience!"
    reply(comment, comment_body)
    title = comment.author.name + " have reached their daily awarder karma limit"
    self_text = ""
    for log in karma_logs:
        self_text += f"Awarded to user u/{log[4]}: [Link to the comment](https://www.reddit.com{log[6]})\n\n"
    legacy76 = get_subreddit_instance("legacy76")
    submission = legacy76.submit(title=title, selftext=self_text, flair_id=CONSTANTS.AWARDER_KARMA_LIMIT_REACHED)
    return f"https://www.reddit.com{submission.permalink}"


def karma_trading_posts_only(comment):
    """
    Comment reply if the user give karma on wrong submission.

    :param comment: The comment that triggered the command.
    :return: None
    """
    comment_body = f"Hi u/{comment.author.name}! You can only give karma to others under a trading post i.e submission with PlayStation, XBOX or PC " \
                   f"flair. Please refer to wiki page for more information."
    reply(comment, comment_body)


def karma_subtract_comment(comment):
    """
    Comment reply when karma is subtracted successfully.

    :param comment: The comment that triggered the command.
    :return: None
    """
    p_comment = comment.parent()
    comment_body = f"{p_comment.author.name} karma has been decremented by one. Please note that karma may take sometime to update."
    reply(comment, comment_body)


def karma_subtract_failed(comment):
    """
    Comment reply when non-moderator uses this command.

    :param comment: The comment that triggered the command.
    :return: None
    """
    comment_body = "Karma can only be subtracted by mods only. Please contact mods if you have been scammed."
    reply(comment, comment_body)


def close_submission_comment(submission):
    """
    Comment reply when the submission close command is triggered.

    :param submission: The submission that will be closed.
    :return: None
    """
    comment_body = "The submission has been closed and comments have been locked. Please contact mods, if you want to open the submission."
    reply(submission, comment_body)


def close_submission_failed(comment, is_trading_post):
    """
    Comment reply when submission close is requested by wrong user.

    :param is_trading_post: Flag to indicated if a user triggered the close command on wrong submission type.
    :param comment: The comment that triggered the command.
    :return: None
    """
    if is_trading_post:
        comment_body = "The submission can only be close by OP or the mods. Please report post if it is breaking rules."
    else:
        comment_body = "This type of submission cannot be closed. Please refer to wiki page for more information."
    reply(comment, comment_body)

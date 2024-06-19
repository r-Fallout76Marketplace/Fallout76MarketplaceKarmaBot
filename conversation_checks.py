from __future__ import annotations

import re
from enum import IntEnum, auto
from typing import Optional

import yaml
from asyncpraw.models import Comment, Redditor, Submission, Subreddit


class CloseChecks(IntEnum):
    CLOSE_CHECKS_PASSED = auto()
    NOT_TRADING_SUBMISSION = auto()
    NOT_OP = auto()


class KarmaChecks(IntEnum):
    KARMA_CHECKS_PASSED = auto()
    ALREADY_REWARDED = auto()
    CANNOT_REWARD_YOURSELF = auto()
    CONVERSATION_NOT_LONG_ENOUGH = auto()
    DELETED_OR_REMOVED = auto()
    INCORRECT_SUBMISSION_TYPE = auto()
    KARMA_AWARDING_LIMIT_REACHED = auto()
    MORE_THAN_TWO_USERS = auto()
    UNAUTHORIZED = auto()


def is_removed_or_deleted(content: Comment | Submission) -> bool:
    """Checks if comment, parent comment or submission has been removed/deleted.

    If it is deleted, the author is None. If it is removed, the removed_by will have moderator name.

    :param content: Reddit's comment or submission

    :returns: True if the items is deleted or removed. Otherwise, False.

    """
    return content.author is None or content.mod_note or content.removed


async def is_mod(user: Redditor, subreddit: Subreddit) -> bool:
    """Checks if the author is a moderator.

    :param user: The Reddit user whose moderator status will be checked.
    :param subreddit: The subreddit where the user's moderator status will be checked.

    :returns: True if the user is a moderator, otherwise False.

    """
    moderators_list = await subreddit.moderator()
    return user in moderators_list


async def is_courier(author: Optional[Redditor], subreddit: Subreddit) -> bool:
    """Checks if the author is a courier.

    :param author: The Redditor to be checked.
    :param subreddit: The subreddit where the user's courier status will be checked.

    :returns: True if the user is a courier, otherwise False.

    """
    if author is None:
        return False

    wiki = await subreddit.wiki.get_page("custom_bot_config/courier_list")
    yaml_format = yaml.safe_load(wiki.content_md)
    courier_list = (x.lower() for x in yaml_format["couriers"])
    return author.name.lower() in courier_list


async def is_mod_or_courier(author: Optional[Redditor], subreddit: Subreddit) -> bool:
    """Checks if the author is a moderator or a courier.

    :param author: The Redditor to be checked.
    :param subreddit: The subreddit where the user's moderator/courier status will be checked.

    :returns: True if the user is a moderator or a courier, otherwise False.

    """
    return await is_mod(author, subreddit) or await is_courier(author, subreddit)


SUBMISSION_FLAIR_REGEX = re.compile("^(XBOX|PlayStation|PC)$", re.IGNORECASE)


async def flair_checks(comment: Comment) -> bool:
    """Checks if submission is eligible for trading by checking the flair.

    The karma can only be exchanged under the submission with flair XBOX, PlayStation, or PC. :param comment: praw Comment that triggered the command.

    """
    submission = comment.submission
    await submission.load()
    submission_flair_text = "" if submission.link_flair_text is None else submission.link_flair_text
    match = SUBMISSION_FLAIR_REGEX.match(submission_flair_text)
    if match is None:
        return False
    else:
        return True


async def checks_for_close_command(comment: Comment) -> CloseChecks:
    """Performs checks to determine if the submission can be closed.

    :param comment: The comment object that triggered the command.

    :returns: A CloseChecks enum value indicating the result of the checks.

    """
    await comment.load()
    submission = comment.submission
    await submission.load()

    # Only OP can close the trade
    if comment.author != submission.author:
        return CloseChecks.NOT_OP

    if await flair_checks(comment):
        return CloseChecks.CLOSE_CHECKS_PASSED
    else:
        return CloseChecks.NOT_TRADING_SUBMISSION


async def checks_for_karma_command(comment: Comment, fo76_subreddit: Subreddit) -> KarmaChecks:
    """Performs checks for karma command comments.

    :param comment: the command comment.
    :param fo76_subreddit: SubredditHelper Subreddit object to make API calls related to subreddit.

    :returns: A KarmaChecks enum value indicating the result of the checks.

    """
    if not await flair_checks(comment):
        return KarmaChecks.INCORRECT_SUBMISSION_TYPE

    # Make sure author isn't rewarding themselves
    parent_post = await comment.parent()
    await parent_post.load()
    if comment.author == parent_post.author:
        return KarmaChecks.CANNOT_REWARD_YOURSELF

    comment_thread = []  # Stores all comments in an array
    users_involved = set()  # Stores all the users involved
    comment_thread.append(comment)
    users_involved.add(comment.author)

    # If the karma comment is not root meaning it ha a parent comment
    if not comment.is_root:
        parent_comment = await comment.parent()
        await parent_comment.load()
        comment_thread.append(parent_comment)
        users_involved.add(parent_comment.author)

    comment_thread.append(comment.submission)
    users_involved.add(comment.submission.author)

    # Remove mods and couriers from the users involved
    for user in users_involved.copy():
        if await is_mod_or_courier(user, fo76_subreddit):
            users_involved.remove(user)

    # If the conversation is shorter than two comments
    if len(comment_thread) <= 2:
        return KarmaChecks.CONVERSATION_NOT_LONG_ENOUGH

    removed_or_deleted = any([is_removed_or_deleted(content) for content in comment_thread])
    if removed_or_deleted:
        return KarmaChecks.DELETED_OR_REMOVED

    # If there are more than two people involved
    if len(users_involved) > 2:
        return KarmaChecks.MORE_THAN_TWO_USERS

    # If all checks pass
    return KarmaChecks.KARMA_CHECKS_PASSED

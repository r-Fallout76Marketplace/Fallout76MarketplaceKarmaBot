import logging

from asyncpraw.exceptions import APIException
from asyncpraw.models import Comment, Submission

response_logger = logging.getLogger("karma_bot")


async def reply(reddit_post: Comment | Submission, body: str) -> None:
    # Adds disclaimer text
    response = body + "\n\n^(This action was performed by a bot. Please contact the mods for any questions. "
    response += "[See disclaimer](https://www.reddit.com/user/Vault-TecTradingCo/comments/lkllre/disclaimer_for_rfallout76marketplace/)) "
    try:
        new_comment = await reddit_post.reply(response)
        response_logger.info(f"Bot replied to the {type(reddit_post).__name__} id {reddit_post.id}")
        await new_comment.mod.distinguish(how="yes")
        await new_comment.mod.lock()
    except APIException:
        new_comment = await reddit_post.submission.reply(response)
        response_logger.warning(f"The comment with id {reddit_post.id} was deleted; therefore, the bot replied to submission {reddit_post.submission.id}.")
        await new_comment.mod.distinguish(how="yes")
        await new_comment.mod.lock()


async def karma_rewarded_comment(comment: Comment) -> None:
    """Comment reply when karma is given successfully.

    :param comment: The comment that triggered the command.

    :returns: None

    """
    p_comment = await comment.parent()
    await p_comment.load()
    comment_body = (
        f"Hi u/{comment.author.name}! You have successfully rewarded u/{p_comment.author.name} with one karma point! Please note that karma may take "
        f"sometime to update."
    )
    await reply(comment, comment_body)


async def karma_reward_failed(comment: Comment) -> None:
    """Comment reply if the user tries to give karma to a deleted comment.

    :param comment: The comment that triggered the command.

    :returns: None

    """
    comment_body = (
        f"Hi u/{comment.author.name}! The bot cannot reward karma for deleted submissions or comments. Please reply to a submission/comment that "
        f"has not been deleted."
    )
    await reply(comment, comment_body)


async def cannot_reward_yourself_comment(comment: Comment) -> None:
    """Comment reply if the user tries to reward themselves.

    :param comment: The comment that triggered the command.

    :returns: None

    """
    comment_body = f"Hi u/{comment.author.name}! You cannot reward yourself with karma. Sorry."
    await reply(comment, comment_body)


async def more_than_two_users_involved(comment: Comment) -> None:
    """Comment reply if more than two users are involved in the conversation.

    :param comment: The comment that triggered the command.

    :returns: None

    """
    comment_body = (
        f"Hi u/{comment.author.name}! It seems that you are trading under someone else's submission. Karma can only be given by the "
        f"Original Poster (OP) to a user and vice versa. This restriction is in place to deter other people from hijacking someone else's post. "
        f"If you want to give karma, one of you needs to create a new submission. Once done, close the submission with the !close command "
        f"rather than deleting it."
    )
    await reply(comment, comment_body)


async def conversation_not_long_enough(comment: Comment) -> None:
    """Comment reply if the conversation is not long enough.

    :param comment: The comment that triggered the command.

    :returns: None

    """
    comment_body = (
        f"Hi u/{comment.author.name}! You cannot award karma to a submission, you need to reply to a comment. Also, please negotiate and exchange "
        f"gamertags in comments rather than in chats/messages. If you are not sure, you can look at an example of a "
        f"[good karma exchange](https://www.reddit.com/r/Fallout76Marketplace/wiki/index/trading_karma). "
        f"This is the minimum conversation we expect from users before they can give karma."
    )
    await reply(comment, comment_body)


async def deleted_or_removed(comment: Comment) -> None:
    """Comment reply if the comment itself is removed or the submission is deleted/removed.

    :param comment: The comment that triggered the command.

    :returns: None

    """
    comment_body = (
        f"Hi u/{comment.author.name}! It seems that either your comment has been removed by AutoModerator, or most probably, the OP has deleted their "
        f"submission or it has been removed by a Moderator. We don't allow users to trade karma on deleted/removed submissions. "
        f"Thank you for your understanding."
    )
    await reply(comment, comment_body)


async def already_rewarded_comment(comment: Comment, permalink: str) -> None:
    """Comment reply if the user has already been rewarded in a submission.

    :param comment: The comment that triggered the command.
    :param permalink: The link to the comment where the user gave karma.

    :returns: None

    """
    p_comment = await comment.parent()
    await p_comment.load()
    comment_body = f"Hi u/{comment.author.name}! You have already rewarded {p_comment.author.name} in this submission. " f"See [here]({permalink})"
    await reply(comment, comment_body)


async def karma_reward_limit_reached(comment: Comment) -> None:
    """Comment reply if the user has reached their karma limit.

    :param comment: The comment that triggered the command.

    :returns: None

    """
    comment_body = (
        f"Hi u/{comment.author.name}! You have reached the karma reward limit. You will not be able to reward karma until the next "
        f"midnight UTC. You can contact mods, and they can give karma on your behalf. Thank you for your patience!"
    )
    await reply(comment, comment_body)


async def karma_trading_posts_only(comment: Comment) -> None:
    """Comment reply if the user gives karma on the wrong submission.

    :param comment: The comment that triggered the command.

    :returns: None

    """
    comment_body = (
        f"Hi u/{comment.author.name}! You can only give karma to others under a trading post, i.e., a submission with PlayStation, XBOX, or PC "
        f"flair. Please refer to the wiki page for more information."
    )
    await reply(comment, comment_body)


async def karma_subtract_comment(comment: Comment) -> None:
    """Comment reply when karma is subtracted successfully.

    :param comment: The comment that triggered the command.

    :returns: None

    """
    p_comment = await comment.parent()
    await p_comment.load()
    comment_body = f"{p_comment.author.name}'s karma has been decremented by one. Please note that karma may take some time to update."
    await reply(comment, comment_body)


async def karma_subtract_failed(comment: Comment) -> None:
    """Comment reply when a non-moderator tries to use this command.

    :param comment: The comment that triggered the command.

    :returns: None

    """
    comment_body = "Karma can only be subtracted by moderators. Please contact mods if you have been scammed."
    await reply(comment, comment_body)


async def close_submission_comment(submission: Submission) -> None:
    """Comment reply when the submission close command is triggered.

    :param submission: The submission that will be closed.

    :returns: None

    """
    comment_body = "The submission has been closed, and comments have been locked. Please contact mods if you want to open the submission."
    await reply(submission, comment_body)


async def close_submission_failed(comment: Comment, is_trading_post: bool) -> None:
    """Comment reply when the submission close is requested by the wrong user.

    :param comment: The comment that triggered the command.
    :param is_trading_post: Flag to indicate if a user triggered the close command on the wrong submission type.

    :returns: None

    """
    if is_trading_post:
        comment_body = "The submission can only be closed by the OP or the mods. Please report the post if it is breaking rules."
    else:
        comment_body = "This type of submission cannot be closed. Please refer to the wiki page for more information."
    await reply(comment, comment_body)

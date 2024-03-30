from __future__ import annotations

import asyncio
from typing import Any, Literal, TypedDict, cast

from asyncpraw.models import Comment, Submission, Subreddit

import bot_responses
from conversation_checks import CloseChecks, KarmaChecks, checks_for_close_command, checks_for_karma_command, is_mod
from db_operations import check_already_rewarded, find_or_create_user_profile, get_daily_given_karma, get_mongo_collection, update_karma_logs
from flair_functions import close_post_trade, update_flair
from utils import Connections, create_logger

bot_commands_logger = create_logger(logger_name="karma_bot")


class GamerTag(TypedDict):
    """A dictionary representing a gamer tag."""

    username: str
    platform: Literal["PC", "XBOX", "PlayStation"]
    user_id: int


async def update_karma(parent_post: Comment | Submission, karma_change: int, connections: Connections) -> None:
    """Updates the karma of the author of the parent_post based on the karma_change value. Both the flair and the database are updated.

    :param parent_post: The comment or submission object whose author's karma is to be updated.
    :param karma_change: The change in karma value. Positive for an increase, negative for a decrease.
    :param connections: An instance of the Connections class containing database and subreddit connection.

    :returns: None

    """
    users_collection = await get_mongo_collection(collection_name="user_karma", fallout76marketplace_karma_db=connections.karma_db)
    profile = await find_or_create_user_profile(parent_post.author.name, users_collection)
    profile = cast(dict[str, Any], profile)
    bot_commands_logger.info(f"Karma before {profile['reddit_username']}: {profile['karma']}")
    if karma_change == 1:
        profile["karma"] += karma_change
    else:
        profile["karma"] -= karma_change
    update_task = asyncio.ensure_future(users_collection.update_one({"reddit_username": parent_post.author.name}, {"$set": {"karma": profile["karma"]}}))

    # Reconstructing user flair from their profile on db
    gamertags: list[GamerTag] = profile["gamertags"]
    platforms_emojis = {f":{gamertag['platform'].lower()}:" for gamertag in gamertags}
    user_flair = f"{' '.join(platforms_emojis).strip()} Karma: {profile['karma'] + profile['m76_karma']}"
    await update_flair(parent_post=parent_post, user_flair=user_flair, karma=profile["karma"], connections=connections)

    await update_task
    bot_commands_logger.info(f"Karma after {profile['reddit_username']}: {profile['karma']}")


async def karma_command(comment: Comment, karma_change: int, connections: Connections) -> None:
    """Handle the karma command.

    Logs the received command and performs necessary checks before awarding karma. If the user is a moderator, it directly updates the karma. If not, it checks
    if the user is authorized to award karma based on certain criteria.

    :param comment: The comment that triggered the karma command.
    :param karma_change: The amount of karma to be awarded (positive) or subtracted (negative).
    :param connections: Connections object containing connections to the database and Reddit API.

    :returns: None

    """
    is_user_mod = await is_mod(comment.author, connections.fo76_subreddit)
    bot_commands_logger.info(f"Received Karma command: is_mod: {is_user_mod}, karma_change: {karma_change}")
    already_rewarded_chk = (KarmaChecks.ALREADY_REWARDED, "")  # Initializing variable for later use
    if not is_user_mod:
        karma_checks = await checks_for_karma_command(comment, connections.fo76_subreddit)

        # Only worth checking if previous checks have passed
        if karma_checks == KarmaChecks.KARMA_CHECKS_PASSED:
            p_comment = await comment.parent()
            await p_comment.load()
            already_rewarded_chk = await check_already_rewarded(
                comment.author.name,
                p_comment.author.name,
                comment.submission.id,
                connections,
            )
            karma_checks = already_rewarded_chk[0]

        # Only worth checking if previous checks have passed
        if karma_checks == KarmaChecks.KARMA_CHECKS_PASSED:
            daily_karma = await get_daily_given_karma(comment.author.name, connections)
            if daily_karma >= 10:
                karma_checks = KarmaChecks.KARMA_AWARDING_LIMIT_REACHED
    else:
        karma_checks = KarmaChecks.KARMA_CHECKS_PASSED
    bot_commands_logger.info(f"Checks Result: {karma_checks.name}, already_rewarded_chk={already_rewarded_chk}")

    match karma_checks:
        case KarmaChecks.KARMA_CHECKS_PASSED:
            p_comment = await comment.parent()
            await p_comment.load()
            async with asyncio.TaskGroup() as tg:
                tg.create_task(update_karma_logs(comment.author.name, p_comment.author.name, comment, connections))
                tg.create_task(update_karma(p_comment, karma_change, connections))
                tg.create_task(bot_responses.karma_rewarded_comment(comment))
        case KarmaChecks.ALREADY_REWARDED:
            await bot_responses.already_rewarded_comment(comment, permalink=already_rewarded_chk[1])
        case KarmaChecks.CANNOT_REWARD_YOURSELF:
            await bot_responses.cannot_reward_yourself_comment(comment)
        case KarmaChecks.CONVERSATION_NOT_LONG_ENOUGH:
            await bot_responses.conversation_not_long_enough(comment)
        case KarmaChecks.DELETED_OR_REMOVED:
            await bot_responses.deleted_or_removed(comment)
        case KarmaChecks.INCORRECT_SUBMISSION_TYPE:
            await bot_responses.karma_trading_posts_only(comment)
        case KarmaChecks.KARMA_AWARDING_LIMIT_REACHED:
            await bot_responses.karma_reward_limit_reached(comment)
            # TODO: Send message to mod channel
        case KarmaChecks.MORE_THAN_TWO_USERS:
            await bot_responses.more_than_two_users_involved(comment)


async def close_command(comment: Comment, fo76_subreddit: Subreddit) -> None:
    """Handle the close command.

    Logs the received command and performs necessary checks before closing the submission. If the user is a moderator, it directly closes the submission. If
    not, it checks if the user is authorized to close the submission based on certain criteria.

    :param comment: The comment that triggered the close command.
    :param fo76_subreddit: SubredditHelper Subreddit object to make API calls related to subreddit.

    :returns: None

    """
    is_user_mod = is_mod(comment.author, fo76_subreddit)
    bot_commands_logger.info(f"Received Closing command: {comment}, is_mod: {is_user_mod}")
    if not is_user_mod:
        close_checks = await checks_for_close_command(comment)
    else:
        close_checks = CloseChecks.CLOSE_CHECKS_PASSED

    match close_checks:
        case CloseChecks.CLOSE_CHECKS_PASSED:
            await close_post_trade(comment)
            await bot_responses.close_submission_comment(comment.submission)
        case CloseChecks.NOT_TRADING_SUBMISSION:
            await bot_responses.close_submission_failed(comment, is_trading_post=False)
        case CloseChecks.NOT_OP:
            await bot_responses.close_submission_failed(comment, is_trading_post=True)

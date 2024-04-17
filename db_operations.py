from __future__ import annotations

from typing import Any, Mapping

from asyncpraw.models import Comment
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ReturnDocument

from conversation_checks import KarmaChecks
from utils import Connections, create_logger, next_midnight_timestamp

db_operations_logs = create_logger("karma_bot")


async def get_mongo_collection(collection_name: str, fallout76marketplace_karma_db: AsyncIOMotorDatabase) -> AsyncIOMotorCollection:
    """Returns the user databased from dataBased Cluster from MongoDB

    :returns: Returns a Collection from Mongo DB

    """
    return fallout76marketplace_karma_db[collection_name]


async def find_or_create_user_profile(reddit_username: str, users_collection: AsyncIOMotorCollection) -> Mapping[str, Any]:
    """Finds the user in the users_collection, or creates one if it doesn't exist using default values.

    :param reddit_username: The user whose profile to find or create
    :param users_collection: The collection in which the profile will be searched or inserted

    :returns: Dict object with user profile info

    """
    profile = await users_collection.find_one({"reddit_username": reddit_username})
    if profile is None:
        profile = await users_collection.find_one_and_update(
            {"reddit_username": reddit_username},
            {
                "$setOnInsert": {
                    "gamertags": [],
                    "karma": 0,
                    "m76_karma": 0,
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    return profile


async def check_already_rewarded(from_user: str, to_user: str, submission_id: str, connections: Connections) -> tuple[KarmaChecks, str]:
    """Check if a user has already rewarded another user on a specific submission.

    :param from_user: The username of the user who initiated the reward.
    :param to_user: The username of the user who received the reward.
    :param submission_id: The unique identifier of the submission.
    :param connections: Connections object containing connections to the database and Reddit API.

    :returns: An instance of KarmaChecks enum indicating the result of the check.

    """
    karma_logs_collection = await get_mongo_collection(collection_name="karma_logs", fallout76marketplace_karma_db=connections.karma_db)
    karma_log = await karma_logs_collection.find_one({"from_user": from_user, "to_user": to_user, "submission_id": submission_id})
    if karma_log is None:
        result = KarmaChecks.KARMA_CHECKS_PASSED
        return result, ""
    else:
        result = KarmaChecks.ALREADY_REWARDED
        return result, karma_log["comment_permalink"]


async def update_karma_logs(from_user: str, to_user: str, comment: Comment, connections: Connections) -> None:
    """Update karma logs by inserting a dictionary.

    :param from_user: The username of the user who initiated the reward.
    :param to_user: The username of the user who received the reward.
    :param comment: The comment that initiated the karma action, granting karma points.
    :param connections: Connections object containing connections to the database and Reddit API.

    """
    db_operations_logs.info(
        f"Inserting karma logs: from_user={from_user}, to_user={to_user}, submission_id={comment.submission.id}, comment_id={comment.id}"
    )
    karma_logs_collection = await get_mongo_collection(collection_name="karma_logs", fallout76marketplace_karma_db=connections.karma_db)
    await karma_logs_collection.insert_one(
        {
            "from_user": from_user,
            "to_user": to_user,
            "submission_id": comment.submission.id,
            "comment_permalink": comment.permalink,
            "utc_created": comment.created_utc,
        }
    )


async def get_daily_given_karma(from_user: str, connections: Connections) -> int:
    """Retrieve the amount of karma given by a specific user on a daily basis.

    :param str from_user: The username of the user whose given karma is to be retrieved.
    :param Connections connections: An object representing connections to databases or APIs.

    :returns: The amount of karma given by the specified user on a daily basis.

    """
    karma_logs_collection = await get_mongo_collection(collection_name="karma_logs", fallout76marketplace_karma_db=connections.karma_db)
    next_midnight = next_midnight_timestamp()
    count = await karma_logs_collection.count_documents({"from_user": from_user, "utc_created": {"$lt": next_midnight, "$gt": next_midnight - 86400}})
    db_operations_logs.info(f"{from_user} gave {count} karma in past 24 hours.")
    return count

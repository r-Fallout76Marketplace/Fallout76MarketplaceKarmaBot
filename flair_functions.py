from asyncpraw.models import Comment, Submission

from conversation_checks import is_mod_or_courier
from utils import Connections, create_logger

flair_func_logger = create_logger(logger_name="karma_bot")

ABOVE_HUNDRED_FLAIR = "0467e0de-4a4d-11eb-9453-0e4e6fcf2865"
FIFTY_TO_HUNDRED_FLAIR = "2624bc6a-4a4d-11eb-8b7c-0e6968d78889"
ZERO_TO_FIFTY_FLAIR = "3c680234-4a4d-11eb-8124-0edd2b620987"
MODS_AND_COURIERS_FLAIR = "51524056-4a4d-11eb-814b-0e7b734c1fd5"


async def update_flair(parent_post: Comment | Submission, user_flair: str, karma: int, connections: Connections) -> None:
    """Assigns flair to user based on karma value and mod/courier status.

    :param parent_post: The comment/submission whose author flair will be updated.
    :param user_flair: The updated user flair text.
    :param karma: User karma value
    :param connections: Connections object containing subreddit object and mongodb connection

    :returns: None

    """
    author_name = parent_post.author.name
    fallout76marketplace = connections.fo76_subreddit

    # If user is mod assigns the green flair
    if await is_mod_or_courier(parent_post.author, fallout76marketplace):
        await fallout76marketplace.flair.set(author_name, text=user_flair, flair_template_id=MODS_AND_COURIERS_FLAIR)
    elif karma < 49:
        await fallout76marketplace.flair.set(author_name, text=user_flair, flair_template_id=ZERO_TO_FIFTY_FLAIR)
    elif 50 <= karma < 99:
        await fallout76marketplace.flair.set(author_name, text=user_flair, flair_template_id=FIFTY_TO_HUNDRED_FLAIR)
    else:
        await fallout76marketplace.flair.set(author_name, text=user_flair, flair_template_id=ABOVE_HUNDRED_FLAIR)
    flair_func_logger.info(f"Updated the user flair for {author_name} to {user_flair}")


TRADE_ENDED_ID = "1e0c3870-a456-11ea-aa7a-0ee73ab9d31f"


async def close_post_trade(comment: Comment) -> None:
    """Changes the flair to Trade Closed and locks submission.

    :param comment: Comment that triggered the command.

    :returns: None

    """
    submission = comment.submission
    await submission.flair.select(TRADE_ENDED_ID)
    await submission.mod.lock()
    flair_func_logger.info(f"Closed the submission with id {submission.id}")

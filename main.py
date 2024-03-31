#!.venv/bin/python
from __future__ import annotations

import asyncio
import re
import time
from traceback import format_exc
from typing import Awaitable, Callable, Never

from asyncpraw import Reddit
from asyncprawcore.exceptions import AsyncPrawcoreException
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorDatabase

from bot_commands import close_command, karma_command
from utils import Connections, create_logger, create_reddit_instance, get_karma_db, send_traceback_to_discord

load_dotenv()


def exception_wrapper(func: Callable[[Reddit, AsyncIOMotorDatabase], Awaitable[None]]) -> Callable[[Reddit, AsyncIOMotorDatabase], Awaitable[None]]:
    """Decorator to handle the exceptions and to ensure the code doesn't exit unexpectedly.

    :param func: function that needs to be called

    :returns: wrapper function
    :rtype: Callable[[Reddit, AsyncIOMotorDatabase], Awaitable[None]]

    """

    async def wrapper(reddit_instance: Reddit, karma_db: AsyncIOMotorDatabase) -> Never:
        global cool_down_timer

        while True:
            try:
                await func(reddit_instance, karma_db)
            except AsyncPrawcoreException as asyncpraw_exc:
                main_logger.exception("AsyncPrawcoreException", exc_info=True)
                await send_traceback_to_discord(exception_name=type(asyncpraw_exc).__name__, exception_message=str(asyncpraw_exc), exception_body=format_exc())

                time.sleep(cool_down_timer)
                cool_down_timer = (cool_down_timer + 30) % 360
                main_logger.info(f"Cooldown: {cool_down_timer} seconds")
            except Exception as general_exc:
                main_logger.critical("Serious Exception", exc_info=True)
                await send_traceback_to_discord(exception_name=type(general_exc).__name__, exception_message=str(general_exc), exception_body=format_exc())

                time.sleep(cool_down_timer)
                cool_down_timer = (cool_down_timer + 30) % 360
                main_logger.info(f"Cooldown: {cool_down_timer} seconds")

    return wrapper


KARMA_PP = re.compile(r"^(\++KARMA|KARMA\++)", re.IGNORECASE)
KARMA_MM = re.compile(r"^(-+KARMA|KARMA-+)", re.IGNORECASE)
CLOSE = re.compile(r"^(!CLOSE|CLOSE!)", re.IGNORECASE)


@exception_wrapper
async def read_comments(reddit_instance: Reddit, karma_db: AsyncIOMotorDatabase) -> None:
    """Checks comments as they come on r/Fallout76MarketPlace and performs actions accordingly.

    :param reddit_instance: The Reddit Instance from AsyncPRAW. Used to make API calls.
    :param karma_db: MongoDB database used to get the collections

    :returns: Nothing is returned

    """
    main_logger.info(f"Logged into {await reddit_instance.user.me()} Account.")
    fo76_subreddit = await reddit_instance.subreddit("Fallout76Marketplace")
    conn = Connections(fo76_subreddit=fo76_subreddit, karma_db=karma_db)

    async for comment in fo76_subreddit.stream.comments(skip_existing=True):  # Comment
        if comment.author is None:
            continue

        if comment.author.name.lower() == "automoderator":
            continue

        comment_body = comment.body.strip().replace("\\", "")
        if KARMA_PP.search(comment_body):
            await karma_command(comment, 1, conn)
        elif KARMA_MM.search(comment_body):
            await karma_command(comment, -1, conn)
        elif CLOSE.search(comment_body):
            await close_command(comment, fo76_subreddit)


async def main() -> None:
    async with (
        get_karma_db() as databased,
        create_reddit_instance() as reddit,
    ):
        await asyncio.gather(
            read_comments(reddit, databased),
        )


if __name__ == "__main__":
    cool_down_timer = 0
    main_logger = create_logger(logger_name="karma_bot", set_format=True)
    asyncio.run(main())

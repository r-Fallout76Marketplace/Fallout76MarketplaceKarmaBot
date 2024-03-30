from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from logging import Logger, config, getLogger
from os import getenv
from pathlib import Path
from traceback import print_exc
from typing import AsyncGenerator, Optional

import aiohttp
import yaml
from aiohttp import ClientSession
from asyncpraw import Reddit
from asyncpraw.models import Subreddit
from colorlog import ColoredFormatter
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

Path("logs").mkdir(exist_ok=True)
conf_file = Path("logging.conf")
config.fileConfig(str(conf_file))


async def post_to_pastebin(title: str, body: str) -> Optional[str]:
    """Uploads the text to PasteBin and returns the url of the Paste

    :param title: Title of the Paste
    :param body: Body of Paste

    :returns: url of Paste

    """
    login_data = {"api_dev_key": getenv("PASTEBIN_DEV_KEY"), "api_user_name": getenv("PASTEBIN_USERNAME"), "api_user_password": getenv("PASTEBIN_PASSWORD")}

    data = {
        "api_option": "paste",
        "api_dev_key": getenv("PASTEBIN_DEV_KEY"),
        "api_paste_code": body,
        "api_paste_name": title,
        "api_paste_expire_date": "1W",
        "api_user_key": None,
        "api_paste_format": "python",
    }

    try:
        async with ClientSession() as session:
            login_resp = await session.post("https://pastebin.com/api/api_login.php", data=login_data)
            if login_resp.status == 200:
                data["api_user_key"] = await login_resp.text()
                post_resp = await session.post("https://pastebin.com/api/api_post.php", data=data)
                if post_resp.status == 200:
                    return await post_resp.text()
    except aiohttp.ClientError:
        print_exc()
    return None


async def send_traceback_to_discord(exception_name: str, exception_message: str, exception_body: str) -> None:
    """Send the traceback of an exception to a Discord webhook.

    :param exception_name: The name of the exception.
    :param exception_message: A brief summary of the exception.
    :param exception_body: The full traceback of the exception.

    """
    paste_bin_url = await post_to_pastebin(f"{exception_name}: {exception_message}", exception_body)

    if paste_bin_url is None:
        return

    webhook = getenv("DISCORD_WEBHOOK", "deadass")
    data = {"content": f"[{exception_name}: {exception_message}]({paste_bin_url})", "username": "Lemmy_BasedCountBot"}
    async with ClientSession(headers={"Content-Type": "application/json"}) as session:
        async with session.post(url=webhook, data=json.dumps(data)):
            pass


@dataclass
class Connections:
    fo76_subreddit: Subreddit
    karma_db: AsyncIOMotorDatabase


@asynccontextmanager
async def get_karma_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Returns the MongoDB AsyncIOMotorClient

    :returns: AsyncIOMotorClient object
    :rtype: AsyncIOMotorClient

    """
    cluster = AsyncIOMotorClient(getenv("MONGO_PASS"))
    try:
        yield cluster["fallout76marketplace_karma_db"]
    finally:
        cluster.close()


@asynccontextmanager
async def create_reddit_instance() -> Reddit:
    """Creates Reddit instance and returns the object

    :returns: Reddit instance object.

    """
    with open("config.yaml") as stream:
        bot_config = yaml.safe_load(stream)

    reddit = Reddit(
        client_id=bot_config["reddit_credentials"]["client_id"],
        client_secret=bot_config["reddit_credentials"]["client_secret"],
        username=bot_config["reddit_credentials"]["username"],
        password=bot_config["reddit_credentials"]["password"],
        user_agent=bot_config["reddit_credentials"]["user_agent"],
    )

    try:
        yield reddit
    finally:
        await reddit.close()


def next_midnight_timestamp() -> float:
    """Get the timestamp of the next midnight.

    :returns: Timestamp of the next midnight.

    """
    now = datetime.now()
    midnight: datetime = now.replace(hour=0, minute=0, second=0, microsecond=0)
    next_midnight: datetime = midnight + timedelta(days=1)
    return next_midnight.timestamp()


def create_logger(logger_name: str, set_format: bool = False) -> Logger:
    """Create logger and return an instance of logging object.

    :returns: Logging Object.

    """
    if set_format:
        log_format = "%(log_color)s[%(asctime)s] %(levelname)s [%(filename)s.%(funcName)s:%(lineno)d] %(message)s"
        root_logger = getLogger("root")
        for handler in root_logger.handlers:
            handler.setFormatter(ColoredFormatter(log_format, datefmt="%Y-%m-%dT%H:%M:%S%z"))

    return getLogger(logger_name)

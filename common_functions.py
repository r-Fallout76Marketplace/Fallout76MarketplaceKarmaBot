import json
import re

import praw
import requests
import yaml
from praw import Reddit


def flair_checks(comment_or_submission) -> bool:
    """
    Checks if submission is eligible for trading by checking the flair.

    The karma can only be exchanged under the submission with flair XBOX, PlayStation, or PC.
    :param comment_or_submission: praw object (Submission or Comment).
    """
    regex = re.compile('^XBOX|PlayStation|PC$', re.IGNORECASE)
    # Check if the object is of submission type otherwise get the submission from comment object
    if isinstance(comment_or_submission, praw.models.reddit.submission.Submission):
        submission = comment_or_submission
    else:
        submission = comment_or_submission.submission
    submission_flair_text = '' if submission.link_flair_text is None else submission.link_flair_text
    match = re.match(regex, submission_flair_text)
    # If No match found match is None
    if match is None:
        return False
    else:
        return True


def send_message_to_discord(channel_name, msg):
    """
    Sends the message to discord channel via webhook url.

    :param msg: message content.
    :param channel_name: Name of the channel to send the message to.
    """

    bot_config = get_bot_config()
    webhook = bot_config['discord_webhooks'][channel_name]
    data = {"content": msg, "username": "Karma Bot"}
    output = requests.post(webhook, data=json.dumps(data), headers={"Content-Type": "application/json"})
    output.raise_for_status()


def get_bot_config() -> dict:
    """
    Reads the bot config from yaml config file and returns the values.
    :return: bot config in a dict
    """
    with open('config.yaml') as stream:
        bot_config = yaml.safe_load(stream)

    return bot_config


def get_reddit_instance() -> Reddit:
    """
    Logs into Reddit and returns a Reddit instance.

    :return: Praw reddit instance
    """
    bot_config = get_bot_config()
    # Logging into Reddit
    reddit = praw.Reddit(client_id=bot_config['reddit_credentials']['client_id'],
                         client_secret=bot_config['reddit_credentials']['client_secret'],
                         username=bot_config['reddit_credentials']['username'],
                         password=bot_config['reddit_credentials']['password'],
                         user_agent=bot_config['reddit_credentials']['user_agent'])
    return reddit


def get_subreddit_instance(subreddit_name: str) -> praw.models.reddit.subreddit.Subreddit:
    """
    Returns the praw subreddit instance

    :param subreddit_name: name of the subreddit.
    :return: Praw subreddit instance
    """
    return get_reddit_instance().subreddit(subreddit_name)

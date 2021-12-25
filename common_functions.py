import json
import re

import praw
import requests


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
    submission_flair_text = submission.link_flair_text
    match = re.match(regex, submission_flair_text)
    # If No match found match is None
    if match is None:
        return False
    else:
        return True


def send_message_to_discord(webhook, msg):
    """
    Sends the message to discord channel via webhook url.

    :param msg: message content.
    :param webhook: webhook url.
    """
    data = {"content": msg, "username": "Karma Bot"}
    output = requests.post(webhook, data=json.dumps(data), headers={"Content-Type": "application/json"})
    output.raise_for_status()

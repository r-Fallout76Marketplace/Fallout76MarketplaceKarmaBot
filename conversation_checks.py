import re

import praw

import CONSTANTS
import bot_responses
import flair_functions


# Checks if submission is eligible for trading
# Checks that need to be passed are
# Submission must have right flair and trade should not be closed
def flair_checks(comment_or_submission):
    regex = re.compile('XBOX|PlayStation|PC', re.IGNORECASE)
    # Check if the object is of submission type otherwise get the submission from comment object
    if isinstance(comment_or_submission, praw.models.reddit.submission.Submission):
        submission = comment_or_submission
    else:
        submission = comment_or_submission.submission
    submission_flair_text = submission.link_flair_text
    match = re.match(regex, str(submission_flair_text))
    # If No match found match is None
    if match is None:
        return False
    else:
        return True


# Performs checks if the submission can be closed
def checks_for_close_command(comment):
    # Only OP can close the trade
    if comment.author == comment.submission.author:
        # You can close trading posts only
        if flair_checks(comment):
            flair_functions.close_post_trade(comment)
            bot_responses.close_submission_comment(comment.submission)
        else:
            # If post isn't trading post
            bot_responses.close_submission_failed(comment, False)
    else:
        # If the close submission is requested by someone other than op
        bot_responses.close_submission_failed(comment, True)


def checks_for_karma_command(comment):
    # Make sure author isn't rewarding themselves
    if comment.author == comment.parent().author:
        bot_responses.cannot_reward_yourself_comment(comment)
        return CONSTANTS.CANNOT_REWARD_YOURSELF
    comment_thread = []  # Stores all comments in a array
    users_involved = set()  # Stores all the users involved
    comment_thread.append(comment)
    users_involved.add(comment.author)

    # If the karma comment is not root meaning it ha a parent comment
    if not comment.is_root:
        parent_comment = comment.parent()
        comment_thread.append(parent_comment)
        users_involved.add(parent_comment.author)

    comment_thread.append(comment.submission)
    users_involved.add(comment.submission.author)

    # Remove mods and couriers from the users involved
    for user in users_involved.copy():
        if flair_functions.is_mod_or_courier(user):
            users_involved.remove(user)

    # If comment itself or the submission has been removed/deleted
    if comment.removed or comment_thread[-1].removed or comment_thread[-1].author is None:
        bot_responses.deleted_or_removed(comment)
        return CONSTANTS.DELETED_OR_REMOVED

    # If there are more than two people involved
    if len(users_involved) > 2:
        bot_responses.more_than_two_users_involved(comment)
        return CONSTANTS.MORE_THAN_TWO_USERS

    # If the conversation is shorter than two comments
    if len(comment_thread) <= 2:
        bot_responses.conversation_not_long_enough(comment)
        return CONSTANTS.CONVERSATION_NOT_LONG_ENOUGH

    # If all checks pass
    return CONSTANTS.KARMA_CHECKS_PASSED

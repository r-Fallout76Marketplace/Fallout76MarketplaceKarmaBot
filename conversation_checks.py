import CONSTANTS
import bot_responses
import common_functions
import flair_functions


def is_removed_or_deleted(content) -> bool:
    """
    Checks if comment, parent comment or submission has been removed/deleted. If it is deleted, the author is None.
    If it is removed, the removed_by will have moderator name.

    :param content: Reddit comment or submission
    :return: True if the items is deleted or removed. Otherwise, False.
    """
    return content.author is None or content.mod_note or content.removed


def checks_for_close_command(comment):
    """
    # Performs checks if the submission can be closed.

    :param comment: The comment object praw.
    """
    # Only OP can close the trade
    if comment.author == comment.submission.author:
        # You can close trading posts only
        if common_functions.flair_checks(comment):
            flair_functions.close_post_trade(comment)
            bot_responses.close_submission_comment(comment.submission)
        else:
            # If post isn't trading post
            bot_responses.close_submission_failed(comment, False)
    else:
        # If the close submission is requested by someone other than op
        bot_responses.close_submission_failed(comment, True)


def checks_for_karma_command(comment):
    """
    Performs checks for karma command comments.

    :param comment: the command comment.
    :return: checks result.
    """
    # Make sure author isn't rewarding themselves
    if comment.author == comment.parent().author:
        bot_responses.cannot_reward_yourself_comment(comment)
        return CONSTANTS.CANNOT_REWARD_YOURSELF

    comment_thread = []  # Stores all comments in an array
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

    # If the conversation is shorter than two comments
    if len(comment_thread) <= 2:
        bot_responses.conversation_not_long_enough(comment)
        return CONSTANTS.CONVERSATION_NOT_LONG_ENOUGH

    removed_or_deleted = any([is_removed_or_deleted(content) for content in comment_thread])
    if removed_or_deleted:
        bot_responses.deleted_or_removed(comment)
        return CONSTANTS.DELETED_OR_REMOVED

    # If there are more than two people involved
    if len(users_involved) > 2:
        bot_responses.more_than_two_users_involved(comment)
        return CONSTANTS.MORE_THAN_TWO_USERS

    # If all checks pass
    return CONSTANTS.KARMA_CHECKS_PASSED

import prawcore

# Replies to comment with text=body
import CONFIG
import CONSTANTS


def reply(comment_or_submission, body):
    # Add disclaimer text
    response = body + "\n\n ^(This action was performed by a bot, please contact the mods for any questions. "
    response += "[See disclaimer](https://www.reddit.com/user/Vault-TecTradingCo/comments/lkllre" \
                "/disclaimer_for_rfallout76marketplace/)) "
    try:
        new_comment = comment_or_submission.reply(response)
        new_comment.mod.distinguish(how="yes")
        new_comment.mod.lock()
    except prawcore.exceptions.Forbidden:
        raise prawcore.exceptions.Forbidden("Could not distinguish/lock comment")


# Comment reply when karma is given successfully
def karma_rewarded_comment(comment):
    p_comment = comment.parent()
    comment_body = "Hi " + comment.author.name + "! You have successfully rewarded "
    comment_body += "u/" + p_comment.author.name + " one karma point! "
    comment_body += "Please note that karma may take sometime to update."
    reply(comment, comment_body)


# Comment reply if the user tries to give deleted comment karma
def karma_reward_failed(comment):
    comment_body = "Hi " + comment.author.name + "! The bot cannot reward karma to deleted submissions or comments. "
    comment_body += "Please reply to a submission/comment that has not been deleted."
    reply(comment, comment_body)


# Cannot award yourself
def cannot_reward_yourself_comment(comment):
    comment_body = "Hi " + comment.author.name + "! You cannot reward yourself karma. Sorry."
    reply(comment, comment_body)


# If more than two users are involved in the conversation
def more_than_two_users_involved(comment):
    comment_body = "Hi " + comment.author.name + "! There are more than two users involved in the conversation. "
    comment_body += "Please separate out your conversations so the bot can tell which user you are trading with. "
    comment_body += "If you are not sure you can look at an example of [good karma exchange](" \
                    "https://www.reddit.com/r/Fallout76Marketplace/wiki/index/trading_karma). " \
                    "You need to have consecutive 3 back to back comments involving two users only to give karma. "
    reply(comment, comment_body)


# If conversation is not long enough
def conversation_not_long_enough(comment):
    comment_body = "Hi " + comment.author.name + "! There is not enough evidence that the conversation occurred.  "
    comment_body += "Please negotiate and exchange gamertags in comments rather than in chats/messages. If you are "
    comment_body += "not sure you can look at an example of [good karma exchange](" \
                    "https://www.reddit.com/r/Fallout76Marketplace/wiki/index/trading_karma). " \
                    "This is the minimum conversation we expect from users before they can give karma."
    reply(comment, comment_body)


# If the comment itself is removed or the submission is deleted/removed
def deleted_or_removed(comment):
    comment_body = "Hi " + comment.author.name + "! It seems that either your comment has been removed by Automoderator"
    comment_body += " or most probably OP has deleted their submission or has been removed by a Moderator. We don't "
    comment_body += " allow users to trade karma on deleted/removed submissions. Thank you for your understanding. "
    reply(comment, comment_body)


# If the users is already awarded in a submission
def already_rewarded_comment(comment, permalink):
    comment_body = "Hi " + comment.author.name + "! You have already rewarded " + comment.parent().author.name
    comment_body += " in this submission [here](https://www.reddit.com/" + permalink + ")."
    reply(comment, comment_body)


# If the users is already awarded in a submission
def karma_reward_limit_reached(comment, karma_logs):
    comment_body = "Hi " + comment.author.name + "! You have reached the karma reward limit. You will not be able to "
    comment_body += "reward karma until next midnight EST. You can contact mods and they can give karma on your behalf "
    comment_body += "Thank you for your patience!"
    reply(comment, comment_body)
    title = comment.author.name + " have reached their daily awarder karma limit"
    self_text = ""
    for i in range(karma_logs):
        self_text += "[Awarded to " + karma_logs[3] + str(i) + "](https://www.reddit.com/" + karma_logs[5] + ")\n\n"
    CONFIG.legacy76.submit(title=title, selftext=self_text, flair_id=CONSTANTS.AWARDER_KARMA_LIMIT_REACHED)


# Failed to give parent comment karma
def karma_trading_posts_only(comment):
    # Replies with comment
    comment_body = "Hi " + comment.author.name + "! You can only give karma to others under a trading post i.e "
    comment_body = comment_body + "submission with PlayStation, XBOX or PC flair. Please refer to wiki page for more " \
                                  "information. "
    reply(comment, comment_body)


# Comment reply when karma is subtracted successfully
def karma_subtract_comment(comment):
    p_comment = comment.parent()
    comment_body = p_comment.author.name + " karma has been decremented by one. "
    comment_body += "Please note that karma may take sometime to update."
    reply(comment, comment_body)


# Subtract parent comment karma failed
def karma_subtract_failed(comment):
    comment_body = "Karma can only be subtracted by mods only. Please contact mods if you have been scammed."
    reply(comment, comment_body)


# Close the submission comment
def close_submission_comment(submission):
    comment_body = "The submission has been closed and comments have been locked. "
    comment_body += "Please contact mods, if you want to open the submission."
    reply(submission, comment_body)


# Submission closed failed
def close_submission_failed(comment, is_trading_post):
    if is_trading_post:
        comment_body = "The submission can only be close by OP or the mods. Please report post if it is breaking rules."
    else:
        comment_body = "This type of submission cannot be closed. Please refer to wiki page for more information."
    reply(comment, comment_body)

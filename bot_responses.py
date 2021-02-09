import prawcore


# Replies to comment with text=body
def reply(comment_or_submission, body):
    # Add disclaimer text
    response = body + "\n\n ^(This action was performed by a bot, please contact the mods for any questions. "
    response += "[See disclaimer](https://www.reddit.com/user/Vault-TecTradingCo/comments/j497xo" \
                "/disclaimer_for_uvaulttectradingco_bot/))"
    try:
        new_comment = comment_or_submission.reply(response)
        new_comment.mod.distinguish(how="yes")
        new_comment.mod.lock()
    except prawcore.exceptions.Forbidden:
        pass


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
    comment_body = "Hi " + comment.author.name + " There are more than two users involved in the conversation. "
    comment_body += "Please separate out your conversations so the bot can tell which user you are trading with. "
    reply(comment, comment_body)


# If conversation is not long enough
def conversation_not_long_enough(comment):
    comment_body = "Hi " + comment.author.name + " There is not enough evidence that the conversation occurred.  "
    comment_body += "Please negotiate and exchange gamertags in comments rather than in chats/messages. "
    reply(comment, comment_body)


# If the users is already awarded in a submission
def already_rewarded_comment(comment, permalink):
    comment_body = "Hi " + comment.author.name + "! You have already rewarded " + comment.parent().author.name
    comment_body += " in this submission [here](https://www.reddit.com/" + permalink + ")."
    reply(comment, comment_body)


# If the users is already awarded in a submission
def karma_reward_limit_reached(comment, karma_logs):
    comment_body = "Hi " + comment.author.name + "! You have reached the karma reward limit. You will not be able to "
    comment_body += "reward karma until midnight tomorrow. Here is your today's history of rewarding karma\n\n"
    for i in range(karma_logs):
        comment_body += "[Awarded to " + karma_logs[3] + str(i) + "](https://www.reddit.com/" + karma_logs[5] + ")\n\n"
    reply(comment, comment_body)


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
def close_submission_comment(submission, time_expired):
    comment_body = "The submission has been closed and comments have been locked. "
    if time_expired:
        comment_body += "**All trading submission gets locked automatically after 1 week.** "
    comment_body += "Please contact mods, if you want to open the submission."
    reply(submission, comment_body)


# Submission closed failed
def close_submission_failed(comment, is_trading_post):
    if is_trading_post:
        comment_body = "The submission can only be close by OP or the mods. Please report post if it is breaking rules."
    else:
        comment_body = "This type of submission cannot be closed. Please refer to wiki page for more information."
    reply(comment, comment_body)


# If submission flair was changed or the submission was not recorded
def submission_flair_changed(comment):
    comment_body = "The bot could not reward karma either because the submission flair was changed to trading flair "
    comment_body += "from non trading flair or the submission was posted when the bot was down. In any case, please "
    comment_body += "[contact mods](https://www.reddit.com/message/compose?to=/r/Fallout76Marketplace&subject=Could" \
                    "%20not%20reward%20karma&message=put%20submission%20link%20here) "
    reply(comment, comment_body)

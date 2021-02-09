from datetime import datetime

import CONFIG
import reddit_user


# Gets the comment author name. It if doesn't exist returns [deleted]
def get_author_name(comment):
    try:
        return comment.author.name
    except AttributeError:
        return "[deleted]"


# Gets the parent comment author name. It if doesn't exist returns [deleted]
def get_parent_author_name(comment):
    try:
        return comment.parent().author.name
    except AttributeError:
        return "[deleted]"


# class UserDatabase
# Stores the information about users karma
# Also can upload the information to a submission

class UserDatabase:

    # Constructor
    def __init__(self):
        self.users_dict = {}

    def log_karma_command(self, comment):
        # saving the info about the user who gave karma
        # Gets the user from hashtable
        reddit_user_obj = self.users_dict.get(get_author_name(comment))
        # If get method returns None, creates a new object and puts it in hashtable
        if reddit_user_obj is None:
            reddit_user_obj = reddit_user.RedditUser(comment.author)
            self.users_dict.update({get_author_name(comment): reddit_user_obj})
        reddit_user_obj.increment_awarder_karma()  # Increment how much this user has awarded karma
        # save info about who the user gave karma to
        reddit_user_obj.update_awarder_karma_logs(get_parent_author_name(comment))
        reddit_user_obj.set_current_karma_level(comment)

        # saving the info about the user who received karma
        reddit_user_obj = self.users_dict.get(get_parent_author_name(comment))
        # If get method returns None, creates a new object and puts it in hashtable
        if reddit_user_obj is None:
            reddit_user_obj = reddit_user.RedditUser(comment.parent().author)
            self.users_dict.update({get_parent_author_name(comment): reddit_user_obj})
        reddit_user_obj.increment_awardee_karma()  # Increment how much this user has received karma
        # save info about who the user received karma from
        reddit_user_obj.update_awardee_karma_logs(get_author_name(comment))
        # updates the karma value
        reddit_user_obj.set_current_karma_level(comment.parent())

    def karma_limits_reached(self, username):
        reddit_user_obj = self.users_dict.get(username)
        if reddit_user_obj is None:
            return False
        else:
            return reddit_user_obj.karma_reward_limit_reached()

    def archive_data(self):
        self_text = ""
        for key, value in self.users_dict.items():
            self_text += str(value)
            self_text += "***\n\n"
        today = datetime.today().strftime('%Y/%m/%d') + " karma logs"
        CONFIG.legacy76.submit(title=today, selftext=self_text)

    # Deletes all the data
    def erase_data(self):
        self.users_dict = {}

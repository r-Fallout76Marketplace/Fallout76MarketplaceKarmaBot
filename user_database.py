from datetime import datetime

import CONFIG
import CONSTANTS
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

    def awarder_karma_limit_reached(self, username):
        reddit_user_obj = self.users_dict.get(username)
        if reddit_user_obj is None:
            return False
        else:
            if reddit_user_obj.current_karma_level < 50 and reddit_user_obj.awarder_karma >= 10:
                return True
            elif reddit_user_obj.current_karma_level < 100 and reddit_user_obj.awarder_karma >= 15:
                return True
            elif reddit_user_obj.current_karma_level >= 100 and reddit_user_obj.awarder_karma >= 50:
                return True
            else:
                return False

    def archive_data(self):
        self_text = ""
        total_awarder_karma = 0
        total_awardee_karma = 0
        # sort the users by how much karma they gave
        sorted_list = sorted(self.users_dict.items(), key=lambda obj: obj[1].awarder_karma, reverse=True)
        for item in sorted_list:
            self_text += str(item[1])
            total_awarder_karma += item[1].awarder_karma
            total_awardee_karma += item[1].awadeee_karma
            self_text += "***\n\n"
        self_text = "Today {} users gave and received karma. A total of {} karma was given and {} karma was " \
                    "received\n***\n\n".format(len(sorted_list), total_awarder_karma, total_awardee_karma) + self_text
        today = datetime.today().strftime('%Y/%m/%d') + " karma logs"
        CONFIG.legacy76.submit(title=today, selftext=self_text, flair_id=CONSTANTS.DAILY_KARMA_LOGS)

    # Deletes all the data
    def erase_data(self):
        self.users_dict = {}

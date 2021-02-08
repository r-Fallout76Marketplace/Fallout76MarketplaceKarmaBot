import CONFIG


# Class RedditUser
# Stores the information about the user, how much karma is awarded and received by whom

class RedditUser:
    def __init__(self, redditor):
        # The input can be either username or redditor instance
        if isinstance(redditor, str):
            self.redditor = CONFIG.reddit_1.redditor(redditor)
        else:
            self.redditor = redditor
        try:
            self.user_name = self.redditor.name
        except AttributeError:
            self.user_name = "[deleted]"
        self.current_karma_level = 0
        self.awarder_karma = 0
        self.awarder_karma_logs = {}
        self.awardee_karma = 0
        self.awardee_karma_logs = {}

    # increments the karma given
    def increment_awarder_karma(self):
        self.awarder_karma = self.awarder_karma + 1

    # Stores the information about who this user awarded the karma
    def update_awarder_karma_logs(self, user_name):
        if user_name in self.awarder_karma_logs:
            karma_value = self.awarder_karma_logs.get(user_name)
            karma_value = karma_value + 1
            self.awarder_karma_logs.update({user_name: karma_value})
        else:
            self.awarder_karma_logs.update({user_name: 1})

    # increments the karma received
    def increment_awardee_karma(self):
        self.awardee_karma = self.awardee_karma + 1

    # Stores the information about who this user got karma from
    def update_awardee_karma_logs(self, user_name):
        if user_name in self.awardee_karma_logs:
            karma_value = self.awardee_karma_logs.get(user_name)
            karma_value = karma_value + 1
            self.awardee_karma_logs.update({user_name: karma_value})
        else:
            self.awardee_karma_logs.update({user_name: 1})

    # updates the current karma level
    def set_current_karma_level(self, comment_or_submission):
        user_flair = comment_or_submission.author_flair_text
        user_flair_split = None
        try:
            user_flair_split = user_flair.split()
            self.current_karma_level = int(user_flair_split[-1])
        except ValueError:
            self.current_karma_level = user_flair_split[-1]
        except AttributeError:
            self.current_karma_level = comment_or_submission.author_flair_text

    # Returns true if user has reached the karma reward limit
    def karma_reward_limit_reached(self):
        if self.current_karma_level < 50 and self.awardee_karma >= 10:
            return True
        elif self.current_karma_level < 100 and self.awardee_karma >= 15:
            return True
        else:
            return False

    # Overrides the str method
    def __str__(self):
        string = "## u/" + self.user_name + " - Current Karma: " + str(self.current_karma_level) + "\n\n"
        string += "**Awarder Karma Total: " + str(self.awarder_karma) + "**\n"
        for key, value in self.awarder_karma_logs.items():
            string += "* u/" + key + ": " + str(value) + "\n"
        string += "\n**Awardee Karma Total: " + str(self.awardee_karma) + "**\n"
        for key, value in self.awardee_karma_logs.items():
            string += "* u/" + key + ": " + str(value) + "\n"
        return string

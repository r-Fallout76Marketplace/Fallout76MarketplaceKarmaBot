import json

import requests

import CONFIG


# Send message to discord channel
def send_message_to_discord(message_param):
    data = {"content": message_param, "username": CONFIG.bot_name}
    output = requests.post(CONFIG.mod_channel, data=json.dumps(data), headers={"Content-Type": "application/json"})
    output.raise_for_status()


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
        self.awarder_limit_alert_sent = 0
        self.awardee_limit_alert_sent = 0

    # increments the karma given
    def increment_awarder_karma(self):
        self.awarder_karma = self.awarder_karma + 1
        if self.awarder_karma > 20 and self.awarder_limit_alert_sent != 1:
            try:
                send_message_to_discord(self.user_name + " has given 20+ karma today")
                self.awarder_limit_alert_sent = 1
            except requests.exceptions.HTTPError:
                pass

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
        if self.awardee_karma > 20 and self.awardee_limit_alert_sent != 1:
            try:
                send_message_to_discord(self.user_name + " has received 20+ karma today")
                self.awardee_limit_alert_sent = 1
            except requests.exceptions.HTTPError:
                pass

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
            self.current_karma_level = 0

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

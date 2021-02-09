# Fallout 76 Marketplace Karma Bot

This is a reddit bot for [r/Fallout76Marketplace](https://www.reddit.com/r/Fallout76Marketplace/). The bot implements
the subreddit own karma system to keep track of how many time a user has traded successfully.

### Features:

- Flair color changes based on karma level
- Locks and closes submissions after 1 week
- Users can give limited amount of karma determined by their karma level
- Submits daily karma logs to a subreddit in the form of submission
- uses multithreading and multiple praw instances to reduce the dropped requests
- and many security and bug fixes
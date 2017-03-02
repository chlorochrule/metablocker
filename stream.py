#-*- coding: utf-8 -*-
import os
import tweepy
import re
import json
import app

consumer_key = os.environ['consumer_key']
consumer_secret = os.environ['consumer_secret']

def get_words(user_id):
    conn = app.get_connector()
    cur = conn.cursor()
    cur.execute('select keywords from users where user_id=%s', (user_id, ))
    words = cur.fetchone()[0]
    cur.close()
    conn.close()
    return words

def change_words(user_id, words):
    conn = app.get_connector()
    cur = conn.cursor()
    cur.execute('update users set keywords=%s where user_id=%s', (words, user_id))
    conn.commit()
    cur.close()
    conn.close()

def add_words(user_id, new_words):
    words = get_words(user_id)
    if words is None:
        return
    new_words = [new_word for new_word in new_words if new_word not in words]
    words += new_words
    change_words(user_id, words)

def remove_words(user_id, removed_words):
    words = get_words(user_id)
    if words is None:
        return
    words = [word for word in words if word not in removed_words]
    change_words(user_id, words)

def parse_to_words(text):
    words = text[3:].split(',')
    if words is None:
        return
    words = [word.strip() for word in words]
    return words

if __name__ == '__main__':
    conn = app.get_connector()
    cur = conn.cursor()
    cur.execute('select access_token_key, access_token_secret from users where user_id=\'metablockerbot\'')
    access_token_key, access_token_secret = cur.fetchone()
    cur.close()
    conn.close()
    bot_api = app.get_auth_api(access_token_key, access_token_secret)

    class Listener(tweepy.StreamListener):
        """docstring for Listener."""
        def __init__(self, *args, **kwargs):
            super(Listener, self).__init__(self, *args, **kwargs)

        def on_data(self, status):
            status = json.loads(status)
            try:
                if 'direct_message' in status.keys():
                    text = status['direct_message']['text']
                    user_id = status['direct_message']['sender']['screen_name']
                    conn = app.get_connector()
                    cur = conn.cursor()
                    cur.execute('select user_id from users')
                    users = [uid[0] for uid in cur.fetchall()]
                    cur.close()
                    conn.close()
                    if user_id not in users or user_id == 'metablockerbot':
                        return True
                    if re.match('bl:', text):
                        new_words = parse_to_words(text)
                        add_words(user_id, new_words)
                    elif re.match('rm:', text):
                        removed_words = parse_to_words(text)
                        remove_words(user_id, removed_words)
            except tweepy.error.TweepError as e:
                print 'catch: tweepy.error.TweepError'
            return True

        def on_error(self, status_code):
            print 'Got an error with status code: ' + str(status_code)
            return True

        def on_timeout(self):
            print 'Timeout...'
            return True

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token_key, access_token_secret)
    listener = Listener()
    stream = tweepy.Stream(auth, listener)
    stream.userstream()

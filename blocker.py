#-*- coding: utf-8 -*-
import os
import tweepy
import psycopg2 as psql
import app
import re

from datetime import datetime

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

def remove_user(user_id):
    conn = app.get_connector()
    cur = conn.cursor()
    cur.execute('delete from users where user_id=%s', (user_id, ))
    conn.commit()
    cur.close()
    conn.close()

def main():
    conn = app.get_connector()
    cur = conn.cursor()
    cur.execute('select * from users')
    rows = cur.fetchall()
    users = [row[0] for row in rows if row[0] != 'metablockerbot']
    for row in rows:
        access_token_key, access_token_secret, words = row[1:4]
        api = app.get_auth_api(access_token_key, access_token_secret)
        if row[0] == 'metablockerbot':
            since_id = row[4]
            dms = api.direct_messages(since_id=since_id)
            for dm in dms:
                user_id = dm.sender_screen_name
                text = dm.text
                if user_id in users:
                    if re.match('bl:', text):
                        new_words = parse_to_words(text)
                        add_words(user_id, new_words)
                    elif re.match('rm:', text):
                        removed_words = parse_to_words(text)
                        remove_words(user_id, removed_words)
            since_id = max(dm.id for dm in dms)
            conn2 = app.get_connector()
            cur2 = conn2.cursor()
            cur2.execute('update users set dm_since_id=%s where user_id=%s', (since_id, 'metablockerbot'))
            conn2.commit()
            cur2.close()
            conn2.close()
        for word in words:
            try:
                for tweet in api.search(q=word, count=100):
                    block_user_id = tweet.user.screen_name
                    friendship = api.lookup_friendships(screen_names=[block_user_id])[0]
                    if not friendship.is_following and not friendship.is_followed_by:
                        api.create_block(screen_name=block_user_id)
            except tweepy.error.TweepError as e:
                if isinstance(e.message, list) and \
                        isinstance(e.message[0], dict) and \
                        'Invalid or expired token.' == e.message[0].get('message', ''):
                    remove_user(row[0])
                break
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()

#-*- coding: utf-8 -*-
import os
import tweepy
import psycopg2 as psql
import app

from datetime import datetime

consumer_key = os.environ['consumer_key']
consumer_secret = os.environ['consumer_secret']

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
    for row in rows:
        if row[0] == 'metablockerbot':
            continue
        access_token_key, access_token_secret, words = row[1:]
        api = app.get_auth_api(access_token_key, access_token_secret)
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

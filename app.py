#-*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

import os
import tweepy
import oauth2 as oauth
from bottle import get, request, redirect, run
import psycopg2 as psql

request_token_url = 'https://twitter.com/oauth/request_token'
access_token_url = 'https://twitter.com/oauth/access_token'
authenticate_url = 'https://twitter.com/oauth/authenticate'

consumer_key = os.environ['consumer_key']
consumer_secret = os.environ['consumer_secret']

def get_connector():
    conn = psql.connect(
        host=os.environ['dbhost'],
        database=os.environ['dbname'],
        user=os.environ['dbuser'],
        password=os.environ['dbpasswd']
    )
    return conn

def get_oauth():
    consumer = oauth.Consumer(key=consumer_key, secret=consumer_secret)
    client = oauth.Client(consumer)
    resp, content = client.request(request_token_url, 'GET')
    request_token = parse_qsl(content)
    oauth_token = request_token['oauth_token']
    oauth_token_secret = request_token['oauth_token_secret']
    url = '{}?oauth_token={}'.format(authenticate_url, oauth_token)
    os.environ['oauth_token_tmp'] = oauth_token
    os.environ['oauth_token_secret_tmp'] = oauth_token_secret
    return url, oauth_token, oauth_token_secret

@get('/auth')
def authenticate():
    url = get_oauth()[0]
    redirect(url)

@get('/callback')
def callback():
    oauth_token = os.environ['oauth_token_tmp']
    os.unsetenv('oauth_token_tmp')
    oauth_token_secret = os.environ['oauth_token_secret_tmp']
    os.unsetenv('oauth_token_secret_tmp')
    oauth_verifier = request.query['oauth_verifier']
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.request_token = {
        'oauth_token': oauth_token,
        'oauth_token_secret': oauth_token_secret,
        'oauth_callback_confirmed': True,
    }
    access_token_key, access_token_secret = auth.get_access_token(oauth_verifier)
    api = get_auth_api(access_token_key, access_token_secret)
    user_id = api.me().screen_name
    conn = get_connector()
    cur = conn.cursor()
    cur.execute('select user_id from users')
    res = cur.fetchall()
    users = [user[0] for user in res]
    if user_id in users:
        cur.execute(
            'update users set access_token_key=%s, access_token_secret=%s where user_id=%s',
            (access_token_key, access_token_secret, user_id)
        )
    else:
        cur.execute(
            'insert into users values(%s, %s, %s, %s)',
            (user_id, access_token_key, access_token_secret, [])
        )
    conn.commit()
    cur.execute('select keywords from users where user_id=%s', (user_id, ))
    words = cur.fetchone()[0]
    text = 'Blocking words:'
    for word in words:
        text += ' ' + word + ','
    text = text[:-1]
    cur.close()
    conn.close()
    return text

def get_auth_api(access_token_key, access_token_secret):
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token_key, access_token_secret)
    api = tweepy.API(auth_handler=auth, api_root='/1.1')
    return api

def parse_qsl(content):
    param = {}
    for i in content.split('&'):
        _p = i.split('=')
        param[_p[0]] = _p[1]
    return param

if __name__ == '__main__':
    run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

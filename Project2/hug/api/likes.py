# Users should be able to:
# like posts
# see how many likes a post has received
# retrieve a list of the posts that another user liked
# see a list of popular posts that were liked by many users

import configparser
import logging.config
import requests
import socket
import os

#import hiredis
import hug
import redis
import sqlite_utils

config = configparser.ConfigParser()
config.read("./etc/timelines.ini")
logging.config.fileConfig(config["logging"]["config"], disable_existing_loggers=False)

#reader = hiredis.Reader()
red = redis.Redis(host='localhost', port=6379, db=0)
red.flushall() # Deletes db when ran

@hug.directive()
def sqlite(section="sqlite", key="dbfile", **kwargs):
    dbfile = config[section][key]
    return sqlite_utils.Database(dbfile)

# Adds all id to redis db and sets each like count to 0
@hug.local()
def fill(db:sqlite):
    for row in db["posts"].rows:
        username = row["username"]
        post_id = row["post_id"]
        url = "/likes/" + username + "/" + str(post_id)
        red.zadd("post_list", {url:0})
fill()

# Like a post
# http POST localhost:8000/likes/brandon2306/bob123/3
@hug.post("/likes/{liker_username}/{username}/{post_id}")
def like(response, liker_username: hug.types.text, username: hug.types.text, post_id: hug.types.text): 
    url = "/likes/" + username + "/" + post_id
    try:
        red.zincrby("post_list", 1, url)
        red.sadd(liker_username, url)
        red.zincrby("popular_list", 1, url)
    except:
        response.status = hug.falcon.HTTP_404
    return {"liker_username": liker_username, "url": url}

# See how many likes a post has received
# http GET localhost:8000/likes/count/bob123/3
@hug.get("/likes/count/{username}/{post_id}")
def like_counts(username: hug.types.text, post_id: hug.types.text):
    url = "/likes/" + username + "/" + post_id
    output = red.zscore("post_list", url)
    return {"url": url, "total likes": output}

# Retrieve a list of the posts that another user liked
# http GET localhost:8000/likes/brandon2306
@hug.get("/likes/{liker_username}") 
def user_liked(liker_username: hug.types.text):
    output = red.smembers(liker_username)
    return {"User Likes": output}

# See a list of popular posts that were liked by many users
# http GET localhost:8000/likes/popular
@hug.get("/likes/popular")
def popular_post():
    output = red.zrevrange("popular_list", 0, -1, withscores=True)
    return {"Popular Posts": output}

@hug.get("/likes/health")
def checkHealth(response):
    try:
        return red.ping()
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"error": str(e)}

@hug.startup()
def selfRegister(api):
    registerURL = "http://localhost:8000/registry/likes"
    url = "http://" + socket.gethostbyname(socket.gethostname()) + ":" + os.environ["PORT"] + "/likes"
    r = requests.post(registerURL, data={"text": url})

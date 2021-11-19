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
redis = redis.Redis(host='localhost', port=6379, db=0)
redis.flushall() # Deletes db when ran

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
        redis.zadd("post_list", {url:0})
fill()

# Like a post
@hug.post("/likes/{liker_username}/{username}/{post_id}")
def like(response, liker_username: hug.types.text, username: hug.types.text, post_id: hug.types.text): 
    url = "/likes/" + username + "/" + post_id
    try:
        redis.zincrby("post_list", 1, url)
        redis.zincrby(liker_username, 1, url)
        redis.zincrby("popular_list", 1, url)
    except:
        response.status = hug.falcon.HTTP_404
    return {"Liked": {"url": url}}

# See how many likes a post has received
@hug.get("/likes/count/{username}/{post_id}")
def like_counts(username: hug.types.text, post_id: hug.types.text):
    url = "/likes/" + username + "/" + post_id
    output = redis.zscore("post_list", url)
    return {"Number of Likes": output}

# Retrieve a list of the posts that another user liked
@hug.get("/likes/{liker_username}") 
def user_liked(liker_username: hug.types.text):
    output = redis.zrevrange(liker_username, 0, -1)
    return {"User Likes": output}

# See a list of popular posts that were liked by many users
@hug.get("/likes/popular")
def popular_post():
    output = redis.zrevrange("popular_list", 0, -1)
    return {"Popular Posts": output}

@hug.get("/likes/health")
def checkHealth(response, db: sqlite):
    try:
        return r.ping()
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"error": str(e)}

# @hug.startup()
# def selfRegister(api):
#     registerURL = "http://localhost:8000/registry/likes"
#     url = "http://" + socket.gethostbyname(socket.gethostname()) + ":" + os.environ["PORT"] + "/likes"
#     r = requests.post(registerURL, data={"text": url})

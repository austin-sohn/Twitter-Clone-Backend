# Users should be able to:
# - like posts
# - see how many likes a post has received
# - retrieve a list of the posts that another user liked
# - see a list of popular posts that were liked by many users

import configparser
import logging.config

import hug
import json
import redis
import sqlite_utils
import timelines

config = configparser.ConfigParser()
config.read("./etc/timelines.ini")
logging.config.fileConfig(config["logging"]["config"], disable_existing_loggers=False)

redis = redis.Redis(host='localhost', port=6379, db=0)
redis.flushall() # deletes db when ran
post = "post"

@hug.directive()
def sqlite(section="sqlite", key="dbfile", **kwargs):
    dbfile = config[section][key]
    return sqlite_utils.Database(dbfile)
    
# Adds all id to redis db and sets each like count to 0.
@hug.local()
def fill():
    db = sqlite()
    for row in db["posts"].rows:
        id =  row["id"]
        redis.zadd(post,{id:0})
fill()

# Like a post.
@hug.post("/timelines/{username}/{post_id}/like")
def like(response, db:sqlite, username: hug.types.text, post_id: hug.types.number): 
    try:
        id = timelines.getUserID(db, username)
        print(id)
        redis.zincrby(post, 1, id)
    except:
        response.status = hug.falcon.HTTP_404
    return {"liked": {"id": id, "username": username, "post_id": post_id}}

# See how many likes a post has received.
@hug.get("/timelines/lcount/{id}")
def like_counts(id: hug.types.number):
    output = redis.zscore(post, id)
    print(output)
    return {"NumLikes":output}

# Retrieve a list of the posts that another user has liked.
#@hug.get()
#def get_specific_likes()

# See a list of popular posts that were liked by many users.
@hug.get("/timelines/popular")
def popular_post():
    output = redis.zrange(post,0,-1, withscores=True)
    return {"popular":output}
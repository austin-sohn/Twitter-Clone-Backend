# Users should be able to like posts
# see how many likes a post has received
# retrieve a list of the posts that another user liked
# see a list of popular posts that were liked by many users.

import configparser
#import hiredis
import hug
import logging.config
import redis
import sqlite_utils

config = configparser.ConfigParser()
config.read("./etc/timelines.ini")
logging.config.fileConfig(config["logging"]["config"], disable_existing_loggers=False)

#reader = hiredis.Reader()
port = 6379
redisClient = redis.Redis(host='localhost', port=port, db=0)
redisClient.flushall() # deletes db when ran
post = "post"

@hug.directive()
def sqlite(section="sqlite", key="dbfile", **kwargs):
    dbfile = config[section][key]
    return sqlite_utils.Database(dbfile)


# adds all id to redis db and sets each like count to 0
@hug.local()
def fill(db:sqlite):
    for row in db["posts"].rows:
        username = row["username"]
        post_id = row["post_id"]
        url = "/likes/"+username+"/"+str(post_id)
        redisClient.zadd(post,{url:0})
fill()

# like a post
@hug.post("/likes/{username}/{post_id}")
def like(response, username: hug.types.text, post_id: hug.types.text): 
    url = "/likes/"+username+"/"+post_id
    try:
        redisClient.zincrby(post, 1, url)
    except:
        response.status = hug.falcon.HTTP_404
    return {"Liked": {"url": url}}

# see amount of likes on a post
@hug.get("/likes/count/{username}/{post_id}")
def like_counts(username: hug.types.text, post_id: hug.types.text):
    url = "/likes/"+username+"/"+post_id
    output = redisClient.zscore(post,url)
    return {"Number of Likes":output}

# see posts a user liked
# TODO
@hug.get("/likes/{username}/") 
def user_liked(username: hug.types.text):


    output = 'idk'

    return {username: output}

# see list of popular a post
@hug.get("/likes/popular")
def popular_post():
    output = redisClient.zrevrange(post,0,-1, withscores=True)
    return {"popular":output}
"""
@hug.get("/timelines/health")
def checkHealth(response, db: sqlite):
    try:
        posts = {"posts": db["posts"].rows_where()}
        return posts
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"error": str(e)}
  
@hug.startup()
def selfRegister(api):
    registerURL = "http://localhost:8000/registry/posts"
    url = "http://" + socket.gethostbyname(socket.gethostname()) + ":" + os.environ["PORT"] + "/timelines" 
    r = requests.post(registerURL, data={"text": url})
"""
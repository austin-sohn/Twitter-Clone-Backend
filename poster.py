from datetime import datetime

import greenstalk
import sqlite_utils
import configparser
import json

config = configparser.ConfigParser()
config.read("./etc/timelines.ini")
client = greenstalk.Client(('127.0.0.1', 11300),watch="posts")

def getUserID(db, username):
        id_user_generator= db["posts"].rows_where("username = :username", {"username": username}, select='user_id')
        id_user_dict = next(id_user_generator)
        id_user = id_user_dict["user_id"]
        return id_user

def post_loop():
    client.use("posts")
    while True:
        try:

            job = client.reserve()
            post = json.loads(job.body)
            dbfile = config["sqlite"]["dbfile"]
            db = sqlite_utils.Database(dbfile)
            id_user = getUserID(db, post["username"])
            posts = db["posts"]
            post["user_id"] = id_user

            # set timestamp
            now = datetime.now()
            date_time = now.strftime("%Y/%m/%d %H:%M:%S")
            post["timestamp"] = date_time

            id_post_dict = next(posts.rows_where(select='max(post_id)+1'))

            # increments post_id before adding to database
            if id_post_dict["max(post_id)+1"] is None:
                post["post_id"] = 1
            else:
                post["post_id"] = id_post_dict["max(post_id)+1"]

            posts.insert(post) # insert to table
            post["id"] = posts.last_pk
            client.delete(job)

        except:
            None


if __name__ == "__main__":
    post_loop()

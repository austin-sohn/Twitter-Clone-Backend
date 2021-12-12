import redis
import sqlite_utils
import configparser
import greenstalk
import json

red = redis.Redis(host='localhost', port=6379, db=0)
msq_queue = greenstalk.Client(('127.0.0.1', 11300),watch="likes")

config = configparser.ConfigParser()
config.read("./etc/timelines.ini")

def undo_like(liker_username, username, post_id):
    url = "/likes/" + username + "/" + post_id
    try:
        print("undoing")
        red.zincrby("post_list", -1, url) # increment post_list by -1
        red.srem(liker_username, url)
        red.zincrby("popular_list", -1, url)

        if red.zscore("popular_list", url) <= 0 :
            red.zrem("popular_list", url)

        if red.zscore("post_list",url) <= 0 :
            red.zrem("post_list", url)

    except:
        None

    return

# def email_liker(username):


def getUserID(db, username):
        id_user_generator= db["posts"].rows_where("username = :username", {"username": username}, select='user_id')
        id_user_dict = next(id_user_generator)
        id_user = id_user_dict["user_id"]
        return id_user

def validate_loop():
    dbfile = config["sqlite"]["dbfile"]
    db = sqlite_utils.Database(dbfile)
    msq_queue.use("likes")
    while True:
        job = msq_queue.reserve()
        data = json.loads(job.body)
        try:
            id_user = getUserID(db, data["username"])
            posts = []
            # finds user's specific post
            for row in db["posts"].rows_where("user_id = :id_user AND post_id = :post_id", {"id_user": id_user, "post_id": data["post_id"]}, order_by="timestamp desc", select='username, text, timestamp, url'):
                posts.append(row)

            if len(posts) == 0:
                undo_like(data["liker_username"], data["username"], data["post_id"])
        except:
            None

        msq_queue.delete(job)

if __name__ == "__main__":
    validate_loop()

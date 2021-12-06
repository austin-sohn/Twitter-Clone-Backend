import redis
import sqlite_utils
import configparser
import greenstalk

red = redis.Redis(host='localhost', port=6379, db=0)
msq_queue = greenstalk.Client(('127.0.0.1', 11300),watch="likes")

config = configparser.ConfigParser()
config.read("./etc/timelines.ini")

def undo_like(username, post_id):
    url = "/likes/" + username + "/" + post_id
    try:
        red.zincrby("post_list", -1, url) # increment post_list by 1
        red.srem(liker_username, url)
        red.zincrby("popular_list", -1, url)
    except:
        None
    return

# def email_liker(username):

def validate_loop():
    dbfile = config["sqlite"]["dbfile"]
    db = sqlite_utils.Database(dbfile)
    msq_queue.use("likes")
    while True:
        job = msq_queue.reserve()
        data = json.loads(job.body)
        try:
            id_user = getUserID(db, data["username"])

            # finds user's specific post
            for row in db["posts"].rows_where("user_id = :id_user AND post_id = :post_id", {"id_user": id_user, "post_id": data["post_id"]}, order_by="timestamp desc", select='username, text, timestamp, url'):
                posts.append(row)

            if len(posts) == 0:
                undo_like(data["username"], data["post_id"])

        except:
            None

        client.delete(job)

if __name__ == "__main__":
    validate_loop()

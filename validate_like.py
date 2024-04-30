import redis
import sqlite_utils
import configparser
import greenstalk
import json
import smtplib

red = redis.Redis(host='localhost', port=6379, db=0)
msq_queue = greenstalk.Client(('127.0.0.1', 11300),watch="likes")

config = configparser.ConfigParser()
config.read("./etc/timelines.ini")
config2 = configparser.ConfigParser()
config2.read("./etc/users.ini")

def undo_like(liker_username, username, post_id):
    url = "/likes/" + username + "/" + post_id
    try:
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

def getUserID(db, username):
        id_user_generator= db["posts"].rows_where("username = :username", {"username": username}, select='user_id')
        id_user_dict = next(id_user_generator)
        id_user = id_user_dict["user_id"]
        return id_user
        
def getUserEmail(db, username):
        email_user_generator= db["users"].rows_where("username = :username", {"username": username}, select='email_address')
        email_user_dict = next(email_user_generator)
        email_user = email_user_dict["email_address"]
        return email_user
    
def validate_loop():
    dbfile = config["sqlite"]["dbfile"]
    db = sqlite_utils.Database(dbfile)
    dbfile2 = config2["sqlite"]["dbfile"]
    db2 = sqlite_utils.Database(dbfile2)
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
                msg = "Cannot like post"
                # python3 -m smtpd -n -c DebuggingServer localhost:1025
                fromaddr = "test@gmail.com"
                toaddrs = getUserEmail(db2, data["username"])
                server = smtplib.SMTP('localhost', 1025)
                server.set_debuglevel(1)
                server.sendmail(fromaddr, toaddrs, msg)
                server.quit()
        except:
            None

        msq_queue.delete(job)

if __name__ == "__main__":
    validate_loop()

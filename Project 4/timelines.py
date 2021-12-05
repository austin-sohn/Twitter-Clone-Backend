from datetime import datetime

import configparser
import logging.config
import requests
import socket
import os
import json
import hug
import sqlite_utils
import greenstalk

config = configparser.ConfigParser()
config.read("./etc/timelines.ini")
logging.config.fileConfig(config["logging"]["config"], disable_existing_loggers=False)
msq_queue = greenstalk.Client(('127.0.0.1', 11300))

@hug.directive()
def sqlite(section="sqlite", key="dbfile", **kwargs):
    dbfile = config[section][key]
    return sqlite_utils.Database(dbfile)

@hug.directive()
def log(name=__name__, **kwargs):
    return logging.getLogger(name)

@hug.cli()
def custom_verify(username,password):
    # test it out with this: http -a brandon2306:chonker123 localhost:8000/timelines/bob123/post text="hello this working?"
    r = requests.get('http://localhost:8000/users/login/' + username)
    if r.status_code != 200:
        return False
    rjson = r.json()
    for word in rjson["password"]:
        if word == password:
            return {"username": username, "password": password}

    return False

# I was not able to make the authentication separate for very user unfortunately
# The authentication is through one user account and it has full access to all users' home and post privileges
u = "student"
p = "password"
global auth
auth = hug.authentication.basic(custom_verify)

# getUserID function returns user_id given username
@hug.local()
def getUserID(db: sqlite, username: hug.types.text):
        id_user_generator= db["posts"].rows_where("username = :username", {"username": username}, select='user_id')
        id_user_dict = next(id_user_generator)
        id_user = id_user_dict["user_id"]
        return id_user

# suppose to set password and username but auth does not change
@hug.local()
def setLogin(username: hug.types.text):
    r = requests.get(f"""http://127.0.0.1:8000/users/login/{username}""")
    r_json = r.json()
    password = r_json["password"]
    auth = hug.authentication.basic(hug.authentication.verify(username,password))


# returns all posts from specific user
@hug.get("/timelines/{username}")
def timeline(response, db: sqlite, username: hug.types.text):
    posts = []
    try:
        id_user = getUserID(db, username)

        # finds all user's existing posts
        for row in db["posts"].rows_where("user_id = :id_user", {"id_user": id_user}, order_by="timestamp desc", select='username, text, timestamp, url'):
            posts.append(row)

    except sqlite_utils.db.NotFoundError:
        response.status = hug.falcon.HTTP_404
    return {"posts": posts}

# returns specific post from specific user
@hug.get("/timelines/{username}/{post_id}")
def post(response, db: sqlite, username: hug.types.text, post_id: hug.types.number):
    posts = []
    try:
        id_user = getUserID(db, username)

        # finds user's specific post
        for row in db["posts"].rows_where("user_id = :id_user AND post_id = :post_id", {"id_user": id_user, "post_id": post_id}, order_by="timestamp desc", select='username, text, timestamp, url'):
            posts.append(row)

    except sqlite_utils.db.NotFoundError:
        response.status = hug.falcon.HTTP_404
    return {"posts": posts}

# calls setLogin() then redirects user
@hug.get("/home/{username}")
def home_login(username: hug.types.text):
    setLogin(username)
    hug.redirect.to(f"""/home/{username}/auth""")

# returns posts from users that the specific user follows
@hug.get("/home/{username}/auth", requires=auth)
def home(response, db: sqlite, username: hug.types.text):
    posts = []
    conditions = []
    try:
        id_user = getUserID(db, username)

        # get request to endpoint in users.db for user's follower list
        r = requests.get(f"""http://127.0.0.1:8000/users/{username}/followers""")
        r_json = r.json()
        follows = r_json["follows"]

        for i in follows:
            conditions.append("user_id = ?")

        if conditions:
            where = " OR ".join(conditions) # ex: user_id = ? OR user_id = ? ...

            # returns posts of user's followers
            for row in db["posts"].rows_where(where, follows, order_by='timestamp desc', select='username, text, timestamp, url'):
                posts.append(row)

    except sqlite_utils.db.NotFoundError:
        response.status = hug.falcon.HTTP_404
    return {"posts": posts}

# create posts
# example: http -a bob123:hello123 localhost:8000/timelines/bob123/post text="post test"
# if url is filled, then it will be considered a repost
# else, it will be considered a post
@hug.post("/timelines/{username}/post", status=hug.falcon.HTTP_201, requires=auth)
def create_post(
    response,
    db: sqlite,
    username: hug.types.text,
    body: hug.types.json
):
    posts = db["posts"]
    body["url"]=""
    try:
        id_user = getUserID(db, username)
        body["user_id"] = id_user
        body["username"] = username

        # set timestamp
        now = datetime.now()
        date_time = now.strftime("%Y/%m/%d %H:%M:%S")
        body["timestamp"] = date_time

        id_post_dict = next(posts.rows_where(select='max(post_id)+1'))
        # increments post_id before adding to database
        if id_post_dict["max(post_id)+1"] is None:
            body["post_id"] = 1
        else:
            body["post_id"] = id_post_dict["max(post_id)+1"]
        posts.insert(body) # insert to table
        body["id"] = posts.last_pk

    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"error": str(e)}

    response.set_header("Location", f"/timeline/{username}/{id_post_dict}")
    return body

# http -a bob123:hello123 localhost:8000/timelines/bob123/asyncpost text="async test"
@hug.post("/timelines/{username}/asyncpost", status=hug.falcon.HTTP_201, requires=auth)
def create_post(
    response,
    username: hug.types.text,
    body: hug.types.json,
):
    body["username"] = username
    msq_queue.put(json.dumps(body))
    response.status = hug.falcon.HTTP_202
    return body

# http localhost:8000/public
# returns all existing posts
@hug.get("/public")
def public(response, db: sqlite):
    return {"posts": db["posts"].rows_where(order_by='timestamp desc', select='username, text, timestamp, url')}

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
    registerURL = "http://localhost:8000/registry/timelines"
    url = "http://" + socket.gethostbyname(socket.gethostname()) + ":" + os.environ["PORT"] + "/timelines"
    r = requests.post(registerURL, data={"text": url})

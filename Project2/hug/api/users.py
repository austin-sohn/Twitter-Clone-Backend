# Project 2
# Brandon Le
# Ble2306@csu.fullerton.edu

import configparser
import logging.config

import hug
import sqlite_utils

config = configparser.ConfigParser()
config.read("./etc/users.ini")
logging.config.fileConfig(config["logging"]["config"], disable_existing_loggers=False)


@hug.directive()
def sqlite(section="sqlite", key="dbfile", **kwargs):
    dbfile = config[section][key]
    return sqlite_utils.Database(dbfile)

@hug.directive()
def log(name=__name__, **kwargs):
    return logging.getLogger(name)

# getUserID function returns user_id given username
@hug.local()
def getUserID(db: sqlite, username: hug.types.text):
        id_user_generator= db["users"].rows_where("username = :username", {"username": username}, select='user_id')
        id_user_dict = next(id_user_generator)
        id_user = id_user_dict["user_id"]
        return id_user

# called by get request from timelines service to find password of user
@hug.get("/users/login/{username}")
def login(response, db: sqlite, username: hug.types.text):
    password = []

    try:
        id_user = getUserID(db, username)

        for row in db["users"].rows_where("user_id = :id_user", {"id_user": id_user}, select='password'):
            password.append(row["password"])

    except sqlite_utils.db.NotFoundError:
        response.status = hug.falcon.HTTP_404
    return {"password": password}

# called by get request from timeline service to find user's followers in users.db
@hug.get("/users/{username}/followers")
def followers(response, db: sqlite, username: hug.types.text):
    follows = []

    try:
        id_user = getUserID(db,username)

        #finds user's followers
        for row in db["follows"].rows_where("user_id = :id_user", {"id_user": id_user}, select='following_id'):
            id_following = row["following_id"]
            follows.append(id_following)

    except sqlite_utils.db.NotFoundError:
        response.status = hug.falcon.HTTP_404
    return {"follows": follows}

# returns all users' public info
@hug.get("/users")
def users(response, db: sqlite):
    return {"users": db["users"].rows_where(select='username, bio')}

# returns specific user's public info
@hug.get("/users/{username}")
def user(response, db: sqlite, username: hug.types.text):
    users = []
    id_user = getUserID(db, username)
    try:

        for row in db["users"].rows_where("user_id = :id_user", {"id_user": id_user}, select='username, bio'):
            users.append(row)

    except sqlite_utils.db.NotFoundError:
        response.status = hug.falcon.HTTP_404
    return {"users": users}

@hug.get("/users/health")
def checkHealth(response, db: sqlite):
    try:
        users = {"users": db["users"].rows_where()}
        return users;
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"error": str(e)}

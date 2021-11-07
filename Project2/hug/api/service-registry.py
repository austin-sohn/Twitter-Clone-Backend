import requests
from collections import defaultdict

import configparser
import logging.config

import hug
import sqlite_utils

import threading
import time

lock = threading.Lock()
daemonList = []
serviceDict = defaultdict(list)

# no database
# store with python dictionary

def healthCheck(url, name):
    while True: # infinite loop
        r = requests.get(url + "/health_check")
        # GET request (the url saved has to be a base url so we need a health check route)
        if r.status_code != 200:
            with lock:
                serviceDict[name].remove(url)
                return

        sleep(60) # health check every 60 seconds

def setUpHealthCheck(url, name):
    x = threading.Thread(target=healthCheck, url, name)
    x.setDaemon(True)
    daemonList.append(x)

@hug.get("/registry/{name}")
def getServiceUrl(
    response,
    name: hug.types.text,
):
    instances = []
    for instance in serviceDict[name]:
        instances.append(instance)

    if len(instances) == 0: # if there are no instances of servicename
        response.status = hug.falcon.HTTP_404

    return {"instances": instances}


@hug.post("/registry/")
def registerService(
    response,
    url: hug.types.text,
    name: hug.types.text,
):
    serviceDict[name].append(url)
    setUpHealthCheck(url,name)
    response.set_header("Location", f"/registry/")
    return url

import requests
from collections import defaultdict

import time

import hug

import threading


lock = threading.Lock()
daemonList = []
services = {}

# no database
# store with python dictionary

def healthCheck(url, name):
    while True: # infinite loop
        r = requests.get(url + "/health")
        # GET request (the url saved has to be a base url so we need a health check route)
        if r.status_code != 200:
            with lock:
                services[name].remove(url)
                return
        
        time.sleep(10) # health check every 10 seconds

def setUpHealthCheck(url, name):
    x = threading.Thread(target=healthCheck, args=(url,name), daemon=True)
    x.start()
    daemonList.append(x)
    return

@hug.get("/registry/{name}")
def getServiceUrl(
    response,
    name: hug.types.text,
):
    if len(services[name]) == 0: # if there are no instances of servicename
        response.status = hug.falcon.HTTP_404

    return {"instances": services[name]}


@hug.get("/registry")
def getRegistry(
    response,
):
    return {"instances": services}


@hug.post("/registry/{name}")
def registerService(
    response,
    text: hug.types.text,
    name: hug.types.text,
):

    if name in services:
        if text not in services[name]:
            services[name].append(text)
        else:
            response.status = hug.falcon.HTTP_409
            return "URL already registered"
    else:
        services[name] = [text]

    setUpHealthCheck(text,name)
    response.set_header("Location", f"/registry/")
    return services[name]

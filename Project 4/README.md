# CPSC449-Project3

## Project Members
* Brandon Le (Ble2306@csu.fullerton.edu)
* Austin Sohn (austinsohn@csu.fullerton.edu)
* Vien Huynh (Squire25@csu.fullerton.edu)
* Stephanie Cobb (stephanie_cobb@csu.fullerton.edu)

## How to create the database and start the services
To create the databases, you can use the init.sh to create the users.db and posts.db

Alternatively, you can run these commands in the command line:
```
# create database via csv files
sqlite-utils insert ./var/users.db users --csv ./share/users.csv --detect-types --pk=user_id
sqlite-utils insert ./var/users.db follows --csv ./share/follows.csv --detect-types --pk=id
sqlite-utils insert ./var/posts.db posts --csv ./share/posts.csv --detect-types --pk=id

# add foreign keys (optional)
sqlite-utils add-foreign-key ./var/users.db follows user_id users user_id
sqlite-utils add-foreign-key ./var/users.db follows following_id users user_id
```

To run DynamoDB database instance locally, you can run this command in the terminal in the directory of Dynamodb installation:
```
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb -port 8001
```

To start the services in production, run these commands in separate terminals:
```
# First terminal
# cd to api directory first!
foreman start -m users=1,timelines=3,registry=1,polls=1,likes=1

# Second terminal
# cd to ./etc/haproxy
haproxy -f haproxy.cfg
```
The web application should now be able to run on **localhost:8000**.

## REST API documentation for each service

### Microblogging services:
1) users.py
    - **getUserID(db, username)** -- local python function to find userID given username and db
    - **/users/login/{username}** -- called by get request from custom_verify in timelines service to find password given username
    - **/users** -- returns all users' public info
    - **/users/{username}** -- returns specific user's public info
    - **/users/{username}/followers** -- called by get request from timelines service to find user's followers
2) timelines.py
    - **auth = hug.authentication.basic(custom_verify)** -- variable for basic authentication
        - **custom_verify(username, password)** -- hug.cli() function that request to "users/login/{username}" endpoint to verify password
    - **/timelines/{username}** -- returns specific user's own posts
    - **/timelines/{username}/{post_id}** -- returns specific post from the specific user
        - ex: the url "/timeline/brandon2306/1" should bring up the user's first post
    - **/timelines/{username}/post** -- requires auth, create post as a certain user (**authentication needed**)
    - **/home/{username}** - requires auth, access user's home page and followers' posts
    - **/public** -- returns all existing posts
    
    For creating post for timelines:
    ```
    # examples for creating post
    http -a bob123:hello123 localhost:8000/timelines/bob123/post text="today sucks!"
    http http -a brandon2306:chonker123 localhost:8000/timelines/brandon2306/post text="i agree!" url ="/timeline/bob123/1"
    ```

3) likes.py
    - connects to redis database at port 6379 locally
    - **{liker_username}/{username}/{post_id}** -- create a like on a specific post
    - **/likes/count/{username}/{post_id}** -- get request to see how many likes a specific post received
    - **/likes/{liker_username}** -- get request to retrieve a list of posts a specific user liked
    - **/likes/popular** -- get request to see a list of popular posts liked by many users
4) polls.py
    - connects to Dynamodb instance at port 8001 locally and creates table if not existed
    - **/polls** -- returns all existing polls
    - **/polls/create** -- POST method that creates post given username, question, and list of responses
        - Unsure about the syntax for inputing a list of responses in terminal. For exmaple, the terminal interpets "[1,2,3,4]" as one element for response
    - **/polls/vote/{poll_id}** -- POST method where user can vote a response from a certain post given username, post_id, and the specific response
        - To choose response, it is numbered from 0-3 
        - User cannot vote twice
5) registry.py
    - **Important** -- the registry assumes the url provided by registered services has a "/{servicename}/health" route that can return a 200 response to GET requests
    - **/registry** -- returns all instances of all registered services
    - **/registry/{servicename}** -- returns all instances of servicename
    - **/registry/{servicename} POST** -- registers an instance of servicename. The url is provided in the format: text="url"
        - each service also has a self-register function that happens at startup when initiated by hug

## NOTE:

Other than the syntax for inputing a list of responses for polls.py, all the features were implemented and should be working correctly. 


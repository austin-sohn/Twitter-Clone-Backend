from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key
import os
import socket
import requests

# import configparser
# import logging.config

import hug
# import sqlite_utils

# config = configparser.ConfigParser()
# config.read("./etc/polls.ini")
# # logging.config.fileConfig(config["logging"]["config"], disable_existing_loggers=False)


# @hug.directive()
# def sqlite(section="sqlite", key="dbfile", **kwargs):
#     dbfile = config[section][key]
#     return sqlite_utils.Database(dbfile)

# @hug.directive()
# def log(name=__name__, **kwargs):
#     return logging.getLogger(name)

session = boto3.Session(
    aws_access_key_id = 'fakeMyKeyId',
    aws_secret_access_key = 'fakeSecretAccessKey'
)

dynamodb = session.resource('dynamodb', endpoint_url='http://127.0.0.1:8001')

try:
    # Created table already locally
    table = dynamodb.create_table(
        TableName='polls',
        KeySchema=[
            {
                'AttributeName': 'poll_id',
                'KeyType': 'HASH'            
            },
            {
                'AttributeName': 'creation_date',
                'KeyType': 'RANGE'
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'poll_id',
                'AttributeType': 'N'
            },
            {
                'AttributeName': 'creation_date',
                'AttributeType': 'N'
            },
            {
                "AttributeName": "show",
                "AttributeType": "N"
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        },
        GlobalSecondaryIndexes=[
            {
                "IndexName": "show_index",
                "KeySchema": [
                    {"AttributeName":"show","KeyType":"HASH"},
                    {"AttributeName":"creation_date","KeyType":"RANGE"}
                ],
                "Projection": {
                    "ProjectionType":"INCLUDE",
                    "NonKeyAttributes": ["poll_id, username", "question", "responses","counts"]
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1
                }
            },
            # {
            #     "IndexName": "test_index",
            #     "KeySchema": [
            #         {"AttributeName":"poll_id","KeyType":"HASH"},
            #         {"AttributeName":"creation_date","KeyType":"RANGE"}
            #     ],
            #     "Projection": {
            #         "ProjectionType":"INCLUDE",
            #         "NonKeyAttributes": ["username", "question", "responses","counts"]
            #     },
            #     "ProvisionedThroughput": {
            #         "ReadCapacityUnits": 1,
            #         "WriteCapacityUnits": 1
            #     }
            # },
            {
                "IndexName": "poll_id_index",
                "KeySchema": [
                    {"AttributeName":"poll_id","KeyType":"HASH"}
                ],
                "Projection": {
                    "ProjectionType":"INCLUDE",
                    "NonKeyAttributes": ["creation_date","voters"]
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1
                }
            }
        ]
    )
    print("Table created!")
except Exception:
    print("Table is already created. Moving on...")
    pass



now = datetime.now()
date_time = int(now.strftime("%Y%m%d%H%M%S"))

table = dynamodb.Table('polls')

# ADD ITEMS
# table.put_item(
#     Item={
#         'poll_id': 0,
#         'creation_date': date_time,
#         'username': "bob123",
#         'question': "What is your favorite food?",
#         'responses': ["Ice cream", "Sushi"],
#         'counts': [2,0],
#         'voters': ["ble2306", "aminta714"],
#         'show': 1
#     }
# )
# table.put_item(
#     Item={
#         'poll_id': 1,
#         'creation_date': date_time,
#         'username': "brandon2306",
#         'question': "What is your favorite show?",
#         'responses': ["Tom and Jerry", "Justice League", "Chowder", "Spongebob"],
#         'counts': [1,0,1,0],
#         'voters': ["bob123", "aminta714"],
#         'show': 1
#     }
# )

@hug.get("/polls")
def polls():
    # response = table.scan(
    #     IndexName="test_index"
    # )
    response = table.query(
        IndexName="show_index",
        Select="ALL_PROJECTED_ATTRIBUTES",
        KeyConditionExpression=Key('show').eq(1),
        ScanIndexForward=False
    )
    items = response['Items']
    return {"polls":items}

@hug.post("/polls/create", status=hug.falcon.HTTP_201)
def createpoll(
    response, 
    username: hug.types.text, 
    question: hug.types.text, 
    responses: hug.types.multiple):
    try:
        poll_id_query = table.query(
            IndexName="show_index",
            Select="ALL_PROJECTED_ATTRIBUTES",
            KeyConditionExpression=Key('show').eq(1),
            ScanIndexForward=False,
            Limit=1
        )
        item = poll_id_query['Items']
        if (len(item) != 0):
            poll_id = item[0]['poll_id']
            poll_id = poll_id + 1
        else:
            poll_id = 0
        print(poll_id)
        poll_output = {
            "poll_id": poll_id,
            "username": username,
            "question": question,
            "responses": responses,
        }

        now = datetime.now()
        date_time = int(now.strftime("%Y%m%d%H%M%S"))
        
        counts_temp = [0] * len(responses)
        voters = []
        table.put_item(
            Item={
                'poll_id': poll_id,
                'creation_date': date_time,
                'username': username,
                'question': question,
                'responses': responses,
                'counts': counts_temp,
                'voters': voters,
                'show': 1
            }
        )
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"error": str(e)}
    return poll_output


@hug.post("/polls/vote/{poll_id}", status=hug.falcon.HTTP_201)
def postVote(
    response,
    username: hug.types.text,
    poll_id: hug.types.number,
    vote: hug.types.number
):
    try:
        creation_date_query= table.query(
            IndexName="poll_id_index",
            Select="ALL_PROJECTED_ATTRIBUTES",
            KeyConditionExpression=Key('poll_id').eq(0),
            Limit=1
        )
        item = creation_date_query['Items']

        creation_date = item[0]['creation_date']

        vote_output = {
            "username": username,
            "vote": vote,
            "poll_id": poll_id
        }

        table.update_item(
            Key= {
                "poll_id": poll_id,
                "creation_date": creation_date
            },
            UpdateExpression=f"ADD counts[{vote}] :v1 SET #V = list_append(#V,:v2)",
            ConditionExpression= "not contains (#V, :v3)",
            ExpressionAttributeNames= {
                "#V": 'voters'
            },
            ExpressionAttributeValues= {
                ":v1": 1,
                ":v2": [username],
                ":v3": username
            },
            # ReturnValues="ALL_NEW"
        )
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        if(e.__class__.__name__ == "ConditionalCheckFailedException"):
            return {"error": "This user has already voted"}
        return {"error": str(e)}
    return vote_output

@hug.get("/polls/health")
def checkHealth(response):
    try:
        q = table.scan(Limit=1)
        items = q['Items']
        return items
    except Exception as e:
        response.status = hug.falcon.HTTP_409
        return {"error": str(e)}

@hug.startup()
def selfRegister(api):
    registerURL = "http://localhost:8000/registry/polls"
    url = "http://" + socket.gethostbyname(socket.gethostname()) + ":" + os.environ["PORT"] + "/polls"
    r = requests.post(registerURL, data={"text": url})

# terraform/src/join_queue_function/main.py

import json
import os
import time
import uuid

import boto3

dynamodb = boto3.resource("dynamodb")
sqs = boto3.client("sqs")
ssm = boto3.client("ssm")

TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME")
QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
PARAMETER_NAME = os.environ.get("SSM_PARAMETER_NAME")
TOKEN_EXPIRATION_MINUTES = 240


def lambda_handler(event, context):
    """
    Handles a new user joining the waiting room.
    1. Generates a unique token.
    2. Creates an item in DynamoDB with status 'WAITING'.
    3. Sends a message to SQS with the token.
    4. Returns the token to the client.
    """
    if not TABLE_NAME or not QUEUE_URL:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Environment variables not configured."}),
        }

    parameter = ssm.get_parameter(Name=PARAMETER_NAME)
    is_waiting_room_enabled = parameter["Parameter"]["Value"].lower() == "true"

    # If waiting room is OFF, grant direct access
    if not is_waiting_room_enabled:
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"status": "DIRECT_ACCESS"}),
        }

    try:
        # 1. Generate a unique token
        user_token = str(uuid.uuid4())

        # 2. Create an item in DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        current_time = int(time.time())
        # Set a TTL for the item to be auto-deleted after some time
        expires_at = current_time + (TOKEN_EXPIRATION_MINUTES * 60)

        table.put_item(
            Item={
                "token": user_token,
                "status": "WAITING",
                "createdAt": current_time,
                "expiresAt": expires_at,
            }
        )

        # 3. Send a message to SQS
        sqs.send_message(
            QueueUrl=QUEUE_URL, MessageBody=json.dumps({"token": user_token})
        )

        # 4. Return the token to the client
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"token": user_token}),
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "An internal error occurred."}),
        }

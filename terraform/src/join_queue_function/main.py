# terraform/src/join_queue_function/main.py

import json
import os
import time
import uuid
from decimal import Decimal

import boto3

dynamodb = boto3.resource("dynamodb")
sqs = boto3.client("sqs")
ssm = boto3.client("ssm")

TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME")
QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
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
    try:
        # 1. Generate a unique token
        user_token = str(uuid.uuid4())

        # 2. Create an item in DynamoDB
        table = dynamodb.Table(TABLE_NAME)

        # Atomically increment the counter to get the next ticket number
        counter_response = table.update_item(
            Key={"token": "counter"},
            UpdateExpression="SET ticketValue = if_not_exists(ticketValue, :start) + :inc",
            ExpressionAttributeValues={":inc": Decimal(1), ":start": Decimal(0)},
            ReturnValues="UPDATED_NEW",
        )
        ticket_number = int(counter_response["Attributes"]["ticketValue"])

        current_time = int(time.time())
        # Set a TTL for the item to be auto-deleted after some time
        expires_at = current_time + (TOKEN_EXPIRATION_MINUTES * 60)

        table.put_item(
            Item={
                "token": user_token,
                "status": "WAITING",
                "ticketNumber": ticket_number,
                "createdAt": current_time,
                "expiresAt": expires_at,
            }
        )

        # 3. Send a message to SQS
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(
                {"token": user_token, "ticketNumber": ticket_number}
            ),
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

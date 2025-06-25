import json
import os
import time
import uuid
from decimal import Decimal

import boto3

dynamodb = boto3.resource("dynamodb")
sqs = boto3.client("sqs")

TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME")
QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
TOKEN_EXPIRATION_MINUTES = 240


def lambda_handler(event, context):
    """
    Handles a new user joining the waiting room.
    1. Atomically increments a counter in DynamoDB to get a ticket number.
    2. Creates an item for the user with their ticket number.
    3. Sends a message to the FIFO SQS queue with a MessageGroupId.
    4. Returns the unique token to the client.
    """
    if not TABLE_NAME or not QUEUE_URL:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Environment variables not configured."}),
        }
    try:
        table = dynamodb.Table(TABLE_NAME)

        # 1. Atomically increment the central counter to get the next ticket number.
        #    This ensures each user gets a unique, sequential number.
        #    'if_not_exists' initializes the counter if it's the very first user.
        counter_response = table.update_item(
            Key={"token": "counter"},
            UpdateExpression="SET ticketValue = if_not_exists(ticketValue, :start) + :inc",
            ExpressionAttributeValues={":inc": Decimal(1), ":start": Decimal(0)},
            ReturnValues="UPDATED_NEW",
        )
        ticket_number = int(counter_response["Attributes"]["ticketValue"])

        # 2. Create a unique record for the user in the DynamoDB table.
        user_token = str(uuid.uuid4())
        current_time = int(time.time())
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

        # 3. Send a message to the SQS FIFO queue.
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(
                {"token": user_token, "ticketNumber": ticket_number}
            ),
            # This is REQUIRED for FIFO queues. All messages in our queue can
            # belong to the same group to ensure they are processed sequentially.
            MessageGroupId="waiting-room-group",
        )

        # 4. Return the unique token to the user's browser.
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"token": user_token}),
        }

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "An internal error occurred."}),
        }

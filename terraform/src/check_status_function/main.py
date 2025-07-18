import datetime
import json
import os

import boto3
import jwt

dynamodb = boto3.resource("dynamodb")

TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")


def lambda_handler(event, context):
    """
    Checks the status of a user in the DynamoDB table based on their token.
    The token is expected as a query string parameter.
    """
    if not TABLE_NAME or not JWT_SECRET_KEY:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Environment variables not configured."}),
        }

    token = event.get("queryStringParameters", {}).get("token")

    if not token:
        return {"statusCode": 400, "body": json.dumps({"error": "Token is required."})}

    try:
        table = dynamodb.Table(TABLE_NAME)

        response = table.get_item(Key={"token": token})

        item = response.get("Item")

        if not item:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Token not found or expired."}),
            }

        status = item.get("status", "UNKNOWN")

        if status == "ALLOWED":
            payload = {
                "sub": token,
                "exp": datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(minutes=5),
            }

            signed_jwt = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"status": "ALLOWED", "jwt": signed_jwt}),
            }

        if status == "WAITING":
            user_ticket = int(item.get("ticketNumber", 0))

            # 2. Get the central counter item to find out who is being served
            counter_response = table.get_item(Key={"token": "counter"})
            counter_item = counter_response.get("Item", {})
            now_serving = int(counter_item.get("nowServing", 0))

            # 3. Calculate the position
            position = user_ticket - now_serving
            if position < 0:
                position = 0

            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"status": "WAITING", "position": position}),
            }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": status}),
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "An internal error occurred."}),
        }

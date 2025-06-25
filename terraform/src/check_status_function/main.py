import json
import os

import boto3

dynamodb = boto3.resource("dynamodb")

TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME")


def lambda_handler(event, context):
    """
    Checks the status of a user in the DynamoDB table based on their token.
    The token is expected as a query string parameter.
    """
    if not TABLE_NAME:
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

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"status": item.get("status", "UNKNOWN")}),
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "An internal error occurred."}),
        }

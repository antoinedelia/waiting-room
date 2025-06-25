import json
import os

import boto3

dynamodb = boto3.resource("dynamodb")
sqs = boto3.client("sqs")

TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME")
QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
USERS_TO_PROCESS = int(os.environ.get("USERS_TO_PROCESS", 10))


def lambda_handler(event, context):
    """
    Processes messages from the SQS queue to allow users into the site.
    1. Receives a batch of messages from SQS.
    2. For each message, updates the user's status in DynamoDB to 'ALLOWED'.
    3. Deletes the processed messages from the SQS queue.
    """
    if not TABLE_NAME or not QUEUE_URL:
        print("Error: Environment variables not configured.")
        return

    print(f"Processing up to {USERS_TO_PROCESS} users from the queue.")

    try:
        # 1. Receive a batch of messages from SQS
        response = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=USERS_TO_PROCESS,
            WaitTimeSeconds=1,
        )

        messages = response.get("Messages", [])
        if not messages:
            print("No messages in the queue to process.")
            return

        print(f"Received {len(messages)} messages to process.")
        table = dynamodb.Table(TABLE_NAME)
        delete_entries = []

        for message in messages:
            message_body = json.loads(message["Body"])
            token = message_body.get("token")

            if not token:
                print(f"Skipping message with no token: {message['MessageId']}")
                continue

            # 2. Update the user's status in DynamoDB
            try:
                table.update_item(
                    Key={"token": token},
                    UpdateExpression="set #s = :s",
                    ConditionExpression="attribute_exists(#t)",
                    ExpressionAttributeNames={"#s": "status", "#t": "token"},
                    ExpressionAttributeValues={":s": "ALLOWED"},
                )
                print(f"Successfully updated status for token: {token}")

                # If the update was successful, add the message to be deleted
                delete_entries.append(
                    {
                        "Id": message["MessageId"],
                        "ReceiptHandle": message["ReceiptHandle"],
                    }
                )
            except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
                # This happens if the TTL expired and the item was deleted.
                # The user is gone, so we should just delete the message.
                print(
                    f"DynamoDB item for token {token} no longer exists. Deleting message."
                )
                delete_entries.append(
                    {
                        "Id": message["MessageId"],
                        "ReceiptHandle": message["ReceiptHandle"],
                    }
                )
            except Exception as e:
                print(f"Error updating DynamoDB for token {token}: {e}")
                # Don't delete the message, let it be reprocessed later

        # 3. Delete the processed messages from SQS in a batch
        if delete_entries:
            sqs.delete_message_batch(QueueUrl=QUEUE_URL, Entries=delete_entries)
            print(f"Deleted {len(delete_entries)} messages from the queue.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        # Re-raise the exception to signal failure to the invoker (EventBridge)
        raise e

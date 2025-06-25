import os
import time

import boto3

ssm = boto3.client("ssm", region_name="eu-west-1")

PARAMETER_NAME = os.environ.get("SSM_PARAMETER_NAME")
WAITING_ROOM_URL = os.environ.get("CLOUDFRONT_WAITING_ROOM_URL")

cached_response = {
    "enabled": None,
    "last_checked": 0,
    "ttl": 30,
}


def is_cache_expired():
    """Checks if the cached SSM parameter value is older than our TTL."""
    return (time.time() - cached_response["last_checked"]) > cached_response["ttl"]


def lambda_handler(event, context):
    """
    This function is triggered on every viewer request to the main site.
    It checks if the waiting room is active and redirects users if necessary.
    """
    request = event["Records"][0]["cf"]["request"]

    # --- 1. Check the Feature Flag (with Caching) ---
    if cached_response["enabled"] is None or is_cache_expired():
        try:
            print("Cache expired or empty. Fetching SSM parameter.")
            parameter = ssm.get_parameter(Name=PARAMETER_NAME)
            is_enabled = parameter["Parameter"]["Value"].lower() == "true"

            # Update the cache
            cached_response["enabled"] = is_enabled
            cached_response["last_checked"] = time.time()
        except Exception as e:
            # If we fail to get the parameter, fail open (let users through)
            print(f"Error fetching SSM parameter: {e}. Defaulting to disabled.")
            cached_response["enabled"] = False

    # --- 2. If Waiting Room is OFF, let the user through ---
    if not cached_response["enabled"]:
        print("Waiting room is disabled. Passing request to origin.")
        return request

    # --- 3. If Waiting Room is ON, check for a "pass" cookie (to be implemented later) ---
    # For now, we will just redirect everyone to demonstrate the interception.
    # In the next step, we would add logic here to check for a valid JWT cookie.

    # --- 4. If no "pass" cookie, REDIRECT ---
    print("Waiting room is enabled. Redirecting user to queue.")
    response = {
        "status": "302",
        "statusDescription": "Found",
        "headers": {"location": [{"key": "Location", "value": WAITING_ROOM_URL}]},
    }
    return response

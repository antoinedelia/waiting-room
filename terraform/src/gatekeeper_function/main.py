import json
import os
import time
from urllib.parse import parse_qs

import boto3
import jwt

ssm = boto3.client("ssm", region_name="eu-west-1")

config_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(config_path) as f:
    config = json.load(f)

PARAMETER_NAME = config["ssm_parameter_name"]
WAITING_ROOM_URL = config["waiting_room_url"]
JWT_SECRET_KEY = config["jwt_secret_key"]
PASS_COOKIE_NAME = "waiting-room-pass"

cached_ssm_response = {
    "enabled": None,
    "last_checked": 0,
    "ttl": 30,
}


def is_cache_expired():
    """Checks if the cached SSM parameter value is older than our TTL."""
    return (time.time() - cached_ssm_response["last_checked"]) > cached_ssm_response[
        "ttl"
    ]


def lambda_handler(event, context):
    """
    This function is triggered on every viewer request to the main site.
    It checks if the waiting room is active and redirects users if necessary.
    """
    request = event["Records"][0]["cf"]["request"]

    # --- 1. Check the Feature Flag (with Caching) ---
    if cached_ssm_response["enabled"] is None or is_cache_expired():
        try:
            print("Cache expired or empty. Fetching SSM parameter.")
            parameter = ssm.get_parameter(Name=PARAMETER_NAME)
            is_enabled = parameter["Parameter"]["Value"].lower() == "true"

            # Update the cache
            cached_ssm_response["enabled"] = is_enabled
            cached_ssm_response["last_checked"] = time.time()
        except Exception as e:
            # If we fail to get the parameter, fail open (let users through)
            print(f"Error fetching SSM parameter: {e}. Defaulting to disabled.")
            cached_ssm_response["enabled"] = False

    # --- 2. If Waiting Room is OFF, let the user through ---
    if not cached_ssm_response["enabled"]:
        print("Waiting room is disabled. Passing request to origin.")
        return request

    # --- 3. If Waiting Room is ON, check for a "pass" cookie ---
    headers = request.get("headers", {})
    if "cookie" in headers:
        for cookie in headers["cookie"][0]["value"].split(";"):
            if PASS_COOKIE_NAME in cookie:
                try:
                    pass_jwt = cookie.strip().split("=")[1]
                    jwt.decode(pass_jwt, JWT_SECRET_KEY, algorithms=["HS256"])
                    print("Valid pass cookie found. Allowing request.")
                    return (
                        request  # Success! The user has a valid pass. Let them through.
                    )
                except jwt.ExpiredSignatureError:
                    print("Pass cookie has expired. User will be redirected.")
                    break  # Stop checking cookies and proceed to redirect
                except Exception as e:
                    print(f"Invalid pass cookie found: {e}. User will be redirected.")
                    break  # Stop checking cookies and proceed to redirect

    query_string = request.get("querystring", "")
    query_params = parse_qs(query_string)
    pass_token_from_url = query_params.get("pass_token", [None])[0]

    if pass_token_from_url:
        try:
            # Validate the token from the URL
            jwt.decode(pass_token_from_url, JWT_SECRET_KEY, algorithms=["HS256"])
            print("Valid pass_token found in URL. Setting cookie and redirecting.")

            # If valid, issue a response that sets the cookie and redirects
            # to the clean URL (without the token in the address bar).
            response = {
                "status": "302",
                "statusDescription": "Found",
                "headers": {
                    "location": [
                        {
                            "key": "Location",
                            "value": f"https://{headers['host'][0]['value']}{request['uri']}",
                        }
                    ],
                    "set-cookie": [
                        {
                            "key": "Set-Cookie",
                            "value": f"{PASS_COOKIE_NAME}={pass_token_from_url}; Path=/; HttpOnly; Secure; Max-Age=300",
                        }
                    ],
                },
            }
            return response
        except Exception as e:
            print(f"Invalid pass_token in URL: {e}")

    # --- 4. If no "pass" cookie, REDIRECT ---
    print("Waiting room is enabled. Redirecting user to queue.")
    response = {
        "status": "302",
        "statusDescription": "Found",
        "headers": {"location": [{"key": "Location", "value": WAITING_ROOM_URL}]},
    }
    return response

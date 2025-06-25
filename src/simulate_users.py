# /// script
# dependencies = [
#   "requests",
# ]
# ///

import threading
import time

import requests

# Replace this with the invoke URL from your API Gateway stage
API_ENDPOINT = "https://c305xzvm7c.execute-api.eu-west-1.amazonaws.com/v1/join"
NUM_USERS_TO_SIMULATE = 100  # How many users to simulate
REQUESTS_PER_SECOND = 50  # How quickly to send requests


def join_queue():
    """Sends a single request to the /join endpoint."""
    try:
        response = requests.post(API_ENDPOINT, timeout=10)
        if response.status_code == 200:
            print(
                f"Success: A user joined the queue. Token: {response.json().get('token')}"
            )
        else:
            print(f"Error: Status code {response.status_code}, Body: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")


def run_simulation():
    """Runs the simulation by sending requests in parallel."""
    threads = []
    start_time = time.time()

    for i in range(NUM_USERS_TO_SIMULATE):
        thread = threading.Thread(target=join_queue)
        threads.append(thread)
        thread.start()

        # Simple rate limiting
        if i % REQUESTS_PER_SECOND == 0 and i > 0:
            time.sleep(1)

    for thread in threads:
        thread.join()

    end_time = time.time()
    print(f"\nSimulation finished in {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    print(f"Starting simulation for {NUM_USERS_TO_SIMULATE} users...")
    run_simulation()

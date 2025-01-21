import asyncio
import base64
import json
import logging
import random
import time
from go2_webrtc_driver.webrtc_driver import Go2WebRTCConnection, WebRTCConnectionMethod

# Enable logging for debugging
# logging.basicConfig(
#     level=logging.DEBUG,  # Set to DEBUG to capture all logs
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Include timestamp, logger name, and log level
#     handlers=[logging.StreamHandler()]  # Ensure logs are sent to the terminal
# )
    
async def main():
    try:
        print("Starting connection process...")
        conn = Go2WebRTCConnection(WebRTCConnectionMethod.LocalAP)

        # Connect to the WebRTC service.
        await conn.connect()
        print("WebRTC connection established.")

        # Check if the data channel is opened.
        if conn.datachannel.data_channel_opened:
            print("Data channel is opened and ready.")
        else:
            print("Data channel is not opened. Exiting...")
            return
        # Log the process of publishing data
        print("Preparing to publish data...")
        parameter = {"x": 0.5, "y": 0.0, "z": 0.0}
        generated_id = int(time.time() * 1000) % 2147483648 + random.randint(0, 1000)
        api_id = 1008
        request_payload = {
            "header": {
            "identity": {
                "id": generated_id,
                "api_id": api_id
            }
            },
            "parameter": json.dumps(parameter)
        }

        # Check if parameter contains x, y, and z
        if all(key in parameter for key in ["x", "y", "z"]):
            print("Parameter contains x, y, and z.")
        else:
            print("Parameter does not contain x, y, and z.")

        try:
            await conn.datachannel.pub_sub.publish("rt/api/sport/request", request_payload)
            print("Data successfully published.")
        except Exception as e:
            print(f"Failed to publish data: {e}")
        await asyncio.sleep(3)

        generated_id = int(time.time() * 1000) % 2147483648 + random.randint(0, 1000)
        api_id = 1008
        request_payload = {
            "header": {
                "identity": {
                    "id": generated_id,
                    "api_id": api_id
                }
            },
            "parameter": json.dumps({"x": 0.0, "y": 0.5, "z": 0.0})
        }
        await conn.datachannel.pub_sub.publish("rt/api/sport/request", request_payload)
        print("Data with api_id 1005 published successfully.")

        # Keep the program running to allow event handling for 1 hour.
        await asyncio.sleep(3600)

    except ValueError as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
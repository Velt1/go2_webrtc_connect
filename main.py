import asyncio
#import base64
import json
import random
import time
#import threading
#import cv2
#import numpy as np
from queue import Queue
from go2_webrtc_driver.webrtc_driver import Go2WebRTCConnection, WebRTCConnectionMethod
#from aiortc import MediaStreamTrack

class RobotServer:
    def __init__(self):
        self.robot_ip = None
        self.clients = set()
        self.robot_status = None
        self.conn = None
        self.frame_queue = Queue()
        
    async def handle_client(self, reader, writer):
        print("Neuer Client verbunden")
        self.clients.add(writer)
        buffer = ""
        try:
            while True:
                data = await reader.read(100)
                if not data:
                    break
                buffer += data.decode()
                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    await self.process_message(json.loads(message), writer)
        except Exception as e:
            print(f"Fehler bei der Verarbeitung des Clients: {e}")
        finally:
            self.clients.remove(writer)
            writer.close()
            print("Client getrennt")
            if (self.conn):
                await self.conn.disconnect();
                self.conn = None

    async def process_message(self, message, writer):
        print(f"Nachricht empfangen: {message}")
        if 'ip_address' in message and not self.conn:
            await self.connect_to_robot(message['ip_address'])
        else:
            api_id = message.get('api_id', None)
            params = message.get('params', {})
            await self.send_command_to_robot(api_id, params)

    def on_robot_reconnected(self):
        print(">>> Robot has reconnected! This is our custom callback.")
        asyncio.create_task(self.update_robot_status())

    async def connect_to_robot(self, ip):
        self.robot_ip = ip
        print("Verbinde mit Roboter... via " + ip)
        self.conn = Go2WebRTCConnection(WebRTCConnectionMethod.LocalSTA, ip=self.robot_ip)
        try:
            if self.conn.isConnected:
                print("Bereits verbunden mit Roboter")
                return

            self.conn.on_reconnected = self.on_robot_reconnected
            await self.conn.connect()
            # await self.conn.connect()
            # await self.conn.datachannel.disableTrafficSaving(True)
            print(f"Verbunden mit Roboter auf IP: {self.robot_ip}")
            asyncio.create_task(self.update_robot_status())
            # asyncio.create_task(self.start_video_stream())
        except Exception as e:
            print(f"Fehler beim Verbinden mit dem Roboter: {e}")

    async def send_command_to_robot(self, api_id, parameter):
        if api_id:
            api_id = int(api_id)
        else:
            print("Keine API-ID angegeben. Befehl nicht gesendet.")
            return
        if all(key in parameter for key in ["x", "y", "z"]):
            parameter = json.dumps(parameter)
        else:
            parameter = ""
            print("Parameter does not contain x, y, and z.")

        print(f"Sende Befehl an Roboter: {api_id}")
        if not self.conn:
            print("Keine Verbindung zum Roboter. Bitte zuerst verbinden.")
            return
        generated_id = int(time.time() * 1000) % 2147483648 + random.randint(0, 1000)
        request_payload = {
            "header": {
                "identity": {
                    "id": generated_id,
                    "api_id": api_id
                }
            },
            "parameter": parameter
        }
        await self.conn.datachannel.pub_sub.publish("rt/api/sport/request", request_payload)

    async def update_robot_status(self):
        if not self.conn:
            print("Keine Verbindung zum Roboter. Status-Updates nicht möglich.")
            return

        def status_callback(message):
            self.robot_status = message["data"]
            self.send_status_to_clients()

        try:
            self.conn.datachannel.pub_sub.subscribe("rt/lf/lowstate", status_callback)
            print("Abonniert für Roboter-Status-Updates")
        except Exception as e:
            print(f"Fehler beim Abonnieren von Status-Updates: {e}")

    def send_status_to_clients(self):
        status_message = json.dumps({"type": "status_update", "data": self.robot_status}) + '\n'
        for client in self.clients:
            try:
                client.write(status_message.encode())
                asyncio.create_task(client.drain())
            except Exception as e:
                print(f"Fehler beim Senden des Status-Updates an Client: {e}")

    # async def recv_camera_stream(self, track: MediaStreamTrack):
    #     failed_frames = 0
    #     max_failed_frames = 10  # Allow some initial failed frames
        
    #     while True:
    #         try:
    #             frame = await track.recv()
    #             img = frame.to_ndarray(format="bgr24")
                
    #             # Basic validation of the frame
    #             if img is not None and img.size > 0 and len(img.shape) == 3:
    #                 failed_frames = 0  # Reset counter on successful frame
    #                 self.frame_queue.put(img)
    #             else:
    #                 failed_frames += 1
    #                 print(f"Received invalid frame (attempt {failed_frames})")
                    
    #         except Exception as e:
    #             failed_frames += 1
    #             print(f"Error receiving frame (attempt {failed_frames}): {e}")
                
    #         if failed_frames >= max_failed_frames:
    #             print("Too many failed frames, waiting before retrying...")
    #             await asyncio.sleep(1)  # Wait a bit before retrying
    #             failed_frames = 0  # Reset counter

    # async def start_video_stream(self):
    #     if not self.conn:
    #         print("Keine Verbindung zum Roboter. Video-Stream nicht möglich.")
    #         return
        
    #     try:
    #         # Clear any existing frames
    #         while not self.frame_queue.empty():
    #             self.frame_queue.get()
            
    #         # Wait for connection to stabilize
    #         await asyncio.sleep(2)
            
    #         # Enable video stream
    #         self.conn.video.switchVideoChannel(True)
    #         print("Video stream enabled, waiting for initialization...")
    #         await asyncio.sleep(1)
            
    #         self.conn.video.add_track_callback(self.recv_camera_stream)
            
    #         # Start display thread
    #         threading.Thread(target=self.display_video, daemon=True).start()
    #         print("Video display thread started")
            
    #     except Exception as e:
    #         print(f"Fehler beim Starten des Video-Streams: {e}")

    # def display_video(self):
    #     cv2.namedWindow("Video", cv2.WINDOW_NORMAL)
    #     while True:
    #         if not self.frame_queue.empty():
    #             img = self.frame_queue.get()
    #             print(f"Shape: {img.shape}, Dimensions: {img.ndim}, Type: {img.dtype}, Size: {img.size}")
                
    #             # Show the image and process events with a very short wait
    #             cv2.imshow("Video", img)
    #             key = cv2.waitKey(1)  # Wait 1ms
    #             if key & 0xFF == ord('q'):
    #                 break
    #         else:
    #             # Shorter sleep to be more responsive
    #             time.sleep(0.001)
                
    #             # Process window events even when queue is empty
    #             key = cv2.waitKey(1)
    #             if key & 0xFF == ord('q'):
    #                 break
        
    #     cv2.destroyAllWindows()

async def main():
    server = RobotServer()
    srv = await asyncio.start_server(server.handle_client, '0.0.0.0', 12346)
    print(f"Server gestartet auf {srv.sockets[0].getsockname()}")
    
    async with srv:
        await srv.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())

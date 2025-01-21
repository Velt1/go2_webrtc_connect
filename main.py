import asyncio
import base64
import json
import random
import time
from go2_webrtc_driver.webrtc_driver import Go2WebRTCConnection, WebRTCConnectionMethod

class RobotServer:
    def __init__(self):
        self.robot_ip = None
        self.clients = set()
        self.robot_status = None
        self.conn = None
        

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

    async def process_message(self, message, writer):
        print(f"Nachricht empfangen: {message}")
        if 'ip_address' in message and not self.conn:
            await self.connect_to_robot(message['ip_address'])
        else:
            api_id = message.get('api_id', None)
            params = message.get('params', {})  # Default to an empty dictionary if 'params' is missing
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
        except Exception as e:
            print(f"Fehler beim Verbinden mit dem Roboter: {e}")

    async def send_command_to_robot(self, api_id, parameter):
        if api_id:
            api_id = int(api_id)
        else:
            print("Keine API-ID angegeben. Befehl nicht gesendet.")
            return
        if all(key in parameter for key in ["x", "y", "z"]):
            print("Parameter contains x, y, and z.")
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

async def main():
    server = RobotServer()
    srv = await asyncio.start_server(server.handle_client, '0.0.0.0', 12346)
    print(f"Server gestartet auf {srv.sockets[0].getsockname()}")
    
    async with srv:
        await srv.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
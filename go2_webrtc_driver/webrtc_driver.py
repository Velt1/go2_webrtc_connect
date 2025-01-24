import asyncio
import logging
import json
import platform
import subprocess
import sys
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceServer, RTCConfiguration
from aiortc.contrib.media import MediaPlayer
from .unitree_auth import send_sdp_to_local_peer, send_sdp_to_remote_peer
from .webrtc_datachannel import WebRTCDataChannel
from .webrtc_audio import WebRTCAudioChannel
from .webrtc_video import WebRTCVideoChannel
from .constants import DATA_CHANNEL_TYPE, WebRTCConnectionMethod
from .util import fetch_public_key, fetch_token, fetch_turn_server_info, print_status
from .multicast_scanner import discover_ip_sn

# # Enable logging for debugging
logging.basicConfig(level=logging.INFO)

class Go2WebRTCConnection:
    def __init__(self, connectionMethod: WebRTCConnectionMethod, serialNumber=None, ip=None, username=None, password=None) -> None:
        self.pc = None
        self.sn = serialNumber
        self.ip = ip
        self.connectionMethod = connectionMethod
        self.isConnected = False
        self.token = fetch_token(username, password) if username and password else ""
        self.on_reconnected = None

    async def connect(self):
        print_status("WebRTC connection", "🟡 started")
        if self.connectionMethod == WebRTCConnectionMethod.Remote:
            self.public_key = fetch_public_key()
            turn_server_info = fetch_turn_server_info(self.sn, self.token, self.public_key)
            await self.init_webrtc(turn_server_info)
        elif self.connectionMethod == WebRTCConnectionMethod.LocalSTA:
            if not self.ip and self.sn:
                discovered_ip_sn_addresses = discover_ip_sn()
                
                if discovered_ip_sn_addresses:
                    if self.sn in discovered_ip_sn_addresses:
                        self.ip = discovered_ip_sn_addresses[self.sn]
                    else:
                        raise ValueError("The provided serial number wasn't found on the network. Provide an IP address instead.")
                else:
                    raise ValueError("No devices found on the network. Provide an IP address instead.")

            await self.init_webrtc(ip=self.ip)
        elif self.connectionMethod == WebRTCConnectionMethod.LocalAP:
            self.ip = "192.168.12.1"
            await self.init_webrtc(ip=self.ip)
    
    async def disconnect(self):
        if self.pc:
            await self.pc.close()
            self.pc = None
        self.isConnected = False
        print_status("WebRTC connection", "🔴 disconnected")

    async def reconnect(self):
        await self.disconnect()
        await self.connect()
        print_status("WebRTC connection", "🟢 reconnected")
        if self.on_reconnected:
            self.on_reconnected()

    def create_webrtc_configuration(self, turn_server_info, stunEnable=True, turnEnable=True) -> RTCConfiguration:
        ice_servers = []

        if turn_server_info:
            username = turn_server_info.get("user")
            credential = turn_server_info.get("passwd")
            turn_url = turn_server_info.get("realm")
            
            if username and credential and turn_url:
                if turnEnable:
                    ice_servers.append(
                        RTCIceServer(
                            urls=[turn_url],
                            username=username,
                            credential=credential
                        )
                    )
                if stunEnable:
                    # Use Google's public STUN server
                    stun_url = "stun:stun.l.google.com:19302"
                    ice_servers.append(
                        RTCIceServer(
                            urls=[stun_url]
                        )
                    )
            else:
                raise ValueError("Invalid TURN server information")
        
        configuration = RTCConfiguration(
            iceServers=ice_servers
        )
        
        return configuration

    async def init_webrtc(self, turn_server_info=None, ip=None):
        configuration = self.create_webrtc_configuration(turn_server_info)
        self.pc = RTCPeerConnection(configuration)


        self.datachannel = WebRTCDataChannel(self, self.pc)

        #self.audio = WebRTCAudioChannel(self.pc, self.datachannel)
        self.video = WebRTCVideoChannel(self.pc, self.datachannel)

        @self.pc.on("icegatheringstatechange")
        async def on_ice_gathering_state_change():
            state = self.pc.iceGatheringState
            if state == "new":
                print_status("ICE Gathering State", "🔵 new")
            elif state == "gathering":
                print_status("ICE Gathering State", "🟡 gathering")
            elif state == "complete":
                print_status("ICE Gathering State", "🟢 complete")


        @self.pc.on("iceconnectionstatechange")
        async def on_ice_connection_state_change():
            state = self.pc.iceConnectionState
            if state == "checking":
                print_status("ICE Connection State", "🔵 checking")
            elif state == "completed":
                print_status("ICE Connection State", "🟢 completed")
            elif state == "failed":
                print_status("ICE Connection State", "🔴 failed")
            elif state == "closed":
                print_status("ICE Connection State", "⚫ closed")


        @self.pc.on("connectionstatechange")
        async def on_connection_state_change():
            state = self.pc.connectionState
            if state == "connecting":
                print_status("Peer Connection State", "🔵 connecting")
            elif state == "connected":
                self.isConnected= True
                print_status("Peer Connection State", "🟢 connected")
            elif state == "closed":
                self.isConnected= False
                print_status("Peer Connection State", "⚫ closed")
                asyncio.create_task(self.reconnect())
            elif state == "failed":
                print_status("Peer Connection State", "🔴 failed")
                asyncio.create_task(self.reconnect())
        
        @self.pc.on("signalingstatechange")
        async def on_signaling_state_change():
            state = self.pc.signalingState
            if state == "stable":
                print_status("Signaling State", "🟢 stable")
            elif state == "have-local-offer":
                print_status("Signaling State", "🟡 have-local-offer")
            elif state == "have-remote-offer":
                print_status("Signaling State", "🟡 have-remote-offer")
            elif state == "closed":
                print_status("Signaling State", "⚫ closed")
        
        @self.pc.on("track")
        async def on_track(track):
            logging.info("Track recieved: %s", track.kind)

            if track.kind == "video":
                #await for the first frame, #ToDo make the code more nicer
                frame = await track.recv()
                await self.video.track_handler(track)
                
            # Audio without Audio Module leads to a crash!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # if track.kind == "audio":
            #     frame = await track.recv()
            #     while True:
            #         frame = await track.recv()
            #         await self.audio.frame_handler(frame)

        logging.info("Creating offer...")
        await self.wait_for_ip(self.ip)
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        async def try_connection():
            if self.connectionMethod == WebRTCConnectionMethod.Remote:
                peer_answer_json = await self.get_answer_from_remote_peer(self.pc, turn_server_info)
            elif self.connectionMethod == WebRTCConnectionMethod.LocalSTA or self.connectionMethod == WebRTCConnectionMethod.LocalAP:
                peer_answer_json = await self.get_answer_from_local_peer(self.pc, self.ip)

            if peer_answer_json is not None:
                return json.loads(peer_answer_json)
            else:
                print("Could not get SDP from the peer. Check if the Go2 is switched on")
                await try_connection()

            if peer_answer['sdp'] == "reject":
                print("Go2 is connected by another WebRTC client. Close your mobile APP and try again.")
                await try_connection()
                
        peer_answer = await try_connection()
        remote_sdp = RTCSessionDescription(sdp=peer_answer['sdp'], type=peer_answer['type']) 
        await self.pc.setRemoteDescription(remote_sdp)
   
        await self.datachannel.wait_datachannel_open()

    def ip_is_reachable(self, ip: str) -> bool:
        """
        Returns True if the IP responds to a single ping request, False otherwise.
        """
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = ['ping', param, '1', ip]
        return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

    async def wait_for_ip(self, ip: str, interval=3):
        """
        Loop until the IP is reachable via ping. Wait 'interval' seconds between checks.
        """
        while True:
            if self.ip_is_reachable(ip):
                print(f"IP {ip} is now reachable.")
                return
            else:

                print(f"IP {ip} not reachable yet. Retrying in {interval} seconds...")
                await asyncio.sleep(interval)
            
    async def get_answer_from_remote_peer(self, pc, turn_server_info):
        sdp_offer = pc.localDescription

        sdp_offer_json = {
            "id": "",
            "turnserver": turn_server_info,
            "sdp": sdp_offer.sdp,
            "type": sdp_offer.type,
            "token": self.token
        }

        logging.debug("Local SDP created: %s", sdp_offer_json)

        peer_answer_json = send_sdp_to_remote_peer(self.sn, json.dumps(sdp_offer_json), self.token, self.public_key)

        return peer_answer_json

    async def get_answer_from_local_peer(self, pc, ip):
        sdp_offer = pc.localDescription

        sdp_offer_json = {
            "id": "STA_localNetwork" if self.connectionMethod == WebRTCConnectionMethod.LocalSTA else "",
            "sdp": sdp_offer.sdp,
            "type": sdp_offer.type,
            "token": self.token
        }

        peer_answer_json = send_sdp_to_local_peer(ip, json.dumps(sdp_offer_json))

        return peer_answer_json
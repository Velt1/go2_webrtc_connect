#!/bin/bash
set -e
echo "Current directory: $(pwd)"
echo "Environment variables:"
env
echo "Contents of /app/acuda_ac:"
ls -la /app/acuda_ac 
echo "Contents of /app/acuda_ac/go2_webrtc_connect:"
ls -la /app/acuda_ac/go2_webrtc_connect 
. /app/venv/bin/activate 

exec python3 -u /app/acuda_ac/go2_webrtc_connect/main.py
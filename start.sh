#!/bin/bash
set -e
echo "Current directory: $(pwd)"
echo "Environment variables:"
env
echo "Contents of /app/acuda_ac:"
ls -la /app/acuda_ac
. /app/venv/bin/activate

exec python3 main.py
#!/bin/bash
cd "$(dirname "$0")"

# Start ngrok agent connecting to the Cloud Endpoint's internal URL
./ngrok http 8000 --url https://default.internal &
NGROK_PID=$!
echo "Started ngrok agent (PID $NGROK_PID)"

# Wait for ngrok to be ready
for i in {1..10}; do
    if curl -s http://localhost:4040/api/tunnels > /dev/null 2>&1; then
        echo "ngrok connected → https://bonelike-utterless-elwanda.ngrok-free.dev"
        break
    fi
    sleep 1
done

# Cleanup ngrok on exit
trap "kill $NGROK_PID 2>/dev/null; echo 'ngrok stopped'" EXIT

# Start the game server (foreground)
python3 server.py

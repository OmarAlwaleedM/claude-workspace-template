#!/bin/bash
cd "$(dirname "$0")"

# Start ngrok (random URL)
./ngrok http 8000 &
NGROK_PID=$!
echo "Started ngrok agent (PID $NGROK_PID)"

# Wait for ngrok to be ready and detect the public URL
NGROK_PUBLIC_URL=""
for i in {1..10}; do
    NGROK_PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])" 2>/dev/null)
    if [ -n "$NGROK_PUBLIC_URL" ]; then
        echo "ngrok connected → $NGROK_PUBLIC_URL"
        break
    fi
    sleep 1
done

if [ -z "$NGROK_PUBLIC_URL" ]; then
    echo "WARNING: Could not detect ngrok URL. Check http://localhost:4040"
else
    # Update .env with the detected URL
    if grep -q "^NGROK_URL=" .env; then
        sed -i '' "s|^NGROK_URL=.*|NGROK_URL=$NGROK_PUBLIC_URL|" .env
    else
        echo "NGROK_URL=$NGROK_PUBLIC_URL" >> .env
    fi
    echo "Updated .env with NGROK_URL=$NGROK_PUBLIC_URL"
fi

# Cleanup ngrok on exit
trap "kill $NGROK_PID 2>/dev/null; echo 'ngrok stopped'" EXIT

# Start the game server (foreground)
python3 server.py

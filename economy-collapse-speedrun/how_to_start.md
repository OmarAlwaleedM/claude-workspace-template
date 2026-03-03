# How to Start the Game

## Step 1: Open two terminal windows

### Terminal 1 — Start the server
```bash
cd ~/Desktop/claude-code/claude-workspace-template/economy-collapse-speedrun
python3 server.py
```

### Terminal 2 — Start ngrok
```bash
cd ~/Desktop/claude-code/claude-workspace-template/economy-collapse-speedrun
./ngrok http 8000
```

## Step 2: Update the ngrok URL

ngrok gives you a new URL each time (e.g. `https://something.ngrok-free.dev`). Copy it from the ngrok terminal output, then edit `.env`:

```
NGROK_URL=https://your-new-url.ngrok-free.dev
```

## Step 3: Restart the server

Go back to Terminal 1, press `Ctrl+C` to stop, then run `python3 server.py` again so it picks up the new URL.

## Step 4: Open the game

- **Projector:** open `http://localhost:8000` in your browser
- **Students:** scan the QR code on the projector screen with their phones
- **Start:** click "Start Game" once enough players have joined

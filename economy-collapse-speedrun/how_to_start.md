# How to Start the Game

## Quick Start (one command)

```bash
cd ~/Desktop/claude-code/claude-workspace-template/economy-collapse-speedrun
./start.sh
```

This starts ngrok + the game server automatically. The permanent URL is:
**https://bonelike-utterless-elwanda.ngrok-free.dev**

Press `Ctrl+C` to stop everything.

## Step 2: Open the host display

Open `http://localhost:8000` in your browser (this goes on the projector).

## Step 3: Configure settings

The settings screen appears first. Choose:
- **Mode**: Destructive (collapse it) or Constructive (build it)
- **Duration**: 3 / 5 / 7 / 10 minutes
- **Parliament Size**: 3 / 4 / 5 members
- **Proposal Time**: 20 / 30 / 40 seconds
- **Voting Time**: 15 / 20 / 25 seconds
- **Names**: Anonymous or Revealed

Click "Continue to Lobby".

## Step 4: Students join

The QR code appears on the projector. Students scan with their phones, enter a name, and join. You'll see names pop up in the lobby.

## Step 5: Start the game

Click "Start Game" once enough players have joined (minimum 2).

The system randomly assigns parliament members. Everyone sees their role on their phone. The first scenario generates, and the game begins.

## Tips for the Demo

- Test ngrok before class to make sure university WiFi allows it
- Have 5+ players for the best experience (at least 2 parliament + 3 people)
- Use Destructive mode for more laughs
- The AI Reveal at game over is the big payoff — make sure to show it
- If the AI is slow, loading messages will appear. Don't panic.

## Manual Start (fallback)

If `start.sh` doesn't work, run in two terminals:

**Terminal 1:**
```bash
./ngrok http 8000 --url https://default.internal
```

**Terminal 2:**
```bash
python3 server.py
```

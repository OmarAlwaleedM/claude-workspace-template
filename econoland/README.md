# Econoland v2 — Parliament Edition

A live multiplayer political simulation built in Python for a university programming course. A randomly elected "parliament" of students writes policy proposals on their phones (visible character-by-character on the projector), the rest of the class votes, and an AI secretly grades every proposal — revealed only at game over with witty commentary.

## Tech Stack

| Technology | Purpose |
|---|---|
| **Python 3.10+** | Primary language |
| **FastAPI** | Web framework with async support |
| **WebSockets** | Real-time bidirectional communication between server, projector, and phones |
| **OpenRouter API** | LLM access (scenario generation, proposal evaluation, narrative) |
| **httpx** | Async HTTP client for parallel API calls |
| **qrcode** | QR code generation for easy player join |
| **ngrok** | Tunnel localhost through university WiFi |
| **Vanilla HTML/JS** | Two frontend pages (no framework dependencies) |

## Architecture

```
                    ┌─────────────────────────────┐
                    │         server.py            │
                    │   FastAPI + WebSockets       │
                    │   Phase timer management     │
                    │   Async AI task orchestration │
                    └──────────┬──────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
       ┌──────┴──────┐  ┌─────┴──────┐  ┌──────┴──────┐
       │   game.py   │  │   llm.py   │  │  config.py  │
       │ Game state  │  │ AI prompts │  │  Settings   │
       │ Roles/Votes │  │ API calls  │  │  Constants  │
       │ Scoring     │  │ Fallbacks  │  └─────────────┘
       └──────┬──────┘  └────────────┘
              │
       ┌──────┴──────┐
       │ economy.py  │
       │ 6 indicators│
       │ 0-100 scale │
       └─────────────┘

WebSocket connections:
  /ws/host           → host.html (projector display)
  /ws/player/{name}  → player.html (phone UI, role-based)
```

## File Structure

```
├── server.py          # FastAPI server, WebSocket handlers, phase orchestration
├── game.py            # Game state, roles, proposals, voting, scoring, history
├── economy.py         # Economy model (6 indicators on 0-100 scale)
├── llm.py             # LLM prompts, API calls, fallback scenarios
├── config.py          # Environment config + GameSettings dataclass
├── static/
│   ├── host.html      # Projector display (settings → lobby → game → game over)
│   └── player.html    # Phone UI (role-based: parliament writes / people vote)
├── start.sh           # One-command startup script (ngrok + server)
├── requirements.txt   # Python dependencies
├── .env.example       # Template for environment variables
└── .gitignore
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your OpenRouter API key
```

Get a free API key from [openrouter.ai](https://openrouter.ai/).

### 3. Start the game

**One command (recommended):**
```bash
./start.sh
```
This auto-starts ngrok, detects the public URL, updates `.env`, and launches the server.

**Manual start (if start.sh doesn't work):**

Terminal 1:
```bash
./ngrok http 8000
# Copy the https://... URL from ngrok output
```

Terminal 2:
```bash
# Update NGROK_URL in .env with the URL from ngrok
python3 server.py
```

### 4. Play

1. Open `http://localhost:8000` on the projector (host display)
2. Configure settings: mode, rounds, parliament size, timers
3. Click "Continue to Lobby" — QR code appears
4. Students scan QR code on their phones, enter a name, join
5. Click "Start Game" when everyone's in

## How It Works

### Game Flow

1. **Settings** → Host configures game mode, rounds, timers
2. **Lobby** → QR code on projector, students join on phones
3. **Role Assignment** → System randomly picks parliament members
4. **Rounds** (repeat 3/5/7 times):
   - **Writing Phase**: AI-generated scenario appears. Parliament types proposals live (visible on projector). Timer counts down.
   - **Voting Phase**: Proposals lock. People vote via numbered buttons on their phones. AI grades proposals in parallel (hidden).
   - **Results**: Winning policy shown, economy indicators update.
5. **Game Over** → AI Reveal (hidden scores + commentary) → Leaderboards → Awards → Satirical narrative

### Two Modes

- **Destructive** (default): Parliament tries to collapse the economy as fast as possible. Anonymous proposals. Dark humor.
- **Constructive**: Parliament tries to save the economy. Names revealed. Thoughtful policies rewarded.

### Scoring

- **Parliament members**: Ranked by total votes received across all rounds (popularity)
- **The People**: Ranked by cumulative AI quality of proposals they voted for (judgment — revealed only at game over)

### Key Technical Features

- **Real-time keystroke streaming**: Parliament proposals appear character-by-character on the projector via WebSockets
- **Parallel AI calls**: Scenario generation and proposal grading run as async background tasks during human activity phases, minimizing wait times
- **Automatic reconnection**: Players who disconnect can rejoin mid-game
- **Fallback scenarios**: If the AI fails, pre-written scenarios ensure the game continues
- **Tiebreaker voting**: Tied proposals trigger an instant runoff vote

## Demo Tips

- Test ngrok before class to make sure university WiFi allows it
- Have 5+ players for the best experience (at least 2 parliament + 3 people)
- Use Destructive mode for more laughs
- The AI Reveal at game over is the main payoff — show it on the projector
- If the AI is slow, loading messages will appear automatically

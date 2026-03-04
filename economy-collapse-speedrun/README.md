# Economy Collapse Speedrun v2 — Parliament Edition

A live multiplayer political simulation for classrooms. A randomly elected parliament writes policy proposals on their phones (visible live on the projector), the rest of the class votes, and an AI secretly grades every proposal — revealed at game over.

## Quick Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure `.env`
```bash
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=x-ai/grok-4.1-fast
NGROK_URL=https://your-ngrok-url.ngrok-free.dev
```

### 3. Start ngrok (separate terminal)
```bash
./ngrok http 8000
```
Copy the public URL and paste it into `.env` as `NGROK_URL`.

### 4. Start the server
```bash
python3 server.py
```

### 5. Play
- Open `http://localhost:8000` on the projector (host display)
- Configure settings (mode, duration, parliament size, timers)
- Click "Continue to Lobby" — QR code appears
- Students scan the QR code on their phones
- Click "Start Game" when everyone's joined

## How It Works

### Roles
- **Parliament** (3-5 random students): Write policy proposals each round (200 char max, live on projector)
- **The People** (everyone else): Vote on proposals using numbered buttons on their phone

### Each Round
1. **Writing Phase**: Scenario appears. Parliament types proposals (visible char by char on projector). Copy disclaimer shown.
2. **Voting Phase**: Proposals lock. People vote via numbered buttons (read text from projector). AI grades in parallel.
3. **Results**: Winner shown, economy updates, AI generates next scenario in parallel.

### Game Over
- AI Reveal: Every proposal from every round shown with hidden AI scores + witty commentary
- Parliament Leaderboard (by votes received)
- People Leaderboard (by cumulative AI quality of proposals they voted for)
- Awards (Supreme Dictator / President, Minister of Chaos / Chief Advisor, The Whistleblower)
- Satirical AI-generated narrative summary

### Two Modes
- **Destructive** (default): Collapse the economy. Anonymous by default. Dark humor.
- **Constructive**: Build the best economy. Names revealed by default. Thoughtful policies.

## File Structure
```
├── server.py          # FastAPI + WebSockets, phase management, parallel AI calls
├── game.py            # Game state, roles, proposals, voting, scoring, history
├── economy.py         # Economy model (6 indicators, 0-100)
├── llm.py             # OpenRouter: scenario gen + proposal evaluation + narrative
├── config.py          # Settings + GameSettings dataclass
├── static/
│   ├── host.html      # Projector display (settings → lobby → game → game over)
│   └── player.html    # Phone UI (role-based: parliament input / people voting)
├── .env               # API key, model, ngrok URL
├── requirements.txt   # Python dependencies
└── ngrok              # ngrok binary
```

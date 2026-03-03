# Economy Collapse Speedrun

A live multiplayer economy simulation where your class votes on absurd policies to destroy a fictional economy as fast as possible. Played on a projector with phones as controllers.

## Quick Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure `.env`
```bash
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=x-ai/grok-3-mini-beta
NGROK_URL=https://your-ngrok-url.ngrok-free.app
```

### 3. Start ngrok (in a separate terminal)
```bash
ngrok http 8000
```
Copy the public URL and paste it into `.env` as `NGROK_URL`.

### 4. Start the server
```bash
python server.py
```

### 5. Play
- Open `http://localhost:8000` on the projector (host display)
- Students scan the QR code on their phones
- Click "Start Game" when everyone's joined
- Vote, watch the economy crumble, laugh

## How It Works
- **Host screen** (projector): Shows economy dashboard, scenarios, news ticker, vote counts
- **Player screen** (phone): Join via QR, vote on policies each round
- **LLM**: Generates scenarios via OpenRouter (Grok) that compound on every previous decision
- **Scoring**: Individual scores based on your votes. MVP Destroyer = most destructive. Boy Scout = tried to save it.

## Game Duration
Default 5 minutes. The game ends when time runs out or the economy collapses (GDP or Employment < 10).

# Plan: Economy Collapse Speedrun

**Created:** 2026-03-03
**Status:** Approved — ready to build
**Presentation:** Tomorrow (March 4, 2026)

---

## 1. Game Overview

A live economy simulation projected on a big screen where the whole class votes on absurd economic policies to collectively destroy a fictional economy as fast as possible. Players join via QR code on their phones. The projector shows a live dashboard with economic indicators crumbling in real time. An LLM generates every scenario in real time, compounding on previous choices and weaving in current world events. Scoring is cumulative — leaderboard and awards only at the end.

### What Makes It Different From Kahoot

- **Living simulation**: The projector shows a real-time economy dashboard that visibly deteriorates. Print money in round 2, face hyperinflation by round 5.
- **Projector is the show**: Phone is just a remote. The entertainment is watching graphs nosedive, news tickers go haywire, indicators turn red.
- **Social dynamics**: Majority rules — the class sees vote distribution. 80% picking the unhinged option while 3 people try to save it = inherently funny.
- **Narrative continuity**: The LLM remembers everything. Legalize drug trade in round 1? Round 3's headline references the booming cocaine industry. The story compounds.
- **Adapts to the class**: If the class picks responsible options, the LLM stays tame. If they go unhinged, the scenarios get progressively more absurd to match. The AI mirrors the room's energy.
- **Current events**: Scenarios weave in real-world headlines (Trump buying Greenland, Iran situation, Maduro) twisted through the lens of the fictional economy.

---

## 2. Game Flow

### Setup Phase (~1 min)
1. Omar launches game on laptop → connects to projector
2. Host screen shows QR code (ngrok public URL)
3. Students scan QR → enter name → land in waiting lobby
4. Host screen shows names appearing live ("12 players joined...")
5. Omar clicks Start Game

### Game Phase (configurable: 5-10 min)
1. Host screen shows: live economy dashboard (6 indicators as animated bars) + news ticker + scenario headline + countdown timer
2. LLM generates the scenario + 4 options based on current economy state, all previous decisions, and current events
3. Players see 4 options on phone, tap to vote. Timer skips ahead if everyone has voted.
4. Results revealed on projector: vote distribution bar chart, winning policy enacted
5. Economy dashboard updates live — bars shift, indicators change color
6. LLM generates next scenario that compounds on everything that just happened. Repeat.

### End Phase (~30 sec)
1. "ECONOMY COLLAPSED" or "ECONOMY SURVIVED" screen
2. Final class destruction score
3. Awards: MVP Destroyer (most negative score) + The Boy Scout (most positive score — tried to save it)

---

## 3. Design Decisions

| Decision | Choice |
| -------- | ------ |
| Scenario generation | **LLM-generated via OpenRouter** (Gemini or Grok — fast + cheap). Each scenario builds on all previous choices + current economy state + real-world events. |
| Compounding | Scenarios explicitly reference and build on previous decisions. Legalize something in round 1 → it's now part of the economy in round 2+. |
| Current events | System prompt includes real-world context (Trump/Greenland, Iran bombings, Maduro/Venezuela, etc.) so scenarios feel grounded and topical. |
| Adaptive tone | LLM mirrors the class's energy. Responsible picks → tamer scenarios. Unhinged picks → progressively more absurd scenarios. |
| Early vote skip | If all players voted, skip remaining countdown immediately |
| Scoring | Cumulative across all rounds. Economy dashboard live, individual leaderboard only at end. |
| Networking | ngrok tunnel (free tier) — university WiFi is strict |
| Timer | Host sets total game duration before starting |
| Off-limits | No rape, no trashing religions, no slurs, no real atrocities. Enforced in system prompt. |
| Fallback | Pre-cache 3-5 emergency scenarios at game start in case the API is slow mid-game |

---

## 4. Technical Architecture

### File Structure
```
economy-collapse-speedrun/
├── server.py              # FastAPI server — all endpoints + WebSockets
├── game.py                # Game state: rounds, timer, voting, scoring
├── economy.py             # Economy model: 6 indicators, impact logic
├── llm.py                 # OpenRouter API integration — scenario generation
├── config.py              # Settings: duration, round time, API key, model
├── static/
│   ├── host.html          # Projector page: dashboard + scenarios + results
│   └── player.html        # Phone page: join + vote
├── .env                   # API key + ngrok URL (not committed)
├── requirements.txt
└── README.md
```

### Tech Stack
| Component | Choice |
| --------- | ------ |
| Web framework | FastAPI (async, WebSocket built-in) |
| Real-time | WebSockets |
| Frontend | Vanilla HTML/JS (2 pages) |
| QR code | qrcode Python library |
| Tunneling | ngrok free tier |
| LLM | OpenRouter API → Gemini or Grok (fast, cheap) |
| HTTP client | httpx (async, for non-blocking LLM calls) |

### Endpoints
| Endpoint | Type | Purpose |
| -------- | ---- | ------- |
| `GET /` | HTTP | Host/projector display page |
| `GET /play` | HTTP | Player phone page |
| `GET /qr` | HTTP | QR code image (points to ngrok URL + /play) |
| `WS /ws/host` | WebSocket | Pushes game state to projector in real time |
| `WS /ws/player/{name}` | WebSocket | Sends scenarios to player, receives votes |
| `POST /start` | HTTP | Host starts the game with config (duration, etc.) |

### Dependencies
```
fastapi
uvicorn[standard]
websockets
qrcode[pil]
httpx
python-dotenv
```
Plus ngrok CLI installed separately (free, not a Python package).

---

## 5. Economy Model

Six indicators, each 0-100, shown as live gauges on the projector:

| Indicator | Start | Meaning | Direction |
| --------- | ----- | ------- | --------- |
| GDP | 75 | Economic output | Higher = better |
| Employment | 80 | Job market health | Higher = better |
| Inflation | 20 | Price instability | Lower = better |
| Public Trust | 70 | Citizen confidence | Higher = better |
| Trade Balance | 60 | Import/export health | Higher = better |
| National Debt | 30 | Debt burden | Lower = better |

The LLM generates both the scenario text AND the numerical impacts for each option. Example output from LLM:
```json
{
  "headline": "Cocaine Is Now 40% of GDP. The Minister of Finance Did a Line on Live TV.",
  "description": "After last round's legalization of the drug trade, the economy has pivoted entirely to narcotics. International investors are concerned. The Finance Minister is not.",
  "news_ticker": ["BREAKING: Peso replaced by cocaine-backed currency", "Wall Street: 'We've seen worse'", "Tourism up 300% for 'interesting' reasons"],
  "options": [
    {"label": "A", "text": "Regulate the drug industry and impose sin taxes", "impacts": {"gdp": 5, "employment": 3, "inflation": -2, "public_trust": 10, "trade_balance": 5, "national_debt": -5}, "destruction_points": 10},
    {"label": "B", "text": "Government becomes the sole drug dealer — nationalize the cartel", "impacts": {"gdp": -5, "employment": -10, "inflation": 10, "public_trust": -15, "trade_balance": -5, "national_debt": 10}, "destruction_points": -20},
    {"label": "C", "text": "Make cocaine the official currency. 1 gram = 1 dollar.", "impacts": {"gdp": -20, "employment": -5, "inflation": 30, "public_trust": -25, "trade_balance": -15, "national_debt": 20}, "destruction_points": -35},
    {"label": "D", "text": "Declare the drug trade was actually a social experiment and ban everything again", "impacts": {"gdp": -10, "employment": -15, "inflation": 5, "public_trust": -10, "trade_balance": 0, "national_debt": 5}, "destruction_points": -15}
  ]
}
```

When a policy wins (majority vote), its impacts are applied to the economy. Indicators are clamped to 0-100.

**Destruction Score** = cumulative sum of destruction_points from all enacted policies.

---

## 6. LLM Integration (llm.py)

### OpenRouter API Call

Uses httpx (async) to call OpenRouter. Non-blocking so the server doesn't freeze waiting for a response.

```python
async def generate_scenario(economy_state, policy_history, round_number) -> dict:
    # Build prompt with full context
    # Call OpenRouter API
    # Parse JSON response
    # Validate structure (all fields present, impacts are integers, etc.)
    # Return scenario dict
```

### System Prompt

```
You are the scenario generator for "Economy Collapse Speedrun," a live multiplayer
game where university economics students collectively vote on policies to (intentionally)
destroy a fictional economy as fast as possible.

CURRENT ECONOMY STATE:
{economy_state_json}

FULL POLICY HISTORY (every policy enacted so far, in order):
{policy_history_json}

ROUND NUMBER: {round_number}

REAL-WORLD CONTEXT (use these for inspiration, twist them into the fictional economy):
- The US and Israel have been bombing Iran
- The Maduro scandal in Venezuela
- Trump has expressed interest in buying Greenland
- Ongoing global trade tensions and tariff wars
- AI disruption across industries
(Feel free to reference or satirize any current 2025-2026 world events)

Generate the next scenario. You MUST return valid JSON only, no other text:

{
  "headline": "A short punchy news headline about the current crisis (1 sentence, max 15 words)",
  "description": "2-sentence description of what's happening. MUST reference and build on previous policies — the economy has been shaped by every past decision.",
  "news_ticker": ["3-5 short fake news headlines/tweets that are funny, satirical commentary on the state of the economy. Mix in references to real-world events twisted through the game's lens."],
  "options": [
    {
      "label": "A",
      "text": "The responsible option (boring, textbook, what a real economist would say)",
      "impacts": {"gdp": X, "employment": X, "inflation": X, "public_trust": X, "trade_balance": X, "national_debt": X},
      "destruction_points": X
    },
    {
      "label": "B",
      "text": "The corrupt/greedy option (self-serving, what a cartoon villain politician would do)",
      "impacts": {...},
      "destruction_points": X
    },
    {
      "label": "C",
      "text": "The unhinged option (absurd, chaotic, should make 20-year-olds laugh out loud)",
      "impacts": {...},
      "destruction_points": X
    },
    {
      "label": "D",
      "text": "The wildcard (creative, unexpected, could be weirdly genius or catastrophically stupid)",
      "impacts": {...},
      "destruction_points": X
    }
  ]
}

TONE RULES:
- You're writing for 20-year-old economics students. Be witty, not edgelord.
- Think "satirical Economist article" meets "Cards Against Humanity."
- Absurdist humor > shock value. "Abolish weekdays" beats generic edginess.
- Twist real economic concepts: "quantitative easing" → "quantitative squeezing,"
  "trickle-down" → "trickle-sideways economics."
- Dark and irreverent is fine: The Purge, dystopian scenarios, corporate greed, absurd
  bureaucracy, corrupt governments.
- ADAPT TO THE PLAYERS: if they've been picking responsible options, keep it moderate.
  If they've been picking unhinged options, escalate the absurdity to match their energy.
  Mirror the room.
- Scenarios MUST compound. If they legalized something, it's now part of the economy.
  If they printed money, inflation should be spiraling. Every round builds on every
  previous decision. Never ignore what happened before.
- The news_ticker entries should feel like satirical tweets or breaking news chyrons.
  Mix game events with twisted real-world references.

HARD RED LINES — NEVER include:
- Sexual violence or rape references
- Mocking or attacking any specific religion
- Racial/ethnic/gender slurs
- References to real-world genocides or atrocities
- Content that would get a student reported to a university dean

IMPACT RULES:
- destruction_points: negative for destructive (A: +5 to +15, B: -10 to -25, C: -20 to -40, D: -30 to +10)
- Impact values: integers between -30 and +30
- Make impacts economically plausible-ish (printing money → inflation up, GDP short-term up)
- The economy should feel like it's responding to real forces, even absurd ones
```

### Pre-caching Strategy

To avoid awkward pauses mid-game:
- When the game starts, immediately generate the first scenario AND pre-generate a second one in the background
- After each round's votes come in, start generating the next scenario immediately while showing results
- Keep 1 pre-cached scenario as emergency fallback
- If the API is slow (>5 seconds), show a "The economy is processing your terrible decisions..." loading message

### Error Handling

- If API call fails: retry once, then use the pre-cached fallback scenario
- If JSON parsing fails: retry with a "Return ONLY valid JSON" nudge
- If response is missing fields: fill defaults and log warning
- Timeout: 8 seconds max per request, then fall back

---

## 7. Scoring System

### Per-Player (cumulative, revealed at end)
- Each round: player earns destruction_points of whichever option they personally voted for
- More negative total = better destroyer = winning the game
- Positive total = tried to save the economy = "losing" but gets the Boy Scout award

### Class-Wide (live on projector)
- Winning policy = most votes each round (majority rules)
- Economy indicators update based on winning policy only
- Class destruction score = sum of all enacted policies' destruction_points
- Displayed live on the dashboard

### End-of-Game Awards
- **MVP Destroyer**: lowest individual cumulative score
- **The Boy Scout**: highest individual cumulative score

---

## 8. Step-by-Step Build Guide

This is the exact sequence to build this project from scratch.

---

### Step 1: Project Setup

**Goal:** Empty project with all files created and dependencies installable.

1. Create the directory: `economy-collapse-speedrun/`
2. Create all files from the file structure (empty or with boilerplate)
3. Write `requirements.txt`:
   ```
   fastapi
   uvicorn[standard]
   websockets
   qrcode[pil]
   httpx
   python-dotenv
   ```
4. Create `.env` file:
   ```
   OPENROUTER_API_KEY=your_key_here
   NGROK_URL=https://your-ngrok-url.ngrok-free.app
   OPENROUTER_MODEL=google/gemini-2.0-flash-001
   ```
5. Run `pip install -r requirements.txt`

**Verify:** `python -c "import fastapi, uvicorn, qrcode, httpx"` runs clean.

---

### Step 2: Config Module (config.py)

**Goal:** Central place for all game settings, loaded from .env where needed.

Build a config that contains:
- `ROUND_TIME_SECONDS` = 20
- `GAME_DURATION_SECONDS` = 300 (default 5 min, configurable at start)
- `MIN_PLAYERS` = 2
- `HOST` = "0.0.0.0"
- `PORT` = 8000
- `OPENROUTER_API_KEY` (from .env)
- `OPENROUTER_MODEL` (from .env, default "google/gemini-2.0-flash-001")
- `NGROK_URL` (from .env)
- Economy starting values: GDP=75, Employment=80, Inflation=20, Public_Trust=70, Trade_Balance=60, National_Debt=30

**Verify:** Import config, confirm all values load including .env variables.

---

### Step 3: Economy Model (economy.py)

**Goal:** A class that holds the 6 indicators and applies policy impacts.

Build an `Economy` class:
- `__init__`: set all 6 indicators to starting values from config
- `apply_policy(impacts: dict)`: add each impact to corresponding indicator, clamp 0-100
- `get_state() -> dict`: return current values of all 6 indicators
- `get_destruction_score() -> int`: return cumulative destruction points
- `add_destruction_points(points: int)`: add to running total
- `is_collapsed() -> bool`: True if GDP < 10 or Employment < 10

**Verify:** Create economy, apply impacts, confirm clamping and score tracking work.

---

### Step 4: LLM Integration (llm.py)

**Goal:** Async function that calls OpenRouter and returns a validated scenario dict.

Build:
- `SYSTEM_PROMPT`: the full system prompt from section 6 above (with placeholders for economy state, history, round number)
- `async def generate_scenario(economy_state: dict, policy_history: list, round_number: int) -> dict`:
  1. Format the system prompt with current state, full policy history, round number
  2. Call OpenRouter API via httpx (async POST to `https://openrouter.ai/api/v1/chat/completions`)
  3. Parse JSON from the response
  4. Validate: check all required fields exist, impacts are integers, destruction_points present
  5. Return the scenario dict
- `def validate_scenario(data: dict) -> dict`: check structure, fill defaults for missing fields
- Error handling: retry once on failure, 8-second timeout, raise exception if all fails

**Verify:** Call `generate_scenario()` with sample economy state and empty history. Confirm valid JSON comes back with all fields.

---

### Step 5: Game State Manager (game.py)

**Goal:** The brain — manages rounds, votes, scores, time, and LLM calls.

Build a `Game` class:
- `__init__(duration_seconds)`: create Economy, player dict, round counter, vote history (list of all enacted policies), policy_history (list of text descriptions for LLM context), game timer
- `add_player(name) -> bool`: add player, return False if game started
- `remove_player(name)`: remove player
- `async start_game()`: mark active, record start time, call LLM to generate first scenario (+ pre-cache second one in background)
- `get_current_scenario() -> dict`: return scenario WITHOUT destruction_points (players shouldn't see point values)
- `submit_vote(player_name, option_label)`: record vote
- `all_voted() -> bool`: check if all active players voted
- `async end_round() -> dict`: tally votes, determine majority winner, apply impacts to economy, update player scores, start generating next scenario in background. Return round results dict.
- `is_game_over() -> bool`: elapsed time >= duration OR economy collapsed
- `get_final_results() -> dict`: class destruction score, per-player scores sorted, MVP Destroyer, Boy Scout, final economy state

Player score tracking:
- `player_scores`: dict of player name → cumulative destruction_points
- Each round, every player gets the points of their individual vote (not the winning policy)

Pre-caching:
- After generating a scenario, immediately start generating the next one in background (using a plausible "if they pick the most popular option type" assumption)
- When actual results come in, if the pre-cached scenario's context is close enough, use it; otherwise regenerate

**Verify:** Simulate full game programmatically with mocked LLM responses. Confirm scores, economy state, and game-over logic.

---

### Step 6: FastAPI Server (server.py)

**Goal:** HTTP endpoints + WebSocket connections for host and players.

Build:
- **Global game instance**: single `Game` object
- **Static file serving**: mount `/static`

HTTP Endpoints:
- `GET /` → serve `static/host.html`
- `GET /play` → serve `static/player.html`
- `GET /qr` → generate QR code (ngrok URL + `/play`), return as PNG
- `POST /start` → accept `{"duration": 300}`, call `game.start_game()`, broadcast first scenario
- `GET /state` → return current game state as JSON (debug)

WebSocket — `WS /ws/host`:
- On connect: send current state
- Receives pushes: lobby updates, round start (scenario + economy), vote updates (live count), round end (results + new economy state), game over (final results)

WebSocket — `WS /ws/player/{name}`:
- On connect: register player, send lobby status
- On game start: send scenario (4 options, no point values)
- On message (vote): record vote, broadcast count to host. If `all_voted()`, trigger `end_round()`.
- On round end: send next scenario
- On game over: send personal final results (score, rank, award)

Broadcast helpers:
- `broadcast_to_host(data)` and `broadcast_to_players(data)`
- Keep sets of connected WebSockets

Game timer:
- On start: launch async background task, check elapsed time every second
- Push timer updates to host every second
- On time up: trigger game over, broadcast to all

Loading state:
- If LLM is still generating when round needs to advance, send a `{"type": "loading", "message": "The economy is processing your terrible decisions..."}` to both host and players

**Verify:** Start server, open both pages in browser, confirm WebSocket connections work and messages flow.

---

### Step 7: Host Display — Projector Page (static/host.html)

**Goal:** Single HTML file (embedded CSS + JS) — the star of the show on the projector.

Layout (no scrolling, designed for a projector screen):
- **Top bar**: "ECONOMY COLLAPSE SPEEDRUN" title + countdown timer + class destruction score
- **Main left (60%)**: Economy dashboard — 6 horizontal bars with labels. Color transitions: green (healthy) → yellow (concerning) → red (critical). CSS transitions for smooth animation when values change.
- **Main right (40%)**: Current scenario panel — headline, description. During voting: live vote count bars for each option (A/B/C/D) updating in real time as votes come in.
- **Bottom strip**: Scrolling news ticker — headlines from the LLM's `news_ticker` field, scrolling left continuously via CSS animation.

Overlay states (full-screen overlays that appear/disappear):
- **Lobby**: Big centered QR code + "Scan to join!" + player count + names appearing
- **Loading**: "The economy is processing your terrible decisions..." (while LLM generates)
- **Round results**: Vote distribution + winning policy highlighted + economy impact (before/after)
- **Game over**: "ECONOMY COLLAPSED" / "ECONOMY SURVIVED" + final score + MVP Destroyer + Boy Scout

JS Logic:
- Connect to WebSocket on page load
- Handle message types: `lobby_update`, `round_start`, `vote_update`, `round_end`, `loading`, `game_over`
- Animate bar changes with CSS transitions (~1 sec)
- News ticker: CSS `@keyframes` scrolling

**Verify:** Open in browser, send test WebSocket messages, confirm all states render and animate.

---

### Step 8: Player Voting Page — Phone UI (static/player.html)

**Goal:** Single HTML file, mobile-optimized. Dead simple: join → vote → wait → repeat → results.

Layout (mobile-first, big touch targets):
- **Join screen**: Name input + "Join Game" button → "Waiting for host to start..."
- **Voting screen**: Scenario headline (short). 4 large buttons (A/B/C/D) with option text. Color-coded: A=green, B=yellow, C=red, D=purple. Timer visible. After voting: "Vote submitted! Waiting..."
- **Loading screen**: "Next scenario loading..." (when LLM is generating)
- **Between rounds**: "Policy enacted: [winning policy text]"
- **Game over**: Your final score + rank + award (if any)

JS Logic:
- Connect to WebSocket with player name
- Handle: `game_start`, `new_round`, `vote_update`, `round_result`, `loading`, `game_over`
- On button click: send `{"vote": "C"}`, disable all buttons
- Minimal — fast load, no fancy animations

**Verify:** Open on phone via ngrok, join and vote, confirm full flow works.

---

### Step 9: QR Code + ngrok Setup

**Goal:** Players scan QR on projector → land on voting page via public URL.

1. Install ngrok (free): download from ngrok.com, sign up for free account
2. Start game server: `uvicorn server:app --host 0.0.0.0 --port 8000`
3. Start tunnel: `ngrok http 8000` → get URL like `https://abc123.ngrok-free.app`
4. Set `NGROK_URL` in `.env` to that URL
5. Restart server (or make it read URL dynamically)
6. `/qr` endpoint generates QR pointing to `{NGROK_URL}/play`
7. Host page shows QR during lobby

**Verify:** Scan QR with phone on mobile data (not WiFi). Player page loads.

---

### Step 10: LLM Prompt Testing

**Goal:** Verify the LLM generates good scenarios before the live demo.

1. Run 5-10 rounds of scenario generation with the system prompt
2. Check: are scenarios funny? Do they compound properly? Do news ticker entries land?
3. Check: are options balanced (responsible/corrupt/unhinged/wildcard)?
4. Check: are impacts reasonable? Does the economy react sensibly?
5. Check: any content that crosses red lines? Adjust system prompt if needed.
6. Check response times — is the model fast enough? (<3 seconds ideal, <5 acceptable)
7. Try both Gemini and Grok, pick whichever is faster and funnier
8. If response quality is inconsistent, add "Return ONLY valid JSON" reinforcement

**Verify:** 10 consecutive rounds produce valid, funny, compounding scenarios with no red-line violations.

---

### Step 11: Integration Testing

**Goal:** Full end-to-end test simulating a real demo.

1. Start server + ngrok
2. Open host page on laptop
3. Join with 2-3 phones via QR code
4. Start game with 2-minute duration
5. Play through several rounds:
   - Confirm LLM scenarios load and display on both screens
   - Confirm scenarios reference previous decisions (compounding works)
   - Confirm voting works and early-skip triggers when all voted
   - Confirm economy dashboard animates
   - Confirm news ticker scrolls LLM-generated headlines
   - Confirm loading state appears if LLM is slow
   - Confirm timer counts down
6. Let game end, verify:
   - Final scores correct
   - MVP Destroyer and Boy Scout awards correct
   - Both screens show game-over state

Fix any bugs.

---

### Step 12: Demo Rehearsal

**Goal:** Full dry run of the presentation.

1. Set up: laptop → projector → ngrok → QR code
2. At least one phone joins
3. Practice intro: "This is Economy Collapse Speedrun. Scan the QR code. Your goal: destroy this economy as fast as possible."
4. Run 2-3 rounds
5. Time it — fits in ~5 minutes?
6. Note rough edges

---

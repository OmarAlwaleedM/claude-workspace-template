# Econoland: Parliament Edition — Presentation Brief

> **This document is a self-contained brief for an AI to generate a polished PowerPoint presentation.** It includes everything needed: project context, audience details, grading criteria, the full game design, code architecture, actual code snippets, slide-by-slide content, speaker notes, and visual suggestions. Read the entire document before generating slides.

---

## Part 1: Context & Background

### Who Is Presenting

Omar, 20 years old, economics student at a university in the Middle East. This is a **final project** for a **Python programming course**. Omar and his group built the project. He needs to present it live to the class and demo it.

### The Assignment

- Build a working Python program and demo it live to the class
- **Total presentation time:** 10 minutes (~5 minutes slides + ~5 minutes live demo)
- The project should demonstrate Python programming skills learned in the course
- **Group project** (2-3 members — speaker names should be left as placeholders like [Speaker 1], [Speaker 2], etc.)

### The Audience

- **~20 economics students** (ages 18-22) — they know economics but are beginner-to-intermediate Python programmers
- **1 professor** (age 45-50) — grading the project, looking for technical substance, clean code, and a good presentation
- The audience is tech-aware but not software engineers — explain concepts accessibly
- They will participate in the live demo (joining on their phones), so get them excited

### Grading Criteria (What the Professor Cares About)

| Category | Weight | What Scores Full Marks |
|----------|--------|----------------------|
| **Code Quality & Functionality** | 30% | Clean code, docstrings on every function, visible error handling (try/except), organized module structure, proper use of data structures |
| **Topic & Complexity** | 30% | Ambitious project that goes beyond basics, real-world relevance, multiple interacting systems |
| **Presentation** | 20% | Clear explanation, good slides, engaging delivery, live demo |
| **Creativity & Innovation** | 20% | Original concept, creative application of programming to a real problem |

### The "Python vs HTML" Issue

The course requirement says the project should be "entirely in Python." This project uses two HTML files for the UI (host.html and player.html). **This must be framed correctly:**

- **Python IS the entire project.** 5 Python modules, 2000+ lines of Python code
- The HTML files are just thin display layers — like a monitor or TV screen. They contain zero game logic
- ALL game state, player management, round flow, AI integration, scoring, voting, networking, and real-time communication runs in Python
- The HTML just renders what Python sends via WebSocket — it's equivalent to using `print()` but in a browser
- **Analogy for the professor:** "The HTML is like a TV screen — it displays the picture, but all the intelligence is in the camera, the studio, and the broadcast equipment. Our Python server is all of that."

### Presentation Style Guidelines

- **Clean, modern, professional** — not overly corporate or boring
- **Dark theme preferred** (dark background, light text, accent colors)
- Keep text minimal on slides — bullet points, not paragraphs
- Use code snippets on the technical slides (actual Python code from the project)
- Diagrams/flowcharts for architecture and game flow
- **No clip art or stock photos** — use clean graphics, icons, or actual screenshots
- The tone should match university students: smart, slightly informal, confident

---

## Part 2: The Project in Full Detail

### What Is Econoland?

Econoland: Parliament Edition is a **live multiplayer political economy simulation** where the entire class participates in real-time using their phones. Here's how it works:

1. **The setup:** Omar's laptop runs a Python server. A projector shows the host screen. Students scan a QR code to join on their phones.
2. **Parliament is chosen:** The system randomly picks 3-5 students to be "Parliament." Everyone else becomes "The People."
3. **Each round:**
   - An AI generates an economic crisis scenario (e.g., "Econoland's Currency Crashes 50%")
   - Parliament members write policy proposals on their phones (200 char max). **Their typing appears live on the projector, character by character** — everyone watches them write in real-time
   - When time's up, The People vote on which proposal to enact using numbered buttons on their phones
   - **While humans vote, the AI secretly grades every proposal** in the background (quality score, economic impacts, witty commentary) — nobody sees these scores until game over
   - The winning policy's impacts are applied to the economy (6 indicators change)
4. **Game over:** After all rounds (or economy collapse), the AI reveal happens:
   - Every proposal from every round gets its hidden AI score and commentary revealed on the big screen
   - Parliament leaderboard (who got the most votes = most popular politician)
   - People leaderboard (who voted for the highest-quality proposals = best judgment)
   - Fun awards (Supreme Dictator, Whistleblower, etc.)
   - AI generates a satirical news anchor narrative summarizing the whole game

### Two Game Modes

| | Constructive Mode | Destructive Mode |
|---|---|---|
| **Goal** | Save the economy | Crash the economy as fast as possible |
| **Parliament names** | Revealed (accountability) | Anonymous (chaos) |
| **AI tone** | Encouraging, rewards smart policy | Sarcastic, rewards creative destruction |
| **Scoring** | Prosperity points | Destruction points |
| **Vibe** | Serious economics simulation | Hilarious chaos simulator |

### Why This Project Is Impressive (For the Professor)

1. **Real-time multiplayer networking** — WebSockets with 20+ concurrent phone connections
2. **AI integration** — 3 different LLM prompts, parallel execution, fallback systems
3. **State machine architecture** — phase management preventing invalid actions
4. **Async programming** — concurrent AI calls during human activity (grading while voting)
5. **Clean code** — 5 modules, 50+ functions, every function has a docstring, proper error handling
6. **Data structures** — dictionaries, lists, dataclasses, typed parameters
7. **Real-world relevance** — economics simulation for economics students

---

## Part 3: Technical Architecture

### Module Map (5 Python Files)

```
economy-collapse-speedrun/
  config.py    (78 lines)  — Environment variables, constants, GameSettings dataclass
  economy.py   (67 lines)  — Economy model: 6 indicators, policy application, clamping
  game.py      (593 lines) — Core game state: players, roles, rounds, voting, scoring, history
  llm.py       (540 lines) — AI integration: scenario gen, proposal eval, narrative, fallbacks
  server.py    (827 lines) — FastAPI server: WebSockets, HTTP endpoints, phase orchestration
  ─────────────────────────
  Total: ~2,105 lines of Python
```

### How the Modules Connect

```
config.py ──────────────────────────────────┐
    │ (constants, settings)                 │
    ▼                                       │
economy.py                                  │
    │ (Economy class)                       │
    ▼                                       │
game.py                                     │
    │ (Game class — uses Economy, Config)    │
    ▼                                       │
server.py ◄────────── llm.py ◄──────────────┘
    │ (orchestrates everything)    (AI calls use config)
    │
    ├──► /ws/host     → Projector display
    └──► /ws/player/  → Player phones
```

### Key Architecture Decisions (Worth Mentioning in Presentation)

1. **Separation of concerns:** Economy knows nothing about players. Game knows nothing about networking. Server orchestrates both.
2. **Callback injection:** Game class communicates with WebSocket clients through callback functions set by server.py — no circular imports.
3. **Parallel AI execution:** AI grades proposals as a background asyncio task WHILE humans are voting. Next scenario generates WHILE results are displayed. Zero wasted time.
4. **Fallback systems:** If any AI call fails (network, rate limit, timeout), pre-written fallback scenarios and default evaluations kick in. The game never crashes.
5. **Reconnection support:** If a player's phone drops connection, they can rejoin and get their current state. Soft disconnects, not hard deletes.

### Game Flow State Machine

```
LOBBY ──[Start]──► ROLE REVEAL ──[3s]──► ROUND START
                                              │
                    ┌─────────────────────────┘
                    ▼
              WRITING PHASE (parliament types, people watch)
                    │ timer expires or all locked
                    ▼
              VOTING PHASE (people vote, AI grades in background)
                    │ timer expires or all voted
                    ├──[tie?]──► TIEBREAKER ──► RESULTS
                    │                              │
                    └──[no tie]──► RESULTS ────────┘
                                      │
                                      ├──[more rounds]──► ROUND START
                                      │
                                      └──[last round or collapse]──► GAME OVER
                                                                        │
                                                                   AI Reveal
                                                                   Leaderboards
                                                                   Awards
                                                                   Narrative
```

---

## Part 4: Key Code Snippets

Use these actual code snippets on the technical slides. They are real, working code from the project.

### Snippet 1: The Economy Model (economy.py)

Good for the "Economy Model" slide. Shows the class, indicators, and policy application.

```python
class Economy:
    """Manages the 6-indicator economy state and cumulative score."""

    def __init__(self):
        """Initialize economy with starting indicator values from config."""
        self.gdp = config.STARTING_GDP               # 75
        self.employment = config.STARTING_EMPLOYMENT  # 80
        self.inflation = config.STARTING_INFLATION    # 20
        self.public_trust = config.STARTING_PUBLIC_TRUST  # 70
        self.trade_balance = config.STARTING_TRADE_BALANCE  # 60
        self.national_debt = config.STARTING_NATIONAL_DEBT  # 30
        self.score = 0

    def apply_policy(self, impacts: dict):
        """Apply a policy's economic impacts, capping each at -15/+15."""
        self.gdp = self._clamp(self.gdp + self._cap_impact(impacts.get("gdp", 0)))
        self.employment = self._clamp(self.employment + self._cap_impact(impacts.get("employment", 0)))
        # ... (same pattern for all 6 indicators)

    @staticmethod
    def _cap_impact(value: int) -> int:
        """Cap a single impact value to the range [-15, +15]."""
        return max(-15, min(15, int(value)))

    @staticmethod
    def _clamp(value: int) -> int:
        """Clamp a value to the valid indicator range [0, 100]."""
        return max(0, min(100, int(value)))
```

### Snippet 2: GameSettings Dataclass (config.py)

Good for showing dataclasses and input validation.

```python
@dataclass
class GameSettings:
    """Configurable game parameters set by the host before the game starts."""
    mode: str = "destructive"      # "constructive" | "destructive"
    num_rounds: int = 5            # 3/5/7
    parliament_size: int = 4       # 3/4/5
    anonymous: bool = True
    proposal_time: int = 120       # seconds
    voting_time: int = 45          # seconds

    @staticmethod
    def from_dict(d: dict) -> "GameSettings":
        """Create GameSettings from a dictionary, clamping values to valid ranges."""
        return GameSettings(
            mode=d.get("mode", "destructive") if d.get("mode") in ("constructive", "destructive") else "destructive",
            num_rounds=max(1, min(20, int(d.get("num_rounds", 5)))),
            parliament_size=max(2, min(15, int(d.get("parliament_size", 4)))),
            # ...
        )
```

### Snippet 3: Parallel AI Execution (server.py)

Good for showing async/await and the parallel execution pattern.

```python
async def start_voting_phase():
    """Begin voting phase. AI grading runs as a background task in parallel with voting."""
    proposals_list = game.get_proposals_list()

    # Fire AI grading in background — runs WHILE humans are voting
    game.grading_task = asyncio.create_task(grade_proposals_background())

    # Send voting UI to players
    await broadcast_to_people({"type": "voting_phase", "proposal_count": len(proposals_list), ...})

    # Start voting timer
    phase_timer_task = asyncio.create_task(voting_phase_timer())
```

### Snippet 4: AI Proposal Evaluation (llm.py)

Good for showing AI integration, JSON parsing, and error handling.

```python
async def evaluate_proposals(scenario, proposals, economy_state, mode="destructive"):
    """Evaluate parliament proposals. Returns list of evaluation dicts."""
    content = await _call_llm(system_prompt, "Evaluate these proposals.", temperature=0.5)
    data = _parse_json(content)  # handles malformed JSON from AI

    # Validate and normalize each evaluation
    for ev in data.get("evaluations", []):
        entry = {
            "proposal_index": int(ev.get("proposal_index", 0)),
            "quality_score": max(0, min(100, int(ev.get("quality_score", 50)))),
            "impacts": {k: max(-30, min(30, int(v))) for k, v in ev.get("impacts", {}).items()},
            "ai_commentary": str(ev.get("ai_commentary", "")),
        }
```

### Snippet 5: Error Handling & Fallbacks (llm.py)

Good for showing try/except and fallback systems.

```python
async def _call_llm(system_prompt, user_message, temperature=0.9, max_tokens=1000):
    """Make a single LLM call via OpenRouter. Retries once on failure."""
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(OPENROUTER_URL, json=payload, headers=_get_headers())
                resp.raise_for_status()
                result = resp.json()
            return result["choices"][0]["message"]["content"].strip()
        except (httpx.HTTPError, KeyError) as e:
            logger.warning(f"LLM call attempt {attempt + 1} failed: {e}")
            if attempt == 0:
                continue  # retry once
            raise

def get_fallback_evaluations(num_proposals):
    """Return fallback evaluations if AI grading fails."""
    return [{"proposal_index": i, "quality_score": 50, "impacts": {k: 0 for k in impact_keys},
             "ai_commentary": "AI was too slow to judge this one. Participation trophy. Sad!"}
            for i in range(num_proposals)]
```

### Snippet 6: WebSocket Broadcasting (server.py)

Good for showing real-time communication and connection management.

```python
async def broadcast_to_host(data: dict):
    """Send a JSON message to all connected host displays."""
    message = json.dumps(data)
    dead = set()
    for ws in host_connections:
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)  # mark dead connections
    for ws in dead:
        host_connections.discard(ws)  # clean up
```

### Snippet 7: Player Role Assignment (game.py)

Good for showing randomization and data structure usage.

```python
def assign_roles(self):
    """Randomly assign parliament members from connected players."""
    connected = self.get_player_names()
    random.shuffle(connected)

    parliament_size = min(self.settings.parliament_size, len(connected) - 1)
    self.parliament_members = connected[:parliament_size]
    self.people_members = connected[parliament_size:]

    for i, name in enumerate(self.parliament_members):
        self.players[name].role = "parliament"
        self.players[name].parliament_index = i
```

---

## Part 5: Libraries & Dependencies Used

| Library | Purpose | Why It Matters |
|---------|---------|---------------|
| `FastAPI` | Web framework with WebSocket support | Handles HTTP endpoints + real-time WebSocket connections |
| `httpx` | Async HTTP client | Makes non-blocking AI API calls (doesn't freeze the server) |
| `asyncio` | Async concurrency | Runs AI calls in parallel with human phases, manages timers |
| `json` | JSON serialization | All WebSocket messages are JSON, AI responses are JSON |
| `dataclasses` | Typed data containers | GameSettings, ProposalRecord, RoundRecord, PlayerData |
| `qrcode` | QR code generation | Creates the join QR code shown on the projector |
| `random` | Randomization | Parliament role assignment, tiebreaker resolution |
| `logging` | Structured logging | Debug info, error tracking, AI call monitoring |
| `os` + `dotenv` | Environment variables | API keys and config loaded from .env file (not hardcoded) |

---

## Part 6: The Slides

### Slide 1: Title Slide

**Title:** Econoland: Parliament Edition
**Subtitle:** A Live Multiplayer Political Economy Simulation
**Visual:** Clean title with a subtle economics-themed background (graph lines, currency symbols, or a stylized parliament building)
**Bottom:** University name, course name, date, group member names as placeholders

---

### Slide 2: What is Econoland?

**Content:**
- A live multiplayer game where the class becomes a country's parliament
- Randomly elected parliament writes policy proposals on their phones
- The rest of the class votes on which policy to enact
- An AI secretly grades every proposal — revealed at game over with commentary
- Economy simulation with 6 real indicators that change each round

**Speaker notes:** "We built a political economy simulation game. The idea is simple: what happens when a group of economics students run a country's parliament? [pause] Chaos, usually. But sometimes brilliance. You're about to find out which one you are."

---

### Slide 3: Why This Topic?

**Content:**
- We're economics students — we wanted to build something relevant to our field
- Simulates real economic decision-making in an engaging, interactive way
- Combines economic theory with game design and artificial intelligence
- Makes abstract concepts (fiscal policy, trade, inflation) tangible and fun
- Everyone participates — not just watching, but making decisions that matter

**Speaker notes:** "As econ students, we thought — instead of just studying how economies work, why not let people break one? Or try to save one. Every policy you write has real consequences on a simulated economy."

---

### Slide 4: How It Works — Architecture Overview

**Content:**
- Python backend (FastAPI) handles ALL game logic, state management, and AI
- WebSockets for real-time bidirectional communication (instant updates)
- OpenRouter API connects to AI for scenario generation, grading, and narrative
- Host display (projector) + Player UI (phones) connected via ngrok tunnel
- The HTML pages are just thin displays — like a TV screen. All intelligence is Python.

**Visual:** Architecture diagram:
```
┌──────────────┐     WebSocket      ┌──────────────────┐
│  Projector   │◄──────────────────►│                  │
│  (host.html) │                    │  Python Server   │
└──────────────┘                    │  (FastAPI)       │
                                    │                  │──► OpenRouter API ──► AI (Grok)
┌──────────────┐     WebSocket      │  - game.py       │
│  Phone 1     │◄──────────────────►│  - economy.py    │
│  Phone 2     │◄──────────────────►│  - llm.py        │
│  Phone 3...  │◄──────────────────►│  - config.py     │
│  (player.html)                    └──────────────────┘
└──────────────┘        ▲
                        │
                     ngrok tunnel
                  (university WiFi)
```

**Speaker notes:** "The entire brain of the game is Python. Five modules, over 2,000 lines of code. The server manages game state, orchestrates phases, runs AI calls in parallel, and pushes updates in real-time to every connected device. The HTML pages on the projector and phones are just thin displays — like a TV screen. They show what Python tells them to show. All logic, all decisions, all intelligence lives in Python."

---

### Slide 5: Key Python Concepts Used

**Content:**
- **Data Structures:** Dictionaries (player state, economy indicators, vote counts), Lists (round history, proposals, leaderboards), Dataclasses (GameSettings, PlayerData, ProposalRecord, RoundRecord)
- **Functions:** 50+ functions organized across 5 modules — every function has a docstring
- **Error Handling:** try/except for API failures, JSON parsing, WebSocket disconnections, with automatic fallback mechanisms
- **Async/Await:** Concurrent AI calls during human activity phases (AI grades WHILE humans vote)
- **Libraries:** FastAPI, httpx, asyncio, json, dataclasses, qrcode, random, logging

**Speaker notes:** "We use dictionaries everywhere — for tracking players, economy state, vote counts, AI evaluations. Dataclasses give us typed containers for game settings and round records. Error handling is critical because we depend on external AI APIs that can fail at any time — so we built fallback systems that keep the game running no matter what."

---

### Slide 6: The Economy Model (economy.py)

**Content:**
- 6 indicators on a 0-100 scale: GDP, Employment, Inflation, Public Trust, Trade Balance, National Debt
- Each round, the winning policy applies AI-determined impacts to all 6 indicators
- Individual impacts capped at +/-15 per indicator per round (prevents instant collapse)
- Collapse detection in destructive mode: GDP or employment hits 0 = early game over
- Clean separation: Economy class knows nothing about players, networking, or AI

**Visual:** Code snippet (Snippet 1 from Part 4)

**Speaker notes:** "The economy model is intentionally simple but effective. Six indicators, each clamped between 0 and 100. Every policy proposal gets AI-assigned impacts, and we cap those at plus or minus 15 to prevent one proposal from ending the game immediately. This creates a compounding effect — bad decisions stack up over rounds. By round 5, the consequences of round 1's policy are still echoing."

---

### Slide 7: Game State Management (game.py)

**Content:**
- Central Game class: ~590 lines managing the entire game lifecycle
- Phase state machine: lobby -> writing -> voting -> tiebreaker -> results -> game over
- Every action is validated: can't vote during writing phase, can't submit proposals after timer
- Role-based logic: Parliament members write proposals, People vote
- Complete history tracking: every proposal, vote, AI evaluation stored per round for the final reveal

**Visual:** State machine diagram (from Part 3 game flow) + Code snippet (Snippet 7)

**Speaker notes:** "game.py is the heart of the project. It's the largest module at nearly 600 lines. The state machine ensures game integrity — you can't vote during the writing phase, you can't submit two votes, and parliament members can't vote on their own proposals. Everything is validated server-side."

---

### Slide 8: AI Integration (llm.py)

**Content:**
- **3 AI interactions per game:**
  1. Scenario generation — creates economic crisis headlines each round
  2. Proposal evaluation — secretly scores every proposal with impacts + commentary
  3. End-game narrative — satirical news anchor summary of the whole game
- Parallel execution: AI grades proposals as a background task WHILE humans are voting
- Next scenario generates WHILE results are displayed — zero wasted time
- Robust fallback: 7 pre-written scenarios + default evaluations if AI fails

**Visual:** Code snippet (Snippet 3 showing asyncio.create_task for parallel execution)

**Speaker notes:** "We use the AI for three things. First, it generates economic crisis scenarios each round — things like 'Econoland's Currency Crashes 50%.' Second, it secretly grades every parliament proposal with a quality score from 0 to 100, economic impacts, and a one-line roast or praise. Nobody sees these until game over — that's the big reveal. Third, at the end, it writes a satirical summary. The key engineering insight: we fire the AI grading as a background task the moment voting starts, so by the time everyone has voted, the AI is already done. No waiting."

---

### Slide 9: Real-Time Communication (server.py)

**Content:**
- FastAPI WebSocket endpoints: `/ws/host` (projector) and `/ws/player/{name}` (phones)
- Role-based messaging: parliament gets a text input, people get numbered vote buttons
- **Live character-by-character display:** when parliament types, every keystroke is streamed to the projector in real-time
- Player reconnection: if a phone drops connection, the player can rejoin without losing progress
- Dead connection cleanup: server detects and removes stale WebSocket connections

**Visual:** Code snippet (Snippet 6 showing broadcast with dead connection cleanup)

**Speaker notes:** "WebSockets are what make this a live experience, not just a web form. When a parliament member types a character on their phone, it appears on the projector within milliseconds. When someone votes, the vote bar updates live for everyone. And if someone's phone loses WiFi, they can rejoin — the server tracks their state and brings them back in."

---

### Slide 10: Two Game Modes

**Content:**
- **Constructive Mode:** Save the economy. Parliament names revealed. AI rewards smart policy. Scored on prosperity.
- **Destructive Mode:** Crash the economy as fast as possible. Anonymous parliament. AI rewards creative chaos. Scored on destruction.
- AI adapts everything to the mode: scenario tone, scoring rubric, commentary style, end-game narrative
- Both modes use the same codebase — mode is just a configuration parameter

**Speaker notes:** "We built two modes. Constructive is the serious economics simulation — can you write policies that save a struggling economy? Destructive is the fun one — how creatively can you crash it? The AI adjusts everything: in destructive mode, scenarios get darker, scoring rewards chaos, and the end-game commentary gets more savage. Same code, different experience."

---

### Slide 11: LIVE DEMO

**Content:** Large text: "Let's play."
**Subtext:** "Scan the QR code to join on your phone."

**Speaker notes:** This is the live demo. ~5 minutes. Rehearse this flow:
1. Show settings screen (30s) — pick mode (destructive for entertainment), 3 rounds, parliament size based on class
2. Show QR code — tell class to scan and enter a name (30s)
3. Start game — show role assignment on projector (15s)
4. Play 2-3 rounds: writing phase (watch parliament type live) -> voting -> results (3 min)
5. Hit "End Game" -> show AI reveal, leaderboards, narrative (1 min)

**Backup plan:** If WiFi/ngrok fails, have screenshots of each game phase ready as backup slides.

---

### Slide 12: Challenges & Solutions

**Content:**
| Challenge | Solution |
|-----------|----------|
| Syncing 20+ phones in real-time | WebSocket broadcasting with dead connection cleanup |
| AI response time could stall gameplay | Parallel execution (grade during voting) + pre-written fallback scenarios |
| Game state consistency across phases | Phase state machine with server-side validation on every action |
| Player disconnections mid-game | Soft disconnects with automatic reconnection support |
| AI returning malformed JSON | Retry logic + JSON extraction from mixed responses + fallback evaluations |

**Speaker notes:** "Building a real-time multiplayer game has unique challenges. The biggest was keeping 20+ devices in sync without lag. If one player's phone loses connection, the game can't break — so we built soft disconnects and reconnection. If the AI is slow, we run it in parallel with human phases. If the AI fails entirely, fallback scenarios kick in. The game never crashes."

---

### Slide 13: Next Steps & Future Improvements

**Content:**
- Role rotation: shuffle parliament each round so everyone gets to write proposals
- Spectator mode for late joiners who want to watch
- Persistent game history and replay system
- Deeper economic models: GDP growth rates, compound interest on debt, inflation spirals
- Mobile-optimized progressive web app
- Tournament mode: multiple games with cumulative scoring across sessions

**Speaker notes:** "If we had more time, the biggest improvement would be parliament rotation — so everyone gets to write proposals, not just the same group. We'd also add a spectator mode, deeper economic modeling with compound effects, and a tournament system for running multiple games."

---

### Slide 14: Comparison to Existing Products

**Content:**
| | Econoland | Kahoot | Mentimeter |
|---|---|---|---|
| **Content source** | Players write it | Pre-written by host | Free-text polls |
| **Game simulation** | Living economy with 6 indicators | None | None |
| **AI integration** | Grades proposals, generates scenarios | None | None |
| **Real-time typing** | Character-by-character live display | N/A | N/A |
| **Scoring** | Dual leaderboards + hidden AI reveal | Speed-based quiz scoring | None |

**Key differentiator:** Players CREATE the content. The AI JUDGES it. The economy REACTS to it. Nothing else does all three live.

**Speaker notes:** "Kahoot gives you 4 pre-written options. We give you a blank text box and say 'write a policy that will save — or destroy — this economy.' That's fundamentally different. It requires creativity and economic thinking, not just recognizing the right answer."

---

### Slide 15: Q&A

**Content:** "Questions?"

**Speaker notes — prepare for these questions:**

- **"How does the AI grading work?"** — The AI receives the scenario, all proposals, and the current economy state. It returns a JSON with a quality score (0-100), economic impacts for each of the 6 indicators, and a one-line commentary. We validate and normalize everything server-side.

- **"What happens if the AI fails?"** — We have a complete fallback system. 7 pre-written scenarios cycle if scenario generation fails. Default evaluations give everyone 50/100 if grading fails. The game never stops.

- **"Why Python and not [X]?"** — Python has the best ecosystem for this: FastAPI for web servers, httpx for async HTTP, and all the AI libraries are Python-first. Plus, it's a Python course.

- **"How do you handle cheating?"** — All validation is server-side. Votes are checked for phase, role, and duplicates. Proposals are capped at 200 characters. The client can't bypass any rules — the server rejects invalid actions.

- **"What AI model do you use?"** — We use OpenRouter as a gateway to access various models. Currently configured for Grok for speed, but it's swappable to any model via a single environment variable.

- **"Why WebSockets and not regular HTTP?"** — Regular HTTP is request-response: the client asks, the server answers. WebSockets are bidirectional: the server can push updates to clients instantly. That's how we do live keystroke display, real-time vote bars, and countdown timers.

---

## Part 7: Presentation Tips

### Timing

| Section | Time | Slides |
|---------|------|--------|
| Intro & concept | 1:30 | 1-3 |
| Architecture & Python concepts | 1:30 | 4-5 |
| Code deep-dive | 1:30 | 6-9 |
| Game modes & transition to demo | 0:30 | 10-11 |
| **Live demo** | **5:00** | 11 |
| Wrap-up & Q&A | 1:00 | 12-15 |

### Suggested Speaker Split (3 members)

- **[Speaker 1]:** Slides 1-5 (intro, what it is, why, architecture, Python concepts)
- **[Speaker 2]:** Slides 6-10 (code deep-dive: economy, game, AI, server, modes)
- **[Speaker 3]:** Slides 11-15 (live demo, challenges, future, comparison, Q&A)

### Demo Rehearsal Notes

- Test ngrok + phones before class. Have the QR code ready.
- Use **destructive mode** for the demo — it's more entertaining and gets more laughs
- Set to **3 rounds** to fit in 5 minutes
- If WiFi dies: have backup screenshots of every game phase as fallback slides
- End the game with the "End Game" button after 2-3 rounds to show the AI reveal

### Key Messages to Land

1. **"2,000+ lines of Python across 5 modules"** — emphasize scale
2. **"AI runs in parallel with human phases — zero wasted time"** — shows engineering sophistication
3. **"The game never crashes — fallback systems for everything"** — shows robustness
4. **"Every function has a docstring, every input is validated"** — shows code quality
5. **"Python is the brain, HTML is just the screen"** — addresses the "Python only" concern

---

## Part 8: Visual Design Suggestions

### Color Palette (Dark Theme)

- **Background:** Deep navy (#0F172A) or charcoal (#1E1E2E)
- **Primary accent:** Electric blue (#3B82F6) or teal (#14B8A6)
- **Secondary accent:** Amber (#F59E0B) for highlights and warnings
- **Text:** White (#F8FAFC) for headings, light gray (#CBD5E1) for body
- **Code blocks:** Slightly lighter dark background (#1E293B) with syntax highlighting

### Typography

- **Headings:** Bold sans-serif (Inter, Montserrat, or similar)
- **Body:** Regular sans-serif, 24-28pt minimum for readability from back of room
- **Code:** Monospace (JetBrains Mono, Fira Code, or Consolas), 18-20pt

### Slide Layout Principles

- Maximum 5-6 bullet points per slide
- Code snippets: show only the essential lines, not entire files
- Use icons or simple graphics, not stock photos
- Diagrams should be clean and minimal — boxes and arrows, not 3D renders
- Leave white space — don't fill every corner

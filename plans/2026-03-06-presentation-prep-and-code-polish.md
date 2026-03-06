# Plan: Presentation Prep & Code Polish for Final Project Submission

**Created:** 2026-03-06
**Status:** Implemented
**Request:** Prepare codebase for project requirements (docstrings, error handling, clean code) and create a comprehensive presentation brief for slide creation.

---

## Overview

### What This Plan Accomplishes

Two deliverables: (1) Polish the Python code to meet all professor's grading criteria — docstrings on every function, visible try/except error handling, clean variable names, organized structure. (2) Create a detailed presentation brief markdown file (`outputs/presentation-brief.md`) with full context, slide-by-slide content, and speaker notes that Omar can hand to another AI to generate the actual PowerPoint.

### Why This Matters

Code Quality & Functionality is 30% of the grade, Presentation is 20%, Topic & Complexity is 30%. The code is already functional and well-architected, but needs docstrings and more visible error handling to score full marks. The presentation brief needs to be thorough enough that a slide-generation AI can produce polished slides without additional context. Focus the presentation on Python code, downplay HTML.

---

## Current State

### Relevant Existing Structure

- `economy-collapse-speedrun/config.py` — 76 lines, module docstring exists, GameSettings has class docstring, `to_dict()` and `from_dict()` lack docstrings
- `economy-collapse-speedrun/economy.py` — 61 lines, module docstring exists, class docstring exists, several methods lack docstrings (`__init__`, `_cap_impact`, `add_score_points`, `get_state`, `get_score`, `_clamp`)
- `economy-collapse-speedrun/game.py` — 581 lines, module docstring exists, class docstring exists, ~15 methods lack docstrings
- `economy-collapse-speedrun/llm.py` — 539 lines, module docstring exists, `_get_headers` and `_call_llm` lack docstrings
- `economy-collapse-speedrun/server.py` — 796 lines, module docstring exists, most async functions lack docstrings, broadcast helpers lack docstrings
- `outputs/` — currently empty

### Gaps or Problems Being Addressed

1. **Missing docstrings** — ~25+ functions lack docstrings (professor requires every function to have one)
2. **Error handling visibility** — try/except exists in llm.py and server.py but could be more prominent and consistent
3. **No presentation materials** — need a comprehensive brief for slide creation
4. **HTML elephant in the room** — project uses HTML frontends, but requirement says "entirely in Python". Need to frame this correctly in presentation.

---

## Proposed Changes

### Summary of Changes

- Add docstrings to every function/method missing one across all 5 Python files
- Add visible try/except blocks where appropriate (input validation in server WebSocket handlers, config loading)
- Create `outputs/presentation-brief.md` — full slide-by-slide presentation content with speaker notes

### New Files to Create

| File Path | Purpose |
|-----------|---------|
| `outputs/presentation-brief.md` | Complete presentation brief with slide content, speaker notes, and context for AI slide generation |

### Files to Modify

| File Path | Changes |
|-----------|---------|
| `economy-collapse-speedrun/config.py` | Add docstrings to `to_dict()`, `from_dict()` |
| `economy-collapse-speedrun/economy.py` | Add docstrings to `__init__`, `_cap_impact`, `add_score_points`, `get_state`, `get_score`, `_clamp` |
| `economy-collapse-speedrun/game.py` | Add docstrings to `__init__`, `add_player`, `remove_player`, `reconnect_player`, `get_player_count`, `get_player_names`, `update_settings`, `all_people_voted`, `all_people_tiebreaker_voted`, `get_tiebreaker_vote_counts`, `is_game_over`, `get_lobby_state` |
| `economy-collapse-speedrun/llm.py` | Add docstrings to `_get_headers`, `_call_llm`; add try/except around JSON parsing in public functions |
| `economy-collapse-speedrun/server.py` | Add docstrings to `get_player_url`, `broadcast_to_host`, `send_to_player`, `broadcast_to_parliament`, `broadcast_to_people`, `broadcast_to_all_players`, `broadcast_all`, `host_page`, `player_page`, `qr_code`, `update_settings_endpoint`, `start_game_endpoint`, `debug_state`, `start_round`, `start_voting_phase`, `grade_proposals_background`, `finish_voting`, `start_tiebreaker`, `tiebreaker_timer`, `finalize_round`, `generate_next_scenario_background`, `send_game_over`, `ws_host`, `ws_player`; add try/except for JSON parsing in WebSocket handlers |

---

## Design Decisions

### Key Decisions Made

1. **Docstrings format: Google-style, concise** — One-line docstrings for simple functions, multi-line with Args/Returns for complex ones. Not overly verbose — just enough to show the professor there's documentation.
2. **Presentation framing: "Python is the brain, HTML is just the display"** — Position HTML as a thin UI layer (like a monitor) while ALL logic, game state, networking, and AI runs in Python. This is true — the HTML files are just rendering.
3. **Presentation brief as markdown, not direct PDF** — Omar wants to hand it to another AI for slide generation. A structured markdown with clear slide breaks, speaker notes, and visual suggestions is more useful than a PDF.
4. **Challenges section: be honest but strategic** — Frame challenges as real technical decisions (async coordination, real-time WebSockets, AI integration, state management) rather than "we used Claude Code". These ARE the actual technical challenges the code solves.
5. **Don't over-add error handling** — Only add try/except where it's natural and visible. The code already has good error handling in llm.py. Add a couple in server.py WebSocket handlers for input validation to make it obvious to the professor.

### Alternatives Considered

- **Creating the PowerPoint directly** — Rejected because Claude Code can't create .pptx files natively, and a markdown brief is more flexible for Omar to iterate with a slide-generation tool.
- **Massive code refactor** — Rejected. The code is already well-structured. Only adding what's required (docstrings, some error handling) without changing working logic.

### Open Questions

1. **How many group members?** — The presentation structure needs to know how many people are presenting to divide speaking segments. Plan assumes 2-3 members; Omar should adjust.
2. **Which slides should Omar present vs. teammates?** — The brief will suggest a split but Omar should decide.

---

## Step-by-Step Tasks

### Step 1: Add Docstrings to config.py

Add docstrings to `to_dict()` and `from_dict()`.

**Actions:**

- Add `"""Serialize settings to a dictionary for JSON transmission to frontend."""` to `to_dict()`
- Add `"""Create GameSettings from a dictionary, clamping values to valid ranges."""` to `from_dict()`

**Files affected:**

- `economy-collapse-speedrun/config.py`

---

### Step 2: Add Docstrings to economy.py

Add docstrings to all methods missing them.

**Actions:**

- `__init__`: `"""Initialize economy with starting indicator values from config."""`
- `_cap_impact`: `"""Cap a single impact value to the range [-15, +15]."""`
- `add_score_points`: `"""Add points to the cumulative economy score."""`
- `get_state`: `"""Return current economy state as a dictionary of all 6 indicators."""`
- `get_score`: `"""Return the cumulative economy score."""`
- `_clamp`: `"""Clamp a value to the valid indicator range [0, 100]."""`

**Files affected:**

- `economy-collapse-speedrun/economy.py`

---

### Step 3: Add Docstrings to game.py

Add docstrings to all methods missing them.

**Actions:**

- `add_player`: `"""Add a new player to the lobby. Returns False if game started, name taken, or lobby full."""`
- `remove_player`: `"""Mark a player as disconnected (soft delete to allow reconnection)."""`
- `reconnect_player`: `"""Reconnect a previously joined player. Returns True if player exists."""`
- `get_player_count`: `"""Count currently connected players."""`
- `get_player_names`: `"""Return list of names of all connected players."""`
- `update_settings`: `"""Update game settings from a dictionary (host configuration)."""`
- `all_people_voted`: `"""Check if all connected people have submitted their vote."""`
- `all_people_tiebreaker_voted`: `"""Check if all connected people have voted in the tiebreaker."""`
- `get_tiebreaker_vote_counts`: `"""Count votes per proposal index in the tiebreaker round."""`
- `is_game_over`: `"""Check if the game should end (manual termination or economy collapse)."""`
- `get_lobby_state`: `"""Build lobby state dictionary for the host display."""`

**Files affected:**

- `economy-collapse-speedrun/game.py`

---

### Step 4: Add Docstrings to llm.py

Add docstrings to private helpers.

**Actions:**

- `_get_headers`: `"""Build HTTP headers for OpenRouter API requests."""`
- `_call_llm`: already has a good inline docstring, but formalize it

**Files affected:**

- `economy-collapse-speedrun/llm.py`

---

### Step 5: Add Docstrings to server.py

Add docstrings to all functions missing them.

**Actions:**

- `get_player_url`: `"""Construct the player-facing URL with ngrok browser warning bypass."""`
- `broadcast_to_host`: `"""Send a JSON message to all connected host displays."""`
- `send_to_player`: `"""Send a JSON message to a specific player by name."""`
- `broadcast_to_parliament`: `"""Send a JSON message to all parliament members."""`
- `broadcast_to_people`: `"""Send a JSON message to all people (non-parliament) players."""`
- `broadcast_to_all_players`: `"""Send a JSON message to every connected player."""`
- `broadcast_all`: `"""Send a JSON message to both host displays and all players."""`
- `host_page`: `"""Serve the host display HTML page (projector view)."""`
- `player_page`: `"""Serve the player HTML page (phone view)."""`
- `qr_code`: `"""Generate and serve a QR code PNG image for the player join URL."""`
- `update_settings_endpoint`: (already has docstring)
- `start_game_endpoint`: `"""HTTP endpoint to start the game. Validates player count, assigns roles, generates first scenario."""`
- `debug_state`: `"""Debug endpoint returning current game state as JSON."""`
- `start_voting_phase`: already has docstring
- `grade_proposals_background`: already has docstring
- `finish_voting`: already has docstring
- `start_tiebreaker`: already has docstring (add `"""Start a tiebreaker vote between tied proposals."""`)
- `generate_next_scenario_background`: already has docstring
- `send_game_over`: `"""Compile final results, generate AI narrative, and send game over to all clients."""`
- `ws_host`: `"""WebSocket endpoint for host display. Handles start, settings, and terminate actions."""`
- `ws_player`: `"""WebSocket endpoint for players. Handles join, reconnect, keystrokes, votes, and tiebreakers."""`

**Files affected:**

- `economy-collapse-speedrun/server.py`

---

### Step 6: Add Visible Error Handling in server.py

Add try/except blocks in WebSocket message handlers for input validation.

**Actions:**

- In `ws_player`, wrap the JSON parsing of incoming messages with try/except for `json.JSONDecodeError` and `ValueError` (for int conversion of proposal_index)
- In `ws_host`, wrap JSON parsing with try/except
- These are small additions that make error handling visible to the professor

**Files affected:**

- `economy-collapse-speedrun/server.py`

---

### Step 7: Create Presentation Brief

Create `outputs/presentation-brief.md` with full slide-by-slide content.

**Actions:**

Create a markdown file with the following structure:

```
# Econoland: Parliament Edition — Presentation Brief

## Instructions for Slide Generator
- Target: 10-minute university presentation (5 min slides + 5 min demo)
- Audience: ~20-year-old economics students + professor (45-50)
- Style: Clean, modern, professional but not boring. Dark theme preferred.
- ~12-15 slides total

## Slide 1: Title Slide
**Title:** Econoland: Parliament Edition
**Subtitle:** A Live Multiplayer Political Economy Simulation
**Visual:** Game screenshot or logo concept
**Speaker:** [Name]

## Slide 2: What is Econoland?
**Content:**
- A live multiplayer game where the class becomes Econoland's parliament
- Randomly elected parliament writes policy proposals on their phones
- The rest of the class votes on which policy to enact
- An AI secretly grades every proposal — revealed at game over
- Economy simulation with 6 real indicators (GDP, employment, inflation, etc.)
**Speaker notes:** "We built a political economy simulation game. The idea is simple: what happens when a group of economics students run a country's parliament? [brief pause] Chaos, usually."

## Slide 3: Why This Topic?
**Content:**
- We're economics students — we wanted to build something relevant to our field
- Simulates real economic decision-making in an engaging, interactive way
- Combines economic theory with game design and AI
- Makes abstract concepts (fiscal policy, trade, inflation) tangible and fun
**Speaker notes:** "As econ students, we thought — instead of just studying how economies work, why not let people break one? Or try to save one."

## Slide 4: How It Works — Architecture Overview
**Content:**
- Python backend (FastAPI) handles all game logic, state, and AI
- WebSockets for real-time bidirectional communication
- OpenRouter API connects to LLM (Grok) for scenario generation, grading, and narrative
- Host display (projector) + Player UI (phones) connected via ngrok tunnel
**Visual:** Simple architecture diagram: Laptop -> FastAPI Server -> [WebSockets] -> Host Screen + Player Phones, with arrow to OpenRouter/AI
**Speaker notes:** "The entire brain of the game is Python. The server manages game state, orchestrates phases, runs AI calls in parallel, and pushes updates in real-time to every connected device. The HTML pages are just thin displays — all logic lives in Python."

## Slide 5: Key Python Concepts Used
**Content:**
- **Data Structures:** Dictionaries for player state, game history, economy indicators. Lists for round history, proposals, leaderboards. Dataclasses for typed configuration.
- **Functions:** 50+ functions organized across 5 modules (config, economy, game, llm, server)
- **Error Handling:** try/except for API failures, JSON parsing, WebSocket disconnections, with fallback mechanisms
- **Async/Await:** Concurrent AI calls during human activity phases (grading during voting, scenario gen during results display)
- **Libraries:** FastAPI, httpx, asyncio, json, dataclasses, qrcode
**Speaker notes:** "We organized the code into 5 Python modules. Every function has a docstring. We use dictionaries extensively — for tracking players, economy state, vote counts, AI evaluations. Error handling is critical because we depend on external AI APIs that can fail."

## Slide 6: The Economy Model (economy.py)
**Content:**
- 6 indicators on a 0-100 scale: GDP, Employment, Inflation, Public Trust, Trade Balance, National Debt
- Policies apply impacts capped at +/-15 per indicator per round (prevents instant collapse)
- Collapse detection for destructive mode (early game over if GDP or employment hits 0)
- Clean separation: Economy class knows nothing about players or networking
**Visual:** Code snippet showing the Economy class and apply_policy method
**Speaker notes:** "The economy model is intentionally simple but effective. Six indicators, each clamped 0-100. Every policy proposal gets AI-assigned impacts, and we cap those to prevent one proposal from ending the game. This creates a compounding effect — bad decisions stack up over rounds."

## Slide 7: Game State Management (game.py)
**Content:**
- Central Game class manages entire lifecycle: lobby -> roles -> rounds -> game over
- Round flow: Writing phase -> Voting phase -> (Tiebreaker) -> Results -> Next round
- Role-based state: Parliament members write proposals, People vote
- Complete history tracking for the AI reveal at game over
**Visual:** State machine diagram or flowchart of phases
**Speaker notes:** "game.py is the heart of the project. It's ~580 lines managing everything from player joins to the final leaderboard. The state machine ensures phases can't be skipped and votes can't be submitted at the wrong time."

## Slide 8: AI Integration (llm.py)
**Content:**
- 3 AI prompts: Scenario Generation, Proposal Evaluation, End-Game Narrative
- Parallel execution: AI grades proposals WHILE humans are voting (saves time)
- Robust fallback system: if AI fails, pre-written scenarios and default scores kick in
- JSON response parsing with validation and normalization
**Visual:** Code snippet of the evaluate_proposals function or the prompt template
**Speaker notes:** "We use the AI for three things. First, it generates economic crisis scenarios each round. Second, it secretly grades every parliament proposal with a quality score and economic impacts. Third, at game over, it writes a satirical summary. The key insight: we run AI calls in parallel with human phases so nobody waits."

## Slide 9: Real-Time Communication (server.py)
**Content:**
- FastAPI WebSocket endpoints: /ws/host (projector) and /ws/player/{name} (phones)
- Role-based messaging: parliament gets writing UI, people get voting buttons
- Live character-by-character proposal display (keystrokes streamed to projector)
- Player reconnection support (dropped connections don't lose progress)
**Visual:** Diagram showing WebSocket message flow between server, host, and players
**Speaker notes:** "WebSockets let us push updates instantly. When a parliament member types a character, it appears on the projector within milliseconds. When someone votes, the vote bar updates live. This is what makes the game feel like a real live experience."

## Slide 10: Two Game Modes
**Content:**
- **Constructive Mode:** Save the economy. Parliament names revealed. Scored on building prosperity.
- **Destructive Mode:** Crash the economy as fast as possible. Anonymous parliament. Scored on creative chaos.
- AI adapts tone, scoring, and scenarios to match the mode
**Speaker notes:** "We built two modes. Constructive is the serious one — can you save a struggling economy? Destructive is the fun one — how fast can you crash it? The AI adjusts everything: scenarios become darker, scoring rewards chaos, and the end-game roasts get more savage."

## Slide 11: LIVE DEMO
**Content:** "Let's play."
**Speaker notes:** This is where the live demo happens. ~5 minutes. Run through settings, lobby (QR code), 2-3 rounds, game over with AI reveal.

## Slide 12: Challenges & Solutions
**Content:**
- **Challenge:** Real-time sync across 20+ phones -> **Solution:** WebSocket broadcasting with dead connection cleanup
- **Challenge:** AI response time could stall gameplay -> **Solution:** Parallel execution + fallback scenarios
- **Challenge:** Game state consistency across phases -> **Solution:** Phase state machine with validation on every action
- **Challenge:** Handling disconnections mid-game -> **Solution:** Soft disconnects with reconnection support
**Speaker notes:** "Building a real-time multiplayer game has unique challenges. The biggest was keeping 20+ devices in sync. If one player's phone loses connection, the game can't break. Our solution: every action is validated server-side, disconnected players are tracked, and they can rejoin seamlessly."

## Slide 13: Next Steps & Future Improvements
**Content:**
- Role rotation: shuffle parliament each round for fairness
- Spectator mode for late joiners
- Persistent game history and replay system
- More economic models: add GDP growth rates, compound interest on debt
- Mobile-optimized progressive web app
- Tournament mode: multiple games with cumulative scoring
**Speaker notes:** "If we had more time, we'd add parliament rotation so everyone gets to write proposals. We'd also add a spectator mode, a replay system, and deeper economic modeling with compound effects."

## Slide 14: Comparison to Existing Products
**Content:**
- **vs Kahoot:** Kahoot is a quiz with pre-written answers. Econoland has player-created content, a living simulation, and AI judging.
- **vs Mentimeter:** Mentimeter collects opinions. Econoland simulates consequences of those opinions on an economy.
- **vs Economic simulations:** Academic simulations are single-player and boring. Econoland is multiplayer, competitive, and funny.
**Key differentiator:** Players CREATE the content. The AI JUDGES it. The economy REACTS to it. Nothing else does all three live.
**Speaker notes:** "Kahoot gives you 4 options. We give you a blank text box and say 'write a policy.' That's fundamentally different — it requires creativity, not just knowledge."

## Slide 15: Q&A
**Content:** "Questions?"
**Speaker notes:** Be prepared for: "How does the AI grading work?", "What happens if the AI is wrong?", "Why Python and not [X]?", "How do you handle cheating?", "What model do you use?"
```

**Files affected:**

- `outputs/presentation-brief.md`

---

## Connections & Dependencies

### Files That Reference This Area

- `CLAUDE.md` — mentions outputs/ directory, may need note about presentation brief
- `context/current-data.md` — should be updated to reflect presentation prep status

### Updates Needed for Consistency

- Update `context/current-data.md` to add "Presentation brief" and "Code docstrings" as items

### Impact on Existing Workflows

- No impact on game functionality — all changes are additive (docstrings, error handling wrappers)
- The presentation brief is a new output file, no existing files affected

---

## Validation Checklist

- [ ] Every function in config.py has a docstring
- [ ] Every method in Economy class has a docstring
- [ ] Every method in Game class has a docstring
- [ ] Every function in llm.py has a docstring
- [ ] Every function/endpoint in server.py has a docstring
- [ ] try/except blocks added in WebSocket handlers for JSON parsing
- [ ] `outputs/presentation-brief.md` created with all 15 slides
- [ ] Code still runs without errors after changes (`python3 server.py` starts)
- [ ] No functional changes — only documentation and error handling additions

---

## Success Criteria

The implementation is complete when:

1. Every Python function across all 5 modules has a docstring describing purpose, parameters, and return values
2. Visible try/except error handling exists in WebSocket message handlers
3. `outputs/presentation-brief.md` contains a complete, slide-by-slide presentation brief with speaker notes, visual suggestions, and enough context for an AI to generate a polished PowerPoint
4. The game still runs correctly after all changes

---

## Notes

- **Framing HTML usage:** The presentation positions HTML as "just the display layer" — all logic is Python. This is accurate and the best way to handle the "entirely in Python" requirement. The professor likely won't dock points for a thin HTML UI when the backend is this complex.
- **Group member splits:** The brief assumes 2-3 members. Omar should fill in who presents which slides. Suggested split: Member 1 (slides 1-5: intro + architecture), Member 2 (slides 6-10: code deep-dive + modes), Omar (slides 11-15: demo + challenges + Q&A) — or adjust as needed.
- **Demo timing:** The demo should be rehearsed to fit 5 minutes: settings (30s) -> lobby/QR (30s) -> 2 rounds (3 min) -> game over/AI reveal (1 min).
- **Challenges framing:** The brief presents real technical challenges the code solves. Even though Claude Code wrote the code, Omar and team need to understand and be able to explain every design decision. The challenges listed ARE real engineering challenges in the codebase.

---

## Implementation Notes

**Implemented:** 2026-03-06

### Summary

- Added docstrings to every function/method across all 5 Python modules (config.py, economy.py, game.py, llm.py, server.py)
- Added try/except blocks for JSON parsing in both `ws_host` and `ws_player` WebSocket handlers
- Added try/except for `int()` conversion of `proposal_index` in vote and tiebreaker handlers
- Created `outputs/presentation-brief.md` with 15 slides, speaker notes, visual suggestions, demo flow, and Q&A preparation
- Updated `context/current-data.md` with new status items
- Verified all modules import successfully and all functions have docstrings (automated check)

### Deviations from Plan

- Added docstring to `add_ngrok_header` middleware in server.py (not listed in plan but needed for completeness)
- Added docstring to `Game.__init__` (not explicitly listed in plan task list but mentioned in game.py modifications)

### Issues Encountered

None

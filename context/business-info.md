# Business Info

> Not applicable — this is a university course project, not a business context.

## Project Overview

**Economy Collapse Speedrun** — a multiplayer classroom game built in Python for a university programming course.

### The Game in One Sentence

A live economy simulation projected on a big screen where an LLM generates compounding scenarios in real time, the whole class votes on absurd policies via their phones, and everyone watches the economy crumble together.

### What Makes It Different From Kahoot

This is NOT a quiz. The key differentiators:

1. **Living simulation** — the projector shows a real-time economy dashboard (GDP, inflation, unemployment, etc.) that visibly deteriorates each round. Decisions compound: print money in round 2, face hyperinflation by round 5.
2. **The projector IS the show** — the phone is just a remote control. The entertainment is watching the economy crumble on the big screen with nosediving graphs, panicked news tickers, and indicators turning red.
3. **Social dynamics** — majority rules means the class sees the vote distribution. 80% picking the unhinged option while 3 people try to save the economy is inherently funny. Collective guilt.
4. **LLM-generated compounding narrative** — an LLM generates every scenario in real time. It receives the full history of enacted policies + current economy state + real-world events. Legalize drugs in round 1? Round 3's headline references the booming cocaine industry. Nothing is disconnected.
5. **Adapts to the class** — if the class picks responsible options, scenarios stay tame. If they go unhinged, the LLM escalates to match. It mirrors the room's energy.
6. **Current events woven in** — scenarios reference real-world headlines (Trump/Greenland, Iran situation, Maduro, trade wars) twisted through the fictional economy's lens.

### Core Mechanics

1. **Host screen** (projector): Live economy dashboard, LLM-generated scenario, vote results, satirical news ticker, QR code to join
2. **Player phones** (via QR code → ngrok public URL): Simple voting interface — pick 1 of 4 policy options each round
3. **LLM-generated scenarios** (via OpenRouter → Gemini/Grok): Each round, the LLM gets the full context (economy state + all previous decisions + current events) and generates a new compounding scenario with 4 options + satirical news ticker headlines
4. **Four option types per round**:
   - A: The responsible one (positive points — bad for the game objective)
   - B: The corrupt/greedy one (moderately destructive)
   - C: The unhinged one (highly destructive, the funny one)
   - D: The wildcard (unpredictable)
5. **Cumulative scoring**: Individual scores accumulate across all rounds, revealed at the end with MVP Destroyer and Boy Scout awards
6. **Configurable duration**: Host sets how long the game runs
7. **Early vote skip**: If all players vote before the timer, move on immediately

### Tone & Vibe

- Witty and satirical, not edgelord — "satirical Economist article" meets "Cards Against Humanity"
- Absurdist humor > shock value — "Abolish weekdays" is funnier than just being offensive
- Economic concept wordplay — "quantitative squeezing," "trickle-sideways economics"
- Dark but classroom-safe — The Purge references, dystopian scenarios, absurd bureaucracy
- Current events twisted satirically — real headlines remixed into the game world
- Adaptive — mirrors the class's energy level
- Hard red lines: no rape, no trashing religions, no slurs, no real atrocities

### Tech Stack

- Python (primary language — this is a Python course)
- FastAPI + WebSockets for real-time multiplayer
- OpenRouter API → Gemini or Grok (fast, cheap) for LLM scenario generation
- httpx for async API calls
- Vanilla HTML/JS for two frontend pages (host + player)
- ngrok for tunneling (university WiFi is strict)
- qrcode library for QR generation

---

# Current Data

---

## Project Status

| Item | Status | Notes |
| ---- | ------ | ----- |
| Game concept | Finalized | Economy destruction speedrun, multiplayer, live simulation, LLM-generated scenarios |
| Core differentiators | Defined | Living dashboard, compounding LLM narrative, adaptive tone, current events, social dynamics |
| Tech stack | Decided | FastAPI + WebSockets + vanilla HTML/JS + ngrok + qrcode + OpenRouter (Gemini/Grok) + httpx |
| LLM system prompt | Drafted | In the plan. Needs testing tonight. |
| LLM integration | Not started | OpenRouter API via httpx (async), pre-caching strategy defined |
| Game server | Not started | FastAPI + WebSocket server |
| Phone voting UI | Not started | Minimal — name entry, lobby, 4 vote buttons |
| Host display | Not started | Live economy dashboard, news ticker, scenario, vote results |
| Economy model | Not started | 6 indicators, 0-100 scale, LLM-generated impacts per option |
| Scoring system | Designed | Cumulative per-player, majority-rules for economy updates, end-of-game awards |
| Networking | Decided | ngrok tunnel (free tier) to bypass university WiFi |
| Demo rehearsal | Not started | Need to test with real phones via ngrok |

## Constraints

- **DEADLINE: Tomorrow, March 4, 2026**
- Must be primarily Python (it's a Python course)
- Must run on Omar's laptop connected to a projector
- Students join via phone browser — no app install
- University WiFi is strict (blocks unknown sites, may isolate devices) — using ngrok
- Total presentation: 10 minutes. Demo portion: ~5 minutes
- Need OpenRouter API key (Omar will provide)
- LLM must be fast (<3-5 seconds per scenario generation)

## Decisions Made

- LLM-generated scenarios (via OpenRouter) — compounding, adaptive, current-events-aware
- Gemini or Grok for speed and cost (test both, pick the better one)
- Pre-cache strategy: generate next scenario in background while showing results
- ngrok for networking (free tier)
- Early vote skip (don't wait for full timer if everyone voted)
- Cumulative scoring (leaderboard only at end)
- Off-limits: rape, trashing religions, slurs, real atrocities (enforced in system prompt)

## Resources Available

- Omar's laptop (host machine)
- University projector + big screen
- Students' phones (20+ concurrent users likely)
- ngrok free tier
- OpenRouter API key (Omar to provide)

---

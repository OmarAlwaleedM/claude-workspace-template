# Current Data

---

## Project Status

| Item | Status | Notes |
| ---- | ------ | ----- |
| Game concept | Finalized | Parliament Edition — parliament writes proposals, people vote, AI grades secretly |
| v1 (original) | Complete | Basic A/B/C/D voting, AI-generated options. Superseded by v2. |
| v2 plan | Complete | `plans/2026-03-04-economy-collapse-v2-parliament.md` |
| v2 backend (config.py) | Complete | GameSettings dataclass — round-based (num_rounds replaces duration_seconds) |
| v2 backend (economy.py) | Complete | 6 indicators, 0-100 scale. Neutral score/add_score_points (display as DESTRUCTION/PROSPERITY by mode) |
| v2 backend (game.py) | Complete | Roles, proposals, phases, tiebreaker, scoring, round history |
| v2 backend (llm.py) | Complete | 3 prompts: scenario gen, proposal evaluation, end narrative |
| v2 backend (server.py) | Complete | Phase management, role-based WebSockets, parallel AI calls |
| v2 frontend (host.html) | Complete | Settings → lobby → role reveal → writing → voting → tiebreaker → results → game over with AI reveal |
| v2 frontend (player.html) | Complete | Role-based: parliament text input / people numbered buttons / tiebreaker |
| Networking (ngrok) | Configured | `./ngrok http 8000`, URL in .env |
| .env | Configured | API key, model (grok-4.1-fast), ngrok URL set |
| Code docstrings | Complete | Every function across all 5 modules has a docstring |
| Error handling | Complete | try/except for JSON parsing + input validation in WebSocket handlers |
| Presentation brief | Complete | `outputs/presentation-brief.md` — 15 slides with speaker notes |
| Demo rehearsal | Not done | Need to test with real phones via ngrok |

## Constraints

- Must be primarily Python (it's a Python course)
- Must run on Omar's laptop connected to a projector
- Students join via phone browser — no app install
- University WiFi is strict — using ngrok to tunnel
- Total presentation: 10 minutes. Demo portion: ~5 minutes
- LLM must be fast (<3-5 seconds per call)

## Decisions Made

- v2 Parliament Edition (players write proposals, not AI)
- Grok (`x-ai/grok-4.1-fast`) via OpenRouter for speed
- Parallel AI calls: grade during voting, generate scenario during results
- Fixed parliament (no rotation during game)
- 200 char proposal limit, auto-lock at timer end (no submit button)
- Live character-by-character typing visible on projector
- Copy detection via AI prompt, permanent disclaimer on projector
- Tiebreaker: revote between tied proposals only, 10 seconds, random if still tied
- Constructive = revealed by default, Destructive = anonymous by default
- People see only numbered buttons on phone (read proposal text from projector)
- Off-limits: rape, trashing religions, slurs, real atrocities (enforced in AI prompts)

## Resources Available

- Omar's laptop (host machine)
- University projector + big screen
- Students' phones (20+ concurrent users likely)
- ngrok free tier (already set up and tested)
- OpenRouter API key (configured in .env)

---

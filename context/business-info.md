# Business Info

> Not applicable — this is a university course project, not a business context.

## Project Overview

**Econoland v2 — Parliament Edition** — a multiplayer classroom political simulation built in Python for a university programming course.

### The Game in One Sentence

A live economy simulation projected on a big screen where a randomly elected "parliament" of students writes policy proposals on their phones (character by character, visible to the whole class), the rest of the class votes on which proposal to enact, and an AI secretly grades every proposal — revealed only at game over.

### What Makes It Different From Kahoot

This is NOT a quiz. The key differentiators:

1. **Players create the content** — parliament members write their own policy proposals live on their phones. The class watches them type character by character on the projector. No pre-written options.
2. **Living simulation** — the projector shows a real-time economy dashboard (GDP, inflation, employment, etc.) that visibly changes each round. Decisions compound: print money in round 2, face hyperinflation by round 5.
3. **The projector IS the show** — phones are just remotes. The entertainment is watching parliament scramble to write proposals, the economy crumble, and the AI roast everyone at the end.
4. **Two scoring systems** — parliament scores by total votes received (popularity). People score by cumulative AI quality of proposals they voted for (judgment). Nobody sees AI scores until the end.
5. **Social dynamics** — watching who writes what, who copies who, and vote distributions creates inherent drama. The AI calls out copiers publicly at game over.
6. **LLM-generated compounding narrative** — an LLM generates every scenario in real time based on full history. It also evaluates proposals and generates a satirical end-game narrative.
7. **Two modes** — Constructive (build the best economy, names revealed) and Destructive (collapse it fastest, names anonymous).

### Core Mechanics

1. **Settings screen**: Host configures mode, number of rounds (3/5/7), parliament size, timers, anonymous/revealed
2. **Lobby**: QR code on projector → students join on phones → host clicks Start
3. **Role assignment**: System randomly picks 3-5 parliament members, rest are "The People"
4. **Each round (3 phases)**:
   - **Writing**: Scenario appears on projector. Parliament types proposals (200 char max, live on projector). People watch. Copy disclaimer visible. Auto-locks at timer end.
   - **Voting**: Proposals finalized on projector. People vote via numbered buttons on phone (read text from projector). AI grades proposals in parallel. Live vote bars on projector.
   - **Results**: Winner displayed, economy updates, AI generates next scenario in parallel. If tied: tiebreaker vote.
5. **Game Over**: Final economy state → AI Reveal (hidden scores + commentary for every proposal every round) → Parliament leaderboard → People leaderboard → Awards → Satirical narrative

### Tone & Vibe

- Witty and satirical, not edgelord — "satirical Economist article" meets "Cards Against Humanity"
- Absurdist humor > shock value — "Abolish weekdays" is funnier than just being offensive
- Economic concept wordplay — "quantitative squeezing," "trickle-sideways economics"
- Dark but classroom-safe — The Purge references, dystopian scenarios, absurd bureaucracy
- Current events twisted satirically — real Feb-Mar 2026 headlines remixed into the game world
- Adaptive — the AI mirrors the class's energy based on past decisions
- Hard red lines: no rape, no trashing religions, no slurs, no real atrocities

### Tech Stack

- Python (primary language — this is a Python course)
- FastAPI + WebSockets for real-time multiplayer with role-based messaging
- OpenRouter API → Grok (`x-ai/grok-4.1-fast`) for scenario generation, proposal evaluation, and narrative
- httpx for async API calls (parallel AI calls during human activity phases)
- Vanilla HTML/JS for two frontend pages (host.html + player.html)
- ngrok for tunneling (university WiFi is strict)
- qrcode library for QR generation

---

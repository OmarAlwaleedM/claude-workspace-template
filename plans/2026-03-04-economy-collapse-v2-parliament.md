# Economy Collapse Speedrun v2 — Parliament Edition

**Created:** 2026-03-04
**Status:** Final Concept — Ready for Implementation
**Context:** Pivot from AI-generated options to player-generated proposals

---

## 1. The Core Idea

The game is a **political simulation**. A real-world economic scenario appears on the projector. A small group of randomly elected **Parliament** members write policy proposals live on their phones — character by character, visible to the entire class on the projector in real time. The rest of the class — **The People** — watch parliament scramble, then vote on which proposal to enact. An AI evaluates each proposal behind the scenes. Nobody sees those AI scores until the game is over.

Two modes: **Constructive** (build the best economy, names revealed by default) and **Destructive** (collapse it fast, names anonymous by default).

The host is just the platform. The edgy, funny, or brilliant content comes entirely from the students.

**Responsive design**: the website works on both computers and phones.

---

## 2. Roles

### Parliament (3-5 players, randomly assigned at game start)
- Each round: see the scenario on the main screen, type a policy proposal on their phone (max 200 chars, auto-locks when time runs out — no submit button)
- Their typing appears live on the projector character by character — the whole class watches them write
- Parliament can see each other's proposals on the projector (they can see the main screen) — if they copy each other, the AI penalizes both with lower scores
- Parliament CANNOT vote
- Scoring: total votes received across all rounds

### The People (~90% of class)
- Watch scenario + parliament proposals on the projector (the main screen is the shared experience)
- On their phone: they see only numbered buttons (Proposal 1, 2, 3, etc.) — they read the actual proposal text from the projector, not their phone. This keeps everyone looking at the same place.
- Vote for one proposal each round
- Scoring: cumulative AI quality scores of proposals they voted for (hidden until end)

---

## 3. Game Settings

| Setting | Options | Default (Constructive) | Default (Destructive) |
| --- | --- | --- | --- |
| Game Mode | Constructive / Destructive | — | — |
| Game Duration | 3 / 5 / 7 / 10 minutes | 5 min | 5 min |
| Parliament Size | 3 / 4 / 5 members | 4 | 4 |
| Names | Anonymous / Revealed | **Revealed** | **Anonymous** |
| Proposal Time | 20 / 30 / 40 seconds | 30 sec | 30 sec |
| Voting Time | 15 / 20 / 25 seconds | 20 sec | 20 sec |

When the host selects a game mode, the anonymous/revealed toggle auto-sets to the default for that mode (can still be overridden manually).

---

## 4. Game Flow — Round by Round

### Pre-Game

1. Host opens settings screen → configures game
2. QR code appears → students join and enter names
3. Host clicks Start Game → system randomly assigns Parliament
4. Projector announces roles. Phones show "You are Parliament" or "You are The People"

### Each Round (3 phases happening in parallel where possible)

```
┌──────────────────────────────────────────────────────────────────────┐
│ PHASE A: Scenario + Parliament Writing (30-40 sec)                   │
│                                                                      │
│ Projector: scenario headline + description + economy dashboard       │
│            + live parliament proposals (char by char)                 │
│            + disclaimer: "Copying yields lower AI scores"            │
│            + countdown timer                                         │
│                                                                      │
│ Parliament phones: text input (200 char max), timer, char counter    │
│ People phones: "Watch the main screen. Voting starts soon."          │
│                                                                      │
│ AT 0 SECONDS: Parliament inputs auto-lock (whatever they typed)      │
│                                                                      │
│ SIMULTANEOUSLY AT LOCK:                                              │
│   → Proposals sent to LLM for grading (AI Call #2)                   │
│   → Voting phase begins immediately                                  │
├──────────────────────────────────────────────────────────────────────┤
│ PHASE B: People Vote (15-20 sec) — AI grading runs in parallel       │
│                                                                      │
│ Projector: all proposals displayed (final text) + live vote bars     │
│            + countdown timer                                         │
│                                                                      │
│ People phones: numbered buttons only (Proposal 1, 2, 3...)          │
│                read actual text from the projector                    │
│ Parliament phones: "Waiting for the people to decide..."             │
│                                                                      │
│ Early skip: if all people voted, move on immediately                 │
│                                                                      │
│ BACKGROUND: AI is grading proposals right now                        │
│ BY END OF VOTING: AI grading should be complete                      │
├──────────────────────────────────────────────────────────────────────┤
│ PHASE C: Results + Next Scenario Generation (3-5 sec)                │
│                                                                      │
│ If votes are TIED between proposals:                                 │
│   → Tiebreaker vote: people vote between the tied proposals only     │
│   → This time they vote on the PERSON (if revealed) or proposal #   │
│   → 10 second tiebreaker, then results                               │
│                                                                      │
│ Projector: vote distribution chart + winning proposal highlighted    │
│            + economy dashboard updates with animation                 │
│            + news ticker updates                                     │
│                                                                      │
│ SIMULTANEOUSLY:                                                      │
│   → AI grades are now available → Python allocates scores            │
│   → Winning proposal impacts applied to economy                      │
│   → AI Call #1 fires: generate next scenario                         │
│     (sends: economy state + ALL previous winning policies            │
│      + vote counts per proposal per round)                           │
│                                                                      │
│ Parliament phones: "You received X votes this round"                 │
│ People phones: "Policy enacted: [winning text]"                      │
│                                                                      │
│ NEXT ROUND starts when scenario generation completes                 │
│ (should be ready by time results display finishes)                   │
└──────────────────────────────────────────────────────────────────────┘
```

### Game Over

When time runs out or economy collapses/thrives past threshold:

1. **Economy Final State** — dashboard in final form
2. **The AI Reveal** — for each round, show every proposal with its hidden AI score + AI commentary. "Proposal 2 (score: 34/100) — 'This would have caused hyperinflation. Creative, but suicidal.'" vs. "Proposal 3 (score: 87/100) — 'Actually brilliant. Nobody voted for it.'"
3. **Parliament Leaderboard** — ranked by total votes received
4. **People Leaderboard** — ranked by cumulative AI quality scores
5. **Awards:**
   - Constructive: **President** (parliament, most votes), **Chief Advisor** (person, best judgment)
   - Destructive: **Supreme Dictator** (parliament, most votes), **Minister of Chaos** (person, best destruction picks)
   - **The Whistleblower** (person who voted against majority most often)
6. **Post-Game Narrative** — AI-generated satirical summary of what happened

---

## 5. Scoring System

### Parliament Scoring (computed in Python, not by AI)

```
parliament_scores = {player_name: 0 for each parliament member}

Each round:
  for each parliament member:
    parliament_scores[name] += number_of_votes_received_this_round

Final ranking: sort by total votes (descending)
```

Simple. No AI involvement. Pure vote count.

### People Scoring (AI grades proposals, Python allocates points)

```
people_scores = {player_name: 0 for each person}

Each round:
  AI returns quality_score (1-100) for each proposal

  for each person:
    voted_for = their_vote_this_round  # e.g., Proposal 2
    quality = ai_evaluations[voted_for].quality_score
    people_scores[name] += quality

Final ranking: sort by cumulative quality (descending)
```

People don't see quality_scores until game over. They're voting blind on judgment.

### Copy Detection & Penalty (AI handles this)

The AI evaluation prompt explicitly checks for similarity between proposals. If two or more proposals are substantially similar:
- Both/all get penalized: quality_score capped at 20
- AI commentary calls it out: "Nice copy-paste job. Both of you get participation trophies."
- This is visible in the end-game AI reveal

The projector always shows a permanent disclaimer at the bottom during the writing phase: **"⚠ Copying yields lower AI scores"**

### Economy Updates (computed in Python)

```
Each round:
  winning_proposal = proposal with most votes (or tiebreaker winner)
  winning_impacts = ai_evaluations[winning_proposal].impacts

  economy.apply_policy(winning_impacts)
  economy.add_destruction_points(ai_evaluations[winning_proposal].destruction_points)
```

---

## 6. Tiebreaker System

When two or more proposals have the same number of votes:

1. The tied proposals are highlighted on the projector
2. A tiebreaker vote starts: people vote ONLY between the tied proposals
3. In this special round, people vote on the **person** (if revealed mode) or the **proposal number** (if anonymous) — not the policy text
4. Tiebreaker lasts 10 seconds
5. If still tied after tiebreaker: random selection between tied proposals
6. Parliament members not in the tie are eliminated for this round — their proposal doesn't get enacted regardless

---

## 7. LLM API Call Timing (Optimized for Zero Wait)

The critical insight: **make LLM calls while humans are busy doing something**.

```
TIMELINE FOR ROUND N:

T=0     Scenario for Round N is already generated (from previous round's results phase)
        → Display scenario + parliament starts writing

T=0-35  Parliament writing (35 sec)
        → No LLM calls. Humans are busy.

T=35    Parliament locked. TWO things happen simultaneously:
        → PEOPLE start voting (15-20 sec)
        → LLM CALL #2 fires: evaluate/grade parliament proposals

T=35-55 Voting phase (20 sec) + AI grading (runs in parallel)
        → AI should finish grading in 3-5 sec, well before voting ends
        → When AI finishes: store grades in memory, don't display yet

T=55    Voting ends. Results computed instantly (all data is ready):
        → Vote counts already tracked in Python
        → AI grades already in memory
        → Apply winning policy impacts to economy
        → Display results (3-5 sec)

T=55    SIMULTANEOUSLY with results display:
        → LLM CALL #1 fires: generate next scenario
          Input: updated economy state + full policy history with vote counts

T=58-60 Results display finishes
        → Next scenario should be ready (LLM had 3-5 sec during results)
        → If not ready: show loading message ("The economy is processing...")

T=60    Round N+1 begins with pre-generated scenario
```

**For Round 1 specifically:**
- Scenario must be generated before the game starts (blocking call during "Starting game...")
- Pre-generate it when host clicks Start Game, show loading overlay

**Fallback if AI is slow:**
- If grading isn't done by end of voting: wait up to 5 more seconds with loading message, then use fallback scores (all proposals get 50/100)
- If scenario generation isn't done by results end: show loading message, wait up to 10 seconds

---

## 8. Complete Data Model — What's Stored Where

### Server-Side State (Python — game.py)

```python
class Game:
    # Settings
    settings: GameSettings          # mode, duration, parliament_size, anonymous, timers

    # Players
    players: dict[str, PlayerData]  # name → {role, score, connected, votes_received (parliament only)}
    parliament_members: list[str]   # names of parliament members
    people_members: list[str]       # names of people

    # Economy
    economy: Economy                # 6 indicators + destruction_score

    # Game State
    started: bool
    game_over: bool
    start_time: float
    round_number: int
    current_phase: str              # "lobby" | "writing" | "voting" | "tiebreaker" | "results" | "gameover"

    # Current Round
    current_scenario: dict          # {headline, description, news_ticker}
    proposals: dict[str, str]       # parliament_name → proposal_text (live, updated char by char)
    proposal_locked: dict[str, bool]  # parliament_name → whether input is locked
    votes: dict[str, int]           # person_name → proposal_index they voted for
    ai_evaluations: dict | None     # AI grades for current round (None until grading completes)

    # History (persists across rounds, sent to LLM for context)
    round_history: list[RoundRecord]  # full history of every round

    # Pre-generated
    next_scenario: dict | None      # pre-generated scenario for next round
    grading_task: asyncio.Task | None   # background AI grading task
    scenario_task: asyncio.Task | None  # background scenario generation task

class RoundRecord:
    round_number: int
    scenario: dict                  # headline, description
    proposals: list[ProposalRecord] # all proposals submitted
    winning_proposal_index: int
    vote_counts: dict[int, int]     # proposal_index → vote count
    economy_before: dict
    economy_after: dict

class ProposalRecord:
    parliament_member: str
    text: str
    votes_received: int
    ai_quality_score: int           # 1-100 (hidden until game over)
    ai_impacts: dict                # {gdp: X, employment: X, ...}
    ai_destruction_points: int
    ai_commentary: str              # witty one-liner (hidden until game over)

class PlayerData:
    role: str                       # "parliament" | "people"
    score: int                      # cumulative
    connected: bool
    votes_received: int             # parliament only: total votes across all rounds
```

### What Gets Sent Where

#### To the Projector (Host WebSocket) — sees everything visual

| Phase | Data Sent |
| --- | --- |
| Lobby | player names, player count, settings, QR URL |
| Role Reveal | parliament member names (or "anonymous" labels), people count |
| Writing Phase | scenario (headline, description), economy state, destruction score, live proposal text (char by char updates), timer, copy disclaimer |
| Voting Phase | final proposal texts (locked), live vote counts per proposal, timer |
| Tiebreaker | tied proposal indices, tiebreaker vote counts, timer |
| Results | vote distribution, winning proposal, economy before/after, destruction score delta, news ticker |
| Game Over | final economy, AI reveal (all proposals + hidden scores + commentary per round), parliament leaderboard, people leaderboard, awards, narrative |

#### To Parliament Phones — only their own input + minimal info

| Phase | Data Sent |
| --- | --- |
| Role Reveal | "You are Parliament. Your role: propose policies." |
| Writing Phase | scenario (headline, description), timer, char limit (200). They type locally, send keystrokes to server. |
| Voting Phase | "The people are voting on your proposals. Watch the main screen." |
| Results | "You received X votes this round. Running total: Y." |
| Game Over | personal stats: total votes received, rank among parliament, AI scores for their proposals, any awards |

#### To People Phones — only numbered buttons + minimal info

| Phase | Data Sent |
| --- | --- |
| Role Reveal | "You are The People. Your role: vote for the best policy." |
| Writing Phase | "Watch the main screen. Parliament is writing proposals. Voting starts soon." |
| Voting Phase | number of proposals (e.g., 4 buttons: "1", "2", "3", "4"), timer. NO proposal text on phone — read from projector. |
| Tiebreaker | tied proposal numbers only (e.g., buttons "2" and "4"), timer |
| Results | "Policy enacted: [winning text]" |
| Game Over | personal stats: cumulative AI quality score, rank among people, per-round breakdown of what they voted for + AI score, any awards |

---

## 9. LLM Prompts

### Prompt 1: Scenario Generation

```
You are the scenario generator for "Economy Collapse Speedrun," a live multiplayer
political simulation game played in a university economics classroom.

GAME MODE: {constructive|destructive}

CURRENT ECONOMY STATE:
{economy_state_json}

FULL POLICY HISTORY (every enacted policy from previous rounds, with vote counts):
{round_history_json}

ROUND NUMBER: {round_number}

CURRENT WORLD EVENTS (Feb-Mar 2026 — twist these into satirical references):
{news_context}

Generate the next scenario. A group of parliament members will write policy proposals
in response to this scenario. Return ONLY valid JSON:

{
  "headline": "Short punchy crisis headline (max 15 words)",
  "description": "2-3 sentences. MUST reference and build on previous enacted policies. The economy has been shaped by every past decision.",
  "news_ticker": ["4-5 satirical headlines/fake tweets. Mix game events with twisted real-world references."]
}

TONE: Satirical Economist meets Cards Against Humanity. Witty, not edgelord.
Absurdist humor > shock value. Reference real economic concepts with twists.
COMPOUNDING: Every scenario builds on ALL previous decisions. Never ignore history.
{mode_specific_instruction}

HARD RED LINES: No sexual violence, no religious attacks, no slurs, no real atrocities.
```

Where `{mode_specific_instruction}` is:
- Constructive: "The scenario should present genuine economic challenges that require thoughtful solutions."
- Destructive: "The scenario should present crises that invite creative chaos. Be dark, be funny."

### Prompt 2: Proposal Evaluation

```
You are an economics AI evaluator for a classroom simulation game.

GAME MODE: {constructive|destructive}
CURRENT SCENARIO:
  Headline: {headline}
  Description: {description}
CURRENT ECONOMY STATE: {economy_state_json}

PARLIAMENT PROPOSALS (evaluate each independently):
{numbered list: "1. [proposal text]", "2. [proposal text]", etc.}

TASK: Evaluate each proposal. Return ONLY valid JSON:

{
  "evaluations": [
    {
      "proposal_index": 1,
      "quality_score": 0-100,
      "impacts": {"gdp": X, "employment": X, "inflation": X, "public_trust": X, "trade_balance": X, "national_debt": X},
      "destruction_points": X,
      "ai_commentary": "Witty 1-sentence analysis (revealed at end of game)"
    }
  ]
}

SCORING:
- Constructive: quality_score = economic soundness + creativity (higher = better policy)
- Destructive: quality_score = destructive creativity + economic logic of why it's devastating (higher = more destructive)

COPY DETECTION — CRITICAL:
- If two or more proposals are substantially similar in meaning or wording:
  - Cap ALL similar proposals at quality_score = 15 maximum
  - ai_commentary MUST call out the copying explicitly and roast them
  - This is the #1 rule. Copying = punishment.

IMPACT RULES:
- Impacts: integers between -30 and +30, economically semi-plausible
- destruction_points: positive = helps economy, negative = hurts economy
- Constructive mode: good proposals have positive destruction_points
- Destructive mode: devastating proposals have large negative destruction_points

EDGE CASES:
- Gibberish/too short/off-topic → quality_score 5-15, neutral impacts, roast in commentary
- Offensive beyond classroom-appropriate → quality_score 5, neutral impacts, note it diplomatically
```

### Prompt 3: End-Game Narrative

```
Summarize what happened to this economy in 3-4 satirical sentences.

Game mode: {constructive|destructive}
Economy started at: {starting_state}
Economy ended at: {final_state}
Rounds played: {n}
Policies enacted (in order): {policy_list}
Did the economy collapse? {yes/no}

Write like a news anchor wrapping up a segment. Be funny and reference the specific
policies that were enacted. Audience: 20-year-old economics students.
```

---

## 10. WebSocket Message Types

### Server → Host

| Message Type | When | Payload |
| --- | --- | --- |
| `lobby_update` | Player joins/leaves | `{players, player_count, min_players}` |
| `settings_update` | Settings changed | `{settings}` |
| `role_reveal` | Game starts | `{parliament: [...], people_count, settings}` |
| `writing_phase` | Round begins | `{round, scenario, economy, destruction_score, timer, proposals: {}}` |
| `proposal_keystroke` | Parliament types | `{parliament_index, text}` (sent on every keystroke) |
| `voting_phase` | Writing ends | `{proposal_count, proposals_final: [...], timer}` |
| `vote_update` | Person votes | `{vote_counts, total_voted, total_people}` |
| `tiebreaker` | Votes tied | `{tied_indices, timer}` |
| `tiebreaker_update` | Tiebreaker vote | `{vote_counts}` |
| `round_end` | Round complete | `{vote_counts, winning_index, winning_text, impacts, old_economy, new_economy, destruction_score}` |
| `timer` | Every second | `{phase, phase_remaining, game_remaining}` |
| `loading` | AI is slow | `{message}` |
| `game_over` | Game ends | `{collapsed, destruction_score, final_economy, ai_reveal: [...], parliament_leaderboard, people_leaderboard, awards, narrative}` |

### Server → Parliament Phone

| Message Type | When | Payload |
| --- | --- | --- |
| `role_assigned` | Game starts | `{role: "parliament", parliament_index}` |
| `writing_phase` | Round begins | `{round, scenario, timer, char_limit: 200}` |
| `input_locked` | Time up | `{final_text}` |
| `voting_started` | Voting begins | `{message: "The people are deciding..."}` |
| `round_result` | Round ends | `{votes_received, running_total}` |
| `game_over` | Game ends | `{personal_stats, rank, ai_scores_for_your_proposals, awards}` |

### Server → People Phone

| Message Type | When | Payload |
| --- | --- | --- |
| `role_assigned` | Game starts | `{role: "people"}` |
| `writing_phase` | Round begins | `{round, message: "Watch the main screen."}` |
| `voting_phase` | Voting begins | `{proposal_count, timer}` (NO text, just count for numbered buttons) |
| `vote_confirmed` | After voting | `{voted_for}` |
| `tiebreaker` | Votes tied | `{tied_indices, timer}` |
| `round_result` | Round ends | `{winning_text}` |
| `game_over` | Game ends | `{personal_stats, rank, per_round_breakdown, awards}` |

### Client → Server

| Message Type | From | Payload |
| --- | --- | --- |
| `keystroke` | Parliament | `{text}` (full current text, sent on every keystroke) |
| `vote` | People | `{proposal_index}` |
| `tiebreaker_vote` | People | `{proposal_index}` |

---

## 11. Revised Round Pacing

```
PHASE A — Scenario + Writing: 30-35 seconds
  ├─ Scenario + parliament proposals shown simultaneously on projector
  ├─ Parliament typing live (char by char on projector)
  ├─ People watching main screen
  ├─ Copy disclaimer visible
  └─ At 0: inputs auto-lock

PHASE B — Voting + AI Grading: 15-20 seconds (parallel)
  ├─ People vote (numbered buttons on phone, text on projector)
  ├─ AI grading proposals in background
  ├─ Live vote bars on projector
  └─ Early skip if all people voted

PHASE C — Results + Next Scenario Gen: 3-5 seconds (parallel)
  ├─ (If tied: 10-second tiebreaker first)
  ├─ Results displayed
  ├─ Economy updates
  ├─ AI generates next scenario in background
  └─ Scores allocated in Python

TOTAL PER ROUND: ~50-60 seconds (no wasted time)
For 5-minute game: ~5-6 rounds
```

No dead time. Every second has either humans doing something or AI processing in parallel.

---

## 12. Responsive Design

Both host.html and player.html must work on desktop and mobile.

### host.html
- Default: optimized for 1920x1080 projector (current design)
- Also works in any desktop browser window (responsive scaling)
- Not expected to be used on phones

### player.html
- Mobile-first: large touch targets, full-width buttons
- Also works on desktop/laptop browsers
- Parliament UI: responsive text input with character counter
- People UI: responsive numbered buttons (big, clear, easy to tap)
- Adapts to screen size via CSS media queries / viewport units

---

## 13. Technical Architecture

### File Structure (updated from v1)
```
economy-collapse-speedrun/
├── server.py              # FastAPI — endpoints, WebSockets, phase management, broadcast logic
├── game.py                # Game state: settings, roles, rounds, proposals, votes, scoring, history
├── economy.py             # Economy model (keep from v1)
├── llm.py                 # OpenRouter: scenario generation + proposal evaluation + end narrative
├── config.py              # Base config + GameSettings dataclass
├── static/
│   ├── host.html          # Projector: settings → lobby → writing → voting → results → gameover
│   └── player.html        # Phone: role-based UI (parliament input / people voting)
├── .env
├── requirements.txt
└── README.md
```

### Dependencies (same as v1)
```
fastapi
uvicorn[standard]
websockets
qrcode[pil]
httpx
python-dotenv
```

---

## 14. Resolved Design Questions

| # | Question | Decision |
| --- | --- | --- |
| 1 | Live typing or submit? | **Live, character by character.** Parliament can see each other on the projector. Copying is penalized by AI and flagged by a permanent disclaimer on screen. |
| 2 | Can parliament see each other? | **Yes, via the projector.** They see all proposals live on the main screen. Copying is penalized. The disclaimer "Copying yields lower AI scores" is always visible during writing. |
| 3 | What if parliament doesn't finish? | **Auto-lock at timer end.** Whatever they've typed is their proposal. No submit button needed. If empty: skipped for that round, 0 votes. |
| 4 | Rotate parliament? | **No.** Fixed for the whole game. Creates competitive identity. Too complex to rotate and removes competitive dynamics. Maybe later. |
| 5 | Tiebreaker? | **Revote between tied proposals only.** People vote on the person (if revealed) or proposal number (if anonymous). 10 seconds. If still tied: random. |
| 6 | Max proposal length? | **200 characters.** Forces brevity, keeps projector clean. |
| 7 | Default anonymous/revealed? | **Constructive = Revealed. Destructive = Anonymous.** Can be overridden in settings. |
| 8 | What do people see on phone? | **Numbered buttons only during voting.** They read proposal text from the projector. This keeps everyone focused on the same screen. |
| 9 | What do parliament see on phone? | **Only their own text input.** Everything else (other proposals, scenario) they read from the projector. |
| 10 | Responsive? | **Yes.** Both computer and phone compatible. Mobile-first for player.html. |

---

## 15. Implementation Steps

### Phase 1: Core Game Refactor (game.py)
- [ ] Add GameSettings dataclass (mode, duration, parliament_size, anonymous, proposal_time, voting_time)
- [ ] Add PlayerData with role tracking
- [ ] Add random parliament assignment at game start
- [ ] Refactor round phases: writing → voting → (tiebreaker) → results
- [ ] Add proposal collection: store partial text from keystrokes, lock at timer end
- [ ] Add vote collection with tiebreaker detection and tiebreaker round
- [ ] Add RoundRecord and round_history for full game context
- [ ] Parliament scoring: count votes per member per round, accumulate
- [ ] People scoring: store AI quality scores, allocate to voters, accumulate
- [ ] Copy detection: handled by AI prompt, but store the flag from AI response
- [ ] Pre-generate scenario for next round during results phase

### Phase 2: LLM Integration (llm.py)
- [ ] Refactor scenario generation prompt (no options, just scenario + news ticker)
- [ ] Add proposal evaluation function (new prompt, receives all proposals, returns grades)
- [ ] Add copy detection instruction in evaluation prompt
- [ ] Add end-game narrative generation function
- [ ] Handle edge cases: empty proposals, gibberish, AI timeout
- [ ] Ensure all calls are async + non-blocking
- [ ] Proper input: send round_history with vote counts to scenario generation

### Phase 3: Server Refactor (server.py)
- [ ] Add settings endpoint: POST /settings
- [ ] Refactor WebSocket handling: role-based message routing
- [ ] Parliament keystroke handler: receive text updates, broadcast to host
- [ ] Phase timer management: writing timer → voting timer → (tiebreaker timer) → results
- [ ] Parallel execution: fire AI grading at writing end, fire scenario gen at results start
- [ ] Tiebreaker flow: detect tie, initiate tiebreaker vote, handle second tie (random)
- [ ] Vote counting and score allocation in Python (not AI)
- [ ] Game over detection and final results compilation including AI reveal data
- [ ] Loading state handling for slow AI

### Phase 4: Host Display (host.html)
- [ ] Settings screen overlay (before lobby)
- [ ] Lobby with QR code (carry from v1)
- [ ] Role reveal overlay ("Parliament has been elected!")
- [ ] Writing phase: split layout — scenario left, live proposals right (char by char updating)
- [ ] Copy disclaimer permanently visible during writing: "⚠ Copying yields lower AI scores"
- [ ] Voting phase: proposals displayed (final text) + live vote bars
- [ ] Tiebreaker overlay: tied proposals highlighted, tiebreaker vote bars
- [ ] Results: vote chart + winning proposal + economy animation (carry from v1, adapt)
- [ ] Game over: AI reveal per round + leaderboards + awards + narrative
- [ ] News ticker (carry from v1)
- [ ] Responsive CSS (works in any desktop browser, optimized for 1920x1080)

### Phase 5: Player UI (player.html)
- [ ] Join screen (carry from v1)
- [ ] Role reveal screen: "You are Parliament" / "You are The People" with distinct styling
- [ ] Parliament writing screen: text input, char counter (X/200), timer, auto-lock at 0
- [ ] Parliament waiting screen: "The people are deciding..."
- [ ] Parliament result screen: "You received X votes"
- [ ] People writing phase screen: "Watch the main screen. Voting starts soon."
- [ ] People voting screen: numbered buttons ONLY (no proposal text), timer
- [ ] People tiebreaker screen: only tied proposal numbers as buttons
- [ ] People vote confirmed screen
- [ ] Game over screen: personal stats, rank, per-round breakdown, awards
- [ ] Responsive CSS: mobile-first, also works on desktop

### Phase 6: Config & Setup
- [ ] Update config.py with GameSettings
- [ ] Update .env template (already has API key and ngrok URL)
- [ ] Update README with new game flow

### Phase 7: Testing
- [ ] Unit test: economy model (carry from v1)
- [ ] Unit test: vote counting, tiebreaker detection, score allocation
- [ ] Integration test: 1 parliament + 2 people on phones via ngrok
- [ ] Test constructive mode with revealed names
- [ ] Test destructive mode with anonymous names
- [ ] Test tiebreaker flow
- [ ] Test empty proposal / disconnect edge cases
- [ ] Test AI grading parallel timing (does it finish before voting ends?)
- [ ] Test responsive layout on phone and desktop
- [ ] Full demo rehearsal (5-minute game)

---

## 16. What We Keep from v1

| Component | Status |
| --- | --- |
| config.py | Extend with GameSettings, keep base config |
| economy.py | **Keep as-is** — no changes needed |
| game.py | Heavy refactor: new phases, roles, proposals, history. Same class structure. |
| llm.py | Keep scenario gen (adapt prompt), add evaluation + narrative functions |
| server.py | Refactor: role-based WebSockets, phase management, parallel AI calls |
| host.html | Major extension: settings, writing phase, tiebreaker, AI reveal. Keep dashboard + ticker. |
| player.html | Rewrite: role-based UI with parliament input and people numbered buttons |
| requirements.txt | **Keep as-is** |
| .env | **Keep as-is** (already has API key + ngrok URL + model) |
| ngrok | **Keep as-is** |
| Economy dashboard | Keep: bars, colors, animations, news ticker |
| QR code flow | **Keep as-is** |
| Lobby flow | Keep, add settings screen before it |

---

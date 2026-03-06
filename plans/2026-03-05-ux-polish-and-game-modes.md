# Plan: UX Polish, Game Mode Fixes, Rename & Architecture Cleanup

**Created:** 2026-03-05
**Status:** Implemented
**Request:** Fix multiple UX issues: add game termination, reduce AI verbosity, fix constructive mode labels, rename the game, show join URL on lobby screen, replace time-based duration with round-based system, and ensure game modes are fully distinct.

---

## Overview

### What This Plan Accomplishes

A comprehensive UX and architecture pass across the entire game — backend, frontend, and AI prompts — to fix broken labels, add missing features (terminate button, join URL), replace the flawed time-based duration system with a round-based one, reduce AI text verbosity, rename the game from "Economy Collapse Speedrun" to something appropriate, and ensure constructive vs destructive modes are truly distinct throughout the entire stack.

### Why This Matters

The game is feature-complete but has UX issues that would be embarrassing in a live classroom demo. A "DESTRUCTION: 0" label in constructive mode, an old name that doesn't fit, overly verbose AI text cluttering the screen, and a duration system that starts new rounds the game can't finish — these all undermine the polished impression needed for a good grade and a fun experience.

---

## Current State

### Relevant Existing Structure

| File | Role |
|------|------|
| `economy-collapse-speedrun/config.py` | `GameSettings` dataclass with `duration_seconds` field |
| `economy-collapse-speedrun/game.py` | Game state, `is_game_over()` checks time, `get_time_remaining()` |
| `economy-collapse-speedrun/economy.py` | Economy model, `get_destruction_score()`, `is_collapsed()` |
| `economy-collapse-speedrun/server.py` | Phase management, `game_timer_loop()`, FastAPI app title |
| `economy-collapse-speedrun/llm.py` | AI prompts, `_call_llm()` max_tokens, prompt templates |
| `economy-collapse-speedrun/static/host.html` | Host UI — settings, lobby, game phases, game over |
| `economy-collapse-speedrun/static/player.html` | Player UI — join, role, writing, voting, game over |

### Gaps or Problems Being Addressed

1. **No way to terminate a game mid-session** — once started, the host has no abort/end button
2. **AI is too verbose** — too much text on screen (news ticker 8 items, long descriptions, lengthy commentary)
3. **Constructive mode shows "DESTRUCTION: 0"** — the top-right badge always says "DESTRUCTION" regardless of mode
4. **Game still called "Economy Collapse Speedrun"** — title, HTML titles, API headers, prompts all use old name
5. **Lobby screen only shows QR code** — the join URL exists in code but isn't visible/prominent enough
6. **Time-based duration creates impossible rounds** — a 5-min game can start a 2-min round with 20 seconds left, which is nonsensical
7. **Game modes not fully distinct** — destructive mode uses `destruction_score` and `destruction_points` but constructive mode has no equivalent positive metric; labels, badges, and AI behavior need mode differentiation

---

## Proposed Changes

### Summary of Changes

- **Rename game** to "Econoland" (short, memorable, matches the fictional country name already used in all prompts)
- **Replace `duration_seconds` with `num_rounds`** in settings — options: 3, 5, 7 rounds
- **Remove `game_timer_loop`** and time-based game-over logic entirely
- **Add "End Game" button** to host top bar (visible during gameplay, requires confirmation)
- **Add terminate WebSocket action** so host can end game from the UI
- **Reduce AI verbosity**: cut news_ticker from 8 to 5 items, cap scenario descriptions at 2 sentences, cap AI commentary at 1 sentence, reduce max_tokens across all LLM calls
- **Fix destruction/prosperity badge** — show "DESTRUCTION: X" in destructive mode, "PROSPERITY: X" in constructive mode
- **Rename `destruction_score` / `destruction_points`** in economy.py to a neutral `score` / `score_points`, with display label determined by mode
- **Make join URL prominent** on lobby screen — large clickable link below QR code
- **Update all HTML `<title>` tags** and references to old name
- **Update LLM prompt headers** and API X-Title to new name
- **Ensure constructive mode AI** doesn't reference destruction, chaos, or collapse in its prompts
- **Remove game timer display** from host top bar (replaced by round counter like "Round 2 of 5")

### Files to Modify

| File | Changes |
|------|---------|
| `config.py` | Replace `duration_seconds` with `num_rounds: int = 5`. Remove duration from `to_dict`/`from_dict`. |
| `game.py` | Remove `start_time`, `get_time_remaining()`. Change `is_game_over()` to check `round_number >= settings.num_rounds` (checked AFTER a round completes). Rename `destruction_score` references. Add `terminate_game()` method. |
| `economy.py` | Rename `destruction_score` to `score`, `add_destruction_points` to `add_score_points`, `get_destruction_score` to `get_score`. Keep `is_collapsed()` for early game-over in destructive mode only. |
| `server.py` | Remove `game_timer_task` and `game_timer_loop()`. Add `terminate` WebSocket action for host. Update FastAPI title. Update `start_game_endpoint` to not start game timer. Update `finalize_round` to check round count for game over. Remove `time_remaining` from all broadcasts. Add `num_rounds` to broadcasts so host knows total. |
| `llm.py` | Reduce `news_ticker` from 8 to 5 items in prompt. Shorten description instruction to "1-2 sentences". Cap `ai_commentary` instruction to "1 SHORT sentence". Reduce `max_tokens` (scenario: 600→400, evaluation: 1500→800, narrative: 300→200). Update game name in prompts. Update `X-Title` header. |
| `static/host.html` | Rename title. Replace duration settings with round count settings (3/5/7 rounds). Remove game timer from top bar. Add round progress display ("Round X of Y"). Add "End Game" button in top bar. Fix destruction badge to be mode-aware ("PROSPERITY" vs "DESTRUCTION"). Make lobby URL more prominent. Remove `time_remaining` references. |
| `static/player.html` | Rename title and join screen text. Remove any time references. |
| `CLAUDE.md` | Update project name references. |
| `context/business-info.md` | Update game name. |

### Files to Delete

None.

---

## Design Decisions

### Key Decisions Made

1. **Name: "Econoland"** — It's already the name of the fictional country used in every AI prompt. Short, memorable, works for both modes. The full subtitle can be "Econoland — Parliament Edition" where needed.

2. **Round-based instead of time-based** — Replacing `duration_seconds` with `num_rounds` (3/5/7) completely eliminates the problem of starting a round that can't finish. Each round runs to natural completion (writing timer + voting timer + results). The game ends after the configured number of rounds OR if the economy collapses (destructive mode only).

3. **Economy collapse only ends game early in destructive mode** — In constructive mode, the economy collapsing shouldn't end the game early since the goal is to save it. Players should get all their rounds. In destructive mode, collapsing early IS the win condition, so it stays.

4. **Neutral internal naming, mode-specific display** — `economy.score` internally, displayed as "DESTRUCTION" or "PROSPERITY" based on mode. Cleaner than having two separate tracking systems.

5. **AI verbosity reduction via prompt constraints AND max_tokens** — Both the prompt instructions AND the token limits are tightened. The prompt tells the AI to be shorter, and the token cap enforces it.

6. **End Game button with confirmation** — A simple browser `confirm()` dialog prevents accidental termination. No need for a fancy modal.

### Alternatives Considered

- **"Parliament" as the game name** — Too generic, doesn't evoke the economic simulation aspect.
- **Keep time-based but prevent new rounds near end** — More complex, still leaves awkward "waiting for timer" periods. Round-based is cleaner.
- **Separate scoring systems for each mode** — Unnecessary complexity. A single score with different labels and AI behavior per mode achieves the same effect.

### Open Questions

1. **Should economy collapse end the game in constructive mode?** — Plan says NO (you get all rounds regardless), but Omar may prefer it ends early with a "you failed" message. **Recommend: No early end in constructive mode.**
2. **Fallback scenarios** — Should they also be shortened for verbosity? **Recommend: Yes, trim news_ticker to 4-5 items in fallbacks too.**

---

## Step-by-Step Tasks

### Step 1: Rename the Game

Update all references from "Economy Collapse Speedrun" to "Econoland".

**Actions:**

- `config.py`: No name references to change (clean)
- `server.py` line 27: Change FastAPI title to `"Econoland — Parliament Edition"`
- `llm.py` line 330: Change `X-Title` header to `"Econoland"`
- `llm.py` line 53: Change prompt text from `"Economy Collapse Speedrun"` to `"Econoland"` (in SCENARIO_PROMPT_TEMPLATE)
- `static/host.html` line 6: Change `<title>` to `"Econoland — Host"`
- `static/host.html` line 305: Change settings title text from `"ECONOMY COLLAPSE SPEEDRUN"` to `"ECONOLAND"`
- `static/player.html` line 6: Change `<title>` to `"Econoland"`
- `static/player.html` line 164: Change join screen title from `"ECONOMY COLLAPSE"` to `"ECONOLAND"`

**Files affected:**
- `server.py`, `llm.py`, `static/host.html`, `static/player.html`

---

### Step 2: Replace Duration with Round Count (Backend)

Remove time-based game logic and replace with round-based.

**Actions:**

- `config.py`:
  - Remove `duration_seconds: int = 300`
  - Add `num_rounds: int = 5` (options will be 3, 5, 7 in frontend)
  - Update `to_dict()` and `from_dict()` accordingly

- `game.py`:
  - Remove `self.start_time` from `__init__`
  - Remove `self.start_time = time.time()` from `start_game()`
  - Remove `import time` (if no longer needed)
  - Remove `get_time_remaining()` method entirely
  - Change `is_game_over()`:
    ```python
    def is_game_over(self) -> bool:
        if self.game_over:
            return True
        # Destructive mode: economy collapse = early win
        if self.settings.mode == "destructive" and self.economy.is_collapsed():
            return True
        return False

    def is_last_round(self) -> bool:
        """Check if current round is the last one."""
        return self.round_number >= self.settings.num_rounds
    ```

- `server.py`:
  - Remove `game_timer_task` global variable
  - Remove `game_timer_loop()` function entirely
  - Remove `game_timer_task = asyncio.create_task(game_timer_loop())` from `start_game_endpoint`
  - In `finalize_round()`: after round completes, check `game.is_last_round()` to trigger game over (replacing the mid-round time check)
  - Remove all `time_remaining` and `game_remaining` from broadcast messages
  - Remove `game.get_time_remaining()` calls

**Files affected:**
- `config.py`, `game.py`, `server.py`

---

### Step 3: Replace Duration with Round Count (Frontend)

Update settings UI and in-game display.

**Actions:**

- `static/host.html` — Settings screen:
  - Replace the "Game Duration" setting row with "Number of Rounds"
  - Options: 3 rounds, **5 rounds** (default), 7 rounds
  - Update `selectSetting` to handle `num_rounds` instead of `duration`
  - Update `gameSettings` default object

- `static/host.html` — Top bar:
  - Remove the game timer (`game-timer` element) from the top bar
  - Add round progress display: "ROUND X / Y" (e.g., "ROUND 2 / 5")
  - Update the round badge to show "ROUND X / Y" format

- `static/host.html` — JavaScript:
  - Remove all `time_remaining` and `game_remaining` handling
  - Remove game timer countdown logic
  - Store `num_rounds` (received from settings/game state) and display progress
  - Update timer messages to only show phase timers (writing/voting), not game timer

- `static/player.html`:
  - No duration/timer references to remove (player only sees phase timers)

**Files affected:**
- `static/host.html`, `static/player.html`

---

### Step 4: Add Game Termination

Allow host to end the game at any time during gameplay.

**Actions:**

- `static/host.html`:
  - Add an "END GAME" button in the top bar (red, positioned near the right side)
  - Style: small, red background, white text, with hover state
  - On click: `if (confirm('End the game now? This will show final results.')) { ws.send(JSON.stringify({action: 'terminate'})); }`
  - Only visible when game is in progress (not during settings/lobby/gameover)

- `server.py` — WebSocket host handler:
  - Add handler for `action == "terminate"`:
    ```python
    elif msg.get("action") == "terminate" and game.started and not game.game_over:
        game.game_over = True
        game.current_phase = "gameover"
        if phase_timer_task and not phase_timer_task.done():
            phase_timer_task.cancel()
        await send_game_over()
    ```

- `game.py`:
  - No changes needed — `game_over = True` flag is sufficient

**Files affected:**
- `static/host.html`, `server.py`

---

### Step 5: Fix Mode-Specific Badges and Scoring

Make constructive and destructive modes visually and mechanically distinct.

**Actions:**

- `economy.py`:
  - Rename `destruction_score` to `score`
  - Rename `add_destruction_points()` to `add_score_points()`
  - Rename `get_destruction_score()` to `get_score()`
  - Update `is_collapsed()` — keep as-is (it checks raw indicator values, not the score)

- `game.py`:
  - Update all references: `economy.get_destruction_score()` → `economy.get_score()`
  - Update all references: `economy.add_destruction_points()` → `economy.add_score_points()`
  - In `get_final_results()`: change key from `"destruction_score"` to `"score"`

- `server.py`:
  - Change all `destruction_score` keys in broadcast messages to `"score"`
  - Add `"mode"` to all relevant broadcasts so the frontend knows which label to show

- `static/host.html`:
  - Change the destruction badge to be mode-aware:
    - Store the game mode when received from settings
    - In destructive mode: show "DESTRUCTION: X" with red background
    - In constructive mode: show "PROSPERITY: X" with green background
  - Update all JavaScript references from `destruction_score` to `score`
  - Update the game-over screen to use mode-appropriate language

- `llm.py`:
  - In evaluation prompt, `destruction_points` field name stays in the JSON schema (it's internal), but update the scoring rubric text:
    - Constructive: "prosperity_points: positive = great policy impact"
    - Destructive: "destruction_points: positive = maximum chaos achieved"
  - Actually, keep the JSON field name `destruction_points` as-is to avoid breaking the eval parsing. Just change the display label in the frontend.

**Files affected:**
- `economy.py`, `game.py`, `server.py`, `static/host.html`, `llm.py`

---

### Step 6: Reduce AI Verbosity

Tighten all AI outputs to reduce on-screen text clutter.

**Actions:**

- `llm.py` — Scenario prompt (`SCENARIO_PROMPT_TEMPLATE`):
  - Change news_ticker instruction from "8 items total: 5 funny... PLUS 3 hints" to "5 items total: 3 funny/snarky headlines PLUS 2 hints"
  - Change description instruction: "1-2 sentences max. State the crisis clearly and end with the question to Parliament."
  - Change headline instruction: "max 10 words" (from 12)
  - Update JSON schema example to show 5 news_ticker items

- `llm.py` — Evaluation prompt (`EVALUATION_PROMPT_TEMPLATE`):
  - Change AI commentary instruction: "Keep it to 1 SHORT punchy sentence — like a tweet, not a paragraph"
  - Reduce max_tokens from 1500 to 800

- `llm.py` — Narrative prompt (`NARRATIVE_PROMPT_TEMPLATE`):
  - Change from "3-4 sentences" to "2-3 sentences"
  - Reduce max_tokens from 300 to 200

- `llm.py` — `_call_llm()` defaults:
  - Keep default max_tokens at 1000 (individual calls override this anyway)

- `llm.py` — `generate_scenario()`:
  - Reduce max_tokens from 600 to 400

- `llm.py` — Fallback scenarios:
  - Trim each fallback's `news_ticker` list from 4 items to 4 items (already fine), but the mode-specific additions in `get_next_fallback_scenario` add 2 more — reduce to 1 hint each

- `static/host.html` — News ticker display:
  - If the ticker area is too crowded, limit display to max 5 items
  - Ensure ticker text size is readable but compact

**Files affected:**
- `llm.py`, `static/host.html`

---

### Step 7: Make Lobby URL Prominent

Ensure the join URL is clearly visible alongside the QR code.

**Actions:**

- `static/host.html` — Lobby overlay:
  - The `lobbyUrl` div (line 378) already receives the URL via WebSocket `qr_url` message
  - Increase font size from 12px to 16px
  - Make it more prominent: white color instead of muted gray, bold
  - Add a "or visit:" label above it
  - Ensure the `<a>` tag is clearly styled as a clickable link
  - Add `user-select: all` so it's easy to copy

- `server.py`:
  - The URL is already being sent via `qr_url` message (line 631) — no backend changes needed
  - Verify the URL format is clean (no extra query params visible to users)

**Files affected:**
- `static/host.html`

---

### Step 8: Ensure Game Modes Are Fully Distinct

Audit and fix all mode-dependent behavior.

**Actions:**

- `static/host.html` — Settings screen:
  - Mode buttons should have clearly different colors and descriptions
  - Destructive: red theme, "Race to destroy Econoland's economy"
  - Constructive: green theme, "Build the strongest economy for Econoland"

- `static/host.html` — In-game:
  - Top bar background tint: subtle red for destructive, subtle green for constructive
  - Phase area scenario display: mode-appropriate framing

- `static/player.html` — Writing screen:
  - Mode reminder already exists (line 190) and switches between "DESTROY THE ECONOMY" / "SAVE THE ECONOMY" — this is good, keep it

- `llm.py` — Constructive mode prompt:
  - Verify `MODE_INSTRUCTIONS["constructive"]` never uses words like "destroy", "collapse", "worst"
  - Verify the scenario ending always says "BEST policy" not "WORST"
  - Verify evaluation in constructive mode rewards smart policies (positive impacts, positive destruction_points)

- `game.py` — Awards:
  - Constructive awards (line 459): "president", "chief_advisor" — good
  - Destructive awards (line 465): "supreme_dictator", "minister_of_chaos" — good
  - Verify both paths work correctly

- `game.py` — `is_game_over()`:
  - Constructive: game ends ONLY when all rounds are played (economy collapse does NOT end the game — you keep trying to save it)
  - Destructive: game ends when rounds are done OR economy collapses (collapse = speed win)

- `static/host.html` — Game over screen:
  - Constructive: "ECONOLAND SURVIVED!" or "ECONOLAND FELL!" with appropriate colors
  - Destructive: "ECONOMY DESTROYED!" or "ECONOMY SURVIVED (YOU FAILED!)" with appropriate colors

**Files affected:**
- `static/host.html`, `static/player.html`, `llm.py`, `game.py`

---

### Step 9: Update Documentation

Update CLAUDE.md and context files to reflect all changes.

**Actions:**

- `CLAUDE.md`:
  - Update project name from "Economy Collapse Speedrun" to "Econoland"
  - Update the active projects section
  - Update directory description

- `context/business-info.md`:
  - Update "Economy Collapse Speedrun v2 — Parliament Edition" → "Econoland — Parliament Edition"
  - Update "The Game in One Sentence" if needed
  - Note the round-based system instead of time-based

- `context/current-data.md`:
  - Update project status to reflect these changes

**Files affected:**
- `CLAUDE.md`, `context/business-info.md`, `context/current-data.md`

---

### Step 10: Test and Verify

Run through the full flow to verify all changes work.

**Actions:**

- Start the server: `cd economy-collapse-speedrun && python3 server.py`
- Verify settings screen shows "ECONOLAND" title and round count options (3/5/7)
- Select constructive mode → verify labels change to green/"PROSPERITY"
- Select destructive mode → verify labels change to red/"DESTRUCTION"
- Go to lobby → verify QR code AND prominent URL are visible
- Start game with at least 2 players (can use multiple browser tabs)
- Verify "End Game" button appears in top bar during gameplay
- Play through rounds → verify game ends after configured number of rounds
- Verify AI text is shorter (scenarios, commentary, narrative)
- Click "End Game" → verify confirmation dialog → verify game over screen shows
- Check constructive game over says "PROSPERITY" not "DESTRUCTION"
- Check player.html title says "Econoland" not "Economy Collapse"

**Files affected:**
- None (testing only)

---

## Connections & Dependencies

### Files That Reference This Area

| File | Reference |
|------|-----------|
| `CLAUDE.md` | Project name, directory listing, tech description |
| `context/business-info.md` | Full project overview with old name |
| `context/current-data.md` | Status tracker |
| `context/strategy.md` | References demo rehearsal |
| `plans/2026-03-04-economy-collapse-v2-parliament.md` | v2 plan (historical, no update needed) |
| `economy-collapse-speedrun/README.md` | Project readme |
| `economy-collapse-speedrun/how_to_start.md` | Startup guide |

### Updates Needed for Consistency

- All `<title>` tags in HTML files
- FastAPI app title in `server.py`
- `X-Title` header in `llm.py`
- Prompt text in `llm.py` (already uses "Econoland" internally, but header still says old name)
- CLAUDE.md workspace structure and active projects
- Context files

### Impact on Existing Workflows

- **Settings screen**: Duration replaced with round count — simpler for the host
- **Game flow**: No more game timer ticking — rounds just play sequentially until done
- **AI prompts**: Shorter outputs — faster API responses, less text to read
- **Host controls**: New "End Game" button adds safety net for live demo

---

## Validation Checklist

- [ ] All HTML `<title>` tags say "Econoland"
- [ ] Settings screen shows round count (3/5/7) instead of duration
- [ ] No `duration_seconds` or `time_remaining` in any broadcast messages
- [ ] `game_timer_loop` removed from server.py
- [ ] "End Game" button visible during gameplay, sends terminate action
- [ ] Host WebSocket handles "terminate" action correctly
- [ ] Constructive mode shows "PROSPERITY: X" badge (green)
- [ ] Destructive mode shows "DESTRUCTION: X" badge (red)
- [ ] Economy collapse only triggers game-over in destructive mode
- [ ] Lobby screen shows QR code AND prominent clickable URL
- [ ] AI scenario descriptions are 1-2 sentences max
- [ ] AI commentary is 1 sentence max
- [ ] News ticker has 5 items (not 8)
- [ ] AI narrative is 2-3 sentences max
- [ ] Game ends after configured number of rounds
- [ ] CLAUDE.md updated with new name
- [ ] Server starts without errors

---

## Success Criteria

The implementation is complete when:

1. The game can be configured with a number of rounds (3/5/7), plays exactly that many rounds, and never starts a round it can't finish
2. The host can terminate the game at any point during gameplay via an "End Game" button
3. Constructive and destructive modes are visually and mechanically distinct — different badges, colors, scoring labels, AI behavior, and game-over conditions
4. All references to "Economy Collapse Speedrun" are replaced with "Econoland"
5. The lobby screen clearly shows both QR code and clickable join URL
6. AI-generated text is noticeably shorter — scenarios, commentary, and narrative all fit comfortably on screen without overwhelming the viewer
7. The server starts without errors and a full game can be played through in both modes

---

## Notes

- The directory name `economy-collapse-speedrun/` is NOT renamed (would break git history and paths for no user-facing benefit). Only user-visible strings are updated.
- The `destruction_points` field in AI evaluation JSON is kept as-is in the LLM prompt to avoid breaking JSON parsing. Only the display label changes.
- Fallback scenarios already have 4 news_ticker items each, which is fine. The mode-specific additions in `get_next_fallback_scenario()` should add 1 hint instead of 2.
- The round-based system means a 5-round game with 120s writing + 45s voting + ~4s results display = ~14 min worst case. For the demo, 3 rounds is recommended (~8 min with AI latency).
- Consider adding a "LAST ROUND!" banner when `round_number == num_rounds` to build tension.

---

## Implementation Notes

**Implemented:** 2026-03-05

### Summary

All 9 implementation steps completed. The game is renamed to "Econoland", uses round-based system (3/5/7), has mode-specific badges (DESTRUCTION/PROSPERITY), reduced AI verbosity, prominent lobby URL, End Game button, and mode-specific game over messaging.

### Deviations from Plan

- Kept `destruction_points` field name in LLM evaluation JSON as planned (no change to avoid breaking parsing).
- The game timer case in host.html JS now simply `break`s instead of being removed entirely — cleaner than removing the case handler since the server could still theoretically send timer messages.

### Issues Encountered

None — all changes applied cleanly and server imports verified.

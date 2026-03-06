# Plan: Fix Timer Sync Bug & Replace Fixed Settings with Flexible Inputs

**Created:** 2026-03-05
**Status:** Implemented
**Request:** Fix the timer skipping its last seconds (e.g., goes from 5 to 0 abruptly) and replace fixed-option setting buttons with flexible number inputs for all game settings.

---

## Overview

### What This Plan Accomplishes

Fixes the timer desync bug where the countdown on player/host screens jumps from ~5 seconds to phase transition because the server timer and client timers drift apart. Also replaces the rigid fixed-option buttons (3/5/7 rounds, 3/4/5 parliament, etc.) in the settings screen with editable number inputs that allow any value within defined ranges, giving the host full control over game configuration.

### Why This Matters

The timer bug is visible and jarring during a live demo — students see "5 seconds left" then suddenly their input locks. It breaks trust in the countdown and causes frustration (especially parliament members mid-typing). The flexible settings give the host power to fine-tune the game for their specific class size and available time.

---

## Current State

### Relevant Existing Structure

| File | Role |
|------|------|
| `economy-collapse-speedrun/server.py` | Server-side phase timers (`writing_phase_timer`, `voting_phase_timer`, `tiebreaker_timer`) broadcast `phase_remaining` to **host only** |
| `economy-collapse-speedrun/static/host.html` | Receives server timer ticks but currently ignores them (`case 'timer': break;`). Settings UI uses fixed-option buttons. |
| `economy-collapse-speedrun/static/player.html` | Runs completely independent `setInterval` timers. Never receives server timer ticks. |
| `economy-collapse-speedrun/config.py` | `GameSettings` dataclass with `num_rounds`, `parliament_size`, `proposal_time`, `voting_time` |

### Gaps or Problems Being Addressed

1. **Timer desync bug**: The server starts its countdown immediately, but clients only start their local countdown when the WebSocket message arrives. With ngrok latency (100ms-2s+), the client timer lags behind the server. When the server finishes its countdown and transitions the phase, the client timer still shows 3-5 seconds remaining — creating the "skip" effect. Additionally, the server timer loop does `asyncio.sleep(1) + await broadcast(...)`, making each tick slightly > 1 second, which can accumulate drift in the opposite direction.

2. **Fixed settings are limiting**: Only 3/5/7 rounds, 3/4/5 parliament, 60/90/120s writing, 30/45/60s voting. The host can't set 4 rounds, 6 parliament members, 100s writing time, etc. For a live demo, the ability to tweak timings precisely is valuable.

---

## Proposed Changes

### Summary of Changes

- **Broadcast timer ticks to ALL clients** (players + host), not just the host
- **Player.html**: sync displayed timer to server-sent `phase_remaining` values instead of running an independent countdown
- **Host.html**: display server-sent `phase_remaining` in the phase area (writing/voting countdown)
- **Replace fixed settings buttons** with number input fields that have min/max constraints and increment/decrement buttons
- **Update `GameSettings.from_dict()`** to clamp values to valid ranges
- **Add validation** on the backend to prevent nonsensical values

### Files to Modify

| File | Changes |
|------|---------|
| `server.py` | Broadcast timer ticks to all players (not just host). Add `phase_remaining` to phase-start messages. |
| `static/host.html` | Add phase timer display. Handle server timer ticks for display. Replace fixed-option buttons with number inputs. Update settings JS. |
| `static/player.html` | Replace independent `setInterval` timer with server-synced timer. Handle `timer` message type. |
| `config.py` | Add clamping/validation in `from_dict()` to enforce min/max ranges. |

### Files to Delete

None.

---

## Design Decisions

### Key Decisions Made

1. **Server as single source of truth for timers**: The server broadcasts `phase_remaining` every second to ALL clients. Clients display that value. This eliminates desync regardless of network latency, ngrok overhead, or asyncio drift. If a tick is missed (packet loss), the next one corrects it.

2. **Keep a local fallback countdown between server ticks**: The client still runs a local `setInterval` to count down between server messages for smooth display. But every time a server tick arrives, it overrides the local value. This gives smooth 1-second updates even if a server tick is delayed, while staying synced.

3. **Number inputs with +/- buttons (stepper style)**: Rather than sliders (imprecise on mobile) or bare text fields (need keyboard), use a styled stepper: a displayed value with +/- buttons on either side. Clean, mobile-friendly, and allows precise control. Each setting has its own min/max/step configuration.

4. **Backend clamping**: `GameSettings.from_dict()` clamps all values to valid ranges so even if the frontend sends garbage, the server stays safe.

### Alternatives Considered

- **Slider inputs**: Considered but rejected — sliders are imprecise on desktop (hard to hit exact values) and the range of values differs wildly per setting (1-20 rounds vs 10-300 seconds). Steppers are more intuitive.
- **Text input fields**: Considered but rejected — require keyboard input and manual validation. Steppers are faster (just click +/-).
- **Client-only timer fix (add latency buffer)**: Rejected — doesn't solve the root cause. The server should be authoritative.

### Open Questions

None — both changes are straightforward.

---

## Step-by-Step Tasks

### Step 1: Broadcast Timer Ticks to All Clients

Make the server send `phase_remaining` to all players, not just the host.

**Actions:**

- `server.py` — `writing_phase_timer()`: Change `broadcast_to_host` to `broadcast_all` for timer ticks
- `server.py` — `voting_phase_timer()`: Change `broadcast_to_host` to `broadcast_all` for timer ticks
- `server.py` — `tiebreaker_timer()`: Change `broadcast_to_host` to `broadcast_all` for timer ticks

**Files affected:**
- `server.py`

---

### Step 2: Player.html — Server-Synced Timer

Replace the independent client-side timer with a server-synced approach.

**Actions:**

- `static/player.html` — Modify `startTimer()` function:
  - Still start a local `setInterval` countdown (for smooth display between server ticks)
  - But also handle `timer` messages from the server to sync the displayed value

- `static/player.html` — Add `timer` case to `handleMessage()`:
  ```javascript
  case 'timer':
    // Sync local timer to server's authoritative value
    if (msg.phase_remaining !== undefined) {
      syncTimer(msg.phase_remaining);
    }
    break;
  ```

- `static/player.html` — Add `syncTimer()` function:
  ```javascript
  function syncTimer(serverRemaining) {
    // Update the currently active timer element with server value
    var activeTimerEl = document.querySelector('.writing-timer:not(.hidden), .voting-timer:not(.hidden), .tb-timer:not(.hidden)');
    // Actually, track which timer element is active
    if (currentTimerEl) {
      currentTimerEl.textContent = serverRemaining;
      if (serverRemaining <= 5) currentTimerEl.classList.add('urgent');
      else currentTimerEl.classList.remove('urgent');
      // Reset local countdown to match
      localRemaining = serverRemaining;
    }
  }
  ```

- Track the active timer element and local remaining value as module-level variables so both `startTimer` and `syncTimer` can access them.

**Files affected:**
- `static/player.html`

---

### Step 3: Host.html — Display Phase Timer and Sync

Add a visible phase countdown to the host display and sync it from server ticks.

**Actions:**

- `static/host.html` — Add a phase timer display element to the top bar (between the phase badge and the end game button):
  ```html
  <div class="phase-timer" id="phaseTimer" style="font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;color:#fbbf24;display:none"></div>
  ```

- `static/host.html` — Update the `timer` case in `handleMessage()`:
  ```javascript
  case 'timer':
    var pt = document.getElementById('phaseTimer');
    if (msg.phase_remaining !== undefined) {
      pt.style.display = 'block';
      pt.textContent = msg.phase_remaining + 's';
      if (msg.phase_remaining <= 5) pt.style.color = '#ef4444';
      else pt.style.color = '#fbbf24';
    }
    break;
  ```

- Hide the phase timer during results/gameover phases (set `display:none` in `renderRoundEnd` and `renderGameOver`).

**Files affected:**
- `static/host.html`

---

### Step 4: Replace Fixed Settings with Number Steppers

Replace button groups with stepper inputs.

**Actions:**

- `static/host.html` — Add CSS for stepper component:
  ```css
  .stepper{display:flex;align-items:center;gap:0}
  .stepper-btn{width:36px;height:36px;font-size:18px;font-weight:800;font-family:'Inter',sans-serif;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .15s}
  .stepper-btn:first-child{border-radius:8px 0 0 8px}
  .stepper-btn:last-child{border-radius:0 8px 8px 0}
  .stepper-btn:hover{background:rgba(0,180,216,0.15);border-color:#00b4d8}
  .stepper-btn:active{transform:scale(0.95)}
  .stepper-value{min-width:60px;height:36px;display:flex;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:700;color:#00b4d8;background:rgba(0,180,216,0.08);border-top:1px solid rgba(255,255,255,0.12);border-bottom:1px solid rgba(255,255,255,0.12)}
  ```

- `static/host.html` — Replace the settings rows. Each setting gets a stepper:

  **Number of Rounds** (min: 1, max: 20, step: 1, default: 5):
  ```html
  <div class="setting-row">
    <div class="setting-name">🔄 Number of Rounds</div>
    <div class="stepper">
      <button class="stepper-btn" onclick="stepSetting('num_rounds', -1)">-</button>
      <div class="stepper-value" id="val_num_rounds">5</div>
      <button class="stepper-btn" onclick="stepSetting('num_rounds', 1)">+</button>
    </div>
  </div>
  ```

  **Parliament Size** (min: 2, max: 15, step: 1, default: 4):
  ```html
  <div class="setting-row">
    <div class="setting-name">🏛 Parliament Size</div>
    <div class="stepper">
      <button class="stepper-btn" onclick="stepSetting('parliament_size', -1)">-</button>
      <div class="stepper-value" id="val_parliament_size">4</div>
      <button class="stepper-btn" onclick="stepSetting('parliament_size', 1)">+</button>
    </div>
  </div>
  ```

  **Writing Time** (min: 30, max: 300, step: 15, default: 120, display as "Xm Ys" or "Xs"):
  ```html
  <div class="setting-row">
    <div class="setting-name">✍️ Writing Time</div>
    <div class="stepper">
      <button class="stepper-btn" onclick="stepSetting('proposal_time', -15)">-</button>
      <div class="stepper-value" id="val_proposal_time">2:00</div>
      <button class="stepper-btn" onclick="stepSetting('proposal_time', 15)">+</button>
    </div>
  </div>
  ```

  **Voting Time** (min: 15, max: 120, step: 5, default: 45, display as seconds):
  ```html
  <div class="setting-row">
    <div class="setting-name">🗳 Voting Time</div>
    <div class="stepper">
      <button class="stepper-btn" onclick="stepSetting('voting_time', -5)">-</button>
      <div class="stepper-value" id="val_voting_time">45s</div>
      <button class="stepper-btn" onclick="stepSetting('voting_time', 5)">+</button>
    </div>
  </div>
  ```

- `static/host.html` — Add `stepSetting()` JS function:
  ```javascript
  var settingConfig = {
    num_rounds:     { min: 1,  max: 20,  step: 1,  format: 'number' },
    parliament_size:{ min: 2,  max: 15,  step: 1,  format: 'number' },
    proposal_time:  { min: 30, max: 300, step: 15, format: 'time'   },
    voting_time:    { min: 15, max: 120, step: 5,  format: 'seconds' },
  };

  window.stepSetting = function(key, delta) {
    var cfg = settingConfig[key];
    var current = gameSettings[key] || 0;
    var newVal = Math.max(cfg.min, Math.min(cfg.max, current + delta));
    gameSettings[key] = newVal;
    if (key === 'num_rounds') numRounds = newVal;
    updateStepperDisplay(key, newVal);
    sendSettings();
  };

  function updateStepperDisplay(key, val) {
    var el = document.getElementById('val_' + key);
    if (!el) return;
    var cfg = settingConfig[key];
    if (cfg.format === 'time') {
      var m = Math.floor(val / 60);
      var s = val % 60;
      el.textContent = m + ':' + String(s).padStart(2, '0');
    } else if (cfg.format === 'seconds') {
      el.textContent = val + 's';
    } else {
      el.textContent = val;
    }
  }
  ```

- Remove the old `selectSetting()` function and its references.
- Remove the old `setting-opt` button elements and `durationOpts`/`parlSizeOpts`/`writeTimeOpts`/`voteTimeOpts` divs.

**Files affected:**
- `static/host.html`

---

### Step 5: Update Settings Sync from Server

When the host receives a `settings_update` message from the server, update all stepper displays.

**Actions:**

- `static/host.html` — Update the `settings_update` case:
  ```javascript
  case 'settings_update':
    if (msg.settings) {
      gameSettings = Object.assign(gameSettings, msg.settings);
      if (msg.settings.mode) currentMode = msg.settings.mode;
      if (msg.settings.num_rounds) numRounds = msg.settings.num_rounds;
      // Update all stepper displays
      for (var key in settingConfig) {
        if (gameSettings[key] !== undefined) updateStepperDisplay(key, gameSettings[key]);
      }
    }
    break;
  ```

**Files affected:**
- `static/host.html`

---

### Step 6: Add Backend Validation/Clamping

Ensure the server clamps all values to valid ranges.

**Actions:**

- `config.py` — Update `from_dict()`:
  ```python
  @staticmethod
  def from_dict(d: dict) -> "GameSettings":
      return GameSettings(
          mode=d.get("mode", "destructive") if d.get("mode") in ("constructive", "destructive") else "destructive",
          num_rounds=max(1, min(20, int(d.get("num_rounds", 5)))),
          parliament_size=max(2, min(15, int(d.get("parliament_size", 4)))),
          anonymous=d.get("anonymous", True),
          proposal_time=max(30, min(300, int(d.get("proposal_time", 120)))),
          voting_time=max(15, min(120, int(d.get("voting_time", 45)))),
          tiebreaker_time=int(d.get("tiebreaker_time", 10)),
      )
  ```

**Files affected:**
- `config.py`

---

### Step 7: Test and Verify

**Actions:**

- Start the server and verify settings screen shows stepper inputs
- Click +/- buttons and verify values change within their ranges
- Cannot go below min or above max
- Timer displays correctly show formatted values (2:00 for 120s, 45s for 45)
- Start a game and verify:
  - Writing timer counts down on both host and player screens
  - Timer stays synced (doesn't skip) — host and player show same remaining seconds
  - Phase transitions happen cleanly at 0
  - Voting timer also synced
  - Tiebreaker timer also synced

**Files affected:**
- None (testing only)

---

## Connections & Dependencies

### Files That Reference This Area

| File | Reference |
|------|-----------|
| `server.py` | Timer loop functions, phase broadcasts |
| `static/host.html` | Settings UI, timer display |
| `static/player.html` | Timer display, phase handling |
| `config.py` | GameSettings with timing values |

### Updates Needed for Consistency

- Remove old `selectSetting` references in host.html
- Remove old `.setting-opt` CSS if no longer used
- Ensure `sendSettings()` sends the updated `gameSettings` object (already does)

### Impact on Existing Workflows

- **Timer behavior**: Players and host now see server-authoritative countdown. No more desync.
- **Settings UX**: Host can set any value within range, not limited to preset options. More powerful but slightly more clicks for common values.

---

## Validation Checklist

- [ ] Server broadcasts timer ticks to all players (not just host)
- [ ] Player.html displays server-sent `phase_remaining` values
- [ ] Player timer doesn't skip or jump when phase transitions
- [ ] Host shows phase countdown in top bar during writing/voting
- [ ] Settings stepper for rounds works (min 1, max 20)
- [ ] Settings stepper for parliament size works (min 2, max 15)
- [ ] Settings stepper for writing time works (min 30s, max 300s, step 15s)
- [ ] Settings stepper for voting time works (min 15s, max 120s, step 5s)
- [ ] Time-based steppers display formatted values (m:ss)
- [ ] Backend clamps values to valid ranges
- [ ] Old fixed-option buttons are fully removed
- [ ] Server starts without errors

---

## Success Criteria

The implementation is complete when:

1. The countdown timer on player screens never "skips" — it counts down smoothly to 0 and the phase transition happens at or very near 0
2. The host screen shows a live countdown during writing and voting phases
3. All game settings use stepper inputs with appropriate ranges and step sizes
4. The backend validates and clamps all settings values

---

## Notes

- The timer fix is the higher priority — it's a visible bug during the live demo. The settings UI is a nice-to-have.
- The `tiebreaker_time` setting (10s) is kept as a fixed value — it's short enough that steppers aren't needed, and tiebreakers are rare.
- The anonymous toggle stays as-is (toggle switch is the right UI for a boolean).
- If network latency is extremely high (>1s), the timer display may briefly show stale values between server ticks, but the next server tick corrects it. This is acceptable.
- The stepper step sizes are chosen for usability: 15s increments for writing time (common values: 30, 45, 60, 75, 90, 105, 120), 5s for voting (15, 20, 25, 30, ..., 60).

---

## Implementation Notes

**Implemented:** 2026-03-05

### Summary

All 6 implementation steps completed. Timer ticks now broadcast to all clients via `broadcast_all`. Player.html syncs its displayed timer from server-sent `phase_remaining` values while maintaining a local fallback countdown for smooth display. Host.html shows a live phase countdown in the top bar. Fixed-option setting buttons replaced with stepper inputs (+/- buttons) with min/max clamping. Backend validates and clamps all settings values.

### Deviations from Plan

None

### Issues Encountered

None

"""
server.py — FastAPI web server with WebSocket real-time communication.

This is the ENTRY POINT of the entire application. When you run this file,
it starts a web server that:

1. Serves two HTML pages:
   - "/" (host.html): The projector display showing the game on the big screen
   - "/play" (player.html): The phone UI students use to join and participate

2. Manages WebSocket connections for real-time bidirectional communication:
   - /ws/host: The projector connects here to receive live game updates
   - /ws/player/{name}: Each student's phone connects here

3. Orchestrates the entire game flow:
   Lobby → Role Assignment → [Writing → Voting → Results] × N → (Tiebreaker?) → Game Over

4. Runs AI tasks in parallel with human activity:
   - While parliament writes proposals → pre-generate nothing (they need focus time)
   - While people vote → AI grades proposals in background
   - While results display → AI generates next scenario in background
   This parallelism minimizes wait times between phases.

Architecture:
    - Game state is managed by the Game class (game.py)
    - AI calls are handled by llm.py via async background tasks
    - Phase timers run as asyncio tasks with 1-second countdown broadcasts
    - All communication between server and clients is JSON over WebSocket
"""

# ---- Standard Library Imports ----
import asyncio     # For async/await, background tasks, and timers
import io          # For in-memory byte streams (QR code generation)
import json        # For encoding/decoding JSON messages
import logging     # For debug and error logging
import random      # For picking random loading messages

# ---- Third-Party Imports ----
import qrcode      # For generating QR code images (students scan to join)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # Web framework
from fastapi.responses import FileResponse, StreamingResponse  # HTTP response types

# ---- Project Imports ----
import config      # Server settings, API keys, player limits
import profanity   # Player name profanity filter
from game import Game  # Core game state and logic
from llm import (      # AI integration functions
    evaluate_proposals,         # AI grades parliament proposals
    generate_narrative,         # AI writes end-game satirical summary
    generate_scenario,          # AI creates economic crisis scenarios
    get_fallback_evaluations,   # Default evaluations if AI fails
    get_next_fallback_scenario, # Pre-written scenarios if AI fails
)

# ---- Logging Setup ----
# Configure logging to show INFO level and above (INFO, WARNING, ERROR)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- Create the FastAPI Application ----
# This is the main web application object that handles all HTTP and WebSocket routes
app = FastAPI(title="Econoland — Parliament Edition")


def get_player_url() -> str:
    """
    Construct the player-facing URL that students will use to join the game.

    Uses the ngrok URL from config (which tunnels to our local server) and
    appends a query parameter to bypass ngrok's browser warning page.

    Returns:
        str: The full URL for the player page (e.g., "https://abc123.ngrok.io/play?ngrok-skip-browser-warning=true")
    """
    # Remove trailing slash from the base URL
    base = config.NGROK_URL.rstrip("/")
    # Use "&" if URL already has query params, otherwise "?"
    sep = "&" if "?" in base else "?"
    return f"{base}/play{sep}ngrok-skip-browser-warning=true"


@app.middleware("http")
async def add_ngrok_header(request, call_next):
    """
    Middleware that adds ngrok header to ALL HTTP responses.

    ngrok shows a browser warning page on first visit. Adding this header
    tells ngrok to skip that warning, so students go straight to the game.

    Args:
        request: The incoming HTTP request
        call_next: The next middleware/handler in the chain

    Returns:
        Response: The HTTP response with the ngrok header added
    """
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response


# ============================================================
# Global Game State
# ============================================================
# Single game instance — the entire server runs one game at a time
game = Game()

# ============================================================
# WebSocket Connection Tracking
# ============================================================
# These dictionaries track all active WebSocket connections
# so we can send messages to specific clients or broadcast to groups.
host_connections: set[WebSocket] = set()        # All host displays (usually 1, but supports multiple)
player_connections: dict[str, WebSocket] = {}   # Maps player name → their WebSocket connection

# ============================================================
# Phase Timer
# ============================================================
# Only one phase timer runs at a time (writing, voting, or tiebreaker).
# It's stored globally so it can be cancelled if needed (e.g., all players voted early).
phase_timer_task: asyncio.Task | None = None

# Funny loading messages shown while waiting for AI responses
LOADING_MESSAGES = [
    "The economy is processing your terrible decisions...",
    "Economists are crying. Please hold.",
    "Calculating how much damage you've done...",
    "The IMF is trying to reach you. Please wait.",
    "Your economy is buffering. Just like your country's internet.",
]


# ============================================================
# Broadcast Helper Functions
# ============================================================
# These functions send JSON messages to different groups of connected clients.
# They handle disconnected clients gracefully by removing dead connections.

async def broadcast_to_host(data: dict):
    """
    Send a JSON message to all connected host displays (projector screens).

    If a host connection has died (WebSocket error), it's automatically
    removed from the tracking set.

    Args:
        data: Dictionary to send as JSON
    """
    message = json.dumps(data)
    dead = set()  # Track dead connections for cleanup
    for ws in host_connections:
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)  # Mark for removal
    # Clean up dead connections
    for ws in dead:
        host_connections.discard(ws)


async def send_to_player(name: str, data: dict):
    """
    Send a JSON message to a specific player by their name.

    If the player's connection has died, it's removed from tracking.

    Args:
        name: The player's display name
        data: Dictionary to send as JSON
    """
    ws = player_connections.get(name)
    if ws:
        try:
            await ws.send_text(json.dumps(data))
        except Exception:
            # Connection died — remove it
            player_connections.pop(name, None)


async def broadcast_to_parliament(data: dict):
    """
    Send a JSON message to all parliament members.

    Args:
        data: Dictionary to send as JSON
    """
    for name in game.parliament_members:
        await send_to_player(name, data)


async def broadcast_to_people(data: dict):
    """
    Send a JSON message to all "people" players (non-parliament voters).

    Args:
        data: Dictionary to send as JSON
    """
    for name in game.people_members:
        await send_to_player(name, data)


async def broadcast_to_all_players(data: dict):
    """
    Send a JSON message to every connected player (both parliament and people).

    Args:
        data: Dictionary to send as JSON
    """
    for name in player_connections:
        await send_to_player(name, data)


async def broadcast_all(data: dict):
    """
    Send a JSON message to EVERYONE — host displays AND all players.

    Used for messages that everyone needs to see, like timer updates
    and loading messages.

    Args:
        data: Dictionary to send as JSON
    """
    await broadcast_to_host(data)
    await broadcast_to_all_players(data)


# ---- Wire up the broadcast callbacks on the Game instance ----
# The Game class needs to send messages but doesn't know about WebSockets.
# We inject these functions so game.py can broadcast without importing server code.
game.on_broadcast_host = broadcast_to_host
game.on_broadcast_parliament = broadcast_to_parliament
game.on_broadcast_people = broadcast_to_people
game.on_broadcast_all = broadcast_all
game.on_send_to_player = send_to_player


# ============================================================
# HTTP Endpoints (regular web pages and API routes)
# ============================================================

@app.get("/")
async def host_page():
    """
    Serve the host display HTML page.

    This is what gets shown on the projector — the big screen that
    everyone in the class watches. It shows the lobby, QR code,
    scenarios, live proposals, vote counts, economy dashboard, etc.

    Returns:
        FileResponse: The host.html file
    """
    return FileResponse("static/host.html")


@app.get("/play")
async def player_page():
    """
    Serve the player HTML page.

    This is what students see on their phones after scanning the QR code.
    It shows the join screen, then role-specific UI (text input for parliament,
    numbered vote buttons for people).

    Returns:
        FileResponse: The player.html file
    """
    return FileResponse("static/player.html")


@app.get("/qr")
async def qr_code():
    """
    Generate and serve a QR code image for the player join URL.

    Creates a QR code PNG image that, when scanned, takes students
    to the player page. The QR code is displayed on the host screen
    during the lobby phase.

    Returns:
        StreamingResponse: A PNG image of the QR code
    """
    # Get the full player URL (with ngrok skip parameter)
    url = get_player_url()
    # Generate QR code image
    img = qrcode.make(url)
    # Save to an in-memory buffer (no file needed)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)  # Reset buffer position to the beginning
    # Return as a streaming PNG response
    return StreamingResponse(buf, media_type="image/png")


@app.post("/settings")
async def update_settings_endpoint():
    """
    Placeholder HTTP endpoint for settings updates.

    Settings are actually updated via WebSocket from the host display,
    not through this HTTP endpoint. This exists for potential future use.

    Returns:
        dict: Simple OK status
    """
    return {"status": "ok"}


@app.post("/start")
async def start_game_endpoint():
    """
    HTTP endpoint to start the game.

    Called when the host clicks "Start Game". This function:
    1. Validates that the game hasn't started and enough players have joined
    2. Shows a loading message to all clients
    3. Assigns roles (randomly picks parliament members)
    4. Sends role assignments to each player's phone
    5. Shows the role reveal on the projector
    6. Generates the first scenario (via AI or fallback)
    7. Starts round 1

    Returns:
        dict: Status message — "started" on success, "error" on failure
    """
    # Don't start if game is already running
    if game.started:
        return {"error": "Game already started"}
    # Need minimum number of players
    if game.get_player_count() < config.MIN_PLAYERS:
        return {"error": f"Need at least {config.MIN_PLAYERS} players"}

    # Show loading message on all screens while we set up
    await broadcast_all({"type": "loading", "message": "Assembling parliament... preparing the economy..."})

    # Initialize the game: set started=True, assign roles randomly
    await game.start_game()

    # Send role assignment to each parliament member's phone
    for name in game.parliament_members:
        await send_to_player(name, {
            "type": "role_assigned",
            "role": "parliament",
            "parliament_index": game.players[name].parliament_index,
        })

    # Send role assignment to each person's phone
    for name in game.people_members:
        await send_to_player(name, {
            "type": "role_assigned",
            "role": "people",
        })

    # Send the role reveal screen to the host display (projector)
    await broadcast_to_host({
        "type": "role_reveal",
        "parliament": [
            {"name": n, "display_name": n if not game.settings.anonymous else f"Member {i+1}"}
            for i, n in enumerate(game.parliament_members)
        ],
        "people_count": len(game.people_members),
        "settings": game.settings.to_dict(),
    })

    # Wait 3 seconds for everyone to see the role reveal
    await asyncio.sleep(3)

    # Generate the first scenario using AI
    try:
        scenario = await generate_scenario(
            game.economy.get_state(),
            game.get_round_history_for_llm(),
            1,  # Round 1
            game.settings.mode,
        )
    except Exception as e:
        # If AI fails, use a pre-written fallback scenario
        logger.error(f"Failed to generate first scenario: {e}")
        scenario = get_next_fallback_scenario(game.settings.mode)

    # Start round 1 with the generated (or fallback) scenario
    await start_round(scenario)

    return {"status": "started"}


@app.get("/state")
async def debug_state():
    """
    Debug endpoint that returns the current game state as JSON.

    Useful for debugging during development — visit /state in a browser
    to see the raw game state including player info, economy, and phase.

    Returns:
        dict: Current game state snapshot
    """
    return {
        "started": game.started,
        "round": game.round_number,
        "phase": game.current_phase,
        "economy": game.economy.get_state(),
        "score": game.economy.get_score(),
        "players": {n: {"role": d.role, "score": d.score, "votes": d.votes_received} for n, d in game.players.items()},
        "game_over": game.game_over,
    }


@app.get("/api/game-info")
async def game_info():
    """Return game settings relevant to the player join flow."""
    return {
        "anonymous": game.settings.anonymous,
        "started": game.started,
    }


# ============================================================
# Phase Management — Controls the flow of each game round
# ============================================================

async def start_round(scenario: dict):
    """
    Begin a new round with the given scenario.

    This function:
    1. Resets per-round data (proposals, votes) via game.start_new_round()
    2. Sends the scenario and writing phase UI to the host display
    3. Sends writing instructions to parliament members' phones
    4. Sends a "watch the screen" message to people's phones
    5. Starts the writing phase countdown timer

    Args:
        scenario: The economic crisis scenario (headline, description, news_ticker)
    """
    # Initialize the new round in the game state
    game.start_new_round(scenario)

    # Send the writing phase data to the host display (projector)
    await broadcast_to_host({
        "type": "writing_phase",
        "round": game.round_number,
        "scenario": scenario,
        "economy": game.economy.get_state(),
        "score": game.economy.get_score(),
        "timer": game.settings.proposal_time,
        # Initialize empty proposal text for each parliament member
        "proposals": {str(i): "" for i in range(len(game.parliament_members))},
        # Display names (real names or "Member 1" depending on anonymous setting)
        "parliament_names": [
            n if not game.settings.anonymous else f"Member {i+1}"
            for i, n in enumerate(game.parliament_members)
        ],
        "num_rounds": game.settings.num_rounds,
        "mode": game.settings.mode,
    })

    # Send writing phase info to parliament members' phones
    # They see the scenario and get a text input to type their proposal
    await broadcast_to_parliament({
        "type": "writing_phase",
        "round": game.round_number,
        "scenario": {
            "headline": scenario.get("headline", ""),
            "description": scenario.get("description", ""),
        },
        "timer": game.settings.proposal_time,
        "char_limit": 200,  # Maximum characters per proposal
        "mode": game.settings.mode,
    })

    # Send waiting message to people's phones
    # They watch the projector while parliament writes
    await broadcast_to_people({
        "type": "writing_phase",
        "round": game.round_number,
        "message": "Watch the main screen. Parliament is writing proposals. Voting starts soon.",
    })

    # Start the writing phase countdown timer as a background task
    global phase_timer_task
    phase_timer_task = asyncio.create_task(writing_phase_timer())


async def writing_phase_timer():
    """
    Countdown timer for the writing phase.

    Counts down from proposal_time to 0, broadcasting the remaining
    time to all clients every second. When time expires, locks all
    proposals and transitions to the voting phase.
    """
    remaining = game.settings.proposal_time

    # Count down 1 second at a time
    while remaining > 0 and not game.game_over:
        await asyncio.sleep(1)
        remaining -= 1

        # Broadcast the remaining time to all clients (host + all players)
        await broadcast_all({
            "type": "timer",
            "phase": "writing",
            "phase_remaining": remaining,
        })

    # If the game was terminated during writing, stop here
    if game.game_over:
        return

    # Time's up — lock all proposals so parliament can't edit anymore
    game.lock_all_proposals()

    # Tell parliament members their proposals are locked
    await broadcast_to_parliament({
        "type": "input_locked",
        "message": "Time's up! Your proposal has been submitted.",
    })

    # Transition to the voting phase
    await start_voting_phase()


async def start_voting_phase():
    """
    Begin the voting phase.

    This function:
    1. Gets the finalized list of proposals
    2. Fires AI grading as a background task (runs IN PARALLEL with human voting)
    3. Sends voting UI to host and people
    4. Tells parliament to wait
    5. Starts the voting countdown timer

    The key optimization here is that AI grading runs while people are voting,
    so there's no waiting for AI after votes are in.
    """
    # Get the final proposal list (text is now locked)
    proposals_list = game.get_proposals_list()

    # Start AI grading in the background — it runs while people vote!
    # This is a key performance optimization: humans and AI work simultaneously
    game.grading_task = asyncio.create_task(grade_proposals_background())

    # Send voting phase UI to the host display
    await broadcast_to_host({
        "type": "voting_phase",
        "round": game.round_number,
        "proposal_count": len(proposals_list),
        "proposals_final": proposals_list,
        "timer": game.settings.voting_time,
    })

    # Send voting buttons to people's phones
    # They see numbered buttons (1, 2, 3...) and read proposals from the projector
    await broadcast_to_people({
        "type": "voting_phase",
        "proposal_count": len(proposals_list),
        "timer": game.settings.voting_time,
    })

    # Tell parliament to wait while people vote
    await broadcast_to_parliament({
        "type": "voting_started",
        "message": "The people are deciding your fate...",
    })

    # Start the voting countdown timer
    global phase_timer_task
    phase_timer_task = asyncio.create_task(voting_phase_timer())


async def grade_proposals_background():
    """
    Background task: AI evaluates all proposals while people are voting.

    Calls the LLM to grade each proposal with quality scores, economic
    impacts, and commentary. If the AI call fails, falls back to neutral
    default evaluations.

    This runs concurrently with the voting timer — by the time voting ends,
    the AI grading is usually already done.
    """
    try:
        proposals_list = game.get_proposals_list()
        # Call the AI to evaluate all proposals
        evaluations = await evaluate_proposals(
            scenario=game.current_scenario,
            proposals=proposals_list,
            economy_state=game.economy.get_state(),
            mode=game.settings.mode,
        )
        # Store the evaluations in the game state
        game.ai_evaluations = evaluations
        logger.info(f"AI grading complete for round {game.round_number}")
    except Exception as e:
        # If AI fails, use neutral fallback evaluations (score=50, zero impacts)
        logger.error(f"AI grading failed: {e}")
        game.ai_evaluations = get_fallback_evaluations(len(game.parliament_members))


async def voting_phase_timer():
    """
    Countdown timer for the voting phase.

    Counts down from voting_time to 0, broadcasting remaining time every second.
    When time expires, calls finish_voting() to process the results.

    Note: This timer can be cancelled early if all people vote before time runs out.
    """
    remaining = game.settings.voting_time

    # Count down 1 second at a time
    while remaining > 0 and not game.game_over:
        await asyncio.sleep(1)
        remaining -= 1

        # Broadcast remaining time to all clients
        await broadcast_all({
            "type": "timer",
            "phase": "voting",
            "phase_remaining": remaining,
        })

    # If the game was terminated during voting, stop here
    if game.game_over:
        return

    # If voting was already handled (e.g., all people voted early), stop here
    if game.current_phase != "voting":
        return

    # Time's up — process the voting results
    await finish_voting()


async def finish_voting():
    """
    Process voting results after all votes are in (or time expires).

    This function:
    1. Waits for AI grading to finish (if it's still running)
    2. Checks for a tie — if tied, starts a tiebreaker vote
    3. If no tie, determines the winner and finalizes the round
    """
    # Guard against double-processing (could happen if timer and early-vote fire simultaneously)
    if game.current_phase != "voting":
        return

    # Wait for AI grading to finish if it's still running
    if game.grading_task and not game.grading_task.done():
        # Show a loading message while we wait
        await broadcast_to_host({"type": "loading", "message": "AI is still evaluating proposals..."})
        try:
            # Wait up to 8 seconds for AI grading to finish
            await asyncio.wait_for(game.grading_task, timeout=8.0)
        except asyncio.TimeoutError:
            # AI took too long — use fallback evaluations
            logger.error("AI grading timed out, using fallback")
            game.ai_evaluations = get_fallback_evaluations(len(game.parliament_members))

    # Determine the winner (random pick if tied) and finalize the round
    winning_index = game.determine_winner()
    await finalize_round(winning_index)


async def start_endgame_tiebreaker(tied_names: list[str]):
    """
    Start an end-game tiebreaker vote between parliament members tied for 1st place.

    People vote for who they think deserves to win the parliament leaderboard.

    Args:
        tied_names: List of parliament member names tied for 1st place
    """
    game.current_phase = "tiebreaker"
    game.tiebreaker_votes = {}
    # Store tied names so we can resolve later
    game.endgame_tiebreaker_names = tied_names

    # Build tied member data for display
    tied_members = []
    for i, name in enumerate(tied_names):
        tied_members.append({
            "index": i,
            "name": name,
            "display_name": name if not game.settings.anonymous else f"Member {i + 1}",
            "votes_received": game.players[name].votes_received,
        })

    # Send tiebreaker UI to host
    await broadcast_to_host({
        "type": "tiebreaker",
        "tied_members": tied_members,
        "timer": game.settings.tiebreaker_time,
    })

    # Send tiebreaker voting buttons to people
    await broadcast_to_people({
        "type": "tiebreaker",
        "tied_members": tied_members,
        "timer": game.settings.tiebreaker_time,
    })

    # Tell parliament about the tie
    await broadcast_to_parliament({
        "type": "tiebreaker",
        "message": "It's a tie! The people are voting for the parliament winner!",
    })

    # Start the tiebreaker timer
    global phase_timer_task
    phase_timer_task = asyncio.create_task(tiebreaker_timer())


async def tiebreaker_timer():
    """
    Short countdown timer for the end-game tiebreaker vote (typically 10 seconds).

    When time expires, resolves the tiebreaker and proceeds to game over.
    """
    remaining = game.settings.tiebreaker_time

    while remaining > 0 and not game.game_over:
        await asyncio.sleep(1)
        remaining -= 1

        await broadcast_all({
            "type": "timer",
            "phase": "tiebreaker",
            "phase_remaining": remaining,
        })

    if game.game_over:
        return

    if game.current_phase != "tiebreaker":
        return

    # Time's up — resolve tiebreaker and go to game over
    await resolve_endgame_tiebreaker()


async def resolve_endgame_tiebreaker():
    """
    Resolve the end-game tiebreaker: give the winner +1 vote to break the tie,
    then proceed to game over.
    """
    tied_names = getattr(game, "endgame_tiebreaker_names", [])
    if tied_names:
        winning_idx = game.resolve_endgame_tiebreaker()
        if isinstance(winning_idx, int) and 0 <= winning_idx < len(tied_names):
            # Give the winner +1 vote to break the tie on the leaderboard
            winner_name = tied_names[winning_idx]
            game.players[winner_name].votes_received += 1

    game.game_over = True
    game.current_phase = "gameover"
    await send_game_over()


async def finalize_round(winning_index: int):
    """
    Finalize the round after a winner is determined.

    This function:
    1. Records the economy state before the policy is applied
    2. Calls game.end_round() which applies impacts and updates scores
    3. Broadcasts the results to the host (projector)
    4. Sends personalized results to parliament and people
    5. Checks if the game is over (round limit or economy collapse)
    6. If not over, generates the next scenario in background and starts next round

    Args:
        winning_index: Index of the winning proposal (0-based)
    """
    # Get vote counts and economy state before applying the winning policy
    vote_counts = game.get_vote_counts()
    economy_before = game.economy.get_state()

    # Finalize the round — this applies economic impacts and updates all scores
    round_record = game.end_round(winning_index)

    # Get economy state after the policy was applied
    economy_after = game.economy.get_state()
    # Get the winning proposal's full data
    winning_proposal = round_record.proposals[winning_index] if winning_index < len(round_record.proposals) else None

    # Broadcast round results to the host display (projector)
    await broadcast_to_host({
        "type": "round_end",
        "round": round_record.round_number,
        "vote_counts": {str(k): v for k, v in vote_counts.items()},
        "winning_index": winning_index,
        "winning_text": winning_proposal.text if winning_proposal else "No policy",
        "winning_member": winning_proposal.parliament_member if winning_proposal else "",
        "impacts": winning_proposal.ai_impacts if winning_proposal else {},
        "old_economy": economy_before,
        "new_economy": economy_after,
        "score": game.economy.get_score(),
        "num_rounds": game.settings.num_rounds,
        "mode": game.settings.mode,
    })

    # Send personalized results to each parliament member
    # They see how many votes their proposal got this round
    for name in game.parliament_members:
        idx = game.players[name].parliament_index
        votes_this_round = vote_counts.get(idx, 0)
        await send_to_player(name, {
            "type": "round_result",
            "votes_received": votes_this_round,
            "running_total": game.players[name].votes_received,
        })

    # Tell people which proposal won
    await broadcast_to_people({
        "type": "round_result",
        "winning_text": winning_proposal.text if winning_proposal else "No policy",
    })

    # Check if the game should end (reached round limit OR economy collapsed)
    if game.is_game_over() or game.is_last_round():
        # Before game over, check if parliament leaderboard has a tie for 1st place
        tied_names = game.detect_parliament_leaderboard_tie()
        if tied_names:
            await start_endgame_tiebreaker(tied_names)
            return
        game.game_over = True
        game.current_phase = "gameover"
        await send_game_over()
        return

    # Game continues — generate next scenario in background while results display
    game.scenario_task = asyncio.create_task(generate_next_scenario_background())

    # Wait 4 seconds for players to see the results screen
    await asyncio.sleep(4)

    # If game was terminated during the wait, stop
    if game.game_over:
        return

    # Get the pre-generated next scenario
    scenario = None
    if game.scenario_task:
        if not game.scenario_task.done():
            # AI is still generating — show a loading message
            await broadcast_to_host({"type": "loading", "message": random.choice(LOADING_MESSAGES)})
            try:
                # Wait up to 20 seconds for the scenario
                await asyncio.wait_for(game.scenario_task, timeout=20.0)
            except asyncio.TimeoutError:
                logger.error("Next scenario generation timed out")
        # Try to get the result
        if game.scenario_task.done():
            try:
                scenario = game.scenario_task.result()
            except BaseException:
                scenario = None

    # If AI scenario generation failed, use a fallback
    if not scenario:
        scenario = get_next_fallback_scenario(game.settings.mode)

    # Start the next round with the new scenario
    await start_round(scenario)


async def generate_next_scenario_background() -> dict:
    """
    Background task: generate the next round's scenario while results are displayed.

    This runs in parallel with the results display, so the next round's
    scenario is ready by the time the results timer finishes. If AI fails,
    returns a pre-written fallback scenario.

    Returns:
        dict: Scenario with "headline", "description", and "news_ticker"
    """
    try:
        return await generate_scenario(
            game.economy.get_state(),
            game.get_round_history_for_llm(),
            game.round_number + 1,
            game.settings.mode,
        )
    except Exception as e:
        logger.error(f"Scenario generation failed: {e}")
        return get_next_fallback_scenario(game.settings.mode)


async def send_game_over():
    """
    End the game: generate narrative, compile results, and send to all clients.

    This function:
    1. Collects the list of all winning policies across rounds
    2. Calls the AI to generate a satirical narrative summary
    3. Gets the complete final results (leaderboards, AI reveal, awards)
    4. Sends full results to the host display
    5. Sends personalized results to each player's phone
    """
    # Collect the text of every winning policy across all rounds
    policy_list = []
    for rr in game.round_history:
        if rr.winning_proposal_index >= 0 and rr.winning_proposal_index < len(rr.proposals):
            policy_list.append(rr.proposals[rr.winning_proposal_index].text)

    # Get the starting economy state for comparison
    starting_state = {
        "gdp": config.STARTING_GDP,
        "employment": config.STARTING_EMPLOYMENT,
        "inflation": config.STARTING_INFLATION,
        "public_trust": config.STARTING_PUBLIC_TRUST,
        "trade_balance": config.STARTING_TRADE_BALANCE,
        "national_debt": config.STARTING_NATIONAL_DEBT,
    }

    # Generate the satirical end-game narrative via AI
    try:
        narrative = await generate_narrative(
            mode=game.settings.mode,
            starting_state=starting_state,
            final_state=game.economy.get_state(),
            rounds_played=game.round_number,
            policy_list=policy_list,
            collapsed=game.economy.is_collapsed(),
        )
    except Exception as e:
        # Fallback narrative if AI fails
        logger.error(f"Narrative failed: {e}")
        narrative = "The economy has spoken. No further comment."

    # Get the complete final results (AI reveal, leaderboards, awards)
    results = game.get_final_results()
    results["narrative"] = narrative

    # Send the full results to the host display (projector — everyone sees this)
    await broadcast_to_host(results)

    # Send personalized results to each player's phone
    # Parliament sees their per-round proposal breakdown
    # People see their score and rank
    for name in game.players:
        personal = game.get_player_game_over(name)
        personal["narrative"] = narrative
        await send_to_player(name, personal)


# ============================================================
# WebSocket Endpoint: Host Display (Projector)
# ============================================================

@app.websocket("/ws/host")
async def ws_host(ws: WebSocket):
    """
    WebSocket endpoint for the host display (projector).

    The host connects here to receive real-time game updates. The host
    can also send commands via this WebSocket:
    - "start": Start the game
    - "update_settings": Change game settings before starting
    - "terminate": End the game early

    Args:
        ws: The WebSocket connection from the host display
    """
    # Accept the WebSocket connection
    await ws.accept()
    # Add to the set of host connections
    host_connections.add(ws)
    logger.info("Host connected")

    # If the game hasn't started yet, send the current lobby state
    if not game.started:
        # Send current player list
        await ws.send_text(json.dumps(game.get_lobby_state()))
        # Send the QR code URL so the host can display it
        await ws.send_text(json.dumps({"type": "qr_url", "url": get_player_url()}))
        # Send current game settings
        await ws.send_text(json.dumps({"type": "settings_update", "settings": game.settings.to_dict()}))

    try:
        # Main message loop — keep reading messages from the host
        while True:
            data = await ws.receive_text()
            # Parse the incoming JSON message
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"Host sent invalid JSON: {data[:100]}")
                continue

            # Handle "start" action — host clicks Start Game
            if msg.get("action") == "start" and not game.started:
                await start_game_endpoint()

            # Handle "update_settings" action — host changes game configuration
            elif msg.get("action") == "update_settings" and not game.started:
                game.update_settings(msg.get("settings", {}))
                # Broadcast updated settings back to all host displays
                await broadcast_to_host({
                    "type": "settings_update",
                    "settings": game.settings.to_dict(),
                })

            # Handle "terminate" action — host clicks End Game
            elif msg.get("action") == "terminate" and game.started and not game.game_over:
                game.game_over = True
                game.current_phase = "gameover"
                # Cancel the active phase timer if one is running
                if phase_timer_task and not phase_timer_task.done():
                    phase_timer_task.cancel()
                # Send game over results
                await send_game_over()

    except WebSocketDisconnect:
        # Host disconnected — remove from tracking
        host_connections.discard(ws)
        logger.info("Host disconnected")


# ============================================================
# WebSocket Endpoint: Player (Phone)
# ============================================================

@app.websocket("/ws/player/{name}")
async def ws_player(ws: WebSocket, name: str):
    """
    WebSocket endpoint for player connections (students' phones).

    Handles the full player lifecycle:
    1. Connection: join the game (new player) or reconnect (returning player)
    2. Writing phase: receive keystroke messages from parliament members
    3. Voting phase: receive vote messages from people
    4. End-game tiebreaker: receive tiebreaker votes from people for parliament leaderboard
    5. Disconnection: mark player as disconnected (allows reconnection)

    Args:
        ws: The WebSocket connection from the player's phone
        name: The player's chosen display name (from the URL path)
    """
    # Accept the WebSocket connection
    await ws.accept()

    if game.started:
        # ---- Game Already Running: Handle Reconnection ----
        if game.reconnect_player(name):
            # Player was in the game before — reconnect them
            player_connections[name] = ws
            logger.info(f"Player reconnected: {name}")
            pd = game.players.get(name)
            if pd:
                # Send them their role so they know what UI to show
                await ws.send_text(json.dumps({
                    "type": "role_assigned",
                    "role": pd.role,
                    "parliament_index": pd.parliament_index if pd.role == "parliament" else -1,
                }))
                # Send current phase info so they can catch up
                if game.current_phase == "writing" and pd.role == "parliament":
                    # Parliament member reconnecting during writing — send scenario
                    await ws.send_text(json.dumps({
                        "type": "writing_phase",
                        "round": game.round_number,
                        "scenario": {
                            "headline": game.current_scenario.get("headline", "") if game.current_scenario else "",
                            "description": game.current_scenario.get("description", "") if game.current_scenario else "",
                        },
                        "timer": 0,  # Timer will update on next tick
                        "char_limit": 200,
                    }))
                elif game.current_phase == "voting" and pd.role == "people":
                    # Person reconnecting during voting — send voting UI
                    await ws.send_text(json.dumps({
                        "type": "voting_phase",
                        "proposal_count": len(game.parliament_members),
                        "timer": 0,
                    }))
                elif game.game_over:
                    # Game is already over — send their personal results
                    personal = game.get_player_game_over(name)
                    await ws.send_text(json.dumps(personal))
        else:
            # Unknown player trying to join after game started — reject
            await ws.send_text(json.dumps({"type": "error", "message": "Game already started"}))
            await ws.close()
            return
    else:
        # ---- Game Not Started: Handle Join or Reconnect in Lobby ----
        if name in game.players:
            # Player name exists — they disconnected and came back
            game.players[name].connected = True
            player_connections[name] = ws
            logger.info(f"Player reconnected (pre-game): {name}")
            # Update the lobby display with the reconnected player
            await broadcast_to_host(game.get_lobby_state())
            # Confirm to the player they're back in
            await ws.send_text(json.dumps({"type": "joined", "name": name}))
        elif profanity.is_name_inappropriate(name):
            # Blocked — offensive or inappropriate name
            await ws.send_text(json.dumps({"type": "error", "message": "That name isn't allowed. Please choose a proper name."}))
            await ws.close()
            return
        elif not game.add_player(name):
            # Failed to add — name is taken or lobby is full
            await ws.send_text(json.dumps({"type": "error", "message": "Name taken or game started"}))
            await ws.close()
            return
        else:
            # New player successfully joined!
            player_connections[name] = ws
            logger.info(f"Player joined: {name}")
            # Update the lobby display with the new player
            await broadcast_to_host(game.get_lobby_state())
            # Confirm to the player they've joined
            await ws.send_text(json.dumps({"type": "joined", "name": name}))

    try:
        # ---- Main Message Loop: Handle incoming messages from the player ----
        while True:
            data = await ws.receive_text()
            # Parse the incoming JSON message
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"Player {name} sent invalid JSON: {data[:100]}")
                continue

            msg_type = msg.get("type", "")

            # ---- Handle keystroke from parliament member (writing phase) ----
            if msg_type == "keystroke" and game.current_phase == "writing":
                text = msg.get("text", "")
                if game.update_proposal(name, text):
                    # Broadcast the updated proposal text to the host display
                    # This creates the live character-by-character typing effect
                    idx = game.players[name].parliament_index
                    await broadcast_to_host({
                        "type": "proposal_keystroke",
                        "parliament_index": idx,
                        "text": game.proposals.get(name, ""),
                    })

            # ---- Handle vote from a person (voting phase) ----
            elif msg_type == "vote" and game.current_phase == "voting":
                # Parse the proposal index they voted for
                try:
                    proposal_index = int(msg.get("proposal_index", -1))
                except (ValueError, TypeError):
                    logger.warning(f"Player {name} sent invalid proposal_index: {msg.get('proposal_index')}")
                    continue

                if game.submit_vote(name, proposal_index):
                    # Vote accepted — update the host display with new vote counts
                    vote_counts = game.get_vote_counts()
                    total_voted = len(game.votes)
                    total_people = len(game.people_members)

                    await broadcast_to_host({
                        "type": "vote_update",
                        "vote_counts": {str(k): v for k, v in vote_counts.items()},
                        "total_voted": total_voted,
                        "total_people": total_people,
                    })

                    # Confirm the vote to the player's phone
                    await ws.send_text(json.dumps({
                        "type": "vote_confirmed",
                        "voted_for": proposal_index,
                    }))

                    # Check if ALL people have voted — end voting phase early
                    if game.all_people_voted() and not game.game_over:
                        # Cancel the voting timer since everyone already voted
                        if phase_timer_task and not phase_timer_task.done():
                            phase_timer_task.cancel()
                        # Process the results immediately
                        await finish_voting()

            # ---- Handle tiebreaker vote from a person ----
            elif msg_type == "tiebreaker_vote" and game.current_phase == "tiebreaker":
                # Parse the proposal index they voted for in the tiebreaker
                try:
                    proposal_index = int(msg.get("proposal_index", -1))
                except (ValueError, TypeError):
                    logger.warning(f"Player {name} sent invalid tiebreaker proposal_index: {msg.get('proposal_index')}")
                    continue

                if game.submit_tiebreaker_vote(name, proposal_index):
                    # Tiebreaker vote accepted — update host with new counts
                    tb_counts = game.get_tiebreaker_vote_counts()
                    await broadcast_to_host({
                        "type": "tiebreaker_update",
                        "vote_counts": {str(k): v for k, v in tb_counts.items()},
                    })
                    # Confirm the vote to the player
                    await ws.send_text(json.dumps({
                        "type": "vote_confirmed",
                        "voted_for": proposal_index,
                    }))

                    # Check if ALL people have voted in tiebreaker — end early
                    if game.all_people_tiebreaker_voted() and not game.game_over:
                        if game.current_phase != "tiebreaker":
                            continue
                        # Cancel the tiebreaker timer
                        if phase_timer_task and not phase_timer_task.done():
                            phase_timer_task.cancel()
                        # Resolve end-game tiebreaker and go to game over
                        await resolve_endgame_tiebreaker()

    except WebSocketDisconnect:
        # Player disconnected — clean up their connection
        player_connections.pop(name, None)
        if name in game.players:
            game.players[name].connected = False
        logger.info(f"Player disconnected: {name}")
        # If we're still in the lobby, update the player list on the host display
        if not game.started:
            await broadcast_to_host(game.get_lobby_state())


# ============================================================
# Application Entry Point
# ============================================================

if __name__ == "__main__":
    # When running this file directly (python server.py), start the server
    import uvicorn
    # Run the FastAPI app with uvicorn on the configured host and port
    # reload=True enables auto-restart when code changes (useful during development)
    uvicorn.run("server:app", host=config.HOST, port=config.PORT, reload=True)

import asyncio
import copy
import io
import json
import logging
import random

import qrcode
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from starlette.staticfiles import StaticFiles

import config
from game import Game
from llm import (
    FALLBACK_SCENARIO,
    evaluate_proposals,
    generate_narrative,
    generate_scenario,
    get_fallback_evaluations,
    get_next_fallback_scenario,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Economy Collapse Speedrun v2 — Parliament Edition")


def get_player_url() -> str:
    base = config.NGROK_URL.rstrip("/")
    sep = "&" if "?" in base else "?"
    return f"{base}/play{sep}ngrok-skip-browser-warning=true"


@app.middleware("http")
async def add_ngrok_header(request, call_next):
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

game = Game()

# Connected WebSocket sets
host_connections: set[WebSocket] = set()
player_connections: dict[str, WebSocket] = {}  # name -> ws

# Phase timer handle
phase_timer_task: asyncio.Task | None = None
game_timer_task: asyncio.Task | None = None

LOADING_MESSAGES = [
    "The economy is processing your terrible decisions...",
    "Economists are crying. Please hold.",
    "Calculating how much damage you've done...",
    "The IMF is trying to reach you. Please wait.",
    "Your economy is buffering. Just like your country's internet.",
]


# ============================================================
# Broadcast Helpers
# ============================================================

async def broadcast_to_host(data: dict):
    message = json.dumps(data)
    dead = set()
    for ws in host_connections:
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    for ws in dead:
        host_connections.discard(ws)


async def send_to_player(name: str, data: dict):
    ws = player_connections.get(name)
    if ws:
        try:
            await ws.send_text(json.dumps(data))
        except Exception:
            player_connections.pop(name, None)


async def broadcast_to_parliament(data: dict):
    for name in game.parliament_members:
        await send_to_player(name, data)


async def broadcast_to_people(data: dict):
    for name in game.people_members:
        await send_to_player(name, data)


async def broadcast_to_all_players(data: dict):
    for name in player_connections:
        await send_to_player(name, data)


async def broadcast_all(data: dict):
    await broadcast_to_host(data)
    await broadcast_to_all_players(data)


# Wire callbacks
game.on_broadcast_host = broadcast_to_host
game.on_broadcast_parliament = broadcast_to_parliament
game.on_broadcast_people = broadcast_to_people
game.on_broadcast_all = broadcast_all
game.on_send_to_player = send_to_player


# ============================================================
# HTTP Endpoints
# ============================================================

@app.get("/")
async def host_page():
    return FileResponse("static/host.html")


@app.get("/play")
async def player_page():
    return FileResponse("static/player.html")


@app.get("/qr")
async def qr_code():
    url = get_player_url()
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@app.post("/settings")
async def update_settings_endpoint():
    """Settings are updated via WebSocket from host, this is a placeholder."""
    return {"status": "ok"}


@app.post("/start")
async def start_game_endpoint():
    if game.started:
        return {"error": "Game already started"}
    if game.get_player_count() < config.MIN_PLAYERS:
        return {"error": f"Need at least {config.MIN_PLAYERS} players"}

    # Notify loading
    await broadcast_all({"type": "loading", "message": "Assembling parliament... preparing the economy..."})

    await game.start_game()

    # Send role assignments
    for name in game.parliament_members:
        await send_to_player(name, {
            "type": "role_assigned",
            "role": "parliament",
            "parliament_index": game.players[name].parliament_index,
        })

    for name in game.people_members:
        await send_to_player(name, {
            "type": "role_assigned",
            "role": "people",
        })

    # Send role reveal to host
    await broadcast_to_host({
        "type": "role_reveal",
        "parliament": [
            {"name": n, "display_name": n if not game.settings.anonymous else f"Member {i+1}"}
            for i, n in enumerate(game.parliament_members)
        ],
        "people_count": len(game.people_members),
        "settings": game.settings.to_dict(),
    })

    # Wait a moment for role reveal
    await asyncio.sleep(3)

    # Generate first scenario (blocking)
    try:
        scenario = await generate_scenario(
            game.economy.get_state(),
            game.get_round_history_for_llm(),
            1,
            game.settings.mode,
        )
    except Exception as e:
        logger.error(f"Failed to generate first scenario: {e}")
        scenario = get_next_fallback_scenario(game.settings.mode)

    # Start round 1
    await start_round(scenario)

    # Start game timer
    global game_timer_task
    game_timer_task = asyncio.create_task(game_timer_loop())

    return {"status": "started"}


@app.get("/state")
async def debug_state():
    return {
        "started": game.started,
        "round": game.round_number,
        "phase": game.current_phase,
        "economy": game.economy.get_state(),
        "destruction_score": game.economy.get_destruction_score(),
        "players": {n: {"role": d.role, "score": d.score, "votes": d.votes_received} for n, d in game.players.items()},
        "game_over": game.game_over,
    }


# ============================================================
# Phase Management
# ============================================================

async def start_round(scenario: dict):
    """Begin a new round with the given scenario."""
    game.start_new_round(scenario)

    # Send writing phase to host
    await broadcast_to_host({
        "type": "writing_phase",
        "round": game.round_number,
        "scenario": scenario,
        "economy": game.economy.get_state(),
        "destruction_score": game.economy.get_destruction_score(),
        "timer": game.settings.proposal_time,
        "proposals": {str(i): "" for i in range(len(game.parliament_members))},
        "parliament_names": [
            n if not game.settings.anonymous else f"Member {i+1}"
            for i, n in enumerate(game.parliament_members)
        ],
        "time_remaining": game.get_time_remaining(),
    })

    # Send to parliament: you can write
    await broadcast_to_parliament({
        "type": "writing_phase",
        "round": game.round_number,
        "scenario": {
            "headline": scenario.get("headline", ""),
            "description": scenario.get("description", ""),
        },
        "timer": game.settings.proposal_time,
        "char_limit": 200,
        "mode": game.settings.mode,
    })

    # Send to people: watch main screen
    await broadcast_to_people({
        "type": "writing_phase",
        "round": game.round_number,
        "message": "Watch the main screen. Parliament is writing proposals. Voting starts soon.",
    })

    # Start writing timer
    global phase_timer_task
    phase_timer_task = asyncio.create_task(writing_phase_timer())


async def writing_phase_timer():
    """Countdown for writing phase. When done, lock proposals and start voting."""
    remaining = game.settings.proposal_time

    while remaining > 0 and not game.game_over:
        await asyncio.sleep(1)
        remaining -= 1

        # Broadcast timer to host
        await broadcast_to_host({
            "type": "timer",
            "phase": "writing",
            "phase_remaining": remaining,
            "game_remaining": game.get_time_remaining(),
        })

    if game.game_over:
        return

    # Lock all proposals
    game.lock_all_proposals()

    # Tell parliament they're locked
    await broadcast_to_parliament({
        "type": "input_locked",
        "message": "Time's up! Your proposal has been submitted.",
    })

    # Start voting phase + fire AI grading in parallel
    await start_voting_phase()


async def start_voting_phase():
    """Begin voting phase. Fire AI grading in parallel."""
    proposals_list = game.get_proposals_list()

    # Fire AI grading in background
    game.grading_task = asyncio.create_task(grade_proposals_background())

    # Send voting phase to host
    await broadcast_to_host({
        "type": "voting_phase",
        "round": game.round_number,
        "proposal_count": len(proposals_list),
        "proposals_final": proposals_list,
        "timer": game.settings.voting_time,
        "time_remaining": game.get_time_remaining(),
    })

    # Send to people: numbered buttons
    await broadcast_to_people({
        "type": "voting_phase",
        "proposal_count": len(proposals_list),
        "timer": game.settings.voting_time,
    })

    # Tell parliament to wait
    await broadcast_to_parliament({
        "type": "voting_started",
        "message": "The people are deciding your fate...",
    })

    # Start voting timer
    global phase_timer_task
    phase_timer_task = asyncio.create_task(voting_phase_timer())


async def grade_proposals_background():
    """Background task: AI grades proposals."""
    try:
        proposals_list = game.get_proposals_list()
        evaluations = await evaluate_proposals(
            scenario=game.current_scenario,
            proposals=proposals_list,
            economy_state=game.economy.get_state(),
            mode=game.settings.mode,
        )
        game.ai_evaluations = evaluations
        logger.info(f"AI grading complete for round {game.round_number}")
    except Exception as e:
        logger.error(f"AI grading failed: {e}")
        game.ai_evaluations = get_fallback_evaluations(len(game.parliament_members))


async def voting_phase_timer():
    """Countdown for voting phase."""
    remaining = game.settings.voting_time

    while remaining > 0 and not game.game_over:
        await asyncio.sleep(1)
        remaining -= 1

        await broadcast_to_host({
            "type": "timer",
            "phase": "voting",
            "phase_remaining": remaining,
            "game_remaining": game.get_time_remaining(),
        })

    if game.game_over:
        return

    if game.current_phase != "voting":
        return  # Already handled by early-vote path

    await finish_voting()


async def finish_voting():
    """Called when voting ends (timer or all voted). Check ties, finalize round."""
    if game.current_phase != "voting":
        return  # Already processing or phase advanced
    # Wait for AI grading if not done yet
    if game.grading_task and not game.grading_task.done():
        await broadcast_to_host({"type": "loading", "message": "AI is still evaluating proposals..."})
        try:
            await asyncio.wait_for(game.grading_task, timeout=8.0)
        except asyncio.TimeoutError:
            logger.error("AI grading timed out, using fallback")
            game.ai_evaluations = get_fallback_evaluations(len(game.parliament_members))

    # Check for tie
    tied = game.detect_tie()
    if tied and len(tied) > 1:
        await start_tiebreaker(tied)
        return

    # No tie — determine winner and finalize
    winning_index = game.determine_winner()
    await finalize_round(winning_index)


async def start_tiebreaker(tied_indices: list[int]):
    """Start a tiebreaker vote between tied proposals."""
    game.current_phase = "tiebreaker"
    game.tiebreaker_votes = {}

    proposals_list = game.get_proposals_list()
    tied_names = []
    for idx in tied_indices:
        if idx < len(proposals_list):
            tied_names.append(proposals_list[idx])

    # Host
    await broadcast_to_host({
        "type": "tiebreaker",
        "tied_indices": tied_indices,
        "tied_proposals": tied_names,
        "timer": game.settings.tiebreaker_time,
    })

    # People
    await broadcast_to_people({
        "type": "tiebreaker",
        "tied_indices": tied_indices,
        "timer": game.settings.tiebreaker_time,
    })

    # Parliament
    await broadcast_to_parliament({
        "type": "tiebreaker",
        "message": "It's a tie! The people are choosing between the tied proposals.",
    })

    # Timer
    global phase_timer_task
    phase_timer_task = asyncio.create_task(tiebreaker_timer())


async def tiebreaker_timer():
    """Countdown for tiebreaker."""
    remaining = game.settings.tiebreaker_time

    while remaining > 0 and not game.game_over:
        await asyncio.sleep(1)
        remaining -= 1

        await broadcast_to_host({
            "type": "timer",
            "phase": "tiebreaker",
            "phase_remaining": remaining,
            "game_remaining": game.get_time_remaining(),
        })

    if game.game_over:
        return

    if game.current_phase != "tiebreaker":
        return  # Already handled by early-vote path

    # Determine winner from tiebreaker or random
    winning_index = game.determine_winner()
    await finalize_round(winning_index)


async def finalize_round(winning_index: int):
    """Finalize the round: apply impacts, record history, broadcast results."""
    vote_counts = game.get_vote_counts()
    economy_before = game.economy.get_state()

    round_record = game.end_round(winning_index)

    economy_after = game.economy.get_state()
    winning_proposal = round_record.proposals[winning_index] if winning_index < len(round_record.proposals) else None

    # Broadcast results to host
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
        "destruction_score": game.economy.get_destruction_score(),
        "time_remaining": game.get_time_remaining(),
    })

    # Tell parliament their vote counts
    for name in game.parliament_members:
        idx = game.players[name].parliament_index
        votes_this_round = vote_counts.get(idx, 0)
        await send_to_player(name, {
            "type": "round_result",
            "votes_received": votes_this_round,
            "running_total": game.players[name].votes_received,
        })

    # Tell people what won
    await broadcast_to_people({
        "type": "round_result",
        "winning_text": winning_proposal.text if winning_proposal else "No policy",
    })

    # Check game over
    if game.is_game_over():
        game.game_over = True
        game.current_phase = "gameover"
        await send_game_over()
        return

    # Fire next scenario generation in parallel with results display
    game.scenario_task = asyncio.create_task(generate_next_scenario_background())

    # Wait for results display (3-5 sec)
    await asyncio.sleep(4)

    if game.game_over:
        return

    # Get next scenario
    scenario = None
    if game.scenario_task:
        if not game.scenario_task.done():
            await broadcast_to_host({"type": "loading", "message": random.choice(LOADING_MESSAGES)})
            try:
                await asyncio.wait_for(game.scenario_task, timeout=20.0)
            except asyncio.TimeoutError:
                logger.error("Next scenario generation timed out")
        if game.scenario_task.done():
            try:
                scenario = game.scenario_task.result()
            except BaseException:
                scenario = None

    if not scenario:
        scenario = get_next_fallback_scenario(game.settings.mode)

    # Start next round
    await start_round(scenario)


async def generate_next_scenario_background() -> dict:
    """Background task: generate next scenario."""
    try:
        return await generate_scenario(
            game.economy.get_state(),
            game.get_round_history_for_llm(),
            game.round_number + 1,
            game.settings.mode,
        )
    except Exception as e:
        logger.error(f"Scenario generation failed: {e}")
        return copy.deepcopy(FALLBACK_SCENARIO)


async def send_game_over():
    """Send game over to all clients."""
    # Generate narrative
    policy_list = []
    for rr in game.round_history:
        if rr.winning_proposal_index >= 0 and rr.winning_proposal_index < len(rr.proposals):
            policy_list.append(rr.proposals[rr.winning_proposal_index].text)

    starting_state = {
        "gdp": config.STARTING_GDP,
        "employment": config.STARTING_EMPLOYMENT,
        "inflation": config.STARTING_INFLATION,
        "public_trust": config.STARTING_PUBLIC_TRUST,
        "trade_balance": config.STARTING_TRADE_BALANCE,
        "national_debt": config.STARTING_NATIONAL_DEBT,
    }

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
        logger.error(f"Narrative failed: {e}")
        narrative = "The economy has spoken. No further comment."

    # Get full results
    results = game.get_final_results()
    results["narrative"] = narrative

    # Send to host
    await broadcast_to_host(results)

    # Send personalized results to each player
    for name in game.players:
        personal = game.get_player_game_over(name)
        personal["narrative"] = narrative
        await send_to_player(name, personal)


# ============================================================
# Game Timer
# ============================================================

async def game_timer_loop():
    """Overall game timer — ends game when time is up."""
    while game.started and not game.game_over:
        await asyncio.sleep(1)
        if game.is_game_over() and not game.game_over:
            game.game_over = True
            game.current_phase = "gameover"
            # Cancel phase timer
            if phase_timer_task and not phase_timer_task.done():
                phase_timer_task.cancel()
            await send_game_over()
            return


# ============================================================
# WebSocket: Host
# ============================================================

@app.websocket("/ws/host")
async def ws_host(ws: WebSocket):
    await ws.accept()
    host_connections.add(ws)
    logger.info("Host connected")

    # Send current state
    if not game.started:
        await ws.send_text(json.dumps(game.get_lobby_state()))
        await ws.send_text(json.dumps({"type": "qr_url", "url": get_player_url()}))
        await ws.send_text(json.dumps({"type": "settings_update", "settings": game.settings.to_dict()}))

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)

            if msg.get("action") == "start" and not game.started:
                await start_game_endpoint()

            elif msg.get("action") == "update_settings" and not game.started:
                game.update_settings(msg.get("settings", {}))
                await broadcast_to_host({
                    "type": "settings_update",
                    "settings": game.settings.to_dict(),
                })

    except WebSocketDisconnect:
        host_connections.discard(ws)
        logger.info("Host disconnected")


# ============================================================
# WebSocket: Player
# ============================================================

@app.websocket("/ws/player/{name}")
async def ws_player(ws: WebSocket, name: str):
    await ws.accept()

    if game.started:
        # Reconnect
        if game.reconnect_player(name):
            player_connections[name] = ws
            logger.info(f"Player reconnected: {name}")
            pd = game.players.get(name)
            if pd:
                await ws.send_text(json.dumps({
                    "type": "role_assigned",
                    "role": pd.role,
                    "parliament_index": pd.parliament_index if pd.role == "parliament" else -1,
                }))
                # Send current phase info
                if game.current_phase == "writing" and pd.role == "parliament":
                    await ws.send_text(json.dumps({
                        "type": "writing_phase",
                        "round": game.round_number,
                        "scenario": {
                            "headline": game.current_scenario.get("headline", "") if game.current_scenario else "",
                            "description": game.current_scenario.get("description", "") if game.current_scenario else "",
                        },
                        "timer": 0,  # they'll get the countdown from next tick
                        "char_limit": 200,
                    }))
                elif game.current_phase == "voting" and pd.role == "people":
                    await ws.send_text(json.dumps({
                        "type": "voting_phase",
                        "proposal_count": len(game.parliament_members),
                        "timer": 0,
                    }))
                elif game.game_over:
                    personal = game.get_player_game_over(name)
                    await ws.send_text(json.dumps(personal))
        else:
            await ws.send_text(json.dumps({"type": "error", "message": "Game already started"}))
            await ws.close()
            return
    else:
        # Pre-game: try to add new player, or reconnect if they dropped
        if name in game.players:
            # Player exists but disconnected — reconnect them
            game.players[name].connected = True
            player_connections[name] = ws
            logger.info(f"Player reconnected (pre-game): {name}")
            await broadcast_to_host(game.get_lobby_state())
            await ws.send_text(json.dumps({"type": "joined", "name": name}))
        elif not game.add_player(name):
            await ws.send_text(json.dumps({"type": "error", "message": "Name taken or game started"}))
            await ws.close()
            return
        else:
            player_connections[name] = ws
            logger.info(f"Player joined: {name}")
            await broadcast_to_host(game.get_lobby_state())
            await ws.send_text(json.dumps({"type": "joined", "name": name}))

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)

            msg_type = msg.get("type", "")

            # Parliament: keystroke
            if msg_type == "keystroke" and game.current_phase == "writing":
                text = msg.get("text", "")
                if game.update_proposal(name, text):
                    # Broadcast to host for live display
                    idx = game.players[name].parliament_index
                    await broadcast_to_host({
                        "type": "proposal_keystroke",
                        "parliament_index": idx,
                        "text": game.proposals.get(name, ""),
                    })

            # People: vote
            elif msg_type == "vote" and game.current_phase == "voting":
                proposal_index = int(msg.get("proposal_index", -1))
                if game.submit_vote(name, proposal_index):
                    vote_counts = game.get_vote_counts()
                    total_voted = len(game.votes)
                    total_people = len(game.people_members)

                    await broadcast_to_host({
                        "type": "vote_update",
                        "vote_counts": {str(k): v for k, v in vote_counts.items()},
                        "total_voted": total_voted,
                        "total_people": total_people,
                    })

                    await ws.send_text(json.dumps({
                        "type": "vote_confirmed",
                        "voted_for": proposal_index,
                    }))

                    # Check if all voted — end early
                    if game.all_people_voted() and not game.game_over:
                        if phase_timer_task and not phase_timer_task.done():
                            phase_timer_task.cancel()
                        await finish_voting()

            # People: tiebreaker vote
            elif msg_type == "tiebreaker_vote" and game.current_phase == "tiebreaker":
                proposal_index = int(msg.get("proposal_index", -1))
                if game.submit_tiebreaker_vote(name, proposal_index):
                    tb_counts = game.get_tiebreaker_vote_counts()
                    await broadcast_to_host({
                        "type": "tiebreaker_update",
                        "vote_counts": {str(k): v for k, v in tb_counts.items()},
                    })
                    await ws.send_text(json.dumps({
                        "type": "vote_confirmed",
                        "voted_for": proposal_index,
                    }))

                    # Check if all tiebreaker voted
                    if game.all_people_tiebreaker_voted() and not game.game_over:
                        if game.current_phase != "tiebreaker":
                            continue
                        if phase_timer_task and not phase_timer_task.done():
                            phase_timer_task.cancel()
                        winning_index = game.determine_winner()
                        await finalize_round(winning_index)

    except WebSocketDisconnect:
        player_connections.pop(name, None)
        if name in game.players:
            game.players[name].connected = False
        logger.info(f"Player disconnected: {name}")
        if not game.started:
            await broadcast_to_host(game.get_lobby_state())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host=config.HOST, port=config.PORT, reload=True)

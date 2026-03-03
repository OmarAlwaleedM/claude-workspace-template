import asyncio
import io
import json
import logging

import qrcode
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse

import config
from game import Game

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Economy Collapse Speedrun")

game = Game()

# Connected WebSocket sets
host_connections: set[WebSocket] = set()
player_connections: dict[str, WebSocket] = {}  # name -> ws

# Round management
round_lock = asyncio.Lock()
round_start_time: float = 0  # asyncio loop time when current round started


# --- Broadcast helpers ---

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


async def broadcast_to_players(data: dict):
    message = json.dumps(data)
    dead = []
    for name, ws in player_connections.items():
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(name)
    for name in dead:
        player_connections.pop(name, None)


async def broadcast_all(data: dict):
    await broadcast_to_host(data)
    await broadcast_to_players(data)


# Wire callbacks
game.on_broadcast_host = broadcast_to_host
game.on_broadcast_players = broadcast_to_players
game.on_broadcast_all = broadcast_all


# --- HTTP Endpoints ---

@app.get("/")
async def host_page():
    return FileResponse("static/host.html")


@app.get("/play")
async def player_page():
    return FileResponse("static/player.html")


@app.get("/qr")
async def qr_code():
    url = f"{config.NGROK_URL}/play"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@app.post("/start")
async def start_game():
    if game.started:
        return {"error": "Game already started"}
    if game.get_player_count() < config.MIN_PLAYERS:
        return {"error": f"Need at least {config.MIN_PLAYERS} players"}

    # Notify loading
    await broadcast_all({"type": "loading", "message": "Generating first scenario... The economy awaits your destruction."})

    await game.start_game()

    scenario_host = game.get_current_scenario_for_host()
    scenario_players = game.get_current_scenario_for_players()

    await broadcast_to_host({
        "type": "round_start",
        "round": game.round_number,
        "scenario": scenario_host,
        "economy": game.economy.get_state(),
        "destruction_score": game.economy.get_destruction_score(),
        "time_remaining": game.get_time_remaining(),
    })

    await broadcast_to_players({
        "type": "round_start",
        "round": game.round_number,
        "scenario": scenario_players,
    })

    # Start game timer
    asyncio.create_task(game_timer_loop())
    # Start round timer
    asyncio.create_task(round_timer_loop())

    return {"status": "started", "round": 1}


@app.get("/state")
async def debug_state():
    return {
        "started": game.started,
        "round": game.round_number,
        "economy": game.economy.get_state(),
        "destruction_score": game.economy.get_destruction_score(),
        "players": {n: d["score"] for n, d in game.players.items()},
        "votes": game.votes,
        "game_over": game.game_over,
    }


# --- WebSocket: Host ---

@app.websocket("/ws/host")
async def ws_host(ws: WebSocket):
    await ws.accept()
    host_connections.add(ws)
    logger.info("Host connected")

    # Send current state
    if not game.started:
        await ws.send_text(json.dumps(game.get_lobby_state()))
        await ws.send_text(json.dumps({"type": "qr_url", "url": f"{config.NGROK_URL}/play"}))
    else:
        await ws.send_text(json.dumps({
            "type": "round_start",
            "round": game.round_number,
            "scenario": game.get_current_scenario_for_host(),
            "economy": game.economy.get_state(),
            "destruction_score": game.economy.get_destruction_score(),
            "time_remaining": game.get_time_remaining(),
        }))

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            # Host can send start command via WS too
            if msg.get("action") == "start":
                if not game.started:
                    await start_game()
    except WebSocketDisconnect:
        host_connections.discard(ws)
        logger.info("Host disconnected")


# --- WebSocket: Player ---

@app.websocket("/ws/player/{name}")
async def ws_player(ws: WebSocket, name: str):
    await ws.accept()

    # Try to join
    if game.started:
        # Allow reconnect
        if game.reconnect_player(name):
            player_connections[name] = ws
            logger.info(f"Player reconnected: {name}")
            # Send current round
            if game.current_scenario and not game.game_over:
                await ws.send_text(json.dumps({
                    "type": "round_start",
                    "round": game.round_number,
                    "scenario": game.get_current_scenario_for_players(),
                }))
            elif game.game_over:
                results = game.get_final_results()
                await ws.send_text(json.dumps(results))
        else:
            await ws.send_text(json.dumps({"type": "error", "message": "Game already started"}))
            await ws.close()
            return
    else:
        if not game.add_player(name):
            await ws.send_text(json.dumps({"type": "error", "message": "Name taken or game started"}))
            await ws.close()
            return
        player_connections[name] = ws
        logger.info(f"Player joined: {name}")

        # Notify all about lobby update
        await broadcast_to_host(game.get_lobby_state())
        await ws.send_text(json.dumps({"type": "joined", "name": name}))

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "vote" and not game.game_over:
                label = msg.get("label", "").upper()
                if game.submit_vote(name, label):
                    # Broadcast vote update to host
                    await broadcast_to_host({
                        "type": "vote_update",
                        "votes": game.get_vote_counts(),
                        "total_voted": len(game.votes),
                        "total_players": game.get_player_count(),
                    })
                    await ws.send_text(json.dumps({"type": "vote_confirmed", "label": label}))

                    # Check if all voted — end round early
                    if game.all_voted() and not game.game_over:
                        await end_current_round()

    except WebSocketDisconnect:
        player_connections.pop(name, None)
        game.remove_player(name)
        logger.info(f"Player disconnected: {name}")
        await broadcast_to_host(game.get_lobby_state())


# --- Game loops ---

async def round_timer_loop():
    """Countdown for each round. Ends round when timer expires."""
    global round_start_time
    round_start_time = asyncio.get_event_loop().time()

    while game.started and not game.game_over:
        await asyncio.sleep(1)

        # Broadcast timer to host
        elapsed_round = asyncio.get_event_loop().time() - round_start_time
        round_remaining = max(0, config.ROUND_TIME_SECONDS - int(elapsed_round))

        await broadcast_to_host({
            "type": "timer",
            "round_time": config.ROUND_TIME_SECONDS,
            "round_remaining": round_remaining,
            "time_remaining": game.get_time_remaining(),
        })

        # Check if round timer expired
        if elapsed_round >= config.ROUND_TIME_SECONDS and not game.game_over:
            await end_current_round()


async def game_timer_loop():
    """Overall game timer — ends game when time is up."""
    while game.started and not game.game_over:
        await asyncio.sleep(1)
        if game.is_game_over():
            game.game_over = True
            results = game.get_final_results()
            await broadcast_all(results)
            return


async def end_current_round():
    """End the current round, broadcast results, start next round."""
    global round_start_time

    async with round_lock:
        if game.game_over:
            return
        # Prevent double-ending the same round
        current_round = game.round_number

        results = await game.end_round()
        await broadcast_all(results)

        if game.game_over:
            final = game.get_final_results()
            await broadcast_all(final)
            return

        # Small delay for players to see results
        await asyncio.sleep(3)

        if game.game_over:
            return

        # Reset round timer
        round_start_time = asyncio.get_event_loop().time()

        # Send next round
        scenario_host = game.get_current_scenario_for_host()
        scenario_players = game.get_current_scenario_for_players()

        await broadcast_to_host({
            "type": "round_start",
            "round": game.round_number,
            "scenario": scenario_host,
            "economy": game.economy.get_state(),
            "destruction_score": game.economy.get_destruction_score(),
            "time_remaining": game.get_time_remaining(),
        })

        await broadcast_to_players({
            "type": "round_start",
            "round": game.round_number,
            "scenario": scenario_players,
        })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host=config.HOST, port=config.PORT, reload=True)

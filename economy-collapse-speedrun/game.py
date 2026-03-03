import asyncio
import copy
import logging
import random
import time

import config
from economy import Economy
from llm import FALLBACK_SCENARIO, generate_scenario

logger = logging.getLogger(__name__)

LOADING_MESSAGES = [
    "The economy is processing your terrible decisions...",
    "Economists are crying. Please hold.",
    "Calculating how much damage you've done...",
    "The IMF is trying to reach you. Please wait.",
    "Your economy is buffering. Just like your country's internet.",
]


class Game:
    def __init__(self, duration_seconds: int = config.GAME_DURATION_SECONDS):
        self.economy = Economy()
        self.duration_seconds = duration_seconds
        self.players: dict[str, dict] = {}  # name -> {score, connected}
        self.round_number = 0
        self.current_scenario: dict | None = None
        self.cached_scenario: dict | None = None
        self.fallback_scenario: dict = copy.deepcopy(FALLBACK_SCENARIO)
        self.generating: bool = False
        self._precache_task: asyncio.Task | None = None
        self.votes: dict[str, str] = {}  # player_name -> option_label
        self.policy_history: list[dict] = []  # [{round, policy_text, option_label, impacts}]
        self.started = False
        self.game_over = False
        self.start_time: float = 0
        self._round_timer_task: asyncio.Task | None = None

        # Callbacks set by server.py
        self.on_broadcast_host = None
        self.on_broadcast_players = None
        self.on_broadcast_all = None

    def add_player(self, name: str) -> bool:
        if self.started:
            return False
        if name in self.players:
            return False
        self.players[name] = {"score": 0, "connected": True}
        return True

    def remove_player(self, name: str):
        if name in self.players:
            self.players[name]["connected"] = False

    def reconnect_player(self, name: str) -> bool:
        if name in self.players:
            self.players[name]["connected"] = True
            return True
        return False

    def get_player_count(self) -> int:
        return sum(1 for p in self.players.values() if p["connected"])

    def get_player_names(self) -> list[str]:
        return [n for n, p in self.players.items() if p["connected"]]

    async def start_game(self):
        self.started = True
        self.start_time = time.time()
        self.round_number = 1

        # Generate round 1 scenario (blocking)
        try:
            self.current_scenario = await generate_scenario(
                self.economy.get_state(), self.policy_history, self.round_number
            )
        except Exception as e:
            logger.error(f"Failed to generate first scenario: {e}")
            self.current_scenario = copy.deepcopy(self.fallback_scenario)

        # Pre-cache round 2 in background
        self._start_precache()

    def _start_precache(self):
        if not self.generating:
            self.generating = True
            self._precache_task = asyncio.create_task(self._precache_next())

    async def _precache_next(self):
        try:
            scenario = await generate_scenario(
                self.economy.get_state(),
                self.policy_history,
                self.round_number + 1,
            )
            self.cached_scenario = scenario
        except Exception as e:
            logger.warning(f"Pre-cache generation failed: {e}")
            self.cached_scenario = None
        finally:
            self.generating = False

    def get_current_scenario_for_players(self) -> dict | None:
        if not self.current_scenario:
            return None
        # Strip destruction_points from options
        scenario = copy.deepcopy(self.current_scenario)
        for opt in scenario["options"]:
            opt.pop("destruction_points", None)
            opt.pop("impacts", None)
        return scenario

    def get_current_scenario_for_host(self) -> dict | None:
        if not self.current_scenario:
            return None
        # Host sees options text but not points either (don't spoil it)
        scenario = copy.deepcopy(self.current_scenario)
        for opt in scenario["options"]:
            opt.pop("destruction_points", None)
            opt.pop("impacts", None)
        return scenario

    def submit_vote(self, player_name: str, option_label: str) -> bool:
        if player_name not in self.players:
            return False
        if player_name in self.votes:
            return False  # Already voted
        valid_labels = {"A", "B", "C", "D"}
        if option_label.upper() not in valid_labels:
            return False
        self.votes[player_name] = option_label.upper()

        # Track individual score
        if self.current_scenario:
            for opt in self.current_scenario["options"]:
                if opt["label"] == option_label.upper():
                    self.players[player_name]["score"] += opt.get("destruction_points", 0)
                    break
        return True

    def all_voted(self) -> bool:
        active = [n for n, p in self.players.items() if p["connected"]]
        return all(n in self.votes for n in active)

    def get_vote_counts(self) -> dict[str, int]:
        counts = {"A": 0, "B": 0, "C": 0, "D": 0}
        for label in self.votes.values():
            counts[label] = counts.get(label, 0) + 1
        return counts

    async def end_round(self) -> dict:
        vote_counts = self.get_vote_counts()

        # Determine winner (most votes, random tiebreak)
        max_votes = max(vote_counts.values()) if vote_counts.values() else 0
        if max_votes == 0:
            winning_label = "C"  # If no one votes, chaos wins
        else:
            winners = [label for label, count in vote_counts.items() if count == max_votes]
            winning_label = random.choice(winners)

        # Find the winning option
        winning_option = None
        if self.current_scenario:
            for opt in self.current_scenario["options"]:
                if opt["label"] == winning_label:
                    winning_option = opt
                    break

        # Apply impacts
        old_state = self.economy.get_state()
        if winning_option:
            self.economy.apply_policy(winning_option["impacts"])
            self.economy.add_destruction_points(winning_option.get("destruction_points", 0))
            self.policy_history.append({
                "round": self.round_number,
                "policy_text": winning_option["text"],
                "option_label": winning_label,
                "impacts": winning_option["impacts"],
            })

        new_state = self.economy.get_state()

        results = {
            "type": "round_end",
            "round": self.round_number,
            "vote_counts": vote_counts,
            "winning_label": winning_label,
            "winning_policy": winning_option["text"] if winning_option else "No policy enacted",
            "impacts": winning_option["impacts"] if winning_option else {},
            "destruction_points": winning_option.get("destruction_points", 0) if winning_option else 0,
            "old_economy": old_state,
            "new_economy": new_state,
            "destruction_score": self.economy.get_destruction_score(),
        }

        # Reset votes for next round
        self.votes = {}
        self.round_number += 1

        # Check game over
        if self.is_game_over():
            self.game_over = True
            return results

        # Get next scenario
        if self.cached_scenario:
            self.current_scenario = self.cached_scenario
            self.cached_scenario = None
            self._start_precache()
        elif self._precache_task and not self._precache_task.done():
            # Still generating — wait for it
            if self.on_broadcast_all:
                await self.on_broadcast_all({
                    "type": "loading",
                    "message": random.choice(LOADING_MESSAGES),
                })
            try:
                await asyncio.wait_for(self._precache_task, timeout=15.0)
                if self.cached_scenario:
                    self.current_scenario = self.cached_scenario
                    self.cached_scenario = None
                else:
                    self.current_scenario = copy.deepcopy(self.fallback_scenario)
            except asyncio.TimeoutError:
                logger.error("Pre-cache timed out, using fallback")
                self.current_scenario = copy.deepcopy(self.fallback_scenario)
            self._start_precache()
        else:
            # Nothing cached, nothing generating — generate now
            if self.on_broadcast_all:
                await self.on_broadcast_all({
                    "type": "loading",
                    "message": random.choice(LOADING_MESSAGES),
                })
            try:
                self.current_scenario = await generate_scenario(
                    self.economy.get_state(), self.policy_history, self.round_number
                )
            except Exception as e:
                logger.error(f"Scenario generation failed: {e}")
                self.current_scenario = copy.deepcopy(self.fallback_scenario)
            self._start_precache()

        return results

    def is_game_over(self) -> bool:
        if self.game_over:
            return True
        if self.economy.is_collapsed():
            return True
        if self.start_time and (time.time() - self.start_time) >= self.duration_seconds:
            return True
        return False

    def get_time_remaining(self) -> int:
        if not self.start_time:
            return self.duration_seconds
        remaining = self.duration_seconds - (time.time() - self.start_time)
        return max(0, int(remaining))

    def get_final_results(self) -> dict:
        sorted_players = sorted(self.players.items(), key=lambda x: x[1]["score"])
        mvp_destroyer = sorted_players[0] if sorted_players else None
        boy_scout = sorted_players[-1] if sorted_players else None

        return {
            "type": "game_over",
            "collapsed": self.economy.is_collapsed(),
            "rounds_played": self.round_number - 1,
            "destruction_score": self.economy.get_destruction_score(),
            "final_economy": self.economy.get_state(),
            "leaderboard": [
                {"name": name, "score": data["score"]}
                for name, data in sorted_players
            ],
            "mvp_destroyer": {
                "name": mvp_destroyer[0],
                "score": mvp_destroyer[1]["score"],
            } if mvp_destroyer else None,
            "boy_scout": {
                "name": boy_scout[0],
                "score": boy_scout[1]["score"],
            } if boy_scout else None,
        }

    def get_lobby_state(self) -> dict:
        return {
            "type": "lobby_update",
            "players": self.get_player_names(),
            "player_count": self.get_player_count(),
            "min_players": config.MIN_PLAYERS,
        }

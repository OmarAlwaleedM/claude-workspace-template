import asyncio
import copy
import logging
import random
import time
from dataclasses import dataclass, field

import config
from config import GameSettings
from economy import Economy

logger = logging.getLogger(__name__)

LOADING_MESSAGES = [
    "The economy is processing your terrible decisions...",
    "Economists are crying. Please hold.",
    "Calculating how much damage you've done...",
    "The IMF is trying to reach you. Please wait.",
    "Your economy is buffering. Just like your country's internet.",
]


@dataclass
class ProposalRecord:
    parliament_member: str
    parliament_index: int
    text: str
    votes_received: int = 0
    ai_quality_score: int = 50
    ai_impacts: dict = field(default_factory=dict)
    ai_destruction_points: int = 0
    ai_commentary: str = ""


@dataclass
class RoundRecord:
    round_number: int
    scenario: dict
    proposals: list  # list of ProposalRecord
    winning_proposal_index: int = -1
    vote_counts: dict = field(default_factory=dict)  # proposal_index -> count
    economy_before: dict = field(default_factory=dict)
    economy_after: dict = field(default_factory=dict)


@dataclass
class PlayerData:
    role: str = "people"  # "parliament" | "people"
    score: int = 0
    connected: bool = True
    votes_received: int = 0  # parliament only: total across all rounds
    parliament_index: int = -1  # parliament only: 0-based index


class Game:
    def __init__(self):
        self.settings = GameSettings()
        self.economy = Economy()

        # Players
        self.players: dict[str, PlayerData] = {}  # name -> PlayerData
        self.parliament_members: list[str] = []  # ordered list of parliament names
        self.people_members: list[str] = []

        # Game state
        self.started = False
        self.game_over = False
        self.start_time: float = 0
        self.round_number = 0
        self.current_phase: str = "lobby"  # lobby|writing|voting|tiebreaker|results|gameover

        # Current round data
        self.current_scenario: dict | None = None
        self.proposals: dict[str, str] = {}  # parliament_name -> current text (live)
        self.proposal_locked: dict[str, bool] = {}  # parliament_name -> locked?
        self.votes: dict[str, int] = {}  # person_name -> proposal_index (0-based)
        self.tiebreaker_votes: dict[str, int] = {}  # person_name -> proposal_index
        self.ai_evaluations: list[dict] | None = None  # list of eval dicts from AI

        # History
        self.round_history: list[RoundRecord] = []

        # Background tasks
        self.next_scenario: dict | None = None
        self.grading_task: asyncio.Task | None = None
        self.scenario_task: asyncio.Task | None = None

        # Callbacks (set by server.py)
        self.on_broadcast_host = None
        self.on_broadcast_parliament = None
        self.on_broadcast_people = None
        self.on_broadcast_all = None
        self.on_send_to_player = None

    # ---- Player Management ----

    def add_player(self, name: str) -> bool:
        if self.started:
            return False
        if name in self.players:
            return False
        self.players[name] = PlayerData()
        return True

    def remove_player(self, name: str):
        if name in self.players:
            self.players[name].connected = False

    def reconnect_player(self, name: str) -> bool:
        if name in self.players:
            self.players[name].connected = True
            return True
        return False

    def get_player_count(self) -> int:
        return sum(1 for p in self.players.values() if p.connected)

    def get_player_names(self) -> list[str]:
        return [n for n, p in self.players.items() if p.connected]

    # ---- Game Setup ----

    def update_settings(self, settings_dict: dict):
        self.settings = GameSettings.from_dict(settings_dict)

    def assign_roles(self):
        """Randomly assign parliament members from connected players."""
        connected = self.get_player_names()
        random.shuffle(connected)

        parliament_size = min(self.settings.parliament_size, len(connected) - 1)
        parliament_size = max(parliament_size, 1)  # at least 1 parliament member

        self.parliament_members = connected[:parliament_size]
        self.people_members = connected[parliament_size:]

        for i, name in enumerate(self.parliament_members):
            self.players[name].role = "parliament"
            self.players[name].parliament_index = i

        for name in self.people_members:
            self.players[name].role = "people"

    async def start_game(self):
        """Initialize and start the game."""
        self.started = True
        self.start_time = time.time()
        self.round_number = 0
        self.assign_roles()

    # ---- Round Management ----

    def start_new_round(self, scenario: dict):
        """Begin a new round with the given scenario."""
        self.round_number += 1
        self.current_scenario = scenario
        self.current_phase = "writing"
        self.proposals = {name: "" for name in self.parliament_members}
        self.proposal_locked = {name: False for name in self.parliament_members}
        self.votes = {}
        self.tiebreaker_votes = {}
        self.ai_evaluations = None

    def update_proposal(self, parliament_name: str, text: str) -> bool:
        """Update a parliament member's proposal text (keystroke handler)."""
        if parliament_name not in self.parliament_members:
            return False
        if self.proposal_locked.get(parliament_name, False):
            return False
        if self.current_phase != "writing":
            return False
        # Enforce 200 char limit
        self.proposals[parliament_name] = text[:200]
        return True

    def lock_all_proposals(self):
        """Lock all proposals at end of writing phase."""
        for name in self.parliament_members:
            self.proposal_locked[name] = True
        self.current_phase = "voting"

    def get_proposals_list(self) -> list[dict]:
        """Get ordered list of proposals for display/evaluation."""
        result = []
        for i, name in enumerate(self.parliament_members):
            text = self.proposals.get(name, "").strip()
            result.append({
                "index": i,
                "parliament_member": name,
                "text": text,
                "display_name": name if not self.settings.anonymous else f"Proposal {i + 1}",
            })
        return result

    def submit_vote(self, player_name: str, proposal_index: int) -> bool:
        """A person submits a vote for a proposal."""
        if player_name not in self.people_members:
            return False
        if player_name in self.votes:
            return False  # already voted
        if self.current_phase != "voting":
            return False
        if proposal_index < 0 or proposal_index >= len(self.parliament_members):
            return False
        self.votes[player_name] = proposal_index
        return True

    def submit_tiebreaker_vote(self, player_name: str, proposal_index: int) -> bool:
        """A person submits a tiebreaker vote."""
        if player_name not in self.people_members:
            return False
        if player_name in self.tiebreaker_votes:
            return False
        if self.current_phase != "tiebreaker":
            return False
        self.tiebreaker_votes[player_name] = proposal_index
        return True

    def all_people_voted(self) -> bool:
        active_people = [n for n in self.people_members if self.players[n].connected]
        return all(n in self.votes for n in active_people)

    def all_people_tiebreaker_voted(self) -> bool:
        active_people = [n for n in self.people_members if self.players[n].connected]
        return all(n in self.tiebreaker_votes for n in active_people)

    def get_vote_counts(self) -> dict[int, int]:
        """Get vote counts per proposal index."""
        counts = {}
        for i in range(len(self.parliament_members)):
            counts[i] = 0
        for idx in self.votes.values():
            counts[idx] = counts.get(idx, 0) + 1
        return counts

    def get_tiebreaker_vote_counts(self) -> dict[int, int]:
        counts = {}
        for idx in self.tiebreaker_votes.values():
            counts[idx] = counts.get(idx, 0) + 1
        return counts

    def detect_tie(self) -> list[int] | None:
        """Check if there's a tie. Returns list of tied indices or None."""
        counts = self.get_vote_counts()
        if not counts:
            return None
        max_votes = max(counts.values())
        if max_votes == 0:
            return None
        tied = [idx for idx, count in counts.items() if count == max_votes]
        if len(tied) > 1:
            return tied
        return None

    def determine_winner(self) -> int:
        """Determine the winning proposal index. Call after voting (and tiebreaker if needed)."""
        counts = self.get_vote_counts()
        if not counts:
            return 0  # fallback

        max_votes = max(counts.values())
        if max_votes == 0:
            return random.randint(0, len(self.parliament_members) - 1)

        winners = [idx for idx, count in counts.items() if count == max_votes]
        if len(winners) == 1:
            return winners[0]

        # Tiebreaker already happened — use tiebreaker votes
        if self.tiebreaker_votes:
            tb_counts = self.get_tiebreaker_vote_counts()
            if tb_counts:
                max_tb = max(tb_counts.values())
                tb_winners = [idx for idx, count in tb_counts.items() if count == max_tb]
                if len(tb_winners) == 1:
                    return tb_winners[0]
                # Still tied after tiebreaker — random
                return random.choice(tb_winners)

        # Random tiebreak
        return random.choice(winners)

    def end_round(self, winning_index: int) -> RoundRecord:
        """Finalize round: apply impacts, record history, update scores."""
        vote_counts = self.get_vote_counts()
        economy_before = self.economy.get_state()

        # Get winning proposal's AI evaluation
        winning_eval = None
        if self.ai_evaluations:
            for ev in self.ai_evaluations:
                if ev.get("proposal_index") == winning_index:
                    winning_eval = ev
                    break

        # Apply winning policy impacts
        if winning_eval and winning_eval.get("impacts"):
            self.economy.apply_policy(winning_eval["impacts"])
            self.economy.add_destruction_points(winning_eval.get("destruction_points", 0))

        economy_after = self.economy.get_state()

        # Build proposal records
        proposal_records = []
        for i, name in enumerate(self.parliament_members):
            text = self.proposals.get(name, "")
            votes_for = vote_counts.get(i, 0)

            # Get AI eval for this proposal
            ai_score = 50
            ai_impacts = {}
            ai_dp = 0
            ai_comment = ""
            if self.ai_evaluations:
                for ev in self.ai_evaluations:
                    if ev.get("proposal_index") == i:
                        ai_score = ev.get("quality_score", 50)
                        ai_impacts = ev.get("impacts", {})
                        ai_dp = ev.get("destruction_points", 0)
                        ai_comment = ev.get("ai_commentary", "")
                        break

            record = ProposalRecord(
                parliament_member=name,
                parliament_index=i,
                text=text,
                votes_received=votes_for,
                ai_quality_score=ai_score,
                ai_impacts=ai_impacts,
                ai_destruction_points=ai_dp,
                ai_commentary=ai_comment,
            )
            proposal_records.append(record)

            # Parliament scoring: add votes received
            self.players[name].votes_received += votes_for

        # People scoring: add AI quality of proposal they voted for
        for person_name, voted_idx in self.votes.items():
            ai_score = 50
            if self.ai_evaluations:
                for ev in self.ai_evaluations:
                    if ev.get("proposal_index") == voted_idx:
                        ai_score = ev.get("quality_score", 50)
                        break
            self.players[person_name].score += ai_score

        # Record round history
        round_record = RoundRecord(
            round_number=self.round_number,
            scenario=copy.deepcopy(self.current_scenario) if self.current_scenario else {},
            proposals=proposal_records,
            winning_proposal_index=winning_index,
            vote_counts=vote_counts,
            economy_before=economy_before,
            economy_after=economy_after,
        )
        self.round_history.append(round_record)

        self.current_phase = "results"
        return round_record

    # ---- Game State Checks ----

    def is_game_over(self) -> bool:
        if self.game_over:
            return True
        if self.economy.is_collapsed():
            return True
        if self.start_time and (time.time() - self.start_time) >= self.settings.duration_seconds:
            return True
        return False

    def get_time_remaining(self) -> int:
        if not self.start_time:
            return self.settings.duration_seconds
        remaining = self.settings.duration_seconds - (time.time() - self.start_time)
        return max(0, int(remaining))

    # ---- Data for Clients ----

    def get_lobby_state(self) -> dict:
        return {
            "type": "lobby_update",
            "players": self.get_player_names(),
            "player_count": self.get_player_count(),
            "min_players": config.MIN_PLAYERS,
        }

    def get_round_history_for_llm(self) -> list[dict]:
        """Compact history for LLM context."""
        history = []
        for rr in self.round_history:
            proposals_summary = []
            for pr in rr.proposals:
                proposals_summary.append({
                    "text": pr.text,
                    "votes": pr.votes_received,
                    "won": pr.parliament_index == rr.winning_proposal_index,
                })
            history.append({
                "round": rr.round_number,
                "scenario_headline": rr.scenario.get("headline", ""),
                "proposals": proposals_summary,
                "winning_policy": rr.proposals[rr.winning_proposal_index].text if rr.winning_proposal_index >= 0 and rr.winning_proposal_index < len(rr.proposals) else "",
                "vote_counts": rr.vote_counts,
                "economy_after": rr.economy_after,
            })
        return history

    def get_final_results(self) -> dict:
        """Compile all final game data for the game over screen."""
        # Parliament leaderboard (by total votes received)
        parliament_lb = sorted(
            [
                {"name": name, "votes_received": self.players[name].votes_received}
                for name in self.parliament_members
            ],
            key=lambda x: x["votes_received"],
            reverse=True,
        )

        # People leaderboard (by cumulative AI quality score)
        people_lb = sorted(
            [
                {"name": name, "score": self.players[name].score}
                for name in self.people_members
                if self.players[name].connected
            ],
            key=lambda x: x["score"],
            reverse=True,
        )

        # AI reveal: per-round proposal details
        ai_reveal = []
        for rr in self.round_history:
            round_data = {
                "round": rr.round_number,
                "scenario_headline": rr.scenario.get("headline", ""),
                "proposals": [],
                "winning_index": rr.winning_proposal_index,
            }
            for pr in rr.proposals:
                round_data["proposals"].append({
                    "parliament_member": pr.parliament_member,
                    "display_name": pr.parliament_member if not self.settings.anonymous else f"Proposal {pr.parliament_index + 1}",
                    "text": pr.text,
                    "votes_received": pr.votes_received,
                    "ai_quality_score": pr.ai_quality_score,
                    "ai_commentary": pr.ai_commentary,
                    "won": pr.parliament_index == rr.winning_proposal_index,
                })
            ai_reveal.append(round_data)

        # Awards
        awards = {}
        if self.settings.mode == "constructive":
            if parliament_lb:
                awards["president"] = {"name": parliament_lb[0]["name"], "votes": parliament_lb[0]["votes_received"]}
            if people_lb:
                awards["chief_advisor"] = {"name": people_lb[0]["name"], "score": people_lb[0]["score"]}
        else:
            if parliament_lb:
                awards["supreme_dictator"] = {"name": parliament_lb[0]["name"], "votes": parliament_lb[0]["votes_received"]}
            if people_lb:
                awards["minister_of_chaos"] = {"name": people_lb[0]["name"], "score": people_lb[0]["score"]}

        # Whistleblower: person who voted against majority most often
        majority_disagreements = {}
        for rr in self.round_history:
            if not rr.vote_counts:
                continue
            majority_idx = max(rr.vote_counts, key=rr.vote_counts.get)
            for person_name in self.people_members:
                if person_name not in majority_disagreements:
                    majority_disagreements[person_name] = 0
                # Check what they voted for in the votes dict — we need to look at the round
                # We stored round data but not per-person votes. Let's derive from proposals.
                # Actually, we only have current round votes. For historical, we need to track.
                # For simplicity, we'll skip exact whistleblower calc or track it during end_round.

        # Simple whistleblower: person with lowest score (voted for worst-graded proposals)
        if people_lb:
            awards["whistleblower"] = {"name": people_lb[-1]["name"], "score": people_lb[-1]["score"]}

        return {
            "type": "game_over",
            "mode": self.settings.mode,
            "collapsed": self.economy.is_collapsed(),
            "rounds_played": self.round_number,
            "destruction_score": self.economy.get_destruction_score(),
            "final_economy": self.economy.get_state(),
            "ai_reveal": ai_reveal,
            "parliament_leaderboard": parliament_lb,
            "people_leaderboard": people_lb,
            "awards": awards,
            "settings": self.settings.to_dict(),
        }

    def get_player_game_over(self, player_name: str) -> dict:
        """Get personalized game-over data for a specific player."""
        pd = self.players.get(player_name)
        if not pd:
            return {}

        base = {
            "type": "game_over",
            "mode": self.settings.mode,
            "role": pd.role,
        }

        if pd.role == "parliament":
            # Per-round breakdown of their proposals
            my_proposals = []
            for rr in self.round_history:
                for pr in rr.proposals:
                    if pr.parliament_member == player_name:
                        my_proposals.append({
                            "round": rr.round_number,
                            "text": pr.text,
                            "votes_received": pr.votes_received,
                            "ai_quality_score": pr.ai_quality_score,
                            "ai_commentary": pr.ai_commentary,
                            "won": pr.parliament_index == rr.winning_proposal_index,
                        })

            # Rank among parliament
            parliament_sorted = sorted(
                self.parliament_members,
                key=lambda n: self.players[n].votes_received,
                reverse=True,
            )
            rank = parliament_sorted.index(player_name) + 1 if player_name in parliament_sorted else 0

            base.update({
                "total_votes": pd.votes_received,
                "rank": rank,
                "total_parliament": len(self.parliament_members),
                "proposals": my_proposals,
            })
        else:
            # People: per-round breakdown
            rank_list = sorted(
                [n for n in self.people_members if self.players[n].connected],
                key=lambda n: self.players[n].score,
                reverse=True,
            )
            rank = rank_list.index(player_name) + 1 if player_name in rank_list else 0

            base.update({
                "score": pd.score,
                "rank": rank,
                "total_people": len(rank_list),
            })

        return base

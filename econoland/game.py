"""
game.py — Core game state and logic.

This is the central module that manages the entire game lifecycle:
1. Player management — joining, disconnecting, and reconnecting players
2. Role assignment — randomly selecting who becomes parliament vs "the people"
3. Round flow — writing proposals, voting, tiebreakers, and scoring
4. History tracking — recording every proposal, vote, and AI evaluation per round
5. Leaderboard and award calculation at game over

Architecture note:
    The Game class does NOT handle networking directly. Instead, server.py
    injects callback functions (on_broadcast_host, on_send_to_player, etc.)
    that the Game class calls when it needs to communicate with clients.
    This separation keeps game logic independent from WebSocket code.

Game flow:
    Lobby → Role Assignment → [Round: Writing → Voting → (Tiebreaker?) → Results] × N → Game Over
"""

# ---- Standard Library Imports ----
import asyncio                               # For async tasks (parallel AI calls)
import copy                                  # For deep-copying data structures
import logging                               # For debug/error logging
import random                                # For random role assignment and tiebreakers
from dataclasses import dataclass, field     # For structured data classes

# ---- Project Imports ----
import config                                # Global constants (player limits, etc.)
from config import GameSettings              # Game configuration dataclass
from economy import Economy                  # Economy simulation model

# Set up logger for this module — messages appear as "game: ..."
logger = logging.getLogger(__name__)


# ============================================================
# Data Classes — Structured records for tracking game data
# ============================================================

@dataclass
class ProposalRecord:
    """
    Stores one parliament member's proposal and its AI evaluation for a single round.

    Each round, every parliament member writes one proposal. The AI evaluates
    each proposal with a quality score, economic impacts, and a witty commentary.
    This record captures all of that for the round history and final results.

    Attributes:
        parliament_member: Name of the player who wrote this proposal
        parliament_index: 0-based index (e.g., 0 = first parliament member)
        text: The actual proposal text written by the player (max 200 chars)
        votes_received: How many people voted for this proposal this round
        ai_quality_score: AI's rating of the proposal (0-100)
        ai_impacts: Dictionary of economic impacts (gdp, employment, etc.)
        ai_destruction_points: Points awarded for how destructive/constructive it is
        ai_commentary: AI's witty one-liner about the proposal
    """
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
    """
    Complete record of one game round, stored in round_history for final results.

    After each round ends, all data is bundled into a RoundRecord and appended
    to the game's round_history list. This is used for:
    - Providing context to the LLM for generating future scenarios
    - Displaying the AI reveal at game over (hidden scores for every proposal)
    - Calculating leaderboards and awards

    Attributes:
        round_number: Which round this was (1-based)
        scenario: The economic crisis scenario for this round (headline + description)
        proposals: List of ProposalRecord objects (one per parliament member)
        winning_proposal_index: Index of the proposal that won the vote
        vote_counts: Dictionary mapping proposal index → number of votes received
        economy_before: Economy state snapshot before the winning policy was applied
        economy_after: Economy state snapshot after the winning policy was applied
    """
    round_number: int
    scenario: dict
    proposals: list                                      # list of ProposalRecord
    winning_proposal_index: int = -1
    vote_counts: dict = field(default_factory=dict)      # proposal_index -> vote count
    economy_before: dict = field(default_factory=dict)
    economy_after: dict = field(default_factory=dict)


@dataclass
class PlayerData:
    """
    Per-player state tracked throughout the game.

    Every player who joins gets a PlayerData instance. This tracks their
    role (parliament or people), their cumulative score, connection status
    (for handling disconnects/reconnects), and parliament-specific data.

    Attributes:
        role: "parliament" (writes proposals) or "people" (votes on proposals)
        score: Cumulative score — for people, this is sum of AI quality scores
               of proposals they voted for across all rounds
        connected: Whether the player is currently connected via WebSocket
        votes_received: Parliament only — total votes received across all rounds
        parliament_index: Parliament only — their 0-based index (for display order)
    """
    role: str = "people"              # "parliament" or "people"
    score: int = 0                    # Cumulative score across rounds
    connected: bool = True            # Is the player currently connected?
    votes_received: int = 0           # Parliament only: total votes across all rounds
    parliament_index: int = -1        # Parliament only: 0-based display index


# ============================================================
# Main Game Class
# ============================================================

class Game:
    """
    Central game state manager.

    This class handles the full game lifecycle:
        Lobby → Role Assignment → Rounds (Writing → Voting → Results) → Game Over

    It communicates with connected clients through callback functions that are
    injected by server.py after initialization. This design keeps the game logic
    completely independent from the WebSocket/networking code.

    Key responsibilities:
        - Track all players and their states (role, score, connection)
        - Manage the round-by-round flow (proposals, voting, tiebreakers)
        - Record complete history for LLM context and final results
        - Calculate leaderboards and awards at game over
    """

    def __init__(self):
        """
        Initialize a new game with default settings and empty state.

        All attributes are set to their starting values. The game begins
        in the "lobby" phase, waiting for players to join and the host
        to configure settings and click Start.
        """
        # ---- Configuration and Economy ----
        self.settings = GameSettings()   # Default game settings (can be updated by host)
        self.economy = Economy()         # Fresh economy with starting indicator values

        # ---- Player Tracking ----
        # Dictionary mapping player name → PlayerData object
        self.players: dict[str, PlayerData] = {}
        # Ordered lists of player names by role (set during role assignment)
        self.parliament_members: list[str] = []    # Players who write proposals
        self.people_members: list[str] = []        # Players who vote on proposals

        # ---- Game State Machine ----
        # These flags track the overall game state
        self.started = False             # Has the host clicked "Start Game"?
        self.game_over = False           # Has the game ended (normally or early)?
        self.round_number = 0            # Current round (0 = not started yet)
        # Current phase within a round — determines what actions are allowed
        # Valid phases: "lobby", "writing", "voting", "tiebreaker", "results", "gameover"
        self.current_phase: str = "lobby"

        # ---- Current Round Data (reset at the start of each round) ----
        self.current_scenario: dict | None = None          # The crisis scenario for this round
        self.proposals: dict[str, str] = {}                # parliament_name → their proposal text
        self.proposal_locked: dict[str, bool] = {}         # parliament_name → is their proposal locked?
        self.votes: dict[str, int] = {}                    # person_name → index of proposal they voted for
        self.tiebreaker_votes: dict[str, int] = {}         # person_name → index in tiebreaker revote
        self.ai_evaluations: list[dict] | None = None      # AI evaluation results for all proposals

        # ---- History (persists across rounds — used for final results and LLM context) ----
        self.round_history: list[RoundRecord] = []

        # ---- Async Background Tasks ----
        # These tasks run AI calls in parallel with human activity phases
        # (e.g., grading proposals while people are voting)
        self.next_scenario: dict | None = None             # Pre-generated next scenario
        self.grading_task: asyncio.Task | None = None      # Background task for AI proposal grading
        self.scenario_task: asyncio.Task | None = None     # Background task for next scenario generation

        # ---- WebSocket Broadcast Callbacks ----
        # These are set by server.py after Game() is created.
        # They allow the game logic to send messages to clients without
        # directly depending on the WebSocket/networking layer.
        self.on_broadcast_host = None          # Send message to host display(s)
        self.on_broadcast_parliament = None    # Send message to all parliament members
        self.on_broadcast_people = None        # Send message to all people (voters)
        self.on_broadcast_all = None           # Send message to everyone (host + all players)
        self.on_send_to_player = None          # Send message to a specific player by name

    # ============================================================
    # Player Management
    # ============================================================

    def add_player(self, name: str) -> bool:
        """
        Add a new player to the lobby.

        Called when a player connects via WebSocket before the game starts.
        Validates that: the game hasn't started, the name isn't taken,
        and the lobby isn't full.

        Args:
            name: The player's chosen display name

        Returns:
            bool: True if the player was added successfully, False otherwise
        """
        # Can't join if the game has already started
        if self.started:
            return False
        # Can't use a name that's already taken
        if name in self.players:
            return False
        # Can't exceed the maximum player limit
        if len(self.players) >= config.MAX_PLAYERS:
            return False
        # Create a new PlayerData with default values and add to the dict
        self.players[name] = PlayerData()
        return True

    def remove_player(self, name: str):
        """
        Mark a player as disconnected (soft delete).

        We don't actually remove the player from the dict — we just mark them
        as disconnected. This allows them to reconnect later and resume their
        role without losing their score or position.

        Args:
            name: The player's display name
        """
        if name in self.players:
            self.players[name].connected = False

    def reconnect_player(self, name: str) -> bool:
        """
        Reconnect a previously joined player who lost their connection.

        If the player exists in our records (even if disconnected), mark them
        as connected again. They'll get their role and current phase info
        sent to them by server.py.

        Args:
            name: The player's display name

        Returns:
            bool: True if the player was found and reconnected, False if unknown name
        """
        if name in self.players:
            self.players[name].connected = True
            return True
        return False

    def get_player_count(self) -> int:
        """
        Count the number of currently connected players.

        Only counts players with connected=True, not disconnected ones.

        Returns:
            int: Number of currently connected players
        """
        return sum(1 for p in self.players.values() if p.connected)

    def get_player_names(self) -> list[str]:
        """
        Get a list of names of all currently connected players.

        Used for the lobby display and for role assignment.

        Returns:
            list[str]: Names of all connected players
        """
        return [n for n, p in self.players.items() if p.connected]

    # ============================================================
    # Game Setup
    # ============================================================

    def update_settings(self, settings_dict: dict):
        """
        Update game settings from a dictionary sent by the host.

        Called when the host changes settings on the configuration screen.
        The from_dict() method handles validation and clamping.

        Args:
            settings_dict: Raw settings dictionary from the frontend
        """
        self.settings = GameSettings.from_dict(settings_dict)

    def assign_roles(self):
        """
        Randomly assign parliament members from the pool of connected players.

        How it works:
        1. Get all connected player names
        2. Shuffle them randomly
        3. Take the first N as parliament (N = settings.parliament_size)
        4. The rest become "the people" (voters)

        The parliament_size is capped to ensure at least 1 person remains
        as a voter (otherwise nobody can vote on proposals).
        """
        # Get all connected player names
        connected = self.get_player_names()
        # Shuffle randomly so role assignment is fair
        random.shuffle(connected)

        # Calculate parliament size — can't be more than (total - 1) so at least 1 voter remains
        parliament_size = min(self.settings.parliament_size, len(connected) - 1)
        parliament_size = max(parliament_size, 1)  # Need at least 1 parliament member

        # Split players into parliament and people
        self.parliament_members = connected[:parliament_size]
        self.people_members = connected[parliament_size:]

        # Assign roles and parliament indices to each player
        for i, name in enumerate(self.parliament_members):
            self.players[name].role = "parliament"
            self.players[name].parliament_index = i  # 0-based index for display ordering

        for name in self.people_members:
            self.players[name].role = "people"

    async def start_game(self):
        """
        Initialize and start the game.

        Called when the host clicks "Start Game". Sets the started flag,
        resets the round counter, and assigns roles to all connected players.
        """
        self.started = True
        self.round_number = 0
        self.assign_roles()

    # ============================================================
    # Round Management
    # ============================================================

    def start_new_round(self, scenario: dict):
        """
        Begin a new round with the given scenario.

        Resets all per-round data (proposals, votes, evaluations) and
        advances to the writing phase. Parliament members will now be
        able to type their proposals.

        Args:
            scenario: The economic crisis scenario from the LLM, containing
                      "headline", "description", and "news_ticker"
        """
        self.round_number += 1
        self.current_scenario = scenario
        self.current_phase = "writing"

        # Initialize empty proposals for each parliament member
        self.proposals = {name: "" for name in self.parliament_members}
        # All proposals start unlocked (parliament can type)
        self.proposal_locked = {name: False for name in self.parliament_members}
        # Clear votes from previous round
        self.votes = {}
        self.tiebreaker_votes = {}
        # Clear AI evaluations from previous round
        self.ai_evaluations = None

    def update_proposal(self, parliament_name: str, text: str) -> bool:
        """
        Update a parliament member's proposal text (called on every keystroke).

        As parliament members type on their phones, each keystroke is sent
        via WebSocket and this method updates the stored proposal text.
        The text is then broadcast to the host display for live viewing.

        Args:
            parliament_name: Name of the parliament member typing
            text: The current full text of their proposal

        Returns:
            bool: True if the update was accepted, False if rejected
        """
        # Only parliament members can update proposals
        if parliament_name not in self.parliament_members:
            return False
        # Can't update if the proposal is already locked (time ran out)
        if self.proposal_locked.get(parliament_name, False):
            return False
        # Can only update during the writing phase
        if self.current_phase != "writing":
            return False
        # Enforce the 200-character limit by truncating
        self.proposals[parliament_name] = text[:200]
        return True

    def lock_all_proposals(self):
        """
        Lock all proposals at the end of the writing phase.

        Called when the writing timer expires. After this, parliament members
        can no longer edit their proposals. The game advances to the voting phase.
        """
        # Mark every parliament member's proposal as locked
        for name in self.parliament_members:
            self.proposal_locked[name] = True
        # Advance to voting phase
        self.current_phase = "voting"

    def get_proposals_list(self) -> list[dict]:
        """
        Get an ordered list of all proposals for display and evaluation.

        Returns proposals in parliament_index order (0, 1, 2, ...) with
        display names that respect the anonymous setting. In anonymous mode,
        names are replaced with "Proposal 1", "Proposal 2", etc.

        Returns:
            list[dict]: List of proposal dictionaries with keys:
                        index, parliament_member, text, display_name
        """
        result = []
        for i, name in enumerate(self.parliament_members):
            text = self.proposals.get(name, "").strip()
            result.append({
                "index": i,
                "parliament_member": name,
                "text": text,
                # In anonymous mode, hide the real name
                "display_name": name if not self.settings.anonymous else f"Proposal {i + 1}",
            })
        return result

    def submit_vote(self, player_name: str, proposal_index: int) -> bool:
        """
        Record a person's vote for a specific proposal.

        Validates that: the voter is a "people" player (not parliament),
        they haven't already voted, it's the voting phase, and the
        proposal index is valid.

        Args:
            player_name: Name of the person voting
            proposal_index: 0-based index of the proposal they're voting for

        Returns:
            bool: True if the vote was accepted, False if rejected
        """
        # Only people can vote (parliament members can't vote on their own proposals)
        if player_name not in self.people_members:
            return False
        # Each person can only vote once per round
        if player_name in self.votes:
            return False
        # Can only vote during the voting phase
        if self.current_phase != "voting":
            return False
        # Validate the proposal index is within range
        if proposal_index < 0 or proposal_index >= len(self.parliament_members):
            return False
        # Record the vote
        self.votes[player_name] = proposal_index
        return True

    def submit_tiebreaker_vote(self, player_name: str, proposal_index: int) -> bool:
        """
        Record a person's vote during a tiebreaker round.

        Same validation as submit_vote but for the tiebreaker phase.
        Only the tied proposals are voteable (validated on the frontend side).

        Args:
            player_name: Name of the person voting
            proposal_index: 0-based index of the tied proposal they're voting for

        Returns:
            bool: True if the vote was accepted, False if rejected
        """
        # Only people can vote in tiebreakers
        if player_name not in self.people_members:
            return False
        # Each person votes once in the tiebreaker
        if player_name in self.tiebreaker_votes:
            return False
        # Must be in tiebreaker phase
        if self.current_phase != "tiebreaker":
            return False
        # Record the tiebreaker vote
        self.tiebreaker_votes[player_name] = proposal_index
        return True

    def all_people_voted(self) -> bool:
        """
        Check if all connected people have submitted their vote.

        Used to end the voting phase early if everyone has voted,
        rather than waiting for the full timer to expire.

        Returns:
            bool: True if every connected person has voted
        """
        # Only check connected people (disconnected players are skipped)
        active_people = [n for n in self.people_members if self.players[n].connected]
        return all(n in self.votes for n in active_people)

    def all_people_tiebreaker_voted(self) -> bool:
        """
        Check if all connected people have voted in the tiebreaker.

        Returns:
            bool: True if every connected person has voted in the tiebreaker
        """
        active_people = [n for n in self.people_members if self.players[n].connected]
        return all(n in self.tiebreaker_votes for n in active_people)

    def get_vote_counts(self) -> dict[int, int]:
        """
        Count how many votes each proposal received.

        Returns a dictionary mapping each proposal's index to its vote count.
        All proposals start at 0 votes, even if nobody voted for them.

        Returns:
            dict[int, int]: proposal_index → number of votes
        """
        # Initialize all proposals to 0 votes
        counts = {}
        for i in range(len(self.parliament_members)):
            counts[i] = 0
        # Count each vote
        for idx in self.votes.values():
            counts[idx] = counts.get(idx, 0) + 1
        return counts

    def get_tiebreaker_vote_counts(self) -> dict[int, int]:
        """
        Count votes per proposal in the tiebreaker round.

        Returns:
            dict[int, int]: proposal_index → number of tiebreaker votes
        """
        counts = {}
        for idx in self.tiebreaker_votes.values():
            counts[idx] = counts.get(idx, 0) + 1
        return counts

    def detect_tie(self) -> list[int] | None:
        """
        Check if there's a tie in the main vote.

        A tie occurs when 2 or more proposals have the same highest vote count.
        If there's a tie, a tiebreaker round is triggered.

        Returns:
            list[int] | None: List of tied proposal indices, or None if no tie
        """
        counts = self.get_vote_counts()
        if not counts:
            return None
        # Find the highest vote count
        max_votes = max(counts.values())
        if max_votes == 0:
            return None  # Nobody voted at all
        # Find all proposals with that highest count
        tied = [idx for idx, count in counts.items() if count == max_votes]
        # It's only a tie if more than one proposal has the max votes
        if len(tied) > 1:
            return tied
        return None

    def determine_winner(self) -> int:
        """
        Determine the winning proposal index after voting (and tiebreaker if needed).

        Decision logic:
        1. If one proposal has the most votes → it wins
        2. If there's a tie and a tiebreaker was held → use tiebreaker results
        3. If still tied after tiebreaker → random choice among tied proposals
        4. If nobody voted at all → random choice

        Returns:
            int: Index of the winning proposal (0-based)
        """
        counts = self.get_vote_counts()
        if not counts:
            return 0  # Fallback if no votes exist

        max_votes = max(counts.values())
        # If nobody voted, pick randomly
        if max_votes == 0:
            return random.randint(0, len(self.parliament_members) - 1)

        # Find all proposals with the highest vote count
        winners = [idx for idx, count in counts.items() if count == max_votes]
        # If there's a clear winner, return it
        if len(winners) == 1:
            return winners[0]

        # If a tiebreaker was held, use those results
        if self.tiebreaker_votes:
            tb_counts = self.get_tiebreaker_vote_counts()
            if tb_counts:
                max_tb = max(tb_counts.values())
                tb_winners = [idx for idx, count in tb_counts.items() if count == max_tb]
                if len(tb_winners) == 1:
                    return tb_winners[0]
                # Still tied after tiebreaker — break it randomly
                return random.choice(tb_winners)

        # No tiebreaker was held (shouldn't happen normally) — random tiebreak
        return random.choice(winners)

    def end_round(self, winning_index: int) -> RoundRecord:
        """
        Finalize a round after the winner is determined.

        This method does several things:
        1. Records the economy state BEFORE applying the winning policy
        2. Applies the winning proposal's economic impacts to the economy
        3. Updates parliament scores (total votes received across all rounds)
        4. Updates people scores (cumulative AI quality of proposals they voted for)
        5. Creates a complete RoundRecord and adds it to round_history
        6. Advances the phase to "results"

        The scoring system works as follows:
        - Parliament members are ranked by POPULARITY (total votes received)
        - People are ranked by JUDGMENT (sum of AI quality scores of proposals they chose)

        Args:
            winning_index: Index of the proposal that won the vote

        Returns:
            RoundRecord: Complete record of this round (stored in round_history)
        """
        # Count votes for each proposal
        vote_counts = self.get_vote_counts()
        # Snapshot the economy BEFORE applying the winning policy
        economy_before = self.economy.get_state()

        # Find the winning proposal's AI evaluation to get its economic impacts
        winning_eval = None
        if self.ai_evaluations:
            for ev in self.ai_evaluations:
                if ev.get("proposal_index") == winning_index:
                    winning_eval = ev
                    break

        # Apply the winning policy's economic impacts to the economy
        if winning_eval and winning_eval.get("impacts"):
            self.economy.apply_policy(winning_eval["impacts"])
            # Add the destruction/prosperity points to the cumulative score
            self.economy.add_score_points(winning_eval.get("destruction_points", 0))

        # Snapshot the economy AFTER applying the winning policy
        economy_after = self.economy.get_state()

        # Build detailed proposal records for every parliament member
        proposal_records = []
        for i, name in enumerate(self.parliament_members):
            text = self.proposals.get(name, "")
            votes_for = vote_counts.get(i, 0)

            # Find this proposal's AI evaluation
            ai_score = 50          # Default quality score
            ai_impacts = {}        # Default empty impacts
            ai_dp = 0             # Default destruction points
            ai_comment = ""       # Default empty commentary
            if self.ai_evaluations:
                for ev in self.ai_evaluations:
                    if ev.get("proposal_index") == i:
                        ai_score = ev.get("quality_score", 50)
                        ai_impacts = ev.get("impacts", {})
                        ai_dp = ev.get("destruction_points", 0)
                        ai_comment = ev.get("ai_commentary", "")
                        break

            # Create the proposal record with all data
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

            # Update parliament member's cumulative vote count (for leaderboard)
            self.players[name].votes_received += votes_for

        # Update people's scores based on the AI quality of the proposal they voted for.
        # This rewards people who consistently vote for "good" proposals (constructive mode)
        # or "effective" proposals (destructive mode).
        for person_name, voted_idx in self.votes.items():
            ai_score = 50  # Default if no AI evaluation exists
            if self.ai_evaluations:
                for ev in self.ai_evaluations:
                    if ev.get("proposal_index") == voted_idx:
                        ai_score = ev.get("quality_score", 50)
                        break
            # Add the AI quality score to the person's cumulative score
            self.players[person_name].score += ai_score

        # Create and store the complete round record
        round_record = RoundRecord(
            round_number=self.round_number,
            # Deep copy the scenario so changes won't affect the record
            scenario=copy.deepcopy(self.current_scenario) if self.current_scenario else {},
            proposals=proposal_records,
            winning_proposal_index=winning_index,
            vote_counts=vote_counts,
            economy_before=economy_before,
            economy_after=economy_after,
        )
        self.round_history.append(round_record)

        # Advance phase to results display
        self.current_phase = "results"
        return round_record

    # ============================================================
    # Game State Checks
    # ============================================================

    def is_game_over(self) -> bool:
        """
        Check if the game should end.

        The game ends in two ways:
        1. The host manually terminates the game (game_over flag set directly)
        2. In destructive mode: the economy collapses (GDP or employment hits 0)
           — this is an early "win" for the players

        Returns:
            bool: True if the game should end
        """
        # Check if manually terminated by host
        if self.game_over:
            return True
        # In destructive mode, economy collapse = early win
        if self.settings.mode == "destructive" and self.economy.is_collapsed():
            return True
        return False

    def is_last_round(self) -> bool:
        """
        Check if the current round is the last one based on settings.

        Returns:
            bool: True if current round number >= configured num_rounds
        """
        return self.round_number >= self.settings.num_rounds

    # ============================================================
    # Data for Clients (methods that build data to send via WebSocket)
    # ============================================================

    def get_lobby_state(self) -> dict:
        """
        Build the lobby state dictionary for the host display.

        Sent to the host whenever a player joins or leaves the lobby,
        so the projector can show the updated player list.

        Returns:
            dict: Lobby state with player names, count, and minimum needed
        """
        return {
            "type": "lobby_update",
            "players": self.get_player_names(),
            "player_count": self.get_player_count(),
            "min_players": config.MIN_PLAYERS,
        }

    def get_round_history_for_llm(self) -> list[dict]:
        """
        Build a compact history of all past rounds for LLM context.

        The LLM needs to know what happened in previous rounds to generate
        relevant new scenarios and avoid repeating topics. This method
        creates a condensed version of the full round history.

        Returns:
            list[dict]: Compact round summaries with scenario, proposals, and economy data
        """
        history = []
        for rr in self.round_history:
            # Summarize each proposal (text, votes, whether it won)
            proposals_summary = []
            for pr in rr.proposals:
                proposals_summary.append({
                    "text": pr.text,
                    "votes": pr.votes_received,
                    "won": pr.parliament_index == rr.winning_proposal_index,
                })
            # Build the compact round summary
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
        """
        Compile all final game data for the game over screen.

        This is the big payoff moment — the "AI reveal" where hidden scores
        and commentary for every proposal from every round are shown.

        The results include:
        - AI reveal: every proposal with its hidden AI quality score and commentary
        - Parliament leaderboard: ranked by total votes received (popularity)
        - People leaderboard: ranked by cumulative AI quality scores (judgment)
        - Awards: fun titles for top performers

        Returns:
            dict: Complete game over data for the host display
        """
        # ---- Parliament Leaderboard (ranked by popularity = total votes received) ----
        parliament_lb = sorted(
            [
                {"name": name, "votes_received": self.players[name].votes_received}
                for name in self.parliament_members
            ],
            key=lambda x: x["votes_received"],
            reverse=True,  # Most votes first
        )

        # ---- People Leaderboard (ranked by judgment = cumulative AI quality score) ----
        people_lb = sorted(
            [
                {"name": name, "score": self.players[name].score}
                for name in self.people_members
                if self.players[name].connected  # Only include connected players
            ],
            key=lambda x: x["score"],
            reverse=True,  # Highest score first
        )

        # ---- AI Reveal: detailed breakdown of every proposal from every round ----
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
                    # Respect anonymous setting when displaying names
                    "display_name": pr.parliament_member if not self.settings.anonymous else f"Proposal {pr.parliament_index + 1}",
                    "text": pr.text,
                    "votes_received": pr.votes_received,
                    "ai_quality_score": pr.ai_quality_score,    # The hidden AI score — revealed now!
                    "ai_commentary": pr.ai_commentary,           # The witty AI comment — revealed now!
                    "won": pr.parliament_index == rr.winning_proposal_index,
                })
            ai_reveal.append(round_data)

        # ---- Awards: fun titles for top players ----
        awards = {}
        if self.settings.mode == "constructive":
            # Constructive mode awards — positive titles
            if parliament_lb:
                awards["president"] = {"name": parliament_lb[0]["name"], "votes": parliament_lb[0]["votes_received"]}
            if people_lb:
                awards["chief_advisor"] = {"name": people_lb[0]["name"], "score": people_lb[0]["score"]}
        else:
            # Destructive mode awards — chaos-themed titles
            if parliament_lb:
                awards["supreme_dictator"] = {"name": parliament_lb[0]["name"], "votes": parliament_lb[0]["votes_received"]}
            if people_lb:
                awards["minister_of_chaos"] = {"name": people_lb[0]["name"], "score": people_lb[0]["score"]}

        # Whistleblower award: the person with the LOWEST score
        # (they consistently voted for the worst-graded proposals)
        majority_disagreements = {}
        for rr in self.round_history:
            if not rr.vote_counts:
                continue
            majority_idx = max(rr.vote_counts, key=rr.vote_counts.get)
            for person_name in self.people_members:
                if person_name not in majority_disagreements:
                    majority_disagreements[person_name] = 0

        # Simple whistleblower: person with the lowest cumulative score
        if people_lb:
            awards["whistleblower"] = {"name": people_lb[-1]["name"], "score": people_lb[-1]["score"]}

        # ---- Build and return the complete results dictionary ----
        return {
            "type": "game_over",
            "mode": self.settings.mode,
            "collapsed": self.economy.is_collapsed(),
            "rounds_played": self.round_number,
            "score": self.economy.get_score(),
            "final_economy": self.economy.get_state(),
            "ai_reveal": ai_reveal,
            "parliament_leaderboard": parliament_lb,
            "people_leaderboard": people_lb,
            "awards": awards,
            "settings": self.settings.to_dict(),
        }

    def get_player_game_over(self, player_name: str) -> dict:
        """
        Get personalized game-over data for a specific player's phone screen.

        Parliament members see their per-round proposal breakdown with AI scores.
        People see their cumulative score and rank among other voters.

        Args:
            player_name: The player's name

        Returns:
            dict: Personalized game over data for this player's phone display
        """
        pd = self.players.get(player_name)
        if not pd:
            return {}

        # Base data sent to all players regardless of role
        base = {
            "type": "game_over",
            "mode": self.settings.mode,
            "role": pd.role,
        }

        if pd.role == "parliament":
            # Parliament members see a breakdown of all their proposals
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

            # Calculate this parliament member's rank (by total votes received)
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
            # People see their score and rank among other voters
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

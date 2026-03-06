"""
config.py — Application configuration and game settings.

This module is responsible for:
1. Loading environment variables from a .env file (API keys, URLs, model names)
2. Defining global constants used across the entire application (server host/port,
   player limits, starting economy values)
3. Defining the GameSettings dataclass — a structured container for all game
   parameters that the host can configure before starting the game

The .env file is loaded automatically when this module is imported, so any
module that imports config will have access to the environment variables.
"""

# ---- Standard Library Imports ----
import os                                    # For reading environment variables
from dataclasses import dataclass, field     # For creating structured data classes
from dotenv import load_dotenv               # For loading .env file into environment

# Load environment variables from .env file in the current directory.
# This makes variables like OPENROUTER_API_KEY available via os.getenv().
load_dotenv()

# ============================================================
# Server Settings
# ============================================================
# "0.0.0.0" means the server listens on all network interfaces,
# which is required for ngrok tunneling to work properly.
HOST = "0.0.0.0"
PORT = 8000

# ============================================================
# Player Limits
# ============================================================
# Minimum players needed to start a game (need at least 1 parliament + 1 voter)
MIN_PLAYERS = 2
# Maximum players allowed to prevent server overload
MAX_PLAYERS = 50

# ============================================================
# External API Configuration
# ============================================================
# OpenRouter is an API gateway that provides access to various LLM models
# (like Grok, GPT, etc.) through a single unified API endpoint.
# We use it to generate scenarios, evaluate proposals, and create narratives.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# The specific LLM model to use via OpenRouter.
# Default is Google's Gemini Flash Lite — fast and cost-effective.
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3.1-flash-lite-preview")

# ngrok creates a public URL that tunnels to our local server.
# This URL is used to generate QR codes so students can join on their phones.
NGROK_URL = os.getenv("NGROK_URL", "http://localhost:8000")

# ============================================================
# Economy Starting Values
# ============================================================
# All indicators use a 0-100 scale where:
# - For GDP, Employment, Public Trust, Trade Balance: higher = better
# - For Inflation, National Debt: lower = better
# These values represent a "decent but not perfect" starting economy.
STARTING_GDP = 75               # Gross Domestic Product (economic output)
STARTING_EMPLOYMENT = 80        # Employment rate (jobs available)
STARTING_INFLATION = 20         # Price increases — lower is better
STARTING_PUBLIC_TRUST = 70      # Citizens' trust in the government
STARTING_TRADE_BALANCE = 60     # Exports vs imports balance
STARTING_NATIONAL_DEBT = 30     # Government debt — lower is better


@dataclass
class GameSettings:
    """
    Configurable game parameters set by the host before the game starts.

    The host adjusts these settings on the settings screen (host.html) before
    clicking "Start Game". The from_dict() method validates and clamps all values
    to prevent invalid inputs from the frontend.

    Attributes:
        mode: Game mode — "constructive" (save the economy) or "destructive" (collapse it)
        num_rounds: How many rounds to play (typically 3, 5, or 7)
        parliament_size: How many players become parliament members (rest are voters)
        anonymous: Whether parliament member names are hidden during the game
        proposal_time: Seconds parliament has to write proposals each round
        voting_time: Seconds the people have to vote on proposals
        tiebreaker_time: Seconds for a tiebreaker vote if proposals are tied
    """
    mode: str = "destructive"          # "constructive" or "destructive"
    num_rounds: int = 5                # Number of rounds (3/5/7 are typical)
    parliament_size: int = 4           # Number of parliament members (3/4/5 typical)
    anonymous: bool = True             # Hide parliament names? (default varies by mode)
    proposal_time: int = 120           # Writing phase duration in seconds (60/90/120)
    voting_time: int = 45              # Voting phase duration in seconds (30/45/60)
    tiebreaker_time: int = 10          # Tiebreaker vote duration in seconds (fixed)

    def to_dict(self) -> dict:
        """
        Convert settings to a plain dictionary for JSON transmission.

        This is used when sending settings to the frontend via WebSocket,
        so JavaScript can read the values as a regular JSON object.

        Returns:
            dict: All settings as key-value pairs
        """
        return {
            "mode": self.mode,
            "num_rounds": self.num_rounds,
            "parliament_size": self.parliament_size,
            "anonymous": self.anonymous,
            "proposal_time": self.proposal_time,
            "voting_time": self.voting_time,
            "tiebreaker_time": self.tiebreaker_time,
        }

    @staticmethod
    def from_dict(d: dict) -> "GameSettings":
        """
        Create a GameSettings instance from a dictionary, with input validation.

        This is called when the host sends updated settings from the frontend.
        Each value is clamped to a valid range to prevent abuse or bugs:
        - mode must be exactly "constructive" or "destructive"
        - num_rounds is clamped to 1-20
        - parliament_size is clamped to 2-15
        - timers are clamped to reasonable ranges

        Args:
            d: Dictionary of settings from the frontend (may contain invalid values)

        Returns:
            GameSettings: A validated GameSettings instance with safe values
        """
        # Validate mode — only accept the two valid options, default to destructive
        mode = d.get("mode", "destructive")
        if mode not in ("constructive", "destructive"):
            mode = "destructive"

        return GameSettings(
            mode=mode,
            # Clamp num_rounds between 1 and 20 (prevent 0-round or 100-round games)
            num_rounds=max(1, min(20, int(d.get("num_rounds", 5)))),
            # Clamp parliament_size between 2 and 15 (need at least 2 for competition)
            parliament_size=max(2, min(15, int(d.get("parliament_size", 4)))),
            # Anonymous is a boolean, defaults to True
            anonymous=d.get("anonymous", True),
            # Clamp proposal_time between 30 and 300 seconds
            proposal_time=max(30, min(300, int(d.get("proposal_time", 120)))),
            # Clamp voting_time between 15 and 120 seconds
            voting_time=max(15, min(120, int(d.get("voting_time", 45)))),
            # Tiebreaker time is typically fixed at 10 seconds
            tiebreaker_time=int(d.get("tiebreaker_time", 10)),
        )

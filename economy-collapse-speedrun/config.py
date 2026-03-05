import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

# Server
HOST = "0.0.0.0"
PORT = 8000

# Min players to start
MIN_PLAYERS = 2
MAX_PLAYERS = 50

# OpenRouter / Grok
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3.1-flash-lite-preview")
NGROK_URL = os.getenv("NGROK_URL", "http://localhost:8000")

# Economy starting values
STARTING_GDP = 75
STARTING_EMPLOYMENT = 80
STARTING_INFLATION = 20
STARTING_PUBLIC_TRUST = 70
STARTING_TRADE_BALANCE = 60
STARTING_NATIONAL_DEBT = 30


@dataclass
class GameSettings:
    mode: str = "destructive"  # "constructive" | "destructive"
    duration_seconds: int = 300  # 3/5/7/10 min → 180/300/420/600
    parliament_size: int = 4  # 3/4/5
    anonymous: bool = True  # default depends on mode; set by frontend
    proposal_time: int = 120  # 60/90/120 seconds
    voting_time: int = 45  # 30/45/60 seconds
    tiebreaker_time: int = 10  # fixed

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "duration_seconds": self.duration_seconds,
            "parliament_size": self.parliament_size,
            "anonymous": self.anonymous,
            "proposal_time": self.proposal_time,
            "voting_time": self.voting_time,
            "tiebreaker_time": self.tiebreaker_time,
        }

    @staticmethod
    def from_dict(d: dict) -> "GameSettings":
        return GameSettings(
            mode=d.get("mode", "destructive"),
            duration_seconds=int(d.get("duration_seconds", 300)),
            parliament_size=int(d.get("parliament_size", 4)),
            anonymous=d.get("anonymous", True),
            proposal_time=int(d.get("proposal_time", 120)),
            voting_time=int(d.get("voting_time", 45)),
            tiebreaker_time=int(d.get("tiebreaker_time", 10)),
        )

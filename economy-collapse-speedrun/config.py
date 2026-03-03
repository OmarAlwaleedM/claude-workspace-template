import os
from dotenv import load_dotenv

load_dotenv()

# Server
HOST = "0.0.0.0"
PORT = 8000

# Game settings
ROUND_TIME_SECONDS = 20
GAME_DURATION_SECONDS = 300  # 5 min default, configurable at start
MIN_PLAYERS = 2

# OpenRouter / Grok
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "x-ai/grok-3-mini-beta")
NGROK_URL = os.getenv("NGROK_URL", "http://localhost:8000")

# Economy starting values
STARTING_GDP = 75
STARTING_EMPLOYMENT = 80
STARTING_INFLATION = 20
STARTING_PUBLIC_TRUST = 70
STARTING_TRADE_BALANCE = 60
STARTING_NATIONAL_DEBT = 30

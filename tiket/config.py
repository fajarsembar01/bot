"""Configuration for Tiket.com auto-buy bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

try:
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)
except Exception:
    pass

TIKET_URL = os.getenv("TIKET_URL", "")
TIKET_PACKAGE = os.getenv("TIKET_PACKAGE", "")
TIKET_QUANTITY = int(os.getenv("TIKET_QUANTITY", "1"))
TIKET_HEADLESS = os.getenv("TIKET_HEADLESS", "False").lower() == "true"
TIKET_REFRESH_SECONDS = float(os.getenv("TIKET_REFRESH_SECONDS", "3"))
TIKET_MAX_ATTEMPTS = int(os.getenv("TIKET_MAX_ATTEMPTS", "500"))

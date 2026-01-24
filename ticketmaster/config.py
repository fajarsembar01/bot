"""Configuration for Ticketmaster helper bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

try:
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)
except Exception:
    pass

TICKETMASTER_URL = os.getenv("TICKETMASTER_URL", "")
TICKETMASTER_BUTTON_TEXT = os.getenv("TICKETMASTER_BUTTON_TEXT", "")
TICKETMASTER_AUTO_BUY = os.getenv("TICKETMASTER_AUTO_BUY", "False").lower() == "true"
TICKETMASTER_QUANTITY = int(os.getenv("TICKETMASTER_QUANTITY", "1"))
TICKETMASTER_HEADLESS = os.getenv("TICKETMASTER_HEADLESS", "False").lower() == "true"
TICKETMASTER_REFRESH_SECONDS = float(os.getenv("TICKETMASTER_REFRESH_SECONDS", "3"))
TICKETMASTER_MAX_ATTEMPTS = int(os.getenv("TICKETMASTER_MAX_ATTEMPTS", "500"))
TICKETMASTER_OPEN_NEW_TAB = os.getenv("TICKETMASTER_OPEN_NEW_TAB", "True").lower() == "true"
TICKETMASTER_NEW_SESSION = os.getenv("TICKETMASTER_NEW_SESSION", "True").lower() == "true"
TICKETMASTER_USER_DATA_DIR = os.getenv("TICKETMASTER_USER_DATA_DIR", "")

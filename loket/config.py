"""
Konfigurasi untuk bot antrian Loket.com
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file jika ada (relative ke folder loket)
try:
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)
except Exception:
    pass  # File .env tidak wajib

# URL konser (bisa URL landing page atau langsung URL widget loket)
# Contoh widget loket: https://widget.loket.com/widget/yqar4pcjnnmn6q9mxobc
CONCERT_URL = os.getenv("CONCERT_URL", "https://ateezinjakarta.com/")
WIDGET_URL = os.getenv("WIDGET_URL", "")  # Opsional: URL widget loket langsung

# Settings browser
HEADLESS = os.getenv("HEADLESS", "False").lower() == "true"
WAIT_TIME = int(os.getenv("WAIT_TIME", "5"))  # detik untuk menunggu sebelum refresh

# Waktu untuk mulai monitoring (format: HH:MM)
START_MONITORING_TIME = os.getenv("START_MONITORING_TIME", "09:00")

# User agent (opsional, untuk menghindari deteksi)
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Loket.com selectors (akan diupdate berdasarkan struktur website)
SELECTORS = {
    "waiting_room_button": "button, a[href*='antrean'], .btn-queue, .waiting-room",
    "queue_status": ".queue-status, .antrean-status, [class*='queue'], [class*='antrean']",
    "login_button": "button.login, a.login, [href*='login']",
}

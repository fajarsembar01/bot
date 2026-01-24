import json
import os
import random
import shutil
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Optional

from flask import Flask, redirect, render_template_string, request, url_for

try:
    from .simple_bot import TicketmasterSimpleBot
except ImportError:
    try:
        from ticketmaster.simple_bot import TicketmasterSimpleBot
    except ImportError:
        from simple_bot import TicketmasterSimpleBot

app = Flask(__name__)

LOG_DIR = Path(__file__).parent / "logs"
DEFAULT_WINDOW_SIZE = "1200,800"


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def normalize_debugger_address(raw_value: str) -> str:
    raw_value = (raw_value or "").strip()
    if not raw_value:
        return ""
    if ":" in raw_value:
        return raw_value
    return f"127.0.0.1:{raw_value}"


def find_chrome_path() -> str:
    candidates = []
    env_path = os.environ.get("CHROME_PATH")
    if env_path:
        candidates.append(env_path)

    if is_macos():
        candidates.extend([
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ])
    elif is_linux():
        candidates.extend([
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ])
    elif is_windows():
        for key in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(key, "")
            if base:
                candidates.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))
    else:
        for key in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(key, "")
            if base:
                candidates.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))

    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "chrome.exe"):
        path_from_which = shutil.which(name)
        if path_from_which:
            candidates.append(path_from_which)

    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return ""


def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def find_free_port(start_port: int = 9222, max_tries: int = 50, exclude_ports=None) -> Optional[int]:
    exclude_ports = exclude_ports or set()
    port = start_port
    for _ in range(max_tries):
        if port not in exclude_ports and is_port_available(port):
            return port
        port += 1
    return None


def wait_for_port(port: int, timeout_seconds: float = 6.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            try:
                sock.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.2)
    return False


def generate_random_user_agent() -> str:
    """Generate random user agent untuk anti-fingerprinting"""
    chrome_versions = ["120.0.0.0", "121.0.0.0", "122.0.0.0", "123.0.0.0", "124.0.0.0"]
    os_versions = [
        ("Windows NT 10.0; Win64; x64", "Windows"),
        ("Macintosh; Intel Mac OS X 10_15_7", "Macintosh"),
        ("X11; Linux x86_64", "Linux"),
    ]
    os_string, platform = random.choice(os_versions)
    chrome_version = random.choice(chrome_versions)
    webkit_version = "537.36"
    
    if platform == "Windows":
        return f"Mozilla/5.0 ({os_string}) AppleWebKit/{webkit_version} (KHTML, like Gecko) Chrome/{chrome_version} Safari/{webkit_version}"
    elif platform == "Macintosh":
        return f"Mozilla/5.0 ({os_string}) AppleWebKit/{webkit_version} (KHTML, like Gecko) Chrome/{chrome_version} Safari/{webkit_version}"
    else:
        return f"Mozilla/5.0 ({os_string}) AppleWebKit/{webkit_version} (KHTML, like Gecko) Chrome/{chrome_version} Safari/{webkit_version}"


def generate_random_resolution() -> tuple[int, int]:
    """Generate random screen resolution"""
    resolutions = [
        (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
        (1280, 720), (1600, 900), (1024, 768), (1280, 1024),
        (1680, 1050), (1920, 1200), (2560, 1440)
    ]
    return random.choice(resolutions)


def generate_random_timezone() -> str:
    """Generate random timezone offset"""
    # Random timezone offset between -12 to +14
    offset = random.randint(-12, 14)
    return f"{offset:+03d}00"


def generate_random_language() -> str:
    """Generate random language"""
    languages = [
        "en-US", "en-GB", "es-ES", "fr-FR", "de-DE", "it-IT",
        "pt-BR", "ja-JP", "ko-KR", "zh-CN", "ru-RU", "ar-SA"
    ]
    return random.choice(languages)


def launch_chrome(port: Optional[int], profile_dir: Path, start_url: str, use_anti_detection: bool = True):
    chrome_path = find_chrome_path()
    if not chrome_path:
        return None, "Chrome tidak ditemukan. Install Chrome atau set CHROME_PATH."

    if not start_url:
        start_url = "about:blank"
    profile_dir.mkdir(parents=True, exist_ok=True)
    args = []
    if port:
        args.append(f"--remote-debugging-port={port}")
    
    # Base arguments
    args.extend([
        f"--user-data-dir={str(profile_dir)}",
        "--no-first-run",
        "--no-default-browser-check",
        "--new-window",
    ])
    
    # Anti-detection flags
    if use_anti_detection:
        # Random window size
        width, height = generate_random_resolution()
        args.append(f"--window-size={width},{height}")
        
        # Anti-fingerprinting flags
        args.extend([
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--disable-notifications",
            "--disable-popup-blocking",
            "--disable-translate",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
            "--disable-hang-monitor",
            "--disable-client-side-phishing-detection",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-domain-reliability",
            "--disable-sync",
            "--metrics-recording-only",
            "--no-first-run",
            "--safebrowsing-disable-auto-update",
            "--password-store=basic",
            "--use-mock-keychain",
            "--disable-extensions-except",
            "--disable-plugins-discovery",
            "--disable-preconnect",
            "--disable-print-preview",
        ])
        
        # Random user agent, timezone, dan language
        user_agent = generate_random_user_agent()
        language = generate_random_language()
        
        # Set user agent via command line
        args.append(f"--user-agent={user_agent}")
        
        # Set language via command line
        args.append(f"--lang={language}")
        
        # Create preferences file untuk set timezone dan language
        prefs_file = profile_dir / "Default" / "Preferences"
        prefs_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Set preferences untuk fingerprint randomization
        prefs = {}
        if prefs_file.exists():
            try:
                with prefs_file.open("r", encoding="utf-8") as f:
                    prefs = json.load(f)
            except:
                pass
        
        # Update preferences dengan language
        if "intl" not in prefs:
            prefs["intl"] = {}
        prefs["intl"]["accept_languages"] = language
        
        # Disable features yang bisa digunakan untuk fingerprinting
        if "profile" not in prefs:
            prefs["profile"] = {}
        if "default_content_setting_values" not in prefs["profile"]:
            prefs["profile"]["default_content_setting_values"] = {}
        prefs["profile"]["default_content_setting_values"]["notifications"] = 2
        prefs["profile"]["default_content_setting_values"]["geolocation"] = 2
        
        with prefs_file.open("w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)
    else:
        args.append(f"--window-size={DEFAULT_WINDOW_SIZE}")
    
    args.append(start_url)
    
    if is_macos() and ".app/Contents/MacOS/" in chrome_path:
        app_path = chrome_path.split(".app/Contents/MacOS/")[0] + ".app"
        cmd = ["open", "-g", "-n", "-a", app_path, "--args", *args]
    else:
        cmd = [chrome_path, *args]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proc, ""
    except Exception as exc:
        return None, str(exc)


class ThreadOutputRouter:
    def __init__(self, default_stream):
        self._default_stream = default_stream
        self._lock = Lock()
        self._streams = {}

    def register(self, thread_id, stream):
        with self._lock:
            self._streams[thread_id] = stream

    def unregister(self, thread_id):
        with self._lock:
            self._streams.pop(thread_id, None)

    def write(self, data):
        stream = self._streams.get(threading.get_ident(), self._default_stream)
        stream.write(data)
        try:
            stream.flush()
        except Exception:
            pass

    def flush(self):
        try:
            self._default_stream.flush()
        except Exception:
            pass

    def isatty(self):
        try:
            return self._default_stream.isatty()
        except Exception:
            return False


STDOUT_ROUTER = ThreadOutputRouter(sys.stdout)
STDERR_ROUTER = ThreadOutputRouter(sys.stderr)
sys.stdout = STDOUT_ROUTER
sys.stderr = STDERR_ROUTER


@dataclass
class BotTask:
    task_id: str
    status: str
    url: str
    button_text: str
    refresh_seconds: float
    max_attempts: int
    headless: bool
    auto_buy: bool
    quantity: int
    debugger_address: str
    open_new_tab: bool
    new_session: bool
    auto_launch: bool
    user_data_dir: str
    stop_event: Event
    close_on_exit: bool = False
    aggressive_order: bool = False
    aggressive_click: bool = False
    skip_refresh: bool = False
    auto_detect_widget: bool = False
    thread: Optional[Thread] = None
    bot: Optional[TicketmasterSimpleBot] = None
    log_path: str = ""
    error: str = ""
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None


TASKS = {}
TASKS_LOCK = Lock()


def is_active(status: str) -> bool:
    return status in {"starting", "running", "stopping"}


def read_log_tail(path: Path, max_bytes: int = 40000) -> str:
    if not path.exists():
        return ""
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > max_bytes:
            handle.seek(size - max_bytes)
        data = handle.read()
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return data.decode(errors="replace")


def run_bot_task(task: BotTask) -> None:
    log_handle = None
    try:
        if task.log_path:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            log_handle = open(task.log_path, "a", encoding="utf-8")
            STDOUT_ROUTER.register(threading.get_ident(), log_handle)
            STDERR_ROUTER.register(threading.get_ident(), log_handle)
            print(f"=== Ticketmaster Bot {task.task_id} started {datetime.now().isoformat(timespec='seconds')} ===")

        task.status = "running"
        task.bot.run()
        if task.stop_event.is_set():
            task.status = "stopped"
        elif not task.bot.setup_success:
            task.status = "error"
            task.error = task.bot.last_error or "Gagal setup driver."
        else:
            task.status = "finished"
    except Exception as exc:
        task.status = "error"
        task.error = str(exc)
    finally:
        task.stopped_at = datetime.now()
        if log_handle:
            print(f"=== Ticketmaster Bot {task.task_id} selesai ({task.status}) {task.stopped_at.isoformat(timespec='seconds')} ===")
            log_handle.flush()
            STDOUT_ROUTER.unregister(threading.get_ident())
            STDERR_ROUTER.unregister(threading.get_ident())
            log_handle.close()


PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Ticketmaster Panel</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=Space+Grotesk:wght@400;500;600&display=swap');

    :root {
      --bg: #f3f0e9;
      --card: #ffffff;
      --ink: #1b2530;
      --muted: #6b7280;
      --accent: #0f766e;
      --accent-2: #f97316;
      --border: #e5e7eb;
      --shadow: rgba(15, 23, 42, 0.1);
      --danger: #b91c1c;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: 'Space Grotesk', sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 15% 20%, #fef7e8 0%, transparent 45%),
        radial-gradient(circle at 80% 10%, #eef2ff 0%, transparent 42%),
        linear-gradient(135deg, #f7f2ea 0%, #f0ede6 100%);
      min-height: 100vh;
    }

    .shell {
      max-width: 1200px;
      margin: 0 auto;
      padding: 28px 24px 48px;
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 20px;
      flex-wrap: wrap;
    }

    header form {
      margin: 0;
    }

    header .btn-primary {
      white-space: nowrap;
    }

    h1 {
      font-family: 'Fraunces', serif;
      margin: 0;
      font-size: clamp(26px, 4vw, 38px);
    }

    .subtitle {
      color: var(--muted);
      margin-top: 6px;
    }

    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 20px;
      box-shadow: 0 16px 36px var(--shadow);
      margin-bottom: 20px;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
    }

    label {
      display: block;
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }

    input[type="text"],
    input[type="number"] {
      width: 100%;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid var(--border);
      font-size: 14px;
      font-family: inherit;
    }

    .row {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      margin-top: 12px;
    }

    .checkbox {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
    }

    button {
      border: none;
      border-radius: 999px;
      padding: 10px 18px;
      font-weight: 600;
      cursor: pointer;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
      font-family: inherit;
    }

    .btn-primary {
      background: var(--accent);
      color: #fff;
      box-shadow: 0 12px 24px rgba(15, 118, 110, 0.25);
    }

    .btn-secondary {
      background: #e5e7eb;
      color: #1f2937;
    }

    button:hover {
      transform: translateY(-1px);
      box-shadow: 0 14px 26px rgba(15, 23, 42, 0.15);
    }

    table {
      width: 100%;
      border-collapse: collapse;
    }

    th, td {
      text-align: left;
      padding: 10px;
      border-bottom: 1px solid var(--border);
      font-size: 13px;
      vertical-align: top;
    }

    th {
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 11px;
    }

    .status {
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 999px;
      display: inline-block;
    }

    .status.running { background: #d1fae5; color: #065f46; }
    .status.finished { background: #e0e7ff; color: #3730a3; }
    .status.error { background: #fee2e2; color: #991b1b; }
    .status.stopped { background: #f3f4f6; color: #374151; }
    .status.starting { background: #fef3c7; color: #92400e; }
    .status.stopping { background: #fde68a; color: #92400e; }

    .mono { font-family: "SFMono-Regular", Menlo, monospace; }
    .muted { color: var(--muted); }

    .actions form { display: inline-block; margin-right: 6px; }

    .banner {
      background: #fee2e2;
      border: 1px solid #fecaca;
      color: #991b1b;
      padding: 10px 12px;
      border-radius: 12px;
      margin-bottom: 12px;
    }

    .success {
      background: #d1fae5;
      border: 1px solid #86efac;
      color: #065f46;
      padding: 10px 12px;
      border-radius: 12px;
      margin-bottom: 12px;
    }

    .hidden {
      display: none;
    }

    @media (prefers-reduced-motion: reduce) {
      * { animation: none !important; transition: none !important; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>Ticketmaster Control Panel</h1>
        <div class="subtitle">Simple auto-click bot with fresh sessions and refresh loop.</div>
      </div>
      <form method="post" action="{{ url_for('launch_chrome_window') }}" style="margin: 0;">
        <button class="btn-primary" type="submit">Open New Chrome Window</button>
      </form>
    </header>

    <div class="card">
      {% if error %}
      <div class="banner">{{ error }}</div>
      {% endif %}
      {% if success %}
      <div class="success">{{ success }}</div>
      {% endif %}
      <form method="post" action="{{ url_for('start') }}">
        <div class="grid">
          <div>
            <label for="url">Event URL</label>
            <input id="url" name="url" type="text" placeholder="https://ticketmaster.sg/..." required />
          </div>
          <div id="button_text_wrap">
            <label for="button_text">Button Text</label>
            <input id="button_text" name="button_text" type="text" placeholder="Buy, Add, Checkout" />
          </div>
          <div>
            <label for="refresh">Refresh Seconds (0.5-4 random recommended)</label>
            <input id="refresh" name="refresh" type="number" step="0.1" min="0.5" max="30" value="3" />
          </div>
          <div>
            <label for="quantity">Quantity</label>
            <input id="quantity" name="quantity" type="number" min="1" max="6" value="1" />
          </div>
          <div>
            <label for="max_attempts">Max Attempts</label>
            <input id="max_attempts" name="max_attempts" type="number" min="1" max="5000" value="500" />
          </div>
        </div>
        <div style="margin-top: 12px;">
          <div class="row">
            <label class="checkbox"><input id="auto_detect_widget" type="checkbox" name="auto_detect_widget" checked /> Auto-detect widget (recommended)</label>
          </div>
        </div>
        <div style="margin-top: 12px;">
          <div class="row">
            <label class="checkbox"><input id="auto_launch" type="checkbox" name="auto_launch" checked /> Auto launch (recommended)</label>
            <label class="checkbox"><input type="checkbox" name="headless" /> Headless</label>
            <label class="checkbox"><input type="checkbox" name="auto_buy" /> Auto-buy</label>
            <label class="checkbox"><input type="checkbox" name="skip_refresh" checked /> Hybrid refresh (recommended)</label>
          </div>
          <p class="muted" style="margin: 6px 0 12px; font-size: 12px;">Auto launch: buka Chrome baru dengan profile terpisah.</p>
        </div>
        <div id="debugger_wrap">
          <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));">
            <div>
              <label for="debugger">Debugger Address (optional)</label>
              <input id="debugger" name="debugger" type="text" placeholder="127.0.0.1:9222 or 9222" />
            </div>
            <div>
              <label for="user_data_dir">User Data Dir (optional)</label>
              <input id="user_data_dir" name="user_data_dir" type="text" placeholder="/path/to/profile" />
            </div>
          </div>
          <div class="row" style="margin-top: 8px;">
            <label class="checkbox"><input id="open_new_tab" type="checkbox" name="open_new_tab" checked /> Open new tab (for debugger)</label>
            <label class="checkbox"><input type="checkbox" name="new_session" checked /> New session</label>
          </div>
        </div>
        <details style="margin-top: 12px; border: 1px solid var(--border); border-radius: 12px; padding: 8px 12px;">
          <summary style="cursor: pointer; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); list-style: none;">
            Advanced
          </summary>
          <div class="row" style="margin-top: 8px;">
            <label class="checkbox"><input type="checkbox" name="aggressive_order" /> Aggressive order (skip qty check)</label>
            <label class="checkbox"><input type="checkbox" name="aggressive_click" /> Aggressive click (skip scroll)</label>
            <label class="checkbox"><input type="checkbox" name="close_on_exit" /> Close browser on stop</label>
          </div>
        </details>
        <div class="row" style="margin-top: 16px;">
          <button class="btn-primary" type="submit">Start Bot</button>
        </div>
      </form>
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Status</th>
            <th>Target</th>
            <th>Options</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody id="tasks-body">{{ table_body|safe }}</tbody>
      </table>
    </div>
  </div>

  <script>
    (function () {
      const autoDetect = document.getElementById("auto_detect_widget");
      const buttonTextWrap = document.getElementById("button_text_wrap");
      const autoLaunch = document.getElementById("auto_launch");
      const debuggerWrap = document.getElementById("debugger_wrap");
      const debuggerInput = document.getElementById("debugger");
      const openNewTab = document.getElementById("open_new_tab");

      if (autoDetect && buttonTextWrap) {
        const syncButtonText = () => {
          buttonTextWrap.classList.toggle("hidden", autoDetect.checked);
          const buttonTextInput = document.getElementById("button_text");
          if (buttonTextInput) {
            buttonTextInput.required = !autoDetect.checked;
          }
        };
        syncButtonText();
        autoDetect.addEventListener("change", syncButtonText);
      }

      if (autoLaunch && debuggerWrap) {
        const syncDebugger = () => {
          const show = !autoLaunch.checked;
          debuggerWrap.classList.toggle("hidden", !show);
          if (debuggerInput) {
            debuggerInput.disabled = !show;
          }
          if (openNewTab) {
            openNewTab.disabled = !show;
          }
        };
        syncDebugger();
        autoLaunch.addEventListener("change", syncDebugger);
      }

      async function refreshTasks() {
        try {
          const response = await fetch("{{ url_for('task_rows') }}", { cache: "no-store" });
          if (!response.ok) return;
          const html = await response.text();
          document.getElementById("tasks-body").innerHTML = html;
        } catch (err) {
          console.error(err);
        }
      }

      refreshTasks();
      setInterval(refreshTasks, 3000);
    })();
  </script>
</body>
</html>
"""

TABLE_BODY_TEMPLATE = """
{% for task in tasks %}
<tr>
  <td class="mono">#{{ task.task_id }}</td>
  <td><span class="status {{ task.status }}">{{ task.status }}</span></td>
  <td>
    <div class="mono">{{ task.url }}</div>
    <div class="muted">{{ task.button_text }}</div>
    {% if task.debugger_address %}
    <div class="muted">• {{ task.debugger_address }}</div>
    {% endif %}
  </td>
  <td>
    <div class="muted">refresh: {{ '%.1f'|format(task.refresh_seconds) }}s</div>
    <div class="muted">auto_buy: {{ 'yes' if task.auto_buy else 'no' }}</div>
    <div class="muted">max: {{ task.max_attempts }}</div>
    <div class="muted">headless: {{ 'yes' if task.headless else 'no' }}</div>
    {% if task.auto_launch %}
    <div class="muted">auto_launch: yes</div>
    {% endif %}
    {% if task.skip_refresh %}
    <div class="muted">skip_refresh: yes</div>
    {% endif %}
    {% if task.auto_detect_widget %}
    <div class="muted">auto_detect: yes</div>
    {% endif %}
  </td>
  <td class="actions">
    {% if task.log_path %}
    <form method="get" action="{{ url_for('view_log', task_id=task.task_id) }}" target="_blank">
      <button class="btn-secondary" type="submit">Log</button>
    </form>
    {% endif %}
    {% if task.status in ['starting', 'running', 'stopping'] %}
    <form method="post" action="{{ url_for('stop_bot', task_id=task.task_id) }}">
      <button class="btn-secondary" type="submit">Stop</button>
    </form>
    {% else %}
    <form method="post" action="{{ url_for('restart_bot', task_id=task.task_id) }}">
      <button class="btn-secondary" type="submit">Restart</button>
    </form>
    {% endif %}
  </td>
</tr>
{% endfor %}
"""

LOG_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Log {{ task.task_id }}</title>
  <style>
    body { font-family: 'Space Grotesk', sans-serif; padding: 16px; background: #0f172a; color: #e2e8f0; }
    pre { white-space: pre-wrap; }
  </style>
</head>
<body>
  <h2>Log Bot {{ task.task_id }}</h2>
  <p>Status: {{ task.status }}</p>
  <pre>{{ log_content }}</pre>
</body>
</html>
"""


@app.get("/")
def index():
    with TASKS_LOCK:
        tasks = sorted(TASKS.values(), key=lambda t: t.started_at or datetime.min, reverse=True)
    table_body = render_template_string(TABLE_BODY_TEMPLATE, tasks=tasks)
    error = request.args.get("error", "")
    success = request.args.get("success", "")
    return render_template_string(PAGE_TEMPLATE, tasks=tasks, error=error, success=success, table_body=table_body)


@app.get("/tasks/rows")
def task_rows():
    with TASKS_LOCK:
        tasks = sorted(TASKS.values(), key=lambda t: t.started_at or datetime.min, reverse=True)
    return render_template_string(TABLE_BODY_TEMPLATE, tasks=tasks)


@app.post("/start")
def start():
    url = (request.form.get("url") or "").strip()
    button_text = (request.form.get("button_text") or "").strip()
    auto_detect_widget = request.form.get("auto_detect_widget") == "on"
    
    if not url:
        return redirect(url_for("index", error="URL wajib diisi."))
    if not button_text and not auto_detect_widget:
        return redirect(url_for("index", error="Button text wajib diisi jika auto-detect widget tidak dicentang."))

    try:
        refresh_seconds = float(request.form.get("refresh") or 3)
    except Exception:
        refresh_seconds = 3.0

    try:
        quantity = int(request.form.get("quantity") or 1)
    except Exception:
        quantity = 1

    try:
        max_attempts = int(request.form.get("max_attempts") or 500)
    except Exception:
        max_attempts = 500

    headless = request.form.get("headless") == "on"
    auto_buy = request.form.get("auto_buy") == "on"
    auto_launch = request.form.get("auto_launch") == "on"
    open_new_tab = request.form.get("open_new_tab") == "on"
    new_session = request.form.get("new_session") == "on"
    skip_refresh = request.form.get("skip_refresh") == "on"
    aggressive_order = request.form.get("aggressive_order") == "on"
    aggressive_click = request.form.get("aggressive_click") == "on"
    close_on_exit = request.form.get("close_on_exit") == "on"

    debugger_address = normalize_debugger_address(request.form.get("debugger"))
    user_data_dir = (request.form.get("user_data_dir") or "").strip()
    
    if not url.startswith("http"):
        url = "https://" + url

    task_id = datetime.now().strftime("%H%M%S%f")[-8:]
    log_path = str(LOG_DIR / f"ticketmaster-{task_id}.log")

    if auto_launch:
        profile_dir = Path(__file__).parent / "chrome_profiles" / f"profile-{task_id}"
        user_data_dir = str(profile_dir)
        debugger_address = ""
        open_new_tab = False

    if debugger_address:
        with TASKS_LOCK:
            for task in TASKS.values():
                if is_active(task.status) and task.debugger_address == debugger_address:
                    return redirect(url_for("index", error="Debugger address sudah dipakai bot lain."))

    if auto_launch:
        with TASKS_LOCK:
            exclude_ports = {
                int(task.debugger_address.split(":")[-1])
                for task in TASKS.values()
                if is_active(task.status) and task.debugger_address
            }
        port = find_free_port(exclude_ports=exclude_ports)
        if not port:
            return redirect(url_for("index", error="Tidak menemukan port kosong untuk Chrome."))
        _, err = launch_chrome(port, Path(user_data_dir), "about:blank", use_anti_detection=True)
        if err:
            return redirect(url_for("index", error=f"Gagal buka Chrome: {err}"))
        if not wait_for_port(port, timeout_seconds=15.0):
            return redirect(url_for("index", error="Chrome tidak merespon port debugging."))
        debugger_address = f"127.0.0.1:{port}"

    stop_event = Event()
    bot = TicketmasterSimpleBot(
        url=url,
        button_text=button_text,
        refresh_seconds=refresh_seconds,
        max_attempts=max_attempts,
        headless=headless,
        auto_buy=auto_buy,
        quantity=quantity,
        debugger_address=debugger_address,
        open_new_tab=open_new_tab,
        user_data_dir=user_data_dir,
        new_session=new_session,
        stop_event=stop_event,
        close_on_exit=close_on_exit,
        interactive=False,
    )

    task = BotTask(
        task_id=task_id,
        status="starting",
        url=url,
        button_text=button_text,
        refresh_seconds=refresh_seconds,
        max_attempts=max_attempts,
        headless=headless,
        auto_buy=auto_buy,
        quantity=quantity,
        debugger_address=debugger_address,
        open_new_tab=open_new_tab,
        new_session=new_session,
        auto_launch=auto_launch,
        user_data_dir=user_data_dir,
        stop_event=stop_event,
        log_path=log_path,
        started_at=datetime.now(),
        bot=bot,
        close_on_exit=close_on_exit,
        aggressive_order=aggressive_order,
        aggressive_click=aggressive_click,
        skip_refresh=skip_refresh,
        auto_detect_widget=auto_detect_widget,
    )

    thread = Thread(target=run_bot_task, args=(task,), daemon=True)
    task.thread = thread

    with TASKS_LOCK:
        TASKS[task_id] = task

    thread.start()
    return redirect(url_for("index"))


@app.post("/stop/<task_id>")
def stop_bot(task_id: str):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
    if not task:
        return redirect(url_for("index", error="Task tidak ditemukan."))

    if is_active(task.status):
        task.status = "stopping"
        task.stop_event.set()
        if task.bot:
            task.bot.request_stop()
    return redirect(url_for("index"))


@app.post("/restart/<task_id>")
def restart_bot(task_id: str):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
    if not task:
        return redirect(url_for("index", error="Task tidak ditemukan."))

    if is_active(task.status):
        return redirect(url_for("index", error="Task masih berjalan."))

    auto_launch = task.auto_launch
    debugger_address = task.debugger_address
    open_new_tab = task.open_new_tab
    new_session = task.new_session
    user_data_dir = task.user_data_dir or ""
    close_on_exit = task.close_on_exit
    aggressive_order = task.aggressive_order
    aggressive_click = task.aggressive_click
    skip_refresh = task.skip_refresh
    auto_detect_widget = task.auto_detect_widget

    if auto_launch:
        reuse_debugger = False
        port = None
        if debugger_address:
            try:
                port = int(debugger_address.split(":")[-1])
            except ValueError:
                port = None
            if port and wait_for_port(port, timeout_seconds=1.5):
                reuse_debugger = True
        if not reuse_debugger:
            with TASKS_LOCK:
                exclude_ports = {
                    int(other.debugger_address.split(":")[-1])
                    for other in TASKS.values()
                    if is_active(other.status) and other.debugger_address
                }
            port = find_free_port(exclude_ports=exclude_ports)
            if not port:
                return redirect(url_for("index", error="Tidak menemukan port kosong untuk Chrome."))
            _, err = launch_chrome(port, Path(user_data_dir), "about:blank", use_anti_detection=True)
            if err:
                return redirect(url_for("index", error=f"Gagal buka Chrome: {err}"))
            if not wait_for_port(port, timeout_seconds=15.0):
                return redirect(url_for("index", error="Chrome tidak merespon port debugging."))
            debugger_address = f"127.0.0.1:{port}"
        open_new_tab = False

    if debugger_address:
        with TASKS_LOCK:
            for other in TASKS.values():
                if other.task_id != task_id and is_active(other.status) and other.debugger_address == debugger_address:
                    return redirect(url_for("index", error="Debugger address sudah dipakai bot lain."))

    stop_event = Event()
    bot = TicketmasterSimpleBot(
        url=task.url,
        button_text=task.button_text,
        refresh_seconds=task.refresh_seconds,
        max_attempts=task.max_attempts,
        headless=task.headless,
        auto_buy=task.auto_buy,
        quantity=task.quantity,
        debugger_address=debugger_address,
        open_new_tab=open_new_tab,
        user_data_dir=user_data_dir,
        new_session=new_session,
        stop_event=stop_event,
        close_on_exit=close_on_exit,
        interactive=False,
    )

    task.stop_event = stop_event
    task.bot = bot
    task.status = "starting"
    task.error = ""
    task.started_at = datetime.now()
    task.stopped_at = None
    task.debugger_address = debugger_address
    task.open_new_tab = open_new_tab

    thread = Thread(target=run_bot_task, args=(task,), daemon=True)
    task.thread = thread
    thread.start()

    return redirect(url_for("index"))


@app.get("/logs/<task_id>")
def view_log(task_id: str):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
    if not task or not task.log_path:
        return "Log tidak ditemukan", 404
    log_content = read_log_tail(Path(task.log_path))
    return render_template_string(LOG_TEMPLATE, task=task, log_content=log_content)


@app.post("/launch-chrome-window")
def launch_chrome_window():
    """Launch a new Chrome window with fresh session and unique debugging port"""
    with TASKS_LOCK:
        exclude_ports = {
            int(task.debugger_address.split(":")[-1])
            for task in TASKS.values()
            if is_active(task.status) and task.debugger_address and ":" in task.debugger_address
        }
    
    port = find_free_port(exclude_ports=exclude_ports)
    if not port:
        return redirect(url_for("index", error="Tidak menemukan port kosong untuk Chrome."))
    
    profile_id = datetime.now().strftime("%H%M%S%f")[-8:]
    profile_dir = Path(__file__).parent / "chrome_profiles" / f"session-{profile_id}"
    user_data_dir = str(profile_dir)
    
    _, err = launch_chrome(port, Path(user_data_dir), "about:blank", use_anti_detection=True)
    if err:
        return redirect(url_for("index", error=f"Gagal buka Chrome: {err}"))
    
    if not wait_for_port(port, timeout_seconds=15.0):
        return redirect(url_for("index", error="Chrome tidak merespon port debugging."))
    
    debugger_address = f"127.0.0.1:{port}"
    return redirect(url_for("index", success=f"Chrome window dibuka dengan debugging port: {debugger_address}. Profile: {profile_dir.name} (Anti-detection enabled)"))


if __name__ == "__main__":
    port = os.environ.get("PANEL_TICKETMASTER_PORT", "").strip()
    if not port:
        port = "5002"
    app.run(host="127.0.0.1", port=int(port), debug=False)

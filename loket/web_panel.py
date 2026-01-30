import json
import os
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
import urllib.request
from uuid import uuid4

from flask import Flask, redirect, render_template_string, request, url_for

try:
    from .simple_bot import SimpleButtonBot
except ImportError:
    try:
        from loket.simple_bot import SimpleButtonBot
    except ImportError:
        from simple_bot import SimpleButtonBot

app = Flask(__name__)

LOG_DIR = Path(__file__).parent / "logs"
DEFAULT_WINDOW_SIZE = "1200,800"

def is_macos() -> bool:
    return sys.platform == "darwin"


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_linux() -> bool:
    return sys.platform.startswith("linux")


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
        except:
            pass

    def flush(self):
        try:
            self._default_stream.flush()
        except:
            pass

    def isatty(self):
        try:
            return self._default_stream.isatty()
        except:
            return False


STDOUT_ROUTER = ThreadOutputRouter(sys.stdout)
STDERR_ROUTER = ThreadOutputRouter(sys.stderr)
sys.stdout = STDOUT_ROUTER
sys.stderr = STDERR_ROUTER


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


def launch_chrome(port: Optional[int], profile_dir: Path, start_url: str):
    chrome_path = find_chrome_path()
    if not chrome_path:
        return None, "Chrome tidak ditemukan. Install Chrome atau set CHROME_PATH."

    if not start_url:
        start_url = "about:blank"
    profile_dir.mkdir(parents=True, exist_ok=True)
    args = []
    if port:
        args.append(f"--remote-debugging-port={port}")
    args.extend([
        f"--user-data-dir={str(profile_dir)}",
        "--no-first-run",
        "--no-default-browser-check",
        f"--window-size={DEFAULT_WINDOW_SIZE}",
        "--new-window",
        start_url,
    ])
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


def activate_chrome_target(debugger_address: str) -> str:
    address = (debugger_address or "").strip()
    if not address:
        return "Debugger address kosong."
    if not address.startswith("http://") and not address.startswith("https://"):
        address = "http://" + address

    targets = None
    for path in ("/json/list", "/json"):
        try:
            with urllib.request.urlopen(address + path, timeout=2) as response:
                data = json.load(response)
            if isinstance(data, list):
                targets = data
                break
        except Exception:
            continue

    if targets is None:
        return "Chrome tidak merespon port debugging."
    if not targets:
        return "Tidak ada target tab di Chrome."

    target_id = ""
    for target in targets:
        if target.get("type") == "page":
            target_id = target.get("id") or target.get("targetId") or ""
            if target_id:
                break
    if not target_id:
        first = targets[0]
        target_id = first.get("id") or first.get("targetId") or ""

    if not target_id:
        return "Tidak ada target tab di Chrome."

    try:
        with urllib.request.urlopen(f"{address}/json/activate/{target_id}", timeout=2) as response:
            response.read()
    except Exception:
        return "Gagal mengaktifkan tab Chrome."
    return ""


def make_auto_open_chrome_handler(debugger_address: str, task_id: str = ""):
    def handler():
        if not debugger_address:
            return
        err = activate_chrome_target(debugger_address)
        if err:
            label = f" ({task_id})" if task_id else ""
            print(f"⚠️ Auto-open Chrome{label} gagal: {err}")

    return handler


def read_log_tail(path: Path, max_bytes: int = 40000) -> str:
    if not path.exists():
        return ""
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > max_bytes:
            handle.seek(-max_bytes, os.SEEK_END)
        data = handle.read()
    return data.decode("utf-8", errors="replace")


@dataclass
class BotTask:
    task_id: str
    concert_url: str
    button_text: str
    auto_buy: bool
    ticket_category: str
    ticket_quantity: int
    debugger_address: str
    open_new_tab: bool
    close_on_exit: bool
    aggressive_order: bool
    aggressive_click: bool
    skip_refresh: bool
    auto_detect_widget: bool
    started_at: datetime
    user_data_dir: str = ""
    log_path: str = ""
    status: str = "starting"
    error: str = ""
    stopped_at: Optional[datetime] = None
    stop_event: Event = field(default_factory=Event)
    bot: Optional[SimpleButtonBot] = None
    thread: Optional[Thread] = None


TASKS = {}
TASKS_LOCK = Lock()


def is_active(status: str) -> bool:
    return status in {"starting", "running", "stopping"}


def is_task_active(task: BotTask) -> bool:
    if not is_active(task.status):
        return False
    if task.thread and not task.thread.is_alive():
        return False
    return True


def run_bot_task(task: BotTask) -> None:
    thread_id = threading.get_ident()
    log_stream = None
    if task.log_path:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = Path(task.log_path)
        log_stream = log_path.open("a", encoding="utf-8")
        STDOUT_ROUTER.register(thread_id, log_stream)
        STDERR_ROUTER.register(thread_id, log_stream)
        print(f"=== Bot {task.task_id} started {datetime.now().isoformat(timespec='seconds')} ===")

    task.status = "running"
    try:
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
        if log_stream:
            print(f"=== Bot {task.task_id} selesai ({task.status}) {task.stopped_at.isoformat(timespec='seconds')} ===")
            STDOUT_ROUTER.unregister(thread_id)
            STDERR_ROUTER.unregister(thread_id)
            log_stream.close()


TABLE_BODY_TEMPLATE = """
        {% for task in tasks %}
        <tr>
          <td class="nowrap mono">#{{ task.task_id }}</td>
          <td class="nowrap">
            <span class="status {{ task.status }}" {% if task.error %}title="{{ task.error }}"{% endif %}>{{ task.status }}</span>
          </td>
          <td class="truncate" title="{{ task.concert_url }} | {{ task.button_text }}{% if task.debugger_address %} | {{ task.debugger_address }}{% endif %}">
            {{ task.concert_url }}
            <span class="muted">• {{ task.button_text }}</span>
            {% if task.debugger_address %}
            <span class="muted">• {{ task.debugger_address }}</span>
            {% endif %}
          </td>
          <td class="auto-cell nowrap">
            {% if task.bot and task.bot.awaiting_auto_buy_selection %}
              {% if task.bot.widget_categories %}
              <form class="inline-form" method="post" action="{{ url_for('set_auto_buy', task_id=task.task_id) }}">
                <select name="ticket_category" required title="Kategori">
                  {% for name in task.bot.widget_categories %}
                  <option value="{{ name }}">{{ name }}</option>
                  {% endfor %}
                </select>
                <input class="qty-input" type="number" name="ticket_quantity" min="1" max="6" value="{{ task.ticket_quantity or 1 }}" title="Qty" />
                <button class="icon-btn btn-start" type="submit" title="Auto-buy">
                  <svg class="icon"><use href="#icon-check"></use></svg>
                </button>
              </form>
              {% else %}
              <span class="muted">Auto: tunggu</span>
              {% endif %}
            {% elif task.bot and task.bot.auto_buy_running %}
              {% if task.bot.auto_buy_paused %}
                <form class="inline-form" method="post" action="{{ url_for('set_auto_buy', task_id=task.task_id) }}">
                  {% if task.bot.widget_categories %}
                  <select name="ticket_category" required title="Kategori">
                    {% for name in task.bot.widget_categories %}
                    <option value="{{ name }}">{{ name }}</option>
                    {% endfor %}
                  </select>
                  {% else %}
                  <input class="cat-input" type="text" name="ticket_category" placeholder="Kategori" required />
                  {% endif %}
                  <input class="qty-input" type="number" name="ticket_quantity" min="1" max="6" value="{{ task.ticket_quantity or 1 }}" title="Qty" />
                  <button class="icon-btn btn-start" type="submit" title="Update & Resume">
                    <svg class="icon icon-fill"><use href="#icon-play"></use></svg>
                  </button>
                </form>
              {% else %}
                <span class="muted">Auto: {{ task.ticket_category or '-' }} x{{ task.ticket_quantity or 1 }}</span>
                <form class="inline-form" method="post" action="{{ url_for('pause_auto_buy', task_id=task.task_id) }}">
                  <button class="icon-btn btn-stop" type="submit" title="Pause">
                    <svg class="icon"><use href="#icon-pause"></use></svg>
                  </button>
                </form>
              {% endif %}
            {% elif task.auto_buy %}
              {% if task.ticket_category %}
              <span class="muted">Auto: {{ task.ticket_category }} x{{ task.ticket_quantity }}</span>
              {% else %}
              <span class="muted">Auto: tunggu</span>
              {% endif %}
            {% else %}
              <span class="muted">Manual</span>
            {% endif %}
          </td>
          <td class="actions-cell nowrap">
            <div class="action-group">
              {% if task.log_path %}
              <a class="icon-btn" href="{{ url_for('view_log', task_id=task.task_id) }}" target="_blank" title="Log">
                <svg class="icon"><use href="#icon-log"></use></svg>
              </a>
              {% endif %}
              {% if task.debugger_address %}
              <form class="inline-form" method="post" action="{{ url_for('open_chrome', task_id=task.task_id) }}">
                <button class="icon-btn btn-chrome" type="submit" title="Chrome">
                  <svg class="icon"><use href="#icon-browser"></use></svg>
                </button>
              </form>
              {% endif %}
              {% if task.status in ['starting', 'running', 'stopping'] %}
              <form class="inline-form" method="post" action="{{ url_for('stop_bot', task_id=task.task_id) }}">
                <button class="icon-btn btn-stop" type="submit" title="Stop">
                  <svg class="icon"><use href="#icon-stop"></use></svg>
                </button>
              </form>
              {% else %}
              <form class="inline-form" method="post" action="{{ url_for('restart_bot', task_id=task.task_id) }}">
                <button class="icon-btn btn-start" type="submit" title="Restart">
                  <svg class="icon"><use href="#icon-restart"></use></svg>
                </button>
              </form>
              {% endif %}
              <form class="inline-form" method="post" action="{{ url_for('delete_bot', task_id=task.task_id) }}" onsubmit="return confirm('Hapus bot ini?');">
                <button class="icon-btn btn-delete" type="submit" title="Hapus">
                  <svg class="icon"><use href="#icon-trash"></use></svg>
                </button>
              </form>
            </div>
          </td>
        </tr>
        {% endfor %}
"""

PAGE_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Bot Simple Panel</title>
  <style>
    :root {
      --bg: #0e1116;
      --card: #161b22;
      --muted: #94a3b8;
      --text: #e2e8f0;
      --accent: #22c55e;
      --danger: #ef4444;
      --border: #2b3240;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", Tahoma, sans-serif;
      background: radial-gradient(circle at top, #1a2233 0%, #0e1116 55%);
      color: var(--text);
    }
    .wrap {
      max-width: 1100px;
      margin: 32px auto 64px;
      padding: 0 20px;
    }
    h1 {
      margin: 0 0 8px;
      font-size: 28px;
      letter-spacing: 0.4px;
    }
    p {
      margin: 4px 0 12px;
      color: var(--muted);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-top: 18px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.25);
    }
    label {
      display: block;
      font-size: 13px;
      margin-bottom: 6px;
      color: var(--muted);
    }
    input[type="text"],
    input[type="number"],
    select {
      width: 100%;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: #0b0f15;
      color: var(--text);
      margin-bottom: 12px;
    }
    select { cursor: pointer; }
    .row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }
    .section-title {
      margin: 0 0 6px;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--muted);
    }
    .options-grid {
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      margin: 6px 0 12px;
    }
    details.advanced {
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 8px 12px;
      margin-top: 10px;
    }
    details.advanced summary {
      cursor: pointer;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--muted);
      list-style: none;
    }
    details.advanced summary::-webkit-details-marker {
      display: none;
    }
    .inline-form {
      display: inline-flex;
      gap: 6px;
      flex-wrap: nowrap;
      align-items: center;
    }
    .checkbox {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 13px;
    }
    .hidden {
      display: none;
    }
    button {
      border: none;
      border-radius: 10px;
      padding: 10px 14px;
      font-weight: 600;
      cursor: pointer;
    }
    .icon-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      padding: 0;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: #0b0f15;
      color: var(--text);
      text-decoration: none;
    }
    .icon {
      width: 16px;
      height: 16px;
      stroke: currentColor;
      stroke-width: 2;
      fill: none;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .icon-fill {
      fill: currentColor;
      stroke: none;
    }
    .btn-start {
      background: var(--accent);
      color: #0b0f15;
    }
    .btn-chrome {
      background: #38bdf8;
      color: #0b0f15;
    }
    .btn-stop {
      background: transparent;
      color: var(--danger);
      border: 1px solid var(--danger);
    }
    .btn-delete {
      background: var(--danger);
      color: #0b0f15;
    }
    .icon-btn.btn-start,
    .icon-btn.btn-chrome,
    .icon-btn.btn-delete {
      border: none;
    }
    .alert {
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.4);
      color: #fecaca;
      padding: 10px 12px;
      border-radius: 10px;
      margin-top: 12px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      font-size: 13px;
    }
    th, td {
      text-align: left;
      padding: 10px 8px;
      border-bottom: 1px solid var(--border);
      vertical-align: middle;
    }
    .table-compact {
      font-size: 12px;
    }
    .table-compact th,
    .table-compact td {
      padding: 8px 6px;
      white-space: nowrap;
    }
    .table-compact select,
    .table-compact input[type="number"],
    .table-compact input[type="text"] {
      height: 28px;
      padding: 4px 8px;
      font-size: 12px;
      margin-bottom: 0;
    }
    .table-compact select {
      max-width: 180px;
    }
    .qty-input {
      width: 60px;
    }
    .cat-input {
      width: 140px;
    }
    .truncate {
      max-width: 520px;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .nowrap {
      white-space: nowrap;
    }
    .mono {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      letter-spacing: 0.2px;
    }
    th { color: var(--muted); font-weight: 600; }
    .status {
      display: inline-flex;
      padding: 3px 8px;
      border-radius: 999px;
      font-size: 12px;
      background: #0b0f15;
      border: 1px solid var(--border);
    }
    .status.running { color: #38bdf8; }
    .status.stopped { color: #fbbf24; }
    .status.finished { color: #22c55e; }
    .status.error { color: #f87171; }
    .muted { color: var(--muted); }
    .action-group {
      display: inline-flex;
      flex-wrap: nowrap;
      gap: 6px;
      align-items: center;
    }
    .action-group form {
      margin: 0;
    }
    .icon-sprite {
      display: none;
    }
    pre {
      background: #0b0f15;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px;
      white-space: pre-wrap;
    }
  </style>
</head>
<body>
  <svg class="icon-sprite" xmlns="http://www.w3.org/2000/svg">
    <symbol id="icon-log" viewBox="0 0 24 24">
      <path d="M6 2h8l4 4v16H6z"></path>
      <path d="M14 2v6h6"></path>
      <path d="M8 12h8"></path>
      <path d="M8 16h8"></path>
    </symbol>
    <symbol id="icon-browser" viewBox="0 0 24 24">
      <rect x="3" y="5" width="18" height="14" rx="2"></rect>
      <path d="M3 9h18"></path>
    </symbol>
    <symbol id="icon-restart" viewBox="0 0 24 24">
      <path d="M20 12a8 8 0 1 1-2.3-5.7"></path>
      <path d="M20 4v6h-6"></path>
    </symbol>
    <symbol id="icon-stop" viewBox="0 0 24 24">
      <rect x="7" y="7" width="10" height="10" rx="1"></rect>
    </symbol>
    <symbol id="icon-pause" viewBox="0 0 24 24">
      <path d="M9 6v12"></path>
      <path d="M15 6v12"></path>
    </symbol>
    <symbol id="icon-play" viewBox="0 0 24 24">
      <path d="M8 6l10 6-10 6z"></path>
    </symbol>
    <symbol id="icon-check" viewBox="0 0 24 24">
      <path d="M5 13l4 4L19 7"></path>
    </symbol>
    <symbol id="icon-trash" viewBox="0 0 24 24">
      <polyline points="3 6 5 6 21 6"></polyline>
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path>
      <path d="M10 11v6"></path>
      <path d="M14 11v6"></path>
      <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"></path>
    </symbol>
  </svg>
  <div class="wrap">
    <h1>Bot Simple Panel</h1>
    <p>Jalankan beberapa bot dengan sesi Chrome berbeda menggunakan remote debugging.</p>
    <div class="card">
      <p class="muted">Contoh buka Chrome dengan port berbeda:</p>
      <pre>"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\\temp\\chrome-profile-1"
"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9223 --user-data-dir="C:\\temp\\chrome-profile-2"</pre>
    </div>

    {% if error %}
    <div class="alert">{{ error }}</div>
    {% endif %}

    <div class="grid">
      <form class="card" method="post" action="{{ url_for('start_bot') }}">
        <p class="section-title">Target</p>
        <label for="concert_url">Concert URL</label>
        <input id="concert_url" name="concert_url" type="text" placeholder="https://example.com" required />

        <div class="row" style="margin-bottom: 10px;">
          <label class="checkbox"><input id="auto_detect_widget" type="checkbox" name="auto_detect_widget" checked /> Auto-detect widget (recommended)</label>
        </div>

        <div id="button_text_wrap">
          <label for="button_text">Button text</label>
          <input id="button_text" name="button_text" type="text" placeholder="Beli Tiket" />
        </div>

        <p class="section-title">Browser</p>
        <div class="options-grid">
          <label class="checkbox"><input id="auto_launch" type="checkbox" name="auto_launch" checked /> Auto launch (recommended)</label>
          <label class="checkbox"><input type="checkbox" name="skip_refresh" checked /> Hybrid refresh (recommended)</label>
        </div>
        <p class="muted" style="margin: 0 0 10px;">Auto launch: buka Chrome baru dengan profile terpisah.</p>

        <div id="debugger_wrap">
          <label for="debugger_address">Debugger address (optional)</label>
          <input id="debugger_address" name="debugger_address" type="text" placeholder="127.0.0.1:9222 or 9222" />
          <div class="options-grid">
            <label class="checkbox"><input id="open_new_tab" type="checkbox" name="open_new_tab" checked /> Open new tab (for debugger)</label>
          </div>
        </div>

        <details class="advanced">
          <summary>Advanced</summary>
          <div class="options-grid" style="margin-top: 8px;">
            <label class="checkbox"><input type="checkbox" name="aggressive_order" /> Aggressive order (skip qty check)</label>
            <label class="checkbox"><input type="checkbox" name="aggressive_click" /> Aggressive click (skip scroll)</label>
            <label class="checkbox"><input type="checkbox" name="close_on_exit" /> Close browser on stop</label>
          </div>
        </details>

        <div style="margin-top: 12px;">
          <button class="btn-start" type="submit">Start Bot</button>
        </div>
      </form>

      <div class="card">
        <h3>Notes</h3>
        <p class="muted">- Centang Auto launch supaya bot buka Chrome baru dengan profile terpisah.</p>
        <p class="muted">- Satu bot per debugger address untuk menghindari tab bentrok.</p>
        <p class="muted">- Jika Auto launch mati dan debugger address kosong, bot membuka Chrome baru.</p>
        <p class="muted">- Untuk Chrome yang sudah dibuka, gunakan port berbeda untuk sesi berbeda.</p>
        <p class="muted">- Auto buy bisa dipilih setelah widget terbuka dari daftar kategori.</p>
      </div>
    </div>

    <h2 style="margin-top: 28px;">Bots</h2>
    <table class="table-compact">
      <thead>
        <tr>
          <th>ID</th>
          <th>Status</th>
          <th>Target</th>
          <th>Auto buy</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody id="tasks-body">{{ table_body|safe }}</tbody>
    </table>
  </div>
  <script>
    (function () {
      const refreshIntervalMs = 2000;
      const tbody = document.getElementById("tasks-body");
      const autoDetect = document.getElementById("auto_detect_widget");
      const buttonTextWrap = document.getElementById("button_text_wrap");
      const autoLaunch = document.getElementById("auto_launch");
      const debuggerWrap = document.getElementById("debugger_wrap");
      const debuggerInput = document.getElementById("debugger_address");
      const openNewTab = document.getElementById("open_new_tab");
      if (!tbody) {
        return;
      }
      if (autoDetect && buttonTextWrap) {
        const syncButtonText = () => {
          buttonTextWrap.classList.toggle("hidden", autoDetect.checked);
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
      function isFormActive() {
        const active = document.activeElement;
        if (!active) {
          return false;
        }
        if (active.closest && active.closest("form")) {
          return true;
        }
        const tag = active.tagName ? active.tagName.toLowerCase() : "";
        return tag === "input" || tag === "select" || tag === "textarea";
      }

      async function refreshTasks() {
        if (isFormActive()) {
          return;
        }
        try {
          const response = await fetch("{{ url_for('task_rows') }}", { cache: "no-store" });
          if (!response.ok) {
            return;
          }
          const html = await response.text();
          tbody.innerHTML = html;
        } catch (err) {
          return;
        }
      }

      refreshTasks();
      setInterval(refreshTasks, refreshIntervalMs);
    })();
  </script>
</body>
</html>
"""


LOG_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta http-equiv="refresh" content="2" />
  <title>Bot Log</title>
  <style>
    :root {
      --bg: #0e1116;
      --card: #161b22;
      --muted: #94a3b8;
      --text: #e2e8f0;
      --border: #2b3240;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", Tahoma, sans-serif;
      background: radial-gradient(circle at top, #1a2233 0%, #0e1116 55%);
      color: var(--text);
    }
    .wrap {
      max-width: 1000px;
      margin: 24px auto;
      padding: 0 20px 40px;
    }
    a { color: #38bdf8; text-decoration: none; }
    .muted { color: var(--muted); }
    pre {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      white-space: pre-wrap;
      min-height: 300px;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Log Bot {{ task.task_id }}</h1>
    <p class="muted">Status: {{ task.status }} | Refresh otomatis 2 detik</p>
    <p><a href="{{ url_for('index') }}">Back to panel</a></p>
    <pre>{{ log_content }}</pre>
  </div>
</body>
</html>
"""

@app.get("/")
def index():
    error = request.args.get("error", "")
    with TASKS_LOCK:
        tasks = sorted(TASKS.values(), key=lambda t: t.started_at, reverse=True)
    table_body = render_template_string(TABLE_BODY_TEMPLATE, tasks=tasks)
    return render_template_string(PAGE_TEMPLATE, tasks=tasks, error=error, table_body=table_body)


@app.get("/tasks/rows")
def task_rows():
    with TASKS_LOCK:
        tasks = sorted(TASKS.values(), key=lambda t: t.started_at, reverse=True)
    return render_template_string(TABLE_BODY_TEMPLATE, tasks=tasks)


@app.post("/start")
def start_bot():
    concert_url = (request.form.get("concert_url") or "").strip()
    button_text = (request.form.get("button_text") or "").strip()
    auto_launch = request.form.get("auto_launch") == "on"
    debugger_address = normalize_debugger_address(request.form.get("debugger_address"))
    open_new_tab = request.form.get("open_new_tab") == "on"
    close_on_exit = request.form.get("close_on_exit") == "on"
    aggressive_order = request.form.get("aggressive_order") == "on"
    aggressive_click = request.form.get("aggressive_click") == "on"
    skip_refresh = request.form.get("skip_refresh") == "on"
    auto_detect_widget = request.form.get("auto_detect_widget") == "on"

    if not concert_url or (not button_text and not auto_detect_widget):
        return redirect(url_for("index", error="Concert URL wajib diisi. Button text wajib diisi jika auto-detect widget tidak dicentang."))

    if not concert_url.startswith("http"):
        concert_url = "https://" + concert_url

    auto_buy = False
    ticket_category = ""
    ticket_quantity = 1

    task_id = uuid4().hex[:8]
    user_data_dir = ""
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
        _, err = launch_chrome(port, Path(user_data_dir), "about:blank")
        if err:
            return redirect(url_for("index", error=f"Gagal buka Chrome: {err}"))
        if not wait_for_port(port, timeout_seconds=15.0):
            return redirect(url_for("index", error="Chrome tidak merespon port debugging."))
        debugger_address = f"127.0.0.1:{port}"

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = str(LOG_DIR / f"bot-{task_id}.log")
    task = BotTask(
        task_id=task_id,
        concert_url=concert_url,
        button_text=button_text,
        auto_buy=auto_buy,
        ticket_category=ticket_category,
        ticket_quantity=ticket_quantity,
        debugger_address=debugger_address,
        open_new_tab=open_new_tab,
        close_on_exit=close_on_exit,
        aggressive_order=aggressive_order,
        aggressive_click=aggressive_click,
        skip_refresh=skip_refresh,
        auto_detect_widget=auto_detect_widget,
        started_at=datetime.now(),
        user_data_dir=user_data_dir,
        log_path=log_path,
    )
    task.bot = SimpleButtonBot(
        concert_url,
        button_text,
        auto_buy=auto_buy,
        ticket_category=ticket_category or None,
        ticket_quantity=ticket_quantity,
        debugger_address=debugger_address or None,
        open_new_tab=open_new_tab,
        user_data_dir=user_data_dir or None,
        stop_event=task.stop_event,
        close_on_exit=close_on_exit,
        aggressive_order=aggressive_order,
        aggressive_click=aggressive_click,
        skip_refresh=skip_refresh,
        auto_detect_widget=auto_detect_widget,
        on_order_click=make_auto_open_chrome_handler(debugger_address, task_id),
        interactive=False,
    )
    task.thread = Thread(target=run_bot_task, args=(task,), daemon=True)

    with TASKS_LOCK:
        TASKS[task_id] = task

    task.thread.start()
    return redirect(url_for("index"))


@app.post("/auto-buy/<task_id>")
def set_auto_buy(task_id: str):
    ticket_category = (request.form.get("ticket_category") or "").strip()
    ticket_quantity_raw = (request.form.get("ticket_quantity") or "").strip()

    if not ticket_category:
        return redirect(url_for("index", error="Kategori tiket wajib diisi untuk auto buy."))

    ticket_quantity = 1
    if ticket_quantity_raw:
        if not ticket_quantity_raw.isdigit():
            return redirect(url_for("index", error="Jumlah tiket harus angka (1-6)."))
        ticket_quantity = int(ticket_quantity_raw)
    if ticket_quantity < 1 or ticket_quantity > 6:
        return redirect(url_for("index", error="Jumlah tiket harus antara 1-6."))

    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if not task or not task.bot:
            return redirect(url_for("index", error="Bot tidak ditemukan."))
        if not is_active(task.status):
            return redirect(url_for("index", error="Bot sudah selesai atau berhenti."))
        task.auto_buy = True
        task.ticket_category = ticket_category
        task.ticket_quantity = ticket_quantity
        bot = task.bot

    bot.set_auto_buy_selection(ticket_category, ticket_quantity)
    if bot.auto_buy_running and bot.auto_buy_paused:
        bot.resume_auto_buy()
    return redirect(url_for("index"))


@app.post("/auto-buy/<task_id>/pause")
def pause_auto_buy(task_id: str):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if not task or not task.bot:
            return redirect(url_for("index", error="Bot tidak ditemukan."))
        if not is_active(task.status):
            return redirect(url_for("index", error="Bot sudah selesai atau berhenti."))
        bot = task.bot

    if not bot.pause_auto_buy():
        return redirect(url_for("index", error="Auto-buy belum berjalan."))
    return redirect(url_for("index"))


@app.post("/auto-buy/<task_id>/resume")
def resume_auto_buy(task_id: str):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if not task or not task.bot:
            return redirect(url_for("index", error="Bot tidak ditemukan."))
        if not is_active(task.status):
            return redirect(url_for("index", error="Bot sudah selesai atau berhenti."))
        bot = task.bot

    if not bot.resume_auto_buy():
        return redirect(url_for("index", error="Auto-buy belum berjalan."))
    return redirect(url_for("index"))



@app.post("/chrome/<task_id>")
def open_chrome(task_id: str):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
    if not task:
        return redirect(url_for("index", error="Bot tidak ditemukan."))
    if not task.debugger_address:
        return redirect(url_for("index", error="Bot ini tidak memakai debugger address."))
    err = activate_chrome_target(task.debugger_address)
    if err:
        return redirect(url_for("index", error=err))
    return redirect(url_for("index"))


@app.post("/restart/<task_id>")
def restart_bot(task_id: str):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
    if not task:
        return redirect(url_for("index", error="Bot tidak ditemukan."))
    if is_active(task.status):
        return redirect(url_for("index", error="Bot masih berjalan."))

    auto_launch = bool(task.user_data_dir)
    debugger_address = task.debugger_address
    open_new_tab = task.open_new_tab
    close_on_exit = task.close_on_exit
    aggressive_order = task.aggressive_order
    aggressive_click = task.aggressive_click
    skip_refresh = task.skip_refresh
    auto_detect_widget = task.auto_detect_widget
    concert_url = task.concert_url
    button_text = task.button_text
    auto_buy = task.auto_buy
    ticket_category = task.ticket_category
    ticket_quantity = task.ticket_quantity
    user_data_dir = task.user_data_dir or ""

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
            _, err = launch_chrome(port, Path(user_data_dir), "about:blank")
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
    bot = SimpleButtonBot(
        concert_url,
        button_text,
        auto_buy=auto_buy,
        ticket_category=ticket_category or None,
        ticket_quantity=ticket_quantity,
        debugger_address=debugger_address or None,
        open_new_tab=open_new_tab,
        user_data_dir=user_data_dir or None,
        stop_event=stop_event,
        close_on_exit=close_on_exit,
        aggressive_order=aggressive_order,
        aggressive_click=aggressive_click,
        skip_refresh=skip_refresh,
        auto_detect_widget=auto_detect_widget,
        on_order_click=make_auto_open_chrome_handler(debugger_address, task_id),
        interactive=False,
    )
    thread = Thread(target=run_bot_task, args=(task,), daemon=True)

    with TASKS_LOCK:
        task.stop_event = stop_event
        task.bot = bot
        task.thread = thread
        task.status = "starting"
        task.error = ""
        task.started_at = datetime.now()
        task.stopped_at = None
        task.debugger_address = debugger_address
        task.open_new_tab = open_new_tab

    thread.start()
    return redirect(url_for("index"))


@app.get("/logs/<task_id>")
def view_log(task_id: str):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
    if not task or not task.log_path:
        return "Log not found", 404
    log_content = read_log_tail(Path(task.log_path))
    return render_template_string(LOG_TEMPLATE, task=task, log_content=log_content)


@app.post("/delete/<task_id>")
def delete_bot(task_id: str):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if not task:
            return redirect(url_for("index", error="Bot tidak ditemukan."))
        if is_task_active(task):
            return redirect(url_for("index", error="Bot masih berjalan. Stop dulu sebelum hapus."))
        TASKS.pop(task_id, None)
    return redirect(url_for("index"))


@app.post("/stop/<task_id>")
def stop_bot(task_id: str):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
    if task and is_active(task.status):
        task.status = "stopping"
        task.stop_event.set()
        if task.bot:
            task.bot.request_stop()
    return redirect(url_for("index"))


if __name__ == "__main__":
    default_port = 5050 if is_macos() else 5000
    raw_port = (os.environ.get("PANEL_PORT") or "").strip()
    port = default_port
    if raw_port:
        try:
            port = int(raw_port)
        except ValueError:
            port = default_port
    if port < 1 or port > 65535:
        port = default_port
    app.run(host="127.0.0.1", port=port, debug=False)

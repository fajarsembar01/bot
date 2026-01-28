import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from flask import Flask, jsonify, redirect, render_template_string, request, url_for

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

STATE_LOCK = Lock()


@dataclass
class PanelState:
    status: str = "idle"
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    log_path: str = ""
    error: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    process: Optional[subprocess.Popen] = None
    log_handle: Optional[Any] = None
    chrome_debugger_process: Optional[subprocess.Popen] = None
    chrome_debugger_running: bool = False


STATE = PanelState()


def _is_running(proc: Optional[subprocess.Popen]) -> bool:
    return proc is not None and proc.poll() is None


def _close_log_handle():
    if STATE.log_handle:
        try:
            STATE.log_handle.close()
        except Exception:
            pass
        STATE.log_handle = None


def _refresh_state():
    if STATE.process and STATE.process.poll() is not None:
        exit_code = STATE.process.returncode
        if STATE.status == "stopping":
            STATE.status = "stopped"
        else:
            if exit_code == 0:
                STATE.status = "finished"
            else:
                STATE.status = "error"
                STATE.error = f"Process exited with code {exit_code}"
        STATE.stopped_at = datetime.now()
        STATE.process = None
        _close_log_handle()


def _find_chrome_path() -> Optional[str]:
    """Find Chrome executable path."""
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def _is_chrome_debugger_running() -> bool:
    """Check if Chrome debugger is running by connecting to port 9222."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(1)
        result = sock.connect_ex(("127.0.0.1", 9222))
        if result == 0:
            return True
    except Exception:
        pass
    finally:
        sock.close()
    
    # Fallback to process check if stored
    if STATE.chrome_debugger_process:
        return STATE.chrome_debugger_process.poll() is None
    return False


def _launch_chrome_debugger() -> str:
    """Launch Chrome with remote debugging enabled."""
    with STATE_LOCK:
        if _is_chrome_debugger_running():
            return "Chrome debugger is already running."
        
        chrome_path = _find_chrome_path()
        if not chrome_path:
            return "Chrome executable not found. Please install Google Chrome."
        
        # Create ChromeProfile directory
        profile_dir = Path("C:/selenium/ChromeProfile")
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        # Launch Chrome with remote debugging
        cmd = [
            chrome_path,
            "--remote-debugging-port=9222",
            f"--user-data-dir={profile_dir}",
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )
            STATE.chrome_debugger_process = process
            STATE.chrome_debugger_running = True
            time.sleep(2)  # Wait for Chrome to start
            return ""
        except Exception as exc:
            return f"Failed to launch Chrome: {exc}"


def _stop_chrome_debugger() -> str:
    """Stop Chrome debugger process."""
    with STATE_LOCK:
        if not _is_chrome_debugger_running():
            STATE.chrome_debugger_running = False
            return "Chrome debugger is not running."
        
        proc = STATE.chrome_debugger_process
        if proc:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception:
                pass
        
        STATE.chrome_debugger_process = None
        STATE.chrome_debugger_running = False
        return ""


def _read_log_tail(path: Path, max_bytes: int = 40000) -> str:
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


def _normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if not raw.startswith("http"):
        raw = "https://" + raw
    return raw


def _parse_int(raw: str, default: int, min_value: int, max_value: int) -> int:
    try:
        value = int(raw)
    except Exception:
        return default
    return max(min_value, min(value, max_value))


def _parse_float(raw: str, default: float, min_value: float, max_value: float) -> float:
    try:
        value = float(raw)
    except Exception:
        return default
    return max(min_value, min(value, max_value))


def _build_command(params: Dict[str, Any]) -> list:
    cmd = [
        sys.executable,
        str(BASE_DIR / "auto_buy.py"),
        "--url",
        params["url"],
        "--quantity",
        str(params["quantity"]),
        "--refresh",
        str(params["refresh"]),
        "--max-attempts",
        str(params["max_attempts"]),
        "--non-interactive",
    ]

    if params.get("package"):
        cmd += ["--package", params["package"]]

    if params.get("headless"):
        cmd.append("--headless")
    else:
        cmd.append("--no-headless")

    debugger = params.get("debugger", "")
    if debugger:
        cmd += ["--debugger", debugger]

    user_data_dir = params.get("user_data_dir", "")
    if user_data_dir:
        cmd += ["--user-data-dir", user_data_dir]

    if params.get("open_new_tab"):
        cmd.append("--open-new-tab")

    if params.get("debug"):
        cmd.append("--debug")

    if not params.get("auto_checkout", True):
        cmd.append("--no-auto-checkout")

    return cmd


def _start_bot(params: Dict[str, Any]) -> str:
    with STATE_LOCK:
        _refresh_state()
        if _is_running(STATE.process):
            return "Bot is already running."

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = LOG_DIR / f"tiket-{timestamp}.log"

        cmd = _build_command(params)
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        try:
            log_handle = log_path.open("a", encoding="utf-8")
            process = subprocess.Popen(
                cmd,
                cwd=str(BASE_DIR),
                env=env,
                stdout=log_handle,
                stderr=log_handle,
            )
        except Exception as exc:
            return f"Failed to start bot: {exc}"

        STATE.status = "running"
        STATE.started_at = datetime.now()
        STATE.stopped_at = None
        STATE.log_path = str(log_path)
        STATE.error = ""
        STATE.params = params
        STATE.process = process
        STATE.log_handle = log_handle
        return ""


def _stop_bot() -> str:
    with STATE_LOCK:
        _refresh_state()
        if not _is_running(STATE.process):
            return "Bot is not running."

        STATE.status = "stopping"
        proc = STATE.process

    if proc:
        try:
            proc.terminate()
        except Exception:
            pass

        try:
            proc.wait(timeout=6)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    with STATE_LOCK:
        _refresh_state()
        if STATE.status == "stopping":
            STATE.status = "stopped"
            STATE.stopped_at = datetime.now()
            STATE.process = None
            _close_log_handle()
    return ""


PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Tiket.com Auto-buy Panel</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=Space+Grotesk:wght@400;500;600&display=swap');

    :root {
      --bg: #f6f1ea;
      --bg-accent: #f0e4d6;
      --card: #ffffff;
      --ink: #1f2933;
      --muted: #6b6f76;
      --accent: #e07a36;
      --accent-2: #2a8a82;
      --border: #e6d7c5;
      --shadow: rgba(31, 41, 51, 0.08);
      --danger: #b7422a;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: 'Space Grotesk', sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 15% 20%, #fff7ec 0%, transparent 45%),
        radial-gradient(circle at 85% 10%, #f3efe6 0%, transparent 42%),
        linear-gradient(135deg, var(--bg) 0%, var(--bg-accent) 100%);
    }

    .shell {
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px 24px 48px;
      position: relative;
    }

    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
      gap: 24px;
      align-items: stretch;
    }

    .hero-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 28px;
      box-shadow: 0 20px 40px var(--shadow);
      position: relative;
      overflow: hidden;
      animation: fadeUp 0.6s ease both;
    }

    .hero-card::after {
      content: "";
      position: absolute;
      top: -60px;
      right: -80px;
      width: 220px;
      height: 220px;
      background: radial-gradient(circle, rgba(224, 122, 54, 0.25), transparent 70%);
      border-radius: 50%;
    }

    h1 {
      font-family: 'Fraunces', serif;
      font-size: clamp(28px, 4vw, 40px);
      margin: 0 0 12px;
      letter-spacing: -0.5px;
    }

    .lead {
      font-size: 16px;
      color: var(--muted);
      line-height: 1.6;
      margin: 0 0 20px;
    }

    .chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }

    .chip {
      padding: 6px 12px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: #fff8f1;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .status-card {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      animation: fadeUp 0.7s ease both;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 14px;
      border-radius: 999px;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 600;
    }

    .status-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: currentColor;
      animation: pulse 1.6s ease infinite;
    }

    .status-pill[data-status="idle"] {
      background: #f5efe6;
      color: #8b6d52;
    }

    .status-pill[data-status="running"] {
      background: #e0f2ef;
      color: #16766e;
    }

    .status-pill[data-status="stopping"] {
      background: #fdf4e3;
      color: #b56a12;
    }

    .status-pill[data-status="stopped"],
    .status-pill[data-status="finished"] {
      background: #eef2f6;
      color: #425466;
    }

    .status-pill[data-status="error"] {
      background: #f8e7e3;
      color: var(--danger);
    }

    .status-detail {
      font-size: 14px;
      color: var(--muted);
      margin-top: 12px;
      line-height: 1.6;
    }

    .main-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 0.9fr);
      gap: 24px;
      margin-top: 28px;
    }

    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 24px;
      box-shadow: 0 18px 36px var(--shadow);
      animation: fadeUp 0.8s ease both;
    }

    .card h2 {
      font-family: 'Fraunces', serif;
      font-size: 22px;
      margin: 0 0 8px;
    }

    .card p {
      margin: 0 0 18px;
      color: var(--muted);
      line-height: 1.6;
    }

    .field-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
    }

    label {
      display: block;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-bottom: 6px;
    }

    input[type="text"],
    input[type="number"] {
      width: 100%;
      border-radius: 12px;
      border: 1px solid var(--border);
      padding: 12px 14px;
      font-size: 15px;
      font-family: inherit;
    }

    .checkbox-row {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 6px;
    }

    .checkbox-row input {
      width: 18px;
      height: 18px;
    }

    .step {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: #fdf5ea;
      border: 1px dashed var(--border);
      border-radius: 999px;
      padding: 6px 12px;
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #9b6b36;
      margin-bottom: 12px;
    }

    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 20px;
    }

    button {
      border: none;
      border-radius: 999px;
      padding: 12px 20px;
      font-size: 14px;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .btn-primary {
      background: var(--accent);
      color: #fff;
      box-shadow: 0 12px 24px rgba(224, 122, 54, 0.25);
    }

    .btn-secondary {
      background: #f0f4f5;
      color: #1f2933;
      border: 1px solid var(--border);
    }

    button:hover {
      transform: translateY(-1px);
      box-shadow: 0 16px 30px rgba(31, 41, 51, 0.15);
    }

    .log-box {
      height: 260px;
      background: #0f172a;
      color: #e2e8f0;
      border-radius: 16px;
      padding: 16px;
      overflow: auto;
      font-family: "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: 12px;
      line-height: 1.6;
    }

    .stat-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }

    .stat {
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 12px;
      background: #fffdfa;
    }

    .stat span {
      display: block;
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }

    .stat strong {
      font-size: 14px;
      font-weight: 600;
      word-break: break-all;
    }

    .banner {
      background: #f8e7e3;
      color: var(--danger);
      border: 1px solid #e7c4bc;
      border-radius: 12px;
      padding: 12px 16px;
      margin-bottom: 18px;
      font-size: 14px;
    }

    footer {
      margin-top: 28px;
      color: var(--muted);
      font-size: 12px;
      text-align: center;
    }

    @keyframes fadeUp {
      from {
        opacity: 0;
        transform: translateY(12px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @keyframes pulse {
      0% { opacity: 0.6; transform: scale(0.9); }
      50% { opacity: 1; transform: scale(1.05); }
      100% { opacity: 0.6; transform: scale(0.9); }
    }

    @media (max-width: 980px) {
      .hero {
        grid-template-columns: 1fr;
      }
      .main-grid {
        grid-template-columns: 1fr;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      * {
        animation: none !important;
        transition: none !important;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header class="hero">
      <div class="hero-card">
        <div class="step">Step 1 - Target</div>
        <h1>Tiket.com Auto-buy Control</h1>
        <p class="lead">Panel ini khusus Tiket.com packages. Isi target URL, pilih paket, lalu jalankan auto-buy tanpa menunggu manual click.</p>
        <div class="chip-row">
          <div class="chip">Packages flow</div>
          <div class="chip">Auto refresh</div>
          <div class="chip">Single run</div>
        </div>
      </div>
      <div class="hero-card status-card">
        <div>
          <div class="status-pill" id="status-pill" data-status="{{ state.status }}">
            <span class="status-dot"></span>
            <span id="status-text">{{ state.status }}</span>
          </div>
          <div class="status-detail" id="status-detail">
            {% if state.error %}
              Error: {{ state.error }}
            {% elif state.started_at %}
              Running since {{ state.started_at.strftime('%Y-%m-%d %H:%M:%S') }}
            {% else %}
              Ready to start.
            {% endif %}
          </div>
        </div>
        <div class="stat-grid">
          <div class="stat">
            <span>URL</span>
            <strong id="stat-url">{{ params.get('url', '-') or '-' }}</strong>
          </div>
          <div class="stat">
            <span>Package</span>
            <strong id="stat-package">{{ params.get('package', '-') or '-' }}</strong>
          </div>
          <div class="stat">
            <span>Quantity</span>
            <strong id="stat-qty">{{ params.get('quantity', '-') or '-' }}</strong>
          </div>
        </div>
      </div>
    </header>

    <section class="card" style="margin-top: 28px;">
      <div class="step">Step 1.5 - Chrome Debugger (Optional but Recommended)</div>
      <h2>Chrome Debugger Control</h2>
      <p>Launch Chrome with remote debugging to avoid login redirects. Once launched, login to Tiket.com manually in Chrome.</p>
      <div style="display: flex; align-items: center; gap: 16px; margin-top: 16px;">
        <div style="flex: 1;">
          <div id="chrome-status-display" style="padding: 12px; border-radius: 12px; border: 1px solid var(--border); background: #f5efe6;">
            <strong>Status:</strong> <span id="chrome-status-text">Checking...</span>
          </div>
          <div style="margin-top: 12px; font-size: 13px; color: var(--muted);">
            <strong>Debugger Address:</strong> 127.0.0.1:9222<br>
            <strong>Profile Directory:</strong> C:\selenium\ChromeProfile
          </div>
        </div>
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <form method="post" action="{{ url_for('launch_chrome') }}" style="margin: 0;">
            <button class="btn-primary" type="submit" style="width: 160px;">Launch Chrome</button>
          </form>
          <form method="post" action="{{ url_for('stop_chrome') }}" style="margin: 0;">
            <button class="btn-secondary" type="submit" style="width: 160px;">Stop Chrome</button>
          </form>
        </div>
      </div>
      <div style="margin-top: 16px; padding: 12px; background: #e0f2ef; border: 1px solid #b8e6df; border-radius: 12px; font-size: 13px;">
        <strong>📌 After launching Chrome:</strong><br>
        1. Chrome will open automatically<br>
        2. Go to tiket.com and login<br>
        3. Keep Chrome running while automation is active<br>
        4. Make sure to fill Debugger Address and User Data Dir below
      </div>
    </section>

    <main class="main-grid">
      <section class="card">
        <div class="step">Step 2 - Setup</div>
        <h2>Input Parameters</h2>
        <p>Gunakan nama paket yang muncul di halaman packages Tiket.com. Bot akan cocokkan sebagian nama.</p>
        {% if error %}
        <div class="banner">{{ error }}</div>
        {% endif %}
        <form method="post" action="{{ url_for('start') }}">
          <div class="field-grid">
            <div>
              <label for="url">Packages URL</label>
              <input id="url" name="url" type="text" required value="{{ params.get('url', '') }}" placeholder="https://www.tiket.com/id-id/to-do/.../packages" />
            </div>
            <div>
              <label for="package">Package Name</label>
              <input id="package" name="package" type="text" value="{{ params.get('package', '') }}" placeholder="CAT 1, VIP, etc" />
            </div>
            <div>
              <label for="quantity">Quantity</label>
              <input id="quantity" name="quantity" type="number" min="1" max="6" value="{{ params.get('quantity', 1) }}" />
            </div>
            <div>
              <label for="refresh">Refresh Seconds</label>
              <input id="refresh" name="refresh" type="number" step="0.1" min="0.5" max="30" value="{{ params.get('refresh', 3) }}" />
            </div>
            <div>
              <label for="max_attempts">Max Attempts</label>
              <input id="max_attempts" name="max_attempts" type="number" min="1" max="5000" value="{{ params.get('max_attempts', 500) }}" />
            </div>
            <div>
              <label for="debugger">Debugger Address</label>
              <input id="debugger" name="debugger" type="text" value="{{ params.get('debugger', '') }}" placeholder="127.0.0.1:9222" />
            </div>
            <div>
              <label for="user_data_dir">User Data Dir</label>
              <input id="user_data_dir" name="user_data_dir" type="text" value="{{ params.get('user_data_dir', '') }}" placeholder="/path/to/profile" />
            </div>
          </div>
          <div class="checkbox-row">
            <input id="headless" name="headless" type="checkbox" {% if params.get('headless') %}checked{% endif %} />
            <label for="headless">Headless mode</label>
          </div>
          <div class="checkbox-row">
            <input id="open_new_tab" name="open_new_tab" type="checkbox" {% if params.get('open_new_tab') %}checked{% endif %} />
            <label for="open_new_tab">Open new tab when attaching</label>
          </div>
          <div class="checkbox-row">
            <input id="debug" name="debug" type="checkbox" {% if params.get('debug') %}checked{% endif %} />
            <label for="debug">Verbose debug logs</label>
          </div>
          <div class="checkbox-row">
            <input id="auto_checkout" name="auto_checkout" type="checkbox" {% if params.get('auto_checkout', True) %}checked{% endif %} />
            <label for="auto_checkout">Auto checkout</label>
          </div>
          <div class="actions">
            <button class="btn-primary" type="submit">Start Auto-buy</button>
            <button class="btn-secondary" type="submit" formaction="{{ url_for('stop') }}">Stop</button>
          </div>
        </form>
      </section>

      <section class="card">
        <div class="step">Step 3 - Monitor</div>
        <h2>Live Output</h2>
        <p>Jika muncul challenge atau login, selesaikan langsung di browser yang dibuka bot.</p>
        <div class="log-box" id="log-stream">{{ log_content }}</div>
      </section>
    </main>

    <footer>
      Tiket.com panel runs one bot at a time. Use separate panel from Loket.
    </footer>
  </div>

<script>
  const statusUrl = "{{ url_for('status') }}";
  const logUrl = "{{ url_for('log_tail') }}";

  const statusPill = document.getElementById("status-pill");
  const statusText = document.getElementById("status-text");
  const statusDetail = document.getElementById("status-detail");
  const logStream = document.getElementById("log-stream");
  const statUrl = document.getElementById("stat-url");
  const statPackage = document.getElementById("stat-package");
  const statQty = document.getElementById("stat-qty");

  async function refreshStatus() {
    try {
      const response = await fetch(statusUrl, { cache: "no-store" });
      const data = await response.json();
      statusPill.dataset.status = data.status;
      statusText.textContent = data.status;

      if (data.error) {
        statusDetail.textContent = "Error: " + data.error;
      } else if (data.started_at) {
        statusDetail.textContent = "Running since " + data.started_at;
      } else {
        statusDetail.textContent = "Ready to start.";
      }

      statUrl.textContent = data.params.url || "-";
      statPackage.textContent = data.params.package || "-";
      statQty.textContent = data.params.quantity || "-";
    } catch (err) {
      statusDetail.textContent = "Status check failed.";
    }
  }

  async function refreshLog() {
    try {
      const response = await fetch(logUrl, { cache: "no-store" });
      const text = await response.text();
      logStream.textContent = text || "";
      logStream.scrollTop = logStream.scrollHeight;
    } catch (err) {
      logStream.textContent = "";
    }
  }

  const chromeStatusUrl = "{{ url_for('chrome_status') }}";
  const chromeStatusText = document.getElementById("chrome-status-text");
  const chromeStatusDisplay = document.getElementById("chrome-status-display");

  async function refreshChromeStatus() {
    try {
      const response = await fetch(chromeStatusUrl, { cache: "no-store" });
      const data = await response.json();
      if (data.running) {
        chromeStatusText.textContent = "🟢 Running (Port 9222)";
        chromeStatusDisplay.style.background = "#e0f2ef";
        chromeStatusDisplay.style.borderColor = "#b8e6df";
      } else {
        chromeStatusText.textContent = "⚪ Not Running";
        chromeStatusDisplay.style.background = "#f5efe6";
        chromeStatusDisplay.style.borderColor = "var(--border)";
      }
    } catch (err) {
      chromeStatusText.textContent = "❌ Status check failed";
      chromeStatusDisplay.style.background = "#f8e7e3";
      chromeStatusDisplay.style.borderColor = "#e7c4bc";
    }
  }

  refreshStatus();
  refreshLog();
  refreshChromeStatus();
  setInterval(refreshStatus, 3000);
  setInterval(refreshLog, 3000);
  setInterval(refreshChromeStatus, 3000);
</script>
</body>
</html>
"""


@app.get("/")
def index():
    error = request.args.get("error", "")
    with STATE_LOCK:
        _refresh_state()
        params = dict(STATE.params)
        log_content = ""
        if STATE.log_path:
            log_content = _read_log_tail(Path(STATE.log_path))
    return render_template_string(
        PAGE_TEMPLATE,
        state=STATE,
        params=params,
        error=error,
        log_content=log_content,
    )


@app.post("/start")
def start():
    url = _normalize_url(request.form.get("url", ""))
    if not url:
        return redirect(url_for("index", error="URL is required."))

    params = {
        "url": url,
        "package": (request.form.get("package", "") or "").strip(),
        "quantity": _parse_int(request.form.get("quantity", "1"), 1, 1, 6),
        "refresh": _parse_float(request.form.get("refresh", "3"), 3.0, 0.5, 30.0),
        "max_attempts": _parse_int(request.form.get("max_attempts", "500"), 500, 1, 5000),
        "headless": request.form.get("headless") == "on",
        "debugger": (request.form.get("debugger", "") or "").strip(),
        "user_data_dir": (request.form.get("user_data_dir", "") or "").strip(),
        "open_new_tab": request.form.get("open_new_tab") == "on",
        "debug": request.form.get("debug") == "on",
        "auto_checkout": request.form.get("auto_checkout") == "on",
    }

    error = _start_bot(params)
    if error:
        return redirect(url_for("index", error=error))
    return redirect(url_for("index"))


@app.post("/stop")
def stop():
    error = _stop_bot()
    if error:
        return redirect(url_for("index", error=error))
    return redirect(url_for("index"))


@app.get("/status")
def status():
    with STATE_LOCK:
        _refresh_state()
        started = STATE.started_at.strftime("%Y-%m-%d %H:%M:%S") if STATE.started_at else ""
        stopped = STATE.stopped_at.strftime("%Y-%m-%d %H:%M:%S") if STATE.stopped_at else ""
        payload = {
            "status": STATE.status,
            "started_at": started,
            "stopped_at": stopped,
            "error": STATE.error,
            "params": STATE.params,
        }
    return jsonify(payload)


@app.get("/log")
def log_tail():
    with STATE_LOCK:
        if STATE.log_path:
            return _read_log_tail(Path(STATE.log_path))
    return ""


@app.post("/chrome/launch")
def launch_chrome():
    error = _launch_chrome_debugger()
    if error:
        return redirect(url_for("index", error=error))
    return redirect(url_for("index"))


@app.post("/chrome/stop")
def stop_chrome():
    error = _stop_chrome_debugger()
    if error:
        return redirect(url_for("index", error=error))
    return redirect(url_for("index"))


@app.get("/chrome/status")
def chrome_status():
    with STATE_LOCK:
        is_running = _is_chrome_debugger_running()
        STATE.chrome_debugger_running = is_running
        return jsonify({"running": is_running})


if __name__ == "__main__":
    port = os.environ.get("PANEL_TIKET_PORT", "").strip()
    if not port:
        if sys.platform == "darwin":
            port = "5051"
        else:
            port = "5001"
    app.run(host="127.0.0.1", port=int(port), debug=False)

import os
import signal
import socket
import subprocess
import sys
import threading
import time
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from threading import Lock

from flask import Flask, jsonify, redirect, render_template_string, request, url_for, Response

app = Flask(__name__)

# --- CONFIG ---
BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_BASE_DIR = Path("C:/selenium")

GLOBAL_LOCK = Lock()

# --- DATA STRUCTURES ---

@dataclass
class BotConfig:
    url: str = "https://www.tiket.com/id-id/to-do/one-ok-rock-detox-tour-2026/packages"
    package: str = "CAT 1"
    quantity: int = 1
    refresh: float = 3.0
    max_attempts: int = 1000
    headless: bool = False
    open_new_tab: bool = True
    auto_checkout: bool = True
    debug: bool = False

@dataclass
class BotInstance:
    id: str
    name: str = "Bot Instance"
    port: int = 9222
    profile_dir: str = ""
    
    # State
    status: str = "idle" # idle, running, stopping, finished, error
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None
    error_msg: str = ""
    
    # Config
    config: BotConfig = field(default_factory=BotConfig)
    
    # Runtime (Not serializable)
    _process: Optional[subprocess.Popen] = None
    _log_file: Optional[str] = None
    _log_handle: Optional[Any] = None

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "port": self.port,
            "profile_dir": self.profile_dir,
            "status": self.status,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "error_msg": self.error_msg,
            "config": asdict(self.config)
        }

# --- GLOBAL STORE ---
class BotManager:
    def __init__(self):
        self.bots: Dict[str, BotInstance] = {}
        # Create default bot
        self.add_bot("Akun Utama", 9222)

    def add_bot(self, name: str, port: int) -> BotInstance:
        bot_id = str(uuid.uuid4())[:8]
        profile_name = f"ChromeProfile_{port}"
        if port == 9222:
             profile_name = "ChromeProfile" # Keep backward compatibility for main
        
        instance = BotInstance(
            id=bot_id,
            name=name,
            port=port,
            profile_dir=str(PROFILE_BASE_DIR / profile_name)
        )
        self.bots[bot_id] = instance
        return instance

    def get_bot(self, bot_id: str) -> Optional[BotInstance]:
        return self.bots.get(bot_id)
    
    def remove_bot(self, bot_id: str):
        if bot_id in self.bots:
            del self.bots[bot_id]

MANAGER = BotManager()

# --- HELPER FUNCTIONS ---

def _find_chrome_path() -> Optional[str]:
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

def _is_port_open(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(0.5)
        result = sock.connect_ex(("127.0.0.1", port))
        return result == 0
    except:
        return False
    finally:
        sock.close()

def _read_log_tail(path_str: str, max_bytes: int = 30000) -> str:
    path = Path(path_str)
    if not path.exists():
        return ""
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            if size > max_bytes:
                f.seek(size - max_bytes)
            data = f.read()
            return data.decode("utf-8", errors="replace")
    except Exception:
        return ""

# --- CORE LOGIC ---

def launch_uptime_checker():
    """Background thread to monitor bot processes"""
    while True:
        with GLOBAL_LOCK:
            for bot in MANAGER.bots.values():
                if bot._process:
                    code = bot._process.poll()
                    if code is not None:
                        # Process finished
                        if bot.status == "stopping":
                            bot.status = "stopped"
                        elif code == 0:
                            bot.status = "finished"
                        else:
                            bot.status = "error"
                            bot.error_msg = f"Exited with code {code}"
                        
                        bot.stopped_at = datetime.now().strftime("%H:%M:%S")
                        bot._process = None
                        if bot._log_handle:
                            try:
                                bot._log_handle.close()
                            except: pass
                            bot._log_handle = None
        time.sleep(1)

def start_bot_process(bot: BotInstance) -> str:
    if bot._process and bot._process.poll() is None:
        return "Bot already running"
    
    # Check if Chrome is running
    if not _is_port_open(bot.port):
        return f"Chrome (Port {bot.port}) is NOT running! Please launch Chrome first."

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"bot_{bot.port}_{timestamp}.log"
    log_path = LOG_DIR / log_filename
    
    cmd = [
        sys.executable,
        str(BASE_DIR / "auto_buy.py"),
        "--url", bot.config.url,
        "--package", bot.config.package,
        "--quantity", str(bot.config.quantity),
        "--refresh", str(bot.config.refresh),
        "--max-attempts", str(bot.config.max_attempts),
        "--debugger", f"127.0.0.1:{bot.port}",
        "--user-data-dir", bot.profile_dir
    ]
    
    if bot.config.open_new_tab:
        cmd.append("--open-new-tab")
    if not bot.config.headless: # Note: auto_buy.py argument logic might be reverse, but typically 'headless' param depends on implementation
        cmd.append("--no-headless")
    if not bot.config.auto_checkout:
        cmd.append("--no-auto-checkout")
    if bot.config.debug:
        cmd.append("--debug")
    
    # IMPORTANT: Force non-interactive for panel usage
    cmd.append("--non-interactive")

    try:
        f = log_path.open("a", encoding="utf-8")
        proc = subprocess.Popen(
            cmd,
            stdout=f,
            stderr=f,
            cwd=str(BASE_DIR),
            env=os.environ.copy()
        )
        bot._process = proc
        bot._log_handle = f
        bot._log_file = str(log_path)
        
        bot.status = "running"
        bot.started_at = datetime.now().strftime("%H:%M:%S")
        bot.stopped_at = None
        bot.error_msg = ""
        return ""
    except Exception as e:
        return str(e)

def stop_bot_process(bot: BotInstance) -> str:
    if not bot._process:
        return "Bot not running"
    
    bot.status = "stopping"
    try:
        bot._process.terminate()
    except: pass
    return ""

def launch_chrome_process(bot: BotInstance) -> str:
    if _is_port_open(bot.port):
        return "Chrome is already running/port active."
    
    chrome_exe = _find_chrome_path()
    if not chrome_exe:
        return "Chrome executable not found"
        
    profile = Path(bot.profile_dir)
    profile.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        chrome_exe,
        f"--remote-debugging-port={bot.port}",
        f"--user-data-dir={profile}"
    ]
    
    try:
        subprocess.Popen(
            cmd,
            # Detach process so it survives script restart
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return ""
    except Exception as e:
        return str(e)


# --- TEMPLATE ---

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Tiket.com Multi-Bot Manager</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root {
            --bg: #f8fafc;
            --surface: #ffffff;
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --danger: #ef4444;
            --success: #22c55e;
            --border: #e2e8f0;
            --text: #0f172a;
            --text-muted: #64748b;
        }
        body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        h1 { font-size: 24px; font-weight: 700; margin: 0; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 24px; }
        
        .card { background: var(--surface); border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); overflow: hidden; }
        .card-header { padding: 16px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: #f1f5f9; }
        .bot-name { font-weight: 600; font-size: 16px; display: flex; align-items: center; gap: 8px; }
        .badge { padding: 4px 8px; border-radius: 99px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
        
        .status-idle { background: #e2e8f0; color: #475569; }
        .status-running { background: #dcfce7; color: #15803d; }
        .status-stopping { background: #fef9c3; color: #a16207; }
        .status-error { background: #fee2e2; color: #b91c1c; }
        
        .card-body { padding: 16px; }
        
        .control-group { margin-bottom: 16px; padding: 12px; background: #f8fafc; border-radius: 8px; border: 1px solid var(--border); }
        .control-title { font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 8px; display: block; }
        
        .row { display: flex; gap: 12px; align-items: center; margin-bottom: 8px; }
        .col { flex: 1; }
        
        label { display: block; font-size: 12px; margin-bottom: 4px; color: var(--text-muted); }
        input[type="text"], input[type="number"] { width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; box-sizing: border-box; }
        
        .chrome-status { font-size: 13px; display: flex; align-items: center; gap: 6px; }
        .dot { width: 8px; height: 8px; border-radius: 50%; background: #ccc; }
        .dot.active { background: var(--success); }
        
        .btn { border: none; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; transition: 0.1s; }
        .btn-primary { background: var(--primary); color: white; }
        .btn-primary:hover { background: var(--primary-dark); }
        .btn-danger { background: var(--danger); color: white; }
        .btn-sm { padding: 4px 8px; font-size: 11px; }
        .btn-outline { background: transparent; border: 1px solid var(--border); color: var(--text); }
        .btn-outline:hover { background: #f1f5f9; }
        
        .log-box { height: 150px; background: #0f172a; color: #e2e8f0; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 11px; overflow-y: auto; white-space: pre-wrap; margin-top: 16px; }
        
        .actions { display: flex; gap: 8px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border); }
        
        .add-btn { position: fixed; bottom: 30px; right: 30px; width: 56px; height: 56px; border-radius: 50%; background: var(--primary); color: white; border: none; font-size: 24px; box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3); cursor: pointer; z-index: 100; display: flex; align-items: center; justify-content: center; }
        .add-btn:hover { transform: scale(1.05); }
    </style>
</head>
<body>

<div class="container">
    <header>
        <div>
            <h1>🤖 Tiket.com Bot Commander</h1>
            <p style="color: var(--text-muted); margin: 4px 0 0;">Manage multiple accounts simultaneously</p>
        </div>
        <div id="clock" style="font-family: monospace; font-size: 16px;">--:--:--</div>
    </header>

    <div id="bot-grid" class="grid">
        <!-- Bot Cards injected here -->
    </div>
</div>

<button class="add-btn" onclick="addNewBot()" title="Add New Bot Instance">+</button>

<script>
    const API_BASE = "";

    function renderBotCard(bot) {
        const isRunning = bot.status === 'running';
        const statusClass = `status-${bot.status}`;
        
        // Form values
        const conf = bot.config;
        
        return `
        <div class="card" id="card-${bot.id}">
            <div class="card-header">
                <div class="bot-name">
                    <span>${bot.name}</span>
                    <span class="badge ${statusClass}">${bot.status}</span>
                </div>
                <div>
                   <span style="font-size:11px; color:#94a3b8; margin-right:8px;">Port: ${bot.port}</span>
                   <button class="btn btn-sm btn-outline btn-danger" onclick="deleteBot('${bot.id}')">✕</button>
                </div>
            </div>
            <div class="card-body">
                <!-- Chrome Control -->
                <div class="control-group">
                    <span class="control-title">1. Browser Session</span>
                    <div class="row">
                        <div class="col chrome-status" id="chrome-status-${bot.id}">
                            <div class="dot"></div>
                            <span>Checking...</span>
                        </div>
                        <button class="btn btn-sm btn-outline" onclick="launchChrome('${bot.id}')">Launch Chrome</button>
                    </div>
                     <div style="font-size:11px; color:var(--text-muted);">Profile: .../${bot.profile_dir.split('/').pop()}</div>
                </div>

                <!-- Config -->
                <form id="form-${bot.id}" onsubmit="return false;">
                    <div class="control-group">
                        <span class="control-title">2. Target Configuration</span>
                        <div style="margin-bottom:8px;">
                            <label>Event Packages URL</label>
                            <input type="text" name="url" value="${conf.url}" placeholder="https://..." ${isRunning ? 'disabled' : ''}>
                        </div>
                        <div class="row">
                            <div class="col">
                                <label>Package Name</label>
                                <input type="text" name="package" value="${conf.package}" placeholder="CAT 1" ${isRunning ? 'disabled' : ''}>
                            </div>
                            <div class="col" style="flex:0.5;">
                                <label>Qty</label>
                                <input type="number" name="quantity" value="${conf.quantity}" min="1" max="10" ${isRunning ? 'disabled' : ''}>
                            </div>
                        </div>
                    </div>
                </form>

                <!-- Actions -->
                <div class="actions">
                    ${isRunning ? 
                        `<button class="btn btn-danger" style="flex:1;" onclick="stopBot('${bot.id}')">STOP BOT</button>` :
                        `<button class="btn btn-primary" style="flex:1;" onclick="startBot('${bot.id}')">START AUTO-BUY</button>`
                    }
                </div>

                <!-- Log -->
                <div class="log-box" id="log-${bot.id}">Waiting for logs...</div>
            </div>
        </div>
        `;
    }

    async function refreshData() {
        try {
            const res = await fetch('/api/bots');
            const bots = await res.json();
            const grid = document.getElementById('bot-grid');
            
            // Should verify diff to avoid full re-render flickering, but for now simple innerHTML
            // We save focus/input states if needed, but simple re-render is safer for sync
            
            // To prevent input loss while typing, we only update if status changed OR if it's first load
            // A better way is to update DOM elements individually.
            
            // IMPLEMENTATION: Update elements in place
            
            Object.values(bots).forEach(bot => {
                let card = document.getElementById(`card-${bot.id}`);
                if (!card) {
                    // New card
                    const div = document.createElement('div');
                    div.innerHTML = renderBotCard(bot);
                    grid.appendChild(div.firstElementChild);
                    card = document.getElementById(`card-${bot.id}`);
                } else {
                    // Update Status Badge
                    const badge = card.querySelector('.badge');
                    badge.className = `badge status-${bot.status}`;
                    badge.textContent = bot.status;
                    
                    // Update Buttons (Start/Stop) logic
                    const actionContainer = card.querySelector('.actions');
                    const isRunning = bot.status === 'running' || bot.status === 'stopping';
                    const btnHtml = isRunning ? 
                        `<button class="btn btn-danger" style="flex:1;" onclick="stopBot('${bot.id}')">STOP BOT</button>` :
                        `<button class="btn btn-primary" style="flex:1;" onclick="startBot('${bot.id}')">START AUTO-BUY</button>`;
                    
                    if (actionContainer.innerHTML.trim() !== btnHtml.trim()) {
                         actionContainer.innerHTML = btnHtml;
                         // Also toggle inputs disabled
                         const inputs = card.querySelectorAll('input');
                         inputs.forEach(inp => inp.disabled = isRunning);
                    }
                }
                
                // Update Log
                updateLog(bot.id);
                // Update Chrome Status
                checkChrome(bot.id);
            });
            
            // Remove deleted bots
            const currentIds = Object.keys(bots);
            const cards = document.querySelectorAll('.card');
            cards.forEach(c => {
                const id = c.id.replace('card-', '');
                if (!currentIds.includes(id)) c.remove();
            });

        } catch (e) {
            console.error(e);
        }
    }

    async function updateLog(botId) {
        const logBox = document.getElementById(`log-${botId}`);
        if (!logBox) return;
        try {
            const res = await fetch(`/api/bot/${botId}/log`);
            const text = await res.text();
            if (text && logBox.textContent.length !== text.length) {
                logBox.textContent = text;
                logBox.scrollTop = logBox.scrollHeight;
            }
        } catch(e) {}
    }

    async function checkChrome(botId) {
        const el = document.getElementById(`chrome-status-${botId}`);
        if (!el) return;
        try {
            const res = await fetch(`/api/bot/${botId}/chrome_status`);
            const json = await res.json();
            const dot = el.querySelector('.dot');
            const span = el.querySelector('span');
            if (json.running) {
                dot.classList.add('active');
                span.textContent = "Running";
            } else {
                dot.classList.remove('active');
                span.textContent = "Not Running";
            }
        } catch(e) {}
    }

    async function startBot(botId) {
        const form = document.getElementById(`form-${botId}`);
        const data = new FormData(form);
        const payload = Object.fromEntries(data.entries());
        
        await fetch(`/api/bot/${botId}/start`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        refreshData();
    }

    async function stopBot(botId) {
         await fetch(`/api/bot/${botId}/stop`, { method: 'POST' });
         refreshData();
    }

    async function launchChrome(botId) {
         await fetch(`/api/bot/${botId}/launch_chrome`, { method: 'POST' });
         // give it time to launch
         setTimeout(() => checkChrome(botId), 2000);
         alert("Chrome launching... Please wait & Login manually.");
    }

    async function addNewBot() {
        const name = prompt("Enter Name for new Bot Instance (e.g. Account 2):", "New Account");
        if (name) {
            await fetch('/api/bots/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: name})
            });
            refreshData();
        }
    }
    
    async function deleteBot(botId) {
        if(confirm("Delete this bot instance?")) {
            await fetch(`/api/bot/${botId}/delete`, { method: 'POST' });
            document.getElementById(`card-${botId}`).remove();
        }
    }

    // Clock
    setInterval(() => {
        document.getElementById('clock').textContent = new Date().toLocaleTimeString();
    }, 1000);

    // Initial load
    refreshData();
    setInterval(refreshData, 2000);

</script>
</body>
</html>
"""

# --- ROUTES ---

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/bots", methods=["GET"])
def get_bots():
    with GLOBAL_LOCK:
        return jsonify({k: v.to_dict() for k,v in MANAGER.bots.items()})

@app.route("/api/bots/add", methods=["POST"])
def add_bot():
    data = request.json
    name = data.get("name", "New Bot")
    # Find next available port starting 9222
    with GLOBAL_LOCK:
        existing_ports = [b.port for b in MANAGER.bots.values()]
        new_port = 9222
        while new_port in existing_ports:
            new_port += 1
        
        MANAGER.add_bot(name, new_port)
    return jsonify({"status": "ok", "port": new_port})

@app.route("/api/bot/<bot_id>/start", methods=["POST"])
def api_start_bot(bot_id):
    with GLOBAL_LOCK:
        bot = MANAGER.get_bot(bot_id)
        if not bot: return jsonify({"error": "Bot not found"}), 404
        
        # Update config from payload
        data = request.json
        bot.config.url = data.get("url", bot.config.url)
        bot.config.package = data.get("package", bot.config.package)
        bot.config.quantity = int(data.get("quantity", bot.config.quantity))
        
        err = start_bot_process(bot)
        if err: return jsonify({"status": "error", "message": err})
        return jsonify({"status": "started"})

@app.route("/api/bot/<bot_id>/stop", methods=["POST"])
def api_stop_bot(bot_id):
    with GLOBAL_LOCK:
        bot = MANAGER.get_bot(bot_id)
        if not bot: return jsonify({"error": "Bot not found"}), 404
        stop_bot_process(bot)
        return jsonify({"status": "stopping"})

@app.route("/api/bot/<bot_id>/delete", methods=["POST"])
def api_delete_bot(bot_id):
    with GLOBAL_LOCK:
        MANAGER.remove_bot(bot_id)
    return jsonify({"status": "deleted"})

@app.route("/api/bot/<bot_id>/launch_chrome", methods=["POST"])
def api_launch_chrome(bot_id):
    with GLOBAL_LOCK:
        bot = MANAGER.get_bot(bot_id)
        if not bot: return jsonify({"error": "Bot not found"}), 404
        err = launch_chrome_process(bot)
        if err: return jsonify({"status": "error", "message": err})
        return jsonify({"status": "launched"})

@app.route("/api/bot/<bot_id>/log", methods=["GET"])
def api_bot_log(bot_id):
    # No lock needed for read
    bot = MANAGER.get_bot(bot_id)
    if not bot or not bot._log_file: return ""
    return _read_log_tail(bot._log_file)

@app.route("/api/bot/<bot_id>/chrome_status", methods=["GET"])
def api_chrome_status(bot_id):
    bot = MANAGER.get_bot(bot_id)
    if not bot: return jsonify({"running": False})
    return jsonify({"running": _is_port_open(bot.port)})

# --- MAIN ---

if __name__ == "__main__":
    # Start background monitor
    t = threading.Thread(target=launch_uptime_checker, daemon=True)
    t.start()
    
    try:
        app.run(host="0.0.0.0", port=5001, debug=False)
    except Exception as e:
        print(f"Failed to start server: {e}")

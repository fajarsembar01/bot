#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

echo "Starting Ticketmaster panel..."

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python not found. Install Python 3 first."
  exit 1
fi

PORT="${PANEL_TICKETMASTER_PORT:-5002}"

$PY -m pip install -q -r "$ROOT_DIR/requirements.txt"
PANEL_TICKETMASTER_PORT="$PORT" $PY web_panel.py &

sleep 1
if command -v open >/dev/null 2>&1; then
  open http://127.0.0.1:$PORT
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open http://127.0.0.1:$PORT
else
  echo "Open browser to http://127.0.0.1:$PORT"
fi

wait

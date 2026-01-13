#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Cleaning old caches..."
rm -rf "$HOME/.wdm" "$HOME/.cache/selenium" "$HOME/Library/Caches/selenium" "logs"

echo "Starting panel..."
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python tidak ditemukan. Install Python 3 terlebih dahulu."
  exit 1
fi

PORT="${PANEL_PORT:-}"
if [ -z "$PORT" ]; then
  if [ "$(uname)" = "Darwin" ]; then
    PORT=5050
  else
    PORT=5000
  fi
fi

$PY -m pip install -q -r requirements.txt
PANEL_PORT="$PORT" $PY web_panel.py &

sleep 1
if command -v open >/dev/null 2>&1; then
  open http://127.0.0.1:$PORT
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open http://127.0.0.1:$PORT
else
  echo "Buka browser ke http://127.0.0.1:$PORT"
fi

wait

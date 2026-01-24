#!/bin/bash

echo "Ticketmaster Helper Bot"
echo "========================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

if [ -d "$ROOT_DIR/venv" ]; then
    echo "Activating virtual environment..."
    source "$ROOT_DIR/venv/bin/activate"
fi

echo "Installing dependencies..."
pip install -q -r "$ROOT_DIR/requirements.txt"

if [ ! -f ".env" ]; then
    echo "No .env found, creating from template..."
    cp env_template.txt .env
fi

echo "Starting bot..."
python3 bot_ticketmaster.py "$@"

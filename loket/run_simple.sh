#!/bin/bash

# Script untuk menjalankan bot sederhana

echo "🤖 Bot Pencari Tombol Loket.com (Simple)"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

# Cek apakah virtual environment ada (opsional)
if [ -d "$ROOT_DIR/venv" ]; then
    echo "🔧 Mengaktifkan virtual environment..."
    source "$ROOT_DIR/venv/bin/activate"
fi

# Install dependencies jika belum
echo "📥 Mengecek dependencies..."
python3 -m pip install -q -r "$ROOT_DIR/requirements.txt" 2>/dev/null || pip install -q -r "$ROOT_DIR/requirements.txt"

# Jalankan bot
echo "🚀 Menjalankan bot..."
echo ""
python3 bot_simple.py "$@"

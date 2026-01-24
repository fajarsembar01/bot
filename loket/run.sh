#!/bin/bash

# Script untuk menjalankan bot antrian Loket.com

echo "🤖 Bot Antrian Loket.com"
echo "========================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

# Cek apakah virtual environment ada
if [ ! -d "$ROOT_DIR/venv" ]; then
    echo "📦 Membuat virtual environment..."
    python3 -m venv "$ROOT_DIR/venv"
fi

# Aktifkan virtual environment
echo "🔧 Mengaktifkan virtual environment..."
source "$ROOT_DIR/venv/bin/activate"

# Install dependencies jika belum
echo "📥 Mengecek dependencies..."
pip install -q -r "$ROOT_DIR/requirements.txt"

# Cek file .env
if [ ! -f ".env" ]; then
    echo "⚠️  File .env tidak ditemukan!"
    echo "📝 Membuat file .env dari template..."
    cp env_template.txt .env
    echo "✅ File .env dibuat. Silakan edit jika perlu."
    echo ""
fi

# Jalankan bot
echo "🚀 Menjalankan bot..."
echo ""
python bot_loket.py "$@"

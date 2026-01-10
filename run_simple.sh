#!/bin/bash

# Script untuk menjalankan bot sederhana

echo "🤖 Bot Pencari Tombol Loket.com (Simple)"
echo "========================================"
echo ""

# Cek apakah virtual environment ada (opsional)
if [ -d "venv" ]; then
    echo "🔧 Mengaktifkan virtual environment..."
    source venv/bin/activate
fi

# Install dependencies jika belum
echo "📥 Mengecek dependencies..."
python3 -m pip install -q selenium webdriver-manager 2>/dev/null || pip install -q selenium webdriver-manager

# Jalankan bot
echo "🚀 Menjalankan bot..."
echo ""
python3 bot_simple.py "$@"


#!/bin/bash

# Script untuk menjalankan bot antrian Loket.com

echo "🤖 Bot Antrian Loket.com"
echo "========================"
echo ""

# Cek apakah virtual environment ada
if [ ! -d "venv" ]; then
    echo "📦 Membuat virtual environment..."
    python3 -m venv venv
fi

# Aktifkan virtual environment
echo "🔧 Mengaktifkan virtual environment..."
source venv/bin/activate

# Install dependencies jika belum
echo "📥 Mengecek dependencies..."
pip install -q -r requirements.txt

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


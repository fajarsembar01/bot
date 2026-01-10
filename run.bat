@echo off
REM Script untuk menjalankan bot antrian Loket.com (Windows)

echo 🤖 Bot Antrian Loket.com
echo ========================
echo.

REM Cek apakah virtual environment ada
if not exist "venv" (
    echo 📦 Membuat virtual environment...
    python -m venv venv
)

REM Aktifkan virtual environment
echo 🔧 Mengaktifkan virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies jika belum
echo 📥 Mengecek dependencies...
pip install -q -r requirements.txt

REM Cek file .env
if not exist ".env" (
    echo ⚠️  File .env tidak ditemukan!
    echo 📝 Membuat file .env dari template...
    copy env_template.txt .env
    echo ✅ File .env dibuat. Silakan edit jika perlu.
    echo.
)

REM Jalankan bot
echo 🚀 Menjalankan bot...
echo.
python bot_loket.py %*


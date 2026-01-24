# 🚀 Quick Start Guide

## Instalasi Cepat (macOS/Linux)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Opsional) Buat file .env (Loket)
cp loket/env_template.txt loket/.env
# Edit loket/.env sesuai kebutuhan

# 3. Jalankan bot
python loket/bot_loket.py
```

Atau gunakan script helper:
```bash
chmod +x loket/run.sh
./loket/run.sh
```

## Instalasi Cepat (Windows)

```cmd
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Opsional) Buat file .env (Loket)
copy loket\\env_template.txt loket\\.env
REM Edit loket\\.env sesuai kebutuhan

# 3. Jalankan bot
python loket\\bot_loket.py
```

Atau gunakan script helper:
```cmd
loket\\run.bat
```

## Contoh Penggunaan

### Contoh 1: URL Default (ateezinjakarta.com)
```bash
python loket/bot_loket.py
```

### Contoh 2: Custom URL
```bash
python loket/bot_loket.py --url https://loket.com/event/konser-xyz
```

### Contoh 3: Headless Mode
```bash
python loket/bot_loket.py --headless
```

## Yang Perlu Diperhatikan

1. ✅ Pastikan Chrome browser terinstall
2. ✅ Pastikan koneksi internet stabil
3. ✅ Login ke akun Loket.com terlebih dahulu (jika diminta)
4. ✅ Siapkan metode pembayaran
5. ✅ Jalankan bot 30-60 menit sebelum waktu penjualan

## Troubleshooting Cepat

**Error: ChromeDriver tidak ditemukan**
- Bot akan otomatis download, tapi pastikan Chrome terinstall

**Error: Module not found**
- Jalankan: `pip install -r requirements.txt`

**Bot tidak menemukan tombol waiting room**
- Pastikan waiting room sudah dibuka
- Cek URL konser apakah benar
- Coba refresh manual di browser

**Bot stuck**
- Ini normal, bot akan terus monitor sampai berhasil
- Pastikan tidak tutup browser

## Tips Sukses

- 🕐 Jalankan bot lebih awal (30-60 menit sebelum penjualan)
- 🌐 Gunakan koneksi internet yang cepat dan stabil
- 💻 Siapkan beberapa perangkat untuk meningkatkan peluang
- 💳 Siapkan data pembayaran sebelum mulai
- 📱 Jangan tutup browser setelah masuk waiting room

## Tiket.com Auto-buy (Beta)

```bash
python tiket/bot_tiket.py \
  --url "https://www.tiket.com/id-id/to-do/one-ok-rock-detox-tour-2026/packages" \
  --package "CAT 1" \
  --quantity 2
```

Jika muncul challenge/login, selesaikan manual di browser, lalu lanjutkan bot.

## Web Panel Tiket.com (Separate)

macOS/Linux:
```bash
./tiket/run_panel_tiket.sh
```

Windows:
```cmd
tiket\\run_panel_tiket.bat
```

## Ticketmaster Simple

```bash
python ticketmaster/bot_ticketmaster.py \
  --url "https://ticketmaster.sg/ticket/area/26sg_ateez/2978" \
  --button "Buy"
```

macOS/Linux:
```bash
./ticketmaster/run_ticketmaster.sh
```

Windows:
```cmd
ticketmaster\\run_ticketmaster.bat
```

## Web Panel Ticketmaster

macOS/Linux:
```bash
./ticketmaster/run_panel_ticketmaster.sh
```

Windows:
```cmd
ticketmaster\\run_panel_ticketmaster.bat
```

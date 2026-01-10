# 🚀 Quick Start Guide

## Instalasi Cepat (macOS/Linux)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Opsional) Buat file .env
cp env_template.txt .env
# Edit .env sesuai kebutuhan

# 3. Jalankan bot
python bot_loket.py
```

Atau gunakan script helper:
```bash
chmod +x run.sh
./run.sh
```

## Instalasi Cepat (Windows)

```cmd
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Opsional) Buat file .env
copy env_template.txt .env
REM Edit .env sesuai kebutuhan

# 3. Jalankan bot
python bot_loket.py
```

Atau gunakan script helper:
```cmd
run.bat
```

## Contoh Penggunaan

### Contoh 1: URL Default (ateezinjakarta.com)
```bash
python bot_loket.py
```

### Contoh 2: Custom URL
```bash
python bot_loket.py --url https://loket.com/event/konser-xyz
```

### Contoh 3: Headless Mode
```bash
python bot_loket.py --headless
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


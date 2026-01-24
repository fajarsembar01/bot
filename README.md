# 🤖 Bot Loket.com + Tiket.com + Ticketmaster

Bot otomatis untuk Loket.com (waiting room/antrian), Tiket.com (auto-buy paket), dan Ticketmaster (simple auto-click).

## 📦 Bot Tersedia

### 1. **loket/bot_simple.py** ⭐ RECOMMENDED (Lebih Mudah)
- Bot sederhana dan mudah digunakan
- Refresh halaman setiap 3 detik
- Mencari tombol berdasarkan text yang Anda masukkan
- Input parameter saat running (link konser + text tombol)
- **Cocok untuk pemula!**

📖 **Lihat panduan**: [loket/docs/CARA_PAKAI_SIMPLE.md](loket/docs/CARA_PAKAI_SIMPLE.md)

### 2. **loket/bot_loket.py** (Advanced)
- Bot dengan fitur lengkap
- Auto-detect widget Loket
- Support multiple method detection
- Konfigurasi via file `.env`

📖 **Lihat panduan**: [loket/docs/CARA_PAKAI.md](loket/docs/CARA_PAKAI.md)

### 3. **tiket/bot_tiket.py** (Tiket.com Auto-buy - Beta)
- Auto pilih paket berdasarkan nama
- Auto set quantity dan lanjut ke checkout
- Cocok untuk halaman packages Tiket.com

### 4. **ticketmaster/bot_ticketmaster.py** (Ticketmaster Simple)
- Refresh halaman dan cari tombol berdasarkan text
- Bisa auto-click + auto-buy sederhana (quantity + checkout)
- Support session baru (profil terpisah) di tab baru



## 📋 Persyaratan

- Python 3.8 atau lebih baru
- Chrome/Chromium browser terinstall
- Koneksi internet yang stabil

## 🚀 Instalasi

1. **Clone atau download repository ini**

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Setup environment variables:**

Loket:
```bash
cp loket/env_template.txt loket/.env
```

Tiket.com:
```bash
cp tiket/env_template.txt tiket/.env
```

Ticketmaster:
```bash
cp ticketmaster/env_template.txt ticketmaster/.env
```

## 🗂️ Struktur Project

- `loket/` - bot Loket.com (simple + advanced + panel)
- `loket/docs/` - panduan Loket.com
- `tiket/` - bot Tiket.com (auto-buy + panel)
- `ticketmaster/` - bot Ticketmaster (monitoring helper)

## 💻 Quick Start (Bot Sederhana - RECOMMENDED)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Jalankan bot sederhana
python3 loket/bot_simple.py

# 3. Input parameter:
#    - Link konser: https://ateezinjakarta.com/
#    - Text tombol: Beli Tiket
```

Bot akan:
- ✅ Refresh halaman setiap 3 detik
- ✅ Mencari tombol dengan text "Beli Tiket"
- ✅ Memberi notifikasi jika tombol ditemukan (enabled/disabled)
- ✅ Otomatis klik jika tombol sudah enabled

**📖 Panduan lengkap**: Lihat [loket/docs/CARA_PAKAI_SIMPLE.md](loket/docs/CARA_PAKAI_SIMPLE.md)

## 💻 Quick Start (Tiket.com Auto-buy)

```bash
# Contoh auto-buy paket
python3 tiket/bot_tiket.py \\
  --url "https://www.tiket.com/id-id/to-do/one-ok-rock-detox-tour-2026/packages" \\
  --package "CAT 1" \\
  --quantity 2
```

Jika muncul challenge/login, selesaikan manual di browser, lalu lanjutkan bot.

Script helper:
- macOS/Linux: `./tiket/run_tiket.sh`
- Windows: `tiket\\run_tiket.bat`

## 💻 Quick Start (Ticketmaster Simple)

```bash
python3 ticketmaster/bot_ticketmaster.py \\
  --url "https://ticketmaster.sg/ticket/area/26sg_ateez/2978" \\
  --button "Buy"
```

Script helper:
- macOS/Linux: `./ticketmaster/run_ticketmaster.sh`
- Windows: `ticketmaster\\run_ticketmaster.bat`

## Web Panel Ticketmaster

macOS/Linux:
```bash
./ticketmaster/run_panel_ticketmaster.sh
```

Windows:
```cmd
ticketmaster\\run_panel_ticketmaster.bat
```

Default port: `http://127.0.0.1:5002` (override with `PANEL_TICKETMASTER_PORT`).

## Web Panel (Recommended untuk Staff)

Panel web memudahkan staff menjalankan bot tanpa perlu input di terminal.

Windows:
```bash
loket\\run_panel.bat
```

macOS/Linux:
```bash
chmod +x loket/run_panel.sh
./loket/run_panel.sh
```

Setelah panel jalan, buka `http://127.0.0.1:5000`, isi URL + button text, lalu klik **Start Bot**.

Jika Chrome tidak ditemukan, set environment `CHROME_PATH` ke lokasi Chrome/Chromium Anda.

## Web Panel Tiket.com (Separate)

Panel Tiket.com dipisah karena flow dan struktur halaman berbeda.

Windows:
```bash
tiket\\run_panel_tiket.bat
```

macOS/Linux:
```bash
chmod +x tiket/run_panel_tiket.sh
./tiket/run_panel_tiket.sh
```

Default port: `http://127.0.0.1:5001` (macOS gunakan 5051). Bisa override lewat `PANEL_TIKET_PORT`.

## 💻 Cara Menggunakan Bot Advanced (loket/bot_loket.py)

### Cara 1: Basic Usage
```bash
python loket/bot_loket.py
```

Bot akan menggunakan URL dari file `.env` (default: ateezinjakarta.com)

### Cara 2: Custom URL
```bash
python loket/bot_loket.py --url https://ateezinjakarta.com/
```

### Cara 3: Headless Mode (browser tidak terlihat)
```bash
python loket/bot_loket.py --headless
```

### Cara 4: Browser Terlihat (explicit)
```bash
python loket/bot_loket.py --no-headless
```

## 📝 Langkah-langkah Penggunaan

1. **Persiapkan Akun Loket.com:**
   - Pastikan sudah punya akun Loket.com
   - Login ke akun Anda di browser biasa untuk memastikan tidak ada masalah
   - Siapkan metode pembayaran

2. **Jalankan Bot:**
   ```bash
   python loket/bot_loket.py
   ```

3. **Jika Perlu Login:**
   - Bot akan mendeteksi jika perlu login
   - Login manual di browser yang terbuka
   - Tekan Enter di terminal untuk melanjutkan

4. **Bot akan:**
   - Otomatis refresh halaman untuk mencari waiting room
   - Masuk ke waiting room begitu tersedia
   - Monitor status antrian
   - Memberi notifikasi ketika berhasil masuk ke halaman pembelian

5. **Setelah Berhasil:**
   - Bot akan memberikan notifikasi
   - Selesaikan pembelian tiket secara manual di browser
   - Jangan tutup browser sampai pembelian selesai

## 🎯 Tips untuk Sukses

1. **Jalankan Bot Lebih Awal:**
   - Mulai bot 30-60 menit sebelum waktu penjualan
   - Waiting room biasanya dibuka 10-30 menit sebelum penjualan

2. **Gunakan Koneksi Internet Stabil:**
   - Gunakan koneksi WiFi atau kabel yang stabil
   - Hindari VPN yang memperlambat koneksi

3. **Siapkan Beberapa Perangkat (Opsional):**
   - Jalankan bot di beberapa perangkat berbeda
   - Ini dapat meningkatkan peluang masuk antrian

4. **Jangan Tutup Browser:**
   - Setelah masuk waiting room, jangan refresh atau tutup browser
   - Tunggu sampai bot memberi notifikasi berhasil

5. **Persiapkan Data Pembayaran:**
   - Siapkan kartu kredit/debit atau metode pembayaran lain
   - Pastikan saldo/cukup limit
   - Siapkan data diri yang diperlukan

## ⚙️ Konfigurasi

Loket config ada di `loket/config.py`, Tiket config ada di `tiket/config.py`, Ticketmaster config ada di `ticketmaster/config.py`.
Anda juga bisa menggunakan file `.env` di masing-masing folder:

Loket:
- `CONCERT_URL`: URL konser yang ingin dibeli
- `HEADLESS`: True/False untuk mode headless
- `WAIT_TIME`: Waktu tunggu sebelum refresh (detik)
- `START_MONITORING_TIME`: Waktu mulai monitoring (format: HH:MM)
- File: `loket/.env`

Tiket.com:
- `TIKET_URL`: URL packages Tiket.com
- `TIKET_PACKAGE`: Nama paket (partial match)
- `TIKET_QUANTITY`: Jumlah tiket
- `TIKET_HEADLESS`: True/False untuk mode headless
- `TIKET_REFRESH_SECONDS`: Interval refresh
- `TIKET_MAX_ATTEMPTS`: Batas percobaan
- File: `tiket/.env`

Ticketmaster:
- `TICKETMASTER_URL`: URL event Ticketmaster
- `TICKETMASTER_BUTTON_TEXT`: Text tombol yang dicari
- `TICKETMASTER_AUTO_BUY`: True/False untuk auto-buy sederhana
- `TICKETMASTER_QUANTITY`: Jumlah tiket
- `TICKETMASTER_HEADLESS`: True/False untuk mode headless
- `TICKETMASTER_REFRESH_SECONDS`: Interval refresh
- `TICKETMASTER_MAX_ATTEMPTS`: Batas percobaan
- `TICKETMASTER_OPEN_NEW_TAB`: Buka target di tab baru
- `TICKETMASTER_NEW_SESSION`: Gunakan profil Chrome baru
- `TICKETMASTER_USER_DATA_DIR`: Profil custom (opsional)
- File: `ticketmaster/.env`

## 🔧 Troubleshooting

### Bot tidak menemukan tombol waiting room
- Pastikan waiting room sudah dibuka
- Cek apakah URL benar
- Coba refresh manual di browser

### Error ChromeDriver
- Bot akan otomatis download ChromeDriver
- Pastikan Chrome browser terinstall
- Jika masih error, coba update Chrome ke versi terbaru

### Browser tidak terbuka
- Coba jalankan tanpa `--headless`
- Cek apakah Chrome terinstall dengan benar
- Pastikan tidak ada masalah permission

### Bot stuck di monitoring
- Ini normal, bot akan terus monitor sampai berhasil
- Pastikan koneksi internet stabil
- Cek terminal untuk status update

## 📸 Screenshot

Bot akan otomatis mengambil screenshot setiap 30 detik untuk monitoring. Screenshot disimpan sebagai `screenshot_YYYYMMDD_HHMMSS.png`

## ⚠️ Disclaimer

- Bot ini dibuat untuk tujuan edukasi dan membantu proses yang legal
- Penggunaan bot adalah tanggung jawab pengguna
- Developer tidak bertanggung jawab atas segala konsekuensi penggunaan bot ini
- Pastikan mematuhi Terms of Service dari Loket.com, Tiket.com, dan Ticketmaster

## 📞 Support

Jika ada masalah atau pertanyaan, silakan buat issue di repository ini.

## 📄 License

MIT License - bebas digunakan untuk keperluan pribadi.

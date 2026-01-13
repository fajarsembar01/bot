# 🤖 Bot Antrian Loket.com

Bot otomatis untuk membantu mendapatkan antrian awal di Loket.com dengan sistem LOKET Antrean.

## 📦 Ada 2 Bot Tersedia

### 1. **bot_simple.py** ⭐ RECOMMENDED (Lebih Mudah)
- Bot sederhana dan mudah digunakan
- Refresh halaman setiap 3 detik
- Mencari tombol berdasarkan text yang Anda masukkan
- Input parameter saat running (link konser + text tombol)
- **Cocok untuk pemula!**

📖 **Lihat panduan**: [CARA_PAKAI_SIMPLE.md](CARA_PAKAI_SIMPLE.md)

### 2. **bot_loket.py** (Advanced)
- Bot dengan fitur lengkap
- Auto-detect widget Loket
- Support multiple method detection
- Konfigurasi via file `.env`

📖 **Lihat panduan**: [CARA_PAKAI.md](CARA_PAKAI.md)

## ⚠️ PENTING

- Bot ini adalah alat bantu untuk otomatisasi proses yang dapat dilakukan secara manual
- Gunakan dengan bijak dan bertanggung jawab
- Pastikan Anda mematuhi Terms of Service Loket.com
- Bot ini hanya membantu memasuki waiting room, pembelian tiket tetap harus dilakukan manual

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
```bash
cp .env.example .env
```

Edit file `.env` dan sesuaikan dengan kebutuhan:
```env
CONCERT_URL=https://ateezinjakarta.com/
HEADLESS=False
WAIT_TIME=5
```

## 💻 Quick Start (Bot Sederhana - RECOMMENDED)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Jalankan bot sederhana
python3 bot_simple.py

# 3. Input parameter:
#    - Link konser: https://ateezinjakarta.com/
#    - Text tombol: Beli Tiket
```

Bot akan:
- ✅ Refresh halaman setiap 3 detik
- ✅ Mencari tombol dengan text "Beli Tiket"
- ✅ Memberi notifikasi jika tombol ditemukan (enabled/disabled)
- ✅ Otomatis klik jika tombol sudah enabled

**📖 Panduan lengkap**: Lihat [CARA_PAKAI_SIMPLE.md](CARA_PAKAI_SIMPLE.md)


## Web Panel (Recommended untuk Staff)

Panel web memudahkan staff menjalankan bot tanpa perlu input di terminal.

Windows:
```bash
run_panel.bat
```

macOS/Linux:
```bash
chmod +x run_panel.sh
./run_panel.sh
```

Setelah panel jalan, buka `http://127.0.0.1:5000`, isi URL + button text, lalu klik **Start Bot**.

Jika Chrome tidak ditemukan, set environment `CHROME_PATH` ke lokasi Chrome/Chromium Anda.

## 💻 Cara Menggunakan Bot Advanced (bot_loket.py)

### Cara 1: Basic Usage
```bash
python bot_loket.py
```

Bot akan menggunakan URL dari file `.env` (default: ateezinjakarta.com)

### Cara 2: Custom URL
```bash
python bot_loket.py --url https://ateezinjakarta.com/
```

### Cara 3: Headless Mode (browser tidak terlihat)
```bash
python bot_loket.py --headless
```

### Cara 4: Browser Terlihat (explicit)
```bash
python bot_loket.py --no-headless
```

## 📝 Langkah-langkah Penggunaan

1. **Persiapkan Akun Loket.com:**
   - Pastikan sudah punya akun Loket.com
   - Login ke akun Anda di browser biasa untuk memastikan tidak ada masalah
   - Siapkan metode pembayaran

2. **Jalankan Bot:**
   ```bash
   python bot_loket.py
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

File `config.py` berisi konfigurasi default. Anda juga bisa menggunakan file `.env`:

- `CONCERT_URL`: URL konser yang ingin dibeli
- `HEADLESS`: True/False untuk mode headless
- `WAIT_TIME`: Waktu tunggu sebelum refresh (detik)
- `START_MONITORING_TIME`: Waktu mulai monitoring (format: HH:MM)

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
- Pastikan mematuhi Terms of Service dari Loket.com

## 📞 Support

Jika ada masalah atau pertanyaan, silakan buat issue di repository ini.

## 📄 License

MIT License - bebas digunakan untuk keperluan pribadi.


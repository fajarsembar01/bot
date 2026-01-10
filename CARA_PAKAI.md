# 📖 Cara Pakai Bot Antrian Loket.com

## Langkah 1: Install Dependencies (Hanya Pertama Kali)

```bash
pip install -r requirements.txt
```

**Atau jika error, coba:**
```bash
python3 -m pip install -r requirements.txt
```

## Langkah 2: Setup URL Konser (Opsional)

Bot sudah dikonfigurasi untuk **ateezinjakarta.com** secara default. 

Jika ingin ganti URL, edit file `.env` atau langsung pakai parameter:

```bash
python3 bot_loket.py --url https://loket.com/event/your-event
```

**Untuk membuat file .env:**
```bash
cp env_template.txt .env
# Lalu edit file .env sesuai kebutuhan
```

## Langkah 3: Jalankan Bot

### Cara Paling Mudah:
```bash
python3 bot_loket.py
```

### Dengan Custom URL:
```bash
python3 bot_loket.py --url https://ateezinjakarta.com/
```

### Dengan Widget URL Langsung (Jika sudah tahu URL widget Loket):
```bash
python3 bot_loket.py --widget https://widget.loket.com/widget/yqar4pcjnnmn6q9mxobc
```

**Cara mendapatkan URL widget:**
1. Buka halaman konser (contoh: ateezinjakarta.com)
2. Klik kanan pada tombol/link "Beli Tiket"
3. Pilih "Copy link address" atau "Salin alamat link"
4. Atau inspect element dan cari href yang mengandung "widget.loket.com"

### Mode Headless (Browser tidak terlihat):
```bash
python3 bot_loket.py --headless
```

### Atau pakai script helper:
```bash
chmod +x run.sh
./run.sh
```

## Langkah 4: Ikuti Instruksi di Terminal

Bot akan:
1. ✅ Membuka browser Chrome
2. ✅ Membuka halaman konser
3. ⏳ Otomatis mencari dan masuk ke waiting room
4. 👀 Monitor status antrian
5. 🎉 Memberi notifikasi ketika berhasil!

## Yang Harus Dilakukan Manual:

### Jika Diminta Login:
- Bot akan menunggu Anda login manual di browser
- Login dulu, lalu tekan **Enter** di terminal

### Setelah Berhasil Masuk Antrian:
- Bot akan memberi notifikasi
- **JANGAN TUTUP BROWSER!**
- Selesaikan pembelian tiket secara manual
- Siapkan data pembayaran dengan cepat

## Tips Penting:

1. **Waktu Terbaik**: Jalankan bot **30-60 menit** sebelum penjualan dimulai
2. **Koneksi Internet**: Pastikan WiFi/koneksi stabil
3. **Login Dulu**: Pastikan sudah punya akun Loket.com dan sudah login sebelumnya
4. **Siapkan Pembayaran**: Siapkan kartu/kartu kredit sebelum mulai
5. **Jangan Refresh**: Setelah masuk waiting room, jangan refresh browser manual

## Troubleshooting:

### Error "ChromeDriver not found"
- Bot akan otomatis download, tapi pastikan Chrome browser terinstall
- Download Chrome di: https://www.google.com/chrome/

### Error "Module not found"
```bash
python3 -m pip install -r requirements.txt
```

### Bot tidak menemukan tombol waiting room / link ke widget Loket
- **Solusi 1**: Gunakan URL widget langsung
  ```bash
  python3 bot_loket.py --widget https://widget.loket.com/widget/xxxxx
  ```
  Untuk mendapatkan URL widget:
  - Buka halaman konser di browser
  - Klik kanan pada tombol "Beli Tiket" → "Copy link address"
  - Atau inspect element (F12) dan cari href dengan "widget.loket.com"

- **Solusi 2**: Pastikan waiting room sudah dibuka (biasanya 10-30 menit sebelum penjualan)
- **Solusi 3**: Cek URL konser apakah benar
- **Solusi 4**: Coba refresh manual di browser sekali, lalu lihat apakah muncul link ke widget

### Browser tidak terbuka
- Jangan pakai `--headless` untuk pertama kali
- Cek apakah Chrome terinstall
- Coba restart terminal

## Contoh Penggunaan Lengkap:

```bash
# 1. Masuk ke folder bot
cd /Users/ainunfajar/botantrian

# 2. Install dependencies (hanya sekali)
pip install -r requirements.txt

# 3. Jalankan bot
python3 bot_loket.py

# 4. Jika perlu custom URL:
python3 bot_loket.py --url https://loket.com/event/konser-xyz

# 5. Atau langsung pakai widget URL (jika sudah tahu):
python3 bot_loket.py --widget https://widget.loket.com/widget/yqar4pcjnnmn6q9mxobc
```

## Catatan Penting:

⚠️ Bot ini membantu proses otomatis yang legal
⚠️ Pastikan patuh Terms of Service Loket.com  
⚠️ Gunakan dengan bijak dan bertanggung jawab

---

**Selamat mencoba! Semoga dapat tiketnya! 🎫✨**


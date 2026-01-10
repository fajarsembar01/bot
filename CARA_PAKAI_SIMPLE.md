# 🚀 Cara Pakai Bot Sederhana (bot_simple.py)

Bot ini lebih sederhana dan fokus:
- ✅ Refresh halaman setiap 3 detik
- ✅ Mencari tombol berdasarkan text yang Anda masukkan
- ✅ Memberi notifikasi jika tombol ditemukan (enabled/disabled)
- ✅ Otomatis klik jika tombol sudah enabled

## 📋 Cara Menggunakan

### Langkah 1: Install Dependencies (Hanya Pertama Kali)

```bash
pip install -r requirements.txt
```

Atau:
```bash
python3 -m pip install -r requirements.txt
```

### Langkah 2: Jalankan Bot

```bash
python3 bot_simple.py
```

### Langkah 3: Input Parameter

Bot akan meminta 2 parameter:

1. **Link Konser** 
   - Contoh: `https://ateezinjakarta.com/`
   - Atau: `ateezinjakarta.com` (bot akan otomatis tambahkan https://)

2. **Text Tombol yang ingin dicari**
   - Contoh: `Beli Tiket`
   - Contoh: `Order Now`
   - Contoh: `Masuk Antrean`
   - Contoh: `Get Ticket`
   - Bot akan mencari tombol yang mengandung text ini (case insensitive)

### Langkah 4: Bot Akan:

1. ✅ Membuka browser Chrome
2. ✅ Membuka halaman konser
3. ✅ Refresh setiap 3 detik
4. ✅ Mencari tombol dengan text yang dimasukkan
5. ✅ Memberi notifikasi ketika tombol ditemukan:
   - 🟢 **Enabled** = Tombol sudah bisa diklik (bot akan otomatis klik)
   - 🔴 **Disabled** = Tombol ditemukan tapi masih disable (bot akan terus monitor)
   - 🟡 **Status lain** = Tombol ditemukan dengan status tertentu

## 📝 Contoh Penggunaan

```bash
$ python3 bot_simple.py

============================================================
🤖 BOT PENCARI TOMBOL LOKET.COM
============================================================

📍 Masukkan Link Konser: https://ateezinjakarta.com/

🔘 Masukkan Text Tombol yang ingin dicari (contoh: 'Beli Tiket', 'Order Now', 'Masuk Antrean'): Beli Tiket

============================================================
✅ Konfigurasi:
   Link: https://ateezinjakarta.com/
   Tombol: 'Beli Tiket'
============================================================

🚀 Jalankan bot sekarang? (y/n): y

[Bot akan mulai bekerja...]
```

## 🎯 Fitur Bot

### ✅ Auto Refresh
- Refresh halaman setiap 3 detik
- Mencari tombol setelah setiap refresh

### ✅ Smart Button Detection
- Mencari tombol berdasarkan text (case insensitive)
- Mencari di: button, link (a), div, span dengan onclick
- Mencari di value attribute untuk input button

### ✅ Status Detection
- **Enabled**: Tombol bisa diklik
- **Disabled**: Tombol ditemukan tapi masih disable
- **Hidden**: Tombol tidak terlihat
- **Out of view**: Tombol di luar viewport

### ✅ Auto Click (IMPORTANT!)
- **Bot akan MENCUBA KLIK APAPUN STATUSNYA** (enabled, disabled, hidden, dll)
- Tidak peduli status, bot tetap coba klik
- Menggunakan beberapa metode: JavaScript click, normal click, ActionChains, event trigger
- Untuk hidden button, bot akan coba buat visible dulu
- **Jika klik berhasil** (halaman berubah/URL berubah), bot akan **BERHENTI**
- Jika klik tidak berhasil, bot akan refresh dan coba lagi

### ✅ Notifikasi
- Notifikasi suara (macOS/Linux) ketika tombol enabled
- Status update di terminal
- Screenshot bisa ditambahkan jika diperlukan

## ⚙️ Contoh Text Tombol yang Bisa Dicari

Berikut beberapa contoh text tombol yang umum digunakan:

- `Beli Tiket`
- `Buy Ticket`
- `Order Now`
- `Pesan Sekarang`
- `Get Ticket`
- `Masuk Antrean`
- `Join Queue`
- `Checkout`
- `Purchase`

**Tips**: Masukkan text yang unik dan mudah ditemukan. Jika tombol berubah text, gunakan sebagian text yang pasti ada.

## 🔧 Troubleshooting

### Bot tidak menemukan tombol
- Pastikan text tombol yang dimasukkan sesuai dengan yang ada di halaman
- Cek di browser manual apakah tombol sudah muncul
- Gunakan text yang lebih umum (contoh: "Beli" saja, bukan "Beli Tiket Sekarang")

### Tombol ditemukan tapi tidak bisa diklik
- Bot akan mencoba beberapa metode klik
- Jika gagal, klik manual di browser (browser tetap terbuka)
- Bot akan terus monitor untuk perubahan

### Browser tidak terbuka
- Pastikan Chrome browser terinstall
- Cek apakah ada error di terminal
- Pastikan dependencies sudah terinstall

### Bot stuck
- Tekan Ctrl+C untuk stop
- Restart bot
- Pastikan koneksi internet stabil

## 💡 Tips

1. **Timing**: Jalankan bot 30-60 menit sebelum penjualan dimulai
2. **Text Tombol**: Gunakan text yang pendek dan pasti (contoh: "Beli" lebih baik daripada "Beli Tiket Sekarang Disini")
3. **Monitor**: Biarkan bot running, jangan tutup terminal
4. **Browser**: Jangan tutup browser yang dibuka bot
5. **Multiple Instances**: Bisa jalankan beberapa bot dengan text tombol berbeda

## 📊 Output Contoh

```
[14:30:15] Refresh #1 - Mencari tombol...
[14:30:18] Refresh #2 - Mencari tombol...
[14:30:21] Refresh #3 - Mencari tombol...

============================================================
🔍 TOMBOL DITEMUKAN (Status: HIDDEN)
============================================================
📍 URL: https://ateezinjakarta.com/
🔘 Text tombol: 'Beli Tiket'
📊 Status: hidden

💡 Bot akan MENCUBA KLIK apapun statusnya...
   Jika klik berhasil (halaman berubah), bot akan berhenti.
============================================================

🖱️ Mencoba mengklik tombol (Status: hidden)...
⚠️ Klik belum berhasil (🟡 hidden). Bot akan refresh dan coba lagi...

[14:30:24] Refresh #4 - Mencari tombol...
🖱️ Mencoba mengklik tombol (Status: hidden)...
⚠️ Klik belum berhasil (🟡 hidden). Bot akan refresh dan coba lagi...

[14:30:27] Refresh #5 - Mencari tombol...

============================================================
🎉 BERHASIL! Tombol berhasil diklik!
============================================================
📍 URL baru: https://widget.loket.com/widget/xxxxx
🔘 Status tombol: hidden

✅ Bot akan berhenti. Silakan lanjutkan pembelian manual.
============================================================

👀 Memonitor perubahan halaman...
✅ URL berubah! Halaman baru: https://widget.loket.com/widget/xxxxx
```

**Note**: Bot akan mencoba klik apapun status tombol (hidden, disabled, enabled, dll). Jika klik berhasil (terdeteksi perubahan URL atau halaman), bot akan berhenti.

## ⚠️ Catatan

- Bot ini membantu proses otomatis yang legal
- Pastikan patuh Terms of Service Loket.com
- Gunakan dengan bijak dan bertanggung jawab
- Bot hanya membantu mencari dan mengklik tombol, pembelian tetap harus diselesaikan manual

---

**Selamat mencoba! Semoga dapat tiketnya! 🎫✨**


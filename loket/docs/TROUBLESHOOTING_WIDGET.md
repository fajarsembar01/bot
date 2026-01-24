# 🔧 Troubleshooting: Bot Tidak Menemukan Widget Loket

## Masalah: Bot tidak bisa menemukan tombol/link yang mengarah ke widget Loket

### ✅ Solusi 1: Gunakan URL Widget Langsung (RECOMMENDED)

Jika Anda sudah tahu URL widget Loket (contoh: `https://widget.loket.com/widget/yqar4pcjnnmn6q9mxobc`), gunakan langsung:

```bash
python3 loket/bot_loket.py --widget https://widget.loket.com/widget/yqar4pcjnnmn6q9mxobc
```

**Cara mendapatkan URL widget:**

#### Method 1: Copy Link (Paling Mudah)
1. Buka halaman konser di browser (contoh: ateezinjakarta.com)
2. Klik kanan pada tombol/link "Beli Tiket" atau tombol yang mengarah ke loket
3. Pilih **"Copy link address"** atau **"Salin alamat link"**
4. Paste URL tersebut ke parameter `--widget`

#### Method 2: Inspect Element
1. Buka halaman konser di browser
2. Tekan **F12** untuk membuka Developer Tools
3. Klik ikon **"Select element"** (ikon pointer di pojok kiri atas)
4. Hover ke tombol "Beli Tiket" dan klik
5. Di panel Elements, cari tag `<a>` atau `<button>` yang mengandung href
6. Cari href yang mengandung `widget.loket.com`
7. Copy URL tersebut

#### Method 3: Network Tab
1. Buka halaman konser di browser
2. Tekan **F12** → Pilih tab **Network**
3. Klik tombol "Beli Tiket" di halaman
4. Lihat request yang muncul, cari yang mengarah ke `widget.loket.com`
5. Copy URL tersebut

### ✅ Solusi 2: Update Bot (Sudah Diperbaiki)

Bot sudah diperbaiki untuk:
- ✅ Mencari link yang mengandung `widget.loket.com` atau `loket.com/widget`
- ✅ Mencari tombol dengan text "Beli", "Buy", "Ticket", "Pesan"
- ✅ Scan page source untuk menemukan URL widget
- ✅ Menangani iframe yang mungkin mengandung widget

Pastikan Anda menggunakan versi terbaru bot.

### ✅ Solusi 3: Manual Check

1. Jalankan bot dengan mode browser terlihat:
   ```bash
   python3 loket/bot_loket.py --no-headless
   ```

2. Bot akan membuka browser, lihat apakah halaman sudah terbuka dengan benar

3. Jika halaman terbuka tapi bot tidak menemukan widget:
   - Screenshot halaman (Ctrl+Shift+S atau Cmd+Shift+4)
   - Cari manual di browser apakah ada link/tombol yang mengarah ke loket
   - Jika ada, copy URL-nya dan gunakan `--widget`

### ✅ Solusi 4: Timing

Widget Loket biasanya hanya muncul:
- 10-30 menit sebelum penjualan dimulai
- Saat waiting room sudah dibuka
- Setelah login (jika diperlukan)

**Tindakan:**
- Jalankan bot 30-60 menit sebelum waktu penjualan
- Jika widget belum muncul, tunggu sampai waiting room dibuka
- Pastikan sudah login ke akun Loket.com jika diperlukan

### ✅ Solusi 5: Debug Mode

Untuk melihat lebih detail apa yang bot temukan:

1. Edit file `loket/bot_loket.py`, tambahkan print statement lebih banyak
2. Atau jalankan dengan Python debugger
3. Periksa screenshot yang diambil bot (file `screenshot_*.png`)

## Contoh URL Widget Loket

Format URL widget biasanya seperti ini:
```
https://widget.loket.com/widget/[id-unik]
```

Contoh:
```
https://widget.loket.com/widget/yqar4pcjnnmn6q9mxobc
```

## Checklist

Sebelum melaporkan masalah, pastikan:
- [ ] Chrome browser sudah terinstall
- [ ] Dependencies sudah terinstall (`pip install -r requirements.txt`)
- [ ] URL konser benar (test di browser manual)
- [ ] Sudah mencoba dengan `--widget` dan URL widget yang benar
- [ ] Timing sudah tepat (waiting room sudah dibuka)
- [ ] Sudah login ke akun Loket.com (jika diperlukan)
- [ ] Koneksi internet stabil

## Masih Bermasalah?

Jika masih tidak bisa, coba:

1. **Manual method**: Buka widget URL langsung di browser, lalu biarkan bot monitor dari sana
2. **Multiple attempts**: Jalankan bot beberapa kali dengan refresh halaman
3. **Check logs**: Lihat output terminal untuk melihat apa yang bot temukan

---

**Tips**: Cara terbaik adalah mendapatkan URL widget terlebih dahulu secara manual, lalu gunakan parameter `--widget` untuk langsung masuk ke widget Loket.

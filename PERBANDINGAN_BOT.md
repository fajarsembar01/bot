# 🔄 Perbandingan: Bot Sederhana vs Bot Advanced

## 📊 Ringkasan Perbandingan

| Aspek | Bot Sederhana (`bot_simple.py`) | Bot Advanced (`bot_loket.py`) |
|-------|--------------------------------|------------------------------|
| **Kompleksitas** | ⭐⭐ Sederhana | ⭐⭐⭐⭐⭐ Advanced |
| **Kemudahan Pakai** | ✅ Sangat Mudah | ⚠️ Perlu setup |
| **Input Parameter** | ✅ Saat running (interaktif) | 📝 Via file config/argumen |
| **Pendekatan** | 🎯 Fokus cari tombol spesifik | 🔍 Auto-detect widget Loket |
| **Ukuran Kode** | ~400 baris | ~550 baris |

---

## 🤖 Bot Sederhana (`bot_simple.py`)

### ✅ Kelebihan:
1. **Mudah digunakan** - Input parameter saat running, tidak perlu setup file config
2. **Fokus** - Hanya cari tombol berdasarkan text yang Anda masukkan
3. **Jelas** - Anda tahu persis tombol apa yang dicari
4. **Cepat setup** - Langsung jalankan, input parameter, selesai
5. **Simple logic** - Refresh → Cari tombol → Klik (jika enabled)

### ❌ Kekurangan:
1. **Harus tahu text tombol** - Harus masukkan text tombol yang benar
2. **Tidak auto-detect widget** - Tidak bisa auto-detect link ke widget Loket
3. **Fitur terbatas** - Hanya fokus pada 1 tugas

### 🎯 Kapan Pakai:
- ✅ **Pakai jika**: Anda sudah tahu tombol apa yang ingin dicari
- ✅ **Pakai jika**: Ingin bot yang simple dan mudah
- ✅ **Pakai jika**: Tidak ingin setup file config

### 💻 Cara Pakai:
```bash
python3 bot_simple.py
# Input: Link konser + Text tombol
```

---

## 🤖 Bot Advanced (`bot_loket.py`)

### ✅ Kelebihan:
1. **Auto-detect widget** - Otomatis cari link ke widget Loket di halaman
2. **Multiple detection methods** - Mencari dengan berbagai cara (link, button, iframe, page source)
3. **Support widget URL langsung** - Bisa langsung ke widget URL
4. **Fitur lengkap** - Support config file, headless mode, dll
5. **Smart detection** - Bisa scan page source untuk cari URL widget

### ❌ Kekurangan:
1. **Lebih kompleks** - Perlu setup file `.env` atau argumen command line
2. **Tidak fokus** - Mencoba banyak hal sekaligus
3. **Harus tahu struktur website** - Untuk menggunakan widget URL langsung

### 🎯 Kapan Pakai:
- ✅ **Pakai jika**: Tidak tahu text tombol apa yang dicari
- ✅ **Pakai jika**: Ingin auto-detect widget Loket
- ✅ **Pakai jika**: Sudah tahu URL widget Loket langsung
- ✅ **Pakai jika**: Butuh fitur advanced (headless, config file, dll)

### 💻 Cara Pakai:
```bash
# Via config file
python3 bot_loket.py

# Atau via argumen
python3 bot_loket.py --url https://ateezinjakarta.com/
python3 bot_loket.py --widget https://widget.loket.com/widget/xxxxx
```

---

## 🔍 Perbedaan Detail

### 1. **Cara Input Parameter**

**Bot Sederhana:**
```python
# Input saat running (interaktif)
📍 Masukkan Link Konser: https://ateezinjakarta.com/
🔘 Masukkan Text Tombol: Beli Tiket
```

**Bot Advanced:**
```python
# Via file config atau argumen
# File .env:
CONCERT_URL=https://ateezinjakarta.com/

# Atau argumen:
python3 bot_loket.py --url https://ateezinjakarta.com/
```

### 2. **Metode Pencarian**

**Bot Sederhana:**
```python
# Fokus cari tombol berdasarkan TEXT
- Cari semua button, link, div dengan text tertentu
- Cek status enabled/disabled
- Klik jika enabled
```

**Bot Advanced:**
```python
# Multi-method detection
- Cari link yang mengandung "widget.loket.com"
- Cari button dengan text "Beli", "Buy", "Ticket"
- Scan page source dengan regex untuk URL widget
- Cek iframe yang mengandung widget
- Support widget URL langsung
```

### 3. **Flow Kerja**

**Bot Sederhana:**
```
1. Input parameter (link + text tombol)
2. Buka browser
3. Refresh setiap 3 detik
4. Cari tombol dengan text
5. Notifikasi jika ditemukan (enabled/disabled)
6. Auto-klik jika enabled
7. Monitor perubahan halaman
```

**Bot Advanced:**
```
1. Baca config/argumen
2. Buka browser
3. Buka halaman konser
4. Cek perlu login?
5. Cari link/button ke widget Loket (multi-method)
6. Jika widget URL langsung → langsung ke widget
7. Masuk ke waiting room/widget
8. Monitor queue status
9. Notifikasi ketika masuk checkout
```

### 4. **Notifikasi**

**Bot Sederhana:**
```
- ✅ Tombol ditemukan dan enabled → Auto-klik
- ⚠️ Tombol ditemukan tapi disabled → Monitor terus
- 🔄 Refresh terus sampai tombol enabled
```

**Bot Advanced:**
```
- ✅ Widget Loket ditemukan
- ✅ Masuk ke waiting room
- ✅ Status antrian (jika ada)
- 🎉 Masuk ke halaman checkout/pembelian
```

---

## 🎯 Rekomendasi: Pakai Yang Mana?

### Pakai **Bot Sederhana** jika:
- ✅ Anda sudah tahu tombol apa yang ingin dicari (contoh: "Beli Tiket")
- ✅ Ingin bot yang simple dan mudah digunakan
- ✅ Tidak ingin setup file config
- ✅ Ingin input parameter langsung saat running

### Pakai **Bot Advanced** jika:
- ✅ Tidak tahu text tombol apa yang akan muncul
- ✅ Ingin auto-detect widget Loket
- ✅ Sudah punya URL widget Loket langsung
- ✅ Butuh fitur advanced (headless mode, config file)
- ✅ Website menggunakan widget Loket yang embedded

---

## 💡 Contoh Skenario

### Skenario 1: Halaman dengan tombol "Beli Tiket"
```
✅ Pakai Bot Sederhana
Input: Link = https://ateezinjakarta.com/
       Text = "Beli Tiket"
Bot akan refresh dan cari tombol "Beli Tiket"
```

### Skenario 2: Halaman dengan link ke widget Loket
```
✅ Pakai Bot Advanced
Bot akan auto-detect link ke widget.loket.com
Atau bisa langsung: --widget https://widget.loket.com/widget/xxxxx
```

### Skenario 3: Tidak tahu struktur website
```
✅ Pakai Bot Advanced
Bot akan coba berbagai metode untuk menemukan widget Loket
```

### Skenario 4: Ingin bot yang simple dan cepat
```
✅ Pakai Bot Sederhana
Jalankan, input parameter, langsung jalan
```

---

## 🔄 Bisa Pakai Keduanya?

Ya! Anda bisa:
1. Coba **Bot Sederhana** dulu (lebih mudah)
2. Jika tidak berhasil, coba **Bot Advanced** (auto-detect)
3. Atau jalankan keduanya di waktu yang sama dengan parameter berbeda

---

## 📝 Kesimpulan

| | Bot Sederhana | Bot Advanced |
|---|---|---|
| **Target User** | Pemula, yang ingin simple | Advanced user, yang butuh auto-detect |
| **Use Case** | Tahu tombol apa yang dicari | Tidak tahu struktur website |
| **Setup** | Tidak perlu | Perlu file config (opsional) |
| **Fleksibilitas** | Fokus 1 tugas | Multiple methods |
| **Rekomendasi** | ⭐⭐⭐⭐⭐ Untuk kebanyakan orang | ⭐⭐⭐ Untuk case khusus |

**💡 Tips**: Mulai dengan **Bot Sederhana** dulu. Jika tidak berhasil, baru coba **Bot Advanced**!


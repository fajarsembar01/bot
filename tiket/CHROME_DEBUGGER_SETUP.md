# Quick Setup Guide - Chrome Debugger Mode

## Langkah-langkah Setup (Dilakukan Sekali Saja)

### 1. Close Semua Chrome
Pastikan tidak ada Chrome yang sedang berjalan.

### 2. Launch Chrome dengan Debugger
Jalankan script yang sudah dibuat:
```
cd d:\DHEA\bot loket\bot\tiket
launch_chrome_debugger.bat
```

Atau manual via PowerShell:
```powershell
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\selenium\ChromeProfile"
```

### 3. Login ke Tiket.com
Di Chrome yang baru terbuka:
- Buka https://www.tiket.com
- Klik tombol **Login**
- Masukkan email dan password
- Pastikan login berhasil (nama user muncul di pojok kanan atas)

### 4. Biarkan Chrome Tetap Buka
**PENTING**: Jangan close Chrome ini selama automation berjalan!

---

## Cara Menjalankan Automation

### 1. Pastikan Chrome Debugger Masih Running
Check di Task Manager apakah Chrome dengan debugging masih berjalan.

### 2. Start Web Panel
```powershell
cd d:\DHEA\bot loket\bot\tiket
python web_panel_tiket.py
```

### 3. Buka Web Panel
Buka browser (bisa browser lain atau tab baru di Chrome debugger):
```
http://127.0.0.1:5001
```

### 4. Konfigurasi Parameter
Set parameter berikut di web panel:

**Required Settings:**
- **URL**: `https://www.tiket.com/id-id/to-do/one-ok-rock-detox-tour-2026/packages`
- **Package Name**: `CAT 1` (atau nama paket yang diinginkan)
- **Quantity**: `2` (atau jumlah tiket)
- **Debugger Address**: `127.0.0.1:9222` ✅ **WAJIB!**
- **User Data Dir**: `C:\selenium\ChromeProfile` ✅ **WAJIB!**

**Checkboxes:**
- ☑ **Open new tab when attaching** ✅ **WAJIB CHECKED!**
- ☐ **Headless mode** (UNCHECK - tidak bisa headless saat attach)
- ☑ **Auto checkout** (checked untuk auto klik checkout)

### 5. Klik "Start Auto-buy"

### 6. Observe
- Bot akan attach ke Chrome debugger
- Bot buka tab baru
- Bot jalankan automation
- **Bot TIDAK akan redirect ke login** karena sudah login!
- Bot akan sampai ke order page
- Browser tetap terbuka untuk complete pembayaran manual

### 7. Complete Pembayaran
- Isi detail pembayaran
- Complete transaksi
- Save konfirmasi

### 8. Stop Bot
Setelah selesai, klik **Stop** di web panel.

---

## Troubleshooting

### Bot Masih Redirect ke Login
✅ Verify Chrome debugger masih running  
✅ Check masih login di Tiket.com (refresh page untuk test)  
✅ Pastikan debugger address = `127.0.0.1:9222`  
✅ Pastikan user data dir = `C:\selenium\ChromeProfile`  
✅ Pastikan "Open new tab" di-check  

### Bot Tidak Bisa Attach
✅ Pastikan Chrome launched dengan `--remote-debugging-port=9222`  
✅ Check port 9222 tidak dipakai aplikasi lain  
✅ Restart Chrome dengan debugger  

### Error "Chrome binary not found"
✅ Pastikan Chrome terinstall di: `C:\Program Files\Google\Chrome\Application\chrome.exe`  
✅ Atau update path di script jika Chrome di lokasi lain  

---

## Tips

**Session Persist**: Dengan user data dir `C:\selenium\ChromeProfile`, login kamu akan tersimpan. Next time kamu jalankan automation, tinggal:
1. Run `launch_chrome_debugger.bat`
2. Chrome otomatis sudah login (tidak perlu login ulang)
3. Langsung jalankan automation dari web panel

**Multiple Events**: Bisa gunakan Chrome debugger yang sama untuk berbagai event Tiket.com, tidak perlu setup ulang.

**Keamanan**: Jangan share folder `C:\selenium\ChromeProfile` karena berisi session login kamu.

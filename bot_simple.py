"""
Bot Sederhana untuk Mencari Tombol di Halaman Konser Loket.com
Refresh setiap 2-5 detik (random) dan cari tombol berdasarkan text
Auto beli tiket setelah masuk widget Loket
"""
import time
import sys
import random
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager


class SimpleButtonBot:
    def __init__(self, concert_url, button_text, auto_buy=False, ticket_category=None, ticket_quantity=1):
        self.concert_url = concert_url
        self.button_text = button_text
        self.auto_buy = auto_buy
        self.ticket_category = ticket_category
        self.ticket_quantity = ticket_quantity
        self.driver = None
    
    def random_delay(self, min_seconds=2, max_seconds=5):
        """Random delay antara min dan max seconds"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        return round(delay, 1)
        
    def setup_driver(self):
        """Setup Chrome WebDriver"""
        print("🔧 Setting up browser...")
        chrome_options = Options()
        
        # Anti-detection options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # User agent
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.maximize_window()
            
            # Anti-detection script
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            
            print("✅ Browser setup berhasil!")
            return True
        except Exception as e:
            print(f"❌ Error setting up browser: {e}")
            return False
    
    def find_buttons_by_text(self):
        """Cari SEMUA tombol berdasarkan text (bukan hanya satu)"""
        try:
            # Cari semua button, link, div, span yang bisa diklik
            elements = self.driver.find_elements(By.XPATH, 
                "//button | //a | //div[@onclick] | //span[@onclick] | //*[@role='button']")
            
            target_buttons = []
            button_text_lower = self.button_text.lower()
            
            for elem in elements:
                try:
                    # Skip jika element tidak ada
                    if not elem:
                        continue
                    
                    # Cek text content
                    text = elem.text.strip().lower()
                    
                    # Cek apakah text tombol ada di element
                    if button_text_lower in text or text in button_text_lower:
                        if text:  # Hanya tambahkan jika ada text
                            target_buttons.append(elem)
                            continue
                    
                    # Cek juga di value attribute (untuk input button)
                    try:
                        value = elem.get_attribute('value')
                        if value and button_text_lower in value.lower():
                            target_buttons.append(elem)
                            continue
                    except:
                        pass
                    
                    # Cek juga di aria-label atau title
                    try:
                        aria_label = elem.get_attribute('aria-label') or ''
                        title = elem.get_attribute('title') or ''
                        if button_text_lower in aria_label.lower() or button_text_lower in title.lower():
                            target_buttons.append(elem)
                    except:
                        pass
                    
                except:
                    continue
            
            return target_buttons if target_buttons else None
            
        except Exception as e:
            print(f"⚠️ Error mencari tombol: {e}")
            return None
    
    def check_button_status(self, button):
        """Cek status tombol (enabled/disabled)"""
        try:
            # Cek apakah button disabled
            disabled = button.get_attribute('disabled')
            if disabled is not None or disabled == 'true':
                return 'disabled'
            
            # Cek class yang mengandung disabled
            classes = button.get_attribute('class') or ''
            if 'disabled' in classes.lower() or 'inactive' in classes.lower():
                return 'disabled'
            
            # Cek style
            style = button.get_attribute('style') or ''
            if 'pointer-events: none' in style.lower() or 'opacity: 0.5' in style.lower():
                return 'disabled'
            
            # Cek apakah button visible dan bisa diklik
            if not button.is_displayed():
                return 'hidden'
            
            # Cek apakah button dalam viewport
            try:
                is_in_viewport = self.driver.execute_script("""
                    var rect = arguments[0].getBoundingClientRect();
                    return (rect.top >= 0 && rect.left >= 0 && 
                            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                            rect.right <= (window.innerWidth || document.documentElement.clientWidth));
                """, button)
                
                if not is_in_viewport:
                    return 'out_of_view'
            except:
                pass
            
            return 'enabled'
            
        except Exception as e:
            print(f"⚠️ Error checking button status: {e}")
            return 'unknown'
    
    def click_button(self, button):
        """Klik tombol dengan berbagai metode, return True jika berhasil"""
        try:
            # Simpan URL dan beberapa info sebelum klik untuk cek perubahan
            url_before = self.driver.current_url
            title_before = self.driver.title
            
            # Scroll ke button (coba beberapa cara untuk hidden button)
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                self.random_delay(0.2, 0.5)
            except:
                # Jika scroll gagal, coba scroll dengan JavaScript langsung
                try:
                    self.driver.execute_script("""
                        var element = arguments[0];
                        element.scrollIntoView(true);
                    """, button)
                    self.random_delay(0.2, 0.5)
                except:
                    pass
            
            # Untuk hidden button, coba buat visible dulu
            try:
                self.driver.execute_script("""
                    var element = arguments[0];
                    element.style.display = 'block';
                    element.style.visibility = 'visible';
                    element.style.opacity = '1';
                    element.style.pointerEvents = 'auto';
                """, button)
                self.random_delay(0.1, 0.3)
            except:
                pass
            
            # Method 1: JavaScript click (paling reliable untuk hidden/disabled button)
            try:
                self.driver.execute_script("arguments[0].click();", button)
                # Tunggu lebih lama untuk melihat perubahan (kadang redirect butuh waktu)
                self.random_delay(2, 5)
                
                # Cek apakah ada perubahan dengan verifikasi yang lebih ketat
                if self._check_click_success_strict(url_before, title_before):
                    return True
            except Exception as e:
                pass
            
            # Method 2: Normal click
            try:
                button.click()
                self.random_delay(2, 5)
                
                if self._check_click_success_strict(url_before, title_before):
                    return True
            except:
                pass
            
            # Method 3: Action chains
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(self.driver).move_to_element(button).click().perform()
                self.random_delay(2, 5)
                
                if self._check_click_success_strict(url_before, title_before):
                    return True
            except:
                pass
            
            # Method 4: Trigger event click via JavaScript (full event)
            try:
                self.driver.execute_script("""
                    var element = arguments[0];
                    var events = ['mousedown', 'mouseup', 'click'];
                    events.forEach(function(eventType) {
                        var event = new MouseEvent(eventType, {
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            buttons: 1
                        });
                        element.dispatchEvent(event);
                    });
                """, button)
                self.random_delay(2, 5)
                
                if self._check_click_success_strict(url_before, title_before):
                    return True
            except:
                pass
            
            return False
            
        except Exception as e:
            print(f"⚠️ Error clicking button: {e}")
            return False
    
    def _check_click_success_strict(self, url_before, title_before):
        """Cek apakah klik berhasil dengan verifikasi yang lebih ketat"""
        try:
            # Tunggu sebentar untuk memastikan perubahan sudah terjadi
            self.random_delay(1, 2)
            
            url_after = self.driver.current_url
            title_after = self.driver.title
            
            # PRIORITAS 1: Cek apakah URL benar-benar berubah (pasti berhasil)
            if url_after != url_before and url_after.strip() != url_before.strip():
                # URL berubah, pastikan bukan hanya karena hash/fragment
                if url_after.split('#')[0] != url_before.split('#')[0]:
                    print(f"✅ URL berubah: {url_before} → {url_after}")
                    return True
            
            # PRIORITAS 2: Cek apakah title berubah (indikasi navigasi)
            if title_after != title_before and title_after.strip():
                print(f"✅ Title berubah: {title_before} → {title_after}")
                return True
            
            # PRIORITAS 3: Cek indikator spesifik di halaman (widget loket, checkout, dll)
            try:
                page_source = self.driver.page_source.lower()
                
                # Indikator yang PASTI menunjukkan berhasil (harus ada salah satu)
                strong_indicators = [
                    'widget.loket.com/widget/',  # URL widget loket
                    'loket.com/widget/',         # URL widget loket (alternatif)
                    'checkout',                  # Halaman checkout
                    'select category',           # Widget loket step 1
                    'personal information',      # Widget loket step 2
                    'confirmation',              # Widget loket step 3
                ]
                
                for indicator in strong_indicators:
                    if indicator in page_source:
                        print(f"✅ Indikator kuat ditemukan: '{indicator}'")
                        return True
                
                # Cek apakah ada iframe baru yang muncul (widget loket biasanya dalam iframe)
                try:
                    iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                    if len(iframes) > 0:
                        for iframe in iframes:
                            src = iframe.get_attribute('src') or ''
                            if 'loket.com' in src.lower() or 'widget' in src.lower():
                                print(f"✅ Iframe widget ditemukan: {src[:100]}")
                                return True
                except:
                    pass
                
                # Cek apakah ada popup/modal yang muncul dengan class/ID spesifik
                try:
                    modals = self.driver.find_elements(By.XPATH, 
                        "//div[contains(@class, 'modal') or contains(@class, 'popup') or contains(@class, 'widget')]")
                    if len(modals) > 0:
                        # Cek apakah modal ini terkait dengan loket
                        for modal in modals[:3]:  # Cek 3 modal pertama saja
                            modal_html = modal.get_attribute('innerHTML') or ''
                            if any(indicator in modal_html.lower() for indicator in ['loket', 'widget', 'ticket', 'order']):
                                print(f"✅ Modal/Widget terdeteksi")
                                return True
                except:
                    pass
                
            except Exception as e:
                pass
            
            # Jika tidak ada indikator kuat, anggap tidak berhasil
            return False
            
        except Exception as e:
            print(f"⚠️ Error checking click success: {e}")
            return False
    
    def notify_found(self, status):
        """Notifikasi ketika tombol ditemukan"""
        print("\n" + "="*60)
        status_messages = {
            'enabled': "✅ TOMBOL DITEMUKAN (Status: ENABLED)",
            'disabled': "⚠️ TOMBOL DITEMUKAN (Status: DISABLED)",
            'hidden': "🔍 TOMBOL DITEMUKAN (Status: HIDDEN)",
            'out_of_view': "📍 TOMBOL DITEMUKAN (Status: OUT OF VIEW)",
            'unknown': "❓ TOMBOL DITEMUKAN (Status: UNKNOWN)"
        }
        
        message = status_messages.get(status, f"ℹ️ TOMBOL DITEMUKAN (Status: {status})")
        print(message)
        print("="*60)
        print(f"📍 URL: {self.driver.current_url}")
        print(f"🔘 Text tombol: '{self.button_text}'")
        print(f"📊 Status: {status}")
        print("\n💡 Bot akan MENCUBA KLIK apapun statusnya...")
        print("   Jika klik berhasil (halaman berubah), bot akan berhenti.")
        print("="*60 + "\n")
        
        # Beep sound untuk notifikasi (1x saja, nanti ada lagi kalau berhasil)
        try:
            import os
            os.system('afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || echo "\\a"')
        except:
            pass
        
    def run(self):
        """Jalankan bot"""
        print("="*60)
        print("🤖 BOT PENCARI TOMBOL LOKET.COM")
        print("="*60)
        print(f"📍 Link Konser: {self.concert_url}")
        print(f"🔘 Text Tombol: '{self.button_text}'")
        print(f"🕐 Waktu mulai: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        if not self.setup_driver():
            return
        
        try:
            print(f"🌐 Membuka halaman: {self.concert_url}")
            self.driver.get(self.concert_url)
            self.random_delay(2, 3)
            
            refresh_count = 0
            last_status = None
            
            print(f"\n🔄 Bot akan refresh setiap 3 detik dan mencari tombol '{self.button_text}'...")
            print("🔄 Bot akan terus loop sampai URL benar-benar berubah!")
            print("⚠️ Tekan Ctrl+C untuk stop\n")
            
            # Simpan URL awal untuk referensi
            initial_url = self.driver.current_url
            
            while True:
                try:
                    refresh_count += 1
                    current_time = datetime.now().strftime('%H:%M:%S')
                    current_url = self.driver.current_url
                    
                    # CEK DULU: Apakah URL sudah berubah dari URL awal?
                    url_before_check = current_url.split('#')[0].split('?')[0].strip().rstrip('/')
                    initial_url_base = initial_url.split('#')[0].split('?')[0].strip().rstrip('/')
                    
                    if url_before_check != initial_url_base:
                        # URL sudah berubah! Cek apakah ini perubahan yang valid
                        if self._verify_page_change(initial_url, current_url):
                            print("\n" + "="*60)
                            print("🎉 URL SUDAH BERUBAH!")
                            print("="*60)
                            print(f"📍 URL awal: {initial_url}")
                            print(f"📍 URL sekarang: {current_url}")
                            print("\n✅ Bot akan berhenti. Silakan lanjutkan pembelian manual.")
                            print("="*60 + "\n")
                            
                            # Notifikasi suara
                            try:
                                import os
                                for _ in range(5):
                                    os.system('afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || echo "\\a"')
                                    time.sleep(0.2)
                            except:
                                pass
                            
                            # Cek apakah ini widget Loket, jika ya tanya apakah mau auto beli
                            if 'widget.loket.com' in current_url or 'loket.com/widget' in current_url:
                                self.handle_widget_loket_auto_buy()
                            
                            self.monitor_after_click()
                            break
                    
                    print(f"[{current_time}] Refresh #{refresh_count} - Mencari tombol... (URL: {url_before_check[:50]}...)", end='\r')
                    
                    # Cari SEMUA tombol dengan text yang sama
                    buttons = self.find_buttons_by_text()
                    
                    if buttons and len(buttons) > 0:
                        if len(buttons) > 1:
                            print(f"\n✅ Ditemukan {len(buttons)} tombol dengan text '{self.button_text}'")
                        else:
                            print(f"\n✅ Ditemukan tombol dengan text '{self.button_text}'")
                        
                        print("   🔄 Bot akan terus loop sampai URL benar-benar berubah!")
                        
                        url_before_click = self.driver.current_url
                        success = False
                        
                        # COBA SEMUA TOMBOL sampai salah satunya benar-benar berhasil
                        for idx, button in enumerate(buttons, 1):
                            try:
                                status = self.check_button_status(button)
                                
                                # Hanya print status jika ini tombol pertama atau status berubah
                                if idx == 1 and (status != last_status or last_status is None):
                                    print()  # New line
                                    self.notify_found(status)
                                    last_status = status
                                
                                if len(buttons) > 1:
                                    print(f"🖱️ Mencoba tombol #{idx}/{len(buttons)} (Status: {status})...")
                                else:
                                    print(f"🖱️ Mencoba mengklik tombol (Status: {status})...")
                                
                                # Coba klik tombol ini
                                url_before_button_click = self.driver.current_url
                                
                                if self.click_button(button):
                                    # Verifikasi ulang setelah beberapa detik untuk memastikan
                                    print("⏳ Verifikasi perubahan halaman...")
                                    self.random_delay(2, 5)
                                    
                                    url_after_click = self.driver.current_url
                                    final_check = self._verify_page_change(url_before_button_click, url_after_click)
                                    
                                    if final_check:
                                        print("\n" + "="*60)
                                        print("🎉 BERHASIL! Tombol berhasil diklik dan halaman benar-benar berubah!")
                                        print("="*60)
                                        print(f"📍 URL sebelum: {url_before_button_click}")
                                        print(f"📍 URL sesudah: {url_after_click}")
                                        print(f"🔘 Tombol yang berhasil: #{idx}/{len(buttons)}")
                                        print(f"📊 Status tombol: {status}")
                                        print("\n✅ Bot akan berhenti. Silakan lanjutkan pembelian manual.")
                                        print("="*60 + "\n")
                                        
                                        # Notifikasi suara
                                        try:
                                            import os
                                            for _ in range(5):
                                                os.system('afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || echo "\\a"')
                                                time.sleep(0.2)
                                        except:
                                            pass
                                        
                                        # Cek apakah ini widget Loket, jika ya tanya apakah mau auto beli
                                        if 'widget.loket.com' in url_after_click or 'loket.com/widget' in url_after_click:
                                            self.handle_widget_loket_auto_buy()
                                        
                                        # Monitor sebentar untuk memastikan
                                        self.monitor_after_click()
                                        success = True
                                        break
                                    else:
                                        # Verifikasi gagal - URL masih sama, lanjutkan loop
                                        if len(buttons) > 1:
                                            print(f"   ❌ Tombol #{idx} tidak mengubah halaman (URL masih sama)")
                                            print(f"   URL: {url_after_click}")
                                            print(f"   Mencoba tombol berikutnya atau refresh...")
                                        else:
                                            print(f"   ❌ Verifikasi gagal: Halaman tidak benar-benar berubah")
                                            print(f"   URL masih sama: {url_after_click}")
                                            print(f"   Bot akan refresh dan coba lagi...")
                                else:
                                    # Klik tidak berhasil, coba tombol berikutnya
                                    if len(buttons) > 1:
                                        print(f"   ❌ Tombol #{idx} tidak bisa diklik, mencoba tombol berikutnya...")
                                    
                            except Exception as e:
                                if len(buttons) > 1:
                                    print(f"   ⚠️ Error pada tombol #{idx}: {e}")
                                continue
                        
                        # Jika semua tombol sudah dicoba dan tidak ada yang berhasil, tetap loop
                        if not success:
                            if len(buttons) > 1:
                                print(f"\n⚠️ Semua {len(buttons)} tombol sudah dicoba, tapi URL masih sama")
                            else:
                                try:
                                    status_icon = "🟢" if status == 'enabled' else "🔴" if status == 'disabled' else "🟡" if status == 'hidden' else "⚪"
                                    print(f"\n⚠️ Klik belum berhasil ({status_icon} {status})")
                                except:
                                    print(f"\n⚠️ Klik belum berhasil")
                            
                            print(f"   🔄 URL masih: {self.driver.current_url}")
                            print(f"   🔄 Bot akan refresh dan loop lagi sampai URL benar-benar berubah...")
                    else:
                        # Tombol tidak ditemukan
                        if last_status is not None:
                            print()  # New line jika sebelumnya ada status
                            print(f"⚠️ Tombol '{self.button_text}' tidak ditemukan")
                            last_status = None
                        print(f"   🔄 URL sekarang: {current_url}")
                        print(f"   🔄 Bot akan refresh dan cari lagi...")
                    
                    # Refresh halaman setiap 2-5 detik random (TETAP LOOP sampai URL berubah)
                    delay = self.random_delay(2, 5)
                    print(f"\n⏳ Menunggu {delay:.1f} detik sebelum refresh...")
                    print(f"🔄 Refresh halaman...")
                    self.driver.refresh()
                    self.random_delay(1, 2)  # Tunggu halaman selesai load setelah refresh
                    
                    # Update initial_url jika halaman baru dibuka
                    new_url = self.driver.current_url
                    if new_url != initial_url:
                        # Cek apakah ini perubahan yang valid
                        if self._verify_page_change(initial_url, new_url):
                            print("\n" + "="*60)
                            print("🎉 URL BERUBAH SETELAH REFRESH!")
                            print("="*60)
                            print(f"📍 URL awal: {initial_url}")
                            print(f"📍 URL sekarang: {new_url}")
                            print("\n✅ Bot akan berhenti. Silakan lanjutkan pembelian manual.")
                            print("="*60 + "\n")
                            
                            # Notifikasi suara
                            try:
                                import os
                                for _ in range(5):
                                    os.system('afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || echo "\\a"')
                                    time.sleep(0.2)
                            except:
                                pass
                            
                            # Cek apakah ini widget Loket, jika ya tanya apakah mau auto beli
                            if 'widget.loket.com' in new_url or 'loket.com/widget' in new_url:
                                self.handle_widget_loket_auto_buy()
                            
                            self.monitor_after_click()
                            break
                        else:
                            # Update initial_url untuk referensi berikutnya
                            initial_url = new_url
                    
                except KeyboardInterrupt:
                    print("\n\n⚠️ Bot dihentikan oleh user")
                    break
                except WebDriverException as e:
                    print(f"\n⚠️ WebDriver error: {e}")
                    print("🔄 Mencoba reconnect...")
                    self.random_delay(2, 3)
                    try:
                        self.driver.get(self.concert_url)
                        self.random_delay(2, 3)
                    except:
                        print("❌ Gagal reconnect, coba restart bot")
                        break
                except Exception as e:
                    print(f"\n⚠️ Error: {e}")
                    self.random_delay(2, 3)
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Bot dihentikan oleh user")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("\n" + "="*60)
            print("⚠️ Tutup browser? (y/n): ", end="")
            try:
                response = input().strip().lower()
                if response == 'y':
                    if self.driver:
                        self.driver.quit()
                        print("✅ Browser ditutup")
                else:
                    print("✅ Browser tetap terbuka. Silakan gunakan manual.")
            except:
                if self.driver:
                    self.driver.quit()
    
    def _verify_page_change(self, url_before, url_after):
        """Verifikasi ulang apakah halaman benar-benar berubah - HARUS KETAT"""
        try:
            # HARUS: URL harus berbeda (dan bukan hanya hash/fragment)
            url_before_base = url_before.split('#')[0].split('?')[0].strip().rstrip('/')
            url_after_base = url_after.split('#')[0].split('?')[0].strip().rstrip('/')
            
            # Jika URL benar-benar berbeda, pasti berhasil
            if url_before_base != url_after_base:
                print(f"   ✅ URL berubah: {url_before_base} → {url_after_base}")
                return True
            
            # Jika URL sama, HARUS ada indikator kuat di halaman
            try:
                page_source = self.driver.page_source.lower()
                
                # Indikator SANGAT KUAT (harus ada salah satu)
                very_strong_indicators = [
                    'widget.loket.com/widget/',  # URL widget di page source
                    'https://widget.loket.com',  # Full URL widget
                    'loket.com/widget/',         # Variasi URL widget
                ]
                
                for indicator in very_strong_indicators:
                    if indicator in page_source:
                        print(f"   ✅ Indikator kuat ditemukan: '{indicator}'")
                        return True
                
                # Cek iframe dengan src widget loket (lebih reliable)
                try:
                    iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                    for iframe in iframes:
                        src = (iframe.get_attribute('src') or '').lower()
                        if 'widget.loket.com' in src or ('loket.com' in src and 'widget' in src):
                            print(f"   ✅ Iframe widget Loket ditemukan: {src[:80]}...")
                            return True
                except:
                    pass
                
                # Cek elemen dengan class/id yang spesifik widget loket
                try:
                    widget_elements = self.driver.find_elements(By.XPATH, 
                        "//*[contains(@class, 'loket') or contains(@id, 'loket') or contains(@class, 'widget')]")
                    if len(widget_elements) > 0:
                        # Cek apakah elemen ini benar-benar widget loket
                        for elem in widget_elements[:3]:
                            elem_html = (elem.get_attribute('innerHTML') or '').lower()
                            if 'widget.loket.com' in elem_html or 'loket.com/widget' in elem_html:
                                print(f"   ✅ Elemen widget Loket ditemukan")
                                return True
                except:
                    pass
                
                # Jika tidak ada indikator kuat, TIDAK BERHASIL
                print(f"   ❌ URL sama dan tidak ada indikator kuat widget Loket")
                return False
                
            except Exception as e:
                print(f"   ⚠️ Error checking indicators: {e}")
                return False
            
        except Exception as e:
            print(f"   ⚠️ Error verifying page change: {e}")
            return False
    
    def handle_widget_loket_auto_buy(self):
        """Handle auto beli tiket setelah widget Loket terbuka"""
        print("\n" + "="*60)
        print("🎫 WIDGET LOKET TERBUKA!")
        print("="*60)
        print(f"📍 URL: {self.driver.current_url}")
        print("\n💡 Bot dapat membantu auto beli tiket!")
        print("="*60)
        
        # Tanya apakah mau auto beli
        auto_buy = input("\n🤖 Ingin bot auto beli tiket? (y/n): ").strip().lower()
        
        if auto_buy == 'y':
            # Pilih kategori tiket dengan nomor
            self.random_delay(1, 2)
            ticket_categories = self._collect_ticket_categories()
            
            if ticket_categories:
                print("\n📋 Daftar kategori tiket (pilih nomor):")
                for idx, name in enumerate(ticket_categories, 1):
                    print(f"   {idx}. {name}")
                
                choice = input("\n🎫 Masukkan nomor kategori tiket: ").strip()
                if not choice.isdigit():
                    print("❌ Input harus angka sesuai daftar!")
                    return
                
                choice_idx = int(choice)
                if choice_idx < 1 or choice_idx > len(ticket_categories):
                    print("❌ Nomor kategori tidak valid!")
                    return
                
                ticket_category = ticket_categories[choice_idx - 1]
                print(f"✅ Dipilih: {ticket_category}")
            else:
                # Fallback manual jika daftar tidak terbaca
                print("\n📋 Kategori tiket yang tersedia (contoh):")
                print("   - FANTASY VIP A PACKAGE")
                print("   - FANTASY VIP B PACKAGE")
                print("   - ORANGE A")
                print("   - ORANGE B")
                print("   - YELLOW")
                print("   - PINK B")
                
                ticket_category = input("\n🎫 Masukkan nama kategori tiket yang ingin dibeli: ").strip()
                if not ticket_category:
                    print("❌ Kategori tiket tidak boleh kosong!")
                    return
            
            # Input jumlah tiket
            try:
                ticket_quantity = int(input("🔢 Masukkan jumlah tiket (1-6): ").strip())
                if ticket_quantity < 1 or ticket_quantity > 6:
                    print("⚠️ Jumlah tiket harus antara 1-6, menggunakan 1")
                    ticket_quantity = 1
            except:
                print("⚠️ Input tidak valid, menggunakan 1 tiket")
                ticket_quantity = 1
            
            print(f"\n✅ Konfigurasi auto beli:")
            print(f"   Kategori: {ticket_category}")
            print(f"   Jumlah: {ticket_quantity}")
            print("\n🚀 Memulai auto beli tiket...")
            
            # Mulai auto beli
            self.auto_buy_ticket(ticket_category, ticket_quantity)
        else:
            print("\n✅ Bot akan berhenti. Silakan beli tiket manual.")
    
    def auto_buy_ticket(self, category_name, quantity):
        """Auto beli tiket di widget Loket"""
        print("\n" + "="*60)
        print("🔄 AUTO BELI TIKET")
        print("="*60)
        print(f"📋 Kategori: {category_name}")
        print(f"🔢 Jumlah: {quantity}")
        print("="*60 + "\n")
        
        attempt = 0
        max_attempts = 1000  # Loop sampai berhasil
        
        while attempt < max_attempts:
            attempt += 1
            current_time = datetime.now().strftime('%H:%M:%S')
            
            print(f"[{current_time}] Percobaan #{attempt} - Refresh dan cari kategori '{category_name}'...")
            
            try:
                # Refresh halaman
                self.driver.refresh()
                delay = self.random_delay(2, 5)
                print(f"   ⏳ Menunggu {delay:.1f} detik setelah refresh...")
                
                # Cari kategori tiket
                category_found = self.find_and_select_ticket_category(category_name, quantity)
                
                if category_found:
                    print("\n" + "="*60)
                    print("🎉 BERHASIL! Kategori tiket ditemukan dan dipilih!")
                    print("="*60)
                    print(f"📋 Kategori: {category_name}")
                    print(f"🔢 Jumlah: {quantity}")
                    print("\n✅ Bot akan berhenti. Silakan lanjutkan pembayaran manual.")
                    print("="*60 + "\n")
                    
                    # Notifikasi suara
                    try:
                        import os
                        for _ in range(5):
                            os.system('afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || echo "\\a"')
                            self.random_delay(0.1, 0.3)
                    except:
                        pass
                    
                    break
                else:
                    print(f"   ⚠️ Kategori '{category_name}' belum tersedia atau belum bisa dipilih")
                    print(f"   🔄 Refresh dan coba lagi...")
                    
            except KeyboardInterrupt:
                print("\n\n⚠️ Auto beli dihentikan oleh user")
                break
            except Exception as e:
                print(f"   ⚠️ Error: {e}")
                self.random_delay(2, 3)
    
    def _extract_first_int(self, text):
        """Ambil angka pertama dari string"""
        try:
            match = re.search(r"\d+", str(text))
            if not match:
                return None
            return int(match.group(0))
        except:
            return None

    def _looks_like_price(self, text):
        """Deteksi teks yang terlihat seperti harga"""
        try:
            text_lower = str(text).strip().lower()
            if not text_lower:
                return True
            if 'rp' in text_lower or 'idr' in text_lower:
                return True
            if re.fullmatch(r"[0-9.,\s]+", text_lower):
                return True
        except:
            pass
        return False

    def _collect_ticket_categories(self):
        """Ambil daftar kategori tiket yang tersedia dari widget"""
        categories = []
        seen = set()

        def add_candidate(name):
            if not name:
                return
            cleaned = re.sub(r"\s+", " ", str(name)).strip()
            if not cleaned:
                return
            if self._looks_like_price(cleaned):
                return
            key = cleaned.lower()
            if key in seen:
                return
            seen.add(key)
            categories.append(cleaned)

        try:
            heading_elements = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'ticket-item')]//h4 | "
                "//div[contains(@class, 'ticket-item')]//h5 | "
                "//div[contains(@class, 'ticket-item')]//h6",
            )
            for heading in heading_elements:
                add_candidate(heading.text)
        except:
            pass

        try:
            data_name_elements = self.driver.find_elements(By.XPATH, "//*[@data-ticket-name]")
            for elem in data_name_elements:
                add_candidate(elem.get_attribute('data-ticket-name'))
        except:
            pass

        try:
            ticket_name_elements = self.driver.find_elements(By.XPATH, "//*[@ticket-name]")
            for elem in ticket_name_elements:
                add_candidate(elem.get_attribute('ticket-name'))
        except:
            pass

        return categories
    
    def _dispatch_input_change(self, element):
        """Trigger input/change event setelah value diubah"""
        try:
            self.driver.execute_script(
                "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
                element,
            )
            self.driver.execute_script(
                "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                element,
            )
        except:
            pass
    
    def _set_quantity_from_select(self, select_elem, quantity):
        """Set quantity dari elemen <select>"""
        try:
            if select_elem.get_attribute('disabled') is not None:
                return False
            if (select_elem.get_attribute('aria-disabled') or '').lower() == 'true':
                return False
        except:
            pass
        
        try:
            select = Select(select_elem)
        except:
            return False
        
        target_str = str(quantity)
        
        try:
            current_value = select_elem.get_attribute('value') or ''
            if self._extract_first_int(current_value) == quantity:
                return True
        except:
            pass
        
        for opt in select.options:
            value = (opt.get_attribute('value') or '').strip()
            text = (opt.text or '').strip()
            if value == target_str:
                select.select_by_value(value)
                self._dispatch_input_change(select_elem)
                return True
            if text == target_str:
                select.select_by_visible_text(text)
                self._dispatch_input_change(select_elem)
                return True
        
        for idx, opt in enumerate(select.options):
            value = (opt.get_attribute('value') or '').strip()
            text = (opt.text or '').strip()
            num = self._extract_first_int(value) or self._extract_first_int(text)
            if num == quantity:
                try:
                    select.select_by_index(idx)
                except:
                    try:
                        opt.click()
                    except:
                        return False
                self._dispatch_input_change(select_elem)
                return True
        
        return False
    
    def _click_agree_popup(self, timeout_seconds=6):
        """Klik tombol Agree pada popup (jika muncul)"""
        end_time = time.time() + timeout_seconds
        
        while time.time() < end_time:
            try:
                agree_btn = self.driver.find_element(By.ID, "btn-agree-tnc")
                if agree_btn and agree_btn.is_displayed():
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        agree_btn,
                    )
                    self.random_delay(0.2, 0.4)
                    try:
                        agree_btn.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", agree_btn)
                    print("   ✅ Popup T&C terdeteksi, klik 'Agree'")
                    self.random_delay(0.5, 1)
                    return True
            except:
                pass
            
            try:
                agree_buttons = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(., 'Agree') or contains(., 'Setuju') or contains(., 'I Agree')]",
                )
                for btn in agree_buttons:
                    try:
                        if not btn.is_displayed():
                            continue
                    except:
                        pass
                    
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        btn,
                    )
                    self.random_delay(0.2, 0.4)
                    try:
                        btn.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", btn)
                    print("   ✅ Popup terdeteksi, klik tombol Agree")
                    self.random_delay(0.5, 1)
                    return True
            except:
                pass
            
            self.random_delay(0.2, 0.5)
        
        return False
    
    def find_and_select_ticket_category(self, category_name, quantity):
        """Cari dan pilih kategori tiket di widget Loket"""
        try:
            category_upper = category_name.upper()
            
            # Cari kategori dengan berbagai metode
            target_section = None
            
            # Method 1: Cari heading (h4, h5, h6) yang mengandung nama kategori
            try:
                headings = self.driver.find_elements(By.XPATH, "//h4 | //h5 | //h6")
                for heading in headings:
                    text = heading.text.strip().upper()
                    if category_upper in text:
                        # Cari parent section yang berisi kategori ini
                        try:
                            # Cari ancestor yang berisi input quantity dan button order
                            section = heading.find_element(By.XPATH, 
                                "./ancestor::*[.//input[@type='number'] or .//select or .//button[contains(text(), 'Order')]][1]")
                            target_section = section
                            break
                        except:
                            # Jika tidak ada, gunakan heading sebagai starting point
                            target_section = heading
                            break
            except:
                pass
            
            # Method 2: Cari dengan text langsung di seluruh halaman
            if not target_section:
                try:
                    # Cari elemen yang mengandung text kategori
                    elements = self.driver.find_elements(By.XPATH, 
                        f"//*[contains(text(), '{category_name}')]")
                    
                    for elem in elements:
                        text = elem.text.strip().upper()
                        if category_upper in text:
                            # Cari section yang berisi elemen ini dan memiliki input quantity
                            try:
                                section = elem.find_element(By.XPATH, 
                                    "./ancestor::*[.//input[@type='number'] or .//select or .//button[contains(text(), 'Order')]][1]")
                                target_section = section
                                break
                            except:
                                target_section = elem
                                break
                except:
                    pass
            
            if not target_section:
                print(f"   ❌ Kategori '{category_name}' tidak ditemukan")
                return False
            
            print(f"   ✅ Kategori '{category_name}' ditemukan!")
            
            # Scroll ke section
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target_section)
            self.random_delay(0.5, 1)
            
            # Cari dan set quantity
            quantity_set = False
            try:
                # Cari input number untuk quantity (biasanya ada di dekat kategori)
                # Cari di section target atau di seluruh halaman dekat kategori
                quantity_inputs = target_section.find_elements(By.XPATH, 
                    ".//input[@type='number'] | .//input[contains(@class, 'quantity')] | .//input[contains(@name, 'quantity')]")
                
                # Jika tidak ada di section, cari di seluruh halaman setelah kategori
                if not quantity_inputs:
                    # Cari semua input number di halaman
                    all_inputs = self.driver.find_elements(By.XPATH, "//input[@type='number']")
                    # Ambil yang paling dekat dengan kategori (bisa jadi beberapa input untuk beberapa kategori)
                    if all_inputs:
                        # Coba input pertama yang terlihat (biasanya sesuai urutan kategori)
                        quantity_inputs = [all_inputs[0]]
                
                if quantity_inputs:
                    for qty_input in quantity_inputs:
                        try:
                            current_value = qty_input.get_attribute('value') or ''
                            if self._extract_first_int(current_value) == quantity:
                                print(f"   ✅ Jumlah tiket sudah {quantity}")
                                quantity_set = True
                                self.random_delay(0.3, 0.6)
                                break
                            
                            # Set quantity dengan JavaScript
                            self.driver.execute_script(f"arguments[0].value = {quantity};", qty_input)
                            self._dispatch_input_change(qty_input)
                            
                            # Verifikasi value sudah ter-set
                            value = qty_input.get_attribute('value')
                            if self._extract_first_int(value) == quantity:
                                print(f"   ✅ Jumlah tiket di-set ke {quantity}")
                                quantity_set = True
                                self.random_delay(0.5, 1)
                                break
                        except:
                            continue
                
                # Jika tidak ada input number, coba dropdown <select>
                if not quantity_set:
                    try:
                        select_elements = target_section.find_elements(
                            By.XPATH,
                            ".//select[contains(@class, 'ticket-types') or contains(@name, 'ticket[') or contains(@id, 'ticket_')] | .//select",
                        )
                        if select_elements:
                            for select_elem in select_elements:
                                try:
                                    if not select_elem.is_displayed():
                                        continue
                                except:
                                    pass
                                
                                if self._set_quantity_from_select(select_elem, quantity):
                                    print(f"   ✅ Jumlah tiket di-set ke {quantity} (via dropdown)")
                                    quantity_set = True
                                    self.random_delay(0.5, 1)
                                    break
                    except:
                        pass
                
                # Jika tidak ada input, coba klik button +/- untuk set quantity
                if not quantity_set:
                    try:
                        # Cari button dengan angka yang sesuai quantity
                        buttons = target_section.find_elements(By.XPATH, 
                            f".//button[text()='{quantity}'] | .//button[contains(@aria-label, '{quantity}')]")
                        if buttons:
                            buttons[0].click()
                            print(f"   ✅ Jumlah tiket di-set ke {quantity} (via button)")
                            quantity_set = True
                            self.random_delay(0.5, 1)
                    except:
                        pass
                
            except Exception as e:
                print(f"   ⚠️ Error setting quantity: {e}")
            
            # Cari dan klik tombol Order Now
            try:
                # Cari tombol Order Now di section atau di seluruh halaman
                order_buttons = target_section.find_elements(By.XPATH, 
                    ".//button[contains(., 'Order') or contains(., 'Pesan')] | " +
                    ".//a[contains(., 'Order') or contains(., 'Pesan')]")
                
                # Jika tidak ada di section, cari di seluruh halaman
                if not order_buttons:
                    order_buttons = self.driver.find_elements(By.XPATH, 
                        "//button[contains(., 'Order Now')] | //button[contains(., 'Order')] | " +
                        "//a[contains(., 'Order Now')]")
                
                if order_buttons:
                    order_btn = order_buttons[0]
                    print(f"   🖱️ Mengklik tombol Order Now...")
                    
                    # Scroll ke tombol
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", order_btn)
                    self.random_delay(0.5, 1)
                    
                    # Klik tombol dengan beberapa metode
                    clicked = False
                    try:
                        order_btn.click()
                        clicked = True
                    except:
                        try:
                            self.driver.execute_script("arguments[0].click();", order_btn)
                            clicked = True
                        except:
                            try:
                                from selenium.webdriver.common.action_chains import ActionChains
                                ActionChains(self.driver).move_to_element(order_btn).click().perform()
                                clicked = True
                            except:
                                pass
                    
                    if clicked:
                        self.random_delay(2, 4)
                        print(f"   ✅ Tombol Order Now diklik!")
                        
                        # Jika muncul popup T&C, langsung klik Agree
                        self._click_agree_popup(timeout_seconds=8)
                        
                        # Cek apakah berhasil (halaman checkout/personal information muncul)
                        self.random_delay(1, 2)
                        page_source = self.driver.page_source.lower()
                        if any(keyword in page_source for keyword in ['personal information', 'confirmation', 'checkout', 'select category']):
                            print(f"   ✅ Halaman checkout/pembelian terdeteksi!")
                            return True
                        
                        # Cek apakah URL berubah
                        current_url = self.driver.current_url
                        if 'checkout' in current_url.lower() or 'personal' in current_url.lower():
                            return True
                        
                        return True
                    else:
                        print(f"   ⚠️ Gagal mengklik tombol Order")
                        return False
                else:
                    print(f"   ⚠️ Tombol Order Now tidak ditemukan")
                    return False
                    
            except Exception as e:
                print(f"   ⚠️ Error saat klik Order: {e}")
                return False
            
        except Exception as e:
            print(f"   ⚠️ Error mencari kategori: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def monitor_after_click(self):
        """Monitor setelah tombol diklik"""
        print("\n👀 Memonitor perubahan halaman...")
        initial_url = self.driver.current_url
        
        for i in range(15):  # Monitor selama 15 x random delay
            try:
                current_url = self.driver.current_url
                if current_url != initial_url and current_url.split('#')[0] != initial_url.split('#')[0]:
                    print(f"\n✅ URL berubah! Halaman baru: {current_url}")
                    break
                
                # Cek apakah ada elemen checkout/pembelian
                page_source = self.driver.page_source.lower()
                if any(keyword in page_source for keyword in ['checkout', 'pembelian', 'order now', 'select category', 'widget.loket.com']):
                    print("\n✅ Halaman pembelian/widget terdeteksi!")
                    break
                
                self.random_delay(2, 3)
            except:
                self.random_delay(2, 3)


def main():
    """Main function"""
    print("="*60)
    print("🤖 BOT PENCARI TOMBOL LOKET.COM")
    print("="*60)
    print()
    
    # Input parameter 1: Link konser
    concert_url = input("📍 Masukkan Link Konser: ").strip()
    if not concert_url:
        print("❌ Link konser tidak boleh kosong!")
        return
    
    if not concert_url.startswith('http'):
        concert_url = 'https://' + concert_url
    
    print()
    
    # Input parameter 2: Text tombol
    button_text = input("🔘 Masukkan Text Tombol yang ingin dicari (contoh: 'Beli Tiket', 'Order Now', 'Masuk Antrean'): ").strip()
    if not button_text:
        print("❌ Text tombol tidak boleh kosong!")
        return
    
    print()
    print("="*60)
    print(f"✅ Konfigurasi:")
    print(f"   Link: {concert_url}")
    print(f"   Tombol: '{button_text}'")
    print("="*60)
    print()
    
    # Konfirmasi
    confirm = input("🚀 Jalankan bot sekarang? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Dibatalkan")
        return
    
    print()
    
    # Jalankan bot
    bot = SimpleButtonBot(concert_url, button_text)
    bot.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Program dihentikan")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

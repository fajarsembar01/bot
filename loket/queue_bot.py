"""
Bot untuk mendapatkan antrian awal di Loket.com
"""
import time
import sys
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
try:
    from . import config
except ImportError:
    try:
        from loket import config
    except ImportError:
        import config


class LoketQueueBot:
    def __init__(self, url=None, headless=None, widget_url=None):
        self.url = url or config.CONCERT_URL
        self.widget_url = widget_url or config.WIDGET_URL
        self.headless = headless if headless is not None else config.HEADLESS
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Setup Chrome WebDriver dengan konfigurasi optimal"""
        print("🔧 Setting up browser...")
        chrome_options = Options()
        
        # Headless mode (opsional)
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Anti-detection options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(f"--user-agent={config.USER_AGENT}")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Prefs untuk menghindari deteksi
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.maximize_window()
            
            # Execute script untuk menghindari deteksi
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            
            self.wait = WebDriverWait(self.driver, 10)
            print("✅ Browser setup berhasil!")
            return True
        except Exception as e:
            print(f"❌ Error setting up browser: {e}")
            return False
    
    def check_waiting_room_available(self):
        """Cek apakah waiting room sudah tersedia atau link ke widget Loket"""
        try:
            # PRIORITAS 1: Cari link yang mengarah ke widget.loket.com atau loket.com/widget
            print("🔍 Mencari link ke widget Loket...")
            js_check_loket_widget = """
            var links = document.querySelectorAll('a[href], button[onclick], div[onclick], span[onclick]');
            for (var i = 0; i < links.length; i++) {
                var href = links[i].href || links[i].getAttribute('href') || '';
                var onclick = links[i].getAttribute('onclick') || '';
                var text = links[i].textContent.toLowerCase();
                
                // Cek href atau onclick yang mengandung widget.loket.com
                if (href.includes('widget.loket.com') || 
                    href.includes('loket.com/widget') || 
                    href.includes('loket.com/event') ||
                    onclick.includes('widget.loket.com') ||
                    onclick.includes('loket.com/widget')) {
                    console.log('Found Loket widget link:', href || onclick);
                    return links[i];
                }
                
                // Cek text yang mengandung "beli", "buy", "ticket", "pesan"
                if ((text.includes('beli') || text.includes('buy') || 
                     text.includes('ticket') || text.includes('pesan') ||
                     text.includes('get ticket') || text.includes('order now') ||
                     text.includes('booking')) && 
                    (href || onclick)) {
                    console.log('Found ticket link:', text, href || onclick);
                    return links[i];
                }
            }
            return null;
            """
            
            element = self.driver.execute_script(js_check_loket_widget)
            if element:
                href = element.get_attribute('href') or element.get_attribute('onclick') or ''
                print(f"✅ Ditemukan link ke Loket: {href[:100]}...")
                return element
            
            # PRIORITAS 2: Cari dengan XPath untuk link loket
            try:
                loket_links = self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(@href, 'widget.loket.com') or contains(@href, 'loket.com/widget') or contains(@href, 'loket.com/event')]"
                )
                if loket_links:
                    print(f"✅ Ditemukan {len(loket_links)} link ke Loket via XPath")
                    return loket_links[0]
            except:
                pass
            
            # PRIORITAS 3: Cari button/link dengan text "Beli", "Buy", "Ticket", dll
            ticket_keywords = ['beli', 'buy', 'ticket', 'pesan', 'booking', 'order', 'purchase', 'get ticket']
            elements = self.driver.find_elements(By.TAG_NAME, "button")
            elements.extend(self.driver.find_elements(By.TAG_NAME, "a"))
            elements.extend(self.driver.find_elements(By.XPATH, "//div[@onclick] | //span[@onclick]"))
            
            for elem in elements:
                try:
                    text = elem.text.lower().strip()
                    href = elem.get_attribute('href') or ''
                    onclick = elem.get_attribute('onclick') or ''
                    
                    # Cek jika ada keyword dan memiliki action
                    if any(keyword in text for keyword in ticket_keywords) and (href or onclick):
                        print(f"✅ Ditemukan tombol tiket: '{text[:50]}...'")
                        return elem
                except:
                    continue
            
            # PRIORITAS 4: Cek iframe yang mungkin mengandung widget loket
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    src = iframe.get_attribute('src') or ''
                    if 'loket.com' in src or 'widget' in src:
                        print(f"✅ Ditemukan iframe Loket: {src[:100]}...")
                        # Switch ke iframe dan cari button di dalamnya
                        self.driver.switch_to.frame(iframe)
                        inner_elements = self.driver.find_elements(By.TAG_NAME, "button")
                        inner_elements.extend(self.driver.find_elements(By.TAG_NAME, "a"))
                        for inner_elem in inner_elements:
                            text = inner_elem.text.lower()
                            if any(keyword in text for keyword in ['beli', 'buy', 'order', 'ticket']):
                                self.driver.switch_to.default_content()
                                return inner_elem
                        self.driver.switch_to.default_content()
            except Exception as e:
                print(f"⚠️ Error checking iframe: {e}")
            
            # PRIORITAS 5: Cek tombol waiting room / antrean (backup)
            js_check_waiting = """
            var buttons = document.querySelectorAll('button, a');
            for (var i = 0; i < buttons.length; i++) {
                var text = buttons[i].textContent.toLowerCase();
                if (text.includes('antrean') || text.includes('queue') || 
                    text.includes('masuk') || text.includes('waiting') ||
                    text.includes('join')) {
                    return buttons[i];
                }
            }
            return null;
            """
            
            element = self.driver.execute_script(js_check_waiting)
            if element:
                print("✅ Ditemukan tombol waiting room")
                return element
                    
            return None
        except Exception as e:
            print(f"⚠️ Error checking waiting room: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def enter_waiting_room(self):
        """Masuk ke waiting room atau widget Loket"""
        try:
            print("🔍 Mencari tombol/link ke Loket widget...")
            element = self.check_waiting_room_available()
            
            if element:
                # Cek apakah ini link langsung ke widget loket
                href = None
                onclick = None
                try:
                    href = element.get_attribute('href')
                    onclick = element.get_attribute('onclick')
                except:
                    pass
                
                # Jika ada href ke widget loket, langsung navigate
                if href and ('widget.loket.com' in href or 'loket.com/widget' in href):
                    print(f"✅ Link widget Loket ditemukan! Mengarahkan ke: {href}")
                    self.driver.get(href)
                    time.sleep(3)
                    return True
                
                # Jika ada onclick yang mengarah ke widget loket
                if onclick and ('widget.loket.com' in onclick or 'loket.com/widget' in onclick):
                    print("✅ Onclick handler ditemukan! Menjalankan...")
                    self.driver.execute_script(onclick)
                    time.sleep(3)
                    return True
                
                # Jika tidak, coba klik element
                print("✅ Element ditemukan! Mengklik...")
                # Scroll ke element terlebih dahulu
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                    time.sleep(1)
                except:
                    pass
                
                # Coba beberapa metode klik
                try:
                    # Method 1: Klik normal
                    element.click()
                except:
                    try:
                        # Method 2: JavaScript click
                        self.driver.execute_script("arguments[0].click();", element)
                    except:
                        try:
                            # Method 3: Action chains
                            from selenium.webdriver.common.action_chains import ActionChains
                            ActionChains(self.driver).move_to_element(element).click().perform()
                        except Exception as e:
                            print(f"⚠️ Error clicking element: {e}")
                            return False
                
                time.sleep(3)
                
                # Cek apakah sudah redirect ke widget loket
                current_url = self.driver.current_url
                if 'widget.loket.com' in current_url or 'loket.com/widget' in current_url:
                    print(f"✅ Berhasil masuk ke widget Loket: {current_url}")
                    return True
                
                return True
            else:
                # Coba cari langsung di page source apakah ada URL widget loket
                try:
                    page_source = self.driver.page_source
                    # Cari pattern widget.loket.com/widget/xxxxx
                    widget_pattern = r'https?://widget\.loket\.com/widget/[a-zA-Z0-9]+'
                    matches = re.findall(widget_pattern, page_source)
                    if matches:
                        widget_url = matches[0]
                        print(f"✅ Ditemukan URL widget di page source: {widget_url}")
                        print("🌐 Membuka widget Loket langsung...")
                        self.driver.get(widget_url)
                        time.sleep(3)
                        return True
                    
                    # Cari pattern loket.com/widget/xxxxx
                    loket_pattern = r'https?://[^"\'\\s]*loket\.com[^"\'\\s]*widget[^"\'\\s]*/[a-zA-Z0-9]+'
                    matches = re.findall(loket_pattern, page_source)
                    if matches:
                        widget_url = matches[0]
                        print(f"✅ Ditemukan URL Loket di page source: {widget_url}")
                        print("🌐 Membuka widget Loket langsung...")
                        self.driver.get(widget_url)
                        time.sleep(3)
                        return True
                except Exception as e:
                    print(f"⚠️ Error searching page source: {e}")
                
                print("⏳ Link/widget Loket belum ditemukan...")
                return False
        except Exception as e:
            print(f"❌ Error entering waiting room: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def monitor_queue(self):
        """Monitor status antrian di widget Loket"""
        print("👀 Memonitor status antrian di widget Loket...")
        
        last_status = ""
        check_count = 0
        
        while True:
            try:
                check_count += 1
                current_url = self.driver.current_url
                page_source = self.driver.page_source.lower()
                
                # Cek apakah sudah masuk ke halaman checkout/pembelian
                checkout_indicators = [
                    "checkout" in current_url,
                    "select category" in page_source,
                    "personal information" in page_source,
                    "confirmation" in page_source,
                    "order now" in page_source,
                    "subticket" in page_source,
                ]
                
                if any(checkout_indicators):
                    print("\n🎉 BERHASIL! Anda telah masuk ke halaman pembelian!")
                    print(f"📍 URL: {current_url}")
                    self.notify_success()
                    break
                
                # Cek apakah ada button "Order Now" atau tombol beli tiket
                try:
                    order_buttons = self.driver.find_elements(
                        By.XPATH,
                        "//button[contains(text(), 'Order Now') or contains(text(), 'Beli') or contains(text(), 'Pesan')]"
                    )
                    if order_buttons and any(btn.is_displayed() for btn in order_buttons):
                        print("\n🎉 Tombol Order/Beli ditemukan! Anda bisa mulai membeli tiket!")
                        print("⚠️ Silakan pilih kategori tiket dan lanjutkan pembelian manual")
                        self.notify_success()
                        break
                except:
                    pass
                
                # Cek status antrian/waiting room di widget
                try:
                    # Cek berbagai elemen status
                    status_selectors = [
                        "//*[contains(@class, 'queue') or contains(@class, 'antrean')]",
                        "//*[contains(text(), 'Antrean') or contains(text(), 'Queue')]",
                        "//*[contains(text(), 'Posisi') or contains(text(), 'Position')]",
                        "//*[contains(text(), 'Menunggu') or contains(text(), 'Waiting')]",
                        "//*[contains(text(), 'Anda berada di')]",
                    ]
                    
                    status_found = False
                    for selector in status_selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for elem in elements[:2]:
                                if elem.is_displayed():
                                    text = elem.text.strip()
                                    if text and len(text) < 150 and text != last_status:
                                        print(f"📊 Status: {text}")
                                        last_status = text
                                        status_found = True
                                        break
                            if status_found:
                                break
                        except:
                            continue
                    
                    # Jika tidak ada status, cek apakah sudah ada kategori tiket yang muncul
                    if not status_found:
                        try:
                            category_elements = self.driver.find_elements(
                                By.XPATH,
                                "//*[contains(text(), 'VIP') or contains(text(), 'Package') or contains(text(), 'Orange') or contains(text(), 'Blue')]"
                            )
                            if category_elements:
                                print("✅ Kategori tiket sudah muncul! Siap untuk dibeli!")
                        except:
                            pass
                    
                except Exception as e:
                    if check_count % 10 == 0:  # Print error setiap 10 kali check
                        print(f"⚠️ Error checking status: {e}")
                
                # Ambil screenshot setiap 30 detik untuk monitoring
                if check_count % 15 == 0:  # Setiap 30 detik (15 x 2 detik)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    try:
                        screenshot_path = f"screenshot_{timestamp}.png"
                        self.driver.save_screenshot(screenshot_path)
                        print(f"📸 Screenshot disimpan: {screenshot_path}")
                    except:
                        pass
                
                # Print status setiap 10 detik
                if check_count % 5 == 0:
                    print(f"⏳ Monitoring... (Cek ke-{check_count}, URL: {current_url[:60]}...)")
                
                time.sleep(2)
                
            except WebDriverException as e:
                print(f"⚠️ WebDriver error: {e}")
                print("🔄 Mencoba refresh halaman...")
                self.driver.refresh()
                time.sleep(5)
            except KeyboardInterrupt:
                print("\n⚠️ Bot dihentikan oleh user")
                break
            except Exception as e:
                print(f"⚠️ Error monitoring: {e}")
                time.sleep(5)
    
    def notify_success(self):
        """Notifikasi ketika berhasil masuk"""
        print("\n" + "="*50)
        print("🎉 BERHASIL MASUK KE HALAMAN PEMBELIAN!")
        print("="*50)
        print("\n⚠️ PENTING:")
        print("1. Jangan tutup browser ini")
        print("2. Selesaikan pembelian tiket dengan cepat")
        print("3. Pastikan informasi pembayaran sudah siap")
        print("\n" + "="*50)
        
        # Beep sound (jika di macOS/Linux)
        try:
            import os
            os.system('afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || echo "\\a"')
        except:
            pass
    
    def start(self):
        """Mulai bot"""
        print("="*50)
        print("🤖 BOT ANTRIAN LOKET.COM")
        print("="*50)
        print(f"📍 URL Target: {self.url}")
        print(f"🕐 Waktu mulai: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50 + "\n")
        
        if not self.setup_driver():
            return False
        
        try:
            # Jika ada widget URL langsung, gunakan itu
            if self.widget_url and 'widget.loket.com' in self.widget_url:
                print(f"🌐 Membuka widget Loket langsung: {self.widget_url}")
                self.driver.get(self.widget_url)
                time.sleep(3)
                print("✅ Langsung masuk ke widget Loket, mulai monitoring...")
                self.monitor_queue()
                return
            
            print(f"🌐 Membuka halaman: {self.url}")
            self.driver.get(self.url)
            time.sleep(3)
            
            # Cek apakah perlu login terlebih dahulu
            print("🔍 Mengecek status login...")
            login_required = self.check_login_required()
            
            if login_required:
                print("⚠️ Sepertinya perlu login terlebih dahulu")
                print("⚠️ Silakan login manual di browser, lalu tekan Enter untuk melanjutkan...")
                input()
            
            # Loop untuk masuk ke waiting room
            max_attempts = 100
            attempt = 0
            
            while attempt < max_attempts:
                attempt += 1
                print(f"\n🔄 Percobaan ke-{attempt}...")
                
                # Refresh halaman setiap beberapa detik untuk cek waiting room
                if attempt > 1:
                    print("🔄 Refresh halaman...")
                    self.driver.refresh()
                    time.sleep(config.WAIT_TIME)
                
                # Coba masuk waiting room
                if self.enter_waiting_room():
                    print("✅ Berhasil masuk waiting room!")
                    time.sleep(3)
                    
                    # Monitor queue
                    self.monitor_queue()
                    break
                else:
                    wait_time = config.WAIT_TIME
                    print(f"⏳ Menunggu {wait_time} detik sebelum coba lagi...")
                    time.sleep(wait_time)
            
            if attempt >= max_attempts:
                print("❌ Mencapai batas maksimum percobaan")
                
        except KeyboardInterrupt:
            print("\n⚠️ Bot dihentikan oleh user")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            print("\n⚠️ Tutup browser? (y/n): ", end="")
            try:
                response = input().strip().lower()
                if response == 'y':
                    self.cleanup()
                else:
                    print("✅ Browser tetap terbuka. Silakan gunakan manual.")
            except:
                self.cleanup()
    
    def check_login_required(self):
        """Cek apakah perlu login"""
        try:
            # Cek apakah ada tombol login yang terlihat
            login_elements = self.driver.find_elements(
                By.XPATH,
                "//a[contains(@href, 'login') or contains(text(), 'Login') or contains(text(), 'Masuk')]"
            )
            return len(login_elements) > 0
        except:
            return False
    
    def cleanup(self):
        """Bersihkan resources"""
        if self.driver:
            print("🧹 Menutup browser...")
            self.driver.quit()
            print("✅ Browser ditutup")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Bot Antrian Loket.com')
    parser.add_argument('--url', type=str, help='URL konser atau landing page (default: dari config)')
    parser.add_argument('--widget', type=str, help='URL widget Loket langsung (contoh: https://widget.loket.com/widget/xxxxx)')
    parser.add_argument('--headless', action='store_true', help='Jalankan dalam mode headless')
    parser.add_argument('--no-headless', action='store_true', help='Jalankan dengan browser terlihat')
    
    args = parser.parse_args()
    
    headless = config.HEADLESS
    if args.headless:
        headless = True
    elif args.no_headless:
        headless = False
    
    bot = LoketQueueBot(url=args.url, headless=headless, widget_url=args.widget)
    bot.start()


if __name__ == "__main__":
    main()

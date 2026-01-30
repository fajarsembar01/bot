"""
Bot Sederhana untuk Mencari Tombol di Halaman Konser Loket.com
Refresh setiap 0.5-4 detik (random) dan cari tombol berdasarkan text
Auto beli tiket setelah masuk widget Loket
"""
import time
import os
import sys
import random
import re
import shutil
from datetime import datetime
from threading import Event, Thread
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager


def is_macos():
    return sys.platform == "darwin"


def is_windows():
    return sys.platform.startswith("win")


def is_linux():
    return sys.platform.startswith("linux")


class SimpleButtonBot:
    def __init__(
        self,
        concert_url,
        button_text,
        auto_buy=False,
        ticket_category=None,
        ticket_quantity=1,
        debugger_address=None,
        open_new_tab=False,
        user_data_dir=None,
        stop_event=None,
        close_on_exit=None,
        aggressive_order=False,
        aggressive_click=False,
        skip_refresh=False,
        auto_detect_widget=False,
        on_order_click=None,
        interactive=True,
    ):
        self.concert_url = concert_url
        self.button_text = button_text
        self.button_text_lower = (button_text or "").strip().lower()
        self.auto_buy = auto_buy
        self.ticket_category = ticket_category
        self.ticket_quantity = ticket_quantity
        self.loop_delay_min = 0.5
        self.loop_delay_max = 4
        self.auto_buy_prompted = False
        self.debugger_address = debugger_address
        self.open_new_tab = open_new_tab
        self.user_data_dir = user_data_dir
        self.stop_event = stop_event
        self.close_on_exit = close_on_exit
        self.aggressive_order = aggressive_order
        self.aggressive_click = aggressive_click
        self.skip_refresh = skip_refresh
        self.skip_refresh_max_attempts = 5
        self.auto_detect_widget = auto_detect_widget
        self.interactive = interactive
        self.setup_success = False
        self.last_error = ""
        self.driver = None
        self.auto_buy_selection_event = Event()
        self.awaiting_auto_buy_selection = False
        self.widget_categories = []
        self.widget_ready = False
        self.auto_buy_running = False
        self.auto_buy_paused = False
        self._cached_buttons = []
        self.log_every = 5
        self.auto_buy_log_every = 5
        self.on_order_click = on_order_click
        self._order_click_notified = False
    
    def random_delay(self, min_seconds=0.5, max_seconds=4):
        """Random delay antara min dan max seconds"""
        if min_seconds < 0:
            min_seconds = 0
        if max_seconds < min_seconds:
            max_seconds = min_seconds
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        return round(delay, 1)

    def request_stop(self):
        """Request bot to stop gracefully."""
        if self.stop_event:
            self.stop_event.set()

    def pause_auto_buy(self):
        if not self.auto_buy_running:
            return False
        self.auto_buy_paused = True
        return True

    def resume_auto_buy(self):
        if not self.auto_buy_running:
            return False
        self.auto_buy_paused = False
        return True

    def set_auto_buy_selection(self, category, quantity):
        """Set auto-buy selection from external controller."""
        category = (category or "").strip()
        if not category:
            return False
        try:
            quantity = int(quantity)
        except:
            quantity = self.ticket_quantity or 1
        if quantity < 1 or quantity > 6:
            quantity = 1
        self.auto_buy = True
        self.ticket_category = category
        self.ticket_quantity = quantity
        self.awaiting_auto_buy_selection = False
        try:
            self.auto_buy_selection_event.set()
        except:
            pass
        return True

    def _should_stop(self):
        return self.stop_event is not None and self.stop_event.is_set()

    def _is_order_button_text(self, text):
        text = (text or "").lower().strip()
        if not text:
            return False
        keywords = [
            "pesan sekarang",
            "pesan sekarng",
            "order now",
            "buy now",
            "checkout",
            "pesan",
            "order",
            "beli",
            "buy",
            "booking",
            "purchase",
            "get ticket",
            "ticket",
        ]
        return any(keyword in text for keyword in keywords)

    def _maybe_trigger_order_click(self, text_hint=""):
        if self._order_click_notified or not self.on_order_click:
            return
        if self._is_order_button_text(text_hint) or self._is_order_button_text(self.button_text):
            self._order_click_notified = True
            try:
                Thread(target=self.on_order_click, daemon=True).start()
            except Exception as exc:
                print(f"⚠️ Auto-open Chrome gagal: {exc}")

    def setup_driver(self):
        """Setup Chrome WebDriver"""
        print("Browser...")
        chrome_options = Options()
        self.setup_success = False
        self.last_error = ""
        if self.debugger_address:
            chrome_options.add_experimental_option("debuggerAddress", self.debugger_address)
        else:
            # Anti-detection options
            if is_linux():
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--window-size=1200,800")
            # Kurangi throttle saat window/tab tidak fokus supaya klik tetap diproses
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            
            # User agent
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            if self.user_data_dir:
                chrome_options.add_argument(f"--user-data-dir={os.path.abspath(self.user_data_dir)}")
        
        try:
            driver_errors = []
            driver = None

            def init_with_timeout(label, fn, timeout_seconds=45):
                result = {"driver": None, "error": None}

                def runner():
                    try:
                        result["driver"] = fn()
                    except Exception as exc:
                        result["error"] = exc

                thread = Thread(target=runner, daemon=True)
                thread.start()
                thread.join(timeout_seconds)
                if thread.is_alive():
                    return None, f"{label} timeout after {timeout_seconds}s"
                if result["driver"] is None and result["error"]:
                    return None, f"{label} failed: {result['error']}"
                return result["driver"], ""

            chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "").strip()
            if chromedriver_path:
                service = Service(chromedriver_path)
                print("Driver: CHROMEDRIVER_PATH...")
                driver, err = init_with_timeout(
                    "CHROMEDRIVER_PATH",
                    lambda: webdriver.Chrome(service=service, options=chrome_options),
                )
                if err:
                    driver_errors.append(err)

            if not driver:
                path_driver = shutil.which("chromedriver") or shutil.which("chromedriver.exe")
                if path_driver:
                    service = Service(path_driver)
                    print("Driver: chromedriver (PATH)...")
                    driver, err = init_with_timeout(
                        "chromedriver (PATH)",
                        lambda: webdriver.Chrome(service=service, options=chrome_options),
                    )
                    if err:
                        driver_errors.append(err)

            if not driver:
                print("Driver: webdriver-manager...")
                def create_manager_driver():
                    service = Service(ChromeDriverManager().install())
                    return webdriver.Chrome(service=service, options=chrome_options)

                driver, err = init_with_timeout("webdriver-manager", create_manager_driver)
                if err:
                    driver_errors.append(err)

            if not driver:
                print("Driver: Selenium Manager...")
                driver, err = init_with_timeout(
                    "Selenium Manager",
                    lambda: webdriver.Chrome(options=chrome_options),
                )
                if err:
                    driver_errors.append(err)

            if not driver:
                raise Exception(" | ".join(driver_errors) or "Driver init failed")

            self.driver = driver
            if not self.debugger_address:
                self.driver.maximize_window()
            try:
                self.driver.set_page_load_timeout(30)
            except:
                pass
            
            # Anti-detection script
            try:
                self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        })
                    '''
                })
            except:
                pass

            if self.debugger_address and self.open_new_tab:
                if not self._open_new_tab():
                    print("Warning: gagal buka tab baru, lanjutkan tab aktif.")
            
            print("Browser siap")
            self.setup_success = True
            return True
        except Exception as e:
            self.last_error = str(e)
            if self.debugger_address:
                print(f"Error attach ke Chrome ({self.debugger_address}): {e}")
                print("Tip: jalankan Chrome dengan --remote-debugging-port=9222 dan --user-data-dir untuk session terpisah.")
            else:
                print(f"Error setting up browser: {e}")
            return False

    def _open_new_tab(self):
        """Buka tab baru lalu pindah ke tab tersebut."""
        try:
            self.driver.switch_to.new_window("tab")
            return True
        except:
            try:
                self.driver.execute_script("window.open('about:blank','_blank');")
                handles = self.driver.window_handles
                if handles:
                    self.driver.switch_to.window(handles[-1])
                    return True
            except:
                pass
        return False

    def _xpath_literal(self, text):
        if "'" not in text:
            return f"'{text}'"
        if '"' not in text:
            return f'"{text}"'
        parts = text.split("'")
        return "concat(" + ", \"'\", ".join(f"'{part}'" for part in parts) + ")"

    def _matches_button_text(self, elem):
        button_text_lower = self.button_text_lower
        if not button_text_lower:
            return False
        try:
            text = (elem.text or "").strip().lower()
            if text and (button_text_lower in text or text in button_text_lower):
                return True
        except:
            return False

        try:
            value = elem.get_attribute('value')
            if value and button_text_lower in value.lower():
                return True
        except:
            pass

        try:
            aria_label = elem.get_attribute('aria-label') or ''
            title = elem.get_attribute('title') or ''
            if button_text_lower in aria_label.lower() or button_text_lower in title.lower():
                return True
        except:
            pass

        return False

    def find_buttons_by_text(self):
        """Cari SEMUA tombol berdasarkan text (bukan hanya satu)"""
        try:
            button_text_lower = self.button_text_lower
            if not button_text_lower:
                return None

            if self._cached_buttons:
                cached_hits = []
                for elem in self._cached_buttons:
                    try:
                        if self._matches_button_text(elem):
                            cached_hits.append(elem)
                    except:
                        continue
                if cached_hits:
                    self._cached_buttons = cached_hits
                    return cached_hits
                self._cached_buttons = []

            target_buttons = []
            try:
                needle = self._xpath_literal(button_text_lower)
                lower_map = "abcdefghijklmnopqrstuvwxyz"
                upper_map = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                fast_xpath = (
                    f"//button[contains(translate(normalize-space(.), '{upper_map}', '{lower_map}'), {needle})] | "
                    f"//a[contains(translate(normalize-space(.), '{upper_map}', '{lower_map}'), {needle})] | "
                    f"//*[@role='button'][contains(translate(normalize-space(.), '{upper_map}', '{lower_map}'), {needle})] | "
                    f"//button[contains(translate(@value, '{upper_map}', '{lower_map}'), {needle})] | "
                    f"//input[@type='button' or @type='submit'][contains(translate(@value, '{upper_map}', '{lower_map}'), {needle})] | "
                    f"//*[@onclick][contains(translate(normalize-space(.), '{upper_map}', '{lower_map}'), {needle})] | "
                    f"//*[@aria-label][contains(translate(@aria-label, '{upper_map}', '{lower_map}'), {needle})] | "
                    f"//*[@title][contains(translate(@title, '{upper_map}', '{lower_map}'), {needle})]"
                )
                fast_candidates = self.driver.find_elements(By.XPATH, fast_xpath)
                for elem in fast_candidates:
                    if self._matches_button_text(elem):
                        target_buttons.append(elem)
            except:
                target_buttons = []

            if not target_buttons:
                elements = self.driver.find_elements(By.XPATH, 
                    "//button | //a | //div[@onclick] | //span[@onclick] | //*[@role='button']")
                for elem in elements:
                    if self._matches_button_text(elem):
                        target_buttons.append(elem)
            
            self._cached_buttons = target_buttons
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
            
        except StaleElementReferenceException:
            return 'stale'
        except Exception as e:
            print(f"⚠️ Error checking button status: {e}")
            return 'unknown'
    
    def click_button(self, button):
        """Klik tombol dengan berbagai metode, return True jika berhasil"""
        try:
            button_text_hint = ""
            try:
                button_text_hint = (button.text or "").strip()
                if not button_text_hint:
                    button_text_hint = (button.get_attribute("aria-label") or button.get_attribute("title") or "").strip()
            except:
                button_text_hint = ""

            def mark_success():
                self._maybe_trigger_order_click(button_text_hint)
                return True

            # Simpan URL dan beberapa info sebelum klik untuk cek perubahan
            url_before = self.driver.current_url
            title_before = self.driver.title
            
            if self.aggressive_click:
                try:
                    button.click()
                    self.random_delay(0.6, 1.6)
                    if self._check_click_success_strict(url_before, title_before):
                        return mark_success()
                except:
                    pass
                try:
                    self.driver.execute_script("arguments[0].click();", button)
                    self.random_delay(0.6, 1.6)
                    if self._check_click_success_strict(url_before, title_before):
                        return mark_success()
                except:
                    pass

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
                self.random_delay(0.6, 1.6)
                
                # Cek apakah ada perubahan dengan verifikasi yang lebih ketat
                if self._check_click_success_strict(url_before, title_before):
                    return mark_success()
            except Exception as e:
                pass
            
            # Method 2: Normal click
            try:
                button.click()
                self.random_delay(0.6, 1.6)
                
                if self._check_click_success_strict(url_before, title_before):
                    return mark_success()
            except:
                pass
            
            # Method 3: Action chains
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(self.driver).move_to_element(button).click().perform()
                self.random_delay(0.6, 1.6)
                
                if self._check_click_success_strict(url_before, title_before):
                    return mark_success()
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
                self.random_delay(0.6, 1.6)
                
                if self._check_click_success_strict(url_before, title_before):
                    return mark_success()
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
            self.random_delay(0.4, 0.9)
            
            url_after = self.driver.current_url
            title_after = self.driver.title
            
            # PRIORITAS 1: Cek apakah URL benar-benar berubah (pasti berhasil)
            if url_after != url_before and url_after.strip() != url_before.strip():
                # URL berubah, pastikan bukan hanya karena hash/fragment
                if url_after.split('#')[0] != url_before.split('#')[0]:
                    return True
            
            # PRIORITAS 2: Cek apakah title berubah (indikasi navigasi)
            if title_after != title_before and title_after.strip():
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
                        return True
                
                # Cek apakah ada iframe baru yang muncul (widget loket biasanya dalam iframe)
                try:
                    iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                    if len(iframes) > 0:
                        for iframe in iframes:
                            src = iframe.get_attribute('src') or ''
                            if 'loket.com' in src.lower() or 'widget' in src.lower():
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
        print(f"\n🔘 Tombol ditemukan ({status}), mencoba klik...")
        
    def run(self):
        """Jalankan bot"""
        print(f"▶️ Start {datetime.now().strftime('%H:%M:%S')}")
        print(f"URL: {self.concert_url}")
        print(f"Target: {self.button_text}")
        
        if not self.setup_driver():
            return
        
        try:
            print("🌐 Open page...")
            try:
                self.driver.get(self.concert_url)
            except TimeoutException:
                try:
                    self.driver.execute_script("window.stop();")
                except:
                    pass
                print("⚠️ Page load timeout, lanjut proses.")
            self.random_delay(0.6, 1.5)
            
            refresh_count = 0
            last_status = None
            last_button_count = None
            
            # Simpan URL awal untuk referensi
            initial_url = self.driver.current_url
            
            while True:
                if self._should_stop():
                    print("\nStop requested. Exiting loop.")
                    break
                try:
                    refresh_count += 1
                    current_time = datetime.now().strftime('%H:%M:%S')
                    current_url = self.driver.current_url

                    if self._is_widget_url(current_url):
                        self._handle_widget_page(current_url)
                        self.monitor_after_click()
                        break

                    if self.auto_detect_widget:
                        widget_url = self._find_widget_url_fast()
                        if widget_url and not self._is_widget_url(current_url):
                            print(f"\n⚡ Widget URL ditemukan: {widget_url}")
                            try:
                                self.driver.get(widget_url)
                            except TimeoutException:
                                try:
                                    self.driver.execute_script("window.stop();")
                                except:
                                    pass
                            self.random_delay(0.4, 0.9)
                            if self._is_widget_url(self.driver.current_url):
                                self._handle_widget_page(self.driver.current_url)
                                self.monitor_after_click()
                                break
                    
                    # CEK DULU: Apakah URL sudah berubah dari URL awal?
                    url_before_check = current_url.split('#')[0].split('?')[0].strip().rstrip('/')
                    initial_url_base = initial_url.split('#')[0].split('?')[0].strip().rstrip('/')
                    
                    if url_before_check != initial_url_base:
                        # URL sudah berubah! Cek apakah ini perubahan yang valid
                        if self._verify_page_change(initial_url, current_url):
                            print(f"\n✅ URL berubah: {current_url}")
                            
                            # Cek apakah ini widget Loket, jika ya tanya apakah mau auto beli
                            if self._is_widget_url(current_url):
                                self._handle_widget_page(current_url)
                            
                            self.monitor_after_click()
                            break
                    
                    if refresh_count % self.log_every == 0:
                        print(f"[{current_time}] #{refresh_count} mencari...", end='\r')
                    
                    # Cari SEMUA tombol dengan text yang sama
                    buttons = self.find_buttons_by_text()
                    
                    if buttons and len(buttons) > 0:
                        count = len(buttons)
                        if count != last_button_count:
                            print(f"\n✅ Ditemukan {count} tombol")
                            last_button_count = count
                        success = False
                        
                        # COBA SEMUA TOMBOL sampai salah satunya benar-benar berhasil
                        for idx, button in enumerate(buttons, 1):
                            if self._should_stop():
                                break
                            try:
                                status = self.check_button_status(button)
                                
                                # Hanya print status jika ini tombol pertama atau status berubah
                                if idx == 1 and (status != last_status or last_status is None):
                                    self.notify_found(status)
                                    last_status = status
                                
                                if count > 1:
                                    print(f"🖱️ Klik {idx}/{count}...")
                                else:
                                    print("🖱️ Klik...")
                                
                                # Coba klik tombol ini
                                url_before_button_click = self.driver.current_url
                                
                                if self.click_button(button):
                                    # Verifikasi ulang setelah beberapa detik untuk memastikan
                                    self.random_delay(0.5, 1.2)
                                    
                                    url_after_click = self.driver.current_url
                                    final_check = self._verify_page_change(url_before_button_click, url_after_click)
                                    
                                    if final_check:
                                        print(f"\n✅ Klik berhasil: {url_after_click}")
                                        
                                        # Cek apakah muncul halaman "Join the Queue" / Waiting Room
                                        if self._detect_join_queue_page():
                                            print("\n🎫 Halaman 'Join the Queue' terdeteksi")
                                            if self._handle_join_queue_step():
                                                print("✅ Berhasil masuk queue")
                                            else:
                                                print("⚠️ Gagal masuk queue, lanjutkan...")
                                        
                                        # Cek apakah ini widget Loket, jika ya tanya apakah mau auto beli
                                        if self._is_widget_url(url_after_click):
                                            self._handle_widget_page(url_after_click)
                                        
                                        # Monitor sebentar untuk memastikan
                                        self.monitor_after_click()
                                        success = True
                                        break
                                    else:
                                        # Verifikasi gagal - URL masih sama, lanjutkan loop
                                        pass
                                else:
                                    pass
                                    
                            except Exception as e:
                                if count > 1:
                                    print(f"⚠️ Error tombol #{idx}: {e}")
                                continue
                        
                        # Jika semua tombol sudah dicoba dan tidak ada yang berhasil, tetap loop
                        if self._should_stop():
                            break
                        if not success:
                            print("\n⏳ Belum berhasil, refresh...")
                    else:
                        # Tombol tidak ditemukan
                        if last_status is not None:
                            last_status = None
                        if last_button_count is not None:
                            last_button_count = None

                    current_url = self.driver.current_url
                    if self._is_widget_url(current_url):
                        self._handle_widget_page(current_url)
                        self.monitor_after_click()
                        break
                    
                    # Refresh halaman setiap 0.5-4 detik random (TETAP LOOP sampai URL berubah)
                    self.random_delay(0.1, 1.0)
                    if self._should_stop():
                        break
                    self.driver.refresh()
                    self.random_delay(0.4, 1.0)  # Tunggu halaman selesai load setelah refresh
                    
                    # Update initial_url jika halaman baru dibuka
                    new_url = self.driver.current_url
                    if new_url != initial_url:
                        # Cek apakah ini perubahan yang valid
                        if self._verify_page_change(initial_url, new_url):
                            print(f"\n✅ URL berubah: {new_url}")
                            
                            # Cek apakah ini widget Loket, jika ya tanya apakah mau auto beli
                            if self._is_widget_url(new_url):
                                self._handle_widget_page(new_url)
                            
                            self.monitor_after_click()
                            break
                        else:
                            # Update initial_url untuk referensi berikutnya
                            initial_url = new_url
                    
                except KeyboardInterrupt:
                    print("\n\n⚠️ Dihentikan")
                    break
                except WebDriverException as e:
                    print(f"\n⚠️ WebDriver error: {e}")
                    self.random_delay(0.6, 1.2)
                    try:
                        self.driver.get(self.concert_url)
                        self.random_delay(0.6, 1.2)
                    except:
                        print("❌ Reconnect gagal")
                        break
                except Exception as e:
                    print(f"\n⚠️ Error: {e}")
                    self.random_delay(0.6, 1.2)
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Dihentikan")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.close_on_exit is None:
                if self.interactive:
                    print("\nTutup browser? (y/n): ", end="")
                    try:
                        response = input().strip().lower()
                        if response == 'y':
                            if self.driver:
                                self.driver.quit()
                                print("? Browser ditutup")
                        else:
                            print("? Browser tetap terbuka")
                    except:
                        if self.driver:
                            self.driver.quit()
                else:
                    if self.driver and not self.debugger_address:
                        self.driver.quit()
            else:
                if self.close_on_exit and self.driver:
                    self.driver.quit()
    
    def _verify_page_change(self, url_before, url_after):
        """Verifikasi ulang apakah halaman benar-benar berubah - HARUS KETAT"""
        try:
            # HARUS: URL harus berbeda (dan bukan hanya hash/fragment)
            url_before_base = url_before.split('#')[0].split('?')[0].strip().rstrip('/')
            url_after_base = url_after.split('#')[0].split('?')[0].strip().rstrip('/')
            
            # Jika URL benar-benar berbeda, pasti berhasil
            if url_before_base != url_after_base:
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
                        return True
                
                # Cek iframe dengan src widget loket (lebih reliable)
                try:
                    iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                    for iframe in iframes:
                        src = (iframe.get_attribute('src') or '').lower()
                        if 'widget.loket.com' in src or ('loket.com' in src and 'widget' in src):
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
                                return True
                except:
                    pass
                
                # Jika tidak ada indikator kuat, TIDAK BERHASIL
                return False
                
            except Exception as e:
                print(f"   ⚠️ Error checking indicators: {e}")
                return False
            
        except Exception as e:
            print(f"   ⚠️ Error verifying page change: {e}")
            return False
    
    def handle_widget_loket_auto_buy(self):
        """Handle auto beli tiket setelah widget Loket terbuka"""
        current_url = self.driver.current_url
        if not self._should_prompt_auto_buy(current_url):
            return
        
        self.auto_buy_prompted = True
        print(f"\n🎫 Widget terbuka: {current_url}")

        if not self.interactive:
            if self.auto_buy and self.ticket_category:
                self.auto_buy_ticket(self.ticket_category, self.ticket_quantity)
                return
            self._wait_for_auto_buy_selection()
            return

        
        # Tanya apakah mau auto beli
        auto_buy = input("Auto buy? (y/n): ").strip().lower()
        
        if auto_buy == 'y':
            # Pilih kategori tiket dengan nomor
            self.random_delay(0.4, 0.9)
            ticket_categories = self._collect_ticket_categories()
            
            if ticket_categories:
                print("\nDaftar kategori (pilih nomor):")
                for idx, name in enumerate(ticket_categories, 1):
                    print(f"   {idx}. {name}")
                
                choice = input("Nomor kategori: ").strip()
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
                ticket_category = input("Nama kategori: ").strip()
                if not ticket_category:
                    print("❌ Kategori tiket tidak boleh kosong!")
                    return
            
            # Input jumlah tiket
            try:
                ticket_quantity = int(input("Jumlah tiket (1-6): ").strip())
                if ticket_quantity < 1 or ticket_quantity > 6:
                    print("⚠️ Jumlah tiket harus antara 1-6, menggunakan 1")
                    ticket_quantity = 1
            except:
                print("⚠️ Input tidak valid, menggunakan 1 tiket")
                ticket_quantity = 1
            
            print(f"\n✅ {ticket_category} x{ticket_quantity}")
            
            # Mulai auto beli
            self.auto_buy_ticket(ticket_category, ticket_quantity)
        else:
            print("\n✅ Manual")
    
    def auto_buy_ticket(self, category_name, quantity):
        """Auto beli tiket di widget Loket"""
        print(f"\nAuto-buy: {category_name} x{quantity}")

        attempt = 0
        max_attempts = 1000  # Loop sampai berhasil
        self.auto_buy_running = True
        self.auto_buy_paused = False
        skip_refresh_attempts = 0

        try:
            while attempt < max_attempts:
                if self._should_stop():
                    print("\nStop requested. Exiting auto-buy.")
                    return False
                if self.auto_buy_paused:
                    self.random_delay(0.4, 0.8)
                    continue

                # Cek dulu: apakah kita sudah berada di halaman form /register?
                try:
                    current_url_now = self.driver.current_url
                except Exception:
                    current_url_now = ""

                # Hanya berhenti kalau benar-benar di halaman /register + form data diri
                if self._is_order_complete_url(current_url_now) and self._is_checkout_form_page():
                    print("\n✅ Detected personal data / register page - stopping auto-buy loop.")
                    return True

                current_category = self.ticket_category or category_name
                current_quantity = self.ticket_quantity or quantity

                attempt += 1
                current_time = datetime.now().strftime('%H:%M:%S')

                if attempt % self.auto_buy_log_every == 0:
                    print(f"[{current_time}] Attempt #{attempt}", end='\r')

                try:
                    if not self.skip_refresh:
                        # Refresh halaman
                        self.driver.refresh()
                        self._click_privacy_popup(timeout_seconds=2)
                        self.random_delay(self.loop_delay_min, self.loop_delay_max)
                    else:
                        # Hybrid: tanpa refresh dulu, tapi sesekali refresh untuk update DOM
                        skip_refresh_attempts += 1
                        if skip_refresh_attempts >= self.skip_refresh_max_attempts:
                            self.driver.refresh()
                            self._click_privacy_popup(timeout_seconds=2)
                            self.random_delay(self.loop_delay_min, self.loop_delay_max)
                            skip_refresh_attempts = 0
                        else:
                            self._click_privacy_popup(timeout_seconds=1)
                            self.random_delay(self.loop_delay_min, self.loop_delay_max)
                    
                    if self.auto_buy_paused:
                        continue
                    
                    # Cek apakah muncul halaman "Join the Queue" setelah refresh
                    if self._detect_join_queue_page():
                        print("\n🎫 Halaman 'Join the Queue' terdeteksi di auto-buy")
                        if self._handle_join_queue_step():
                            print("✅ Berhasil masuk queue, tunggu widget muncul...")
                            # Tunggu widget muncul setelah join queue
                            for wait_attempt in range(15):
                                if self._should_stop():
                                    break
                                self.random_delay(1.0, 2.0)
                                if self._is_widget_url(self.driver.current_url) or self._detect_widget_on_page():
                                    print("✅ Widget muncul setelah join queue")
                                    break
                                if wait_attempt == 14:
                                    print("⚠️ Widget belum muncul setelah join queue")
                        continue

                    # Cari kategori tiket
                    category_found = self.find_and_select_ticket_category(current_category, current_quantity)
                    
                    if category_found:
                        print(f"\nSiap: {current_category} x{current_quantity}")
                        return True
                    else:
                        pass

                except KeyboardInterrupt:
                    print("\n\nDihentikan")
                    return False
                except Exception as e:
                    print(f"\nError: {e}")
                    self.random_delay(0.6, 1.2)
        finally:
            self.auto_buy_running = False
            self.auto_buy_paused = False

        return False
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

    def _collect_ticket_categories(self, allow_cached=True):
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

        if categories:
            return categories
        if allow_cached and self.widget_categories:
            return list(self.widget_categories)
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

    def _should_prompt_auto_buy(self, current_url):
        """Cek apakah perlu prompt auto-buy lagi"""
        if self.auto_buy_prompted:
            return False
        url = (current_url or "").lower()
        if any(step in url for step in ['register', 'checkout', 'confirmation', 'payment', 'personal']):
            return False
        return True

    def _is_widget_url(self, url):
        """Return True if URL looks like Loket widget page."""
        if not url:
            return False
        url_lower = url.lower()
        return "widget.loket.com/widget" in url_lower or "loket.com/widget" in url_lower

    def _is_order_complete_url(self, url):
        """Cek apakah URL sudah di step /register (konfirmasi / informasi personal)."""
        if not url:
            return False
        url_base = url.split("#")[0].split("?")[0].strip().rstrip("/")
        # Hanya anggap selesai jika benar-benar di path /register
        return url_base.endswith("/register")

    def _is_checkout_form_page(self):
        """Deteksi halaman form data diri / personal information di widget Loket."""
        try:
            page_source = (self.driver.page_source or "").lower()
            url = (self.driver.current_url or "").lower()
        except Exception:
            return False

        # Harus sedang di widget loket
        if "widget.loket.com/widget" not in url and "/register" not in url:
            return False

        keywords = [
            "data diri",
            "informasi personal",
            "personal information",
            "nama depan",
            "nama belakang",
            "nomor identitas",
            "no. handphone",
        ]
        return any(k in page_source for k in keywords)

    def _normalize_widget_url(self, raw):
        raw = (raw or "").strip().strip("'\"")
        if not raw:
            return ""
        if raw.startswith("//"):
            raw = "https:" + raw
        if raw.startswith("widget.loket.com") or raw.startswith("loket.com/widget"):
            raw = "https://" + raw
        return raw

    def _find_widget_url_fast(self):
        """Cari URL widget langsung dari DOM/HTML tanpa klik tombol."""
        try:
            url = self.driver.execute_script(
                """
                try {
                  const link = document.querySelector('a[href*="loket.com/widget"]');
                  if (link && link.href) return link.href;
                  const dataEl = document.querySelector('[data-url*="loket.com/widget"],[data-href*="loket.com/widget"],[data-link*="loket.com/widget"]');
                  if (dataEl) return dataEl.getAttribute('data-url') || dataEl.getAttribute('data-href') || dataEl.getAttribute('data-link') || '';
                  const html = document.documentElement ? document.documentElement.outerHTML : '';
                  let match = html.match(/https?:\\/\\/(?:widget\\.)?loket\\.com\\/widget\\/[A-Za-z0-9_-]+/i);
                  if (!match) {
                    match = html.match(/(?:widget\\.)?loket\\.com\\/widget\\/[A-Za-z0-9_-]+/i);
                  }
                  return match ? match[0] : '';
                } catch (e) {
                  return '';
                }
                """
            )
        except Exception:
            url = ""

        url = self._normalize_widget_url(url)
        if url and self._is_widget_url(url):
            return url
        return ""

    def _handle_widget_page(self, current_url):
        """Handle widget page actions such as privacy popup and auto-buy."""
        # Cek apakah ada halaman "Join the Queue" sebelum masuk widget
        if self._detect_join_queue_page():
            print("\n🎫 Halaman 'Join the Queue' terdeteksi sebelum widget")
            if self._handle_join_queue_step():
                print("✅ Berhasil masuk queue, tunggu widget muncul...")
                # Tunggu widget muncul setelah join queue
                for _ in range(10):
                    if self._should_stop():
                        return
                    self.random_delay(1.0, 2.0)
                    if self._is_widget_url(self.driver.current_url) or self._detect_widget_on_page():
                        print("✅ Widget muncul setelah join queue")
                        break
        
        self.widget_ready = True
        self._click_privacy_popup(timeout_seconds=6)
        if self._should_prompt_auto_buy(current_url):
            self.handle_widget_loket_auto_buy()

    def _wait_for_auto_buy_selection(self):
        self.awaiting_auto_buy_selection = True
        try:
            self.auto_buy_selection_event.clear()
        except:
            pass

        categories = []
        for _ in range(6):
            categories = self._collect_ticket_categories()
            if categories:
                break
            self.random_delay(0.4, 0.8)
        self.widget_categories = categories

        if categories:
            print("Auto-buy siap dipilih dari panel.")
        else:
            print("Auto-buy menunggu kategori widget.")

        last_scan = time.time()
        while not self._should_stop():
            if self.auto_buy and self.ticket_category:
                self.awaiting_auto_buy_selection = False
                self.auto_buy_ticket(self.ticket_category, self.ticket_quantity)
                return

            if time.time() - last_scan > 1.5:
                self._click_privacy_popup(timeout_seconds=1)
                new_categories = self._collect_ticket_categories()
                if new_categories:
                    self.widget_categories = new_categories
                last_scan = time.time()

            try:
                self.auto_buy_selection_event.wait(timeout=0.5)
            except:
                self.random_delay(0.4, 0.8)

        self.awaiting_auto_buy_selection = False

    def _page_has_privacy_banner(self):
        try:
            page_source = (self.driver.page_source or "").lower()
            return "we value your privacy" in page_source
        except:
            return False

    def _page_has_terms_modal(self):
        """Deteksi popup Terms & Conditions Loket di halaman widget."""
        try:
            page_source = (self.driver.page_source or "").lower()
            if "terms and conditions" in page_source or "syarat dan ketentuan" in page_source:
                return True
            # Cari elemen modal spesifik
            modals = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'modal') or contains(@class, 'swal') or contains(@class, 'term')]"
            )
            for m in modals:
                try:
                    if m.is_displayed():
                        return True
                except:
                    continue
            return False
        except:
            return False

    def _try_click_privacy_popup(self):
        if not self._page_has_privacy_banner():
            return False

        try:
            buttons = self.driver.find_elements(By.XPATH, "//button | //a | //*[@role='button']")
        except:
            return False

        for btn in buttons:
            try:
                if not btn.is_displayed():
                    continue
            except:
                pass

            text = (btn.text or "").strip().lower()
            if not text:
                try:
                    text = (btn.get_attribute("aria-label") or "").strip().lower()
                except:
                    text = ""

            if not text:
                continue

            if any(token in text for token in ("accept", "agree", "setuju")):
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        btn,
                    )
                    self.random_delay(0.2, 0.4)
                except:
                    pass

                try:
                    btn.click()
                except:
                    try:
                        self.driver.execute_script("arguments[0].click();", btn)
                    except:
                        return False

                print("Privacy accept clicked.")
                self.random_delay(0.2, 0.5)
                return True

        return False

    def _try_click_privacy_popup_in_iframes(self):
        try:
            frames = self.driver.find_elements(By.TAG_NAME, "iframe")
        except:
            return False

        for frame in frames:
            try:
                self.driver.switch_to.frame(frame)
                if self._try_click_privacy_popup():
                    return True
            except:
                pass
            finally:
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass

        return False

    def _click_privacy_popup(self, timeout_seconds=6):
        """Click Accept on the privacy popup if it appears."""
        end_time = time.time() + timeout_seconds
        while time.time() < end_time:
            if self._should_stop():
                return False
            if self._try_click_privacy_popup():
                return True
            if self._try_click_privacy_popup_in_iframes():
                return True
            self.random_delay(0.2, 0.5)
        return False
    
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
        
        def attempt_click():
            # Loket T&C modal: tombol "Agree" / "Setuju"
            try:
                agree_btn = None
                try:
                    agree_btn = self.driver.find_element(By.ID, "btn-agree-tnc")
                except:
                    pass

                if not agree_btn:
                    # Fallback: cari tombol berdasarkan text
                    candidates = self.driver.find_elements(
                        By.XPATH,
                        "//button[contains(., 'Agree') or contains(., 'Setuju')] | "
                        "//button[contains(., 'AGREE')] | "
                        "//button[contains(., 'I Agree')]",
                    )
                    for btn in candidates:
                        try:
                            if btn.is_displayed():
                                agree_btn = btn
                                break
                        except:
                            continue

                if agree_btn and agree_btn.is_displayed():
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        agree_btn,
                    )
                    self.random_delay(0.2, 0.4)
                    clicked = False
                    try:
                        agree_btn.click()
                        clicked = True
                    except:
                        try:
                            self.driver.execute_script("arguments[0].click();", agree_btn)
                            clicked = True
                        except:
                            try:
                                from selenium.webdriver.common.action_chains import ActionChains
                                ActionChains(self.driver).move_to_element(agree_btn).click().perform()
                                clicked = True
                            except:
                                clicked = False

                    if clicked:
                        # Tunggu sampai modal hilang
                        for _ in range(20):
                            self.random_delay(0.1, 0.2)
                            try:
                                if not agree_btn.is_displayed():
                                    break
                            except:
                                break
                        print("✅ Agree")
                        self.random_delay(0.2, 0.6)
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
                    print("✅ Agree")
                    self.random_delay(0.2, 0.6)
                    return True
            except:
                pass
            return False

        while time.time() < end_time:
            if attempt_click():
                return True

            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            except:
                iframes = []
            for iframe in iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                except:
                    continue
                try:
                    if attempt_click():
                        self.driver.switch_to.default_content()
                        return True
                finally:
                    try:
                        self.driver.switch_to.default_content()
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

            # Method 0: Cari di blok ticket-item langsung
            try:
                ticket_items = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'ticket-item')]")
                for item in ticket_items:
                    try:
                        item_text = (item.text or '').strip().upper()
                        if category_upper in item_text:
                            target_section = item
                            break
                        
                        name_elems = item.find_elements(By.XPATH, ".//*[@data-ticket-name or @ticket-name]")
                        for elem in name_elems:
                            name_attr = (elem.get_attribute('data-ticket-name') or elem.get_attribute('ticket-name') or '')
                            if category_upper in name_attr.upper():
                                target_section = item
                                break
                        if target_section:
                            break
                    except:
                        continue
            except:
                pass
            
            # Method 1: Cari heading (h4, h5, h6) yang mengandung nama kategori
            if not target_section:
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
                return False
            
            target_container = target_section
            try:
                ticket_container = target_section.find_element(
                    By.XPATH,
                    "./ancestor::*[contains(@class, 'ticket-item')][1]",
                )
                target_container = ticket_container
            except:
                pass
            
            # Scroll ke section
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target_container)
            self.random_delay(0.2, 0.6)
            
            # Cari dan set quantity
            quantity_set = False
            try:
                # Cari input number untuk quantity (biasanya ada di dekat kategori)
                # Cari di section target atau di seluruh halaman dekat kategori
                quantity_inputs = target_container.find_elements(By.XPATH, 
                    ".//input[@type='number'] | .//input[contains(@class, 'quantity')] | .//input[contains(@name, 'quantity')]")
                
                if quantity_inputs:
                    for qty_input in quantity_inputs:
                        try:
                            current_value = qty_input.get_attribute('value') or ''
                            if self._extract_first_int(current_value) == quantity:
                                quantity_set = True
                                self.random_delay(0.3, 0.6)
                                break
                            
                            # Set quantity dengan JavaScript
                            self.driver.execute_script(f"arguments[0].value = {quantity};", qty_input)
                            self._dispatch_input_change(qty_input)
                            
                            # Verifikasi value sudah ter-set
                            value = qty_input.get_attribute('value')
                            if self._extract_first_int(value) == quantity:
                                quantity_set = True
                                self.random_delay(0.2, 0.6)
                                break
                        except:
                            continue
                
                # Jika tidak ada input number, coba dropdown <select>
                if not quantity_set:
                    try:
                        select_elements = target_container.find_elements(
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
                                    quantity_set = True
                                    self.random_delay(0.2, 0.6)
                                    break
                    except:
                        pass
                
                # Jika tidak ada input, coba klik button +/- untuk set quantity
                if not quantity_set:
                    try:
                        # Cari button dengan angka yang sesuai quantity
                        buttons = target_container.find_elements(By.XPATH, 
                            f".//button[text()='{quantity}'] | .//button[contains(@aria-label, '{quantity}')]")
                        if buttons:
                            buttons[0].click()
                            quantity_set = True
                            self.random_delay(0.2, 0.6)
                    except:
                        pass
                
            except Exception as e:
                print(f"   ⚠️ Error setting quantity: {e}")
            
            if not quantity_set and not self.aggressive_order:
                return False
            
            # Cari dan klik tombol Order Now / Pesan Sekarang
            try:
                # Tunggu sedikit untuk memastikan quantity sudah ter-set dengan benar
                self.random_delay(0.3, 0.6)
                
                # Cari tombol Order Now / Pesan Sekarang dengan berbagai variasi text
                order_button_texts = [
                    "Pesan Sekarang",
                    "Order Now",
                    "Pesan",
                    "Order",
                    "Beli",
                    "Buy Now",
                    "Checkout"
                ]
                
                order_btn = None
                
                # Method 1: Cari di dalam section target_container
                for btn_text in order_button_texts:
                    try:
                        order_buttons = target_container.find_elements(By.XPATH, 
                            f".//button[contains(., '{btn_text}')] | "
                            f".//a[contains(., '{btn_text}')] | "
                            f".//*[@role='button'][contains(., '{btn_text}')]"
                        )
                        
                        for btn in order_buttons:
                            try:
                                if btn.is_displayed():
                                    btn_text_actual = (btn.text or "").strip()
                                    if btn_text.lower() in btn_text_actual.lower():
                                        order_btn = btn
                                        break
                            except:
                                continue
                        
                        if order_btn:
                            break
                    except:
                        continue
                
                # Method 2: Jika tidak ada di section, cari di seluruh halaman (prioritas "Pesan Sekarang")
                if not order_btn:
                    for btn_text in order_button_texts:
                        try:
                            order_buttons = self.driver.find_elements(By.XPATH, 
                                f"//button[contains(., '{btn_text}')] | "
                                f"//a[contains(., '{btn_text}')] | "
                                f"//*[@role='button'][contains(., '{btn_text}')]"
                            )
                            
                            for btn in order_buttons:
                                try:
                                    if not btn.is_displayed():
                                        continue
                                    
                                    btn_text_actual = (btn.text or "").strip()
                                    btn_aria = (btn.get_attribute('aria-label') or "").strip()
                                    
                                    # Prioritas untuk "Pesan Sekarang"
                                    if btn_text == "Pesan Sekarang":
                                        if 'pesan' in btn_text_actual.lower() and 'sekarang' in btn_text_actual.lower():
                                            order_btn = btn
                                            break
                                    elif btn_text.lower() in btn_text_actual.lower() or btn_text.lower() in btn_aria.lower():
                                        order_btn = btn
                                        break
                                except:
                                    continue
                            
                            if order_btn:
                                break
                        except:
                            continue
                
                # Method 3: Cari dengan class/id spesifik
                if not order_btn:
                    try:
                        specific_selectors = [
                            "//button[contains(@class, 'order')]",
                            "//button[contains(@class, 'pesan')]",
                            "//button[contains(@id, 'order')]",
                            "//button[contains(@id, 'pesan')]",
                            "//a[contains(@class, 'order')]",
                            "//a[contains(@class, 'pesan')]"
                        ]
                        
                        for selector in specific_selectors:
                            try:
                                buttons = self.driver.find_elements(By.XPATH, selector)
                                for btn in buttons:
                                    try:
                                        if btn.is_displayed():
                                            btn_text = (btn.text or "").strip().lower()
                                            if any(text in btn_text for text in ['pesan', 'order', 'beli', 'buy']):
                                                order_btn = btn
                                                break
                                    except:
                                        continue
                                if order_btn:
                                    break
                            except:
                                continue
                    except:
                        pass
                
                if not order_btn:
                    print("   ⚠️ Tombol 'Pesan Sekarang' tidak ditemukan")
                    return False

                order_btn_text = ""
                try:
                    order_btn_text = (order_btn.text or "").strip()
                    if not order_btn_text:
                        order_btn_text = (order_btn.get_attribute("aria-label") or order_btn.get_attribute("title") or "").strip()
                except:
                    order_btn_text = ""
                
                # Scroll ke tombol
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        order_btn
                    )
                    self.random_delay(0.3, 0.6)
                except:
                    pass
                
                # Pastikan tombol enabled dan visible
                try:
                    if order_btn.get_attribute('disabled') is not None:
                        print("   ⚠️ Tombol 'Pesan Sekarang' disabled")
                        return False
                except:
                    pass
                
                # Klik tombol dengan beberapa metode
                print(f"   🖱️ Klik tombol: {(order_btn.text or '').strip()}")
                url_before_click = self.driver.current_url
                
                clicked = False
                
                # Method 1: JavaScript click (paling reliable)
                try:
                    self.driver.execute_script("arguments[0].click();", order_btn)
                    clicked = True
                    self.random_delay(0.8, 1.5)
                except:
                    pass
                
                # Method 2: Normal click
                if not clicked:
                    try:
                        order_btn.click()
                        clicked = True
                        self.random_delay(0.8, 1.5)
                    except:
                        pass
                
                # Method 3: Action chains
                if not clicked:
                    try:
                        from selenium.webdriver.common.action_chains import ActionChains
                        ActionChains(self.driver).move_to_element(order_btn).click().perform()
                        clicked = True
                        self.random_delay(0.8, 1.5)
                    except:
                        pass
                
                # Method 4: Trigger event click via JavaScript (full event)
                if not clicked:
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
                        """, order_btn)
                        clicked = True
                        self.random_delay(0.8, 1.5)
                    except:
                        pass
                
                if not clicked:
                    print("   ⚠️ Gagal klik tombol 'Pesan Sekarang'")
                    return False

                self._maybe_trigger_order_click(order_btn_text)
                
                # Tunggu dan cek hasil
                self.random_delay(0.6, 1.2)
                
                # Jika muncul popup T&C, langsung klik Agree
                agree_clicked = self._click_agree_popup(timeout_seconds=12)

                # Setelah klik Pesan Sekarang (dan Agree kalau ada), JANGAN langsung refresh.
                # Tunggu beberapa detik sambil pantau apakah pindah ke /register atau halaman form.
                wait_start = time.time()
                max_wait = 25  # detik
                while time.time() - wait_start < max_wait:
                    if self._should_stop():
                        return False
                    self.random_delay(0.4, 0.8)
                    try:
                        current_url = self.driver.current_url
                    except Exception:
                        current_url = ""

                    # Kalau sudah di /register + form data diri -> sukses total
                    if self._is_order_complete_url(current_url) and self._is_checkout_form_page():
                        print("   ✅ Klik 'Pesan Sekarang' berhasil (masuk halaman Data Diri)")
                        return True

                    # Kalau URL sudah berubah signifikan dari sebelum klik, anggap klik berhasil
                    if current_url and current_url != url_before_click:
                        url_before_base = url_before_click.split('#')[0].split('?')[0].strip().rstrip('/')
                        url_after_base = current_url.split('#')[0].split('?')[0].strip().rstrip('/')
                        if url_before_base != url_after_base:
                            print("   ✅ Klik 'Pesan Sekarang' berhasil (URL berubah)")
                            return True

                    # Kalau modal T&C masih kelihatan, coba klik lagi sebentar
                    if agree_clicked and self._page_has_terms_modal():
                        self._click_agree_popup(timeout_seconds=6)

                # Sampai timeout belum pindah ke /register
                if agree_clicked:
                    print("   ⚠️ Popup T&C diklik tapi belum pindah ke halaman Data Diri (timeout)")
                    return False

                print("   ⚠️ Klik 'Pesan Sekarang' dilakukan tapi hasil tidak jelas (timeout tunggu redirect)")
                return False
                    
            except Exception as e:
                print(f"   ⚠️ Error saat klik Order/Pesan: {e}")
                import traceback
                traceback.print_exc()
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
        initial_url = self.driver.current_url
        
        for _ in range(6):
            if self._should_stop():
                return
            try:
                current_url = self.driver.current_url
                if current_url != initial_url and current_url.split('#')[0] != initial_url.split('#')[0]:
                    break
                
                # Cek apakah muncul halaman "Join the Queue"
                if self._detect_join_queue_page():
                    print("\n🎫 Halaman 'Join the Queue' terdeteksi")
                    if self._handle_join_queue_step():
                        print("✅ Berhasil masuk queue")
                    break
                
                # Cek apakah ada elemen checkout/pembelian
                page_source = self.driver.page_source.lower()
                if any(keyword in page_source for keyword in ['checkout', 'pembelian', 'order now', 'select category', 'widget.loket.com']):
                    break
                
                self.random_delay(0.5, 1.2)
            except:
                self.random_delay(0.5, 1.2)
    
    def _detect_join_queue_page(self):
        """Deteksi apakah halaman saat ini adalah halaman 'Join the Queue' / Waiting Room"""
        try:
            current_url = self.driver.current_url.lower()
            page_source = (self.driver.page_source or "").lower()
            
            # Indikator URL
            url_indicators = [
                'waiting',
                'queue',
                'antrean',
                'join-queue',
                'join_queue'
            ]
            
            # Indikator teks di halaman
            text_indicators = [
                'waiting room',
                'join the queue',
                'join queue',
                'masuk antrean',
                'antrean tiket',
                'please click the button below to initiate',
                'ticket purchase queueing process'
            ]
            
            # Cek URL
            for indicator in url_indicators:
                if indicator in current_url:
                    return True
            
            # Cek teks di halaman
            for indicator in text_indicators:
                if indicator in page_source:
                    return True
            
            # Cek elemen spesifik
            try:
                # Cari tombol "Join the Queue"
                join_queue_buttons = self.driver.find_elements(By.XPATH, 
                    "//button[contains(., 'Join') and contains(., 'Queue')] | "
                    "//a[contains(., 'Join') and contains(., 'Queue')] | "
                    "//button[contains(., 'Join the Queue')] | "
                    "//*[@role='button'][contains(., 'Join') and contains(., 'Queue')]"
                )
                if join_queue_buttons:
                    for btn in join_queue_buttons:
                        try:
                            if btn.is_displayed():
                                return True
                        except:
                            continue
            except:
                pass
            
            # Cek heading "Waiting Room"
            try:
                waiting_room_headers = self.driver.find_elements(By.XPATH,
                    "//h1[contains(., 'Waiting Room')] | "
                    "//h2[contains(., 'Waiting Room')] | "
                    "//*[contains(@class, 'waiting-room')] | "
                    "//*[contains(@id, 'waiting-room')]"
                )
                if waiting_room_headers:
                    return True
            except:
                pass
            
            return False
        except Exception as e:
            return False
    
    def _detect_cloudflare_challenge(self):
        """Deteksi apakah ada Cloudflare challenge yang sedang berlangsung"""
        try:
            page_source = (self.driver.page_source or "").lower()
            current_url = self.driver.current_url.lower()
            
            # Indikator Cloudflare challenge
            cloudflare_indicators = [
                'cloudflare',
                'checking your browser',
                'please wait',
                'ddos protection',
                'ray id',
                'cf-browser-verification',
                'cf-challenge',
                'challenge-platform',
                '__cf_bm',
                'cf_clearance'
            ]
            
            # Cek di page source
            for indicator in cloudflare_indicators:
                if indicator in page_source:
                    return True
            
            # Cek elemen spesifik Cloudflare
            try:
                # Cek logo Cloudflare
                cloudflare_elements = self.driver.find_elements(By.XPATH,
                    "//*[contains(@class, 'cf-')] | "
                    "//*[contains(@id, 'cf-')] | "
                    "//*[contains(@class, 'cloudflare')] | "
                    "//img[contains(@alt, 'Cloudflare')] | "
                    "//*[contains(text(), 'Cloudflare')]"
                )
                if cloudflare_elements:
                    return True
                
                # Cek error message Cloudflare
                error_elements = self.driver.find_elements(By.XPATH,
                    "//*[contains(text(), 'Kegagalan')] | "
                    "//*[contains(text(), 'Failure')] | "
                    "//*[contains(text(), 'Mengalami masalah')]"
                )
                if error_elements:
                    # Cek apakah ada logo Cloudflare di dekatnya
                    for elem in error_elements:
                        try:
                            parent = elem.find_element(By.XPATH, "./ancestor::*[contains(@class, 'cloudflare') or contains(@id, 'cf-')]")
                            if parent:
                                return True
                        except:
                            pass
            except:
                pass
            
            # Cek apakah ada iframe Cloudflare
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    src = (iframe.get_attribute('src') or '').lower()
                    if 'cloudflare' in src or 'challenges.cloudflare.com' in src:
                        return True
            except:
                pass
            
            return False
        except Exception as e:
            return False
    
    def _wait_for_cloudflare_bypass(self, timeout_seconds=30):
        """Tunggu sampai Cloudflare challenge selesai"""
        print("🛡️ Cloudflare challenge terdeteksi, menunggu bypass...")
        start_time = time.time()
        last_log_time = start_time
        
        while time.time() - start_time < timeout_seconds:
            if self._should_stop():
                return False
            
            # Cek apakah Cloudflare challenge masih ada
            if not self._detect_cloudflare_challenge():
                # Tunggu sedikit lagi untuk memastikan challenge benar-benar selesai
                self.random_delay(1.0, 2.0)
                if not self._detect_cloudflare_challenge():
                    print("✅ Cloudflare challenge selesai")
                    return True
            
            # Log progress setiap 5 detik
            elapsed = time.time() - last_log_time
            if elapsed >= 5:
                remaining = timeout_seconds - (time.time() - start_time)
                print(f"   ⏳ Menunggu Cloudflare... ({int(remaining)}s tersisa)", end='\r')
                last_log_time = time.time()
            
            self.random_delay(0.5, 1.0)
        
        print(f"\n⚠️ Cloudflare challenge timeout setelah {timeout_seconds}s")
        return False
    
    def _handle_join_queue_step(self):
        """Handle langkah 'Join the Queue' - deteksi dan klik tombol"""
        try:
            # Tunggu halaman selesai load
            self.random_delay(1.0, 2.0)
            
            # Cek dan handle Cloudflare challenge jika ada
            if self._detect_cloudflare_challenge():
                if not self._wait_for_cloudflare_bypass(timeout_seconds=30):
                    print("⚠️ Cloudflare challenge tidak selesai, lanjutkan...")
                    return False
            
            # Cari tombol "Join the Queue" dengan berbagai metode
            join_queue_button = None
            
            # Method 1: Cari dengan text "Join the Queue" atau variasi
            try:
                button_texts = [
                    "Join the Queue",
                    "Join the Queue >",
                    "Join Queue",
                    "Masuk Antrean",
                    "Join",
                    "Queue"
                ]
                
                for btn_text in button_texts:
                    try:
                        buttons = self.driver.find_elements(By.XPATH,
                            f"//button[contains(., '{btn_text}')] | "
                            f"//a[contains(., '{btn_text}')] | "
                            f"//*[@role='button'][contains(., '{btn_text}')] | "
                            f"//*[contains(@class, 'btn')][contains(., '{btn_text}')]"
                        )
                        
                        for btn in buttons:
                            try:
                                if btn.is_displayed():
                                    btn_text_actual = (btn.text or "").strip()
                                    if any(text.lower() in btn_text_actual.lower() for text in button_texts[:3]):
                                        join_queue_button = btn
                                        break
                            except:
                                continue
                        
                        if join_queue_button:
                            break
                    except:
                        continue
            except:
                pass
            
            # Method 2: Cari dengan class/id spesifik
            if not join_queue_button:
                try:
                    selectors = [
                        "//button[contains(@class, 'join-queue')]",
                        "//button[contains(@class, 'join_queue')]",
                        "//button[contains(@id, 'join-queue')]",
                        "//a[contains(@class, 'join-queue')]",
                        "//*[@role='button'][contains(@class, 'queue')]"
                    ]
                    
                    for selector in selectors:
                        try:
                            buttons = self.driver.find_elements(By.XPATH, selector)
                            for btn in buttons:
                                try:
                                    if btn.is_displayed():
                                        join_queue_button = btn
                                        break
                                except:
                                    continue
                            if join_queue_button:
                                break
                        except:
                            continue
                except:
                    pass
            
            # Method 3: Cari semua button dan filter berdasarkan text
            if not join_queue_button:
                try:
                    all_buttons = self.driver.find_elements(By.XPATH, "//button | //a | //*[@role='button']")
                    for btn in all_buttons:
                        try:
                            if not btn.is_displayed():
                                continue
                            
                            btn_text = (btn.text or "").strip().lower()
                            btn_aria = (btn.get_attribute('aria-label') or "").strip().lower()
                            
                            keywords = ['join', 'queue', 'antrean']
                            if any(keyword in btn_text or keyword in btn_aria for keyword in keywords):
                                # Pastikan bukan tombol lain yang kebetulan mengandung kata tersebut
                                if 'join' in btn_text or 'queue' in btn_text:
                                    join_queue_button = btn
                                    break
                        except:
                            continue
                except:
                    pass
            
            if not join_queue_button:
                print("⚠️ Tombol 'Join the Queue' tidak ditemukan")
                return False
            
            # Scroll ke tombol
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    join_queue_button
                )
                self.random_delay(0.3, 0.6)
            except:
                pass
            
            # Klik tombol dengan berbagai metode
            print("🖱️ Mencoba klik tombol 'Join the Queue'...")
            
            url_before = self.driver.current_url
            
            # Method 1: JavaScript click
            try:
                self.driver.execute_script("arguments[0].click();", join_queue_button)
                self.random_delay(1.0, 2.0)
                
                # Cek apakah berhasil
                url_after = self.driver.current_url
                if url_after != url_before:
                    print("✅ Klik 'Join the Queue' berhasil (URL berubah)")
                    return True
                
                # Cek apakah halaman berubah (widget muncul)
                if self._is_widget_url(url_after) or self._detect_widget_on_page():
                    print("✅ Klik 'Join the Queue' berhasil (widget muncul)")
                    return True
            except Exception as e:
                pass
            
            # Method 2: Normal click
            try:
                join_queue_button.click()
                self.random_delay(1.0, 2.0)
                
                url_after = self.driver.current_url
                if url_after != url_before:
                    print("✅ Klik 'Join the Queue' berhasil (URL berubah)")
                    return True
                
                if self._is_widget_url(url_after) or self._detect_widget_on_page():
                    print("✅ Klik 'Join the Queue' berhasil (widget muncul)")
                    return True
            except Exception as e:
                pass
            
            # Method 3: Action chains
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(self.driver).move_to_element(join_queue_button).click().perform()
                self.random_delay(1.0, 2.0)
                
                url_after = self.driver.current_url
                if url_after != url_before:
                    print("✅ Klik 'Join the Queue' berhasil (URL berubah)")
                    return True
                
                if self._is_widget_url(url_after) or self._detect_widget_on_page():
                    print("✅ Klik 'Join the Queue' berhasil (widget muncul)")
                    return True
            except Exception as e:
                pass
            
            # Tunggu sedikit dan cek lagi apakah widget muncul
            self.random_delay(2.0, 3.0)
            if self._is_widget_url(self.driver.current_url) or self._detect_widget_on_page():
                print("✅ Widget muncul setelah klik 'Join the Queue'")
                return True
            
            print("⚠️ Klik 'Join the Queue' dilakukan tapi hasil tidak jelas")
            return False
            
        except Exception as e:
            print(f"⚠️ Error handling 'Join the Queue': {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _detect_widget_on_page(self):
        """Deteksi apakah widget Loket sudah muncul di halaman"""
        try:
            page_source = (self.driver.page_source or "").lower()
            
            # Indikator widget Loket
            widget_indicators = [
                'widget.loket.com',
                'pilih kategori',
                'select category',
                'ticket-item',
                'loket.com/widget'
            ]
            
            for indicator in widget_indicators:
                if indicator in page_source:
                    return True
            
            # Cek iframe widget
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    src = (iframe.get_attribute('src') or '').lower()
                    if 'widget.loket.com' in src or 'loket.com/widget' in src:
                        return True
            except:
                pass
            
            return False
        except:
            return False


def main():
    """Main function"""
    print("🤖 Bot Loket")
    
    # Input parameter 1: Link konser
    concert_url = input("Link konser: ").strip()
    if not concert_url:
        print("❌ Link konser tidak boleh kosong!")
        return
    
    if not concert_url.startswith('http'):
        concert_url = 'https://' + concert_url
    
    # Input parameter 2: Text tombol
    button_text = input("Text tombol: ").strip()
    if not button_text:
        print("❌ Text tombol tidak boleh kosong!")
        return

    # Pilih mode Chrome
    use_existing = input("Gunakan Chrome yang sudah dibuka? (y/n): ").strip().lower()
    debugger_address = None
    open_new_tab = False
    if use_existing == 'y':
        print("Catatan: Chrome harus dijalankan dengan --remote-debugging-port.")
        raw_addr = input("Remote debugging address (default 127.0.0.1:9222 atau isi port saja): ").strip()
        if not raw_addr:
            debugger_address = "127.0.0.1:9222"
        elif ":" in raw_addr:
            debugger_address = raw_addr
        else:
            debugger_address = f"127.0.0.1:{raw_addr}"
        open_new_tab = True

    
    # Konfirmasi
    confirm = input("Jalankan? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Dibatalkan")
        return
    
    # Jalankan bot
    bot = SimpleButtonBot(
        concert_url,
        button_text,
        debugger_address=debugger_address,
        open_new_tab=open_new_tab,
    )
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

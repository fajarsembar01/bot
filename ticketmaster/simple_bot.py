"""Simple Ticketmaster bot to find and click target buttons."""
import os
import random
import re
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from threading import Event, Thread

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

try:
    from . import config
except ImportError:
    try:
        from ticketmaster import config
    except ImportError:
        import config


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_linux() -> bool:
    return sys.platform.startswith("linux")


@dataclass
class ClickResult:
    clicked: bool
    reason: str


class TicketmasterSimpleBot:
    def __init__(
        self,
        url: str,
        button_text: str,
        refresh_seconds: float = 3.0,
        max_attempts: int = 500,
        headless: bool = False,
        auto_buy: bool = False,
        quantity: int = 1,
        debugger_address: str = "",
        open_new_tab: bool = True,
        user_data_dir: str = "",
        new_session: bool = True,
        stop_event: Event = None,
        close_on_exit: bool = None,
        interactive: bool = True,
    ):
        self.url = (url or "").strip()
        self.button_text = (button_text or "").strip()
        self.button_text_lower = self.button_text.lower()
        self.refresh_seconds = max(0.5, float(refresh_seconds))
        self.max_attempts = max(1, int(max_attempts))
        self.headless = headless
        self.auto_buy = auto_buy
        self.quantity = max(1, min(int(quantity or 1), 6))
        self.debugger_address = (debugger_address or "").strip()
        self.open_new_tab = open_new_tab
        self.user_data_dir = (user_data_dir or "").strip()
        self.new_session = new_session
        self.stop_event = stop_event
        self.close_on_exit = close_on_exit
        self.interactive = interactive
        self.driver = None
        self.setup_success = False
        self.last_error = ""
        self._cached_buttons = []
        self.log_every = 5

    def _should_stop(self) -> bool:
        return self.stop_event is not None and self.stop_event.is_set()

    def request_stop(self):
        if self.stop_event:
            self.stop_event.set()

    def _random_delay(self, min_seconds=0.5, max_seconds=4.0):
        """Random delay antara min dan max seconds"""
        if min_seconds < 0:
            min_seconds = 0
        if max_seconds < min_seconds:
            max_seconds = min_seconds
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        return round(delay, 1)

    def _build_session_dir(self) -> str:
        sessions_dir = os.path.join(os.path.dirname(__file__), "sessions")
        os.makedirs(sessions_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(sessions_dir, f"session-{timestamp}")
        os.makedirs(session_dir, exist_ok=True)
        return session_dir

    def setup_driver(self) -> bool:
        chrome_options = Options()
        if self.debugger_address:
            chrome_options.add_experimental_option("debuggerAddress", self.debugger_address)
        else:
            if self.headless:
                chrome_options.add_argument("--headless=new")
            if is_linux():
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            chrome_options.add_argument("--window-size=1280,900")
            chrome_options.add_argument(
                "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            user_data_dir = self.user_data_dir
            if not user_data_dir and self.new_session:
                user_data_dir = self._build_session_dir()
            if user_data_dir:
                chrome_options.add_argument(f"--user-data-dir={os.path.abspath(user_data_dir)}")

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
                    driver, err = init_with_timeout(
                        "chromedriver (PATH)",
                        lambda: webdriver.Chrome(service=service, options=chrome_options),
                    )
                    if err:
                        driver_errors.append(err)

            if not driver:
                def create_manager_driver():
                    service = Service(ChromeDriverManager().install())
                    return webdriver.Chrome(service=service, options=chrome_options)

                driver, err = init_with_timeout("webdriver-manager", create_manager_driver)
                if err:
                    driver_errors.append(err)

            if not driver:
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
            except Exception:
                pass

            try:
                self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': """
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        })
                    """
                })
            except Exception:
                pass

            self.setup_success = True
            return True
        except Exception as exc:
            self.last_error = str(exc)
            if self.debugger_address:
                print(f"Error attach ke Chrome ({self.debugger_address}): {exc}")
                print("Tip: jalankan Chrome dengan --remote-debugging-port dan profile terpisah.")
            else:
                print(f"Error setting up browser: {exc}")
            return False

    def _open_new_tab(self):
        if not self.driver:
            return False
        try:
            self.driver.switch_to.new_window("tab")
            return True
        except Exception:
            try:
                self.driver.execute_script("window.open('about:blank','_blank');")
                handles = self.driver.window_handles
                if handles:
                    self.driver.switch_to.window(handles[-1])
                    return True
            except Exception:
                pass
        return False

    def _xpath_literal(self, text):
        if "'" not in text:
            return f"'{text}'"
        if '"' not in text:
            return f'"{text}"'
        parts = text.split("'")
        return "concat(" + ", \"'\", ".join(f"'{part}'" for part in parts) + ")"

    def _matches_button_text(self, elem) -> bool:
        needle = self.button_text_lower
        if not needle:
            return False

        try:
            text = (elem.text or "").strip().lower()
            if text and (needle in text or text in needle):
                return True
        except Exception:
            pass

        for attr in ("value", "aria-label", "title", "data-testid", "data-qa", "data-automation"):
            try:
                value = elem.get_attribute(attr) or ""
            except Exception:
                value = ""
            value = value.strip().lower()
            if value and (needle in value or value in needle):
                return True
        return False

    def find_buttons_by_text(self):
        if not self.button_text_lower:
            return None

        if self._cached_buttons:
            cached_hits = []
            for elem in self._cached_buttons:
                try:
                    if self._matches_button_text(elem):
                        cached_hits.append(elem)
                except Exception:
                    continue
            if cached_hits:
                self._cached_buttons = cached_hits
                return cached_hits
            self._cached_buttons = []

        target_buttons = []
        try:
            needle = self._xpath_literal(self.button_text_lower)
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
        except Exception:
            target_buttons = []

        if not target_buttons:
            elements = self.driver.find_elements(By.XPATH,
                "//button | //a | //div[@onclick] | //span[@onclick] | //*[@role='button']")
            for elem in elements:
                if self._matches_button_text(elem):
                    target_buttons.append(elem)

        self._cached_buttons = target_buttons
        return target_buttons if target_buttons else None

    def check_button_status(self, button) -> str:
        try:
            disabled = button.get_attribute('disabled')
            if disabled is not None or disabled == 'true':
                return 'disabled'

            classes = button.get_attribute('class') or ''
            if 'disabled' in classes.lower() or 'inactive' in classes.lower():
                return 'disabled'

            style = button.get_attribute('style') or ''
            if 'pointer-events: none' in style.lower() or 'opacity: 0.5' in style.lower():
                return 'disabled'

            if not button.is_displayed():
                return 'hidden'

            try:
                is_in_viewport = self.driver.execute_script("""
                    var rect = arguments[0].getBoundingClientRect();
                    return (rect.top >= 0 && rect.left >= 0 &&
                            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                            rect.right <= (window.innerWidth || document.documentElement.clientWidth));
                """, button)
                if not is_in_viewport:
                    return 'out_of_view'
            except Exception:
                pass

            return 'enabled'
        except StaleElementReferenceException:
            return 'stale'
        except Exception:
            return 'unknown'

    def _check_click_success(self, url_before, title_before, handles_before) -> bool:
        try:
            if self.driver.current_url != url_before:
                return True
        except Exception:
            pass
        try:
            if self.driver.title != title_before:
                return True
        except Exception:
            pass
        try:
            if len(self.driver.window_handles) != handles_before:
                return True
        except Exception:
            pass
        return False

    def click_button(self, button) -> ClickResult:
        try:
            url_before = self.driver.current_url
            title_before = self.driver.title
            handles_before = len(self.driver.window_handles)
        except Exception:
            url_before = ""
            title_before = ""
            handles_before = 0

        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                button,
            )
            self._random_delay(0.2, 0.5)
        except Exception:
            pass

        try:
            self.driver.execute_script("arguments[0].click();", button)
            self._random_delay(0.6, 1.6)
            if self._check_click_success(url_before, title_before, handles_before):
                return ClickResult(True, "js_click")
        except Exception:
            pass

        try:
            button.click()
            self._random_delay(0.6, 1.6)
            if self._check_click_success(url_before, title_before, handles_before):
                return ClickResult(True, "click")
        except Exception:
            pass

        try:
            ActionChains(self.driver).move_to_element(button).click().perform()
            self._random_delay(0.6, 1.6)
            if self._check_click_success(url_before, title_before, handles_before):
                return ClickResult(True, "action_chains")
        except Exception:
            pass

        return ClickResult(False, "failed")

    def _page_needs_attention(self) -> bool:
        try:
            title = (self.driver.title or "").lower()
            source = (self.driver.page_source or "").lower()
        except Exception:
            return False

        if "just a moment" in title:
            return True
        if "captcha" in source:
            return True
        if "verify" in source and "human" in source:
            return True
        return False

    def _set_quantity_from_select(self, select_elem, quantity: int) -> bool:
        try:
            select = Select(select_elem)
        except Exception:
            return False

        target = str(quantity)
        for opt in select.options:
            if (opt.get_attribute("value") or "").strip() == target:
                select.select_by_value(target)
                return True
            if (opt.text or "").strip() == target:
                select.select_by_visible_text(target)
                return True
        return False

    def _set_quantity(self, quantity: int) -> bool:
        if quantity <= 1:
            return True

        try:
            selects = self.driver.find_elements(By.XPATH, "//select")
        except Exception:
            selects = []
        for select_elem in selects:
            if self._set_quantity_from_select(select_elem, quantity):
                return True

        try:
            inputs = self.driver.find_elements(By.XPATH, "//input[@type='number']")
        except Exception:
            inputs = []
        for input_elem in inputs:
            try:
                input_elem.clear()
                input_elem.send_keys(str(quantity))
                return True
            except Exception:
                continue

        try:
            plus_buttons = self.driver.find_elements(
                By.XPATH,
                "//button[contains(., '+') or contains(@aria-label, 'increase') or contains(@aria-label, 'tambah') or contains(@aria-label, 'add')]",
            )
        except Exception:
            plus_buttons = []

        for button in plus_buttons:
            try:
                if not button.is_displayed():
                    continue
                for _ in range(quantity - 1):
                    self.driver.execute_script("arguments[0].click();", button)
                    time.sleep(0.2)
                return True
            except Exception:
                continue

        return False

    def _click_checkout(self) -> bool:
        keywords = ["lanjut", "continue", "checkout", "pesan", "beli", "book", "order", "next", "proceed"]
        try:
            buttons = self.driver.find_elements(By.XPATH, "//button | //a[@role='button'] | //*[@role='button']")
        except Exception:
            return False

        for button in buttons:
            try:
                text = (button.text or "").strip().lower()
            except Exception:
                text = ""
            if not text:
                continue
            if not any(token in text for token in keywords):
                continue
            try:
                if button.get_attribute("disabled") is not None:
                    continue
            except Exception:
                pass
            if self.click_button(button).clicked:
                return True
        return False

    def _is_checkout_url(self) -> bool:
        try:
            url = (self.driver.current_url or "").lower()
        except Exception:
            return False
        return any(token in url for token in ["checkout", "booking", "order", "payment"])

    def _attempt_auto_buy(self):
        for _ in range(20):
            if self._should_stop():
                return False
            if self._is_checkout_url():
                print("Checkout detected. Complete purchase manually.")
                return True
            self._set_quantity(self.quantity)
            if self._click_checkout():
                print("Checkout clicked. Complete purchase manually.")
                return True
            time.sleep(1)
        return False

    def run(self):
        if not self.url:
            print("URL harus diisi.")
            return False
        if not self.button_text:
            print("Text tombol harus diisi.")
            return False

        print("Browser...")
        if not self.setup_driver():
            return False

        try:
            if self.debugger_address and self.open_new_tab:
                self._open_new_tab()

            print(f"Opening: {self.url}")
            self.driver.get(self.url)
            self._random_delay(1.2, 2.0)

            attempt = 0
            while attempt < self.max_attempts:
                if self._should_stop():
                    print("Stop requested. Exiting.")
                    return False
                attempt += 1

                if self._page_needs_attention():
                    print("Page needs manual verification/login.")
                    if self.interactive:
                        input("Press Enter after completing verification...")

                buttons = self.find_buttons_by_text() or []
                if buttons:
                    statuses = []
                    for btn in buttons:
                        status = self.check_button_status(btn)
                        statuses.append(status)

                    enabled_buttons = [btn for btn, status in zip(buttons, statuses) if status == 'enabled']
                    if enabled_buttons:
                        result = self.click_button(enabled_buttons[0])
                        if result.clicked:
                            print(f"Clicked ({result.reason}).")
                            if self.auto_buy:
                                self._attempt_auto_buy()
                            return True

                if attempt % self.log_every == 0:
                    now = datetime.now().strftime("%H:%M:%S")
                    print(f"[{now}] Refresh attempt {attempt}")

                # Use random delay for refresh (0.5-4 seconds like loket)
                # If refresh_seconds is set, use it as max, with min being 0.5
                min_delay = 0.5
                max_delay = max(min_delay, float(self.refresh_seconds))
                if max_delay > 4.0:
                    max_delay = 4.0
                delay = self._random_delay(min_delay, max_delay)
                
                try:
                    self.driver.refresh()
                    # Small delay after refresh to let page load
                    self._random_delay(0.4, 1.0)
                except WebDriverException:
                    self._random_delay(min_delay, max_delay)
            print("Max attempts reached.")
            return False
        finally:
            if self.close_on_exit is None and self.interactive:
                try:
                    keep_open = input("Keep browser open? (y/n): ").strip().lower()
                except Exception:
                    keep_open = "y"
                close = keep_open == "n"
            else:
                close = bool(self.close_on_exit)

            if close:
                try:
                    self.driver.quit()
                except Exception:
                    pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ticketmaster simple bot")
    parser.add_argument("--url", type=str, default=config.TICKETMASTER_URL, help="Ticketmaster event URL")
    parser.add_argument("--button", type=str, default=config.TICKETMASTER_BUTTON_TEXT, help="Button text to search")
    parser.add_argument("--refresh", type=float, default=config.TICKETMASTER_REFRESH_SECONDS, help="Refresh interval (seconds)")
    parser.add_argument("--max-attempts", type=int, default=config.TICKETMASTER_MAX_ATTEMPTS, help="Max attempts")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--no-headless", action="store_true", help="Run visible")
    parser.add_argument("--auto-buy", action="store_true", help="Attempt auto-buy after click")
    parser.add_argument("--no-auto-buy", action="store_true", help="Disable auto-buy")
    parser.add_argument("--quantity", type=int, default=config.TICKETMASTER_QUANTITY, help="Ticket quantity")
    parser.add_argument("--debugger", type=str, default="", help="Chrome debugger address")
    parser.add_argument("--open-new-tab", action="store_true", help="Open new tab when attaching")
    parser.add_argument("--no-open-new-tab", action="store_true", help="Disable new tab")
    parser.add_argument("--user-data-dir", type=str, default=config.TICKETMASTER_USER_DATA_DIR, help="Chrome user data dir")
    parser.add_argument("--new-session", action="store_true", help="Use a fresh user data dir")
    parser.add_argument("--no-new-session", action="store_true", help="Reuse default profile")
    parser.add_argument("--non-interactive", action="store_true", help="Disable prompts")

    args = parser.parse_args()

    url = args.url or ""
    button_text = args.button or ""

    if not url and not args.non_interactive:
        url = input("Link event: ").strip()
    if not button_text and not args.non_interactive:
        button_text = input("Text tombol: ").strip()

    headless = config.TICKETMASTER_HEADLESS
    if args.no_headless:
        headless = False
    elif args.headless:
        headless = True

    auto_buy = config.TICKETMASTER_AUTO_BUY
    if args.no_auto_buy:
        auto_buy = False
    elif args.auto_buy:
        auto_buy = True

    open_new_tab = config.TICKETMASTER_OPEN_NEW_TAB
    if args.no_open_new_tab:
        open_new_tab = False
    elif args.open_new_tab:
        open_new_tab = True

    new_session = config.TICKETMASTER_NEW_SESSION
    if args.no_new_session:
        new_session = False
    elif args.new_session:
        new_session = True

    bot = TicketmasterSimpleBot(
        url=url,
        button_text=button_text,
        refresh_seconds=args.refresh,
        max_attempts=args.max_attempts,
        headless=headless,
        auto_buy=auto_buy,
        quantity=args.quantity,
        debugger_address=args.debugger,
        open_new_tab=open_new_tab,
        user_data_dir=args.user_data_dir,
        new_session=new_session,
        interactive=not args.non_interactive,
    )
    bot.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped by user")
    except Exception as exc:
        print(f"Fatal error: {exc}")

"""Auto-buy bot for Tiket.com package pages."""
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from selenium import webdriver
from selenium.common.exceptions import WebDriverException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

try:
    from . import config
except ImportError:
    try:
        from tiket import config
    except ImportError:
        import config


ACTION_KEYWORDS = ["pilih", "select", "beli", "pesan", "book", "buy", "order", "checkout"]
IGNORE_KEYWORDS = ["detail", "info", "terms", "syarat", "faq", "lihat"]
UNAVAILABLE_KEYWORDS = ["sold out", "habis", "penuh", "tidak tersedia", "unavailable", "not available"]


@dataclass
class PackageOption:
    name: str
    button: object
    available: bool
    raw_text: str


class TiketAutoBuyBot:
    def __init__(
        self,
        url: str,
        package_name: str = "",
        quantity: int = 1,
        headless: bool = False,
        refresh_seconds: float = 3.0,
        max_attempts: int = 500,
        debugger_address: str = "",
        open_new_tab: bool = False,
        user_data_dir: str = "",
        interactive: bool = True,
    ):
        self.url = url
        self.package_name = (package_name or "").strip()
        self.quantity = max(1, min(int(quantity or 1), 6))
        self.headless = headless
        self.refresh_seconds = max(0.5, float(refresh_seconds))
        self.max_attempts = max(1, int(max_attempts))
        self.debugger_address = (debugger_address or "").strip()
        self.open_new_tab = open_new_tab
        self.user_data_dir = (user_data_dir or "").strip()
        self.interactive = interactive
        self.driver = None
        self.wait = None
        self.log_every = 5

    def setup_driver(self) -> bool:
        chrome_options = Options()
        if self.debugger_address:
            chrome_options.add_experimental_option("debuggerAddress", self.debugger_address)
        else:
            if self.headless:
                chrome_options.add_argument("--headless=new")
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
            if self.user_data_dir:
                chrome_options.add_argument(f"--user-data-dir={os.path.abspath(self.user_data_dir)}")

        try:
            if self.debugger_address:
                self.driver = webdriver.Chrome(options=chrome_options)
            else:
                service = None
                chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "").strip()
                if chromedriver_path:
                    service = Service(chromedriver_path)
                else:
                    path_driver = shutil.which("chromedriver") or shutil.which("chromedriver.exe")
                    if path_driver:
                        service = Service(path_driver)

                if not service:
                    service = Service(ChromeDriverManager().install())

                self.driver = webdriver.Chrome(service=service, options=chrome_options)

            if not self.debugger_address:
                self.driver.maximize_window()
            self.wait = WebDriverWait(self.driver, 15)
            return True
        except Exception as exc:
            print(f"Error setting up browser: {exc}")
            return False

    def _open_new_tab(self) -> bool:
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

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", str(text or "")).strip()

    def _page_is_challenge(self) -> bool:
        try:
            title = (self.driver.title or "").lower()
            if "just a moment" in title:
                return True
            source = (self.driver.page_source or "").lower()
            if "cf-chl" in source or "challenge" in source and "cloudflare" in source:
                return True
            return False
        except Exception:
            return False

    def _wait_for_challenge(self):
        if not self._page_is_challenge():
            return
        print("Cloudflare challenge detected. Solve it in the browser.")
        if self.interactive:
            input("Press Enter after the page is ready...")
        else:
            time.sleep(6)

    def _wait_for_body(self, timeout: int = 20):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except Exception:
            pass

    def _element_is_disabled(self, elem) -> bool:
        try:
            if elem.get_attribute("disabled") is not None:
                return True
        except Exception:
            pass
        try:
            if (elem.get_attribute("aria-disabled") or "").lower() == "true":
                return True
        except Exception:
            pass
        try:
            classes = elem.get_attribute("class") or ""
            if "disabled" in classes.lower():
                return True
        except Exception:
            pass
        return False

    def _button_text(self, elem) -> str:
        text = ""
        try:
            text = elem.text or ""
        except Exception:
            text = ""
        text = self._normalize_text(text)
        if text:
            return text
        for attr in ("aria-label", "title", "data-testid"):
            try:
                value = elem.get_attribute(attr) or ""
            except Exception:
                value = ""
            value = self._normalize_text(value)
            if value:
                return value
        return ""

    def _find_card_for_button(self, button):
        try:
            return button.find_element(By.XPATH, "./ancestor::*[self::div or self::section][1]")
        except Exception:
            return None

    def _extract_package_name(self, card) -> str:
        if not card:
            return ""
        headings = []
        try:
            headings = card.find_elements(By.XPATH, ".//h1 | .//h2 | .//h3 | .//h4 | .//h5")
        except Exception:
            headings = []
        for heading in headings:
            try:
                text = self._normalize_text(heading.text)
                if text:
                    return text
            except Exception:
                continue

        try:
            text = self._normalize_text(card.text)
        except Exception:
            text = ""
        if text:
            return text.splitlines()[0]
        return ""

    def _collect_packages(self) -> List[PackageOption]:
        packages: List[PackageOption] = []
        try:
            buttons = self.driver.find_elements(By.XPATH, "//button | //a[@role='button'] | //a")
        except Exception:
            return packages

        for button in buttons:
            try:
                if not button.is_displayed():
                    continue
            except Exception:
                continue

            text = self._button_text(button).lower()
            if not text:
                continue
            if any(token in text for token in IGNORE_KEYWORDS):
                continue
            if not any(token in text for token in ACTION_KEYWORDS):
                continue

            card = self._find_card_for_button(button)
            card_text = ""
            if card:
                try:
                    card_text = self._normalize_text(card.text)
                except Exception:
                    card_text = ""
            name = self._extract_package_name(card) or text

            available = True
            if self._element_is_disabled(button):
                available = False
            if card_text:
                lower_card = card_text.lower()
                if any(token in lower_card for token in UNAVAILABLE_KEYWORDS):
                    available = False

            packages.append(PackageOption(name=name, button=button, available=available, raw_text=card_text))

        return packages

    def _choose_package(self, packages: List[PackageOption]) -> Optional[PackageOption]:
        if not packages:
            return None
        if self.package_name:
            target = self.package_name.lower()
            for pkg in packages:
                if target in (pkg.name or "").lower():
                    return pkg
            return None

        if not self.interactive:
            return packages[0]

        print("Available packages:")
        for idx, pkg in enumerate(packages, 1):
            status = "available" if pkg.available else "unavailable"
            print(f"  {idx}. {pkg.name} ({status})")

        choice = input("Select package number: ").strip()
        if not choice.isdigit():
            return None
        index = int(choice)
        if index < 1 or index > len(packages):
            return None
        return packages[index - 1]

    def _safe_click(self, elem) -> bool:
        try:
            elem.click()
            return True
        except Exception:
            pass
        try:
            self.driver.execute_script("arguments[0].click();", elem)
            return True
        except Exception:
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

        plus_buttons = []
        try:
            plus_buttons = self.driver.find_elements(
                By.XPATH,
                "//button[contains(., '+') or contains(@aria-label, 'increase') or contains(@aria-label, 'tambah')]",
            )
        except Exception:
            plus_buttons = []

        for button in plus_buttons:
            try:
                if not button.is_displayed():
                    continue
                if self._element_is_disabled(button):
                    continue
                for _ in range(quantity - 1):
                    self._safe_click(button)
                    time.sleep(0.2)
                return True
            except Exception:
                continue

        return False

    def _click_checkout(self) -> bool:
        keywords = ["lanjut", "continue", "checkout", "pesan", "beli", "book", "order", "next"]
        try:
            buttons = self.driver.find_elements(By.XPATH, "//button | //a[@role='button']")
        except Exception:
            return False

        for button in buttons:
            text = self._button_text(button).lower()
            if not text:
                continue
            if not any(token in text for token in keywords):
                continue
            if self._element_is_disabled(button):
                continue
            if not self._safe_click(button):
                continue
            return True
        return False

    def _is_checkout_url(self) -> bool:
        try:
            url = (self.driver.current_url or "").lower()
        except Exception:
            return False
        return any(token in url for token in ["checkout", "booking", "order", "payment"])

    def auto_buy(self) -> bool:
        attempts = 0
        while attempts < self.max_attempts:
            attempts += 1

            if attempts % self.log_every == 0:
                now = datetime.now().strftime("%H:%M:%S")
                print(f"[{now}] Attempt {attempts}")

            try:
                packages = self._collect_packages()
                selected = self._choose_package(packages)
                if not selected:
                    time.sleep(self.refresh_seconds)
                    self.driver.refresh()
                    self._wait_for_challenge()
                    continue

                if not selected.available:
                    time.sleep(self.refresh_seconds)
                    self.driver.refresh()
                    self._wait_for_challenge()
                    continue

                if not self._safe_click(selected.button):
                    time.sleep(self.refresh_seconds)
                    self.driver.refresh()
                    self._wait_for_challenge()
                    continue

                time.sleep(2)
                self._set_quantity(self.quantity)

                if self._is_checkout_url():
                    print("Checkout page detected. Complete purchase manually.")
                    return True

                if self._click_checkout():
                    print("Checkout button clicked. Complete purchase manually.")
                    return True

                time.sleep(self.refresh_seconds)
                self.driver.refresh()
                self._wait_for_challenge()
            except WebDriverException as exc:
                print(f"WebDriver error: {exc}")
                try:
                    self.driver.refresh()
                except Exception:
                    pass
                time.sleep(self.refresh_seconds)
            except Exception as exc:
                print(f"Error: {exc}")
                time.sleep(self.refresh_seconds)

        return False

    def start(self) -> bool:
        if not self.url:
            print("URL is required.")
            return False

        if not self.setup_driver():
            return False

        try:
            if self.debugger_address and self.open_new_tab:
                self._open_new_tab()

            print(f"Opening: {self.url}")
            self.driver.get(self.url)
            self._wait_for_body()
            self._wait_for_challenge()

            if not self.package_name and self.interactive:
                packages = self._collect_packages()
                if packages:
                    chosen = self._choose_package(packages)
                    if chosen:
                        self.package_name = chosen.name

            return self.auto_buy()
        finally:
            if self.interactive:
                try:
                    keep_open = input("Keep browser open? (y/n): ").strip().lower()
                except Exception:
                    keep_open = "y"
                if keep_open != "y":
                    try:
                        self.driver.quit()
                    except Exception:
                        pass


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Tiket.com auto-buy bot")
    parser.add_argument("--url", type=str, default=config.TIKET_URL, help="Tiket.com event packages URL")
    parser.add_argument("--package", dest="package_name", type=str, default=config.TIKET_PACKAGE, help="Package name")
    parser.add_argument("--quantity", type=int, default=config.TIKET_QUANTITY, help="Ticket quantity")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--no-headless", action="store_true", help="Run with visible browser")
    parser.add_argument("--refresh", type=float, default=config.TIKET_REFRESH_SECONDS, help="Refresh interval (seconds)")
    parser.add_argument("--max-attempts", type=int, default=config.TIKET_MAX_ATTEMPTS, help="Max attempts")
    parser.add_argument("--debugger", type=str, default="", help="Chrome debugger address (127.0.0.1:9222)")
    parser.add_argument("--user-data-dir", type=str, default="", help="Chrome user-data-dir path")
    parser.add_argument("--open-new-tab", action="store_true", help="Open new tab when attaching")
    parser.add_argument("--non-interactive", action="store_true", help="Disable prompts")

    args = parser.parse_args()

    headless = config.TIKET_HEADLESS
    if args.headless:
        headless = True
    elif args.no_headless:
        headless = False

    bot = TiketAutoBuyBot(
        url=args.url,
        package_name=args.package_name,
        quantity=args.quantity,
        headless=headless,
        refresh_seconds=args.refresh,
        max_attempts=args.max_attempts,
        debugger_address=args.debugger,
        open_new_tab=args.open_new_tab,
        user_data_dir=args.user_data_dir,
        interactive=not args.non_interactive,
    )
    bot.start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped by user")
    except Exception as exc:
        print(f"Fatal error: {exc}")

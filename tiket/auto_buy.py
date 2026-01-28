"""Auto-buy bot for Tiket.com package pages."""
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

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


# Keywords for package selection buttons ONLY
ACTION_KEYWORDS = ["pilih", "select", "beli", "add", "tambah", "cari tiket", "find tickets"]
# Keywords for checkout/next steps
CHECKOUT_KEYWORDS = ["lanjut", "continue", "checkout", "pesan", "beli", "book", "order", "next", "bayar", "payment"]

IGNORE_KEYWORDS = ["detail", "info", "terms", "syarat", "faq", "lihat", "history", "riwayat", "help", "bantuan", "login", "masuk", "daftar", "register"]
UNAVAILABLE_KEYWORDS = ["sold out", "habis", "penuh", "tidak tersedia", "unavailable", "not available"]
CLASS_DISABLED_TOKENS = {
    "disabled",
    "is-disabled",
    "btn-disabled",
    "btn--disabled",
    "button-disabled",
    "disabled-state",
}


def _resolve_chromedriver_path(path: str) -> str:
    path = (path or "").strip().strip('"')
    if not path:
        return ""
    if os.path.isdir(path):
        for name in ("chromedriver.exe", "chromedriver"):
            candidate = os.path.join(path, name)
            if os.path.isfile(candidate):
                return candidate
        return path
    base = os.path.basename(path).lower()
    if base in ("chromedriver.exe", "chromedriver"):
        return path
    folder = os.path.dirname(path)
    for name in ("chromedriver.exe", "chromedriver"):
        candidate = os.path.join(folder, name)
        if os.path.isfile(candidate):
            return candidate
    return path


def _xpath_literal(value: str) -> str:
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    parts = value.split("'")
    return "concat(" + ", \"'\", ".join(f"'{part}'" for part in parts) + ")"


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
        debug: bool = False,
        auto_checkout: bool = True,
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
        self.debug = bool(debug)
        self.auto_checkout = bool(auto_checkout)
        self.interactive = interactive
        self.driver = None
        self.wait = None
        self.log_every = 5

    def setup_driver(self) -> bool:
        chrome_options = Options()
        self._debug(
            f"setup_driver headless={self.headless} debugger={'yes' if self.debugger_address else 'no'} "
            f"open_new_tab={self.open_new_tab} user_data_dir={self.user_data_dir or '-'} "
            f"auto_checkout={self.auto_checkout}"
        )
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
                chromedriver_path = _resolve_chromedriver_path(
                    os.environ.get("CHROMEDRIVER_PATH", "")
                )
                if chromedriver_path:
                    service = Service(chromedriver_path)
                else:
                    path_driver = shutil.which("chromedriver") or shutil.which("chromedriver.exe")
                    if path_driver:
                        service = Service(_resolve_chromedriver_path(path_driver))

                if not service:
                    driver_path = _resolve_chromedriver_path(ChromeDriverManager().install())
                    service = Service(driver_path)

                self.driver = webdriver.Chrome(service=service, options=chrome_options)

            if not self.debugger_address:
                self.driver.maximize_window()
            self.wait = WebDriverWait(self.driver, 15)
            self._debug("driver ready")
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

    def _normalize_match(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())

    def _scroll_into_view(self, elem) -> None:
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                elem,
            )
            time.sleep(0.15)
        except Exception:
            pass

    def _debug(self, message: str) -> None:
        if not self.debug:
            return
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[debug {now}] {message}")

    def _describe_element(self, elem) -> str:
        try:
            tag = elem.tag_name
        except Exception:
            tag = "?"
        attrs = {}
        for name in (
            "id",
            "name",
            "class",
            "data-testid",
            "data-qa",
            "aria-label",
            "aria-haspopup",
            "role",
        ):
            try:
                value = (elem.get_attribute(name) or "").strip()
            except Exception:
                value = ""
            if value:
                attrs[name] = self._normalize_text(value)
        try:
            text = self._normalize_text(elem.text)
        except Exception:
            text = ""
        if text and len(text) > 80:
            text = text[:77] + "..."
        attr_str = " ".join(f"{key}='{val}'" for key, val in attrs.items())
        if text:
            return f"<{tag} {attr_str} text='{text}'>"
        return f"<{tag} {attr_str}>"

    def _describe_button_state(self, elem) -> str:
        reasons = self._disabled_reasons(elem)
        return f"{self._describe_element(elem)} disabled={reasons or '-'}"

    def _log_quantity_controls(self) -> None:
        if not self.debug:
            return
        try:
            url = self.driver.current_url
        except Exception:
            url = ""
        if url:
            self._debug(f"quantity: current_url={url}")

        def visible(elements):
            shown = []
            for elem in elements:
                try:
                    if elem.is_displayed():
                        shown.append(elem)
                except Exception:
                    continue
            return shown

        try:
            dialogs = self.driver.find_elements(
                By.XPATH,
                "//*[@role='dialog' or contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'modal') "
                "or contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'drawer') "
                "or contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sheet')]",
            )
        except Exception:
            dialogs = []
        dialogs = visible(dialogs)
        self._debug(f"quantity: dialog candidates={len(dialogs)}")
        for idx, dialog in enumerate(dialogs[:3], 1):
            self._debug(f"quantity: dialog[{idx}] {self._describe_element(dialog)}")

        try:
            comboboxes = self.driver.find_elements(
                By.XPATH,
                "//*[@role='combobox' or @aria-haspopup='listbox']",
            )
        except Exception:
            comboboxes = []
        comboboxes = visible(comboboxes)
        self._debug(f"quantity: combobox candidates={len(comboboxes)}")
        for idx, combo in enumerate(comboboxes[:5], 1):
            self._debug(f"quantity: combobox[{idx}] {self._describe_element(combo)}")

        try:
            listboxes = self.driver.find_elements(By.XPATH, "//*[@role='listbox']")
        except Exception:
            listboxes = []
        listboxes = visible(listboxes)
        self._debug(f"quantity: listbox candidates={len(listboxes)}")
        for idx, box in enumerate(listboxes[:3], 1):
            self._debug(f"quantity: listbox[{idx}] {self._describe_element(box)}")

        try:
            options = self.driver.find_elements(By.XPATH, "//*[@role='option']")
        except Exception:
            options = []
        options = visible(options)
        self._debug(f"quantity: option candidates={len(options)}")
        for idx, opt in enumerate(options[:5], 1):
            self._debug(f"quantity: option[{idx}] {self._describe_element(opt)}")

        try:
            keyword_elems = self.driver.find_elements(
                By.XPATH,
                "//*[contains(translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'jumlah') "
                "or contains(translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'quantity') "
                "or contains(translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'qty')]",
            )
        except Exception:
            keyword_elems = []
        keyword_elems = visible(keyword_elems)
        self._debug(f"quantity: keyword elements={len(keyword_elems)}")
        for idx, elem in enumerate(keyword_elems[:5], 1):
            self._debug(f"quantity: keyword[{idx}] {self._describe_element(elem)}")

    def _is_bad_package_name(self, text: str) -> bool:
        if not text:
            return True
        lower = text.lower()
        if any(token in lower for token in IGNORE_KEYWORDS):
            return True
        if any(token in lower for token in ACTION_KEYWORDS) and len(lower.split()) <= 2:
            return True
        if any(token in lower for token in UNAVAILABLE_KEYWORDS):
            return True
        if re.fullmatch(r"(rp|idr)?\s*[-\d.,]+", lower):
            return True
        return False

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
        return bool(self._disabled_reasons(elem))

    def _disabled_reasons(self, elem) -> List[str]:
        reasons = []
        try:
            disabled_attr = elem.get_attribute("disabled")
        except Exception:
            disabled_attr = None
        if disabled_attr is not None:
            value = str(disabled_attr).strip().lower()
            if value not in ("false", "0", "none"):
                reasons.append("disabled-attr")
        try:
            aria_disabled = (elem.get_attribute("aria-disabled") or "").strip().lower()
        except Exception:
            aria_disabled = ""
        if aria_disabled == "true":
            reasons.append("aria-disabled")
        try:
            classes = (elem.get_attribute("class") or "").lower().split()
        except Exception:
            classes = []
        if any(token in CLASS_DISABLED_TOKENS for token in classes):
            reasons.append("class-disabled")
        return reasons

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

    def _score_card(self, elem) -> int:
        score = 0
        try:
            data_testid = (elem.get_attribute("data-testid") or "").lower()
        except Exception:
            data_testid = ""
        if any(token in data_testid for token in ["package", "product", "ticket", "card"]):
            score += 2
        try:
            class_name = (elem.get_attribute("class") or "").lower()
        except Exception:
            class_name = ""
        if any(token in class_name for token in ["package", "product", "ticket", "card"]):
            score += 1
        try:
            headings = elem.find_elements(By.XPATH, ".//h1 | .//h2 | .//h3 | .//h4 | .//h5 | .//*[@role='heading']")
        except Exception:
            headings = []
        if headings:
            score += 2
        try:
            text = (elem.text or "").lower()
        except Exception:
            text = ""
        if "rp" in text or "idr" in text:
            score += 1
        if len(text) > 30:
            score += 1
        return score

    def _find_card_for_element(self, elem):
        try:
            ancestors = elem.find_elements(
                By.XPATH,
                "./ancestor::*[self::div or self::section or self::article or self::li]",
            )
        except Exception:
            return None
        best = None
        best_score = -1
        for ancestor in ancestors[:10]:
            try:
                text_len = len(ancestor.text or "")
            except Exception:
                text_len = 0
            action_count = self._count_action_buttons(ancestor)
            score = self._score_card(ancestor)
            if action_count == 1 and score >= 2 and text_len <= 1200:
                return ancestor
            if text_len > 2500:
                continue
            if score > best_score:
                best_score = score
                best = ancestor
        return best

    def _find_card_for_button(self, button):
        return self._find_card_for_element(button)

    def _extract_package_name(self, card) -> str:
        if not card:
            return ""
        candidates = []
        
        # 1. Look for explicit headings
        try:
            candidates += card.find_elements(
                By.XPATH,
                ".//h1 | .//h2 | .//h3 | .//h4 | .//h5 | .//*[@role='heading']",
            )
        except Exception:
            pass
            
        # 2. Look for specific Tiket classes/IDs (heuristics)
        try:
            candidates += card.find_elements(
                By.XPATH,
                ".//*[contains(@class, 'title') or contains(@class, 'name') or contains(@data-testid, 'title')]"
            )
        except Exception:
            pass
            
        # 3. Look for elements with specific data attributes
        try:
            for attr in ["data-testid", "data-qa", "id"]:
                elems = card.find_elements(By.XPATH, f".//*[@{attr}]")
                for el in elems:
                    val = (el.get_attribute(attr) or "").lower()
                    if any(x in val for x in ["package-name", "ticket-title", "product-title"]):
                         candidates.append(el)
        except Exception:
            pass

        seen = set()
        best_candidate = ""
        
        for candidate in candidates:
            try:
                key = candidate.id
            except Exception:
                key = str(candidate)
            if key in seen:
                continue
            seen.add(key)
            
            try:
                if not candidate.is_displayed():
                    continue
                text = self._normalize_text(candidate.text)
            except Exception:
                continue
            
            if self._is_bad_package_name(text):
                continue
                
            # Prefer longer, specific names usually found in headings
            if len(text) > len(best_candidate):
                 best_candidate = text
                 
        if best_candidate:
            return best_candidate

        # Fallback to splitting card text
        try:
            text = self._normalize_text(card.text)
        except Exception:
            text = ""
        if not text:
            return ""
            
        # Heuristic: the first valid line in a card is often the title
        for line in text.splitlines():
            line = self._normalize_text(line)
            if not self._is_bad_package_name(line) and len(line) > 5:
                # Extra check: usually titles don't start with numbers (prices)
                if not re.match(r'^\d', line):
                    return line
        return ""

    def _find_action_button(self, container):
        try:
            buttons = container.find_elements(
                By.XPATH,
                ".//button | .//a[@role='button'] | .//*[@role='button']",
            )
        except Exception:
            return None
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
            return button
        return None

    def _count_action_buttons(self, container) -> int:
        try:
            buttons = container.find_elements(
                By.XPATH,
                ".//button | .//a[@role='button'] | .//*[@role='button']",
            )
        except Exception:
            return 0
        count = 0
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
            count += 1
        return count

    def _unavailable_hits(self, text: str) -> List[str]:
        if not text:
            return []
        lower = text.lower()
        return [token for token in UNAVAILABLE_KEYWORDS if token in lower]

    def _dedupe_packages(self, packages: List[PackageOption]) -> List[PackageOption]:
        if not packages:
            return packages
        deduped: List[PackageOption] = []
        seen: Dict[str, int] = {}
        for pkg in packages:
            key = self._normalize_match(pkg.name) or self._normalize_match(pkg.raw_text)
            if not key:
                deduped.append(pkg)
                continue
            if key not in seen:
                seen[key] = len(deduped)
                deduped.append(pkg)
                continue
            idx = seen[key]
            current = deduped[idx]
            if not current.available and pkg.available:
                deduped[idx] = pkg
            elif current.available == pkg.available:
                if len(pkg.raw_text or "") < len(current.raw_text or ""):
                    deduped[idx] = pkg
        return deduped

    def _collect_packages(self) -> List[PackageOption]:
        packages: List[PackageOption] = []
        try:
            # More inclusive XPath for buttons/clickables
            buttons = self.driver.find_elements(
                By.XPATH,
                "//button | //a[@role='button'] | //*[@role='button'] | //input[@type='submit' or @type='button']"
            )
        except Exception:
            buttons = []
        self._debug(f"collect_packages: buttons={len(buttons)}")

        seen_buttons = set()
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

            try:
                key = button.id
            except Exception:
                key = str(button)
            if key in seen_buttons:
                continue
            seen_buttons.add(key)

            card = self._find_card_for_button(button)
            card_text = ""
            try:
                card_text = self._normalize_text(card.text if card else "")
            except Exception:
                card_text = ""
            name = self._extract_package_name(card) or self._button_text(button)
            if self._is_bad_package_name(name):
                name = self._button_text(button)

            disabled_reasons = self._disabled_reasons(button)
            text_hits = self._unavailable_hits(card_text)
            text_len = len(card_text)
            available = True
            if disabled_reasons:
                available = False
            elif text_hits and text_len <= 400:
                available = False
            elif text_hits and text_len > 400:
                self._debug(
                    f"availability: ignore text hits (len={text_len}) hits={text_hits}"
                )

            packages.append(PackageOption(name=name, button=button, available=available, raw_text=card_text))
            if self.debug:
                action_text = self._button_text(button)
                self._debug(
                    "package: name='{name}' action='{action}' available={available} "
                    "disabled={disabled} text_hits={hits} text_len={length}".format(
                        name=name,
                        action=action_text,
                        available=available,
                        disabled=disabled_reasons or "-",
                        hits=text_hits or "-",
                        length=text_len,
                    )
                )

        if packages:
            return self._dedupe_packages(packages)

        # Removed risky fallback logic that was clicking navigation links
        self._debug("collect_packages: no packages found via primary method")
        return []

    def _choose_package(self, packages: List[PackageOption]) -> Optional[PackageOption]:
        if not packages:
            self._debug("choose_package: no packages found")
            return None
        if self.package_name:
            target = self._normalize_match(self.package_name)
            fallback = None
            for pkg in packages:
                name_norm = self._normalize_match(pkg.name)
                raw_norm = self._normalize_match(pkg.raw_text)
                if target and (target in name_norm or target in raw_norm):
                    if pkg.available:
                        return pkg
                    if fallback is None:
                        fallback = pkg
            if fallback:
                return fallback
            if self.debug:
                names = [pkg.name for pkg in packages[:10] if pkg.name]
                self._debug(
                    "choose_package: target not matched; candidates="
                    + ", ".join(names)
                )
            return None

        if not self.interactive:
            for pkg in packages:
                if pkg.available:
                    return pkg
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
        self._scroll_into_view(elem)
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

    def _set_quantity_via_combobox(self, quantity: int) -> bool:
        target = str(quantity)
        try:
            combos = self.driver.find_elements(
                By.XPATH,
                "//*[@role='combobox' or @aria-haspopup='listbox' "
                "or contains(@data-testid, 'quantity') or contains(@data-qa, 'quantity') "
                "or contains(@data-testid, 'qty') or contains(@data-qa, 'qty')]",
            )
        except Exception:
            combos = []

        visible_combos = []
        for combo in combos:
            try:
                if combo.is_displayed():
                    visible_combos.append(combo)
            except Exception:
                continue
        if not visible_combos:
            return False

        matched = []
        for combo in visible_combos:
            if self._combobox_matches_quantity(combo):
                matched.append(combo)
        if not matched and len(visible_combos) == 1:
            matched = visible_combos

        for combo in matched:
            if not self._safe_click(combo):
                continue
            time.sleep(0.3)
            if self._select_quantity_option(target):
                self._debug("quantity: set via combobox")
                return True
            try:
                self.driver.execute_script("arguments[0].blur();", combo)
            except Exception:
                pass
        return False

    def _set_quantity_via_label_trigger(self, quantity: int) -> bool:
        target = str(quantity)
        triggers = self._find_quantity_triggers()
        if not triggers:
            return False
        if self.debug:
            self._debug(f"quantity: label triggers={len(triggers)}")
            for idx, trig in enumerate(triggers[:5], 1):
                self._debug(f"quantity: trigger[{idx}] {self._describe_element(trig)}")
        for trigger in triggers:
            if not self._safe_click(trigger):
                continue
            time.sleep(0.3)
            if self._select_quantity_option(target):
                self._debug("quantity: set via label trigger")
                return True
            try:
                self.driver.execute_script("arguments[0].blur();", trigger)
            except Exception:
                pass
        return False

    def _find_quantity_triggers(self):
        try:
            labels = self.driver.find_elements(
                By.XPATH,
                "//*[contains(translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'jumlah') "
                "or contains(translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'quantity') "
                "or contains(translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'qty')]",
            )
        except Exception:
            return []
        triggers = []
        seen = set()
        for label in labels:
            try:
                container = label.find_element(
                    By.XPATH,
                    "./ancestor::*[self::div or self::section or self::form][1]",
                )
            except Exception:
                continue
            try:
                candidates = container.find_elements(
                    By.XPATH,
                    ".//*[self::button or @role='button' or @role='combobox' "
                    "or @aria-haspopup='listbox']",
                )
            except Exception:
                candidates = []
            for candidate in candidates:
                try:
                    if not candidate.is_displayed():
                        continue
                except Exception:
                    continue
                text = self._button_text(candidate).lower()
                if text and any(token in text for token in ACTION_KEYWORDS):
                    continue
                try:
                    key = candidate.id
                except Exception:
                    key = str(candidate)
                if key in seen:
                    continue
                seen.add(key)
                triggers.append(candidate)
        return triggers

    def _combobox_matches_quantity(self, combo) -> bool:
        keywords = ("jumlah", "quantity", "qty", "tiket", "ticket")
        try:
            data_testid = (combo.get_attribute("data-testid") or "").lower()
        except Exception:
            data_testid = ""
        try:
            data_qa = (combo.get_attribute("data-qa") or "").lower()
        except Exception:
            data_qa = ""
        try:
            aria_label = (combo.get_attribute("aria-label") or "").lower()
        except Exception:
            aria_label = ""
        try:
            placeholder = (combo.get_attribute("placeholder") or "").lower()
        except Exception:
            placeholder = ""
        try:
            title = (combo.get_attribute("title") or "").lower()
        except Exception:
            title = ""
        if any(key in data_testid for key in keywords) or any(key in data_qa for key in keywords):
            return True
        if any(key in aria_label for key in keywords):
            return True
        if any(key in placeholder for key in keywords):
            return True
        if any(key in title for key in keywords):
            return True
        try:
            container = combo.find_element(
                By.XPATH,
                "./ancestor::*[self::div or self::section or self::form][1]",
            )
        except Exception:
            return False
        try:
            text = self._normalize_text(container.text).lower()
        except Exception:
            text = ""
        return any(key in text for key in keywords)

    def _select_quantity_option(self, target: str) -> bool:
        options = []
        try:
            options = self.driver.find_elements(By.XPATH, "//*[@role='option']")
        except Exception:
            options = []
        if not options:
            try:
                options = self.driver.find_elements(By.XPATH, "//li")
            except Exception:
                options = []

        visible_options = []
        for opt in options:
            try:
                if opt.is_displayed():
                    visible_options.append(opt)
            except Exception:
                continue

        if self.debug:
            self._debug(f"quantity: options visible={len(visible_options)}")
            for idx, opt in enumerate(visible_options[:6], 1):
                self._debug(f"quantity: option[{idx}] {self._describe_element(opt)}")

        for opt in visible_options:
            try:
                text = self._normalize_text(opt.text)
            except Exception:
                text = ""
            if not text:
                continue
            digits = re.findall(r"\d+", text)
            if digits and digits[0] == target:
                if self._safe_click(opt):
                    return True
            if text.strip() == target:
                if self._safe_click(opt):
                    return True
        return False

    def _wait_for_quantity_controls(self, timeout: int = 5) -> None:
        def has_controls(driver) -> bool:
            selectors = [
                (By.XPATH, "//select"),
                (By.XPATH, "//input[@type='number' or @inputmode='numeric']"),
                (By.XPATH, "//*[@role='combobox' or @aria-haspopup='listbox']"),
                (By.XPATH, "//*[@role='spinbutton']"),
                (By.XPATH, "//*[@role='listbox']"),
            ]
            for by, selector in selectors:
                try:
                    elems = driver.find_elements(by, selector)
                except Exception:
                    continue
                for elem in elems:
                    try:
                        if elem.is_displayed():
                            return True
                    except Exception:
                        continue
            return False

        try:
            WebDriverWait(self.driver, timeout).until(has_controls)
        except Exception:
            pass

    def _set_quantity(self, quantity: int) -> bool:
        if quantity <= 1:
            self._debug("quantity: target <= 1, skip")
            return True
        self._debug(f"quantity: target={quantity}")

        try:
            selects = self.driver.find_elements(By.XPATH, "//select")
        except Exception:
            selects = []
        if self.debug:
            self._debug(f"quantity: select elements={len(selects)}")
            for idx, select_elem in enumerate(selects[:3], 1):
                self._debug(f"quantity: select[{idx}] {self._describe_element(select_elem)}")
                try:
                    options = select_elem.find_elements(By.TAG_NAME, "option")
                except Exception:
                    options = []
                if options:
                    values = []
                    for opt in options[:10]:
                        value = (opt.get_attribute("value") or "").strip()
                        text = self._normalize_text(opt.text)
                        if value and text and value != text:
                            values.append(f"{value}:{text}")
                        else:
                            values.append(value or text)
                    if len(options) > 10:
                        values.append("...")
                    self._debug(f"quantity: select[{idx}] options={', '.join(values)}")
        for select_elem in selects:
            if self._set_quantity_from_select(select_elem, quantity):
                self._debug("quantity: set via <select>")
                return True

        if self._set_quantity_via_combobox(quantity):
            return True
        if self._set_quantity_via_label_trigger(quantity):
            return True

        try:
            inputs = self.driver.find_elements(
                By.XPATH,
                "//input[@type='number' or @inputmode='numeric']",
            )
        except Exception:
            inputs = []
        if self.debug:
            self._debug(f"quantity: numeric inputs={len(inputs)}")
            for idx, input_elem in enumerate(inputs[:3], 1):
                self._debug(f"quantity: input[{idx}] {self._describe_element(input_elem)}")
        for input_elem in inputs:
            try:
                input_elem.clear()
                input_elem.send_keys(str(quantity))
                self._debug("quantity: set via numeric input")
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
        if self.debug:
            self._debug(f"quantity: plus buttons={len(plus_buttons)}")
            for idx, button in enumerate(plus_buttons[:3], 1):
                self._debug(f"quantity: plus[{idx}] {self._describe_element(button)}")

        for button in plus_buttons:
            try:
                if not button.is_displayed():
                    continue
                if self._element_is_disabled(button):
                    continue
                for _ in range(quantity - 1):
                    self._safe_click(button)
                    time.sleep(0.2)
                self._debug("quantity: set via plus button")
                return True
            except Exception:
                continue

        self._log_quantity_controls()
        return False

    def _click_checkout(self) -> bool:
        # Use centralized keywords
        keywords = CHECKOUT_KEYWORDS
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
        self._debug("checkout: button not found")
        return False

    def _is_checkout_url(self) -> bool:
        try:
            url = (self.driver.current_url or "").lower()
        except Exception:
            return False
        return any(token in url for token in ["checkout", "booking", "order", "payment"])

    def _find_target_package_direct(self) -> Optional[PackageOption]:
        target = self._normalize_text(self.package_name).lower()
        if not target:
            return None
        literal = _xpath_literal(target)
        queries = [
            "//h1 | //h2 | //h3 | //h4 | //h5 | //*[@role='heading']",
            "//*[@data-testid or @data-qa]",
            "//p | //span",
        ]
        for query in queries:
            xpath = (
                f"{query}[contains(translate(normalize-space(.), "
                f"'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), {literal})]"
            )
            try:
                matches = self.driver.find_elements(By.XPATH, xpath)
            except Exception:
                matches = []
            for match in matches:
                card = self._find_card_for_element(match)
                if not card:
                    continue
                button = self._find_action_button(card)
                if not button:
                    continue
                card_text = ""
                try:
                    card_text = self._normalize_text(card.text)
                except Exception:
                    card_text = ""
                available = True
                if self._element_is_disabled(button):
                    available = False
                if card_text:
                    lower_card = card_text.lower()
                    if any(token in lower_card for token in UNAVAILABLE_KEYWORDS):
                        available = False
                name = self._extract_package_name(card) or self._button_text(button)
                self._debug(f"direct match: name='{name}' available={available}")
                return PackageOption(name=name, button=button, available=available, raw_text=card_text)
        self._debug("direct match: not found")
        return None

    def _wait_for_packages(self, timeout: int = 10):
        """Wait for package buttons to appear."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check for any actionable button or package card detection
                buttons = self.driver.find_elements(
                    By.XPATH,
                    "//button | //a[@role='button'] | //*[@data-testid='package-card']"
                )
                valid_buttons = 0
                for btn in buttons:
                     if btn.is_displayed():
                         valid_buttons += 1
                
                if valid_buttons > 0:
                     return
            except Exception:
                pass
            time.sleep(0.5)

    def auto_buy(self) -> bool:
        attempts = 0
        while attempts < self.max_attempts:
            attempts += 1

            if attempts % self.log_every == 0:
                now = datetime.now().strftime("%H:%M:%S")
                print(f"[{now}] Attempt {attempts}")

            try:
                # Wait for packages to load before collecting
                self._wait_for_packages(timeout=5)

                packages = self._collect_packages()
                selected = self._choose_package(packages)
                if not selected and self.package_name:
                    selected = self._find_target_package_direct()
                
                # Double check with a small delay if no packages found (sometimes rendering lags)
                if not selected:
                    time.sleep(1.0)
                    packages = self._collect_packages()
                    selected = self._choose_package(packages)

                if not selected:
                    time.sleep(self.refresh_seconds)
                    self.driver.refresh()
                    self._wait_for_challenge()
                    continue

                if self.debug:
                    action_text = self._button_text(selected.button)
                    self._debug(
                        "selected: name='{name}' action='{action}' available={avail} button={btn}".format(
                            name=selected.name,
                            action=action_text,
                            avail=selected.available,
                            btn=self._describe_button_state(selected.button),
                        )
                    )

                if not selected.available:
                    if self.debug:
                        reasons = self._disabled_reasons(selected.button)
                        hits = self._unavailable_hits(selected.raw_text)
                        self._debug(
                            "selected unavailable: {name} disabled={disabled} text_hits={hits}".format(
                                name=selected.name,
                                disabled=reasons or "-",
                                hits=hits or "-",
                            )
                        )
                    time.sleep(self.refresh_seconds)
                    self.driver.refresh()
                    self._wait_for_challenge()
                    continue

                try:
                    before_url = self.driver.current_url
                except Exception:
                    before_url = ""
                if not self._safe_click(selected.button):
                    self._debug("click failed: selected package")
                    time.sleep(self.refresh_seconds)
                    self.driver.refresh()
                    self._wait_for_challenge()
                    continue

                time.sleep(0.6)
                if self.debug:
                    try:
                        after_url = self.driver.current_url
                    except Exception:
                        after_url = ""
                    if before_url and after_url and after_url != before_url:
                        self._debug(f"url changed: {before_url} -> {after_url}")
                self._wait_for_quantity_controls()
                time.sleep(0.6)
                quantity_ok = self._set_quantity(self.quantity)
                if self.debug and not quantity_ok:
                    self._debug("quantity: failed to set")

                if not self.auto_checkout:
                    print("Auto checkout disabled. Complete purchase manually.")
                    if self.interactive:
                        try:
                            input("Press Enter to stop the bot...")
                        except Exception:
                            pass
                    else:
                        while True:
                            time.sleep(1)
                    return True

                if self._is_checkout_url():
                    print("Checkout page detected. Complete purchase manually.")
                    if self.interactive:
                        try:
                            input("Press Enter to close browser...")
                        except Exception:
                            pass
                    else:
                        # Keep browser open in non-interactive mode
                        print("Browser will stay open. Stop the bot from the panel when done.")
                        while True:
                            time.sleep(1)
                    return True

                if self._click_checkout():
                    print("Checkout button clicked. Complete purchase manually.")
                    if self.interactive:
                        try:
                            input("Press Enter to close browser...")
                        except Exception:
                            pass
                    else:
                        # Keep browser open in non-interactive mode
                        print("Browser will stay open. Stop the bot from the panel when done.")
                        while True:
                            time.sleep(1)
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
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging")
    parser.add_argument("--no-auto-checkout", action="store_true", help="Disable auto checkout click")

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
        debug=args.debug,
        auto_checkout=not args.no_auto_checkout,
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

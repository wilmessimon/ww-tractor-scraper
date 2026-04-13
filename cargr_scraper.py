#!/usr/bin/env python3
"""
Spezialisierter Scraper für Car.gr (Griechenland).

Die Plattform ist inzwischen hinter einer Cloudflare-Challenge. Deshalb nutzt
dieser Scraper bevorzugt Firecrawl. Falls kein API-Key vorhanden ist, fällt er
auf Playwright zurück.
"""

import logging
import random
import re
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from firecrawl_client import FirecrawlClient

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - optional at import time during setup
    PlaywrightTimeoutError = Exception
    sync_playwright = None

logger = logging.getLogger(__name__)

# User-Agents für Car.gr
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


class CarGrScraper:
    """Spezialisierter Scraper für car.gr"""

    BASE_URL = "https://www.car.gr"
    SEARCH_URL = "https://www.car.gr/classifieds/tractors/?category=15420&variant=trac"

    def __init__(self):
        self.user_agent = random.choice(USER_AGENTS)
        self.firecrawl = FirecrawlClient()

    def scrape(self) -> List[Dict]:
        """Scraped alle MB-trac Inserate von car.gr."""
        listings = []

        try:
            logger.info(f"Scraping car.gr: {self.SEARCH_URL}")
            html = self._load_search_page()
            if not html:
                return listings

            soup = BeautifulSoup(html, "html.parser")

            listing_links = soup.find_all("a", href=re.compile(r"/classifieds/tractors/view/"))

            seen_urls = set()
            for link in listing_links:
                href = link.get("href", "")
                if not href or href in seen_urls:
                    continue

                full_url = urljoin(self.BASE_URL, href)
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                listing = self._parse_listing_card(link, full_url)
                if listing:
                    listings.append(listing)

            logger.info(f"Car.gr: {len(listings)} Inserate gefunden")

        except Exception as e:
            logger.error(f"Car.gr Parser-Fehler: {e}")

        return listings

    def _load_search_page(self) -> str:
        """Lädt die Suchseite bevorzugt via Firecrawl, sonst via Playwright."""
        if self.firecrawl.is_configured:
            logger.info("Car.gr: nutze Firecrawl für den Abruf")
            return self.firecrawl.fetch_html(
                url=self.SEARCH_URL,
                country_code="GR",
                wait_for=12000,
                timeout_ms=120000,
                actions=[
                    {"type": "wait", "milliseconds": 5000},
                    {"type": "scroll", "direction": "down", "amount": 1200},
                ],
                proxy="auto",
                only_main_content=False,
            )

        if sync_playwright is None:
            raise RuntimeError("Weder Firecrawl-Key noch Playwright verfügbar")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**self._launch_options())
            context = browser.new_context(
                user_agent=self.user_agent,
                locale="el-GR",
                timezone_id="Europe/Athens",
                viewport={"width": 1440, "height": 2200},
            )
            context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'languages', { get: () => ['el-GR', 'el', 'en-US', 'en'] });
                Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
                """
            )

            page = context.new_page()
            page.set_extra_http_headers(
                {
                    "Accept-Language": "el-GR,el;q=0.9,en;q=0.8,de;q=0.7",
                    "Upgrade-Insecure-Requests": "1",
                }
            )

            try:
                page.goto(self.SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
                self._wait_for_access(page)
                try:
                    page.wait_for_selector("a[href*='/classifieds/tractors/view/']", timeout=20000)
                except PlaywrightTimeoutError:
                    if self._is_challenge_page(page):
                        raise RuntimeError("Car.gr bleibt auf der Cloudflare-Sicherheitsprüfung hängen.")
                    logger.warning("Car.gr: Keine Listing-Links innerhalb des Timeouts gefunden.")

                return page.content()
            finally:
                context.close()
                browser.close()

    def _launch_options(self) -> Dict[str, object]:
        """Bevorzugt das volle Chrome-Binary, wenn es lokal vorhanden ist."""
        options: Dict[str, object] = {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        }
        chrome_path = Path("/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome")
        if chrome_path.exists():
            options["executable_path"] = str(chrome_path)
        return options

    def _wait_for_access(self, page) -> None:
        """
        Gibt Cloudflare ein Zeitfenster, die Seite freizuschalten.

        Wenn nach mehreren Versuchen weiter die Challenge-Seite steht, loggen wir
        den Zustand explizit, damit die Plattform im Monitoring nachvollziehbar
        als blockiert sichtbar bleibt.
        """
        attempts = 4
        for index in range(attempts):
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except PlaywrightTimeoutError:
                pass

            if not self._is_challenge_page(page):
                return

            logger.info("Car.gr: Cloudflare-Challenge noch aktiv, warte auf Freigabe (%s/%s)", index + 1, attempts)
            time.sleep(5)

        title = page.title()
        body_preview = page.locator("body").inner_text(timeout=5000)[:300].replace("\n", " ")
        raise RuntimeError(f"Car.gr weiterhin blockiert. title={title!r}, preview={body_preview!r}")

    def _is_challenge_page(self, page) -> bool:
        """Erkennt englische und griechische Cloudflare-/Verification-Seiten."""
        title = page.title().strip().lower()
        body_text = page.locator("body").inner_text(timeout=5000).strip().lower()
        markers = [
            "just a moment",
            "enable javascript and cookies to continue",
            "πραγματοποιείται επαλήθευση ασφαλείας",
            "μη συμβατή επέκταση προγράμματος περιήγησης ή διαμόρφωσης δικτύου",
            "challenges.cloudflare.com",
            "από την cloudflare",
            "ray id:",
        ]
        return "περιμένετε" in title or any(marker in body_text for marker in markers)

    def _parse_listing_card(self, link_element, url: str) -> Optional[Dict]:
        """Parst eine Listing-Karte"""
        try:
            container = link_element.find_parent(["article", "li"]) or link_element.parent or link_element

            img = container.find("img") or link_element.find("img")
            image_url = ""
            if img:
                image_url = img.get("src") or img.get("data-src") or img.get("srcset", "").split(" ")[0]

            heading = (
                container.find(["h1", "h2", "h3", "h4"])
                or link_element.find(["h1", "h2", "h3", "h4"])
            )
            if heading:
                title_parts = heading.get_text(strip=True).replace("\n", " ").split()
                title = " ".join(title_parts)
            elif img and img.get("alt"):
                title = img.get("alt", "")
            else:
                title = link_element.get_text(" ", strip=True)

            full_text = container.get_text(" ", strip=True)

            model_match = re.search(r"MB\s*TRAC\s*\d+", full_text, re.IGNORECASE)
            if model_match:
                model = model_match.group(0)
                if model not in title:
                    title = f"{title} {model}"

            price = None
            price_numeric = None
            price_match = re.search(r"(\d{1,3}(?:[\.,]\d{3})*)\s*€", full_text)
            if price_match:
                price = f"{price_match.group(1)} €"
                price_numeric = float(price_match.group(1).replace(".", "").replace(",", ""))

            location = None
            loc_match = re.search(r"([A-ZΑ-Ω]{2,}(?:\s+[A-ZΑ-Ω]+)*)\s*(?:Ν\.\s*[^\d]+)?\s*(\d{5})", full_text)
            if loc_match:
                location = f"{loc_match.group(1)} {loc_match.group(2)}"
            else:
                loc_match2 = re.search(r"([A-ZΑ-Ω][\wΆ-ώ.\- ]{2,})\s+\d{5}", full_text)
                if loc_match2:
                    location = loc_match2.group(0)

            year = None
            year_match = re.search(r"\b(19[7-9]\d|20[0-2]\d)\b", title)
            if year_match:
                year = year_match.group(1)

            if not re.search(r"(?:mb[- ]?trac|mercedes.*trac|trac.*mercedes)", full_text, re.IGNORECASE):
                return None

            return {
                "platform": "Car.gr",
                "country": "GR",
                "title": title.strip(),
                "price": price,
                "price_numeric": price_numeric,
                "location": location,
                "url": url,
                "image_url": image_url,
                "year": year,
                "category": "fahrzeug",
            }

        except Exception as e:
            logger.debug(f"Fehler beim Parsen eines Car.gr Inserats: {e}")
            return None


def main():
    """Test-Funktion"""
    logging.basicConfig(level=logging.INFO)
    scraper = CarGrScraper()
    listings = scraper.scrape()

    print(f"\n{'='*60}")
    print(f"Car.gr Ergebnisse: {len(listings)} Inserate")
    print('='*60)

    for listing in listings:
        print(f"\n📌 {listing['title']}")
        print(f"   💰 {listing.get('price', 'k.A.')}")
        print(f"   📍 {listing.get('location', 'k.A.')}")
        print(f"   🔗 {listing['url']}")
        if listing.get('image_url'):
            print(f"   🖼️  {listing['image_url'][:60]}...")


if __name__ == "__main__":
    main()

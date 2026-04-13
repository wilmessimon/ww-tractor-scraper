#!/usr/bin/env python3
"""
MB-trac European Scraper
========================
Täglicher Crawler für MB-trac Inserate auf europäischen Plattformen.

Features:
- Modulare Scraper-Architektur für jede Plattform
- SQLite-Datenbank für Persistenz
- Duplikaterkennung
- HTML-Dashboard für neue Inserate
- Desktop-Benachrichtigungen (optional)
"""

import os
import sys
import json
import time
import hashlib
import re
import sqlite3
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
import random

# Lokale Module
from storage import SQLiteDatabase
from firecrawl_client import FirecrawlClient
from filters import filter_listing, Category
from brands import get_matching_brand, get_brand_display_name, BRANDS
from platform_parsers import get_platform_parser_config
from mascus_scraper import MascusScraper as SpecializedMascusScraper
from cargr_scraper import CarGrScraper as SpecializedCarGrScraper
# Dashboard wird nicht mehr bei jedem Scraper-Lauf generiert
# Es lädt Daten live von GitHub Raw

# Konfiguration
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
DB_PATH = DATA_DIR / "mbtrac.db"

# Das Logging wird bereits beim Import initialisiert.
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Logging einrichten
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / f"scraper_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# User-Agent Rotation für Anti-Bot-Umgehung
USER_AGENTS = [
    # Chrome auf Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    # Chrome auf Mac
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    # Firefox auf Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    # Firefox auf Mac
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
    # Safari auf Mac
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    # Edge auf Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
]

def get_random_headers():
    """Generiert zufällige, browserähnliche Headers"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': random.choice([
            'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
            'de,en-US;q=0.9,en;q=0.8',
            'en-US,en;q=0.9,de;q=0.8',
            'nl-NL,nl;q=0.9,en;q=0.8',
            'fr-FR,fr;q=0.9,en;q=0.8',
        ]),
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }

# Standard-Headers für Kompatibilität
HEADERS = get_random_headers()


@dataclass
class Listing:
    """Datenklasse für ein Inserat"""
    id: str                     # Eindeutige ID (Hash aus URL)
    platform: str               # Name der Plattform
    country: str                # Ländercode
    title: str                  # Titel des Inserats
    price: Optional[str]        # Preis (als String, da unterschiedliche Formate)
    location: Optional[str]     # Standort
    url: str                    # Direkt-Link zum Inserat
    image_url: Optional[str]    # Vorschaubild
    description: Optional[str]  # Kurzbeschreibung
    first_seen: str             # Datum des ersten Fundes
    last_seen: str              # Datum der letzten Aktualisierung
    is_new: bool = True         # Neu seit letztem Scan?
    category: str = "sonstiges" # Kategorie: fahrzeug, ersatzteil, modell, suchgesuch, sonstiges
    price_numeric: Optional[float] = None  # Numerischer Preis
    is_negotiable: bool = False # Preis verhandelbar?
    brand: str = "mb_trac"     # Erkannte Marke (z.B. "fendt", "john_deere")

    @staticmethod
    def generate_id(url: str) -> str:
        """Generiert eine eindeutige ID aus der URL"""
        return hashlib.md5(url.encode()).hexdigest()[:16]


class Database:
    """JSON-basierte Datenbank für Inserate (SQLite-Alternative für bessere Portabilität)"""

    SAVE_INTERVAL = 25

    def __init__(self, db_path: Path):
        self.db_path = db_path.with_suffix('.json')
        self.history_path = db_path.parent / 'scan_history.json'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._dirty = False
        self._pending_writes = 0
        self._load_data()
        self._build_content_index()

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalisiert Titel für Duplikaterkennung"""
        import re
        # Lowercase, extra Whitespace entfernen
        normalized = title.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        # Sonderzeichen entfernen die variieren könnten
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return normalized

    @staticmethod
    def _generate_content_hash(title: str, price_numeric: float = None) -> str:
        """Generiert Hash aus normalisiertem Titel + Preis"""
        normalized = Database._normalize_title(title)
        # Preis auf 100er runden (kleine Preisunterschiede ignorieren)
        price_rounded = round(price_numeric / 100) * 100 if price_numeric else 0
        content = f"{normalized}|{price_rounded}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _build_content_index(self):
        """Baut Index für Content-basierte Duplikaterkennung"""
        self.content_index = {}  # content_hash -> listing_id
        for lid, listing in self.listings.items():
            content_hash = self._generate_content_hash(
                listing.get('title', ''),
                listing.get('price_numeric')
            )
            # Behalte nur den ersten (ältesten) Eintrag
            if content_hash not in self.content_index:
                self.content_index[content_hash] = lid

    def _load_data(self):
        """Lädt die Datenbank aus JSON"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    self.listings = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.listings = {}
        else:
            self.listings = {}

    def _save_data(self):
        """Speichert die Datenbank als JSON"""
        tmp_path = self.db_path.with_suffix(f"{self.db_path.suffix}.tmp")
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(self.listings, f, ensure_ascii=False, indent=2)
        tmp_path.replace(self.db_path)
        self._dirty = False
        self._pending_writes = 0

    def flush(self):
        """Schreibt ausstehende Änderungen nur dann auf Platte, wenn nötig."""
        if self._dirty:
            self._save_data()

    def _mark_dirty(self):
        """Bündelt Schreibvorgänge, ohne Änderungen zu lange nur im Speicher zu halten."""
        self._dirty = True
        self._pending_writes += 1
        if self._pending_writes >= self.SAVE_INTERVAL:
            self._save_data()

    def listing_exists(self, listing_id: str) -> bool:
        """Prüft ob ein Inserat bereits existiert"""
        return listing_id in self.listings

    def add_listing(self, listing: Listing) -> bool:
        """Fügt ein neues Inserat hinzu. Gibt True zurück wenn es neu ist."""
        # Check 1: Exakte URL bereits vorhanden?
        if listing.id in self.listings:
            # Bereits vorhanden, last_seen aktualisieren
            self.listings[listing.id]['last_seen'] = listing.last_seen
            self.listings[listing.id]['is_active'] = True
            # Bild nachtragen falls fehlend
            if not self.listings[listing.id].get('image_url') and listing.image_url:
                self.listings[listing.id]['image_url'] = listing.image_url
            self._mark_dirty()
            return False

        # Check 2: Content-Duplikat (gleicher Titel + ähnlicher Preis)?
        content_hash = self._generate_content_hash(listing.title, listing.price_numeric)
        if content_hash in self.content_index:
            existing_id = self.content_index[content_hash]
            if existing_id in self.listings:
                # Duplikat gefunden - last_seen beim Original aktualisieren
                self.listings[existing_id]['last_seen'] = listing.last_seen
                self.listings[existing_id]['is_active'] = True

                # Bild nachtragen falls beim Original fehlend
                if not self.listings[existing_id].get('image_url') and listing.image_url:
                    self.listings[existing_id]['image_url'] = listing.image_url

                # Füge alternative URL hinzu (für Referenz)
                if 'alt_urls' not in self.listings[existing_id]:
                    self.listings[existing_id]['alt_urls'] = []
                if listing.url not in self.listings[existing_id]['alt_urls']:
                    self.listings[existing_id]['alt_urls'].append(listing.url)
                self._mark_dirty()
                return False

        # Wirklich neues Inserat
        self.listings[listing.id] = {
            'id': listing.id,
            'platform': listing.platform,
            'country': listing.country,
            'title': listing.title,
            'price': listing.price,
            'location': listing.location,
            'url': listing.url,
            'image_url': listing.image_url,
            'description': listing.description,
            'first_seen': listing.first_seen,
            'last_seen': listing.last_seen,
            'is_active': True,
            'category': listing.category,
            'price_numeric': listing.price_numeric,
            'is_negotiable': listing.is_negotiable
        }
        # Content-Index aktualisieren
        self.content_index[content_hash] = listing.id
        self._mark_dirty()
        return True

    def get_new_listings(self, since: str) -> List[Dict]:
        """Holt alle neuen Inserate seit einem bestimmten Datum"""
        return sorted(
            [l for l in self.listings.values() if l.get('first_seen', '') >= since],
            key=lambda x: x.get('first_seen', ''),
            reverse=True
        )

    def get_all_active(self) -> List[Dict]:
        """Holt alle aktiven Inserate"""
        return sorted(
            [l for l in self.listings.values() if l.get('is_active', True)],
            key=lambda x: x.get('first_seen', ''),
            reverse=True
        )

    def log_scan(self, platforms: int, new_listings: int, total: int, duration: float):
        """Protokolliert einen Scan-Durchlauf"""
        history = []
        if self.history_path.exists():
            try:
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []

        history.append({
            'scan_date': datetime.now().isoformat(),
            'platforms_scanned': platforms,
            'new_listings': new_listings,
            'total_listings': total,
            'duration_seconds': duration
        })

        with open(self.history_path, 'w', encoding='utf-8') as f:
            json.dump(history[-100:], f, ensure_ascii=False, indent=2)  # Nur letzte 100 behalten

    def get_stats(self) -> Dict:
        """Holt Statistiken"""
        today = datetime.now().strftime("%Y-%m-%d")
        active_listings = [l for l in self.listings.values() if l.get('is_active', True)]

        by_country = {}
        for l in active_listings:
            country = l.get('country', 'XX')
            by_country[country] = by_country.get(country, 0) + 1

        new_today = sum(1 for l in self.listings.values()
                        if l.get('first_seen', '').startswith(today))

        return {
            "total": len(self.listings),
            "active": len(active_listings),
            "new_today": new_today,
            "by_country": by_country
        }


class BaseScraper:
    """Basis-Klasse für alle Plattform-Scraper"""

    def __init__(self, platform_config: Dict):
        self.config = platform_config
        self.name = platform_config["name"]
        self.search_url = platform_config["search_url"]
        self.search_terms = platform_config.get("search_terms", ["MB-trac"])
        self.parser_config = get_platform_parser_config(platform_config)
        self.session = requests.Session()
        self.firecrawl = FirecrawlClient()
        self.used_firecrawl = False
        self.last_error: Optional[str] = None
        for key in (
            "listing_url_patterns",
            "firecrawl_enabled",
            "firecrawl_force",
            "firecrawl_wait_for",
            "firecrawl_timeout",
            "firecrawl_actions",
            "firecrawl_proxy",
        ):
            if key in self.parser_config and key not in self.config:
                self.config[key] = self.parser_config[key]
        # Zufällige Headers für jeden Scraper
        self.session.headers.update(get_random_headers())

    def _firecrawl_enabled(self) -> bool:
        return self.firecrawl.is_configured and bool(
            self.config.get("firecrawl_force") or self.config.get("firecrawl_enabled")
        )

    def _fetch_page_via_firecrawl(self, url: str, reason: Optional[str] = None) -> Optional[BeautifulSoup]:
        if not self._firecrawl_enabled():
            return None

        try:
            html = self.firecrawl.fetch_html(
                url=url,
                country_code=self.config.get("country_code"),
                wait_for=self.config.get("firecrawl_wait_for", 8000),
                timeout_ms=self.config.get("firecrawl_timeout", 120000),
                actions=self.config.get("firecrawl_actions"),
                proxy=self.config.get("firecrawl_proxy", "auto"),
                only_main_content=False,
            )
            if not html:
                raise RuntimeError("Firecrawl hat leeres HTML geliefert")

            self.used_firecrawl = True
            self.last_error = None
            if reason:
                logger.info(f"{self.name}: Firecrawl-Fallback erfolgreich nach {reason}")
            else:
                logger.info(f"{self.name}: Firecrawl-Fetch erfolgreich")
            return BeautifulSoup(html, "html.parser")
        except Exception as e:
            self.last_error = f"Firecrawl failed: {e}"
            logger.error(f"{self.name}: Firecrawl-Fetch fehlgeschlagen: {e}")
            return None

    def fetch_page(self, url: str, params: Dict = None, max_retries: int = 2) -> Optional[BeautifulSoup]:
        """
        Lädt eine Seite mit Retry-Logik und Anti-Bot-Maßnahmen.

        Args:
            url: Die zu ladende URL
            params: Query-Parameter
            max_retries: Maximale Anzahl Versuche (default: 2)
        """
        self.last_error = None
        self.used_firecrawl = False

        if self.config.get("firecrawl_force"):
            soup = self._fetch_page_via_firecrawl(url, reason="forced mode")
            if soup:
                return soup

        for attempt in range(max_retries + 1):
            try:
                # Zufällige Pause vor dem Request (0.5-2 Sekunden)
                if attempt > 0:
                    delay = random.uniform(1.0, 3.0)
                    time.sleep(delay)
                    # Neue Headers bei Retry
                    self.session.headers.update(get_random_headers())

                response = self.session.get(url, params=params, timeout=30)

                # Bei 403/429 Fehler: Retry mit anderen Headers
                if response.status_code in [403, 405, 406, 429]:
                    soup = self._fetch_page_via_firecrawl(url, reason=f"HTTP {response.status_code}")
                    if soup:
                        return soup
                    if attempt < max_retries:
                        logger.debug(f"{self.name}: Status {response.status_code}, Retry {attempt + 1}...")
                        continue
                    else:
                        response.raise_for_status()

                response.raise_for_status()
                return BeautifulSoup(response.text, 'html.parser')

            except requests.RequestException as e:
                if attempt == max_retries:
                    soup = self._fetch_page_via_firecrawl(url, reason=str(e))
                    if soup:
                        return soup
                    self.last_error = str(e)
                    logger.error(f"Fehler beim Laden von {url}: {e}")
                    return None

        return None

    def scrape(self) -> List[Listing]:
        """Hauptmethode zum Scrapen - muss überschrieben werden"""
        raise NotImplementedError("Subklassen müssen scrape() implementieren")

    def parse_listing(self, element) -> Optional[Listing]:
        """Parst ein einzelnes Listing-Element - muss überschrieben werden"""
        raise NotImplementedError("Subklassen müssen parse_listing() implementieren")


class GenericScraper(BaseScraper):
    """
    Generischer Scraper für die meisten Plattformen.
    Versucht intelligente Extraktion basierend auf gängigen HTML-Strukturen.
    """

    def scrape(self) -> List[Listing]:
        soup = self.fetch_page(self.search_url)
        if not soup:
            return []

        listings = self._extract_from_items(soup)
        if not listings and self.parser_config.get("json_ld_enabled", True):
            listings = self._extract_from_json_ld(soup)
        if not listings and self.parser_config.get("link_fallback_enabled", True):
            listings = self._extract_from_links(soup)

        listings = self._dedupe_listings(listings)
        logger.info(f"{self.name}: {len(listings)} Inserate gefunden")
        return listings

    def _dedupe_listings(self, listings: List[Listing]) -> List[Listing]:
        deduped: List[Listing] = []
        seen = set()
        for listing in listings:
            if listing.id in seen:
                continue
            seen.add(listing.id)
            deduped.append(listing)
        return deduped

    def _select_items(self, soup: BeautifulSoup):
        selectors = self.parser_config.get("item_selectors") or [
            'article',
            '[class*="listing"]',
            '[class*="item"]',
            '[class*="ad-"]',
            '[class*="result"]',
            '[class*="product"]',
            '[class*="offer"]',
            '.classified',
            '.advertisement',
            '.search-result',
        ]
        best_items = []
        minimum = int(self.parser_config.get("item_min_count", 1))

        for selector in selectors:
            try:
                items = soup.select(selector)
            except Exception:
                continue
            if len(items) > len(best_items):
                best_items = items
            if len(items) >= minimum:
                return items

        return best_items

    def _extract_from_items(self, soup: BeautifulSoup) -> List[Listing]:
        listings: List[Listing] = []
        items = self._select_items(soup)

        for item in items[: self.parser_config.get("max_items", 50)]:
            try:
                listing = self._extract_listing(item)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.debug(f"Fehler beim Parsen eines Items auf {self.name}: {e}")

        return listings

    @staticmethod
    def _normalize_whitespace(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        cleaned = re.sub(r'[\u00a0\u2007\u202f]+', ' ', value)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned or None

    def _extract_value_from_elements(
        self,
        root,
        selectors: List[str],
        *,
        attributes: Optional[List[str]] = None,
        max_length: int = 250,
    ) -> Optional[str]:
        for selector in selectors:
            try:
                elements = [root] if selector == "self" else root.select(selector)
            except Exception:
                continue

            for elem in elements[:5]:
                if attributes:
                    for attr in attributes:
                        value = elem.get(attr) if hasattr(elem, "get") else None
                        if isinstance(value, list):
                            value = " ".join(str(v) for v in value if v)
                        value = self._normalize_whitespace(value)
                        if value:
                            return value[:max_length]

                text = self._normalize_whitespace(elem.get_text(" ", strip=True))
                if text:
                    return text[:max_length]

        return None

    def _resolve_url(self, href: str) -> str:
        return href if href.startswith("http") else urljoin(self.search_url, href)

    def _find_best_link(self, item):
        patterns = self.config.get("listing_url_patterns", [])
        selectors = self.parser_config.get("link_selectors") or ['a[href]']
        candidates = []

        for selector in selectors:
            try:
                candidates.extend(item.select(selector))
            except Exception:
                continue

        for candidate in candidates:
            href = candidate.get("href", "")
            if not href:
                continue
            if patterns and not any(pattern in href for pattern in patterns):
                continue
            return candidate

        for candidate in candidates:
            href = candidate.get("href", "")
            if href:
                return candidate

        return None

    def _clean_title(self, title: Optional[str]) -> Optional[str]:
        title = self._normalize_whitespace(title)
        if not title:
            return None

        title = re.split(
            r"\s+(?:\d[\d\s.,]*\s?(?:€|eur|chf|fr\.|kr|pln)|sofort kaufen|mon,|mo,|di,|mi,|do,|fr,|sa,|so,)\b",
            title,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()
        return title[:250] if title else None

    def _extract_price_from_text(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return None

        patterns = [
            r"(?<![:/\d])(\d{1,3}(?:[\s'.]\d{3})*(?:[.,]\d{2})?\.-)",
            r"(?<![:/\d])(\d{1,3}(?:[\s'.]\d{3})*(?:[.,]\d{2})?)\s*(?=(?:\(\d+\s*gebote\)|sofort kaufen|oder preis vorschlagen|heute|morgen|mo,|di,|mi,|do,|fr,|sa,|so,))",
            r"Prix:\s*(\d{1,3}(?:[\s'.]\d{3})*(?:[.,]\d{2})?)\s?(€|eur|chf|fr\.|kr|pln)",
            r"(?<![:/\d])(\d{1,3}(?:[\s'.]\d{3})*(?:[.,]\d{2})?)\s?(?:€|eur|chf|fr\.|kr|pln)",
            r"(?:kr\.?\s*)(\d{1,3}(?:[\s'.]\d{3})*(?:[.,]\d{2})?)",
            r"(?<![:/\d])(\d{1,3}(?:[\s'.]\d{3})*(?:[.,]\d{2})?)\s?(?:lei|ron)",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if not matches:
                continue

            match = matches[-1]
            if isinstance(match, tuple):
                if len(match) >= 2 and any(str(part).lower() in {"€", "eur", "chf", "fr.", "kr", "pln"} for part in match[1:]):
                    value = " ".join(str(part) for part in match if part).strip()
                else:
                    value = next((str(part) for part in reversed(match) if part), "")
            else:
                value = str(match)

            value = self._normalize_whitespace(value)
            if value:
                return value
        return None

    def _extract_location_from_text(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        if self.name == "Leboncoin":
            match = re.search(r"Située à\s+([^\.]+)", text, re.IGNORECASE)
            if match:
                return self._normalize_whitespace(match.group(1))
        return None

    def _extract_image(self, item) -> Optional[str]:
        selectors = self.parser_config.get("image_selectors") or ['img[src]', 'img[data-src]']
        for selector in selectors:
            try:
                images = item.select(selector)
            except Exception:
                continue

            for img in images[:3]:
                for attr in ("src", "data-src", "data-original", "srcset"):
                    value = img.get(attr)
                    if not value:
                        continue
                    if attr == "srcset":
                        value = value.split(",")[0].strip().split(" ")[0]
                    return value
        return None

    def _build_listing(
        self,
        *,
        url: str,
        title: Optional[str],
        price: Optional[str],
        location: Optional[str],
        image: Optional[str],
        description: Optional[str] = None,
    ) -> Optional[Listing]:
        title = self._clean_title(title)
        if not title or len(title) < 3:
            return None

        required_terms = self.parser_config.get("required_terms_any") or []
        if required_terms:
            haystack = " ".join(filter(None, [title, description]))
            haystack_normalized = self._normalize_whitespace(haystack.lower()) or ""
            if not any(term.lower() in haystack_normalized for term in required_terms):
                return None

        matched_brand = get_matching_brand(title)
        description = self._normalize_whitespace(description)
        if not matched_brand and description:
            matched_brand = get_matching_brand(description)
        if not matched_brand:
            return None

        filter_result = filter_listing(title, price)
        if not filter_result.is_valid:
            logger.debug(f"Gefiltert: {title[:50]}... - {filter_result.reason}")
            return None

        now = datetime.now().isoformat()
        return Listing(
            id=Listing.generate_id(url),
            platform=self.name,
            country=self.config.get('country_code', 'XX'),
            title=title,
            price=price,
            location=location,
            url=url,
            image_url=image,
            description=description,
            first_seen=now,
            last_seen=now,
            category=filter_result.category.value,
            price_numeric=filter_result.price_numeric,
            is_negotiable=filter_result.is_negotiable,
            brand=filter_result.brand or matched_brand or "mb_trac",
        )

    def _extract_listing(self, item) -> Optional[Listing]:
        """Extrahiert ein Inserat aus einem konfigurierten HTML-Container."""
        link = self._find_best_link(item)
        if not link:
            return None

        url = self._resolve_url(link.get('href', ''))
        title = (
            self._extract_value_from_elements(item, self.parser_config.get("title_selectors") or ['h2', 'h3', 'a'])
            or self._extract_value_from_elements(link, ["self"], attributes=["title", "aria-label"], max_length=250)
        )
        price = self._extract_value_from_elements(
            item,
            self.parser_config.get("price_selectors") or ['[class*="price"]', '.price'],
            max_length=80,
        )
        full_text = self._normalize_whitespace(item.get_text(" ", strip=True))
        if not price:
            price = self._extract_price_from_text(full_text)

        location = self._extract_value_from_elements(
            item,
            self.parser_config.get("location_selectors") or ['[class*="location"]', '[class*="city"]'],
            max_length=120,
        )
        if not location:
            location = self._extract_location_from_text(full_text)

        image = self._extract_image(item)
        description = self._extract_value_from_elements(
            item,
            self.parser_config.get("description_selectors") or ['[class*="description"]'],
            max_length=500,
        )

        return self._build_listing(
            url=url,
            title=title,
            price=price,
            location=location,
            image=image,
            description=description or full_text,
        )

    def _extract_from_links(self, soup: BeautifulSoup) -> List[Listing]:
        """Fallback für JS-lastige Plattformen: extrahiert direkt aus Detail-Links."""
        listings: List[Listing] = []
        seen_urls = set()
        patterns = self.config.get("listing_url_patterns", [])
        if not patterns:
            return listings

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if not href or not any(pattern in href for pattern in patterns):
                continue
            link_text = self._normalize_whitespace(link.get_text(" ", strip=True))
            if link_text and re.fullmatch(r"\d+", link_text) and not (link.get("title") or link.get("aria-label")):
                continue

            url = href if href.startswith("http") else urljoin(self.search_url, href)
            if url in seen_urls:
                continue
            seen_urls.add(url)

            try:
                listing = self._extract_listing_from_link(link, url)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.debug(f"Fehler beim Link-Fallback auf {self.name}: {e}")

            if len(listings) >= 50:
                break

        return listings

    def _extract_listing_from_link(self, link, url: str) -> Optional[Listing]:
        """Parst ein Listing aus einem einzelnen Detail-Link."""
        if self.parser_config.get("link_container_mode") == "link":
            container = link
        else:
            container = link.find_parent(self.parser_config.get("container_tags") or ["article", "li", "div"]) or link
        heading = container.find(["h1", "h2", "h3", "h4"])
        img = container.find("img")
        image = self._extract_image(container)
        full_text = container.get_text(" ", strip=True)

        hidden_title = None
        if self.name == "Leboncoin":
            hidden_title_elem = link.find("span", title=True)
            if hidden_title_elem:
                hidden_title = hidden_title_elem.get("title", "")
                hidden_title = re.sub(r"^Voir l[’']annonce:\s*", "", hidden_title, flags=re.IGNORECASE).strip()

        aria_label = link.get("aria-label")
        if aria_label and aria_label.strip().lower() in {
            "voir l’annonce",
            "voir l'annonce",
            "anzeige ansehen",
            "view ad",
            "open ad",
        }:
            aria_label = None

        link_text = link.get_text(" ", strip=True)
        title_candidates = []
        if self.parser_config.get("prefer_anchor_text"):
            title_candidates.extend([
                link_text,
                link.get("title"),
                aria_label,
                hidden_title,
                heading.get_text(" ", strip=True) if heading else None,
                img.get("alt") if img and img.get("alt") else None,
                full_text,
            ])
        else:
            title_candidates.extend([
                heading.get_text(" ", strip=True) if heading else None,
                img.get("alt") if img and img.get("alt") else None,
                hidden_title,
                aria_label,
                link.get("title"),
                link_text,
                full_text,
            ])
        title = next((candidate for candidate in title_candidates if candidate), None)
        title = self._clean_title(title)
        if not title:
            return None

        price = None
        price_selectors = self.parser_config.get("price_selectors") or ["[class*='price']", "[class*='amount']", "[class*='cost']", ".price"]
        for selector in price_selectors:
            elem = container.select_one(selector)
            if elem and elem.get_text(strip=True):
                price = elem.get_text(" ", strip=True)[:80]
                break

        if not price:
            price_source_text = " ".join(filter(None, [link_text, full_text]))
            if self.name == "Leboncoin":
                price_match = re.search(r"Prix:\s*(\d[\d\s'.,]*)\s?(€|eur|chf|fr\.|kr)", price_source_text, re.IGNORECASE)
                if price_match:
                    price = f"{price_match.group(1).strip()} {price_match.group(2)}".strip()
            if not price:
                price = self._extract_price_from_text(price_source_text)

        location = None
        loc_selectors = self.parser_config.get("location_selectors") or ["[class*='location']", "[class*='city']", "[class*='region']", "[class*='postal']"]
        for selector in loc_selectors:
            elem = container.select_one(selector)
            if elem and elem.get_text(strip=True):
                location = elem.get_text(" ", strip=True)[:100]
                break

        if not location:
            location = self._extract_location_from_text(full_text)

        return self._build_listing(
            url=url,
            title=title,
            price=price,
            location=location,
            image=image,
            description=full_text,
        )

    def _iter_json_candidates(self, node):
        if isinstance(node, list):
            for item in node:
                yield from self._iter_json_candidates(item)
            return

        if not isinstance(node, dict):
            return

        if isinstance(node.get("itemListElement"), list):
            yield from self._iter_json_candidates(node["itemListElement"])

        if isinstance(node.get("item"), dict):
            yield from self._iter_json_candidates(node["item"])

        if isinstance(node.get("mainEntity"), dict):
            yield from self._iter_json_candidates(node["mainEntity"])

        if any(key in node for key in ("name", "headline", "title")) and any(key in node for key in ("url", "@id", "offers", "image")):
            yield node

        for value in node.values():
            if isinstance(value, (dict, list)):
                yield from self._iter_json_candidates(value)

    def _extract_from_json_ld(self, soup: BeautifulSoup) -> List[Listing]:
        listings: List[Listing] = []
        for script in soup.find_all("script", attrs={"type": lambda v: v and "ld+json" in v}):
            raw = script.string or script.get_text(strip=True)
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue

            for candidate in self._iter_json_candidates(data):
                title = candidate.get("name") or candidate.get("headline") or candidate.get("title")
                url = candidate.get("url") or candidate.get("@id")
                if isinstance(url, dict):
                    url = url.get("@id") or url.get("url")
                if not title or not url or not str(url).startswith(("http", "/")):
                    continue

                price = candidate.get("price")
                offers = candidate.get("offers")
                if isinstance(offers, dict):
                    price = price or offers.get("price") or offers.get("lowPrice")
                    currency = offers.get("priceCurrency")
                    if price and currency:
                        price = f"{price} {currency}"

                image = candidate.get("image")
                if isinstance(image, list):
                    image = image[0] if image else None
                if isinstance(image, dict):
                    image = image.get("url") or image.get("contentUrl")

                description = candidate.get("description")
                location = None
                area = candidate.get("areaServed")
                if isinstance(area, dict):
                    location = area.get("name")
                address = candidate.get("address")
                if isinstance(address, dict):
                    location = address.get("addressLocality") or address.get("addressRegion") or location

                listing = self._build_listing(
                    url=self._resolve_url(str(url)),
                    title=str(title),
                    price=str(price) if price else None,
                    location=location,
                    image=str(image) if image else None,
                    description=description,
                )
                if listing:
                    listings.append(listing)
        return listings


# Spezialisierte Scraper für wichtige Plattformen

class MascusScraper(BaseScraper):
    """Spezialisierter Scraper für Mascus-Plattformen - nutzt den optimierten mascus_scraper.py"""

    def __init__(self, platform_config: Dict):
        super().__init__(platform_config)
        # Extrahiere Domain aus der Such-URL
        parsed = urlparse(self.search_url)
        self.domain = parsed.netloc.replace('www.', '')
        # Nutze den spezialisierten Mascus-Scraper
        self._specialized = SpecializedMascusScraper(filter_lkw=True)

    def scrape(self) -> List[Listing]:
        """Scrapt Mascus mit dem optimierten HTML-Parser"""
        listings = []
        now = datetime.now().isoformat()

        try:
            # Nutze den spezialisierten Scraper
            mascus_listings = self._specialized.scrape_domain(self.domain, 'mb trac')

            for ml in mascus_listings:
                # Filter anwenden
                filter_result = filter_listing(ml.title, ml.price)
                if not filter_result.is_valid:
                    continue

                # MascusListing -> Listing konvertieren
                listing = Listing(
                    id=Listing.generate_id(ml.url),
                    platform=self.name,
                    country=ml.country,
                    title=ml.title,
                    price=ml.price,
                    location=ml.location,
                    url=ml.url,
                    image_url=ml.image_url,
                    description=None,
                    first_seen=now,
                    last_seen=now,
                    category=filter_result.category.value,
                    price_numeric=ml.price_numeric or filter_result.price_numeric,
                    is_negotiable=filter_result.is_negotiable,
                    brand=filter_result.brand or "mb_trac"
                )
                listings.append(listing)

            logger.info(f"{self.name}: {len(listings)} Inserate gefunden")

        except Exception as e:
            logger.error(f"Mascus scraping error for {self.domain}: {e}")

        return listings


class CarGrScraperIntegrated(BaseScraper):
    """Spezialisierter Scraper für Car.gr (Griechenland)"""

    def __init__(self, platform_config: Dict):
        super().__init__(platform_config)
        self._specialized = SpecializedCarGrScraper()

    def scrape(self) -> List[Listing]:
        """Scrapt Car.gr mit dem spezialisierten Parser"""
        listings = []
        now = datetime.now().isoformat()

        try:
            cargr_listings = self._specialized.scrape()

            for cl in cargr_listings:
                # Filter anwenden
                filter_result = filter_listing(cl.get('title', ''), cl.get('price'))
                if not filter_result.is_valid:
                    continue

                listing = Listing(
                    id=Listing.generate_id(cl['url']),
                    platform=self.name,
                    country='GR',
                    title=cl.get('title', ''),
                    price=cl.get('price'),
                    location=cl.get('location'),
                    url=cl['url'],
                    image_url=cl.get('image_url'),
                    description=None,
                    first_seen=now,
                    last_seen=now,
                    category=cl.get('category', filter_result.category.value),
                    price_numeric=cl.get('price_numeric') or filter_result.price_numeric,
                    is_negotiable=filter_result.is_negotiable,
                    brand=filter_result.brand or "mb_trac"
                )
                listings.append(listing)

            logger.info(f"{self.name}: {len(listings)} Inserate gefunden")

        except Exception as e:
            logger.error(f"Car.gr scraping error: {e}")

        return listings


class TraktorpoolScraper(BaseScraper):
    """Spezialisierter Scraper für Traktorpool"""

    def scrape(self) -> List[Listing]:
        listings = []
        soup = self.fetch_page(self.search_url)

        if not soup:
            return listings

        items = soup.select('.machine-card, .result-item, article')

        for item in items[:50]:
            try:
                listing = self._parse_item(item)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.debug(f"Traktorpool parsing error: {e}")

        logger.info(f"{self.name}: {len(listings)} Inserate gefunden")
        return listings

    def _parse_item(self, item) -> Optional[Listing]:
        now = datetime.now().isoformat()

        link = item.find('a', href=True)
        if not link:
            return None

        url = link.get('href', '')
        if not url.startswith('http'):
            url = urljoin(self.search_url, url)

        title_elem = item.select_one('h3, h2, .machine-title, [class*="title"]')
        title = title_elem.get_text(strip=True) if title_elem else None

        if not title:
            return None

        price_elem = item.select_one('[class*="price"], .machine-price')
        price = price_elem.get_text(strip=True) if price_elem else None

        # Filter anwenden
        filter_result = filter_listing(title, price)
        if not filter_result.is_valid:
            return None

        img = item.find('img')
        image = img.get('src') or img.get('data-src') if img else None

        return Listing(
            id=Listing.generate_id(url),
            platform=self.name,
            country=self.config.get('country_code', 'XX'),
            title=title,
            price=price,
            location=None,
            url=url,
            image_url=image,
            description=None,
            first_seen=now,
            last_seen=now,
            category=filter_result.category.value,
            price_numeric=filter_result.price_numeric,
            is_negotiable=filter_result.is_negotiable,
            brand=filter_result.brand or "mb_trac"
        )


class FinnNoScraper(BaseScraper):
    """Spezialisierter Scraper für Finn.no (Norwegen)"""

    def scrape(self) -> List[Listing]:
        listings = []
        soup = self.fetch_page(self.search_url)

        if not soup:
            return listings

        # Finn.no verwendet article-Tags für Listings
        items = soup.select('article, [class*="ads__unit"], [class*="result-item"]')

        for item in items[:50]:
            try:
                listing = self._parse_finn_item(item)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.debug(f"Finn.no parsing error: {e}")

        logger.info(f"{self.name}: {len(listings)} Inserate gefunden")
        return listings

    def _parse_finn_item(self, item) -> Optional[Listing]:
        now = datetime.now().isoformat()

        link = item.find('a', href=True)
        if not link:
            return None

        url = link.get('href', '')
        if not url.startswith('http'):
            url = urljoin('https://www.finn.no', url)

        # Titel
        title_elem = item.select_one('h2, h3, [class*="title"], [class*="heading"]')
        title = title_elem.get_text(strip=True) if title_elem else None

        if not title:
            return None

        # Preis - Finn.no spezifische Selektoren
        price = None
        price_selectors = [
            '[class*="price"]',
            '[class*="amount"]',
            '[class*="cost"]',
            'span[class*="kr"]',
        ]
        for sel in price_selectors:
            elem = item.select_one(sel)
            if elem:
                price_text = elem.get_text(strip=True)
                if price_text and any(c.isdigit() for c in price_text):
                    price = price_text
                    break

        # Wenn kein Preis gefunden, versuche im Text zu suchen
        if not price:
            text = item.get_text()
            # Norwegisches Preisformat: "15 000 kr" oder "kr 15.000"
            import re
            price_match = re.search(r'(\d[\d\s.,]*)\s*kr|kr\s*(\d[\d\s.,]*)', text, re.IGNORECASE)
            if price_match:
                price = price_match.group(0)

        # Filter anwenden
        filter_result = filter_listing(title, price)
        if not filter_result.is_valid:
            return None

        # Bild
        img = item.find('img')
        image = img.get('src') or img.get('data-src') if img else None

        # Location
        location = None
        loc_elem = item.select_one('[class*="location"], [class*="area"]')
        if loc_elem:
            location = loc_elem.get_text(strip=True)

        return Listing(
            id=Listing.generate_id(url),
            platform=self.name,
            country=self.config.get('country_code', 'NO'),
            title=title,
            price=price,
            location=location,
            url=url,
            image_url=image,
            description=None,
            first_seen=now,
            last_seen=now,
            category=filter_result.category.value,
            price_numeric=filter_result.price_numeric,
            is_negotiable=filter_result.is_negotiable,
            brand=filter_result.brand or "mb_trac"
        )


class DBADkScraper(BaseScraper):
    """Spezialisierter Scraper für DBA.dk (Dänemark)"""

    def scrape(self) -> List[Listing]:
        listings = []
        soup = self.fetch_page(self.search_url)

        if not soup:
            return listings

        items = soup.select('article, [class*="listing"], [class*="result"]')

        for item in items[:50]:
            try:
                listing = self._parse_dba_item(item)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.debug(f"DBA.dk parsing error: {e}")

        logger.info(f"{self.name}: {len(listings)} Inserate gefunden")
        return listings

    def _parse_dba_item(self, item) -> Optional[Listing]:
        now = datetime.now().isoformat()

        link = item.find('a', href=True)
        if not link:
            return None

        url = link.get('href', '')
        if not url.startswith('http'):
            url = urljoin('https://www.dba.dk', url)

        # Titel
        title_elem = item.select_one('h2, h3, [class*="title"]')
        title = title_elem.get_text(strip=True) if title_elem else None

        if not title:
            return None

        # Preis - DBA.dk spezifische Selektoren
        price = None
        price_selectors = [
            '[class*="price"]',
            '[class*="amount"]',
            'span[class*="kr"]',
        ]
        for sel in price_selectors:
            elem = item.select_one(sel)
            if elem:
                price_text = elem.get_text(strip=True)
                if price_text and any(c.isdigit() for c in price_text):
                    price = price_text
                    break

        # Wenn kein Preis gefunden, versuche im Text zu suchen
        if not price:
            text = item.get_text()
            import re
            # Dänisches Format: "15.000 kr" oder "kr. 15000"
            price_match = re.search(r'(\d[\d\s.,]*)\s*kr|kr\.?\s*(\d[\d\s.,]*)', text, re.IGNORECASE)
            if price_match:
                price = price_match.group(0)

        # Filter anwenden
        filter_result = filter_listing(title, price)
        if not filter_result.is_valid:
            return None

        # Bild
        img = item.find('img')
        image = img.get('src') or img.get('data-src') if img else None

        # Location
        location = None
        loc_elem = item.select_one('[class*="location"], [class*="area"]')
        if loc_elem:
            location = loc_elem.get_text(strip=True)

        return Listing(
            id=Listing.generate_id(url),
            platform=self.name,
            country=self.config.get('country_code', 'DK'),
            title=title,
            price=price,
            location=location,
            url=url,
            image_url=image,
            description=None,
            first_seen=now,
            last_seen=now,
            category=filter_result.category.value,
            price_numeric=filter_result.price_numeric,
            is_negotiable=filter_result.is_negotiable,
            brand=filter_result.brand or "mb_trac"
        )


class SubitoScraper(BaseScraper):
    """
    Spezialisierter Scraper für Subito.it (Italien).
    Subito ist eine Next.js-App — die Listing-Daten stecken im
    __NEXT_DATA__ JSON statt im regulären HTML.
    """

    def fetch_page(self, url: str, params: Dict = None, max_retries: int = 2) -> Optional[BeautifulSoup]:
        """
        Überschriebene fetch_page für Subito.it.
        Subito liefert Brotli-komprimierte Responses, die requests ohne
        das brotli-Paket nicht dekodieren kann. Wir fordern explizit nur
        gzip/deflate an und setzen Subito-spezifische Headers.
        """
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    delay = random.uniform(1.0, 3.0)
                    time.sleep(delay)

                headers = get_random_headers()
                # Kein Brotli akzeptieren - nur gzip/deflate
                headers['Accept-Encoding'] = 'gzip, deflate'
                headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                headers['Accept-Language'] = 'it-IT,it;q=0.9,en;q=0.8'
                self.session.headers.update(headers)

                response = self.session.get(url, params=params, timeout=30)

                if response.status_code in [403, 429]:
                    if attempt < max_retries:
                        logger.debug(f"{self.name}: Status {response.status_code}, Retry {attempt + 1}...")
                        continue
                    else:
                        response.raise_for_status()

                response.raise_for_status()

                # Sicherstellen dass der Content als Text dekodiert wird
                response.encoding = response.apparent_encoding or 'utf-8'
                return BeautifulSoup(response.text, 'html.parser')

            except requests.RequestException as e:
                if attempt == max_retries:
                    logger.error(f"Fehler beim Laden von {url}: {e}")
                    return None

        return None

    def scrape(self) -> List[Listing]:
        listings = []
        soup = self.fetch_page(self.search_url)

        if not soup:
            return listings

        now = datetime.now().isoformat()

        # Methode 1: __NEXT_DATA__ JSON extrahieren (primär)
        next_data_listings = self._extract_from_next_data(soup, now)
        listings.extend(next_data_listings)

        # Methode 2: Fallback auf article-Elemente (falls vorhanden)
        if not listings:
            article_listings = self._extract_from_articles(soup, now)
            listings.extend(article_listings)

        logger.info(f"{self.name}: {len(listings)} Inserate gefunden")
        return listings

    def _extract_from_next_data(self, soup, now: str) -> List[Listing]:
        """Extrahiert Listings aus dem __NEXT_DATA__ Script-Tag"""
        listings = []

        script = soup.find('script', id='__NEXT_DATA__')
        if not script or not script.string:
            logger.debug(f"{self.name}: Kein __NEXT_DATA__ gefunden")
            return listings

        try:
            data = json.loads(script.string)
        except json.JSONDecodeError:
            logger.debug(f"{self.name}: __NEXT_DATA__ JSON ungültig")
            return listings

        # Navigiere zur Listing-Liste
        items = (data.get('props', {})
                     .get('pageProps', {})
                     .get('initialState', {})
                     .get('items', {}))

        item_list = items.get('list', [])
        if not item_list:
            # Fallback: items könnte direkt eine Liste sein
            if isinstance(items, list):
                item_list = items
            else:
                logger.debug(f"{self.name}: Keine Items in __NEXT_DATA__")
                return listings

        for entry in item_list:
            try:
                item = entry.get('item', entry)  # Manchmal direkt, manchmal verschachtelt
                listing = self._parse_next_data_item(item, now)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.debug(f"{self.name}: Fehler beim Parsen eines Next.js Items: {e}")

        return listings

    def _parse_next_data_item(self, item: dict, now: str) -> Optional[Listing]:
        """Parst ein einzelnes Item aus dem __NEXT_DATA__ JSON"""
        # Titel (subject)
        title = item.get('subject', '')
        if not title or len(title) < 3:
            return None

        # Brand+Modell prüfen (Titel + Body kombiniert für besseres Matching)
        body = item.get('body', '')
        # Primär den Titel checken
        matched_brand = get_matching_brand(title)
        # Falls Titel nicht matcht, auch den Body checken
        if not matched_brand and body:
            matched_brand = get_matching_brand(body)

        if not matched_brand:
            return None

        # URL aus URN bauen
        urn = item.get('urn', '')
        # URN Format: "id:ad:uuid:list:ADID"
        ad_id = urn.split(':')[-1] if urn else ''
        # Kategorie-URL-Teil
        category_info = item.get('category', {})
        friendly_name = category_info.get('friendlyName', 'annunci')
        # Slug aus dem Titel bauen
        import re as _re
        slug = _re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        # Geo-Info für URL
        geo = item.get('geo', {})
        city = geo.get('city', {}).get('friendlyName', '') if isinstance(geo.get('city'), dict) else ''
        town = geo.get('town', {}).get('friendlyName', '') if isinstance(geo.get('town'), dict) else ''
        location_slug = town or city or ''

        if ad_id:
            url = f"https://www.subito.it/{friendly_name}/{slug}-{location_slug}-{ad_id}.htm"
        else:
            # Fallback: URLs direkt aus dem Item
            urls = item.get('urls', {})
            url = urls.get('default', urls.get('mobile', ''))
            if not url:
                return None

        # Preis
        price_str = None
        price_numeric = None
        features = item.get('features', {})
        price_feature = features.get('/price', {})
        price_values = price_feature.get('values', [])
        if price_values:
            price_str = price_values[0].get('value', '')
            try:
                price_numeric = float(price_values[0].get('key', '0'))
            except (ValueError, TypeError):
                pass

        # Filter anwenden
        filter_result = filter_listing(title, price_str)
        if not filter_result.is_valid:
            logger.debug(f"Gefiltert: {title[:50]}... - {filter_result.reason}")
            return None

        # Bild
        image_url = None
        images = item.get('images', [])
        if images:
            cdn_url = images[0].get('cdnBaseUrl', '')
            if cdn_url:
                image_url = f"{cdn_url}?rule=gallery-small"

        # Ort
        location = None
        if geo:
            city_name = geo.get('city', {}).get('value', '') if isinstance(geo.get('city'), dict) else ''
            region_name = geo.get('region', {}).get('value', '') if isinstance(geo.get('region'), dict) else ''
            location = f"{city_name}, {region_name}".strip(', ') if city_name or region_name else None

        return Listing(
            id=Listing.generate_id(url),
            platform=self.name,
            country=self.config.get('country_code', 'IT'),
            title=title,
            price=price_str,
            location=location,
            url=url,
            image_url=image_url,
            description=body[:500] if body else None,
            first_seen=now,
            last_seen=now,
            category=filter_result.category.value,
            price_numeric=price_numeric or filter_result.price_numeric,
            is_negotiable=filter_result.is_negotiable,
            brand=filter_result.brand or matched_brand or "mb_trac"
        )

    def _extract_from_articles(self, soup, now: str) -> List[Listing]:
        """Fallback: Extrahiert Listings aus article-HTML-Elementen"""
        listings = []
        articles = soup.select('article')

        for article in articles[:50]:
            try:
                # Titel
                title_elem = article.select_one('h2, h3, [class*="title"]')
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)

                matched_brand = get_matching_brand(title)
                if not matched_brand:
                    continue

                # URL
                link = article.find('a', href=True)
                if not link:
                    continue
                url = link.get('href', '')
                if not url.startswith('http'):
                    url = f"https://www.subito.it{url}"

                # Preis
                price_elem = article.select_one('[class*="price"]')
                price_str = price_elem.get_text(strip=True) if price_elem else None

                filter_result = filter_listing(title, price_str)
                if not filter_result.is_valid:
                    continue

                # Bild
                img = article.find('img', src=True)
                image_url = img.get('src') or img.get('data-src') if img else None

                listings.append(Listing(
                    id=Listing.generate_id(url),
                    platform=self.name,
                    country=self.config.get('country_code', 'IT'),
                    title=title,
                    price=price_str,
                    location=None,
                    url=url,
                    image_url=image_url,
                    description=None,
                    first_seen=now,
                    last_seen=now,
                    category=filter_result.category.value,
                    price_numeric=filter_result.price_numeric,
                    is_negotiable=filter_result.is_negotiable,
                    brand=filter_result.brand or matched_brand or "mb_trac"
                ))
            except Exception as e:
                logger.debug(f"{self.name}: Fehler beim Parsen eines article-Elements: {e}")

        return listings


class MBTracScraper:
    """Hauptklasse zum Orchestrieren aller Scraper"""

    def __init__(self, db: Database):
        self.db = db
        # Importiere Plattformen
        from platforms import PLATFORMS
        self.platforms = PLATFORMS

    def get_scraper_for_platform(self, platform_config: Dict, country_code: str) -> BaseScraper:
        """Wählt den passenden Scraper für eine Plattform"""
        config = {**platform_config, 'country_code': country_code}
        name_lower = platform_config['name'].lower()

        # Spezialisierte Scraper zuweisen
        if 'mascus' in name_lower:
            return MascusScraper(config)
        elif 'car.gr' in name_lower:
            return CarGrScraperIntegrated(config)
        elif 'traktorpool' in name_lower or 'technikboerse' in name_lower:
            return TraktorpoolScraper(config)
        elif 'subito' in name_lower:
            return SubitoScraper(config)
        else:
            return GenericScraper(config)

    def scrape_platform(self, country_code: str, platform_config: Dict) -> Dict[str, Any]:
        """Scrapt eine einzelne Plattform und liefert Metadaten für das Run-Tracking."""
        started_at = time.time()
        search_urls = [platform_config["search_url"], *(platform_config.get("additional_search_urls") or [])]
        all_listings: List[Listing] = []
        seen_ids = set()
        error_messages: List[str] = []

        try:
            for search_url in search_urls:
                config = {**platform_config, "search_url": search_url}
                scraper = self.get_scraper_for_platform(config, country_code)
                listings = scraper.scrape()

                for listing in listings:
                    if listing.id in seen_ids:
                        continue
                    seen_ids.add(listing.id)
                    all_listings.append(listing)

                if getattr(scraper, "last_error", None):
                    error_messages.append(f"{search_url}: {scraper.last_error}")

            duration = round(time.time() - started_at, 2)
            if error_messages and not all_listings:
                status = 'error'
            elif all_listings:
                status = 'success'
            else:
                status = 'empty'
            return {
                'listings': all_listings,
                'status': status,
                'error_message': " | ".join(error_messages) if error_messages else None,
                'duration_seconds': duration,
            }
        except Exception as e:
            logger.error(f"Fehler beim Scrapen von {platform_config['name']}: {e}")
            return {
                'listings': [],
                'status': 'error',
                'error_message': str(e),
                'duration_seconds': round(time.time() - started_at, 2),
            }

    def run(self, countries: List[str] = None, priority: str = None,
            max_workers: int = 5, brands: List[str] = None) -> Dict:
        """
        Führt den Scraper aus.

        Args:
            countries: Liste der Ländercodes (z.B. ['DE', 'AT']). None = alle
            priority: Filter nach Priorität ('high', 'medium', 'low'). None = alle
            max_workers: Anzahl paralleler Threads
            brands: Liste der Marken-Keys (z.B. ['fendt', 'john_deere']). None = nur MB-trac

        Returns:
            Statistiken über den Scan-Durchlauf
        """
        start_time = time.time()
        total_new = 0
        total_listings = 0
        platforms_scanned = 0
        platforms_success = 0
        platforms_empty = 0
        platforms_error = 0

        # Plattformen sammeln (Haupt-URLs für MB-trac)
        tasks = []
        for country_code, country_data in self.platforms.items():
            if countries and country_code not in countries:
                continue

            for platform in country_data['platforms']:
                if platform.get('enabled', True) is False:
                    logger.info(f"Überspringe deaktivierte Plattform: {platform['name']}")
                    continue
                if priority and platform.get('priority') != priority:
                    continue
                # Haupt-URL (MB-trac) immer mit aufnehmen
                tasks.append((country_code, platform))

                # Zusätzliche Brand-URLs wenn Marken aktiviert sind
                if brands and 'brand_search_urls' in platform:
                    for brand_key in brands:
                        if brand_key in platform['brand_search_urls']:
                            # Erstelle eine Kopie der Platform-Config mit der Brand-URL
                            brand_config = {**platform}
                            brand_config['search_url'] = platform['brand_search_urls'][brand_key]
                            brand_config['name'] = f"{platform['name']} ({get_brand_display_name(brand_key)})"
                            tasks.append((country_code, brand_config))

        logger.info(f"Starte Scan von {len(tasks)} Plattformen...")
        scan_run_id = self.db.start_scan_run(len(tasks))

        # Parallel ausführen
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(self.scrape_platform, cc, pf): (cc, pf)
                for cc, pf in tasks
            }

            for future in as_completed(future_to_task):
                country_code, platform = future_to_task[future]
                try:
                    result = future.result()
                    listings = result['listings']
                    platforms_scanned += 1
                    new_for_platform = 0

                    for listing in listings:
                        is_new = self.db.add_listing(listing)
                        if is_new:
                            total_new += 1
                            new_for_platform += 1
                        total_listings += 1

                    if result['status'] == 'success':
                        platforms_success += 1
                    elif result['status'] == 'empty':
                        platforms_empty += 1
                    else:
                        platforms_error += 1

                    self.db.log_platform_run(
                        scan_run_id=scan_run_id,
                        country_code=country_code,
                        platform_name=platform['name'],
                        search_url=platform['search_url'],
                        status=result['status'],
                        error_message=result['error_message'],
                        listings_found=len(listings),
                        new_listings=new_for_platform,
                        duration_seconds=result['duration_seconds'],
                    )

                    logger.info(
                        f"{platform['name']}: status={result['status']} "
                        f"listings={len(listings)} new={new_for_platform} "
                        f"duration={result['duration_seconds']}s"
                    )

                except Exception as e:
                    logger.error(f"Fehler bei {platform['name']}: {e}")
                    platforms_error += 1
                    self.db.log_platform_run(
                        scan_run_id=scan_run_id,
                        country_code=country_code,
                        platform_name=platform['name'],
                        search_url=platform['search_url'],
                        status='error',
                        error_message=str(e),
                        listings_found=0,
                        new_listings=0,
                        duration_seconds=0,
                    )

                # Zufällige Pause zwischen Requests (0.3-1.5 Sekunden)
                time.sleep(random.uniform(0.3, 1.5))

        duration = time.time() - start_time
        self.db.flush()
        self.db.finish_scan_run(
            scan_run_id,
            platforms_scanned=platforms_scanned,
            new_listings=total_new,
            total_listings=total_listings,
            duration_seconds=round(duration, 2),
            platforms_success=platforms_success,
            platforms_empty=platforms_empty,
            platforms_error=platforms_error,
        )

        stats = {
            'platforms_scanned': platforms_scanned,
            'new_listings': total_new,
            'total_listings': total_listings,
            'duration_seconds': round(duration, 2),
            'platforms_success': platforms_success,
            'platforms_empty': platforms_empty,
            'platforms_error': platforms_error,
        }

        logger.info(f"Scan abgeschlossen: {stats}")
        return stats


def generate_dashboard(db, output_path: Path):
    """Generiert ein HTML-Dashboard mit Kategorie-Filtern"""
    stats = db.get_stats()
    listings = db.get_all_active()
    today = datetime.now().strftime("%Y-%m-%d")
    new_today = db.get_new_listings(today)

    # Kategorien zählen
    cat_counts = {'fahrzeug': 0, 'ersatzteil': 0, 'modell': 0, 'suchgesuch': 0, 'sonstiges': 0}
    for l in listings:
        cat = l.get('category', 'sonstiges')
        if cat in cat_counts:
            cat_counts[cat] += 1

    # Fahrzeuge mit Preis für Highlight
    vehicles_with_price = [l for l in listings
                          if l.get('category') == 'fahrzeug'
                          and l.get('price_numeric') and l.get('price_numeric') > 1000]
    vehicles_with_price.sort(key=lambda x: x.get('first_seen', ''), reverse=True)

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MB-trac Scraper Dashboard</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ color: #1a1a2e; margin-bottom: 20px; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{ color: #666; font-size: 0.85em; margin-bottom: 5px; }}
        .stat-card .value {{ font-size: 1.8em; font-weight: bold; color: #1a1a2e; }}
        .stat-card.new .value {{ color: #27ae60; }}
        .stat-card.vehicle .value {{ color: #e74c3c; }}
        .section {{ margin-bottom: 30px; }}
        .section h2 {{ margin-bottom: 15px; color: #1a1a2e; }}
        .listings {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }}
        .listing {{
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        .listing:hover {{ transform: translateY(-3px); }}
        .listing.new {{ border-left: 4px solid #27ae60; }}
        .listing.cat-fahrzeug {{ border-left: 4px solid #e74c3c; }}
        .listing.cat-ersatzteil {{ border-left: 4px solid #3498db; }}
        .listing.cat-modell {{ border-left: 4px solid #9b59b6; }}
        .listing.cat-suchgesuch {{ border-left: 4px solid #f39c12; }}
        .listing img {{
            width: 100%;
            height: 200px;
            object-fit: cover;
            background: #eee;
        }}
        .listing-content {{ padding: 15px; }}
        .listing h3 {{ font-size: 1em; margin-bottom: 10px; line-height: 1.3; }}
        .listing h3 a {{ color: #333; text-decoration: none; }}
        .listing h3 a:hover {{ color: #2980b9; }}
        .listing .meta {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 5px; }}
        .listing .price {{ font-weight: bold; color: #27ae60; font-size: 1.1em; }}
        .listing .price.negotiable {{ color: #f39c12; }}
        .listing .platform {{
            background: #e8e8e8;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8em;
        }}
        .listing .category {{
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            color: white;
        }}
        .listing .category.fahrzeug {{ background: #e74c3c; }}
        .listing .category.ersatzteil {{ background: #3498db; }}
        .listing .category.modell {{ background: #9b59b6; }}
        .listing .category.suchgesuch {{ background: #f39c12; }}
        .listing .category.sonstiges {{ background: #95a5a6; }}
        .listing .location {{ color: #666; font-size: 0.9em; margin-top: 8px; }}
        .no-image {{
            width: 100%;
            height: 200px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 3em;
        }}
        .update-time {{ color: #999; text-align: right; margin-top: 20px; }}
        .filter-bar {{
            background: white;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .filter-bar h3 {{ margin-bottom: 10px; font-size: 0.9em; color: #666; }}
        .filter-btn {{
            padding: 8px 16px;
            margin-right: 5px;
            margin-bottom: 5px;
            border: none;
            background: #e8e8e8;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .filter-btn:hover {{ background: #d0d0d0; }}
        .filter-btn.active {{ background: #1a1a2e; color: white; }}
        .filter-btn.fahrzeug.active {{ background: #e74c3c; }}
        .filter-btn.ersatzteil.active {{ background: #3498db; }}
        .filter-btn.modell.active {{ background: #9b59b6; }}
        .filter-btn.suchgesuch.active {{ background: #f39c12; }}
        .hidden {{ display: none !important; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚜 MB-trac Scraper Dashboard</h1>

        <div class="stats">
            <div class="stat-card new">
                <h3>Neue heute</h3>
                <div class="value">{stats['new_today']}</div>
            </div>
            <div class="stat-card vehicle">
                <h3>🚜 Fahrzeuge</h3>
                <div class="value">{cat_counts['fahrzeug']}</div>
            </div>
            <div class="stat-card">
                <h3>🔧 Ersatzteile</h3>
                <div class="value">{cat_counts['ersatzteil']}</div>
            </div>
            <div class="stat-card">
                <h3>🎮 Modelle</h3>
                <div class="value">{cat_counts['modell']}</div>
            </div>
            <div class="stat-card">
                <h3>🔍 Suchgesuche</h3>
                <div class="value">{cat_counts['suchgesuch']}</div>
            </div>
            <div class="stat-card">
                <h3>Gesamt</h3>
                <div class="value">{stats['active']}</div>
            </div>
        </div>

        <div class="filter-bar">
            <h3>Filter nach Kategorie:</h3>
            <button class="filter-btn active" data-filter="all">Alle ({stats['active']})</button>
            <button class="filter-btn fahrzeug" data-filter="fahrzeug">🚜 Fahrzeuge ({cat_counts['fahrzeug']})</button>
            <button class="filter-btn ersatzteil" data-filter="ersatzteil">🔧 Ersatzteile ({cat_counts['ersatzteil']})</button>
            <button class="filter-btn modell" data-filter="modell">🎮 Modelle ({cat_counts['modell']})</button>
            <button class="filter-btn suchgesuch" data-filter="suchgesuch">🔍 Suchgesuche ({cat_counts['suchgesuch']})</button>
        </div>
"""

    # Fahrzeuge-Sektion (wenn vorhanden)
    if vehicles_with_price:
        html += """
        <div class="section">
            <h2>🚜 Fahrzeuge zum Verkauf</h2>
            <div class="listings">
"""
        for listing in vehicles_with_price[:12]:
            img_html = f'<img src="{listing["image_url"]}" alt="" loading="lazy">' if listing.get('image_url') else '<div class="no-image">🚜</div>'
            price_num = listing.get('price_numeric')
            price_display = f"{price_num:,.0f} €".replace(',', '.') if price_num else listing.get('price', '')
            neg_class = 'negotiable' if listing.get('is_negotiable') else ''
            price_html = f'<span class="price {neg_class}">{price_display}</span>' if price_display else ''
            location_html = f'<div class="location">📍 {listing["location"]}</div>' if listing.get('location') else ''

            html += f"""
                <div class="listing cat-fahrzeug" data-category="fahrzeug">
                    {img_html}
                    <div class="listing-content">
                        <h3><a href="{listing['url']}" target="_blank">{listing['title'][:100]}</a></h3>
                        <div class="meta">
                            {price_html}
                            <span class="platform">{listing['country']} · {listing['platform']}</span>
                        </div>
                        {location_html}
                    </div>
                </div>
"""
        html += """
            </div>
        </div>
"""

    # Neue Inserate heute
    if new_today:
        html += """
        <div class="section">
            <h2>🆕 Neue Inserate heute</h2>
            <div class="listings">
"""
        for listing in new_today[:20]:
            cat = listing.get('category', 'sonstiges')
            img_html = f'<img src="{listing["image_url"]}" alt="" loading="lazy">' if listing.get('image_url') else '<div class="no-image">🚜</div>'
            price_num = listing.get('price_numeric')
            neg_class = 'negotiable' if listing.get('is_negotiable') else ''
            if price_num:
                price_display = f"{price_num:,.0f} €".replace(',', '.')
            else:
                price_display = listing.get('price', '')
            price_html = f'<span class="price {neg_class}">{price_display}</span>' if price_display else ''
            location_html = f'<div class="location">📍 {listing["location"]}</div>' if listing.get('location') else ''
            cat_label = {'fahrzeug': '🚜', 'ersatzteil': '🔧', 'modell': '🎮', 'suchgesuch': '🔍'}.get(cat, '')

            html += f"""
                <div class="listing new cat-{cat}" data-category="{cat}">
                    {img_html}
                    <div class="listing-content">
                        <h3><a href="{listing['url']}" target="_blank">{listing['title'][:100]}</a></h3>
                        <div class="meta">
                            {price_html}
                            <span class="category {cat}">{cat_label} {cat.title()}</span>
                            <span class="platform">{listing['country']} · {listing['platform']}</span>
                        </div>
                        {location_html}
                    </div>
                </div>
"""
        html += """
            </div>
        </div>
"""

    html += """
        <div class="section">
            <h2>📋 Alle Inserate</h2>
            <div class="listings" id="all-listings">
"""
    for listing in listings[:200]:
        cat = listing.get('category', 'sonstiges')
        is_new_class = 'new' if listing.get('first_seen', '').startswith(today) else ''
        img_html = f'<img src="{listing["image_url"]}" alt="" loading="lazy">' if listing.get('image_url') else '<div class="no-image">🚜</div>'
        price_num = listing.get('price_numeric')
        neg_class = 'negotiable' if listing.get('is_negotiable') else ''
        if price_num:
            price_display = f"{price_num:,.0f} €".replace(',', '.')
        else:
            price_display = listing.get('price', '')
        price_html = f'<span class="price {neg_class}">{price_display}</span>' if price_display else ''
        location_html = f'<div class="location">📍 {listing["location"]}</div>' if listing.get('location') else ''
        cat_label = {'fahrzeug': '🚜', 'ersatzteil': '🔧', 'modell': '🎮', 'suchgesuch': '🔍'}.get(cat, '')

        html += f"""
            <div class="listing {is_new_class} cat-{cat}" data-category="{cat}">
                {img_html}
                <div class="listing-content">
                    <h3><a href="{listing['url']}" target="_blank">{listing['title'][:100]}</a></h3>
                    <div class="meta">
                        {price_html}
                        <span class="category {cat}">{cat_label} {cat.title()}</span>
                        <span class="platform">{listing['country']} · {listing['platform']}</span>
                    </div>
                    {location_html}
                </div>
            </div>
"""

    html += f"""
            </div>
        </div>

        <p class="update-time">Letzte Aktualisierung: {datetime.now().strftime('%d.%m.%Y %H:%M')} Uhr</p>
    </div>

    <script>
        // Filter-Funktionalität
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', function() {{
                const filter = this.dataset.filter;

                // Active-Klasse aktualisieren
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                // ALLE Listings auf der Seite filtern
                document.querySelectorAll('.listing').forEach(listing => {{
                    if (filter === 'all' || listing.dataset.category === filter) {{
                        listing.classList.remove('hidden');
                    }} else {{
                        listing.classList.add('hidden');
                    }}
                }});

                // Sektionen ausblenden wenn leer
                document.querySelectorAll('.section').forEach(section => {{
                    const visibleListings = section.querySelectorAll('.listing:not(.hidden)');
                    if (visibleListings.length === 0) {{
                        section.classList.add('hidden');
                    }} else {{
                        section.classList.remove('hidden');
                    }}
                }});
            }});
        }});
    </script>
</body>
</html>
"""

    output_path.write_text(html, encoding='utf-8')
    logger.info(f"Dashboard generiert: {output_path}")


def main():
    from brands import get_all_brand_keys
    all_brands = [k for k in get_all_brand_keys() if k != "mb_trac"]

    parser = argparse.ArgumentParser(description='Traktor European Scraper (MB-trac + weitere Marken)')
    parser.add_argument('--countries', '-c', nargs='+', help='Länder zum Scrapen (z.B. DE AT CH)')
    parser.add_argument('--priority', '-p', choices=['high', 'medium', 'low'],
                        help='Nur Plattformen mit dieser Priorität')
    parser.add_argument('--workers', '-w', type=int, default=3,
                        help='Anzahl paralleler Threads (default: 3)')
    parser.add_argument('--dashboard-only', '-d', action='store_true',
                        help='Nur Dashboard generieren, nicht scrapen')
    parser.add_argument('--stats', '-s', action='store_true',
                        help='Nur Statistiken anzeigen')
    parser.add_argument('--brands', '-b', nargs='+', choices=all_brands,
                        help=f'Zusätzliche Marken scrapen: {", ".join(all_brands)}')
    parser.add_argument('--all-brands', action='store_true',
                        help='Alle verfügbaren Marken scrapen (inkl. MB-trac)')

    args = parser.parse_args()

    # Verzeichnisse sicherstellen
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Datenbank initialisieren
    db = SQLiteDatabase(DB_PATH)

    if args.stats:
        stats = db.get_stats()
        print("\n📊 MB-trac Scraper Statistiken")
        print("=" * 40)
        print(f"Inserate gesamt: {stats['total']}")
        print(f"Aktive Inserate: {stats['active']}")
        print(f"Neue heute: {stats['new_today']}")
        print("\nNach Land:")
        for country, count in sorted(stats['by_country'].items(), key=lambda x: -x[1]):
            print(f"  {country}: {count}")
        return

    if args.dashboard_only:
        from dashboard_generator import generate_modern_dashboard
        generate_modern_dashboard(BASE_DIR / "dashboard.html")
        return

    # Marken bestimmen
    enabled_brands = None
    if args.all_brands:
        enabled_brands = all_brands
    elif args.brands:
        enabled_brands = args.brands

    if enabled_brands:
        logger.info(f"Zusätzliche Marken aktiviert: {', '.join(enabled_brands)}")

    # Scraper ausführen
    scraper = MBTracScraper(db)
    stats = scraper.run(
        countries=args.countries,
        priority=args.priority,
        max_workers=args.workers,
        brands=enabled_brands
    )

    # Dashboard lädt Daten live von GitHub Raw - kein Rebuild nötig

    print(f"\n✅ Scan abgeschlossen!")
    print(f"   Plattformen gescannt: {stats['platforms_scanned']}")
    print(f"   Erfolgreich: {stats['platforms_success']}")
    print(f"   Leer: {stats['platforms_empty']}")
    print(f"   Fehler: {stats['platforms_error']}")
    print(f"   Neue Inserate: {stats['new_listings']}")
    print(f"   Dauer: {stats['duration_seconds']}s")
    print(f"\n🌐 API/UI: Starte mit 'uvicorn app:app --reload'")


if __name__ == "__main__":
    main()

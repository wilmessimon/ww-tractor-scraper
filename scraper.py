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
from filters import filter_listing, Category
from mascus_scraper import MascusScraper as SpecializedMascusScraper
from cargr_scraper import CarGrScraper as SpecializedCarGrScraper
from dashboard_generator import generate_modern_dashboard

# Konfiguration
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
DB_PATH = DATA_DIR / "mbtrac.db"

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

    @staticmethod
    def generate_id(url: str) -> str:
        """Generiert eine eindeutige ID aus der URL"""
        return hashlib.md5(url.encode()).hexdigest()[:16]


class Database:
    """JSON-basierte Datenbank für Inserate (SQLite-Alternative für bessere Portabilität)"""

    def __init__(self, db_path: Path):
        self.db_path = db_path.with_suffix('.json')
        self.history_path = db_path.parent / 'scan_history.json'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
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
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self.listings, f, ensure_ascii=False, indent=2)

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
            self._save_data()
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
                self._save_data()
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
        self._save_data()
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
        self.session = requests.Session()
        # Zufällige Headers für jeden Scraper
        self.session.headers.update(get_random_headers())

    def fetch_page(self, url: str, params: Dict = None, max_retries: int = 2) -> Optional[BeautifulSoup]:
        """
        Lädt eine Seite mit Retry-Logik und Anti-Bot-Maßnahmen.

        Args:
            url: Die zu ladende URL
            params: Query-Parameter
            max_retries: Maximale Anzahl Versuche (default: 2)
        """
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
                if response.status_code in [403, 429]:
                    if attempt < max_retries:
                        logger.debug(f"{self.name}: Status {response.status_code}, Retry {attempt + 1}...")
                        continue
                    else:
                        response.raise_for_status()

                response.raise_for_status()
                return BeautifulSoup(response.text, 'html.parser')

            except requests.RequestException as e:
                if attempt == max_retries:
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
        listings = []
        soup = self.fetch_page(self.search_url)

        if not soup:
            return listings

        # Versuche verschiedene gängige Selektoren für Listing-Container
        selectors = [
            # Häufige Klassen für Listing-Container
            'article', '[class*="listing"]', '[class*="item"]', '[class*="ad-"]',
            '[class*="result"]', '[class*="product"]', '[class*="offer"]',
            '.classified', '.advertisement', '.search-result'
        ]

        items = []
        for selector in selectors:
            items = soup.select(selector)
            if len(items) > 2:  # Mindestens ein paar Ergebnisse
                break

        for item in items[:50]:  # Maximal 50 pro Seite
            try:
                listing = self._extract_listing(item)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.debug(f"Fehler beim Parsen eines Items auf {self.name}: {e}")

        logger.info(f"{self.name}: {len(listings)} Inserate gefunden")
        return listings

    def _extract_listing(self, item) -> Optional[Listing]:
        """Versucht Listing-Daten aus einem HTML-Element zu extrahieren"""
        now = datetime.now().isoformat()

        # URL extrahieren
        link = item.find('a', href=True)
        if not link:
            return None

        url = link.get('href', '')
        if not url.startswith('http'):
            # Relative URL auflösen
            base = urlparse(self.search_url)
            url = f"{base.scheme}://{base.netloc}{url}"

        # Titel extrahieren
        title_selectors = ['h2', 'h3', '.title', '[class*="title"]', 'a']
        title = None
        for sel in title_selectors:
            elem = item.select_one(sel)
            if elem and elem.get_text(strip=True):
                title = elem.get_text(strip=True)[:200]
                break

        if not title or len(title) < 3:
            return None

        # Prüfen ob MB-trac relevant (verschiedene Schreibweisen)
        title_lower = title.lower()
        mb_trac_patterns = [
            'mb-trac', 'mb trac', 'mbtrac', 'mb_trac',  # Verschiedene Schreibweisen
            'mercedes trac', 'mercedes-benz trac',      # Mit Markenname
            'wf trac', 'werner trac',                   # Werner Forstmaschinen (übernahm MB-trac)
        ]
        # Auch Modellnummern prüfen wenn "trac" im Titel
        model_numbers = ['65', '70', '700', '800', '900', '1000', '1100', '1300', '1400', '1500', '1600', '1800']

        is_relevant = any(pattern in title_lower for pattern in mb_trac_patterns)
        if not is_relevant and 'trac' in title_lower:
            # Wenn "trac" vorkommt, prüfe auf Modellnummern
            is_relevant = any(num in title for num in model_numbers)
        if not is_relevant and ('mb' in title_lower or 'mercedes' in title_lower) and 'unimog' in title_lower:
            # MB/Mercedes + Unimog ist oft relevant (gleiche Teile)
            is_relevant = True

        if not is_relevant:
            return None

        # Preis extrahieren
        price = None
        price_selectors = ['[class*="price"]', '[class*="cost"]', '.price']
        for sel in price_selectors:
            elem = item.select_one(sel)
            if elem:
                price = elem.get_text(strip=True)[:50]
                break

        # Filter anwenden
        filter_result = filter_listing(title, price)
        if not filter_result.is_valid:
            logger.debug(f"Gefiltert: {title[:50]}... - {filter_result.reason}")
            return None

        # Bild extrahieren
        image = None
        img = item.find('img', src=True)
        if img:
            image = img.get('src') or img.get('data-src')

        # Location extrahieren
        location = None
        loc_selectors = ['[class*="location"]', '[class*="city"]', '[class*="region"]']
        for sel in loc_selectors:
            elem = item.select_one(sel)
            if elem:
                location = elem.get_text(strip=True)[:100]
                break

        return Listing(
            id=Listing.generate_id(url),
            platform=self.name,
            country=self.config.get('country_code', 'XX'),
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
            is_negotiable=filter_result.is_negotiable
        )


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
                    is_negotiable=filter_result.is_negotiable
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
                    is_negotiable=filter_result.is_negotiable
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
            is_negotiable=filter_result.is_negotiable
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
            is_negotiable=filter_result.is_negotiable
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
            is_negotiable=filter_result.is_negotiable
        )


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
        elif 'finn.no' in name_lower or 'finn' in name_lower:
            return FinnNoScraper(config)
        elif 'dba.dk' in name_lower or 'dba' in name_lower:
            return DBADkScraper(config)
        else:
            return GenericScraper(config)

    def scrape_platform(self, country_code: str, platform_config: Dict) -> List[Listing]:
        """Scrapt eine einzelne Plattform"""
        scraper = self.get_scraper_for_platform(platform_config, country_code)
        try:
            return scraper.scrape()
        except Exception as e:
            logger.error(f"Fehler beim Scrapen von {platform_config['name']}: {e}")
            return []

    def run(self, countries: List[str] = None, priority: str = None, max_workers: int = 5) -> Dict:
        """
        Führt den Scraper aus.

        Args:
            countries: Liste der Ländercodes (z.B. ['DE', 'AT']). None = alle
            priority: Filter nach Priorität ('high', 'medium', 'low'). None = alle
            max_workers: Anzahl paralleler Threads

        Returns:
            Statistiken über den Scan-Durchlauf
        """
        start_time = time.time()
        total_new = 0
        total_listings = 0
        platforms_scanned = 0

        # Plattformen sammeln
        tasks = []
        for country_code, country_data in self.platforms.items():
            if countries and country_code not in countries:
                continue

            for platform in country_data['platforms']:
                if priority and platform.get('priority') != priority:
                    continue
                tasks.append((country_code, platform))

        logger.info(f"Starte Scan von {len(tasks)} Plattformen...")

        # Parallel ausführen
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(self.scrape_platform, cc, pf): (cc, pf)
                for cc, pf in tasks
            }

            for future in as_completed(future_to_task):
                country_code, platform = future_to_task[future]
                try:
                    listings = future.result()
                    platforms_scanned += 1

                    for listing in listings:
                        is_new = self.db.add_listing(listing)
                        if is_new:
                            total_new += 1
                        total_listings += 1

                except Exception as e:
                    logger.error(f"Fehler bei {platform['name']}: {e}")

                # Zufällige Pause zwischen Requests (0.3-1.5 Sekunden)
                time.sleep(random.uniform(0.3, 1.5))

        duration = time.time() - start_time
        self.db.log_scan(platforms_scanned, total_new, total_listings, duration)

        stats = {
            'platforms_scanned': platforms_scanned,
            'new_listings': total_new,
            'total_listings': total_listings,
            'duration_seconds': round(duration, 2)
        }

        logger.info(f"Scan abgeschlossen: {stats}")
        return stats


def generate_dashboard(db: Database, output_path: Path):
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
    parser = argparse.ArgumentParser(description='MB-trac European Scraper')
    parser.add_argument('--countries', '-c', nargs='+', help='Länder zum Scrapen (z.B. DE AT CH)')
    parser.add_argument('--priority', '-p', choices=['high', 'medium', 'low'],
                        help='Nur Plattformen mit dieser Priorität')
    parser.add_argument('--workers', '-w', type=int, default=3,
                        help='Anzahl paralleler Threads (default: 3)')
    parser.add_argument('--dashboard-only', '-d', action='store_true',
                        help='Nur Dashboard generieren, nicht scrapen')
    parser.add_argument('--stats', '-s', action='store_true',
                        help='Nur Statistiken anzeigen')

    args = parser.parse_args()

    # Verzeichnisse sicherstellen
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Datenbank initialisieren
    db = Database(DB_PATH)

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
        generate_modern_dashboard(db.db_path, BASE_DIR / "dashboard.html")
        return

    # Scraper ausführen
    scraper = MBTracScraper(db)
    stats = scraper.run(
        countries=args.countries,
        priority=args.priority,
        max_workers=args.workers
    )

    # Dashboard generieren (modernes Tailwind-Design)
    generate_modern_dashboard(db.db_path, BASE_DIR / "dashboard.html")

    print(f"\n✅ Scan abgeschlossen!")
    print(f"   Plattformen gescannt: {stats['platforms_scanned']}")
    print(f"   Neue Inserate: {stats['new_listings']}")
    print(f"   Dauer: {stats['duration_seconds']}s")
    print(f"\n📊 Dashboard: {BASE_DIR / 'dashboard.html'}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Mascus Scraper
==============
Spezialisierter Scraper für Mascus-Plattformen.
Extrahiert Daten aus dem eingebetteten Next.js JSON (__NEXT_DATA__).
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime
import hashlib

# Browser-ähnliche Headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

@dataclass
class MascusListing:
    """Ein Mascus-Inserat"""
    id: str
    title: str
    price: Optional[str]
    price_numeric: Optional[float]
    currency: str
    location: Optional[str]
    country: str
    url: str
    image_url: Optional[str]
    year: Optional[int]
    hours: Optional[int]
    platform: str

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'title': self.title,
            'price': self.price,
            'price_numeric': self.price_numeric,
            'currency': self.currency,
            'location': self.location,
            'country': self.country,
            'url': self.url,
            'image_url': self.image_url,
            'year': self.year,
            'hours': self.hours,
            'platform': self.platform,
            'first_seen': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
        }


class MascusScraper:
    """Scraper für Mascus-Plattformen"""

    # LKW-Keywords zum Filtern (keine Traktoren!)
    LKW_KEYWORDS = [
        'arocs', 'actros', 'atego', 'axor', 'antos', 'econic',
        'kipper', 'sattelzug', 'lkw', 'truck', 'lorry'
    ]

    # Mascus-Domains mit Ländercode
    DOMAINS = {
        'mascus.de': 'DE',
        'mascus.at': 'AT',
        'mascus.ch': 'CH',
        'mascus.nl': 'NL',
        'mascus.be': 'BE',
        'mascus.no': 'NO',
        'mascus.se': 'SE',
        'mascus.fi': 'FI',
        'mascus.dk': 'DK',
        'mascus.co.uk': 'UK',
        'mascus.ie': 'IE',
        'mascus.fr': 'FR',
        'mascus.es': 'ES',
        'mascus.pt': 'PT',
        'mascus.it': 'IT',
        'mascus.gr': 'GR',
        'mascus.pl': 'PL',
        'mascus.cz': 'CZ',
        'mascus.sk': 'SK',
        'mascus.hu': 'HU',
        'mascus.ro': 'RO',
        'mascus.bg': 'BG',
        'mascus.hr': 'HR',
        'mascus.rs': 'RS',
        'mascus.si': 'SI',
        'mascus.ee': 'EE',
        'mascus.lv': 'LV',
        'mascus.lt': 'LT',
    }

    def __init__(self, filter_lkw: bool = True):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.filter_lkw = filter_lkw

    def is_lkw(self, title: str) -> bool:
        """Prüft ob ein Titel ein LKW (Arocs/Actros/etc.) ist"""
        title_lower = title.lower()
        return any(kw in title_lower for kw in self.LKW_KEYWORDS)

    def filter_listings(self, listings: List[MascusListing]) -> List[MascusListing]:
        """Filtert LKW aus den Ergebnissen"""
        if not self.filter_lkw:
            return listings

        filtered = []
        removed = 0
        for listing in listings:
            if self.is_lkw(listing.title):
                removed += 1
            else:
                filtered.append(listing)

        if removed > 0:
            print(f"  🚛 {removed} LKW gefiltert (Arocs/Actros/etc.)")

        return filtered

    def get_search_url(self, domain: str, query: str = "mb trac") -> str:
        """Generiert die Such-URL für eine Mascus-Domain"""
        # URL-encode den Suchbegriff
        encoded_query = query.replace(' ', '%20')
        return f"https://www.{domain}/{encoded_query}/+/1,relevance,search.html"

    def extract_next_data(self, html: str) -> Optional[Dict]:
        """Extrahiert die __NEXT_DATA__ JSON aus dem HTML"""
        soup = BeautifulSoup(html, 'html.parser')

        # Suche nach dem __NEXT_DATA__ Script-Tag
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        if next_data_script and next_data_script.string:
            try:
                return json.loads(next_data_script.string)
            except json.JSONDecodeError:
                pass

        # Fallback: Suche nach JSON in Script-Tags
        for script in soup.find_all('script'):
            if script.string and 'searchResult' in script.string:
                # Versuche JSON zu extrahieren
                try:
                    # Suche nach dem pageProps Objekt
                    match = re.search(r'"pageProps"\s*:\s*(\{.*\})\s*,\s*"__N_SSP"', script.string, re.DOTALL)
                    if match:
                        return {'props': {'pageProps': json.loads(match.group(1))}}
                except:
                    pass

        return None

    def parse_listings_from_next_data(self, data: Dict, domain: str) -> List[MascusListing]:
        """Parst Listings aus den __NEXT_DATA__"""
        listings = []

        try:
            # Navigation durch die Next.js Datenstruktur
            page_props = data.get('props', {}).get('pageProps', {})

            # Mascus verwendet searchRes.searchData.items
            items = None

            # Primär: searchRes.searchData.items (aktuelle Mascus-Struktur)
            search_res = page_props.get('searchRes', {})
            if search_res:
                search_data = search_res.get('searchData', {})
                items = search_data.get('items', [])

            # Fallback: andere mögliche Strukturen
            if not items:
                for key in ['searchResult', 'searchResults', 'results', 'listings', 'items']:
                    if key in page_props:
                        val = page_props[key]
                        if isinstance(val, dict):
                            items = val.get('items', val.get('listings', []))
                        elif isinstance(val, list):
                            items = val
                        if items:
                            break

            if not items:
                return listings

            country = self.DOMAINS.get(domain, 'XX')
            base_url = f"https://www.{domain}"

            for item in items:
                try:
                    listing = self._parse_item(item, domain, country, base_url)
                    if listing:
                        listings.append(listing)
                except Exception as e:
                    print(f"  Fehler beim Parsen eines Items: {e}")
                    continue

        except Exception as e:
            print(f"  Fehler beim Parsen der Next.js Daten: {e}")

        return listings

    def _parse_item(self, item, domain: str, country: str, base_url: str) -> Optional[MascusListing]:
        """Parst ein einzelnes Item aus den Daten"""
        # Prüfe ob item ein Dict ist
        if not isinstance(item, dict):
            return None

        # Titel: Mascus verwendet brand + model
        title = item.get('title') or item.get('name') or item.get('headline', '')
        if not title:
            brand = item.get('brand', '')
            model = item.get('model', '')
            if brand or model:
                title = f"{brand} {model}".strip()
        if not title:
            return None

        # URL: Mascus verwendet assetUrl
        url = item.get('url') or item.get('assetUrl') or item.get('link') or item.get('href', '')
        if url and not url.startswith('http'):
            url = base_url + url

        # ID generieren
        item_id = item.get('id') or item.get('productId') or item.get('listingId') or hashlib.md5(url.encode()).hexdigest()[:16]

        # Preis: Mascus verwendet priceEURO oder priceOriginal
        price_numeric = item.get('priceEURO') or item.get('priceOriginal') or item.get('priceInUserCurrency')
        currency = item.get('priceOriginalUnit') or item.get('userCurrency') or 'EUR'

        if price_numeric is None:
            price_data = item.get('price', {})
            if isinstance(price_data, dict):
                price_numeric = price_data.get('amount') or price_data.get('value')
                currency = price_data.get('currency', 'EUR')
            elif isinstance(price_data, (int, float)):
                price_numeric = price_data

        price_str = f"{price_numeric} {currency}" if price_numeric else None

        # Bild: Mascus verwendet imageUrl (direkte Cloudfront-URL!)
        image = item.get('imageUrl') or item.get('image') or item.get('thumbnail')
        if isinstance(image, dict):
            image = image.get('url') or image.get('src')
        if isinstance(image, list) and len(image) > 0:
            image = image[0].get('url') if isinstance(image[0], dict) else image[0]

        # Location: Mascus verwendet locationCity + locationCountryCode
        location = item.get('locationCity') or item.get('location') or item.get('city') or item.get('region')
        if isinstance(location, dict):
            location = location.get('name') or location.get('city')
        # Füge Land hinzu wenn nicht im Location
        loc_country = item.get('locationCountryCode')
        if loc_country and location and loc_country not in location:
            location = f"{location}, {loc_country}"

        # Jahr: Mascus verwendet yearOfManufacture
        year = item.get('yearOfManufacture') or item.get('year') or item.get('productionYear')

        # Stunden: Mascus verwendet meterReadout
        hours = item.get('meterReadout') or item.get('hours') or item.get('operatingHours')

        return MascusListing(
            id=str(item_id),
            title=title,
            price=price_str,
            price_numeric=float(price_numeric) if price_numeric else None,
            currency=currency,
            location=location,
            country=country,
            url=url,
            image_url=image,
            year=int(year) if year else None,
            hours=int(hours) if hours else None,
            platform=f"Mascus.{domain.split('.')[-1].upper()}"
        )

    def parse_listings_from_html(self, html: str, domain: str) -> List[MascusListing]:
        """Fallback: Parst Listings direkt aus dem HTML"""
        listings = []
        soup = BeautifulSoup(html, 'html.parser')

        country = self.DOMAINS.get(domain, 'XX')
        base_url = f"https://www.{domain}"

        # Mascus-Links haben typischerweise eine ID am Ende wie /uhncwfsi.html (8 Zeichen vor .html)
        # Beispiel: /poľnohospodarske-stroje/traktory/mb-trac-unimog-u421/uhncwfsi.html
        link_pattern = re.compile(r'/[a-z0-9]{6,10}\.html$', re.IGNORECASE)

        seen_urls = set()

        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '')
            text = a_tag.get_text(strip=True)

            # Filter: Muss .html am Ende haben mit kurzer ID
            if not link_pattern.search(href):
                continue

            # Filter: Muss ein Titel vorhanden sein
            if not text or len(text) < 5:
                continue

            # Filter: Keine Navigations-Links
            if any(skip in href.lower() for skip in ['/login', '/register', '/contact', '/about', '/help']):
                continue

            full_url = href if href.startswith('http') else base_url + href

            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Versuche Bild zu finden - mehrere Strategien
            image_url = None

            # Strategie 1: Bild direkt im Link
            img = a_tag.find('img')
            if img:
                image_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')

            # Strategie 2: Suche in mehreren Parent-Ebenen
            if not image_url:
                parent = a_tag.parent
                for _ in range(5):  # Bis zu 5 Ebenen nach oben
                    if not parent:
                        break
                    # Suche nach Bildern mit relevanten URLs (cloudfront, mascus, etc.)
                    for img in parent.find_all('img'):
                        src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or ''
                        # Ignoriere Platzhalter und Icons
                        if src and not src.startswith('data:') and len(src) > 50:
                            if any(x in src.lower() for x in ['cloudfront', 'mascus', 'product', 'listing', 'image']):
                                image_url = src
                                break
                    if image_url:
                        break
                    parent = parent.parent

            # Strategie 3: Suche nach Geschwister-Elementen mit Bildern
            if not image_url and a_tag.parent:
                for sibling in a_tag.parent.find_all(['div', 'figure', 'picture', 'span']):
                    img = sibling.find('img')
                    if img:
                        src = img.get('src') or img.get('data-src') or ''
                        if src and not src.startswith('data:') and len(src) > 50:
                            image_url = src
                            break

            # Versuche Preis zu finden (im Parent-Container)
            price_str = None
            price_numeric = None
            parent = a_tag.parent
            for _ in range(3):  # Bis zu 3 Ebenen nach oben
                if parent:
                    parent_text = parent.get_text()
                    # Verschiedene Preisformate
                    price_patterns = [
                        r'([\d\s.,]+)\s*(?:€|EUR)',
                        r'€\s*([\d\s.,]+)',
                        r'([\d\s.,]+)\s*(?:USD|\$)',
                        r'([\d\s.,]+)\s*(?:CHF|Fr\.)',
                    ]
                    for pattern in price_patterns:
                        price_match = re.search(pattern, parent_text)
                        if price_match:
                            price_str = price_match.group(0).strip()
                            # Extrahiere numerischen Wert
                            num_str = price_match.group(1).replace(' ', '').replace('.', '').replace(',', '.')
                            try:
                                price_numeric = float(num_str)
                            except:
                                pass
                            break
                    if price_str:
                        break
                    parent = parent.parent

            listing = MascusListing(
                id=hashlib.md5(full_url.encode()).hexdigest()[:16],
                title=text,
                price=price_str,
                price_numeric=price_numeric,
                currency='EUR',
                location=None,
                country=country,
                url=full_url,
                image_url=image_url,
                year=None,
                hours=None,
                platform=f"Mascus.{domain.split('.')[-1].upper()}"
            )
            listings.append(listing)

        return listings

    def scrape_domain(self, domain: str, query: str = "mb trac") -> List[MascusListing]:
        """Scrapt eine einzelne Mascus-Domain"""
        url = self.get_search_url(domain, query)
        print(f"🔍 Scrape {domain}: {url}")

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"  ❌ Fehler: {e}")
            return []

        # Methode 1: Versuche __NEXT_DATA__ zu extrahieren
        next_data = self.extract_next_data(response.text)
        if next_data:
            listings = self.parse_listings_from_next_data(next_data, domain)
            if listings:
                print(f"  ✅ {len(listings)} Inserate gefunden (via Next.js)")
                return self.filter_listings(listings)

        # Methode 2: Fallback auf HTML-Parsing
        listings = self.parse_listings_from_html(response.text, domain)
        print(f"  {'✅' if listings else '⚠️'} {len(listings)} Inserate gefunden (via HTML)")
        return self.filter_listings(listings)

    def scrape_all(self, query: str = "mb trac") -> List[MascusListing]:
        """Scrapt alle Mascus-Domains"""
        all_listings = []

        for domain in self.DOMAINS.keys():
            listings = self.scrape_domain(domain, query)
            all_listings.extend(listings)

        print(f"\n📊 Gesamt: {len(all_listings)} Inserate von {len(self.DOMAINS)} Mascus-Seiten")
        return all_listings


def main():
    """Test-Funktion"""
    import sys

    scraper = MascusScraper()

    print("=" * 60)
    print("MASCUS SCRAPER TEST")
    print("=" * 60)

    # Prüfe ob --all Flag gesetzt ist
    test_all = '--all' in sys.argv

    if test_all:
        # Teste alle Domains
        print("Teste ALLE Mascus-Domains...\n")
        all_listings = scraper.scrape_all('mb trac')

        print(f"\n📋 Gefundene Inserate (erste 20):")
        for listing in all_listings[:20]:
            print(f"\n  📦 {listing.title}")
            print(f"     Preis: {listing.price} ({listing.price_numeric})")
            print(f"     Land: {listing.country} | Plattform: {listing.platform}")
            print(f"     URL: {listing.url[:70]}...")
    else:
        # Teste nur ausgewählte Domains
        test_domains = ['mascus.sk', 'mascus.de', 'mascus.nl', 'mascus.fr', 'mascus.it']

        total = 0
        for domain in test_domains:
            listings = scraper.scrape_domain(domain, 'mb trac')
            total += len(listings)

            if listings:
                print(f"  Beispiel: {listings[0].title[:50]}...")
                if listings[0].price:
                    print(f"            Preis: {listings[0].price}")

        print(f"\n📊 Gesamt: {total} Inserate von {len(test_domains)} Test-Domains")
        print("\n💡 Tipp: Nutze 'python3 mascus_scraper.py --all' um alle Domains zu testen")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Spezialisierter Scraper für Car.gr (Griechenland)
Extrahiert MB-trac Inserate aus der griechischen Fahrzeugplattform.
"""

import re
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.parse import urljoin

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
        self.session = requests.Session()
        import random
        self.session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'el-GR,el;q=0.9,en;q=0.8,de;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def scrape(self) -> List[Dict]:
        """Scraped alle MB-trac Inserate von car.gr"""
        listings = []

        try:
            logger.info(f"Scraping car.gr: {self.SEARCH_URL}")
            response = self.session.get(self.SEARCH_URL, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Finde alle Listing-Links
            listing_links = soup.find_all('a', href=re.compile(r'/classifieds/tractors/view/'))

            seen_urls = set()
            for link in listing_links:
                href = link.get('href', '')
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

        except requests.RequestException as e:
            logger.error(f"Car.gr Fehler: {e}")
        except Exception as e:
            logger.error(f"Car.gr Parser-Fehler: {e}")

        return listings

    def _parse_listing_card(self, link_element, url: str) -> Optional[Dict]:
        """Parst eine Listing-Karte"""
        try:
            # Bild
            img = link_element.find('img')
            image_url = img.get('src', '') if img else ''

            # Titel aus h2/h3 oder img alt
            heading = link_element.find(['h2', 'h3'])
            if heading:
                title_parts = heading.get_text(strip=True).replace('\n', ' ').split()
                title = ' '.join(title_parts)
            elif img and img.get('alt'):
                title = img.get('alt', '')
            else:
                title = ''

            # Gesamter Text für weitere Extraktion
            full_text = link_element.get_text(' ', strip=True)

            # Modell extrahieren (MB TRAC XXXX)
            model_match = re.search(r'MB\s*TRAC\s*\d+', full_text, re.IGNORECASE)
            if model_match:
                model = model_match.group(0)
                if model not in title:
                    title = f"{title} {model}"

            # Preis extrahieren (XX.XXX €)
            price = None
            price_numeric = None
            price_match = re.search(r'(\d{1,3}(?:\.\d{3})*)\s*€', full_text)
            if price_match:
                price = f"{price_match.group(1)} €"
                price_numeric = float(price_match.group(1).replace('.', ''))

            # Location extrahieren (Ort mit Postleitzahl)
            location = None
            # Suche nach griechischen Orten mit PLZ
            loc_match = re.search(r'([A-ZΑ-Ω]{2,}(?:\s+[A-ZΑ-Ω]+)*)\s*(?:Ν\.\s*[^\d]+)?\s*(\d{5})', full_text)
            if loc_match:
                location = f"{loc_match.group(1)} {loc_match.group(2)}"
            else:
                # Alternativ: Suche nach bekannten Präfixen
                loc_match2 = re.search(r'([A-ZΑ-Ω]{3,})\s+\d{5}', full_text)
                if loc_match2:
                    location = loc_match2.group(0)

            # Jahr extrahieren
            year = None
            year_match = re.search(r'\b(19[7-9]\d|20[0-2]\d)\b', title)
            if year_match:
                year = year_match.group(1)

            # Validierung: Muss MB-trac relevanter Titel sein
            if not re.search(r'(?:mb[- ]?trac|mercedes.*trac|trac.*mercedes)', title, re.IGNORECASE):
                return None

            return {
                'platform': 'Car.gr',
                'country': 'GR',
                'title': title.strip(),
                'price': price,
                'price_numeric': price_numeric,
                'location': location,
                'url': url,
                'image_url': image_url,
                'year': year,
                'category': 'fahrzeug'
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

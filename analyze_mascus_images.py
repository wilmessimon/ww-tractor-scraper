#!/usr/bin/env python3
"""Analysiert Mascus HTML um Bild-Struktur zu verstehen"""

import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
}

def analyze():
    url = "https://www.mascus.de/mb%20trac/+/1,relevance,search.html"
    print(f"Fetching {url}...")

    response = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Finde alle Bilder
    all_imgs = soup.find_all('img')
    print(f"\nGefundene <img> Tags: {len(all_imgs)}")

    # Zeige Bild-URLs die relevant aussehen
    print("\n--- Relevante Bild-URLs ---")
    relevant_imgs = []
    for img in all_imgs:
        src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or ''
        if 'trac' in src.lower() or 'mascus' in src.lower() or 'cloudinary' in src.lower() or 'cdn' in src.lower():
            relevant_imgs.append(img)
            print(f"  src: {src[:100]}...")
            # Zeige Parent-Struktur
            parent = img.parent
            if parent:
                print(f"      parent: <{parent.name} class='{parent.get('class', [])}'>")

    # Suche nach Listing-Containern
    print("\n--- Suche nach Listing-Containern ---")

    # Typische Container-Klassen
    container_patterns = [
        '[class*="listing"]',
        '[class*="result"]',
        '[class*="item"]',
        '[class*="card"]',
        '[class*="product"]',
        'article',
    ]

    for pattern in container_patterns:
        containers = soup.select(pattern)
        if containers:
            print(f"\n{pattern}: {len(containers)} gefunden")
            if containers:
                c = containers[0]
                # Hat dieser Container ein Bild?
                img = c.find('img')
                link = c.find('a', href=True)
                print(f"  Erster Container:")
                print(f"    - Hat Bild: {bool(img)}")
                if img:
                    print(f"    - Bild src: {(img.get('src') or img.get('data-src') or '')[:80]}...")
                print(f"    - Hat Link: {bool(link)}")
                if link:
                    print(f"    - Link href: {link.get('href', '')[:80]}...")

    # Suche spezifisch nach Mascus-Strukturen
    print("\n--- Mascus-spezifische Analyse ---")

    # Suche nach Links die auf Listings zeigen
    link_pattern = re.compile(r'/[a-z0-9]{6,10}\.html$', re.IGNORECASE)
    listing_links = [a for a in soup.find_all('a', href=True) if link_pattern.search(a.get('href', ''))]

    print(f"Listing-Links gefunden: {len(listing_links)}")

    if listing_links:
        print("\nAnalyse des ersten Listing-Links:")
        link = listing_links[0]
        print(f"  Link text: {link.get_text(strip=True)[:50]}...")
        print(f"  Link href: {link.get('href', '')}")

        # Suche Bild in verschiedenen Ebenen
        print("\n  Bildsuche:")

        # Im Link selbst
        img = link.find('img')
        print(f"    - Im <a> selbst: {bool(img)}")

        # Im Parent
        parent = link.parent
        for level in range(5):
            if parent:
                img = parent.find('img')
                if img:
                    src = img.get('src') or img.get('data-src') or ''
                    print(f"    - Level {level+1} ({parent.name}): GEFUNDEN!")
                    print(f"      src: {src[:100]}...")
                    break
                parent = parent.parent
            else:
                break

        # Suche nach Geschwister-Elementen
        print("\n  Geschwister-Analyse:")
        parent = link.parent
        if parent:
            siblings = parent.find_all(['img', 'div', 'figure', 'picture'])
            for sib in siblings[:5]:
                if sib.name == 'img':
                    src = sib.get('src') or sib.get('data-src') or ''
                    print(f"    Geschwister <img>: {src[:80]}...")
                elif sib.find('img'):
                    img = sib.find('img')
                    src = img.get('src') or img.get('data-src') or ''
                    print(f"    In <{sib.name}>: {src[:80]}...")

if __name__ == "__main__":
    analyze()

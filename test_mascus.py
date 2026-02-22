#!/usr/bin/env python3
"""
Mascus Test-Scraper
===================
Untersucht die Mascus-Seitenstruktur um herauszufinden,
wie wir die Suchergebnisse extrahieren können.
"""

import requests
from bs4 import BeautifulSoup
import json
import re

# Test-URL (Mascus Slovakia mit MB trac Suche)
TEST_URL = "https://www.mascus.sk/mb%20trac/+/1,relevance,search.html"

# Browser-ähnliche Headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def analyze_mascus():
    print(f"🔍 Lade: {TEST_URL}\n")

    session = requests.Session()
    session.headers.update(HEADERS)

    response = session.get(TEST_URL, timeout=30)
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Content-Length: {len(response.text)} Zeichen\n")

    # HTML speichern für manuelle Analyse
    with open('mascus_response.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print("📄 HTML gespeichert in: mascus_response.html\n")

    soup = BeautifulSoup(response.text, 'html.parser')

    # Suche nach verschiedenen möglichen Listing-Containern
    print("=" * 60)
    print("SUCHE NACH LISTING-CONTAINERN")
    print("=" * 60)

    selectors_to_try = [
        # Gängige Listing-Klassen
        ('article', 'article'),
        ('[class*="listing"]', 'class*="listing"'),
        ('[class*="item"]', 'class*="item"'),
        ('[class*="result"]', 'class*="result"'),
        ('[class*="product"]', 'class*="product"'),
        ('[class*="offer"]', 'class*="offer"'),
        ('[class*="ad"]', 'class*="ad"'),
        ('[class*="card"]', 'class*="card"'),
        # Mascus-spezifische Versuche
        ('[class*="mascus"]', 'class*="mascus"'),
        ('[class*="search"]', 'class*="search"'),
        ('[data-listing]', 'data-listing'),
        ('[data-id]', 'data-id'),
        ('li[class]', 'li[class]'),
        ('div[class*="row"]', 'div class*="row"'),
    ]

    for selector, name in selectors_to_try:
        elements = soup.select(selector)
        if elements:
            print(f"\n✅ {name}: {len(elements)} Elemente gefunden")
            # Zeige erste 2 Elemente
            for i, el in enumerate(elements[:2]):
                classes = el.get('class', [])
                text_preview = el.get_text(strip=True)[:100]
                print(f"   [{i+1}] Klassen: {classes}")
                print(f"       Text: {text_preview}...")

    # Suche nach JSON-Daten im HTML (oft werden Daten als JSON eingebettet)
    print("\n" + "=" * 60)
    print("SUCHE NACH EINGEBETTETEN JSON-DATEN")
    print("=" * 60)

    scripts = soup.find_all('script')
    for i, script in enumerate(scripts):
        if script.string:
            # Suche nach JSON-ähnlichen Strukturen
            if 'listings' in script.string.lower() or 'results' in script.string.lower() or 'items' in script.string.lower():
                print(f"\n📦 Script #{i} enthält möglicherweise Daten:")
                print(f"   Länge: {len(script.string)} Zeichen")
                # Versuche JSON zu extrahieren
                json_matches = re.findall(r'\{[^{}]*"[^"]*"[^{}]*\}', script.string)
                if json_matches:
                    print(f"   Gefundene JSON-Objekte: {len(json_matches)}")

    # Suche nach API-Endpunkten
    print("\n" + "=" * 60)
    print("SUCHE NACH API-ENDPUNKTEN")
    print("=" * 60)

    api_patterns = [
        r'api[./]',
        r'/search',
        r'/listings',
        r'\.json',
        r'fetch\(',
        r'axios',
        r'XMLHttpRequest',
    ]

    for script in scripts:
        if script.string:
            for pattern in api_patterns:
                if re.search(pattern, script.string, re.IGNORECASE):
                    # Finde die Zeile mit dem Pattern
                    for line in script.string.split('\n'):
                        if re.search(pattern, line, re.IGNORECASE):
                            print(f"🔗 Gefunden '{pattern}': {line.strip()[:100]}...")
                            break
                    break

    # Versuche Links zu finden die auf Inserate zeigen
    print("\n" + "=" * 60)
    print("SUCHE NACH INSERAT-LINKS")
    print("=" * 60)

    links = soup.find_all('a', href=True)
    trac_links = [a for a in links if 'trac' in a.get('href', '').lower() or 'trac' in a.get_text(strip=True).lower()]

    print(f"Gefundene Links mit 'trac': {len(trac_links)}")
    for link in trac_links[:5]:
        href = link.get('href', '')
        text = link.get_text(strip=True)[:50]
        print(f"   → {href[:80]}")
        print(f"     Text: {text}")

    # Suche nach Bildern (Inserate haben meist Bilder)
    print("\n" + "=" * 60)
    print("SUCHE NACH PRODUKT-BILDERN")
    print("=" * 60)

    images = soup.find_all('img', src=True)
    product_images = [img for img in images if any(x in img.get('src', '').lower() for x in ['product', 'listing', 'thumb', 'mascus'])]

    print(f"Produkt-Bilder gefunden: {len(product_images)}")
    for img in product_images[:3]:
        src = img.get('src', '')
        alt = img.get('alt', '')[:50]
        print(f"   → {src[:80]}")
        print(f"     Alt: {alt}")

    print("\n" + "=" * 60)
    print("FERTIG - Prüfe mascus_response.html für Details")
    print("=" * 60)

if __name__ == "__main__":
    analyze_mascus()

#!/usr/bin/env python3
"""
Debug-Script: Testen ob Subito.it erreichbar ist und was zurückkommt.
Lokal auf deinem Mac ausführen: python debug_subito.py
"""

import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

urls = [
    ("MB-trac Suche", "https://www.subito.it/annunci-italia/vendita/usato/?q=mb+trac"),
    ("Fendt Suche", "https://www.subito.it/annunci-italia/vendita/usato/?q=fendt+trattore"),
    ("Direktes Inserat", "https://www.subito.it/veicoli-commerciali/trattore-agricolo-fendt-930-siena-637652179.htm"),
]

for name, url in urls:
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"URL: {url}")
    print('='*60)

    try:
        r = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        print(f"Status: {r.status_code}")
        print(f"Final URL: {r.url}")
        print(f"Content-Length: {len(r.text)}")

        soup = BeautifulSoup(r.text, 'html.parser')
        title = soup.find('title')
        print(f"Page Title: {title.text.strip() if title else 'NONE'}")

        # Check for JS-only rendering
        if '__NEXT_DATA__' in r.text:
            print("⚠️  Next.js App — Inhalte werden per JavaScript geladen!")
            # Parse Next.js data
            import json
            script = soup.find('script', id='__NEXT_DATA__')
            if script:
                data = json.loads(script.string)
                print(f"   Next.js Page: {data.get('page', 'unknown')}")
                props = data.get('props', {}).get('pageProps', {})
                # Check for listings in the data
                for key in props:
                    val = props[key]
                    if isinstance(val, list) and len(val) > 0:
                        print(f"   Key '{key}': {len(val)} items")
                    elif isinstance(val, dict) and 'items' in val:
                        print(f"   Key '{key}' has 'items': {len(val['items'])} items")

        # Check all selector types
        selectors = {
            'article': 'article',
            '[class*="item"]': '[class*="item"]',
            '[class*="listing"]': '[class*="listing"]',
            '[class*="result"]': '[class*="result"]',
            '[class*="ad-"]': '[class*="ad-"]',
            '[class*="card"]': '[class*="card"]',
            '[class*="annunci"]': '[class*="annunci"]',
            'a[href*="/annunci"]': 'a[href*="/annunci"]',
        }

        print("\nHTML-Elemente gefunden:")
        for label, sel in selectors.items():
            count = len(soup.select(sel))
            if count > 0:
                print(f"  {label}: {count}")
                # Show first element's classes
                first = soup.select(sel)[0]
                classes = first.get('class', [])
                print(f"    → Klassen: {' '.join(classes) if classes else 'keine'}")

        # Show body text preview
        body_text = soup.get_text()[:500].strip()
        print(f"\nText-Vorschau:\n{body_text[:300]}...")

        # Save full HTML for inspection
        filename = f"debug_subito_{name.replace(' ', '_').lower()}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(r.text)
        print(f"\n💾 Vollständiges HTML gespeichert: {filename}")

    except Exception as e:
        print(f"❌ Fehler: {e}")

print("\n\n" + "="*60)
print("FAZIT")
print("="*60)
print("Wenn du '__NEXT_DATA__' siehst, ist Subito.it eine JS-App.")
print("Dann brauchen wir entweder:")
print("  1. Die Daten aus dem __NEXT_DATA__ JSON extrahieren")
print("  2. Oder einen Headless Browser (Playwright/Selenium)")
print("Schick mir die Ausgabe, dann baue ich den Fix!")

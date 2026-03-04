#!/usr/bin/env python3
"""
Test-Script für den SubitoScraper.
Nutzt die gespeicherte debug HTML-Datei, um den Parser offline zu testen.

Voraussetzung: debug_subito.py wurde vorher ausgeführt und hat
debug_subito_fendt_suche.html und debug_subito_mb-trac_suche.html gespeichert.

Ausführen: python test_subito_scraper.py
"""

import json
from pathlib import Path
from bs4 import BeautifulSoup
from scraper import SubitoScraper

# Test-Config
config = {
    'name': 'Subito.it (Test)',
    'search_url': 'https://www.subito.it/annunci-italia/vendita/usato/?q=fendt+trattore',
    'country_code': 'IT',
}

scraper = SubitoScraper(config)

# Teste beide HTML-Dateien
test_files = [
    'debug_subito_fendt_suche.html',
    'debug_subito_mb-trac_suche.html',
]

for filename in test_files:
    filepath = Path(filename)
    if not filepath.exists():
        print(f"⚠️  {filename} nicht gefunden — überspringe")
        continue

    print(f"\n{'='*60}")
    print(f"Teste: {filename}")
    print('='*60)

    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')

    # __NEXT_DATA__ Methode testen
    next_data_listings = scraper._extract_from_next_data(soup, '2026-03-04T12:00:00')
    print(f"\n📊 __NEXT_DATA__ Methode: {len(next_data_listings)} Inserate gefunden")

    for i, listing in enumerate(next_data_listings[:10]):
        print(f"\n  [{i+1}] {listing.title[:70]}")
        print(f"      Brand: {listing.brand} | Preis: {listing.price} | Land: {listing.country}")
        print(f"      URL: {listing.url[:80]}...")
        if listing.image_url:
            print(f"      Bild: ✅")
        if listing.location:
            print(f"      Ort: {listing.location}")

    # article Methode testen
    article_listings = scraper._extract_from_articles(soup, '2026-03-04T12:00:00')
    print(f"\n📊 Article Methode: {len(article_listings)} Inserate gefunden")

    for i, listing in enumerate(article_listings[:5]):
        print(f"  [{i+1}] {listing.title[:70]} | Brand: {listing.brand}")

print("\n\n✅ Test abgeschlossen!")
print("Wenn Inserate gefunden wurden, funktioniert der Subito-Scraper.")
print("Pushe die Änderungen und starte den GitHub Actions Workflow erneut.")

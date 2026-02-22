#!/usr/bin/env python3
"""
Prüft welche Fahrzeugtypen in Mascus-Ergebnissen sind
"""

from mascus_scraper import MascusScraper
from collections import Counter
import re

scraper = MascusScraper()
listings = scraper.scrape_domain('mascus.de', 'mb trac')

print("\n" + "=" * 60)
print("FAHRZEUGTYPEN IN MASCUS-ERGEBNISSEN")
print("=" * 60)

# Kategorisiere nach Typ
categories = {
    'MB-trac (echte)': [],
    'Unimog': [],
    'LKW (Arocs/Actros/Atego)': [],
    'Sonstige': []
}

# Keywords für Kategorisierung
mbtrac_keywords = ['mb-trac', 'mb trac', 'mbtrac', 'trac 800', 'trac 900', 'trac 1000',
                   'trac 1100', 'trac 1300', 'trac 1500', 'trac 1600', 'trac 1800',
                   'trac 65', 'trac 70', 'trac 700', '-800', '-1000', '-1300', '-1500']
unimog_keywords = ['unimog', 'u1200', 'u1400', 'u1600', 'u400', 'u500', 'u90', 'u421']
lkw_keywords = ['arocs', 'actros', 'atego', 'antos', 'econic', 'axor']

for listing in listings:
    title_lower = listing.title.lower()

    # Prüfe LKW zuerst (höchste Priorität für Ausschluss)
    if any(kw in title_lower for kw in lkw_keywords):
        categories['LKW (Arocs/Actros/Atego)'].append(listing.title)
    # Dann Unimog
    elif any(kw in title_lower for kw in unimog_keywords):
        categories['Unimog'].append(listing.title)
    # Dann echte MB-trac
    elif any(kw in title_lower for kw in mbtrac_keywords):
        categories['MB-trac (echte)'].append(listing.title)
    else:
        categories['Sonstige'].append(listing.title)

print(f"\n📊 Zusammenfassung (von {len(listings)} Inseraten):")
for cat, items in categories.items():
    print(f"\n{'✅' if cat in ['MB-trac (echte)', 'Unimog'] else '❌'} {cat}: {len(items)}")
    for item in items[:5]:
        print(f"      → {item[:55]}...")
    if len(items) > 5:
        print(f"      ... und {len(items) - 5} weitere")

# Zeige was gefiltert werden sollte
to_filter = len(categories['LKW (Arocs/Actros/Atego)']) + len(categories['Sonstige'])
to_keep = len(categories['MB-trac (echte)']) + len(categories['Unimog'])

print(f"\n" + "=" * 60)
print(f"EMPFEHLUNG:")
print(f"  ✅ Behalten: {to_keep} Inserate (MB-trac + Unimog)")
print(f"  ❌ Filtern: {to_filter} Inserate (LKW + Sonstige)")
print("=" * 60)

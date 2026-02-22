#!/usr/bin/env python3
"""
Migriert bestehende Daten und fügt Kategorien hinzu.
"""

import json
from pathlib import Path
from filters import filter_listing

DATA_FILE = Path(__file__).parent / "data" / "mbtrac.json"


def migrate():
    if not DATA_FILE.exists():
        print("Keine Daten zum Migrieren gefunden.")
        return

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        listings = json.load(f)

    updated = 0
    excluded = 0

    for listing_id, listing in list(listings.items()):
        title = listing.get('title', '')
        price = listing.get('price')

        # Filter anwenden
        result = filter_listing(title, price)

        if not result.is_valid:
            # Inserat sollte ausgeschlossen werden
            listing['is_active'] = False
            listing['category'] = 'ausgeschlossen'
            listing['exclude_reason'] = result.reason
            excluded += 1
        else:
            listing['category'] = result.category.value
            listing['price_numeric'] = result.price_numeric
            listing['is_negotiable'] = result.is_negotiable

        updated += 1

    # Speichern
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(listings, f, ensure_ascii=False, indent=2)

    print(f"Migration abgeschlossen:")
    print(f"  - {updated} Inserate aktualisiert")
    print(f"  - {excluded} Inserate als ausgeschlossen markiert")

    # Statistiken
    cats = {}
    for l in listings.values():
        cat = l.get('category', 'unbekannt')
        cats[cat] = cats.get(cat, 0) + 1

    print("\nKategorien:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  - {cat}: {count}")


if __name__ == "__main__":
    migrate()

#!/usr/bin/env python3
"""
Bereinigt Duplikate aus der Datenbank basierend auf Titel + Preis.
"""

import json
import hashlib
import re
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent / "data" / "mbtrac.json"

def normalize_title(title: str) -> str:
    """Normalisiert Titel für Duplikaterkennung"""
    normalized = title.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r'[^\w\s]', '', normalized)
    return normalized

def generate_content_hash(title: str, price_numeric: float = None) -> str:
    """Generiert Hash aus normalisiertem Titel + Preis"""
    normalized = normalize_title(title)
    price_rounded = round(price_numeric / 100) * 100 if price_numeric else 0
    content = f"{normalized}|{price_rounded}"
    return hashlib.md5(content.encode()).hexdigest()[:16]

def main():
    print("=" * 60)
    print("DUPLIKAT-BEREINIGUNG")
    print("=" * 60)

    # Lade Datenbank
    with open(DB_PATH, 'r', encoding='utf-8') as f:
        listings = json.load(f)

    print(f"\nVorher: {len(listings)} Einträge")

    # Gruppiere nach Content-Hash
    by_hash = defaultdict(list)
    for lid, listing in listings.items():
        content_hash = generate_content_hash(
            listing.get('title', ''),
            listing.get('price_numeric')
        )
        by_hash[content_hash].append((lid, listing))

    # Finde Duplikate
    duplicates = {h: items for h, items in by_hash.items() if len(items) > 1}
    print(f"Duplikat-Gruppen gefunden: {len(duplicates)}")

    # Zähle zu löschende Einträge
    to_delete = []
    to_keep = {}

    for content_hash, items in by_hash.items():
        if len(items) == 1:
            # Kein Duplikat
            lid, listing = items[0]
            to_keep[lid] = listing
        else:
            # Duplikate - behalte den ältesten (nach first_seen)
            sorted_items = sorted(items, key=lambda x: x[1].get('first_seen', ''))

            # Behalte den ersten
            keep_id, keep_listing = sorted_items[0]

            # Sammle alternative URLs
            alt_urls = []
            for lid, listing in sorted_items[1:]:
                alt_urls.append(listing['url'])
                to_delete.append(lid)

            # Füge alt_urls hinzu
            keep_listing['alt_urls'] = alt_urls
            to_keep[keep_id] = keep_listing

    print(f"Zu löschen: {len(to_delete)} Duplikate")
    print(f"Nachher: {len(to_keep)} eindeutige Einträge")

    # Zeige Beispiele
    if duplicates:
        print("\nBeispiele von zusammengeführten Duplikaten:")
        for i, (h, items) in enumerate(list(duplicates.items())[:5]):
            title = items[0][1].get('title', '')[:50]
            platforms = [item[1].get('platform', '') for item in items]
            print(f"  {i+1}. \"{title}...\"")
            print(f"     → {len(items)} Einträge auf: {', '.join(platforms[:5])}{'...' if len(platforms) > 5 else ''}")

    # Speichere bereinigte Datenbank
    print("\n" + "=" * 60)
    confirm = input("Bereinigung durchführen? (j/n): ")

    if confirm.lower() == 'j':
        # Backup erstellen
        backup_path = DB_PATH.with_suffix('.backup.json')
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(listings, f, ensure_ascii=False, indent=2)
        print(f"Backup erstellt: {backup_path}")

        # Bereinigte DB speichern
        with open(DB_PATH, 'w', encoding='utf-8') as f:
            json.dump(to_keep, f, ensure_ascii=False, indent=2)
        print(f"✅ Datenbank bereinigt: {len(to_keep)} Einträge")
    else:
        print("Abgebrochen.")


if __name__ == "__main__":
    main()

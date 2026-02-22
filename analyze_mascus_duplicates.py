#!/usr/bin/env python3
"""
Analyse: Sind Mascus-Inserate auf allen Länderseiten gleich?
"""

from mascus_scraper import MascusScraper
from collections import defaultdict

def analyze_duplicates():
    scraper = MascusScraper()

    # Teste 5 verschiedene Länder
    test_domains = ['mascus.de', 'mascus.nl', 'mascus.fr', 'mascus.it', 'mascus.pl']

    all_listings = {}  # URL -> Liste von Domains wo gefunden
    domain_listings = {}  # Domain -> Liste von URLs

    print("=" * 60)
    print("DUPLIKAT-ANALYSE: Mascus Länderseiten")
    print("=" * 60)

    for domain in test_domains:
        listings = scraper.scrape_domain(domain, 'mb trac')
        domain_listings[domain] = []

        for listing in listings:
            url = listing.url
            # Normalisiere URL (entferne Domain-Teil für Vergleich)
            # z.B. /landmaschinen/traktoren/mb-trac-1000/abc123.html
            url_path = url.split('.html')[0].split('/')[-1] if '.html' in url else url

            if url_path not in all_listings:
                all_listings[url_path] = []
            all_listings[url_path].append(domain)
            domain_listings[domain].append(url_path)

    print("\n" + "=" * 60)
    print("ERGEBNISSE")
    print("=" * 60)

    # Zähle wie oft jedes Inserat vorkommt
    occurrence_counts = defaultdict(int)
    for url_path, domains in all_listings.items():
        occurrence_counts[len(domains)] += 1

    print(f"\n📊 Inserate nach Häufigkeit:")
    for count in sorted(occurrence_counts.keys(), reverse=True):
        num_listings = occurrence_counts[count]
        print(f"   Auf {count} Seiten: {num_listings} Inserate")

    total_unique = len(all_listings)
    total_found = sum(len(listings) for listings in domain_listings.values())

    print(f"\n📈 Zusammenfassung:")
    print(f"   Domains getestet: {len(test_domains)}")
    print(f"   Inserate gefunden (gesamt): {total_found}")
    print(f"   Einzigartige Inserate: {total_unique}")
    print(f"   Duplikat-Rate: {((total_found - total_unique) / total_found * 100):.1f}%")

    # Zeige Beispiele für Duplikate
    print(f"\n📋 Beispiele für Duplikate (auf allen {len(test_domains)} Seiten):")
    duplicates_on_all = [url for url, domains in all_listings.items() if len(domains) == len(test_domains)]
    for url_path in duplicates_on_all[:5]:
        print(f"   → {url_path}")

    # Zeige Beispiele für einzigartige Inserate
    print(f"\n📋 Beispiele für einzigartige Inserate (nur 1 Seite):")
    unique_listings = [(url, domains[0]) for url, domains in all_listings.items() if len(domains) == 1]
    for url_path, domain in unique_listings[:5]:
        print(f"   → {url_path} (nur auf {domain})")

    print("\n" + "=" * 60)
    print("EMPFEHLUNG")
    print("=" * 60)

    if total_unique < total_found * 0.2:  # Weniger als 20% einzigartig
        print("⚠️  Mascus zeigt auf allen Länderseiten dieselben internationalen Ergebnisse.")
        print("   → Nur EINE Mascus-Domain scrapen reicht aus!")
        print("   → Empfehlung: mascus.com oder mascus.de verwenden")
    else:
        print("✅ Mascus zeigt teilweise länderspezifische Ergebnisse.")
        print("   → Mehrere Domains scrapen macht Sinn")

if __name__ == "__main__":
    analyze_duplicates()

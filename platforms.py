"""
Traktor-Scraper - Europäische Plattform-Datenbank
Konsolidierte Liste aller Plattformen für gebrauchte Landmaschinen/Traktoren in Europa.
Unterstützt MB-trac und weitere Marken (definiert in brands.py).
"""

from brands import BRANDS

# ==========================================
# ZENTRALE SUCHBEGRIFF-KONFIGURATION
# ==========================================

# Haupt-Suchbegriffe (verschiedene Schreibweisen)
SEARCH_TERMS_PRIMARY = [
    "MB-trac",      # Offizielle Schreibweise
    "MB Trac",      # Häufigste Variante in Inseraten
    "MB trac",      # Kleinschreibung
    "Mb Trac",      # Mixed Case
    "MBtrac",       # Zusammengeschrieben
    "Mercedes Trac", # Mit vollem Markennamen
]

# Modellnummern (für spezifische Suche)
SEARCH_TERMS_MODELS = [
    "MB-trac 65",
    "MB-trac 70",
    "MB-trac 700",
    "MB-trac 800",
    "MB-trac 900",
    "MB-trac 1000",
    "MB-trac 1100",
    "MB-trac 1300",
    "MB-trac 1400",
    "MB-trac 1500",
    "MB-trac 1600",
    "MB-trac 1800",
]

# Baureihen-Nummern (intern)
SEARCH_TERMS_SERIES = [
    "440",  # Kleine Baureihe (65/70)
    "441",  # Mittlere Baureihe (700-1000)
    "442",  # Große Baureihe (1100-1500)
    "443",  # Große Baureihe (1300-1800)
]

# Verwandte Fahrzeuge (Werner Forstmaschinen übernahm MB-trac Technologie)
SEARCH_TERMS_RELATED = [
    "WF Trac",
    "Werner Trac",
]

# Standard-Suchbegriffe für die meisten Plattformen
DEFAULT_SEARCH_TERMS = [
    # Korrekte Schreibweisen
    "MB-trac", "MB Trac", "MB trac", "MBtrac",
    "Mercedes Trac", "Mercedes-Benz Trac",
]

# Häufige Falschschreibungen (für Plattformen mit guter Suche)
MISSPELLED_SEARCH_TERMS = [
    "MB Track", "MB-Track", "MBTrack",      # Track statt Trac
    "MB Trak", "MB-Trak", "MBTrak",         # Trak (phonetisch)
    "Mercedes Track", "Mercedes Trak",
]

# Erweiterte Suchbegriffe für Plattformen mit guter Suche
EXTENDED_SEARCH_TERMS = DEFAULT_SEARCH_TERMS + MISSPELLED_SEARCH_TERMS + [
    "MB-trac 1600", "MB-trac 1800", "WF Trac", "Unimog"
]

# ==========================================
# ALLE VERFÜGBAREN MARKEN (aus brands.py)
# ==========================================
ALL_BRAND_KEYS = [k for k in BRANDS.keys() if k != "mb_trac"]

PLATFORMS = {
    # ==========================================
    # DACH + BENELUX
    # ==========================================
    "DE": {
        "country": "Deutschland",
        "platforms": [
            {
                "name": "eBay Kleinanzeigen",
                "url": "https://www.kleinanzeigen.de",
                # Suche nach "mb trac" (ohne Bindestrich, häufigste Schreibweise)
                "search_url": "https://www.kleinanzeigen.de/s-mb-trac/k0",
                "type": "kleinanzeigen",
                "search_terms": DEFAULT_SEARCH_TERMS,
                "priority": "high",
                "brand_search_urls": {
                    "fendt": "https://www.kleinanzeigen.de/s-fendt-traktor/k0",
                    "john_deere": "https://www.kleinanzeigen.de/s-john-deere-traktor/k0",
                    "deutz": "https://www.kleinanzeigen.de/s-deutz-traktor/k0",
                    "ihc": "https://www.kleinanzeigen.de/s-ihc-traktor/k0",
                    "case_ih": "https://www.kleinanzeigen.de/s-case-ih-traktor/k0",
                    "fiat": "https://www.kleinanzeigen.de/s-fiat-traktor/k0",
                    "new_holland": "https://www.kleinanzeigen.de/s-new-holland-traktor/k0",
                    "claas_xerion": "https://www.kleinanzeigen.de/s-claas-xerion/k0",
                }
            },
            {
                # Zweite Suche für Modell 1600 (oft separat gelistet)
                "name": "eBay Kleinanzeigen (1600)",
                "url": "https://www.kleinanzeigen.de",
                "search_url": "https://www.kleinanzeigen.de/s-trac-1600/k0",
                "type": "kleinanzeigen",
                "search_terms": ["MB-trac 1600", "Trac 1600"],
                "priority": "medium"
            },
            {
                "name": "Traktorpool.de",
                "url": "https://www.traktorpool.de",
                "search_url": "https://www.traktorpool.de/gebraucht/a-Traktoren/24/b-Traktoren/95/c-MercedesBenz/337/model/MB+Trac/",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            },
            {
                "name": "Technikboerse",
                "url": "https://www.technikboerse.com",
                "search_url": "https://www.technikboerse.com/en/marke/mercedes-benz-791",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB-trac", "Mercedes-Benz"],
                "priority": "high"
            },
            {
                "name": "Landwirt.com",
                "url": "https://www.landwirt.com",
                "search_url": "https://www.landwirt.com/en/classifieds/tractors/agricultural-tractors/mercedes",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB-trac"],
                "priority": "high"
            },
            {
                "name": "Mascus.de",
                "url": "https://www.mascus.de",
                "search_url": "https://www.mascus.de/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high",
                "brand_search_urls": {
                    "fendt": "https://www.mascus.de/fendt/+/1,relevance,search.html",
                    "john_deere": "https://www.mascus.de/john%20deere/+/1,relevance,search.html",
                    "deutz": "https://www.mascus.de/deutz/+/1,relevance,search.html",
                    "ihc": "https://www.mascus.de/ihc/+/1,relevance,search.html",
                    "case_ih": "https://www.mascus.de/case%20ih/+/1,relevance,search.html",
                    "fiat": "https://www.mascus.de/fiat%20traktor/+/1,relevance,search.html",
                    "new_holland": "https://www.mascus.de/new%20holland%20tm/+/1,relevance,search.html",
                    "claas_xerion": "https://www.mascus.de/claas%20xerion/+/1,relevance,search.html",
                }
            },
            {
                "name": "TruckScout24",
                "url": "https://www.truckscout24.de",
                "search_url": "https://www.truckscout24.de/landmaschinen/gebraucht/alle/mercedes-benz/mb-trac",
                "type": "fahrzeug_portal",
                "search_terms": ["MB-trac"],
                "priority": "medium"
            },
            {
                "name": "Agriaffaires",
                "url": "https://www.agriaffaires.de",
                "search_url": "https://www.agriaffaires.de/gebrauchte/landmaschinen/1-deutschland.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB-trac"],
                "priority": "medium"
            }
        ]
    },
    "AT": {
        "country": "Österreich",
        "platforms": [
            {
                "name": "Traktorpool.at",
                "url": "https://www.traktorpool.at",
                "search_url": "https://www.traktorpool.at/gebraucht/a-Traktoren/24/c-MercedesBenz/337/",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            },
            {
                "name": "Willhaben.at",
                "url": "https://www.willhaben.at",
                "search_url": "https://www.willhaben.at/iad/kaufen-und-verkaufen/marktplatz?keyword=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB Trac", "MB-trac"],
                "priority": "high",
                "brand_search_urls": {
                    "fendt": "https://www.willhaben.at/iad/kaufen-und-verkaufen/marktplatz?keyword=fendt+traktor",
                    "john_deere": "https://www.willhaben.at/iad/kaufen-und-verkaufen/marktplatz?keyword=john+deere+traktor",
                    "deutz": "https://www.willhaben.at/iad/kaufen-und-verkaufen/marktplatz?keyword=deutz+traktor",
                    "ihc": "https://www.willhaben.at/iad/kaufen-und-verkaufen/marktplatz?keyword=ihc+traktor",
                    "case_ih": "https://www.willhaben.at/iad/kaufen-und-verkaufen/marktplatz?keyword=case+ih+traktor",
                }
            },
            {
                "name": "Maschinensucher.at",
                "url": "https://www.maschinensucher.at",
                "search_url": "https://www.maschinensucher.at/mss/mb+trac",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "medium"
            }
        ]
    },
    "CH": {
        "country": "Schweiz",
        "platforms": [
            {
                "name": "Traktorpool.ch",
                "url": "https://www.traktorpool.ch",
                "search_url": "https://www.traktorpool.ch/gebraucht/a-Traktoren/24/c-MercedesBenz/337/",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            },
            {
                "name": "Ricardo.ch",
                "url": "https://www.ricardo.ch",
                "search_url": "https://www.ricardo.ch/de/s/mb%20trac/",
                "type": "auktion",
                "search_terms": ["MB-trac", "MB Trac"],
                "priority": "high"
            },
            {
                "name": "Tutti.ch",
                "url": "https://www.tutti.ch",
                "search_url": "https://www.tutti.ch/de/q/suche/Ak6dtYiB0cmFjwJTAwMDA?sorting=newest&page=1&query=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB Trac"],
                "priority": "medium"
            }
        ]
    },
    "NL": {
        "country": "Niederlande",
        "platforms": [
            {
                "name": "Marktplaats",
                "url": "https://www.marktplaats.nl",
                "search_url": "https://www.marktplaats.nl/q/mb+trac/",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "Mercedes trac"],
                "priority": "high",
                "brand_search_urls": {
                    "fendt": "https://www.marktplaats.nl/q/fendt+traktor/",
                    "john_deere": "https://www.marktplaats.nl/q/john+deere+traktor/",
                    "deutz": "https://www.marktplaats.nl/q/deutz+traktor/",
                    "ihc": "https://www.marktplaats.nl/q/ihc+traktor/",
                }
            },
            {
                "name": "TrucksNL",
                "url": "https://www.trucksnl.com",
                "search_url": "https://www.trucksnl.com/farm-tractors/mb-trac",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "medium"
            },
            {
                "name": "Mascus.nl",
                "url": "https://www.mascus.nl",
                "search_url": "https://www.mascus.nl/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            }
        ]
    },
    "BE": {
        "country": "Belgien",
        "platforms": [
            {
                "name": "2dehands.be",
                "url": "https://www.2dehands.be",
                "search_url": "https://www.2dehands.be/q/mb+trac/",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac"],
                "priority": "high"
            },
            {
                "name": "Mascus.be",
                "url": "https://www.mascus.be",
                "search_url": "https://www.mascus.be/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            }
        ]
    },

    # ==========================================
    # NORDEUROPA
    # ==========================================
    "NO": {
        "country": "Norwegen",
        "platforms": [
            {
                "name": "Finn.no",
                "url": "https://www.finn.no",
                "search_url": "https://www.finn.no/bap/forsale/search.html?q=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "MB-trac", "traktor"],
                "priority": "high"
            },
            {
                "name": "Mascus.no",
                "url": "https://www.mascus.no",
                "search_url": "https://www.mascus.no/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac", "traktor"],
                "priority": "high"
            }
        ]
    },
    "SE": {
        "country": "Schweden",
        "platforms": [
            {
                "name": "Blocket.se",
                "url": "https://www.blocket.se",
                "search_url": "https://www.blocket.se/annonser/hela_sverige?q=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "traktor"],
                "priority": "high"
            },
            {
                "name": "Traktorpool.se",
                "url": "https://www.traktorpool.se",
                "search_url": "https://www.traktorpool.se/begagnat/a-Traktorer/24/c-MercedesBenz/337/",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            },
            {
                "name": "Mascus.se",
                "url": "https://www.mascus.se",
                "search_url": "https://www.mascus.se/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "medium"
            }
        ]
    },
    "FI": {
        "country": "Finnland",
        "platforms": [
            {
                "name": "Nettikone.com",
                "url": "https://www.nettikone.com",
                "search_url": "https://www.nettikone.com/maatalouskoneet/traktorit",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB trac", "traktor"],
                "priority": "high"
            },
            {
                "name": "Traktorpool.fi",
                "url": "https://www.traktorpool.fi",
                "search_url": "https://www.traktorpool.fi/käytetty/a-Traktorit/24/",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            },
            {
                "name": "Mascus.fi",
                "url": "https://www.mascus.fi",
                "search_url": "https://www.mascus.fi/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "medium"
            }
        ]
    },
    "DK": {
        "country": "Dänemark",
        "platforms": [
            {
                "name": "DBA.dk",
                "url": "https://www.dba.dk",
                "search_url": "https://www.dba.dk/soeg/?soeg=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "traktor"],
                "priority": "high"
            },
            {
                "name": "Traktorpool.dk",
                "url": "https://www.traktorpool.dk",
                "search_url": "https://www.traktorpool.dk/brugt/a-Traktorer/24/c-MercedesBenz/337/model/MB+Trac/",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            },
            {
                "name": "Mascus.dk",
                "url": "https://www.mascus.dk",
                "search_url": "https://www.mascus.dk/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            }
        ]
    },

    # ==========================================
    # WESTEUROPA (UK, IE, FR)
    # ==========================================
    "UK": {
        "country": "Großbritannien",
        "platforms": [
            {
                "name": "Gumtree",
                "url": "https://www.gumtree.com",
                "search_url": "https://www.gumtree.com/search?q=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "Mercedes trac"],
                "priority": "high"
            },
            {
                "name": "Mascus UK",
                "url": "https://www.mascus.co.uk",
                "search_url": "https://www.mascus.co.uk/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            },
            {
                "name": "Auto Trader Farm",
                "url": "https://www.autotrader.co.uk/farm",
                "search_url": "https://www.autotrader.co.uk/farm",
                "type": "fahrzeug_portal",
                "search_terms": ["MB trac", "tractor"],
                "priority": "medium"
            },
            {
                "name": "Farmers Weekly",
                "url": "https://classified.fwi.co.uk",
                "search_url": "https://classified.fwi.co.uk/",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB trac"],
                "priority": "medium"
            }
        ]
    },
    "IE": {
        "country": "Irland",
        "platforms": [
            {
                "name": "DoneDeal",
                "url": "https://www.donedeal.ie",
                "search_url": "https://www.donedeal.ie/farming?words=mb%20trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "tractor"],
                "priority": "high"
            },
            {
                "name": "Mascus Ireland",
                "url": "https://www.mascus.ie",
                "search_url": "https://www.mascus.ie/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            },
            {
                "name": "Farm And Plant",
                "url": "https://www.farmandplant.ie",
                "search_url": "https://www.farmandplant.ie/",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB trac"],
                "priority": "medium"
            }
        ]
    },
    "FR": {
        "country": "Frankreich",
        "platforms": [
            {
                "name": "Leboncoin",
                "url": "https://www.leboncoin.fr",
                "search_url": "https://www.leboncoin.fr/recherche?text=mb%20trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "tracteur Mercedes"],
                "priority": "high"
            },
            {
                "name": "Agriaffaires FR",
                "url": "https://www.agriaffaires.com",
                "search_url": "https://www.agriaffaires.com/occasion/tracteur-agricole/1/m.ht",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB trac", "tracteur"],
                "priority": "high"
            },
            {
                "name": "Mascus.fr",
                "url": "https://www.mascus.fr",
                "search_url": "https://www.mascus.fr/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            }
        ]
    },

    # ==========================================
    # SÜDEUROPA
    # ==========================================
    "ES": {
        "country": "Spanien",
        "platforms": [
            {
                "name": "MilAnuncios",
                "url": "https://www.milanuncios.com",
                "search_url": "https://www.milanuncios.com/anuncios/mb-trac.htm",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "tractor Mercedes"],
                "priority": "high"
            },
            {
                "name": "Wallapop",
                "url": "https://www.wallapop.com",
                "search_url": "https://es.wallapop.com/app/search?keywords=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac"],
                "priority": "medium"
            },
            {
                "name": "Mascus.es",
                "url": "https://www.mascus.es",
                "search_url": "https://www.mascus.es/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            }
        ]
    },
    "PT": {
        "country": "Portugal",
        "platforms": [
            {
                "name": "OLX Portugal",
                "url": "https://www.olx.pt",
                "search_url": "https://www.olx.pt/ads/q-mb-trac/",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "trator Mercedes"],
                "priority": "high"
            },
            {
                "name": "CustoJusto",
                "url": "https://www.custojusto.pt",
                "search_url": "https://www.custojusto.pt/portugal/q/mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac"],
                "priority": "medium"
            }
        ]
    },
    "IT": {
        "country": "Italien",
        "platforms": [
            {
                "name": "Subito.it",
                "url": "https://www.subito.it",
                "search_url": "https://www.subito.it/annunci-italia/vendita/usato/?q=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "trattore Mercedes"],
                "priority": "high",
                "brand_search_urls": {
                    "fendt": "https://www.subito.it/annunci-italia/vendita/usato/?q=fendt+trattore",
                    "john_deere": "https://www.subito.it/annunci-italia/vendita/usato/?q=john+deere+trattore",
                    "deutz": "https://www.subito.it/annunci-italia/vendita/usato/?q=deutz+trattore",
                    "ihc": "https://www.subito.it/annunci-italia/vendita/usato/?q=ihc+trattore",
                    "case_ih": "https://www.subito.it/annunci-italia/vendita/usato/?q=case+ih+trattore",
                    "fiat": "https://www.subito.it/annunci-italia/vendita/usato/?q=fiat+trattore",
                    "new_holland": "https://www.subito.it/annunci-italia/vendita/usato/?q=new+holland+trattore",
                    "claas_xerion": "https://www.subito.it/annunci-italia/vendita/usato/?q=claas+xerion",
                }
            },
            {
                "name": "Mascus.it",
                "url": "https://www.mascus.it",
                "search_url": "https://www.mascus.it/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            }
        ]
    },
    "GR": {
        "country": "Griechenland",
        "platforms": [
            {
                "name": "Car.gr",
                "url": "https://www.car.gr",
                "search_url": "https://www.car.gr/classifieds/tractors/?category=15420&variant=trac",
                "type": "fahrzeug_portal",
                "search_terms": ["MB trac", "τρακτέρ"],
                "priority": "high"
            },
            {
                "name": "Mascus.gr",
                "url": "https://www.mascus.gr",
                "search_url": "https://www.mascus.gr/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "medium"
            }
        ]
    },

    # ==========================================
    # OSTEUROPA
    # ==========================================
    "PL": {
        "country": "Polen",
        "platforms": [
            {
                "name": "OLX.pl",
                "url": "https://www.olx.pl",
                "search_url": "https://www.olx.pl/rolnictwo/ciagniki/q-mb-trac/",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "ciągnik Mercedes"],
                "priority": "high"
            },
            {
                "name": "Allegro.pl",
                "url": "https://allegro.pl",
                "search_url": "https://allegro.pl/listing?string=mb%20trac",
                "type": "auktion",
                "search_terms": ["MB trac"],
                "priority": "high"
            },
            {
                "name": "Mascus.pl",
                "url": "https://www.mascus.pl",
                "search_url": "https://www.mascus.pl/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            },
            {
                "name": "Otomoto.pl",
                "url": "https://www.otomoto.pl",
                "search_url": "https://www.otomoto.pl/maszyny-rolnicze/traktory",
                "type": "fahrzeug_portal",
                "search_terms": ["MB trac"],
                "priority": "medium"
            }
        ]
    },
    "CZ": {
        "country": "Tschechien",
        "platforms": [
            {
                "name": "Bazos.cz",
                "url": "https://www.bazos.cz",
                "search_url": "https://stroje.bazos.cz/?hledat=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "traktor"],
                "priority": "high"
            },
            {
                "name": "Mascus.cz",
                "url": "https://www.mascus.cz",
                "search_url": "https://www.mascus.cz/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            },
            {
                "name": "Sbazar.cz",
                "url": "https://www.sbazar.cz",
                "search_url": "https://www.sbazar.cz/hledej/mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac"],
                "priority": "medium"
            }
        ]
    },
    "SK": {
        "country": "Slowakei",
        "platforms": [
            {
                "name": "Bazos.sk",
                "url": "https://www.bazos.sk",
                "search_url": "https://stroje.bazos.sk/?hladat=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "traktor"],
                "priority": "high"
            },
            {
                "name": "Mascus.sk",
                "url": "https://www.mascus.sk",
                "search_url": "https://www.mascus.sk/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            }
        ]
    },
    "HU": {
        "country": "Ungarn",
        "platforms": [
            {
                "name": "Jófogás",
                "url": "https://www.jofogas.hu",
                "search_url": "https://www.jofogas.hu/magyarorszag?q=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "traktor"],
                "priority": "high"
            },
            {
                "name": "Mascus.hu",
                "url": "https://www.mascus.hu",
                "search_url": "https://www.mascus.hu/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            },
            {
                "name": "Traktorpool.hu",
                "url": "https://www.traktorpool.hu",
                "search_url": "https://www.traktorpool.hu/",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "medium"
            }
        ]
    },
    "RO": {
        "country": "Rumänien",
        "platforms": [
            {
                "name": "OLX.ro",
                "url": "https://www.olx.ro",
                "search_url": "https://www.olx.ro/oferte/q-mb-trac/",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "tractor Mercedes"],
                "priority": "high"
            },
            {
                "name": "Autovit.ro",
                "url": "https://www.autovit.ro",
                "search_url": "https://www.autovit.ro/utilaje-agricole/tractoare",
                "type": "fahrzeug_portal",
                "search_terms": ["MB trac"],
                "priority": "medium"
            },
            {
                "name": "Mascus.ro",
                "url": "https://www.mascus.ro",
                "search_url": "https://www.mascus.ro/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            }
        ]
    },
    "BG": {
        "country": "Bulgarien",
        "platforms": [
            {
                "name": "Mobile.bg",
                "url": "https://www.mobile.bg",
                "search_url": "https://www.mobile.bg/obiavi/agro/traktor",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "трактор"],
                "priority": "high"
            },
            {
                "name": "OLX.bg",
                "url": "https://www.olx.bg",
                "search_url": "https://www.olx.bg/ads/q-mb-trac/",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac"],
                "priority": "high"
            },
            {
                "name": "Auto.bg",
                "url": "https://www.auto.bg",
                "search_url": "https://www.auto.bg/obiavi/agro/traktor",
                "type": "fahrzeug_portal",
                "search_terms": ["MB trac"],
                "priority": "medium"
            }
        ]
    },
    "UA": {
        "country": "Ukraine",
        "platforms": [
            {
                "name": "OLX.ua",
                "url": "https://www.olx.ua",
                "search_url": "https://www.olx.ua/uk/transport/selhoztehnika/q-mb-trac/",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "трактор"],
                "priority": "high"
            },
            {
                "name": "AGRO.RIA",
                "url": "https://agro.ria.com",
                "search_url": "https://agro.ria.com/",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB trac", "трактор"],
                "priority": "high"
            }
        ]
    },

    # ==========================================
    # BALKAN
    # ==========================================
    "HR": {
        "country": "Kroatien",
        "platforms": [
            {
                "name": "Njuskalo.hr",
                "url": "https://www.njuskalo.hr",
                "search_url": "https://www.njuskalo.hr/traktori?keywords=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "traktor"],
                "priority": "high"
            },
            {
                "name": "Mascus.hr",
                "url": "https://www.mascus.hr",
                "search_url": "https://www.mascus.hr/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            }
        ]
    },
    "RS": {
        "country": "Serbien",
        "platforms": [
            {
                "name": "KupujemProdajem",
                "url": "https://www.kupujemprodajem.com",
                "search_url": "https://www.kupujemprodajem.com/pretraga?keywords=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "traktor"],
                "priority": "high"
            },
            {
                "name": "Polovniautomobili.com",
                "url": "https://www.polovniautomobili.com",
                "search_url": "https://www.polovniautomobili.com/traktori",
                "type": "fahrzeug_portal",
                "search_terms": ["MB trac"],
                "priority": "high"
            },
            {
                "name": "Mascus.rs",
                "url": "https://www.mascus.rs",
                "search_url": "https://www.mascus.rs/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "medium"
            }
        ]
    },
    "SI": {
        "country": "Slowenien",
        "platforms": [
            {
                "name": "Bolha.com",
                "url": "https://www.bolha.com",
                "search_url": "https://www.bolha.com/iskanje?q=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "traktor"],
                "priority": "high"
            },
            {
                "name": "Avto.net",
                "url": "https://www.avto.net",
                "search_url": "https://www.avto.net/Ads/results.asp",
                "type": "fahrzeug_portal",
                "search_terms": ["MB trac"],
                "priority": "medium"
            },
            {
                "name": "Mascus.si",
                "url": "https://www.mascus.si",
                "search_url": "https://www.mascus.si/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            }
        ]
    },

    # ==========================================
    # BALTIKUM
    # ==========================================
    "EE": {
        "country": "Estland",
        "platforms": [
            {
                "name": "Osta.ee",
                "url": "https://www.osta.ee",
                "search_url": "https://www.osta.ee/search/?q=mb+trac",
                "type": "auktion",
                "search_terms": ["MB trac", "traktor"],
                "priority": "high"
            },
            {
                "name": "Mascus.ee",
                "url": "https://www.mascus.ee",
                "search_url": "https://www.mascus.ee/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            },
            {
                "name": "Auto24.ee",
                "url": "https://www.auto24.ee",
                "search_url": "https://www.auto24.ee/",
                "type": "fahrzeug_portal",
                "search_terms": ["MB trac"],
                "priority": "medium"
            }
        ]
    },
    "LV": {
        "country": "Lettland",
        "platforms": [
            {
                "name": "SS.lv",
                "url": "https://www.ss.lv",
                "search_url": "https://www.ss.lv/lv/agriculture/agricultural-machinery/tractors/",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "traktori"],
                "priority": "high"
            },
            {
                "name": "Mascus.lv",
                "url": "https://www.mascus.lv",
                "search_url": "https://www.mascus.lv/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            }
        ]
    },
    "LT": {
        "country": "Litauen",
        "platforms": [
            {
                "name": "Skelbiu.lt",
                "url": "https://www.skelbiu.lt",
                "search_url": "https://www.skelbiu.lt/skelbimai/?keywords=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "traktoriai"],
                "priority": "high"
            },
            {
                "name": "Autoplius.lt",
                "url": "https://www.autoplius.lt",
                "search_url": "https://www.autoplius.lt/skelbimai/naudoti-traktoriai",
                "type": "fahrzeug_portal",
                "search_terms": ["MB trac"],
                "priority": "high"
            },
            {
                "name": "Mascus.lt",
                "url": "https://www.mascus.lt",
                "search_url": "https://www.mascus.lt/mb%20trac/+/1,relevance,search.html",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB Trac"],
                "priority": "high"
            }
        ]
    },

    # ==========================================
    # INTERNATIONALE MÄRKTE (außerhalb Europa)
    # ==========================================
    "ZA": {
        "country": "Südafrika",
        "platforms": [
            {
                "name": "AgriMag.co.za",
                "url": "https://www.agrimag.co.za",
                "search_url": "https://www.agrimag.co.za/tractors?q=mb+trac",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB trac", "Mercedes trac"],
                "priority": "high"
            },
            {
                "name": "Gumtree.co.za",
                "url": "https://www.gumtree.co.za",
                "search_url": "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac"],
                "priority": "medium"
            },
            {
                "name": "TruckTrader.co.za",
                "url": "https://www.trucktrader.co.za",
                "search_url": "https://www.trucktrader.co.za/search?q=mb+trac",
                "type": "fahrzeug_portal",
                "search_terms": ["MB trac"],
                "priority": "medium"
            }
        ]
    },
    "AU": {
        "country": "Australien",
        "platforms": [
            {
                "name": "Machines4U.com.au",
                "url": "https://www.machines4u.com.au",
                "search_url": "https://www.machines4u.com.au/search/Tractors/mb-trac",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB trac", "Mercedes trac"],
                "priority": "high"
            },
            {
                "name": "FarmTrader.com.au",
                "url": "https://www.farmtrader.com.au",
                "search_url": "https://www.farmtrader.com.au/search?q=mb+trac",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB trac"],
                "priority": "high"
            },
            {
                "name": "Gumtree.com.au",
                "url": "https://www.gumtree.com.au",
                "search_url": "https://www.gumtree.com.au/s-farming-vehicles/mb+trac/k0c18626",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac"],
                "priority": "medium"
            },
            {
                "name": "TradeFarmMachinery.com.au",
                "url": "https://www.tradefarmingmachinery.com.au",
                "search_url": "https://www.tradefarmingmachinery.com.au/search?q=mb+trac",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB trac"],
                "priority": "medium"
            }
        ]
    },
    "NZ": {
        "country": "Neuseeland",
        "platforms": [
            {
                "name": "TradeMe.co.nz",
                "url": "https://www.trademe.co.nz",
                "search_url": "https://www.trademe.co.nz/a/motors/farming/tractors/search?search_string=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac"],
                "priority": "high"
            }
        ]
    },
    "US": {
        "country": "USA",
        "platforms": [
            {
                "name": "TractorHouse.com",
                "url": "https://www.tractorhouse.com",
                "search_url": "https://www.tractorhouse.com/listings/farm-equipment/for-sale/list?keywords=mb%20trac",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB trac", "Mercedes trac"],
                "priority": "high"
            },
            {
                "name": "MachineryTrader.com",
                "url": "https://www.machinerytrader.com",
                "search_url": "https://www.machinerytrader.com/listings/farm-equipment/for-sale/list?keywords=mb%20trac",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB trac"],
                "priority": "high"
            },
            {
                "name": "FastlineAuctions.com",
                "url": "https://www.fastline.com",
                "search_url": "https://www.fastline.com/search?q=mb+trac&category=tractors",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB trac"],
                "priority": "medium"
            }
        ]
    },
    "CA": {
        "country": "Kanada",
        "platforms": [
            {
                "name": "Kijiji.ca",
                "url": "https://www.kijiji.ca",
                "search_url": "https://www.kijiji.ca/b-farming-equipment/canada/mb-trac/k0c172l0",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac"],
                "priority": "high"
            },
            {
                "name": "TractorHouse.com (CA)",
                "url": "https://www.tractorhouse.com",
                "search_url": "https://www.tractorhouse.com/listings/farm-equipment/for-sale/list?keywords=mb%20trac&country=CAN",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB trac"],
                "priority": "medium"
            }
        ]
    },
    "AR": {
        "country": "Argentinien",
        "platforms": [
            {
                "name": "MercadoLibre.com.ar",
                "url": "https://www.mercadolibre.com.ar",
                "search_url": "https://listado.mercadolibre.com.ar/mb-trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "tractor Mercedes"],
                "priority": "high"
            },
            {
                "name": "Agrofy.com.ar",
                "url": "https://www.agrofy.com.ar",
                "search_url": "https://www.agrofy.com.ar/tractores?q=mb+trac",
                "type": "agrar_spezialisiert",
                "search_terms": ["MB trac"],
                "priority": "medium"
            }
        ]
    },
    "BR": {
        "country": "Brasilien",
        "platforms": [
            {
                "name": "MercadoLivre.com.br",
                "url": "https://www.mercadolivre.com.br",
                "search_url": "https://lista.mercadolivre.com.br/mb-trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac", "trator Mercedes"],
                "priority": "high"
            },
            {
                "name": "OLX.com.br",
                "url": "https://www.olx.com.br",
                "search_url": "https://www.olx.com.br/brasil?q=mb+trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac"],
                "priority": "medium"
            }
        ]
    },
    "NA": {
        "country": "Namibia",
        "platforms": [
            {
                "name": "MarketBook.na",
                "url": "https://www.marketbook.com.na",
                "search_url": "https://www.marketbook.com.na/listings/search?Category=1100&keywords=mb%20trac",
                "type": "kleinanzeigen",
                "search_terms": ["MB trac"],
                "priority": "medium"
            }
        ]
    }
}

# Zusammenfassung der Statistiken
def get_platform_stats():
    total_countries = len(PLATFORMS)
    total_platforms = sum(len(country_data["platforms"]) for country_data in PLATFORMS.values())
    high_priority = sum(
        1 for country_data in PLATFORMS.values()
        for p in country_data["platforms"]
        if p["priority"] == "high"
    )
    return {
        "total_countries": total_countries,
        "total_platforms": total_platforms,
        "high_priority_platforms": high_priority
    }

if __name__ == "__main__":
    stats = get_platform_stats()
    print(f"MB-trac Scraper Plattform-Datenbank")
    print(f"=" * 40)
    print(f"Länder: {stats['total_countries']}")
    print(f"Plattformen gesamt: {stats['total_platforms']}")
    print(f"High Priority: {stats['high_priority_platforms']}")

"""
Traktor-Scraper - Filter und Kategorisierung
=============================================
Intelligente Filterung und Kategorisierung von Inseraten.
Unterstützt MB-trac und weitere Marken (definiert in brands.py).
"""

import re
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from enum import Enum
from brands import get_matching_brand, get_non_mbtrac_brand_spellings


class Category(Enum):
    """Kategorien für Inserate"""
    VEHICLE = "fahrzeug"           # Komplettes Fahrzeug
    PARTS = "ersatzteil"           # Ersatzteile
    MODEL = "modell"               # Spielzeug / Sammlermodelle
    WANTED = "suchgesuch"          # Jemand sucht etwas
    OTHER = "sonstiges"            # Nicht kategorisierbar
    EXCLUDED = "ausgeschlossen"    # False Positive, ausfiltern


@dataclass
class FilterResult:
    """Ergebnis der Filterung"""
    is_valid: bool                 # Soll das Inserat behalten werden?
    category: Category             # Kategorie des Inserats
    reason: Optional[str] = None   # Grund für Ausschluss (wenn is_valid=False)
    price_numeric: Optional[float] = None  # Extrahierter numerischer Preis
    is_negotiable: bool = False    # Ist der Preis VB/verhandelbar?
    brand: Optional[str] = None    # Erkannte Marke (z.B. "fendt", "mb_trac")


# ============================================================
# BLACKLISTS - Begriffe die zum Ausschluss führen
# ============================================================

# Fahrzeuge die KEINE MB-trac sind, aber "MB" im Namen haben
BLACKLIST_VEHICLES = [
    'sprinter',          # Mercedes Sprinter
    'vito',              # Mercedes Vito
    'actros',            # Mercedes Actros LKW
    'atego',             # Mercedes Atego LKW
    'arocs',             # Mercedes Arocs LKW
    'econic',            # Mercedes Econic
    'antos',             # Mercedes Antos
    'citan',             # Mercedes Citan
    'axor',              # Mercedes Axor LKW
    'lamborghini',       # Lamborghini Traktoren
    # HINWEIS: fendt, john deere, new holland, case ih, deutz, claas
    # wurden aus der Blacklist entfernt — diese werden jetzt über brands.py
    # mit spezifischen Modellnummern validiert.
    'massey ferguson',   # Massey Ferguson
    'valtra',            # Valtra
    'kubota',            # Kubota
    'zetor',             # Zetor
    'steyr',             # Steyr
    'same',              # Same
    'landini',           # Landini
    'mccormick',         # McCormick
    'terraking',         # Terraking Landmaschinen
    'terracombi',        # TerraCombi
    'opticorn',          # Opticorn Header
    'man tg',            # MAN LKW (TGX, TGS, TGM, TGL)
    'man truck',         # MAN Truck
    'yamaha tracer',     # Yamaha Motorrad
    'yamaha mt',         # Yamaha Motorrad
    'michael bang',      # Designer (MB = Michael Bang, nicht Mercedes)
    'holmegaard',        # Glaswerk (oft mit Michael Bang)
    'gamecube',          # Videospiele
    'playstation',       # Videospiele
    'nintendo',          # Videospiele
    'xbox',              # Videospiele
    'vinyl',             # Schallplatten
    'hard rock',         # Musik
    'metal/',            # Musik
    'cd og kassett',     # Musik (norwegisch)
]

# Begriffe die auf generische Seiten / nicht-Inserate hinweisen
BLACKLIST_GENERIC = [
    'plant & tractors',
    'auto, moto si ambarcatiuni',  # Rumänische Kategorie-Seite
    'kategorien',
    'categories',
    'alle anzeigen',
    'view all',
    'mehr ergebnisse',
]

# ============================================================
# KATEGORISIERUNGS-KEYWORDS
# ============================================================

# Keywords die auf ein SUCHGESUCH hindeuten
WANTED_KEYWORDS = [
    'suche', 'gesucht', 'suchen', 'kaufe',
    'looking for', 'wanted', 'wtb', 'want to buy',
    'cherche', 'recherche',
    'søker', 'ønskes kjøpt',  # Norwegisch
    'söker', 'köpes',         # Schwedisch
    'szukam', 'kupię',        # Polnisch
    'hledám', 'koupím',       # Tschechisch
    'keresek', 'vennék',      # Ungarisch
    'gezocht',                # Niederländisch
]

# Keywords die auf SPIELZEUG/MODELLE hindeuten
MODEL_KEYWORDS = [
    'weise toys', 'weise-toys', 'weisetoys',
    'siku', 'bruder', 'schuco', 'minichamps',
    'modellauto', 'modelltraktor', 'modell 1:',
    '1:32', '1:43', '1:50', '1:64', '1:87',
    'scale model', 'diecast', 'die-cast',
    'spielzeug', 'toy', 'jouet',
    'sammlerstück', 'sammler', 'collector',
    'vitrine', 'display',
    'miniatur', 'miniature',
]

# Keywords die auf ERSATZTEILE hindeuten
PARTS_KEYWORDS = [
    # Deutsche Begriffe
    'ersatzteil', 'ersatzteile', 'zubehör',
    'motor', 'getriebe', 'achse', 'differential',
    'hydraulik', 'pumpe', 'ventil', 'zylinder',
    'kabine', 'fahrerhaus', 'sitz', 'lenkrad',
    'reifen', 'felge', 'rad', 'radmutter',
    'bremse', 'bremsscheibe', 'bremsbelag',
    'kupplung', 'clutch', 'kupplungsscheibe',
    'lichtmaschine', 'anlasser', 'starter',
    'ölfilter', 'luftfilter', 'kraftstofffilter',
    'dichtung', 'dichtungssatz', 'wellendichtring',
    'schlauch', 'leitung', 'rohr',
    'schalter', 'hebel', 'pedal', 'gestänge',
    'spiegel', 'scheibe', 'glas', 'fenster',
    'kotflügel', 'haube', 'verkleidung',
    'auspuff', 'krümmer', 'abgaskrümmer',
    'kühler', 'radiator', 'lüfter',
    'batterie', 'kabel', 'stecker',
    'instrument', 'tacho', 'anzeige',
    'feder', 'dämpfer', 'stoßdämpfer',
    'lager', 'buchse', 'bolzen', 'schraube',
    'welle', 'kardanwelle', 'antriebswelle',
    'griff', 'halterung', 'halter', 'konsole',
    'deckel', 'abdeckung', 'kappe',
    'broschüre', 'prospekt', 'brochure',  # Auch Literatur
    'handbuch', 'manual', 'anleitung',
    'werkstatthandbuch', 'reparaturanleitung',
    # Englische Begriffe
    'spare part', 'parts', 'component',
    'transmission', 'gearbox', 'axle',
    'hydraulic', 'pump', 'valve', 'cylinder',
    'cabin', 'seat', 'steering',
    'tire', 'tyre', 'wheel', 'rim',
    'brake', 'clutch',
    'alternator', 'starter',
    'filter', 'gasket', 'seal',
    'hose', 'pipe', 'tube',
    # Französische Begriffe
    'pièce', 'piece', 'pièces', 'pieces',
    'jante', 'jantes',           # Felge
    'roue', 'roues',             # Rad
    'pneu', 'pneus',             # Reifen
    'moteur',                    # Motor
    'capot',                     # Haube
    'siège',                     # Sitz
    'volant',                    # Lenkrad
    'phare',                     # Scheinwerfer
    'prise de force',           # Zapfwelle
    'forestière', 'forestier',  # Forst-Ausrüstung
    'brosjyre',                 # Broschüre (norwegisch)
    # Norwegische Begriffe
    'deler', 'reservedel',
    'dørhåndtak',               # Türgriff
    'dynamo',                   # Lichtmaschine
    # Niederländische Begriffe
    'onderdeel', 'onderdelen',
]

# Keywords die auf ein KOMPLETTES FAHRZEUG hindeuten
VEHICLE_KEYWORDS = [
    # Typbezeichnungen (mit Leerzeichen)
    'mb trac 65', 'mb trac 70', 'mb trac 80',
    'mb trac 700', 'mb trac 800', 'mb trac 900',
    'mb trac 1000', 'mb trac 1100', 'mb trac 1300',
    'mb trac 1400', 'mb trac 1500', 'mb trac 1600',
    'mb trac 1800', 'mb trac turbo',
    # Typbezeichnungen (mit Bindestrich)
    'mb-trac 65', 'mb-trac 70', 'mb-trac 80',
    'mb-trac 700', 'mb-trac 800', 'mb-trac 900',
    'mb-trac 1000', 'mb-trac 1100', 'mb-trac 1300',
    'mb-trac 1400', 'mb-trac 1500', 'mb-trac 1600',
    'mb-trac 1800', 'mb-trac turbo',
    # Baureihen-Nummern (intern bei Mercedes)
    'trac 440', 'trac 441', 'trac 442', 'trac 443',
    '440 trac', '441 trac', '442 trac', '443 trac',
    # Werner Forstmaschinen (übernahm MB-trac Technologie)
    'wf trac', 'wf-trac', 'werner trac', 'wftrac',
    'wf trac 1300', 'wf trac 1500', 'wf trac 1700',
    # Zustandsbeschreibungen die auf Fahrzeuge hindeuten
    'frontlader', 'forstausrüstung', 'forst',
    'allrad', '4x4', 'vierradantrieb',
    'betriebsstunden', 'bh', 'hours',
    'baujahr', 'bj', 'year',
    'erstzulassung', 'ez',
    'tüv', 'hu', 'hauptuntersuchung',
    'restauriert', 'restored', 'renoviert',
    'top zustand', 'sehr guter zustand',
    'fahrbereit', 'einsatzbereit',
    'wenig gelaufen', 'wenig stunden',
]


def normalize_text(text: str) -> str:
    """Normalisiert Text für Vergleiche"""
    if not text:
        return ""
    # Kleinschreibung und mehrfache Leerzeichen entfernen
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def extract_price(price_str: Optional[str]) -> Tuple[Optional[float], bool]:
    """
    Extrahiert den numerischen Preis aus einem Preis-String.

    Returns:
        Tuple von (numerischer_preis, ist_verhandelbar)
        numerischer_preis ist None wenn kein Preis erkennbar
    """
    if not price_str:
        return None, False

    price_lower = price_str.lower()

    # Prüfen ob verhandelbar
    is_negotiable = any(term in price_lower for term in [
        'vb', 'v.b.', 'verhandlungsbasis', 'verhandelbar',
        'negotiable', 'o.n.o', 'ono', 'obo', 'or best offer',
        'n.o.t.k', 'preis auf anfrage', 'auf anfrage',
        'bieden', 'biedt', 'bieten',  # Niederländisch
        'pris ved forespørsel',  # Norwegisch
    ])

    # Nur "VB" ohne Zahl
    if price_lower.strip() in ['vb', 'v.b.', 'verhandlungsbasis']:
        return None, True

    # Zahlen extrahieren (mit Punkt oder Komma als Tausendertrennzeichen)
    # Beispiele: "14.990 €", "€ 27.750,00", "49000", "1.400 €"

    # Entferne Währungssymbole und Text
    cleaned = re.sub(r'[€$£]|EUR|USD|GBP|CHF|SEK|NOK|DKK|PLN|CZK|HUF|RON|BGN', '', price_str)

    # Finde Zahlen mit möglichen Tausendertrennzeichen
    # Pattern für verschiedene Formate: 14.990 / 14,990 / 14990 / 27.750,00
    matches = re.findall(r'[\d.,]+', cleaned)

    for match in matches:
        try:
            # Wenn Komma am Ende (europäisches Format mit Dezimalstellen)
            if ',' in match and '.' in match:
                # Format: 27.750,00 -> 27750.00
                num_str = match.replace('.', '').replace(',', '.')
            elif ',' in match:
                # Könnte 1,400 (Tausender) oder 14,99 (Dezimal) sein
                parts = match.split(',')
                if len(parts) == 2 and len(parts[1]) == 2:
                    # Wahrscheinlich Dezimal: 14,99
                    num_str = match.replace(',', '.')
                else:
                    # Wahrscheinlich Tausender: 1,400
                    num_str = match.replace(',', '')
            elif '.' in match:
                # Könnte 1.400 (Tausender) oder 14.99 (Dezimal) sein
                parts = match.split('.')
                if len(parts) == 2 and len(parts[1]) == 2:
                    # Wahrscheinlich Dezimal: 14.99
                    num_str = match
                else:
                    # Wahrscheinlich Tausender: 1.400
                    num_str = match.replace('.', '')
            else:
                num_str = match

            price = float(num_str)

            # Plausibilitätsprüfung: Preise zwischen 1 und 500.000
            if 1 <= price <= 500000:
                return price, is_negotiable

        except ValueError:
            continue

    return None, is_negotiable


def is_blacklisted(title: str) -> Tuple[bool, Optional[str]]:
    """
    Prüft ob der Titel auf der Blacklist steht.

    Returns:
        Tuple von (ist_blacklisted, grund)
    """
    title_lower = normalize_text(title)

    # Prüfe auf generische Seiten
    for term in BLACKLIST_GENERIC:
        if term in title_lower:
            return True, f"Generische Seite: {term}"

    # Prüfe auf falsche Fahrzeuge
    # WICHTIG: Nur ausschließen wenn KEIN erkanntes Marke+Modell-Paar im Titel
    matched_brand = get_matching_brand(title)

    if not matched_brand:
        for term in BLACKLIST_VEHICLES:
            if term in title_lower:
                return True, f"Falsches Fahrzeug: {term}"

    return False, None


def categorize_listing(title: str, price_str: Optional[str] = None) -> Category:
    """
    Kategorisiert ein Inserat basierend auf dem Titel.

    Returns:
        Category Enum
    """
    title_lower = normalize_text(title)

    # 1. Prüfe auf Suchgesuch (höchste Priorität)
    # WICHTIG: Nur wenn "Suche" am ANFANG steht (erste 15 Zeichen)
    # Nicht bei "MB Trac 800, Suche Rückewagen" (das ist ein Verkauf!)
    title_start = title_lower[:15]
    for keyword in WANTED_KEYWORDS:
        if keyword in title_start:
            return Category.WANTED

    # 2. Prüfe auf Spielzeug/Modell
    for keyword in MODEL_KEYWORDS:
        if keyword in title_lower:
            return Category.MODEL

    # 3. Prüfe auf komplettes Fahrzeug (vor Ersatzteilen!)
    vehicle_score = 0
    for keyword in VEHICLE_KEYWORDS:
        if keyword in title_lower:
            vehicle_score += 1

    # 4. Prüfe auf Ersatzteile
    parts_score = 0
    for keyword in PARTS_KEYWORDS:
        if keyword in title_lower:
            parts_score += 1

    # Entscheidung basierend auf Scores
    if vehicle_score > 0 and vehicle_score >= parts_score:
        return Category.VEHICLE
    elif parts_score > 0:
        return Category.PARTS

    # 5. Fallback: Preis als Indikator
    if price_str:
        price, _ = extract_price(price_str)
        if price and price > 5000:
            # Hoher Preis deutet auf Fahrzeug hin
            return Category.VEHICLE
        elif price and price < 500:
            # Niedriger Preis deutet auf Ersatzteil hin
            return Category.PARTS

    # 6. Default: Als Sonstiges kategorisieren
    return Category.OTHER


def filter_listing(title: str, price_str: Optional[str] = None,
                   min_price_vehicle: float = 1000) -> FilterResult:
    """
    Hauptfunktion: Filtert und kategorisiert ein Inserat.

    Args:
        title: Titel des Inserats
        price_str: Preis als String (optional)
        min_price_vehicle: Mindestpreis für Fahrzeuge (default 1000€)

    Returns:
        FilterResult mit allen Informationen
    """
    # 1. Blacklist prüfen
    is_bl, reason = is_blacklisted(title)
    if is_bl:
        return FilterResult(
            is_valid=False,
            category=Category.EXCLUDED,
            reason=reason
        )

    # 1b. PFLICHT: Muss erkanntes Marke+Modell-Paar enthalten (via brands.py)
    matched_brand = get_matching_brand(title)

    if not matched_brand:
        return FilterResult(
            is_valid=False,
            category=Category.EXCLUDED,
            reason="Kein erkanntes Traktor-Modell gefunden"
        )

    # 2. Preis extrahieren
    price_numeric, is_negotiable = extract_price(price_str)

    # 3. Kategorisieren
    category = categorize_listing(title, price_str)

    # 4. Mindestpreis-Filter für Fahrzeuge
    # WICHTIG: Nur anwenden wenn Kategorie=VEHICLE UND ein Preis vorhanden ist
    # Bei VB oder keinem Preis NICHT ausfiltern!
    if category == Category.VEHICLE and price_numeric is not None:
        if price_numeric < min_price_vehicle and not is_negotiable:
            return FilterResult(
                is_valid=True,  # Trotzdem behalten, nur Kategorie ändern
                category=Category.PARTS,  # Wahrscheinlich doch ein Ersatzteil
                price_numeric=price_numeric,
                is_negotiable=is_negotiable,
                reason=f"Preis unter {min_price_vehicle}€, als Ersatzteil kategorisiert",
                brand=matched_brand
            )

    return FilterResult(
        is_valid=True,
        category=category,
        price_numeric=price_numeric,
        is_negotiable=is_negotiable,
        brand=matched_brand
    )


# ============================================================
# TEST / DEMO
# ============================================================

if __name__ == "__main__":
    # Test mit echten Beispielen aus dem Scraper
    test_cases = [
        ("MB Trac 800 Forst , Suche neuen Rückewagen", "49.000 €"),
        ("MB Trac 800 Mercedes Benz Traktor Trecker Frontlader", "14.990 €"),
        ("Mb-Trac Sitz orginal Isri ohne Lendenwirbelpolsterung", "1.400 €"),
        ("Suche MB trac 700-1100 auch defekt", "VB"),
        ("Weise Toys 1013 MB Trac 1100 Traktor Modell 1:32", "330 €"),
        ("MB Sprinter W900 2002-2006 Koplamp Links", "€ 84,95"),
        ("Lamborghini R4-110 CHELNI TOVARACH", "24 800 EUR"),
        ("MB trac brosjyre", None),
        ("MB TRAC FRONTHYDRAULIKK 442/443", None),
        ("Veiling: Tractor MB Trac 800 Diesel 54kW 1980", "€ 7.000,00"),
        ("50 Jahre MB Trac Half Zip, Quarter Zip, Pullover, Gr. S", "20 €"),
        ("Plant & Tractors", None),
    ]

    print("=" * 80)
    print("MB-trac Filter Test")
    print("=" * 80)

    for title, price in test_cases:
        result = filter_listing(title, price)
        status = "✅" if result.is_valid else "❌"
        print(f"\n{status} {title[:60]}...")
        print(f"   Preis: {price} -> {result.price_numeric} ({'VB' if result.is_negotiable else 'fest'})")
        print(f"   Kategorie: {result.category.value}")
        if result.reason:
            print(f"   Grund: {result.reason}")

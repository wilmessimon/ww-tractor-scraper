"""
Traktor-Scraper - Marken & Modell-Konfiguration
=================================================
Zentrale Definition aller gesuchten Marken, Modelle und Schreibvarianten.
Wird von filters.py und scraper.py verwendet.
"""

import re
from typing import Optional, Tuple, List, Dict


# ============================================================
# MARKEN-DEFINITIONEN
# ============================================================

BRANDS = {
    # ---------------------------------------------------------
    # MB-trac (bestehend, höchste Priorität)
    # ---------------------------------------------------------
    "mb_trac": {
        "display_name": "MB-trac",
        "spellings": [
            "mb-trac", "mb trac", "mbtrac",
            "mb-track", "mb track", "mbtrack",
            "mb-trak", "mb trak", "mbtrak",
            "mb-trec", "mb trec",
            "mb-tracc", "mb tracc",
            "mb-trax", "mb trax",
            "mb træc",
            "mercedes trac", "mercedes-trac",
            "mercedes trak", "mercedes track",
            "mercedes benz trac", "mercedes-benz trac",
            "mercedesbenz trac",
        ],
        "extra_keywords": [
            "unimog",
            "wf-trac", "wf trac", "wftrac", "werner trac",
            "trac 440", "trac 441", "trac 442", "trac 443",
            "trac 700", "trac 800", "trac 900", "trac 1000",
            "trac 1100", "trac 1300", "trac 1400", "trac 1500", "trac 1600",
            "mbtrac700", "mbtrac800", "mbtrac900",
            "mbtrac1000", "mbtrac1100", "mbtrac1300",
            "mbtrac1400", "mbtrac1500", "mbtrac1600",
        ],
        # MB-trac braucht KEINE Modellnummer-Validierung — Markenname reicht
        "match_brand_only": True,
        "models": [],
        "search_terms": [
            "MB-trac", "MB Trac", "MB trac", "MBtrac",
            "Mercedes Trac", "Mercedes-Benz Trac",
            "MB Track", "MB-Track", "MBTrack",
            "MB Trak", "MB-Trak", "MBTrak",
            "Unimog", "WF Trac",
        ],
    },

    # ---------------------------------------------------------
    # Fendt (Fend, Fent)
    # ---------------------------------------------------------
    "fendt": {
        "display_name": "Fendt",
        "spellings": ["fendt", "fend", "fent"],
        "extra_keywords": [],
        "match_brand_only": False,  # Braucht Marke + Modell
        "models": [
            # 304-312 LS/LSA
            {"range": (304, 312), "suffixes": ["", "LS", "LSA"]},
            # 509-515 C
            {"range": (509, 515), "suffixes": ["", "C"]},
            # 611-615 LS/LSA
            {"range": (611, 615), "suffixes": ["", "LS", "LSA"]},
            # Vario 712-718 (Vario optional — Leute schreiben "Fendt 714")
            {"prefix": "Vario", "prefix_optional": True, "range": (712, 718), "suffixes": ["", "Vario"]},
            # Vario 815-820
            {"prefix": "Vario", "prefix_optional": True, "range": (815, 820), "suffixes": ["", "Vario"]},
            # Vario 916-930
            {"prefix": "Vario", "prefix_optional": True, "range": (916, 930), "suffixes": ["", "Vario"]},
        ],
        "search_terms": [
            "Fendt 309", "Fendt 311", "Fendt Vario 714",
            "Fendt 611", "Fendt 614", "Fendt 509",
            "Fendt Vario 916", "Fendt Vario 818",
        ],
    },

    # ---------------------------------------------------------
    # John Deere
    # ---------------------------------------------------------
    "john_deere": {
        "display_name": "John Deere",
        "spellings": ["john deere", "johndeere", "john deer", "john-deere"],
        "extra_keywords": [],
        "match_brand_only": False,
        "models": [
            # 6210-6910
            {"range": (6210, 6910), "suffixes": [""]},
            # 7710-7810
            {"range": (7710, 7810), "suffixes": [""]},
            # 6220-6920
            {"range": (6220, 6920), "suffixes": [""]},
            # 6230-6930
            {"range": (6230, 6930), "suffixes": [""]},
        ],
        "search_terms": [
            "John Deere 6910", "John Deere 6810",
            "John Deere 7710", "John Deere 7810",
            "John Deere 6310", "John Deere 6410",
        ],
    },

    # ---------------------------------------------------------
    # Deutz
    # ---------------------------------------------------------
    "deutz": {
        "display_name": "Deutz",
        "spellings": ["deutz", "deutz-fahr", "deutz fahr"],
        "extra_keywords": [],
        "match_brand_only": False,
        "models": [
            # 8006, 10006, 13006
            {"exact": [8006, 10006, 13006]},
            # 6005, 8005, 9005
            {"exact": [6005, 8005, 9005]},
            # DX Agrostar 4.61-6.61 (Prefixe optional — Leute schreiben "Deutz 6.61")
            {"prefix": "DX", "prefix_optional": True, "exact_str": [
                "4.61", "4.71", "6.01", "6.06", "6.11", "6.21", "6.31", "6.61"
            ]},
            {"prefix": "Agrostar", "prefix_optional": True, "exact_str": [
                "4.61", "4.71", "6.01", "6.06", "6.11", "6.21", "6.31", "6.61"
            ]},
            {"prefix": "DX Agrostar", "prefix_optional": True, "exact_str": [
                "4.61", "4.71", "6.01", "6.06", "6.11", "6.21", "6.31", "6.61"
            ]},
        ],
        "search_terms": [
            "Deutz 8006", "Deutz 10006", "Deutz 13006",
            "Deutz DX", "Deutz Agrostar",
            "Deutz-Fahr DX", "Deutz-Fahr Agrostar",
        ],
    },

    # ---------------------------------------------------------
    # IHC / IH / International / Case
    # ---------------------------------------------------------
    "ihc": {
        "display_name": "IHC",
        "spellings": ["ihc", "ih ", "international harvester", "international"],
        "extra_keywords": [],
        "match_brand_only": False,
        "models": [
            # 844, 856, 956, 1056 XL
            {"exact": [844, 856, 956, 1056], "suffixes": ["", "XL"]},
            # 946, 1046, 1246
            {"exact": [946, 1046, 1246], "suffixes": [""]},
            # 523, 624, 724, 824
            {"exact": [523, 624, 724, 824], "suffixes": [""]},
        ],
        "search_terms": [
            "IHC 844", "IHC 856", "IHC 956", "IHC 1056",
            "IHC 946", "IHC 1046", "IHC 1246",
            "IHC 724", "IHC 824", "IHC 624",
        ],
    },

    # ---------------------------------------------------------
    # Case IH International
    # ---------------------------------------------------------
    "case_ih": {
        "display_name": "Case IH",
        "spellings": ["case ih", "case-ih", "caseih"],
        "extra_keywords": [],
        "match_brand_only": False,
        "models": [
            # 1255 XL, 1455 XL
            {"exact": [1255, 1455], "suffixes": ["", "XL"]},
        ],
        "search_terms": [
            "Case IH 1255", "Case IH 1455",
            "Case IH 1255 XL", "Case IH 1455 XL",
        ],
    },

    # ---------------------------------------------------------
    # Fiat (XX-90 Serie)
    # ---------------------------------------------------------
    "fiat": {
        "display_name": "Fiat",
        "spellings": ["fiat"],
        "extra_keywords": [],
        "match_brand_only": False,
        "models": [
            # 70-90 bis 180-90 (die XX-90 Serie)
            {"exact_str": [
                "70-90", "80-90", "90-90", "100-90", "110-90",
                "115-90", "130-90", "140-90", "160-90", "180-90",
            ]},
        ],
        "search_terms": [
            "Fiat 100-90", "Fiat 110-90", "Fiat 130-90",
            "Fiat 80-90", "Fiat 140-90", "Fiat 160-90",
        ],
    },

    # ---------------------------------------------------------
    # New Holland
    # ---------------------------------------------------------
    "new_holland": {
        "display_name": "New Holland",
        "spellings": ["new holland", "newholland", "new-holland"],
        "extra_keywords": [],
        "match_brand_only": False,
        "models": [
            # TM 120-140 (TM optional — Leute schreiben "New Holland 130")
            {"prefix": "TM", "prefix_optional": True, "exact": [120, 125, 130, 135, 140]},
        ],
        "search_terms": [
            "New Holland TM 130", "New Holland TM 135",
            "New Holland TM 140", "New Holland TM 120",
        ],
    },

    # ---------------------------------------------------------
    # Claas Xerion
    # ---------------------------------------------------------
    "claas_xerion": {
        "display_name": "Claas Xerion",
        "spellings": ["claas xerion", "claas-xerion", "xerion"],
        "extra_keywords": [],
        "match_brand_only": False,
        "models": [
            {"exact": [3300, 3800]},
        ],
        "search_terms": [
            "Claas Xerion 3300", "Claas Xerion 3800",
        ],
    },
}


# ============================================================
# MATCHING-LOGIK
# ============================================================

def _normalize(text: str) -> str:
    """Normalisiert Text für Vergleiche"""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def _build_patterns(prefix: str, num_str: str, suffix: str, prefix_optional: bool) -> List[str]:
    """
    Baut alle Pattern-Varianten für eine Modellnummer.
    Wenn prefix_optional=True, werden zusätzlich Patterns OHNE Prefix generiert.
    z.B. Fendt Vario 930 → matcht auch "Fendt 930" oder "Fendt 930 Vario"
    """
    patterns = []
    pl = prefix.lower() if prefix else ""
    sl = suffix.lower() if suffix else ""

    if pl:
        # MIT Prefix: "vario 930", "vario930"
        patterns.append(f"{pl} {num_str}")
        patterns.append(f"{pl}{num_str}")
        if sl:
            patterns.append(f"{pl} {num_str} {sl}")
            patterns.append(f"{pl} {num_str}{sl}")
            patterns.append(f"{pl}{num_str} {sl}")

        if prefix_optional:
            # OHNE Prefix: "930" (nur die Nummer)
            patterns.append(num_str)
            if sl:
                patterns.append(f"{num_str} {sl}")
                patterns.append(f"{num_str}{sl}")
    else:
        # Kein Prefix definiert: "309", "309 ls", "309ls"
        patterns.append(num_str)
        if sl:
            patterns.append(f"{num_str} {sl}")
            patterns.append(f"{num_str}{sl}")

    return patterns


def _check_model_match(title_lower: str, brand_config: dict) -> bool:
    """
    Prüft ob der Titel ein gültiges Modell für die gegebene Marke enthält.
    """
    models = brand_config.get("models", [])
    if not models:
        return True  # Keine Modelle definiert = Marke allein reicht

    for model_def in models:
        prefix = model_def.get("prefix", "")
        prefix_optional = model_def.get("prefix_optional", False)

        # Typ 1: Nummern-Range (z.B. 304-312)
        if "range" in model_def:
            start, end = model_def["range"]
            suffixes = model_def.get("suffixes", [""])

            for num in range(start, end + 1):
                for suffix in suffixes:
                    patterns = _build_patterns(prefix, str(num), suffix, prefix_optional)
                    for pattern in patterns:
                        if pattern in title_lower:
                            return True

        # Typ 2: Exakte Nummern (z.B. [844, 856, 956])
        elif "exact" in model_def and isinstance(model_def["exact"], list):
            if isinstance(model_def["exact"][0], int):
                suffixes = model_def.get("suffixes", [""])

                for num in model_def["exact"]:
                    for suffix in suffixes:
                        patterns = _build_patterns(prefix, str(num), suffix, prefix_optional)
                        for pattern in patterns:
                            if pattern in title_lower:
                                return True

        # Typ 3: Exakte Strings (z.B. ["4.61", "6.61"] oder ["70-90", "80-90"])
        elif "exact_str" in model_def:
            for s in model_def["exact_str"]:
                patterns = _build_patterns(prefix, s, "", prefix_optional)
                for pattern in patterns:
                    if pattern in title_lower:
                        return True

    return False


def get_matching_brand(title: str) -> Optional[str]:
    """
    Prüft ob der Titel eine gültige Marke+Modell-Kombination enthält.

    Returns:
        Brand-Key (z.B. "fendt", "mb_trac") oder None
    """
    title_lower = _normalize(title)
    if not title_lower:
        return None

    for brand_key, config in BRANDS.items():
        # 1. Prüfe ob Markenname im Titel vorkommt
        brand_found = False
        for spelling in config["spellings"]:
            if spelling.lower() in title_lower:
                brand_found = True
                break

        # 2. Prüfe extra_keywords (für MB-trac: unimog, wf-trac, etc.)
        if not brand_found:
            for kw in config.get("extra_keywords", []):
                if kw.lower() in title_lower:
                    brand_found = True
                    break

        if not brand_found:
            continue

        # 3. Wenn match_brand_only=True → Marke allein reicht (MB-trac)
        if config.get("match_brand_only", False):
            return brand_key

        # 4. Sonst: Prüfe ob auch ein gültiges Modell im Titel steht
        if _check_model_match(title_lower, config):
            return brand_key

    return None


def get_brand_display_name(brand_key: str) -> str:
    """Gibt den Anzeigenamen einer Marke zurück"""
    if brand_key in BRANDS:
        return BRANDS[brand_key]["display_name"]
    return brand_key


def get_all_brand_keys() -> List[str]:
    """Gibt alle Marken-Keys zurück"""
    return list(BRANDS.keys())


def get_non_mbtrac_brand_spellings() -> List[str]:
    """
    Gibt alle Markennamen-Schreibweisen zurück, die NICHT MB-trac sind.
    Wird von filters.py verwendet um diese aus der Blacklist auszunehmen.
    """
    spellings = []
    for brand_key, config in BRANDS.items():
        if brand_key == "mb_trac":
            continue
        spellings.extend(config["spellings"])
    return spellings


def get_search_terms_for_brand(brand_key: str) -> List[str]:
    """Gibt Suchbegriffe für eine bestimmte Marke zurück"""
    if brand_key in BRANDS:
        return BRANDS[brand_key].get("search_terms", [])
    return []


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    test_cases = [
        # MB-trac (soll matchen)
        ("MB Trac 800 Forst", "mb_trac"),
        ("MB-trac 1600 turbo", "mb_trac"),
        ("Unimog 406 Cabrio", "mb_trac"),
        ("WF Trac 1300", "mb_trac"),
        ("MB Track 1000", "mb_trac"),

        # Fendt (soll matchen)
        ("Fendt 309 LS Traktor", "fendt"),
        ("Fend 311 LSA", "fendt"),
        ("Fendt Vario 714 Traktor", "fendt"),
        ("Fendt Vario 916 Profi", "fendt"),
        ("Fent 510 C", "fendt"),
        # Fendt OHNE Vario-Prefix (Leute vergessen "Vario")
        ("Fendt 930 Traktor", "fendt"),
        ("Fendt 718 zu verkaufen", "fendt"),
        ("Fent 815 Schlepper", "fendt"),
        ("Fendt 920 Vario", "fendt"),  # Nummer + Vario als Suffix

        # Fendt (soll NICHT matchen — Modell nicht in Liste)
        ("Fendt 936 Vario", None),
        ("Fendt Farmer 108", None),
        ("Fendt 1050", None),

        # John Deere
        ("John Deere 6910 Premium", "john_deere"),
        ("John Deere 7810 AutoQuad", "john_deere"),
        ("John Deer 6410", "john_deere"),  # Tippfehler
        ("John Deere 8400", None),  # Nicht in Liste

        # Deutz
        ("Deutz 8006 Traktor", "deutz"),
        ("Deutz DX 6.61 Agrostar", "deutz"),
        ("Deutz-Fahr Agrostar 6.31", "deutz"),
        ("Deutz 6.61 Traktor", "deutz"),  # Ohne DX/Agrostar
        ("Deutz 4.71 zu verkaufen", "deutz"),  # Ohne Prefix
        ("Deutz 6206", None),  # Nicht in Liste

        # IHC
        ("IHC 844 XL Traktor", "ihc"),
        ("IHC 1056 XL", "ihc"),
        ("IHC 724 Schlepper", "ihc"),
        ("IHC 1455", None),  # Das ist Case IH

        # Case IH
        ("Case IH 1255 XL", "case_ih"),
        ("Case IH 1455 XL", "case_ih"),

        # Fiat
        ("Fiat 110-90 DT", "fiat"),
        ("Fiat 80-90 Traktor", "fiat"),
        ("Fiat 500 Auto", None),  # Kein Traktor

        # New Holland
        ("New Holland TM 135 Traktor", "new_holland"),
        ("New Holland TM 140", "new_holland"),
        ("New Holland 130 Traktor", "new_holland"),  # Ohne TM
        ("New Holland 140", "new_holland"),  # Ohne TM
        ("New Holland T7", None),  # Nicht in Liste

        # Claas Xerion
        ("Claas Xerion 3300", "claas_xerion"),
        ("Claas Xerion 3800 Trac", "claas_xerion"),
        ("Claas Arion 640", None),  # Nicht in Liste

        # Komplett irrelevant
        ("Mercedes Sprinter 313 CDI", None),
        ("Lamborghini Huracan", None),
    ]

    print("=" * 70)
    print("Marken-Matching Test")
    print("=" * 70)

    passed = 0
    failed = 0
    for title, expected in test_cases:
        result = get_matching_brand(title)
        status = "✅" if result == expected else "❌"
        if result != expected:
            failed += 1
            print(f"{status} '{title[:50]}...' → {result} (erwartet: {expected})")
        else:
            passed += 1
            print(f"{status} '{title[:50]}...' → {result}")

    print(f"\n{passed} bestanden, {failed} fehlgeschlagen")

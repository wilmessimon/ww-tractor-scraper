"""
Plattform-spezifische Parser-Definitionen.

Die meisten Plattformen laufen weiterhin über den GenericScraper, erhalten
hier aber host-/typ-spezifische Selektoren, URL-Muster und Firecrawl-Defaults.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict
from urllib.parse import urlparse


def _merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in (override or {}).items():
        merged[key] = deepcopy(value)
    return merged


TYPE_PRESETS: Dict[str, Dict[str, Any]] = {
    "kleinanzeigen": {
        "item_selectors": [
            'article',
            'li[data-testid]',
            'div[data-testid*="listing"]',
            'div[data-testid*="search-result"]',
            'li[class*="listing"]',
            'div[class*="listing"]',
            'div[class*="result"]',
            'div[class*="item"]',
            'div[class*="ad-"]',
        ],
        "title_selectors": [
            'h1', 'h2', 'h3', 'h4',
            '[data-testid*="title"]',
            '[class*="title"]',
            '[class*="heading"]',
            'a[title]',
            'img[alt]',
            'a',
        ],
        "price_selectors": [
            '[data-testid*="price"]',
            '[class*="price"]',
            '[class*="amount"]',
            '[class*="cost"]',
            '[class*="value"]',
        ],
        "location_selectors": [
            '[data-testid*="location"]',
            '[data-testid*="subtitle"]',
            '[class*="location"]',
            '[class*="region"]',
            '[class*="city"]',
            '[class*="postal"]',
        ],
        "image_selectors": ['img[src]', 'img[data-src]', 'img[data-original]'],
        "description_selectors": [
            '[data-testid*="description"]',
            '[class*="description"]',
            '[class*="summary"]',
        ],
        "link_selectors": ['a[href]'],
        "link_attributes": ['href'],
        "container_tags": ['article', 'li', 'div'],
        "max_items": 60,
        "json_ld_enabled": True,
        "link_fallback_enabled": True,
    },
    "agrar_spezialisiert": {
        "item_selectors": [
            'article',
            'div[data-testid*="listing"]',
            'div[class*="machine"]',
            'div[class*="result"]',
            'div[class*="card"]',
            'li[class*="listing"]',
            'li[class*="result"]',
        ],
        "title_selectors": [
            'h1', 'h2', 'h3', 'h4',
            '[data-testid*="title"]',
            '[class*="title"]',
            '[class*="machine"]',
            'a[title]',
            'a',
        ],
        "price_selectors": [
            '[data-testid*="price"]',
            '[class*="price"]',
            '[class*="amount"]',
            '[class*="cost"]',
        ],
        "location_selectors": [
            '[data-testid*="location"]',
            '[class*="location"]',
            '[class*="region"]',
            '[class*="country"]',
            '[class*="city"]',
        ],
        "image_selectors": ['img[src]', 'img[data-src]', 'img[data-original]'],
        "description_selectors": ['[class*="description"]', '[class*="summary"]'],
        "link_selectors": ['a[href]'],
        "link_attributes": ['href'],
        "container_tags": ['article', 'li', 'div'],
        "max_items": 60,
        "json_ld_enabled": True,
        "link_fallback_enabled": True,
    },
    "fahrzeug_portal": {
        "item_selectors": [
            'article',
            'div[data-testid*="listing"]',
            'div[class*="vehicle"]',
            'div[class*="result"]',
            'div[class*="card"]',
            'li[class*="listing"]',
        ],
        "title_selectors": [
            'h1', 'h2', 'h3', 'h4',
            '[data-testid*="title"]',
            '[class*="title"]',
            '[class*="heading"]',
            'a[title]',
            'a',
        ],
        "price_selectors": [
            '[data-testid*="price"]',
            '[class*="price"]',
            '[class*="amount"]',
            '[class*="cost"]',
        ],
        "location_selectors": [
            '[data-testid*="location"]',
            '[class*="location"]',
            '[class*="region"]',
            '[class*="city"]',
        ],
        "image_selectors": ['img[src]', 'img[data-src]', 'img[data-original]'],
        "description_selectors": ['[class*="description"]', '[class*="summary"]'],
        "link_selectors": ['a[href]'],
        "link_attributes": ['href'],
        "container_tags": ['article', 'li', 'div'],
        "max_items": 60,
        "json_ld_enabled": True,
        "link_fallback_enabled": True,
    },
    "auktion": {
        "item_selectors": [
            'article',
            'li[data-testid]',
            'div[data-testid*="listing"]',
            'div[data-testid*="offer"]',
            'div[class*="offer"]',
            'div[class*="listing"]',
            'div[class*="result"]',
        ],
        "title_selectors": [
            'h1', 'h2', 'h3', 'h4',
            '[data-testid*="title"]',
            '[class*="title"]',
            '[class*="heading"]',
            'a[title]',
            'a',
        ],
        "price_selectors": [
            '[data-testid*="price"]',
            '[class*="price"]',
            '[class*="amount"]',
            '[class*="bid"]',
        ],
        "location_selectors": [
            '[data-testid*="location"]',
            '[class*="location"]',
            '[class*="region"]',
            '[class*="city"]',
        ],
        "image_selectors": ['img[src]', 'img[data-src]', 'img[data-original]'],
        "description_selectors": ['[class*="description"]', '[class*="summary"]'],
        "link_selectors": ['a[href]'],
        "link_attributes": ['href'],
        "container_tags": ['article', 'li', 'div'],
        "max_items": 60,
        "json_ld_enabled": True,
        "link_fallback_enabled": True,
    },
}


HOST_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "kleinanzeigen.de": {
        "item_selectors": ['article[data-testid]', 'article', 'li[class*="aditem"]'],
    },
    "leboncoin.fr": {
        "listing_url_patterns": ["/ad/"],
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 12000,
    },
    "milanuncios.com": {
        "item_selectors": ['article', 'div[data-testid*="listing"]', 'div.ma-AdCard'],
        "listing_url_patterns": ["/milanuncios.com/", ".htm"],
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 12000,
    },
    "wallapop.com": {
        "item_selectors": ['a[href*="/item/"] article', 'article', 'div[data-testid*="item"]'],
        "listing_url_patterns": ["/item/"],
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 12000,
        "firecrawl_actions": [
            {"type": "wait", "milliseconds": 4000},
            {"type": "scroll", "direction": "down", "amount": 1200},
        ],
    },
    "car.gr": {
        "firecrawl_force": True,
        "firecrawl_wait_for": 12000,
        "firecrawl_actions": [
            {"type": "wait", "milliseconds": 5000},
            {"type": "scroll", "direction": "down", "amount": 1200},
        ],
    },
    "willhaben.at": {
        "item_selectors": [
            'div[data-testid*="search-result-entry"]',
            'article[data-testid]',
            'article',
        ],
        "title_selectors": ['[data-testid*="title"]', 'h2', 'h3', 'a[title]', 'a'],
        "price_selectors": ['[data-testid*="price"]', '[class*="price"]'],
        "location_selectors": ['[data-testid*="subtitle"]', '[data-testid*="location"]', '[class*="location"]'],
        "listing_url_patterns": ['/iad/kaufen-und-verkaufen/d/'],
        "firecrawl_force": True,
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 12000,
        "firecrawl_actions": [
            {"type": "wait", "milliseconds": 3500},
            {"type": "scroll", "direction": "down", "amount": 900},
        ],
    },
    "ricardo.ch": {
        "item_selectors": [
            'article[data-testid]',
            'div[data-testid*="listing"]',
            'article',
        ],
        "listing_url_patterns": ['/de/a/'],
        "link_container_mode": "link",
        "prefer_anchor_text": True,
        "firecrawl_force": True,
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 12000,
    },
    "tutti.ch": {
        "item_selectors": [
            'article[data-testid]',
            'div[data-testid*="listing"]',
            'article',
        ],
        "listing_url_patterns": ['/de/vi/'],
        "prefer_anchor_text": True,
        "firecrawl_force": True,
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 12000,
    },
    "allegro.pl": {
        "item_selectors": [
            'article[data-role="offer"]',
            'div[data-box-name*="items"] article',
            'article',
        ],
        "listing_url_patterns": ['/oferta/'],
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 12000,
    },
    "donedeal.ie": {
        "item_selectors": [
            'li[data-testid*="listing-card-index"]',
            'article[data-testid]',
            'div[data-testid*="card"]',
            'article',
        ],
        "title_selectors": ['p[class*="Title"]', 'h2', 'h3', 'a[title]', 'a'],
        "price_selectors": ['div[class*="Price"]', '[data-testid*="price"]', '[class*="price"]'],
        "location_selectors": ['ul[class*="MetaInfo"] li:nth-of-type(2)', '[class*="location"]'],
        "listing_url_patterns": ['/tractors-for-sale/', '/farm-machinery-for-sale/', '/farming-for-sale/'],
        "prefer_anchor_text": True,
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 12000,
    },
    "finn.no": {
        "item_selectors": [
            'article[data-testid]',
            'article',
            'div[class*="ads__unit"]',
        ],
        "listing_url_patterns": ['/ad.html?finnkode='],
        "firecrawl_force": True,
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 12000,
    },
    "dba.dk": {
        "item_selectors": [
            'article[data-testid]',
            'article',
            'div[class*="listing"]',
        ],
        "listing_url_patterns": ['/annonce/'],
        "firecrawl_force": True,
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 12000,
    },
    "bazos.cz": {
        "item_selectors": ['div.inzeraty', 'div[class*="inzerat"]', 'table tr'],
        "listing_url_patterns": ['/inzerat/'],
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 10000,
    },
    "bazos.sk": {
        "item_selectors": ['div.inzeraty', 'div[class*="inzerat"]', 'table tr'],
        "listing_url_patterns": ['/inzerat/'],
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 10000,
    },
    "sbazar.cz": {
        "item_selectors": ['article[data-testid]', 'article', 'div[class*="advert"]'],
        "listing_url_patterns": ['/detail/'],
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 10000,
    },
    "bolha.com": {
        "item_selectors": ['li.EntityList-item', 'article', 'div[class*="Entity"]'],
        "listing_url_patterns": ['/oglasi/'],
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 10000,
    },
    "marktplaats.nl": {
        "item_selectors": ['li[data-testid*="listing"]', 'article', 'li[class*="Listing"]'],
        "listing_url_patterns": ['/v/'],
    },
    "2dehands.be": {
        "item_selectors": ['li[data-testid*="listing"]', 'article', 'li[class*="Listing"]'],
        "listing_url_patterns": ['/v/'],
    },
    "agriaffaires.com": {
        "item_selectors": ['article[data-testid]', 'article', 'div[class*="listing"]'],
        "listing_url_patterns": ['/occasion/'],
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 12000,
    },
    "agriaffaires.de": {
        "item_selectors": ['article[data-testid]', 'article', 'div[class*="listing"]'],
        "listing_url_patterns": ['/gebrauchte/'],
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 12000,
    },
    "olx.pl": {
        "item_selectors": ['div[data-cy="l-card"]', 'article[data-testid]', 'article'],
        "listing_url_patterns": ['/d/oferta/'],
    },
    "olx.pt": {
        "item_selectors": ['div[data-cy="l-card"]', 'article[data-testid]', 'article'],
        "listing_url_patterns": ['/d/anuncio/'],
    },
    "olx.ro": {
        "item_selectors": ['div[data-cy="l-card"]', 'article[data-testid]', 'article'],
        "listing_url_patterns": ['/d/oferta/'],
    },
    "olx.bg": {
        "item_selectors": ['div[data-cy="l-card"]', 'article[data-testid]', 'article'],
        "listing_url_patterns": ['/d/ad/'],
    },
    "olx.ua": {
        "item_selectors": ['div[data-cy="l-card"]', 'article[data-testid]', 'article'],
        "listing_url_patterns": ['/d/uk/obyavlenie/'],
    },
    "gumtree.com": {
        "item_selectors": ['article', 'div[class*="listing"]', 'li[class*="listing"]'],
    },
    "gumtree.com.au": {
        "item_selectors": ['article', 'div[class*="listing"]', 'li[class*="listing"]'],
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 12000,
    },
    "gumtree.co.za": {
        "item_selectors": ['article', 'div[class*="listing"]', 'li[class*="listing"]'],
    },
    "njuskalo.hr": {
        "item_selectors": ['article', 'li.EntityList-item', 'div[class*="entity"]'],
        "listing_url_patterns": ['/oglas/'],
    },
    "otomoto.pl": {
        "item_selectors": ['article[data-testid]', 'article', 'div[class*="ooa"]'],
    },
    "trucksnl.com": {
        "item_selectors": ['article', 'div[class*="card"]', 'div[class*="result"]'],
    },
}


NAME_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "eBay Kleinanzeigen (1600)": {
        "item_selectors": ['article[data-testid]', 'article', 'li[class*="aditem"]'],
    },
    "Agriaffaires FR": {
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 12000,
        "listing_url_patterns": ['/occasion/'],
        "required_terms_any": [
            'mb trac',
            'mb-trac',
            'mbtrac',
            'mercedes trac',
            'mercedes-benz trac',
        ],
    },
    "Agriaffaires": {
        "firecrawl_enabled": True,
        "firecrawl_wait_for": 12000,
    },
}


def get_platform_parser_config(platform_config: Dict[str, Any]) -> Dict[str, Any]:
    platform_type = platform_config.get("type", "kleinanzeigen")
    preset = TYPE_PRESETS.get(platform_type, TYPE_PRESETS["kleinanzeigen"])
    parser = deepcopy(preset)

    host = urlparse(platform_config.get("url") or platform_config.get("search_url") or "").netloc.lower()
    host = host.removeprefix("www.")

    if host in HOST_OVERRIDES:
        parser = _merge(parser, HOST_OVERRIDES[host])

    if platform_config.get("name") in NAME_OVERRIDES:
        parser = _merge(parser, NAME_OVERRIDES[platform_config["name"]])

    explicit = platform_config.get("parser")
    if explicit:
        parser = _merge(parser, explicit)

    return parser

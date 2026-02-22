#!/usr/bin/env python3
"""
Modernes Dashboard Generator für MB-trac Scraper
Erstellt ein schönes React-ähnliches UI mit Tailwind CSS
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

def generate_modern_dashboard(db_path: Path, output_path: Path):
    """Generiert ein modernes HTML-Dashboard"""

    # Lade Daten
    with open(db_path, 'r', encoding='utf-8') as f:
        listings = json.load(f)

    today = datetime.now().strftime("%Y-%m-%d")
    all_listings = sorted(
        [l for l in listings.values() if l.get('is_active', True)],
        key=lambda x: x.get('first_seen', ''),
        reverse=True
    )

    # Statistiken
    new_today = [l for l in all_listings if l.get('first_seen', '').startswith(today)]

    # Kategorien zählen
    categories = {}
    countries = {}
    for l in all_listings:
        cat = l.get('category', 'sonstiges')
        categories[cat] = categories.get(cat, 0) + 1

        country = l.get('country', 'XX')
        countries[country] = countries.get(country, 0) + 1

    # Fahrzeuge mit Preis
    vehicles = [l for l in all_listings
                if l.get('category') == 'fahrzeug'
                and l.get('price_numeric') and l.get('price_numeric') > 1000]
    vehicles.sort(key=lambda x: x.get('price_numeric', 0))

    # Preisstatistiken für Fahrzeuge
    if vehicles:
        prices = [v.get('price_numeric', 0) for v in vehicles if v.get('price_numeric')]
        avg_price = sum(prices) / len(prices) if prices else 0
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
    else:
        avg_price = min_price = max_price = 0

    # Berechne Zeitfenster
    from datetime import timedelta
    now = datetime.now()
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")

    new_yesterday = [l for l in all_listings if l.get('first_seen', '') >= yesterday]
    new_this_week = [l for l in all_listings if l.get('first_seen', '') >= week_ago]

    # Listing Cards HTML generieren
    def generate_listing_card(listing: Dict, is_new: bool = False) -> str:
        cat = listing.get('category', 'sonstiges')
        cat_colors = {
            'fahrzeug': 'bg-red-500',
            'ersatzteil': 'bg-blue-500',
            'modell': 'bg-purple-500',
            'suchgesuch': 'bg-amber-500',
            'sonstiges': 'bg-slate-500'
        }
        cat_icons = {
            'fahrzeug': '🚜',
            'ersatzteil': '🔧',
            'modell': '🎮',
            'suchgesuch': '🔍',
            'sonstiges': '📦'
        }

        img_url = listing.get('image_url', '')
        fallback_div = '<div class=&quot;w-full h-48 bg-gradient-to-br from-slate-700 to-slate-900 flex items-center justify-center text-4xl&quot;>🚜</div>'
        if img_url:
            img_html = f'<img src="{img_url}" alt="" class="w-full h-48 object-cover" loading="lazy" onerror="this.parentElement.innerHTML=\'{fallback_div}\'">'
        else:
            img_html = '<div class="w-full h-48 bg-gradient-to-br from-slate-700 to-slate-900 flex items-center justify-center text-4xl">🚜</div>'

        price = listing.get('price_numeric')
        if price:
            price_html = f'<span class="text-lg font-bold text-emerald-400">{price:,.0f} €</span>'.replace(',', '.')
        elif listing.get('price'):
            price_html = f'<span class="text-lg font-bold text-emerald-400">{listing["price"]}</span>'
        else:
            price_html = '<span class="text-slate-400">Preis auf Anfrage</span>'

        location = listing.get('location', '')
        location_html = f'<span class="text-slate-400 text-sm">📍 {location}</span>' if location else ''

        new_badge = '<span class="absolute top-2 left-2 bg-emerald-500 text-white text-xs font-bold px-2 py-1 rounded-full animate-pulse">NEU</span>' if is_new else ''

        title = listing.get('title', '')[:80]
        if len(listing.get('title', '')) > 80:
            title += '...'

        first_seen = listing.get('first_seen', '')[:10]
        new_ring = 'ring-2 ring-emerald-500/50' if is_new else ''

        return f'''
        <div class="listing-card group bg-slate-800 rounded-xl overflow-hidden border border-slate-700 hover:border-slate-500 transition-all duration-300 hover:shadow-xl hover:shadow-slate-900/50 hover:-translate-y-1 {new_ring}"
             data-category="{cat}"
             data-country="{listing.get('country', 'XX')}"
             data-price="{listing.get('price_numeric', 0)}"
             data-first-seen="{first_seen}">
            <div class="relative">
                {img_html}
                {new_badge}
                <span class="absolute top-2 right-2 {cat_colors.get(cat, 'bg-slate-500')} text-white text-xs font-medium px-2 py-1 rounded-full">
                    {cat_icons.get(cat, '📦')} {cat.title()}
                </span>
            </div>
            <div class="p-4">
                <h3 class="font-semibold text-white mb-2 line-clamp-2 group-hover:text-emerald-400 transition-colors">
                    <a href="{listing.get('url', '#')}" target="_blank" rel="noopener">{title}</a>
                </h3>
                <div class="flex items-center justify-between mb-2">
                    {price_html}
                    <span class="text-xs bg-slate-700 px-2 py-1 rounded text-slate-300">
                        {listing.get('country', 'XX')} · {listing.get('platform', '')}
                    </span>
                </div>
                {location_html}
            </div>
        </div>
        '''

    # Alle Listing Cards
    listing_cards = '\n'.join([
        generate_listing_card(l, l.get('first_seen', '').startswith(today))
        for l in all_listings[:300]
    ])

    # Country options für Filter
    country_options = '\n'.join([
        f'<option value="{code}">{code} ({count})</option>'
        for code, count in sorted(countries.items(), key=lambda x: -x[1])
    ])

    html = f'''<!DOCTYPE html>
<html lang="de" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MB-trac Finder</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ font-family: 'Inter', sans-serif; }}
        .line-clamp-2 {{
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .stat-card {{
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.8) 100%);
            backdrop-filter: blur(10px);
        }}
        .glass {{
            background: rgba(30, 41, 59, 0.6);
            backdrop-filter: blur(10px);
        }}
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: #1e293b; }}
        ::-webkit-scrollbar-thumb {{ background: #475569; border-radius: 4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #64748b; }}
    </style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen">
    <!-- Header -->
    <header class="sticky top-0 z-50 glass border-b border-slate-700">
        <div class="max-w-7xl mx-auto px-4 py-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <span class="text-3xl">🚜</span>
                    <div>
                        <h1 class="text-xl font-bold text-white">MB-trac Finder</h1>
                        <p class="text-xs text-slate-400">Europaweit Inserate finden</p>
                    </div>
                </div>
                <div class="flex items-center gap-4">
                    <span class="text-sm text-slate-400">
                        Aktualisiert: {datetime.now().strftime('%d.%m.%Y %H:%M')}
                    </span>
                    <button onclick="location.reload()" class="p-2 hover:bg-slate-700 rounded-lg transition-colors" title="Aktualisieren">
                        🔄
                    </button>
                </div>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
        <!-- Stats Grid -->
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
            <div class="stat-card rounded-xl p-4 border border-slate-700">
                <p class="text-slate-400 text-sm mb-1">Gesamt</p>
                <p class="text-2xl font-bold text-white">{len(all_listings)}</p>
            </div>
            <div class="stat-card rounded-xl p-4 border border-emerald-500/30 bg-emerald-500/10">
                <p class="text-emerald-400 text-sm mb-1">Neu heute</p>
                <p class="text-2xl font-bold text-emerald-400">{len(new_today)}</p>
            </div>
            <div class="stat-card rounded-xl p-4 border border-amber-500/30 bg-amber-500/10">
                <p class="text-amber-400 text-sm mb-1">Letzte 24h</p>
                <p class="text-2xl font-bold text-amber-400">{len(new_yesterday)}</p>
            </div>
            <div class="stat-card rounded-xl p-4 border border-red-500/30 bg-red-500/10">
                <p class="text-red-400 text-sm mb-1">🚜 Fahrzeuge</p>
                <p class="text-2xl font-bold text-red-400">{categories.get('fahrzeug', 0)}</p>
            </div>
            <div class="stat-card rounded-xl p-4 border border-blue-500/30 bg-blue-500/10">
                <p class="text-blue-400 text-sm mb-1">🔧 Ersatzteile</p>
                <p class="text-2xl font-bold text-blue-400">{categories.get('ersatzteil', 0)}</p>
            </div>
            <div class="stat-card rounded-xl p-4 border border-slate-600">
                <p class="text-slate-400 text-sm mb-1">Ø Preis</p>
                <p class="text-2xl font-bold text-white">{avg_price:,.0f}€</p>
            </div>
            <div class="stat-card rounded-xl p-4 border border-slate-600">
                <p class="text-slate-400 text-sm mb-1">Länder</p>
                <p class="text-2xl font-bold text-white">{len(countries)}</p>
            </div>
        </div>

        <!-- Filters -->
        <div class="glass rounded-xl p-4 mb-8 border border-slate-700">
            <div class="flex flex-wrap items-center gap-4">
                <div class="flex items-center gap-2">
                    <span class="text-sm text-slate-400">Kategorie:</span>
                    <div class="flex gap-1">
                        <button class="filter-btn active px-3 py-1.5 rounded-lg text-sm font-medium transition-all" data-filter="all">
                            Alle
                        </button>
                        <button class="filter-btn px-3 py-1.5 rounded-lg text-sm font-medium transition-all" data-filter="fahrzeug">
                            🚜 Fahrzeuge
                        </button>
                        <button class="filter-btn px-3 py-1.5 rounded-lg text-sm font-medium transition-all" data-filter="ersatzteil">
                            🔧 Teile
                        </button>
                        <button class="filter-btn px-3 py-1.5 rounded-lg text-sm font-medium transition-all" data-filter="modell">
                            🎮 Modelle
                        </button>
                    </div>
                </div>

                <div class="flex items-center gap-2">
                    <span class="text-sm text-slate-400">Zeitraum:</span>
                    <select id="time-filter" class="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500">
                        <option value="all">Alle</option>
                        <option value="today">Heute</option>
                        <option value="24h">Letzte 24h</option>
                        <option value="7d">Letzte 7 Tage</option>
                    </select>
                </div>

                <div class="flex items-center gap-2">
                    <span class="text-sm text-slate-400">Land:</span>
                    <select id="country-filter" class="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500">
                        <option value="all">Alle Länder</option>
                        {country_options}
                    </select>
                </div>

                <div class="flex items-center gap-2">
                    <span class="text-sm text-slate-400">Preis:</span>
                    <select id="price-filter" class="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500">
                        <option value="all">Alle Preise</option>
                        <option value="0-5000">Bis 5.000€</option>
                        <option value="5000-15000">5.000 - 15.000€</option>
                        <option value="15000-30000">15.000 - 30.000€</option>
                        <option value="30000-999999">Über 30.000€</option>
                    </select>
                </div>

                <div class="flex items-center gap-2 ml-auto">
                    <span class="text-sm text-slate-400">Sortieren:</span>
                    <select id="sort-select" class="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500">
                        <option value="newest">Neueste zuerst</option>
                        <option value="price-asc">Preis aufsteigend</option>
                        <option value="price-desc">Preis absteigend</option>
                    </select>
                </div>
            </div>

            <div class="mt-3 flex items-center gap-2">
                <input type="text" id="search-input" placeholder="Suche nach Titel..."
                       class="flex-1 bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-emerald-500 placeholder-slate-400">
                <span id="result-count" class="text-sm text-slate-400">{len(all_listings)} Ergebnisse</span>
            </div>
        </div>

        <!-- Listings Grid -->
        <div id="listings-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {listing_cards}
        </div>

        <!-- Empty State -->
        <div id="empty-state" class="hidden text-center py-16">
            <span class="text-6xl mb-4 block">🔍</span>
            <p class="text-xl text-slate-400">Keine Inserate gefunden</p>
            <p class="text-sm text-slate-500 mt-2">Versuche andere Filtereinstellungen</p>
        </div>
    </main>

    <!-- Footer -->
    <footer class="border-t border-slate-800 mt-16">
        <div class="max-w-7xl mx-auto px-4 py-8 text-center text-slate-500 text-sm">
            <p>MB-trac Finder • {len(all_listings)} Inserate aus {len(countries)} Ländern</p>
            <p class="mt-1">Automatisch aktualisiert • Letzte Aktualisierung: {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
        </div>
    </footer>

    <script>
        // Filter State
        let currentCategory = 'all';
        let currentCountry = 'all';
        let currentPrice = 'all';
        let currentTime = 'all';
        let currentSort = 'newest';
        let searchQuery = '';

        // Datums-Helfer
        const today = new Date().toISOString().slice(0, 10);
        const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
        const weekAgo = new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10);

        // Filter Buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', function() {{
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active', 'bg-emerald-500', 'text-white'));
                this.classList.add('active', 'bg-emerald-500', 'text-white');
                currentCategory = this.dataset.filter;
                applyFilters();
            }});
        }});

        // Set initial active state
        document.querySelector('.filter-btn[data-filter="all"]').classList.add('bg-emerald-500', 'text-white');

        // Time Filter
        document.getElementById('time-filter').addEventListener('change', function() {{
            currentTime = this.value;
            applyFilters();
        }});

        // Country Filter
        document.getElementById('country-filter').addEventListener('change', function() {{
            currentCountry = this.value;
            applyFilters();
        }});

        // Price Filter
        document.getElementById('price-filter').addEventListener('change', function() {{
            currentPrice = this.value;
            applyFilters();
        }});

        // Sort
        document.getElementById('sort-select').addEventListener('change', function() {{
            currentSort = this.value;
            applyFilters();
        }});

        // Search
        document.getElementById('search-input').addEventListener('input', function() {{
            searchQuery = this.value.toLowerCase();
            applyFilters();
        }});

        function applyFilters() {{
            const cards = document.querySelectorAll('.listing-card');
            let visibleCount = 0;
            const cardsArray = Array.from(cards);

            // Sort
            cardsArray.sort((a, b) => {{
                const priceA = parseFloat(a.dataset.price) || 0;
                const priceB = parseFloat(b.dataset.price) || 0;

                if (currentSort === 'price-asc') return priceA - priceB;
                if (currentSort === 'price-desc') return priceB - priceA;
                return 0; // newest - keep original order
            }});

            // Re-append in sorted order
            const grid = document.getElementById('listings-grid');
            cardsArray.forEach(card => grid.appendChild(card));

            // Filter
            cards.forEach(card => {{
                const category = card.dataset.category;
                const country = card.dataset.country;
                const price = parseFloat(card.dataset.price) || 0;
                const firstSeen = card.dataset.firstSeen || '';
                const title = card.querySelector('h3').textContent.toLowerCase();

                let visible = true;

                // Time filter
                if (currentTime === 'today' && firstSeen < today) visible = false;
                if (currentTime === '24h' && firstSeen < yesterday) visible = false;
                if (currentTime === '7d' && firstSeen < weekAgo) visible = false;

                // Category filter
                if (currentCategory !== 'all' && category !== currentCategory) visible = false;

                // Country filter
                if (currentCountry !== 'all' && country !== currentCountry) visible = false;

                // Price filter
                if (currentPrice !== 'all') {{
                    const [min, max] = currentPrice.split('-').map(Number);
                    if (price < min || price > max) visible = false;
                }}

                // Search filter
                if (searchQuery && !title.includes(searchQuery)) visible = false;

                card.style.display = visible ? '' : 'none';
                if (visible) visibleCount++;
            }});

            // Update count
            document.getElementById('result-count').textContent = visibleCount + ' Ergebnisse';

            // Empty state
            document.getElementById('empty-state').classList.toggle('hidden', visibleCount > 0);
            document.getElementById('listings-grid').classList.toggle('hidden', visibleCount === 0);
        }}
    </script>
</body>
</html>
'''

    output_path.write_text(html, encoding='utf-8')
    print(f"✨ Modernes Dashboard generiert: {output_path}")


if __name__ == "__main__":
    from pathlib import Path

    BASE_DIR = Path(__file__).parent
    DB_PATH = BASE_DIR / "data" / "mbtrac.json"
    OUTPUT_PATH = BASE_DIR / "dashboard.html"

    generate_modern_dashboard(DB_PATH, OUTPUT_PATH)

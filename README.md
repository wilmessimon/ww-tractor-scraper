# 🚜 MB-trac European Scraper

Ein automatisierter Crawler, der täglich europaweit nach gebrauchten **MB-trac Traktoren** sucht.

## 📋 Features

- **100+ Plattformen** in 30+ europäischen Ländern
- **Automatische Duplikaterkennung** via SQLite
- **API + Web-Oberfläche** zur Übersicht aller Inserate und Plattformläufe
- **Tägliche Ausführung** via Cron oder manuell
- **Modulare Architektur** - einfach erweiterbar

## 🗺️ Abgedeckte Länder

| Region | Länder |
|--------|--------|
| DACH + Benelux | 🇩🇪 🇦🇹 🇨🇭 🇳🇱 🇧🇪 🇱🇺 |
| Nordeuropa | 🇳🇴 🇸🇪 🇫🇮 🇩🇰 🇮🇸 |
| Westeuropa | 🇬🇧 🇮🇪 🇫🇷 |
| Südeuropa | 🇪🇸 🇵🇹 🇮🇹 🇬🇷 🇲🇹 🇨🇾 |
| Osteuropa | 🇵🇱 🇨🇿 🇸🇰 🇭🇺 🇷🇴 🇧🇬 🇺🇦 🇲🇩 |
| Balkan | 🇭🇷 🇷🇸 🇸🇮 🇧🇦 🇲🇪 🇲🇰 🇦🇱 🇽🇰 |
| Baltikum | 🇪🇪 🇱🇻 🇱🇹 |

## 🚀 Installation

```bash
# Repository klonen / Dateien kopieren
cd mbtrac-scraper

# Python-Abhängigkeiten installieren
pip install -r requirements.txt

# Optional: Virtual Environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📖 Verwendung

### Erster Scan (alle Plattformen)

```bash
python scraper.py
```

### Nur bestimmte Länder

```bash
python scraper.py --countries DE AT CH
```

### Nur High-Priority-Plattformen (schneller)

```bash
python scraper.py --priority high
```

### Nur Dashboard aktualisieren

```bash
python scraper.py --dashboard-only
```

### API und Oberfläche starten

```bash
uvicorn app:app --reload
```

Dann im Browser öffnen:

```bash
http://127.0.0.1:8000
```

### Statistiken anzeigen

```bash
python scraper.py --stats
```

## ⏰ Automatische tägliche Ausführung

### Option 1: Cronjob

```bash
# Crontab öffnen
crontab -e

# Jeden Tag um 8:00 Uhr ausführen
0 8 * * * /pfad/zu/mbtrac-scraper/run_daily.sh
```

### Option 2: Systemd Timer (Linux)

Erstelle `/etc/systemd/system/mbtrac-scraper.service`:

```ini
[Unit]
Description=MB-trac Scraper
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/pfad/zu/mbtrac-scraper
ExecStart=/usr/bin/python3 /pfad/zu/mbtrac-scraper/scraper.py --priority high
User=dein-benutzer
```

Erstelle `/etc/systemd/system/mbtrac-scraper.timer`:

```ini
[Unit]
Description=Run MB-trac Scraper daily

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Aktivieren:

```bash
sudo systemctl enable mbtrac-scraper.timer
sudo systemctl start mbtrac-scraper.timer
```

### Option 3: Windows Task Scheduler

1. Task Scheduler öffnen
2. "Einfache Aufgabe erstellen"
3. Täglich, 08:00 Uhr
4. Programm: `python.exe`
5. Argumente: `C:\pfad\zu\scraper.py --priority high`
6. Starten in: `C:\pfad\zu\mbtrac-scraper`

## 📁 Projektstruktur

```
mbtrac-scraper/
├── scraper.py          # Hauptskript
├── platforms.py        # Plattform-Datenbank (100+ Plattformen)
├── requirements.txt    # Python-Abhängigkeiten
├── run_daily.sh        # Shell-Skript für Cronjob
├── README.md           # Diese Dokumentation
├── dashboard.html      # Generiertes Dashboard (nach erstem Run)
├── app.py              # FastAPI-App für API und UI
├── data/
│   └── mbtrac.db       # SQLite-Datenbank
├── static/
│   └── index.html      # API-basierte Web-Oberfläche
└── logs/
    └── scraper_*.log   # Log-Dateien
```

## 🔧 Anpassungen

### Neue Plattform hinzufügen

Bearbeite `platforms.py`:

```python
"XX": {  # Ländercode
    "country": "Landname",
    "platforms": [
        {
            "name": "Plattform Name",
            "url": "https://example.com",
            "search_url": "https://example.com/search?q=mb+trac",
            "type": "kleinanzeigen",  # oder: agrar_spezialisiert, auktion, fahrzeug_portal
            "search_terms": ["MB-trac", "Mercedes Trac"],
            "priority": "high"  # oder: medium, low
        }
    ]
}
```

### Spezialisierter Scraper

Für Plattformen mit besonderer HTML-Struktur kann ein spezialisierter Scraper erstellt werden:

```python
class MeineScraper(BaseScraper):
    def scrape(self) -> List[Listing]:
        # Eigene Implementierung
        pass
```

## 📊 Oberfläche und API

Die neue Oberfläche lädt Daten direkt über die lokale API:

- `/api/listings` liefert Inserate
- `/api/stats` liefert Kennzahlen und den letzten Gesamtlauf
- `/api/platform-runs/latest` zeigt den letzten Plattformstatus mit Fehlern und leeren Läufen

Die Seite unter `http://127.0.0.1:8000` zeigt diese Daten direkt an.

## ⚠️ Hinweise

- **Rate Limiting**: Der Scraper wartet zwischen Requests. Erhöhe bei Problemen die Wartezeit in `scraper.py`.
- **Rechtliche Aspekte**: Beachte die Nutzungsbedingungen der jeweiligen Plattformen.
- **Ergebnisqualität**: Nicht alle Plattformen haben exakte HTML-Strukturen. Der generische Scraper versucht, die wichtigsten Daten zu extrahieren.
- **Abhängigkeiten**: Vor dem ersten Lauf müssen die Pakete aus `requirements.txt` installiert sein.

## 🔍 Suchbegriffe nach Sprache

| Sprache | Suchbegriffe |
|---------|--------------|
| Deutsch | MB-trac, Mercedes Trac, Traktor |
| Englisch | MB-trac, tractor, agricultural |
| Französisch | MB-trac, tracteur, matériel agricole |
| Polnisch | MB trac, ciągnik, maszyny rolnicze |
| Tschechisch | MB trac, traktor, zemědělské stroje |
| etc. | (siehe platforms.py für vollständige Liste) |

## 📝 Lizenz

Dieses Projekt ist für den privaten Gebrauch bestimmt.

---

**Viel Erfolg bei der MB-trac Suche!** 🚜

# MB-trac Scraper - Online Deployment

## Schnellstart (5 Minuten)

### 1. GitHub Repository erstellen

```bash
cd mbtrac-scraper
git init
git add .
git commit -m "Initial commit: MB-trac Scraper"
```

Auf GitHub ein neues Repository erstellen (z.B. `mbtrac-scraper`), dann:

```bash
git remote add origin https://github.com/DEIN-USERNAME/mbtrac-scraper.git
git branch -M main
git push -u origin main
```

### 2. GitHub Pages aktivieren

1. Gehe zu **Settings** → **Pages**
2. Source: **GitHub Actions** auswählen
3. Fertig! Die Seite wird automatisch deployed

### 3. Scraper manuell starten (erster Test)

1. Gehe zu **Actions** → **MB-trac Scraper**
2. Klick **Run workflow** → **Run workflow**
3. Warte ca. 5-10 Minuten
4. Dashboard ist dann live unter: `https://DEIN-USERNAME.github.io/mbtrac-scraper/`

## Zeitplan

Der Scraper läuft automatisch 4x am Tag:

| Uhrzeit (UTC) | Uhrzeit (MEZ) |
|---|---|
| 06:00 | 07:00 |
| 12:00 | 13:00 |
| 18:00 | 19:00 |
| 00:00 | 01:00 |

## Architektur

```
GitHub Actions (Cron 4x/Tag)
    ↓
scraper.py (crawlt ~100 Plattformen)
    ↓
data/mbtrac.json (Datenbank)
    ↓
dashboard_generator.py → docs/index.html
    ↓
GitHub Pages (statische Seite)
```

## Anpassen

### Andere Zeiten
In `.github/workflows/scraper.yml` die Cron-Zeile ändern:
```yaml
- cron: '0 6,12,18,0 * * *'  # 4x am Tag
- cron: '0 */6 * * *'         # Alle 6 Stunden
- cron: '0 8 * * *'           # 1x am Tag um 8:00
```

### Nur bestimmte Länder
```yaml
run: python scraper.py --countries DE AT CH
```

## Troubleshooting

- **Actions laufen nicht:** Prüfe ob Actions aktiviert sind (Settings → Actions → General)
- **Pages zeigt nichts:** Prüfe ob `docs/index.html` existiert
- **Scraper Timeout:** Reduziere Worker: `--workers 2`

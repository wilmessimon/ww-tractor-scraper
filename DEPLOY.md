# MB-trac Scraper - API Deployment

## Schnellstart

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

### 2. API starten

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

### 3. Scraper manuell starten (erster Test)

1. Gehe zu **Actions** → **MB-trac Scraper**
2. Klick **Run workflow** → **Run workflow**
3. Warte ca. 5-10 Minuten
4. Oberfläche ist dann live unter: `http://SERVER:8000/`

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
Scraper / Cron / GitHub Actions
    ↓
scraper.py (crawlt ~100 Plattformen)
    ↓
data/mbtrac.db
    ↓
FastAPI (`app.py`)
    ↓
Web-UI + API
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
- **UI zeigt nichts:** Prüfe ob `uvicorn app:app` läuft und `data/mbtrac.db` existiert
- **Scraper Timeout:** Reduziere Worker: `--workers 2`

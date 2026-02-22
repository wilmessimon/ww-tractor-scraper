#!/bin/bash
#
# MB-trac Scraper - Tägliches Ausführungsskript
#
# Installation als Cronjob:
#   crontab -e
#   0 8 * * * /pfad/zu/mbtrac-scraper/run_daily.sh
#
# Oder mit systemd timer für robustere Ausführung

set -e

# Verzeichnis des Skripts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Logging
LOG_FILE="$SCRIPT_DIR/logs/cron_$(date +%Y%m%d).log"
mkdir -p "$SCRIPT_DIR/logs"

echo "========================================" >> "$LOG_FILE"
echo "Start: $(date)" >> "$LOG_FILE"

# Virtual Environment aktivieren (falls vorhanden)
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# Scraper ausführen
# --priority high: Nur die wichtigsten Plattformen (schneller)
# Ohne --priority: Alle Plattformen (umfassender)
python3 "$SCRIPT_DIR/scraper.py" --priority high --workers 3 >> "$LOG_FILE" 2>&1

echo "Ende: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Optional: Desktop-Benachrichtigung bei neuen Inseraten
# (Erfordert notify-send auf Linux oder terminal-notifier auf macOS)
NEW_COUNT=$(grep "Neue Inserate:" "$LOG_FILE" | tail -1 | grep -oP '\d+' || echo "0")
if [ "$NEW_COUNT" -gt "0" ]; then
    if command -v notify-send &> /dev/null; then
        notify-send "MB-trac Scraper" "$NEW_COUNT neue Inserate gefunden!"
    elif command -v terminal-notifier &> /dev/null; then
        terminal-notifier -title "MB-trac Scraper" -message "$NEW_COUNT neue Inserate gefunden!"
    fi
fi

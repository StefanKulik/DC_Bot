# Discord Bot mit Datenbank und GitHub Pages

Dieses Projekt erweitert den vorhandenen `discord.py`-Bot um ein einfaches Inhaltsmodul:

- Der Bot speichert Inhalte in einer PostgreSQL-Datenbank.
- Ein Export-Skript schreibt diese Inhalte als JSON nach `docs/data/site-data.json`.
- GitHub Pages stellt die statische Webseite aus dem `docs/`-Ordner bereit.

Wichtig: GitHub Pages kann keine Datenbank direkt auslesen. Deshalb ist der saubere Weg hier:
`Discord Bot -> PostgreSQL -> JSON-Export -> GitHub Pages`

## Funktionen

- Slash-Commands zum Verwalten von Web-Inhalten direkt in Discord
- Datenhaltung in PostgreSQL ueber `asyncpg`
- Statische Webseite in `docs/`
- GitHub-Actions-Workflow fuer Export und Deployment

## Neue Slash-Commands

- `/website_config`
  Konfiguriert Seitentitel, Beschreibung, Einladungslink und Akzentfarbe pro Server.
- `/website_add`
  Legt einen neuen Eintrag fuer die Webseite an.
- `/website_list`
  Zeigt die letzten gespeicherten Eintraege an.
- `/website_publish`
  Schaltet einen Eintrag sichtbar oder unsichtbar.
- `/website_delete`
  Loescht einen Eintrag.

## Projektstruktur

```text
Bot.py
cogs/Web/Website.py              Discord-Commands fuer Website-Inhalte
config/WebsiteStore.py          Gemeinsame DB-Logik und Validierung
scripts/export_site_data.py     Exportiert DB-Inhalte nach docs/data/site-data.json
docs/index.html                 GitHub-Pages-Seite
docs/styles.css
docs/app.js
.github/workflows/pages.yml     Export + Deployment
```

## Einrichtung lokal

1. Virtuelle Umgebung aktivieren
2. Abhaengigkeiten installieren
3. `config/.env` anlegen
4. Bot starten
5. Export-Skript ausfuehren

Beispiel:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python Bot.py
python scripts/export_site_data.py
```

## Beispiel fuer `config/.env`

Siehe [config/.env.example](config/.env.example).

Wichtige Variablen:

- `TOKEN`
- `OWNER`
- `DATABASE_URL`
- `DEFAULT_PREFIX`
- `SITE_PROJECT_NAME`
- `SITE_PROJECT_TAGLINE`

## GitHub Pages aktivieren

1. Repository auf GitHub pushen
2. Unter `Settings -> Pages` als Source `GitHub Actions` auswaehlen
3. Unter `Settings -> Secrets and variables -> Actions` das Secret `DATABASE_URL` setzen
4. Optional Repository-Variablen setzen:
   - `SITE_PROJECT_NAME`
   - `SITE_PROJECT_TAGLINE`
   - `DISCORD_SERVER_INVITE`

Der Workflow `.github/workflows/pages.yml` exportiert die Daten und deployt anschliessend die Seite.

## Hinweis zur Datenbank

Der Export liest ausschliesslich veroefentlichte Eintraege (`published = true`) aus. Dadurch kannst du Inhalte im Bot vorbereiten, ohne sie sofort auf der Webseite anzuzeigen.

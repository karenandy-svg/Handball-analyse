# WURFBILD: Authentifizierung und Offline-Synchronisierung

## Phase 1 (in Arbeit)
FastAPI, SQLite, Argon2id-Passwörter und opaque HttpOnly-Sitzungscookies.
Der Server liefert aktuell nur API-Endpunkte. Noch **nicht produktiv einsetzen**:
Tests, dauerhaftes Login-Rate-Limiting, Session-Verwaltung, Passwort-Reset,
geschütztes Ausliefern aller App-Dateien und Nginx-Integration fehlen.

### Lokale Entwicklung
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
export WURFBILD_DB_PATH="$PWD/.local/wurfbild.sqlite3"
python -m backend.create_admin admin
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
API erwartet Origin: https://wurfbilder.duckdns.org bei mutierenden Anfragen.
Produktionsbetrieb ausschließlich hinter TLS-Reverse-Proxy.

## Offline- und Konfliktkonzept (geplant)
- Ein Spiel hat genau einen aktiven Bearbeiter. Die Sperre ist serverseitig,
  durch eine zufällige Bearbeitungs-ID und Benutzer/Gerät gebunden.
- Online vor dem Offlinegehen: Spiel exklusiv übernehmen; lokale Berechtigung
  mit serverseitig vermerktem Offline-Bearbeitungsfenster ausstellen.
- Solange Offline-Änderungen ausstehen, Spiel **nicht** durch bloßen
  Verbindungsabbruch freigeben. Nach Ablauf der Offline-Frist nur durch
  explizite Administrator-Übernahme mit Konfliktwarnung freigeben.
- Offline in IndexedDB: Ereignisse mit UUID, Spiel-ID, Basisversion,
  fortlaufender lokaler Sequenz und Änderungsinhalt dauerhaft ablegen.
- Beim Wiederverbinden idempotente Übertragung; UUIDs serverseitig eindeutig
  speichern, um Doppelwürfe bei Wiederholungen zu verhindern.
- Version und Bearbeitungs-ID bei jedem Schreibzugriff serverseitig prüfen.
  Bei Konflikten nicht überschreiben: lokale Änderungen behalten,
  Warnung zeigen, manuelle Prüfung/Übernahme ermöglichen.
- Nur bestätigte Ereignisse als synchronisiert markieren. Spiel erst
  nach erfolgreicher Übertragung und bestätigter Freigabe entsperren.
- Andere Trainer können synchronisierte Daten lesen, aber nicht bearbeiten.
  Offline neu erfasste Würfe sind bis zur Synchronisierung nicht sichtbar.
- Erst nach sicherer Implementierung Offline-Caching geschützter App-Dateien
  und gespeicherter Daten freigeben; beim Logout lokale sensible Daten löschen
  oder verschlüsseln und Cache-Isolation zwischen Konten prüfen.
- Bestehende localStorage-Daten `wurfbild-v1` über validierten Import migrieren;
  niemals automatisch bestehende zentrale Daten überschreiben.

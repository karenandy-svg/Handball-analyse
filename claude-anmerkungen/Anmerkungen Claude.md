# Anmerkungen Claude – Handball-analyse (WURFBILD)

Stand: 24.11.2026 · analysierter Commit: `bbf10a3`
Umfang: alle Dateien in `dist/`, `tests/` und `tools/` (ca. 109 KB Quelltext inklusive Tests und CSS, davon rund 75 KB JavaScript und Python)

**Vorgehen:** Code vollständig gelesen, `node --check` auf allen JS-Dateien, die vorhandenen Tests (`tests/data.test.cjs`, alle drei Blöcke grün) und `py_compile` für das Python-Tool ausgeführt. Befunde mit **★** habe ich zusätzlich mit kleinen Testskripten nachgestellt (die Skripte liegen nicht im Repo). Alles ohne ★ ist aus dem Code abgeleitet und nicht ausgeführt oder auf einem Gerät getestet.

Diese Datei liegt bewusst außerhalb von `dist/`, damit sie nicht mit der Website veröffentlicht wird.

---

## Kurzfazit

Für ein Projekt ohne Abhängigkeiten ist die Fachlogik solide und die Datenvalidierung ungewöhnlich sorgfältig. Die Schwachstellen liegen an den Rändern: beim Laden und Speichern der lokalen Daten, bei einzelnen Bedienelementen, die Daten zerstören können, und beim Offlinebetrieb in der Halle. Sechs Punkte sind klein genug, um sie in einem Zug zu beheben (Nr. 1–6). Die Architektur (Nr. 9) ist das größte Wartbarkeitsthema, aber nichts, was akut etwas kaputt macht.

## Was gut gelöst ist

- **Datenschutz der eigenen Daten:** `validImport` prüft Struktur, Wertebereiche, doppelte IDs und Querverweise sehr genau. Alte Sicherungen bleiben kompatibel (`legacyResults`, optionale Felder).
- **Ausgabe:** HTML wird fast überall mit `esc()` ausgegeben, und im CSV-Export sind Formelzeichen (`= + @ -`) entschärft.
- **Handball4all-Import:** prüft vor jeder Änderung (keine halb geschriebenen Daten), gleicht Torfolge und Endstand ab, ist idempotent und lehnt im Zweifel ab (fail-closed). Offizielle Tore bleiben von eigenen Würfen getrennt, und es werden keine Positionen erfunden.
- **Fachlich richtige Kennzahlen:** Fangquote als gehalten / (gehalten + Gegentore), Torhüter als Momentaufnahme am Wurf gespeichert, Spielerstatistik getrennt nach Mannschaft und Nummer.
- **Tests** prüfen echte Fachlogik (Angriffswechsel, Torhüterhistorie, Filter-Schnittmengen, Altdaten) statt nur Syntax.

---

## Befunde

### Hoch

**1 ★ Importierte IDs gelangen ungeprüft in HTML-Attribute (XSS über Sicherungsdatei)**
`validImport` (`dist/app.js`, Zeile 48) prüft Team-, Spiel- und Wurf-IDs nur auf `typeof === 'string'`. Beim Rendern landen sie ohne `esc()` in Attributen: `data-open`, `data-deletegame`, `data-editteam` (`app.js`), `data-team`, `data-history` (`match.js`) und `data-reference` (`h4-import.js`).
Nachgestellt: Ein Spiel mit der ID `g" onclick="alert(1)` wird akzeptiert, und die Spielliste enthält danach ein `onclick`-Attribut. Weil Sicherungsdateien zwischen Geräten und Personen getauscht werden, kann so eine fremde Datei Script ausführen und den kompletten `localStorage` lesen oder verändern.
*Behebung:* IDs in `validImport` auf `/^[\w-]{1,64}$/` beschränken und zusätzlich in allen Templates `esc()` verwenden (zwei Schutzschichten). Aufwand klein.

**2 ★ Unerwarteter Inhalt im `localStorage` legt die App lahm**
`dist/app.js`, Zeile 4, fängt nur Parse-Fehler ab. Nachgestellt: `{}` oder `null` führen schon beim Start zu einem `TypeError`, ein Spiel ohne `shots` erst beim Öffnen dieses Spiels – jeweils weißer Bildschirm ohne Meldung. Der Hinweis „Bitte eine Sicherung importieren“ erscheint nur bei syntaktisch kaputtem JSON. Dort kommt hinzu: Die App startet mit leerer Datenbank, und schon das `pagehide`-Ereignis (`persist()`, Zeile 51) überschreibt den defekten Rohstring mit dieser leeren Datenbank, ohne dass er vorher gesichert wurde.
*Behebung:* Nach `JSON.parse` dieselbe Prüfung wie beim Import anwenden. Bei Fehlschlag den Rohstring unter einem zweiten Schlüssel (z. B. `wurfbild-v1-defekt`) ablegen, mit leerer Datenbank starten und deutlich darauf hinweisen. Alle Spieldaten liegen nur an dieser einen Stelle, deshalb lohnt sich der Aufwand.

**3 ★ Halbzeit-Schalter kann mit einem Doppeltipp die Spielzeit auf 00:00 zurücksetzen**
`actions.period` (`dist/team-features.js`, Zeile 35) schaltet zwischen 1. und 2. Halbzeit um und überschreibt die Zeit: 2. HZ → Halbzeitlänge, 1. HZ → 0. Nachgestellt: 18:20 → 25:00 → 00:00. Der Button sitzt direkt neben der Uhr und ist als `1. HZ ⇄` beschriftet, ein versehentlicher zweiter Tipp ist auf dem iPad schnell passiert. Neue Würfe bekommen dann falsche Zeiten, und der Abgleich mit Handball4all (±10 s) findet keine Treffer mehr.
*Behebung:* Zeit nur beim Wechsel 1 → 2 setzen (`Math.max(elapsed, halfMinutes*60)`), beim Zurückwechsel die Zeit behalten oder zuvor bestätigen lassen.

### Mittel

**4 ★ Auswertungsfilter zeigt auf gelöschte Spiele**
Der Löschen-Handler (`app.js`, `bind`) entfernt das Spiel, räumt aber `filter.games` nicht auf. Nachgestellt: Filter = [g1], g1 löschen → Auswertung leer, Filteranzeige „1 Spiel“, obwohl ein weiteres Spiel existiert. Erst ein erneutes Öffnen des Filters behebt es.
*Behebung:* Nach dem Löschen `filter.games` bereinigen, und `selectedGames()` sollte unbekannte IDs ignorieren.

**5 ★ Speicherfehler werden als Erfolg gemeldet**
`persist()` gibt bei Fehlern `false` zurück, aber kein Aufrufer wertet das aus. Nachgestellt (voller Speicher): Es erscheint ein Alert, und direkt danach trotzdem der Toast „Wurf gespeichert“. Weil die laufende Uhr alle 5 s `persist()` aufruft, würde bei vollem Speicher außerdem mitten im Spiel wiederholt ein blockierendes `alert()` aufpoppen.
*Behebung:* Rückgabewert prüfen und bei Fehlern „NICHT gespeichert“ melden. Den Alert nur einmal pro Sitzung zeigen und danach ein dauerhaftes Banner („Speichern fehlgeschlagen – bitte Sicherung exportieren“) einblenden.

**6 `crypto.randomUUID()` erfordert einen sicheren Kontext**
`uid()` nutzt `crypto.randomUUID()`, das nur über HTTPS oder `localhost` verfügbar ist (und erst ab Safari 15.4). Der README-Start mit `python3 -m http.server` funktioniert am Rechner, aber wer die App auf dem iPad über die LAN-Adresse (`http://192.168.x.x:8765`) testet, kann keine Mannschaft anlegen. Auch der Service Worker registriert sich dort nicht.
*Behebung:* Fallback in `uid()`, z. B. `crypto.randomUUID?.() || Date.now().toString(36)+Math.random().toString(36).slice(2,10)`, und einen Satz dazu im README.

**7 Service Worker: Network-first ohne Timeout**
`dist/sw.js` fragt zuerst das Netz und fällt erst bei einem Fehler auf den Cache zurück. In Hallen mit schlechtem WLAN hängt der Abruf, bis der Browser selbst aufgibt – die App startet dann sehr langsam oder gar nicht, obwohl alles im Cache liegt. Außerdem wird `handballfeld.jpg` (175 KB) vorab gecacht, obwohl die App es nicht mehr verwendet, und die Cache-Version (`v6`) muss von Hand hochgezählt werden.
*Behebung:* Für die App-Shell „stale-while-revalidate“ oder Network-first mit kurzem Timeout (`AbortController`, ca. 3 s), das Bild aus `FILES` entfernen.

**8 Home-Bildschirm-Symbol auf dem iPad**
Das Manifest enthält nur ein SVG-Icon, `index.html` hat kein `apple-touch-icon`. iOS verwendet für das Symbol auf dem Home-Bildschirm PNGs; SVG wird dafür nicht verlässlich genutzt. Wahrscheinlich erscheint ein Standard- oder Screenshot-Symbol (auf dem Gerät prüfen).
*Behebung:* PNGs (180, 192, 512 px) erzeugen, `<link rel="apple-touch-icon">` und ggf. `apple-mobile-web-app-title` / `-status-bar-style` ergänzen.

**9 Architektur: Funktionen werden global überschrieben**
`match.js`, `team-features.js`, `h4-import.js` und `analysis.js` ersetzen per Zuweisung Funktionen aus `app.js` (`liveView`, `bind`, `teamDialog`, `gamesView`, `teamsView`, `analysisView`, `actions.period`), meist nach dem Muster `const bindBefore=bind; bind=function(){…}`. Folgen:

- Die Ladereihenfolge in `index.html` ist Teil der Logik. `app.js` läuft nicht eigenständig vollständig (Speichern, Import und Mannschaftsansicht), weil es `opposingTeam`, `keeperValue`, `playerFlags` und `isColor` aus späteren Dateien braucht.
- In `app.js` steckt erheblicher toter Code: das ursprüngliche `liveView`, `eventView`, der `data-edit`-Handler und der Platzhalter `analysisView`.
- `render()` wird am Ende jeder Datei erneut aufgerufen (fünfmal beim Start).
- `teamsView` und `gamesView` verändern bereits erzeugtes HTML per `String.replace`. Wenn sich das Markup ändert, greift der Ersatz stillschweigend nicht mehr.

*Empfehlung:* schrittweise auf ES-Module umstellen (`<script type="module">`, weiterhin ohne Build): z. B. `state.js`, `storage.js`, `views/…`. Toten Code löschen und Views direkt anpassen statt zu überschreiben. Die vorhandenen Tests sichern das Refactoring gut ab.

### Niedrig

**10 Wartbarkeit und Tests**
Der Code liegt in sehr langen Zeilen (`validImport` allein hat rund 3 KB in einer Zeile), es gibt keinen Formatter und keinen Linter. Es fehlen `package.json` und eine automatische Ausführung der Tests; die Prüfliste im README nennt `analysis.js`, `team-features.js` und `h4-import.js` nicht. Vorschlag: einmal Prettier laufen lassen, `package.json` mit `"test"`-Skript anlegen und eine GitHub-Action ergänzen (`node --check` plus `node tests/data.test.cjs`).

**11 Python-Importtool (`tools/import_handball4all.py`)**
- `Path.write_text(json.dumps(…, ensure_ascii=False))` (Zeile 119) ohne `encoding='utf-8'`: Unter Windows können Umlaute falsch geschrieben werden oder das Schreiben bricht ab, der Browser liest die Datei aber als UTF-8.
- Der Report-Parser hängt am Textlayout der PDFs. Er scheitert bei Änderungen sauber (fail-closed), hat aber keine Tests. Ein kleiner Text-Fixture-Test würde Layoutänderungen früh sichtbar machen.
- Fehlermeldungen sind englisch, der Rest des Projekts deutsch.

**12 Datenmodell: Spieler nur über Rückennummer**
Namen werden live aus dem aktuellen Kader gelesen, nur der Torhütername wird am Wurf gespeichert. Eine Kaderänderung (neue Nummer oder anderer Name) wirkt deshalb rückwirkend auf alle alten Spiele. Für saisonübergreifende Auswertungen kann das verfälschen. Option: Spieler-ID plus Namens-Momentaufnahme am Wurf (wie bei `keeperName`). Außerdem gibt es keine Funktion „Mannschaft löschen oder zusammenführen“, abweichende Schreibweisen im Handball4all-Import erzeugen also doppelte Mannschaften.

**13 Auswertung**
7 Meter ist ein normales Feldsegment und fließt in Trefferquote und Fangquote mit den Feldwürfen zusammen. Es gibt keinen Filter nach Wurfposition oder Halbzeit und keine Verlängerung (`period` nur 1 oder 2).

**14 Kleinigkeiten**
- `analysis.css` und `team-features.css` werden erst am Ende des `<body>` geladen (kurzes Flackern beim Start).
- Das Zeitfeld hat `inputmode="numeric"`, die Eingabe verlangt aber `MM:SS`. Auf Smartphone-Tastaturen fehlt dann der Doppelpunkt (nicht getestet).
- Jeder Tipp rendert die gesamte Ansicht inklusive Feldgrafik neu. Auf älteren iPads könnte das spürbar sein (nicht gemessen).
- `.openai/hosting.json` enthält die Projekt-ID in einem öffentlichen Repository. Vermutlich unkritisch, aber bewusst entscheiden.

---

## Empfohlene Reihenfolge

1. **Schnelle Absicherung (Nr. 1–6):** ID-Validierung, defensives Laden, Halbzeit-Schalter, Filter aufräumen, Speicherfehler anzeigen, `uid()`-Fallback.
2. **Offlinebetrieb in der Halle (Nr. 7, 8):** Service-Worker-Strategie und iPad-Icon.
3. **Wartbarkeit (Nr. 9, 10):** toten Code löschen, Formatter und Tests in CI, danach schrittweise auf Module umstellen.
4. **Fachliche Erweiterungen (Nr. 12, 13):** Spieler-IDs, Filter nach Wurfposition.

## Nicht geprüft

Verhalten auf einem echten iPad und in Safari, Barrierefreiheit im Detail, CSS-Layout und visuelles Ergebnis, Performance unter Last, ein Live-Lauf des Python-Tools gegen Handball4all und die tatsächliche Hosting-Konfiguration.

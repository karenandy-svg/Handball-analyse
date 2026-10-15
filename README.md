# Handball-analyse · WURFBILD

Web-App für die manuelle Handballanalyse auf dem iPad. Verwaltet Mannschaften, Spiele, Würfe und spielübergreifende Statistiken.

## Spiel erfassen

1. Unter **Mannschaften** mindestens zwei Teams und ihre Trikotnummern anlegen.
2. Unter **Spiele** ein Spiel anlegen oder öffnen.
3. Mannschaft und Spieler links wählen.
4. Das Feldsegment der Wurfposition antippen (Stift, Finger oder Maus).
5. Eines der neun Torsegmente antippen (aus Sicht des Werfers).
6. **Tor**, **Gehalten** oder **Daneben** antippen. Der Wurf wird sofort gespeichert; die Ergebnisschaltflächen werden erst nach Spieler, Feldsegment und Torsegment freigegeben.

Der Spielstand ergibt sich aus den erfassten Toren. Die Spieluhr lässt sich starten, pausieren und direkt anpassen. Beim Antippen des Feldsegments wird die Wurfzeit vorgemerkt. **Technischer Fehler** und **Ballverlust** speichern sofort ein eigenes Ereignis mit Spielzeit und ausgewähltem Spieler (sonst „?“), ohne Feldsegment, Torsegment oder Wurf. Danach wechselt die angreifende Mannschaft. Tore wechseln die Mannschaft ebenfalls; gehaltene und daneben gegangene Würfe sowie Korrekturen nicht. Unter **Spielverlauf** lassen sich Würfe und Ereignisse korrigieren oder löschen. Frühere Laufwege bleiben in vorhandenen Daten und Sicherungen erhalten; neue Einträge benötigen keinen Laufweg.

Die Spielansicht ist für iPads im Querformat ohne Seiten-Scrollen ausgelegt. Sehr große Kader haben eine separat scrollbare Nummernliste; auf Smartphones ist die Ansicht gestapelt. Das Spielfeld verwendet eine klare SVG-Darstellung mit einer einzigen Segmentaufteilung; das ursprüngliche Referenzbild bleibt in der Ablage erhalten.

## Daten & Offlinebetrieb

Daten werden lokal in `localStorage` unter `wurfbild-v1` gespeichert. Vorhandene Daten und alte Sicherungen bleiben kompatibel. Würfe speichern `origin` (Feldsegment), `zone` (Torsegment) und `result`; Ereignisse ohne Wurf stehen separat in `game.events`. Sie beeinflussen keine Wurf-/Fangquoten. Regelmäßig unter **Datensicherung** eine JSON-Sicherung exportieren. Der Import ersetzt nach Bestätigung den lokalen Datenbestand. CSV-Auswertungen enthalten Würfe und Ereignisse, mit leeren Positionsfeldern für Ereignisse und zusätzlichen Spalten für LH und TW.

Es gibt noch keine geräteübergreifende Synchronisierung und keinen Video-Agenten. Der Service Worker hält die App-Dateien nach einem erfolgreichen Onlinebesuch vor; privates Hosting und Offlinebetrieb sind auf dem konkreten iPad zu testen.

## Lokal starten

Keine Installation oder Build-Abhängigkeiten erforderlich:

```sh
python3 -m http.server 8765 --directory dist
```

Danach `http://localhost:8765` im Browser öffnen. Syntax- und Datenprüfungen:

```sh
node --check dist/app.js
node --check dist/match.js
node --check dist/sw.js
node tests/data.test.cjs
```

## Quellcode und Hosting

GitHub: https://github.com/karenandy-svg/Handball-analyse

Bereitstellung: https://handball-spielanalyse.tiny-whale-2048.chatgpt.site

`dist/` enthält den direkt auslieferbaren Quellcode. `.openai/hosting.json` beschreibt die bestehende private Sites-Bereitstellung. GitHub verwaltet den Code; Änderungen auf GitHub werden erst durch eine separate Sites-Bereitstellung auf der Website sichtbar. Hosting-Zugangsberechtigungen gehören weder in Dateien noch in GitHub. Die bestehende Sites-Quellablage bleibt als notwendige Veröffentlichungsablage erhalten.

## Torhüter, Farben und Handball4all

Es gibt keine Torhüterabfrage vor dem Spiel. Links unten über **Kader bearbeiten** steht der gegnerische Torhüter des aktuellen Angriffs. Die Auswahl enthält ausschließlich Spieler mit TW-Kennzeichen sowie „Unbekannt“ und „Leeres Tor“. Die Auswahl bleibt pro Spiel und Mannschaft erhalten. Ohne Auswahl wird ein unbekannter Torhüter gespeichert. Jeder Wurf speichert Nummer, Mannschaft und damaligen Namen des Torhüters; spätere Wechsel ändern historische Einträge nicht. Ein historischer, inzwischen aus dem TW-Kader entfernter Torhüter wird beim Korrigieren nur als nicht auswählbarer Hinweis dargestellt.

Unter **Kader bearbeiten** hat jeder Spieler Checkboxen für **LH** (Linkshänder) und **TW** (Torhüter). Die Merkmale werden in Spielerliste und Auswertung angezeigt und bei neuen Ereignissen/Würfen mitgespeichert. Importierte Kader ersetzen bestehende Merkmale nicht. Eigene Mannschaftsfarben bleiben einstellbar; ohne eigene Farbe gilt Heim Blau und Gast Rot. Die Farbe kennzeichnet Mannschaft, ausgewählten Spieler und Feldsegment. Beim Anlegen eines Spiels sind 20, 25 oder 30 Minuten pro Halbzeit einstellbar; Handball4all-Spiele übernehmen die Importvorgabe.

**Mannschaften → Mannschaften importieren** liest CSV/TSV mit den Spalten `Mannschaft;Nummer;Name;Farbe`. Die Farbe ist optional und verwendet das Format `#2563eb`. Vorschau vor Übernahme. Der CSV-Import ergänzt Kader; vorhandene Nummern können durch die bestätigte Datei aktualisiert werden.

Der Handball4all-Import verwendet die bereits in `karenandy-svg/h4all-statistik` erprobten öffentlichen Endpunkte. Dieses andere Projekt wird nicht verändert. Daten werden zunächst als lokale Importdatei bereitgestellt, nicht live aus der statischen Web-App abgerufen:

```sh
python3 -m pip install pdfplumber
python3 tools/import_handball4all.py --org 216 --league 161291 --half-minutes 25 --reports 20
```

Danach unter **Spiele → Handball4all-Spiel importieren** die erzeugte Datei `output/handball4all-161291.json` auswählen und ein Spiel übernehmen. Die Datei enthält den Spielplan sowie die erfolgreich geprüften Berichte. Berichte mit unklarer Namenszuordnung, fehlenden Kadern oder abweichender Torfolge werden nicht als geprüft übernommen. Nicht gespielte Partien können ohne Kader vorliegen. Ein erneuter Import derselben Liga/Saison/Spiel-ID aktualisiert die Vergleichsdaten und erhält eigene Würfe und Torhüter. Bei widersprüchlichen Spielernamen derselben Nummer stoppt der Import zur manuellen Prüfung.

Offizielle Tore bleiben in `referenceGoals` getrennt von eigenen Würfen. **Abgleich** zeigt Endstand und Zuordnungsvorschläge anhand Team, Rückennummer und maximal 10 Sekunden Zeitabweichung. Das erzeugt keine erfundenen Feld- oder Torsegmente. Automatische Erkennung der Spielanzeige im Video ist noch nicht angeschlossen. Generierte Liga- und Personendaten in `output/` sind von Git und der Website-Veröffentlichung ausgeschlossen.

## Auswertung und Wurfbilder

Unter **Auswertung** lassen sich Mannschaften und Spiele jeweils mehrfach auswählen. Standardmäßig sind alle enthalten; **Übernehmen** wendet die Auswahl an. Der Spielerfilter wurde durch antippbare Zeilen im Spielervergleich ersetzt. Ein Spieler-Wurfbild verwendet dieselbe Spielauswahl und trennt auch bei gleicher Rückennummer nach Mannschaft.

Jeder neue Wurf speichert bereits Feldsegment (`origin`) und Torsegment (`zone`). Das Wurfbild verbindet deren Mittelpunkte. Gleiche Verbindungen werden mit Anzahl und Toren zusammengefasst, durch dickere Linien und eine stärkere rote Färbung hervorgehoben und zusätzlich als Tabelle aufgelistet. Alle Wurfergebnisse zählen zur Häufigkeit. Ältere Einträge ohne vollständige Segmente bleiben in Statistiken und Sicherungen erhalten; die Grafik weist sie als fehlend aus und erfindet keine Positionen.

Die Torhüterauswertung filtert nach **Torhüter-Mannschaft** (`keeperTeam`), unabhängig vom Filter auf angreifende Mannschaften in der Wurfstatistik. Sie zählt gegnerische Würfe aus den gewählten Spielen. Bei mehreren ausgewählten Mannschaften werden deren Torhüter gemeinsam, aber getrennt nach Mannschaft und Nummer angezeigt.

**Ereignisse ohne Wurf** zeigt je Spieler Ballverluste, technische Fehler und deren Summe sowie eine Gesamtzeile. Spieler ohne Ereignisse werden mit null angezeigt; unbekannte Spieler erhalten eine eigene Zeile. Diese Ereignisse verändern keine Wurfquoten. Der CSV-Export berücksichtigt dieselbe Mannschafts- und Spielauswahl.

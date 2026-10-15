# Handball-analyse · WURFBILD

Web-App für die manuelle Handballanalyse auf dem iPad. Verwaltet Mannschaften, Spiele, Würfe und spielübergreifende Statistiken.

## Spiel erfassen

1. Unter **Mannschaften** mindestens zwei Teams und ihre Trikotnummern anlegen.
2. Unter **Spiele** ein Spiel anlegen oder öffnen.
3. Mannschaft und Spieler links wählen.
4. Auf dem Spielfeld mit Apple Pencil, Finger oder Maus einen Laufweg zeichnen.
5. Eines der neun Torsegmente antippen (aus Sicht des Werfers).
6. Ergebnis auswählen und **Wurf speichern** drücken.

Der Spielstand ergibt sich aus den erfassten Toren. Die Spieluhr lässt sich starten, pausieren und direkt anpassen. Beim Zeichnen wird die Wurfzeit vorgemerkt. Bereits erfasste Würfe sind über **Würfe ansehen** korrigierbar. Alte Würfe ohne Laufweg bleiben lesbar; beim Korrigieren in der neuen Ansicht kann ein Laufweg ergänzt werden. Ein abgebrochener Stiftkontakt verwirft die angefangene Zeichnung.

Die Spielansicht ist für iPads im Querformat ohne Seiten-Scrollen ausgelegt. Sehr große Kader haben eine separat scrollbare Nummernliste; auf Smartphones ist die Ansicht gestapelt. Das Spielfeld stammt aus dem vom Nutzer bereitgestellten Bild `Handballfeld.jpg`.

## Daten & Offlinebetrieb

Daten werden lokal in `localStorage` unter `wurfbild-v1` gespeichert. Laufwege enthalten normalisierte Koordinaten zwischen 0 und 1, damit sie unabhängig von der Bildschirmgröße dargestellt werden. Vorhandene Daten bleiben erhalten. Regelmäßig unter **Datensicherung** eine JSON-Sicherung exportieren. Der Import ersetzt nach Bestätigung den lokalen Datenbestand. CSV-Auswertungen enthalten die Wurfdaten; die vollständigen Laufwege stehen in der JSON-Sicherung.

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

Vor der ersten Erfassung beide Torhüter auswählen. Die Auswahl bleibt pro Spiel und Mannschaft erhalten, bis sie geändert wird. Jeder Wurf speichert Nummer, Mannschaft und damaligen Namen des gegnerischen Torhüters. Historische Einträge ändern sich bei einem späteren Torhüterwechsel nicht. „Unbekannt“ und „Leeres Tor“ sind ausdrücklich auswählbar. Neue Tore wechseln das angreifende Team; andere Ergebnisse und Korrekturen tun das nicht.

Eigene Mannschaftsfarben unter **Mannschaften → Bearbeiten** einstellen. Ohne eigene Farbe gilt Heim Blau und Gast Rot. Die Farbe wird an Mannschaftsschaltern, Spielernummern und Laufweg verwendet. Im Torhüterdialog sind 20, 25 oder 30 Minuten pro Halbzeit einstellbar.

**Mannschaften → Mannschaften importieren** liest CSV/TSV mit den Spalten `Mannschaft;Nummer;Name;Farbe`. Die Farbe ist optional und verwendet das Format `#2563eb`. Vorschau vor Übernahme. Der CSV-Import ergänzt Kader; vorhandene Nummern können durch die bestätigte Datei aktualisiert werden.

Der Handball4all-Import verwendet die bereits in `karenandy-svg/h4all-statistik` erprobten öffentlichen Endpunkte. Dieses andere Projekt wird nicht verändert. Daten werden zunächst als lokale Importdatei bereitgestellt, nicht live aus der statischen Web-App abgerufen:

```sh
python3 -m pip install pdfplumber
python3 tools/import_handball4all.py --org 216 --league 161291 --half-minutes 25 --reports 20
```

Danach unter **Spiele → Handball4all-Spiel importieren** die erzeugte Datei `output/handball4all-161291.json` auswählen und ein Spiel übernehmen. Die Datei enthält den Spielplan sowie die erfolgreich geprüften Berichte. Berichte mit unklarer Namenszuordnung, fehlenden Kadern oder abweichender Torfolge werden nicht als geprüft übernommen. Nicht gespielte Partien können ohne Kader vorliegen. Ein erneuter Import derselben Liga/Saison/Spiel-ID aktualisiert die Vergleichsdaten und erhält eigene Würfe und Torhüter. Bei widersprüchlichen Spielernamen derselben Nummer stoppt der Import zur manuellen Prüfung.

Offizielle Tore bleiben in `referenceGoals` getrennt von eigenen Würfen. **Abgleich** zeigt Endstand und Zuordnungsvorschläge anhand Team, Rückennummer und maximal 10 Sekunden Zeitabweichung. Das erzeugt keine erfundenen Torsegmente oder Laufwege. Automatische Erkennung der Spielanzeige im Video ist noch nicht angeschlossen. Generierte Liga- und Personendaten in `output/` sind von Git und der Website-Veröffentlichung ausgeschlossen.

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

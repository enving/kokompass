# kokompass

Vorlage für einen **persönlichen Kompass**: das Gedächtnis einer Person für ihre KI-Agenten. Wer sie ist, was sie
will, was sie entschieden hat und was offen ist, als Markdown-Dateien mit Frontmatter
([OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)) und ein kleiner
Befehl `kompass`, der jeder Sitzung den Stand in 20 Zeilen gibt. Funktioniert mit jedem Agenten, der eine Shell hat
(Claude Code, Codex, OpenCode, Vibe). Der Grundbetrieb braucht nur Python und Git; externe Quellen sind optional.

Der Kompass gehört der Person und bleibt privat. Kokompass liefert das gemeinsame System mit einer leeren Vorlage.
Eine ausgefüllte private Instanz nutzt dieselben Funktionen mit ihren eigenen Daten und Einstellungen.

## Aufbau

```text
kokompass/
├── METHODE.md        # die Regeln (zuständige Quelle): Knotentypen, Pflichtfelder, Regeln für Agenten
├── BEITRAGEN.md      # wie Verbesserungen aus dem eigenen Kompass zurückkommen
├── KONTEXTQUELLEN.md # Quellen anbinden (Notizen, Fotos, Memos …) und die Rolle des Dirigenten
├── vorlage/          # Startgerüst einer eigenen Instanz
├── beispiel/         # erfundene Person „Mara“, zeigt jeden Knotentyp
├── werkzeuge/        # gemeinsame Laufzeit, Navigation, Quellen, Berichte und Fortsetzungen
└── tests/            # laufen gegen beispiel/ und vorlage/
```

## Eigenen Kompass anlegen

```bash
git init mein-kompass && cd mein-kompass
cp -R /pfad/zu/kokompass/vorlage/. .
git submodule add https://github.com/enving/kokompass kern
ln -s "$PWD/kern/werkzeuge/kompass" ~/.local/bin/kompass
export KOMPASS_DIR="$PWD"        # dauerhaft in die Shell-Konfiguration
kompass diagnose                 # lokale Einrichtung prüfen
kompass                          # Startausgabe
```

Dann `person/ich.md` und `person/ziele.md` ausfüllen und in `kontextquellen.md` eintragen, woraus der Kompass
lernen soll ([Anleitung](KONTEXTQUELLEN.md)). Damit jede Sitzung mit dem Stand beginnt:

| Werkzeug | Einbindung |
|---|---|
| Claude Code, Codex | Sitzungsstart-Hook, der `kompass` ausführt |
| OpenCode | `kompass datei ~/.agents/KOMPASS_STAND.md` per Cron, die Datei in `instructions` |
| alles andere | Anweisung in `AGENTS.md`: zuerst `kompass` ausführen |

`kompass vorwissen --auto` eignet sich als Hook beim Absenden einer Frage: Er meldet sich nur, wenn die Frage
nach einer Bewertung klingt und der Kompass dazu schon etwas weiß.

## Funktionen

| Aufgabe | Befehl |
|---|---|
| Persönlicher Kontext und vorhandenes Wissen | `kompass`, `kompass vorwissen "Frage"` |
| Projekt finden und aktuelle Originalquellen erschließen | `kompass repos`, `kompass kontext "Thema"` |
| Eingänge und Repo-Übergaben erfassen | `kompass scan`, `kompass uebergaben` |
| Quellen versioniert sichern, Berichte und Export | `kompass eingang`, `bericht`, `neutral`, `export`, `alles` |
| Wiki-Quellen als Entwürfe verarbeiten | `kompass pflege --scan` bzw. ausdrücklich konfigurierte Verarbeitung |
| GitHub-Workflows und Kontomitteilungen | `kompass github-fehler --uebersicht`, `--kontingente`, `--mails` |
| Fortsetzungen und Blocker prüfen | `kompass weiter --abschluss`, `db-import`, `wartet` |
| Lokale Einrichtung und Wissensverweise prüfen | `kompass diagnose`, `pruefen`, optional `validieren` |

Instanzwerte und optionale Installationen sind in [KONTEXTQUELLEN.md](KONTEXTQUELLEN.md#laufzeit-der-eigenen-instanz)
beschrieben. Die leere Vorlage hat keine externen Quellen, keine Modellwahl und keinen aktiven Dirigenten.
Ein erster Scan legt dessen Register pausiert an. Die SQLite-Datenbank ist nur ein optionaler lokaler Spiegel;
Wissen bleibt Markdown. Keine Funktion legt automatisch Zeitpläne an oder startet Bearbeiter.

### Beispiel und Prüfungen

```bash
KOMPASS_DIR=beispiel python3 werkzeuge/kompass.py
KOMPASS_DIR=vorlage python3 werkzeuge/kompass.py diagnose
python3 -m unittest discover tests -v
```

Das Beispiel „Mara“ enthält zwei erfundene Projekt-Verweise. Sie werden erst nutzbar, wenn ihre Pfade
auf eigene Arbeitsbäume zeigen. Der automatisierte Durchlauf in `tests/test_navigation.py` erzeugt dafür
zwei temporäre Git-Repos und prüft Navigation, fehlende Pfade, Blocker und einen unvollständigen Abschluss.
Er liest keine echten Konten und ruft kein Modell auf. Weitere Regressionstests decken Quellenversionen,
unveränderte Originale, Exportkonflikte und den privaten Push-Schutz ab.

### Aktualisieren und Wiederherstellen

Die gemeinsame Laufzeit wird nur in diesem Repo gepflegt. Eine Instanz aktualisiert ihren festgelegten
Kern-Commit nach Prüfung und behält ihre eigenen Dateien. Private Zugangsdaten und Betriebsregister werden
nicht in die Vorlage kopiert. Nach einem Rechnerwechsel zuerst Instanz und Submodul wiederherstellen,
dann die konfigurierten lokalen Pfade prüfen. Für den nicht versionierten Fortsetzungszustand gilt die
[Wiederherstellung in KONTEXTQUELLEN.md](KONTEXTQUELLEN.md#laufzeit-der-eigenen-instanz).

## Wo kokompass eingebunden ist

- **Eine Person:** eigene Instanz, kokompass als Submodul `kern/`. Die eigene Instanz kann ein privates Repo zur
  Versionierung haben; sie ist nie öffentlich.
- **Eine Firma:** [kobetriebssystem](https://github.com/enving/kobetriebssystem) bindet kokompass unter `user/`
  ein, als persönliche Ebene neben dem gemeinsamen Betriebssystem. Wie beide Ebenen voneinander lernen, ist dort
  noch offen.

## Herkunft

Abgeleitet aus einem seit September 2026 täglich genutzten privaten Kompass mit mehreren hundert Knoten. Ergänzt
um Bausteine aus Cole Medins „4 Components of Every Successful AI Second Brain“
([Video](https://www.youtube.com/watch?v=qIWB1yMsqRo)): Kontext-Test für frische Sitzungen, feste Aufgabenliste
nach größeren Änderungen, Automatik erst nach Vertrauen (`pruefung/fragen.md`, METHODE.md).

## Stand

kokompass ist **kein Paket** (kein pip/npm): Man bindet das Repo als Git-Submodul ein, die Version ist
der Commit, auf den das Submodul zeigt; Updates mit `git submodule update --remote kern`. Ein Paket lohnt sich erst,
wenn eine Paketverteilung gebraucht wird. Quellenverarbeitung, Repo-Kontext, Berichte, Export und die lokale
Fortsetzungssteuerung sind Teil der gemeinsamen Laufzeit. Konkrete Host-Anbindungen, Konten und Pfade werden
in jeder Instanz eingerichtet.

Das [Fortsetzungsprotokoll](KONTEXTQUELLEN.md#übergaben-automatisch-fortsetzen-die-person-nahe-am-ablauf)
beschreibt Dauermandat, frische Bearbeiter, Ergebnisprüfung und die Grenze zwischen öffentlichen und privaten
Quellen. Die automatische Ergebnisrückgabe zwischen Bearbeitern benötigt weiterhin eine ausdrücklich eingerichtete Host-Anbindung.

## Die Ko-Familie

kokompass gehört zur Ko-Familie von Digitalalchemisten, offene Werkzeuge für Arbeit mit KI:
[KoBetriebssystem](https://github.com/enving/kobetriebssystem) (gemeinsames Betriebssystem einer Firma, bindet
kokompass ein), [Koprotokoll](https://github.com/enving/Koprotokoll) und
[Kodiktat](https://github.com/enving/kodiktat).

## Lizenz

[MPL-2.0](LICENSE)

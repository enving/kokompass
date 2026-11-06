# kokompass

Vorlage für einen **persönlichen Kompass**: das Gedächtnis einer Person für ihre KI-Agenten. Wer sie ist, was sie
will, was sie entschieden hat und was offen ist, als Markdown-Dateien mit Frontmatter
([OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)) und ein kleiner
Befehl `kompass`, der jeder Sitzung den Stand in 20 Zeilen gibt. Funktioniert mit jedem Agenten, der eine Shell hat
(Claude Code, Codex, OpenCode, Vibe), ohne Datenbank und ohne Cloud.

Der Kompass gehört der Person und bleibt privat. Dieses Repo enthält nur Methode, Vorlage, Werkzeug und ein
erfundenes Beispiel.

## Aufbau

```text
kokompass/
├── METHODE.md        # die Regeln (zuständige Quelle): Knotentypen, Pflichtfelder, Regeln für Agenten
├── BEITRAGEN.md      # wie Verbesserungen aus dem eigenen Kompass zurückkommen
├── KONTEXTQUELLEN.md # Quellen anbinden (Notizen, Fotos, Memos …) und die Rolle des Dirigenten
├── vorlage/          # Startgerüst einer eigenen Instanz
├── beispiel/         # erfundene Person „Mara“, zeigt jeden Knotentyp
├── werkzeuge/        # kompass (Einstieg) und kompass.py (Logik, nur Standardbibliothek)
└── tests/            # laufen gegen beispiel/ und vorlage/
```

## Eigenen Kompass anlegen

```bash
git init mein-kompass && cd mein-kompass
cp -R /pfad/zu/kokompass/vorlage/. .
git submodule add https://github.com/enving/kokompass kern
ln -s "$PWD/kern/werkzeuge/kompass" ~/.local/bin/kompass
export KOMPASS_DIR="$PWD"        # dauerhaft in die Shell-Konfiguration
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

## Wo kokompass eingebunden ist

- **Eine Person:** eigene Instanz, kokompass als Submodul `kern/`. Die eigene Instanz kann ein privates Repo zur
  Versionierung haben; sie ist nie öffentlich.
- **Eine Firma:** [kobetriebssystem](https://github.com/enving/kobetriebssystem) bindet kokompass unter `user/`
  ein, als persönliche Ebene neben dem gemeinsamen Betriebssystem. Wie beide Ebenen voneinander lernen, ist dort
  noch offen (Lückenregister L20–L22 in `PRD.md`).

## Herkunft

Abgeleitet aus einem seit September 2026 täglich genutzten privaten Kompass mit mehreren hundert Knoten. Ergänzt
um Bausteine aus Cole Medins „4 Components of Every Successful AI Second Brain“
([Video](https://www.youtube.com/watch?v=qIWB1yMsqRo)): Kontext-Test für frische Sitzungen, feste Aufgabenliste
nach größeren Änderungen, Automatik erst nach Vertrauen (`pruefung/fragen.md`, METHODE.md).

## Stand

Version 0.1. Noch nicht enthalten, weil an die erste Instanz gebunden: Wissenseingang aus einem Obsidian-Vault,
Lagebild-Bericht, Export. Die erste Instanz stellt erst auf dieses Repo um; was sich dabei als allgemein erweist,
kommt per PR hierher.

## Lizenz

[MPL-2.0](LICENSE)

#!/usr/bin/env python3
"""kompass — Startausgabe, Verbindungen, Prüfung und Vorwissen für einen Kompass (OKF-Bundle).

  kompass               Wer, Ziele, Fragen an die Person, Fristen, offene Aufgaben, Regeln (Startausgabe)
  kompass datei [PFAD]  dieselbe Ausgabe in eine Datei schreiben (für Werkzeuge ohne Sitzungsstart-Hook)
  kompass sync          Verbindungsabschnitte aller Knoten aus dem Frontmatter neu schreiben
  kompass pruefen       fehlender type, tote Verweise; Exit 1 bei Befunden
  kompass vorwissen "Text"   was der Kompass zu den Begriffen schon enthält (vor jeder Bewertung)
  kompass vorwissen --auto   dasselbe für Hooks: Text von stdin, still, wenn es nicht nach Bewertung klingt

Ort des Kompass: Umgebungsvariable KOMPASS_DIR, sonst das aktuelle Verzeichnis.
Name der Person: Feld `name` in person/ich.md. Nur Standardbibliothek, Python 3.9+.
Regeln: METHODE.md im kokompass-Repo.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

WURZEL = Path(os.environ.get("KOMPASS_DIR") or Path.cwd()).resolve()
HEUTE = datetime.date.today()
ALT_TAGE = 30
AUSGENOMMEN = {"index.md", "log.md", "README.md", "AGENTS.md", "CLAUDE.md"}
NICHT_KNOTEN = {"werkzeuge", "kern", "privat", "tests", "node_modules"}
BEZIEHUNGEN = {
    "betrifft": "Betrifft", "belegt_durch": "Belegt durch", "braucht": "Braucht", "blockiert": "Blockiert",
    "nutzt": "Nutzt", "zeigt": "Zeigt", "ueber": "Über", "an": "An",
}
MARKER = re.compile(r"<!-- verbindungen:start -->.*?<!-- verbindungen:ende -->", re.S)


# ------------------------------------------------------------------ Lesen
def frontmatter(text: str) -> tuple[dict, str]:
    """Flache YAML-Frontmatter: Schlüssel: Wert und Listen in eckigen Klammern. Keine Abhängigkeiten."""
    if not text.startswith("---"):
        return {}, text
    ende = text.find("\n---", 3)
    if ende < 0:
        return {}, text
    felder: dict = {}
    for zeile in text[3:ende].strip().splitlines():
        if ":" not in zeile or zeile.startswith((" ", "\t", "-")):
            continue
        k, v = zeile.split(":", 1)
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            v = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
        else:
            v = v.strip("'\"")
        felder[k.strip()] = v
    return felder, text[ende + 4:]


def lies(pfad: Path) -> str:
    try:
        return pfad.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def ist_knoten(pfad: Path) -> bool:
    rel = pfad.relative_to(WURZEL)
    if pfad.name in AUSGENOMMEN or len(rel.parts) < 2:
        return False
    return not (rel.parts[0].startswith(".") or rel.parts[0] in NICHT_KNOTEN)


def laden() -> dict:
    knoten = {}
    for p in sorted(WURZEL.rglob("*.md")):
        if ist_knoten(p):
            fm, body = frontmatter(lies(p))
            knoten["/" + str(p.relative_to(WURZEL))] = {"pfad": p, "fm": fm, "body": body}
    return knoten


def tage_seit(wert) -> int | None:
    try:
        return (HEUTE - datetime.date.fromisoformat(str(wert)[:10])).days
    except ValueError:
        return None


def koerper(pfad: Path) -> str:
    return frontmatter(lies(pfad))[1].split("<!-- verbindungen:start -->")[0]


def name() -> str:
    return frontmatter(lies(WURZEL / "person" / "ich.md"))[0].get("name") or "die Person"


# ------------------------------------------------------------------ Startausgabe
def stand() -> str:
    wer = name()
    z = [f"=== KOMPASS von {wer} (privat) ===",
         f"Ort: {WURZEL}  ·  Regeln: METHODE.md (kokompass) und AGENTS.md der Instanz  ·  Befehl: kompass"]

    # Wer und wohin: abgeleitet aus den fett markierten Kernaussagen, keine Kopie.
    selbstbild = re.findall(r"\*\*(.+?)\*\*", koerper(WURZEL / "person" / "ich.md"))
    ziele_pfad = WURZEL / "person" / "ziele.md"
    ziele = [k.rstrip(":.").strip() for _, k in re.findall(r"^(\d+)\.\s+\*\*(.+?)\*\*", koerper(ziele_pfad), re.M)][:5]
    if selbstbild:
        z.append(f"Wer: {wer} — {selbstbild[0]} (person/ich.md)")
    if ziele:
        z.append("Ziele (gelten parallel, Spannungen benennen, nicht auflösen): " + " · ".join(ziele) + " (person/ziele.md)")
        alter = tage_seit(frontmatter(lies(ziele_pfad))[0].get("stand", ""))
        if alter is not None and alter > ALT_TAGE:
            z.append(f"  ? Ziele seit {alter} Tagen nicht bestätigt — {wer} fragen, ob sie noch gelten; nicht selbst ändern.")

    knoten = laden()
    an = [nid.lstrip("/") for nid, k in knoten.items() if re.search(rf"^# An {re.escape(wer)}\s*$", k["body"], re.M)]
    if an:
        z.append(f"AN {wer.upper()} ({len(an)}, Fragen stehen oben im Knoten): " + ", ".join(an[:6]) + (" …" if len(an) > 6 else ""))

    s = WURZEL / "stand" / "aktuell.md"
    if s.exists():
        d = frontmatter(lies(s))[0].get("stand", "unbekannt")
        t = tage_seit(d)
        z.append(f"Stand: {d}" + (f" — {t} Tage alt, am Sitzungsende fortschreiben" if t and t > 3 else ""))

    offen: dict[str, list[str]] = defaultdict(list)
    fristen = []
    for nid, k in knoten.items():
        f = k["fm"]
        if not nid.startswith("/aufgaben/") or f.get("status") != "offen":
            continue
        merk = ["hoch"] if f.get("prioritaet") == "hoch" else []
        alter = tage_seit(f.get("timestamp", ""))
        if alter is not None and alter > ALT_TAGE:
            merk.append(f"{alter} T")
        stamm = Path(nid).stem
        offen[f.get("wer", "Agent")].append(stamm + (f" ({', '.join(merk)})" if merk else ""))
        if f.get("frist"):
            rest = tage_seit(f["frist"])
            if rest is not None:
                fristen.append((-rest, stamm, f["frist"]))
    if fristen:
        z += ["", "FRISTEN:"]
        for rest, stamm, frist in sorted(fristen):
            wie = f"in {rest} Tagen" if rest > 0 else ("HEUTE" if rest == 0 else f"seit {-rest} Tagen überfällig")
            z.append(f"  ! {frist} ({wie}): {stamm}")
    for wer_ in sorted(offen, key=lambda w: (w == "Agent", w)):
        z.append(f"Offen {wer_}: " + ", ".join(offen[wer_]))
    if any(" T)" in e or " T," in e for l in offen.values() for e in l):
        z.append(f"  (n T = seit n Tagen offen: bei Gelegenheit {wer} fragen, ob noch aktuell)")

    try:
        oben = subprocess.run(["git", "-C", str(WURZEL), "rev-parse", "--show-toplevel"], capture_output=True,
                              text=True, timeout=10).stdout.strip()
        g = subprocess.run(["git", "-C", str(WURZEL), "status", "--porcelain", "--ignore-submodules=dirty"],
                           capture_output=True, text=True, timeout=10)
        # Nur melden, wenn der Kompass selbst das Repo ist (nicht, wenn er als Ordner in einem anderen liegt).
        if oben and Path(oben).resolve() == WURZEL and g.returncode == 0 and g.stdout.strip():
            zeilen = g.stdout.splitlines()
            neu = sum(1 for x in zeilen if x.startswith("??"))
            z.append(f"GIT: {neu} Dateien nie committet, {len(zeilen) - neu} geändert — nicht pauschal committen.")
    except (OSError, subprocess.SubprocessError):
        pass

    z += ["", "REGELN (Kurzform, vollständig in METHODE.md):",
          f"  1. Entscheiden tut nur {wer}. Eigene Einschätzungen mit Modell und Datum kennzeichnen.",
          "  2. Beleg, Einschätzung, Entscheidung getrennt halten. Richtung nie aus Belegen ableiten.",
          "  3. Mehrere Ziele gelten parallel. Frust und Kehrtwenden als Zitat, nicht als Ziel.",
          f"  4. Fragen an {wer} ganz oben im Knoten unter '# An {wer}'.",
          "  5. Vor jeder Bewertung: kompass vorwissen \"<Frage>\".",
          "  6. Sitzungsende: stand/aktuell.md überschreiben, log.md ergänzen, kompass sync && kompass pruefen."]
    return "\n".join(z)


# ------------------------------------------------------------------ sync und pruefen
def kanten(knoten: dict):
    aus, ein = defaultdict(list), defaultdict(list)
    for nid, k in knoten.items():
        for key in BEZIEHUNGEN:
            ziele = k["fm"].get(key)
            for ziel in ziele if isinstance(ziele, list) else []:
                aus[nid].append((key, ziel))
                ein[ziel].append((key, nid))
    return aus, ein


def sync() -> int:
    knoten = laden()
    aus, ein = kanten(knoten)

    def link(ziel: str, von: Path) -> str:
        t = knoten[ziel]["fm"].get("title", ziel) if ziel in knoten else f"{ziel} (fehlt)"
        return f"[{t}]({os.path.relpath(WURZEL / ziel.lstrip('/'), von.parent)})"

    for nid, k in knoten.items():
        teile = ["<!-- verbindungen:start -->", "", "# Verbindungen", ""]
        nach = defaultdict(list)
        for key, ziel in aus[nid]:
            nach[key].append(ziel)
        for key, ziele in nach.items():
            teile.append(f"- **{BEZIEHUNGEN[key]}:** " + ", ".join(link(z, k["pfad"]) for z in ziele))
        if ein[nid]:
            teile.append("- **Verweise hierher:** " + ", ".join(sorted({link(q, k['pfad']) for _, q in ein[nid]})))
        if len(teile) == 4:
            teile.append("- keine")
        teile += ["", "<!-- verbindungen:ende -->"]
        alt = lies(k["pfad"])
        neu = MARKER.sub("\n".join(teile), alt) if MARKER.search(alt) else alt.rstrip() + "\n\n" + "\n".join(teile) + "\n"
        if neu != alt:
            k["pfad"].write_text(neu, encoding="utf-8")
    print(f"sync: {len(knoten)} Knoten")
    return 0


def pruefen() -> int:
    knoten = laden()
    aus, _ = kanten(knoten)
    befunde = 0
    for nid, k in knoten.items():
        if not k["fm"].get("type"):
            print(f"FEHLER  {nid}: kein type")
            befunde += 1
        for key, ziel in aus[nid]:
            if ziel not in knoten:
                print(f"TOT     {nid} --{key}--> {ziel}")
                befunde += 1
    print(f"pruefen: {len(knoten)} Knoten, {befunde} Befunde")
    return 1 if befunde else 0


# ------------------------------------------------------------------ vorwissen
MAX_DF, MAX_TITEL_DF, SELTEN_DF, MAX_TREFFER, REL_SCHWELLE = 12, 8, 8, 5, 0.35
ANLASS = re.compile(
    r"bewert|einsch[aä]tz|beurteil|kritisch|critical|assess|evaluat|review|look at|schau\w*\s+(mal|dir)|"
    r"taugt|n[uü]tzlich|nutzen|einsetz|verwenden|ob wir|sollen wir|sollten wir|lohnt|was h[aä]ltst|"
    r"vergleich|compare|empfiehl|recommend|alternativ|https?://", re.I)
STOP = set("""
aber alle allem allen aller alles also andere auch auf aus bei beim bin bis bitte dabei dafür dann das dass
dazu dem den der des die dies diese diesem diesen dieser dieses doch dort durch eine einem einen einer eines
einfach für gern geht gibt haben habe hat hatte hier immer ist jetzt kann kannst kein keine können machen
macht mal man mehr mein meine mir mit muss nach nicht noch nun nur oder ohne schon sehr sein seine sich sie
sind soll sollen sondern uns und unser unsere vom von vor war was weil wenn werden wie wir wird wollen wurde
zum zur über about after also and any are because been before but can could did does for from had has have
her here how into its just like make more most much must not now only other our out over should some such
than that the their them then there these they this those through too very was were what when where which
while who why will with would you your please look use build see kompass tool tools werkzeug bewertung
""".split())
TOKEN = re.compile(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9_-]{2,}")


def begriffe(text: str) -> list[str]:
    gesehen: list[str] = []
    for t in TOKEN.findall(text):
        k = t.lower().strip("-_")
        if k in STOP or k in gesehen or (len(k) < 4 and not any(c.isdigit() for c in k)):
            continue
        gesehen.append(k)
    return gesehen


def suche(text: str) -> list:
    woerter = begriffe(text)
    if not woerter:
        return []
    knoten = laden()
    inhalt = {nid: lies(k["pfad"]).lower() for nid, k in knoten.items()}
    treffer, titel_treffer, df, titel_df = defaultdict(set), defaultdict(set), defaultdict(int), defaultdict(int)
    for w in woerter:
        m = re.compile(r"(?<![a-zäöüß0-9])" + re.escape(w) + r"(?![a-zäöüß0-9])")
        for nid, roh in inhalt.items():
            if m.search(roh):
                treffer[nid].add(w)
                df[w] += 1
                if m.search((str(knoten[nid]["fm"].get("title", "")) + " " + Path(nid).stem).lower()):
                    titel_treffer[nid].add(w)
                    titel_df[w] += 1
    erg = []
    for nid, ws in treffer.items():
        gut = {w for w in ws if df[w] <= MAX_DF or (w in titel_treffer[nid] and titel_df[w] <= MAX_TITEL_DF)}
        in_titel = titel_treffer[nid] & gut
        selten = {w for w in gut if df[w] <= SELTEN_DF}
        if not gut or (not in_titel and not selten and len(gut) < 2):
            continue
        erg.append((sum(1.0 / df[w] for w in gut) + 3.0 * len(in_titel), nid, knoten[nid]["fm"], sorted(gut)))
    erg.sort(key=lambda e: -e[0])
    if erg:
        erg = [e for e in erg if e[0] >= REL_SCHWELLE * erg[0][0]]
    return erg[:MAX_TREFFER]


def vorwissen(argv: list[str]) -> int:
    try:
        if argv and argv[0] == "--auto":
            roh = sys.stdin.read()
            try:
                daten = json.loads(roh)
                text = str(daten.get("prompt") or daten.get("user_prompt") or "") if isinstance(daten, dict) else roh
            except ValueError:
                text = roh
            if len(text) < 15 or not ANLASS.search(text):
                return 0
        else:
            text = " ".join(argv) if argv else sys.stdin.read()
        gefunden = suche(text)
        if not gefunden:
            return 0
        print("KOMPASS-VORWISSEN (automatisch, kein Urteil): Zu Begriffen dieser Frage steht schon etwas im Kompass. "
              "Vor der Bewertung lesen; Altes nicht ungeprüft übernehmen und nicht ignorieren.")
        for _, nid, fm, ws in gefunden:
            d = str(fm.get("datum") or fm.get("stand") or fm.get("timestamp") or "")[:10]
            t = tage_seit(d) if d else None
            alt = f", {t} Tage alt: vor Gebrauch neu prüfen" if t is not None and t > ALT_TAGE else ""
            titel = str(fm.get("title") or Path(nid).stem)[:110]
            print(f"- {nid.lstrip('/')} [{fm.get('type', '?')}, {d or 'ohne Datum'}{alt}] {titel} (Begriffe: {', '.join(ws)})")
    except Exception as fehler:  # ein Hook darf nie eine Sitzung blockieren
        if "--auto" not in argv:
            print(f"vorwissen: {fehler}", file=sys.stderr)
    return 0


# ------------------------------------------------------------------ Aufruf
def main(argv: list[str]) -> int:
    from cli import main as cli_main
    return cli_main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

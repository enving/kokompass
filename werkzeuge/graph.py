#!/usr/bin/env python3
"""Kompass-Graph: liest das OKF-Bundle, pflegt Verbindungsabschnitte, schreibt das Lagebild.

  graph.py sync      Verbindungsabschnitte in allen Knoten aus dem Frontmatter neu schreiben (Obsidian-Graph)
  graph.py bericht   berichte/lagebild.md und berichte/graph.json erzeugen
  graph.py pruefen   fehlender type, tote Verweise
  graph.py eingang   neue Notizen aus dem Obsidian-Vault (Clippings/, Kompass/Eingang/) als quellen/ übernehmen
  graph.py export    Lagebild und „Was ich mitnehme" zum Lesen in den Vault (Kompass/) schreiben
  graph.py alles     eingang → sync → pruefen → bericht → export
  graph.py bestaetigen <beleg>   geprüften Commit eines Belegs auf den aktuellen Stand setzen
  graph.py neutral   berichte/faktenlage.md: nur Belegtes und der Person Entscheidungen, ohne Agenten-Einschätzungen (für Blind-Gegenproben)

Beziehungen stehen als Listen bundle-absoluter Pfade im Frontmatter (z. B. `braucht: [/faehigkeiten/x.md]`).
Die Frontmatter ist die Quelle; die Abschnitte zwischen den verbindungen-Markern sind abgeleitet.
Der Vault enthält Originalquellen und ein Fachwiki; Kompass bleibt das lokale private Gedächtnis. Pfad über KOMPASS_VAULT änderbar.
Nur Standardbibliothek.
"""
import json, os, re, shutil, sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from konfiguration import wurzel, felder, vault_pfad, pfad

ROOT = wurzel()
VAULT = vault_pfad(ROOT)
from kern_adapter import lade_kern

_KERN = lade_kern(ROOT)
BEZIEHUNGEN = _KERN.BEZIEHUNGEN
MARKER = _KERN.MARKER
AUSGENOMMEN = _KERN.AUSGENOMMEN
SPIEGEL_ORDNER = set(felder(ROOT).get('spiegel_ordner', []))
SPIEGEL_SPERRE = tuple(felder(ROOT).get('spiegel_sperre', []))

# ------------------------------------------------------------ Laden
frontmatter = _KERN.frontmatter
kanten = _KERN.kanten


def laden():
    knoten = lade_kern(ROOT).laden()
    for k in knoten.values():
        k["ordner"] = k["pfad"].relative_to(ROOT).parts[0]
    return knoten


def titel(knoten, nid):
    return knoten[nid]["fm"].get("title", nid) if nid in knoten else f"{nid} (fehlt)"


def datum(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def slug(s):
    s = s.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60] or "quelle"


# ------------------------------------------------------------ sync
def cmd_sync(knoten):
    return lade_kern(ROOT, knoten=knoten).sync()


def cmd_pruefen(knoten):
    return lade_kern(ROOT, knoten=knoten).pruefen()


# ------------------------------------------------------------ eingang
def cmd_eingang(knoten):
    if VAULT is None:
        raise ValueError('vault_pfad in kontextquellen.md fehlt; kein Eingang gelesen')
    import eingang
    return eingang.ingest(sys.modules[__name__], knoten)


# ------------------------------------------------------------ repos



def git(pfad, *args):
    import subprocess
    r = subprocess.run(["git", "-C", str(pfad), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def repo_pfad(k):
    r = k["fm"].get("repo")
    return Path(os.path.expanduser(r)) if isinstance(r, str) and r else None


def repo_lage(knoten):
    """Belege, deren Repo seit der letzten Prüfung neue Commits oder offene Änderungen hat, und Repos ohne Beleg."""
    neu, ohne, bekannt = [], [], set()
    for n, k in sorted(knoten.items()):
        p = repo_pfad(k)
        if not p:
            continue
        bekannt.add(p.resolve())
        kopf = git(p, "rev-parse", "HEAD")
        if not kopf:
            neu.append((n, "Repo nicht lesbar")); continue
        alt = str(k["fm"].get("geprueft_commit", ""))
        offen = git(p, "status", "--porcelain")
        n_offen = len(offen.splitlines()) if offen else 0
        teile = []
        if not alt:
            teile.append("noch nie geprüft")
        elif not kopf.startswith(alt):
            anzahl = git(p, "rev-list", "--count", f"{alt}..HEAD") or "?"
            teile.append(f"{anzahl} neue Commit(s) seit Prüfung, letzter {git(p, 'log', '-1', '--format=%ad', '--date=short')}")
        if n_offen:
            teile.append(f"{n_offen} uncommittete Änderung(en)")
        if teile:
            neu.append((n, "; ".join(teile)))
    import wissen
    for p in wissen.repo_paths():
        if p.resolve() not in bekannt and p.resolve() != ROOT:
            ohne.append(p.name)
    return neu, ohne


def cmd_bestaetigen(knoten, beleg):
    nid = f"/belege/{beleg}.md"
    k = knoten.get(nid)
    if not k or not repo_pfad(k):
        sys.exit(f"bestaetigen: {nid} fehlt oder hat kein repo-Feld")
    kopf = git(repo_pfad(k), "rev-parse", "--short=12", "HEAD")
    text = k["pfad"].read_text()
    if re.search(r"^geprueft_commit:.*$", text, re.M):
        text = re.sub(r"^geprueft_commit:.*$", f"geprueft_commit: {kopf}", text, count=1, flags=re.M)
    else:
        text = text.replace("\ntimestamp:", f"\ngeprueft_commit: {kopf}\ntimestamp:", 1)
    k["pfad"].write_text(text)
    print(f"bestaetigen: {nid} → {kopf}")


# ------------------------------------------------------------ bericht
def cmd_bericht(knoten, heute):
    aus, ein = kanten(knoten)
    von = lambda ordner: {n: k for n, k in knoten.items() if k["ordner"] == ordner}
    fm = lambda n: knoten[n]["fm"] if n in knoten else {}
    link = lambda n: f"[{titel(knoten, n)}](..{n})"
    ideen, kanaele, faehig, belege, netz, fragen, auss, quellen = (von(o) for o in ("ideen", "kanaele", "faehigkeiten", "belege", "netzwerk", "fragen", "aussendungen", "quellen"))
    aktiv = {n: k for n, k in ideen.items() if k["fm"].get("status") not in ("verworfen",)}
    z = []

    # 1 Output-Bilanz
    z += ["## 1 · Output-Bilanz (30 Tage)", ""]
    arten = defaultdict(int)
    for n, k in auss.items():
        d = datum(k["fm"].get("datum"))
        if k["fm"].get("status") == "erledigt" and d and (heute - d).days <= 30:
            arten[k["fm"].get("art", "sonstig")] += 1
    geplant = [n for n, k in auss.items() if k["fm"].get("status") == "geplant"]
    for art in ("akquise", "veroeffentlichung", "partner", "bewerbung", "sonstig"):
        z.append(f"- **{art}:** {arten.get(art, 0)}")
    if (felder(ROOT).get("output_ziel") and not arten.get("akquise") and not arten.get("veroeffentlichung")):
        z += ["", f"> **Output-Hinweis:** {sum(arten.values())} Aussendungen, davon **0 Akquise und 0 Veröffentlichungen**. "
              f"Erklärter Bezugspunkt: {felder(ROOT)['output_ziel']}."]
    if geplant:
        z += ["", "Geplant, noch nicht erledigt: " + ", ".join(link(n) for n in geplant)]
    z.append("")

    # 2 Anschlussfähigkeit der Ideen
    z += ["## 2 · Anschlussfähigkeit der aktiven Ideen", "",
          "Zählt, was schon da ist — kein Score, keine Gewichtung. **Antrieb zuerst lesen:** Belege zeigen Können, nicht Wollen.", "",
          "| Idee | Status | **Antrieb** | belegte Fähigkeiten | unbelegt | genutzte Kanäle | warmes Netz | Belege genutzt | Quellen |", "|---|---|---|---|---|---|---|---|---|"]
    for n, k in sorted(aktiv.items(), key=lambda x: x[1]["fm"].get("status", "")):
        br = k["fm"].get("braucht", [])
        unbelegt = [b for b in br if not fm(b).get("belegt_durch")]
        ka = [c for c in k["fm"].get("kanal", []) if fm(c).get("genutzt") in ("ja", "teilweise")]
        warm = [w for w in k["fm"].get("netzwerk", []) if str(fm(w).get("beziehung", "")).startswith(("warm", "aktiv", "indirekt"))]
        q = [s for key, s in ein[n] if key == "betrifft" and s in quellen]
        z.append(f"| {link(n)} | {k['fm'].get('status')} | {k['fm'].get('antrieb', 'unklar')} | {len(br) - len(unbelegt)}/{len(br)} | {', '.join(titel(knoten, u) for u in unbelegt) or '–'} | "
                 f"{len(ka)}/{len(k['fm'].get('kanal', []))} | {len(warm)} | {len(k['fm'].get('nutzt', []))} | {len(q)} |")
    z.append("")

    # 3 Ideen ohne tragenden Kanal
    z += ["## 3 · Ideen ohne genutzten Kanal", ""]
    for n, k in aktiv.items():
        ka = k["fm"].get("kanal", [])
        if not any(fm(c).get("genutzt") in ("ja", "teilweise") for c in ka):
            z.append(f"- {link(n)} — Kanäle: {', '.join(titel(knoten, c) for c in ka) or 'keiner eingetragen'}")
    z.append("")

    # 4 Ungenutzte Belege
    z += ["## 4 · Gebautes, das keine aktive Idee nutzt", ""]
    genutzt = {b for k in aktiv.values() for b in k["fm"].get("nutzt", [])}
    for n, k in belege.items():
        if n not in genutzt:
            z.append(f"- {link(n)} — {k['fm'].get('status', '')}; zeigt: {', '.join(titel(knoten, f) for f in k['fm'].get('zeigt', []))}")
    z.append("")

    # 5 Netzwerk
    z += ["## 5 · Netzwerk ohne Verwendung oder ohne Kontakt", ""]
    netz_genutzt = {w for k in aktiv.values() for w in k["fm"].get("netzwerk", [])}
    for n, k in netz.items():
        bez = str(k["fm"].get("beziehung", ""))
        hinweise = []
        if n not in netz_genutzt:
            hinweise.append("keine aktive Idee nutzt es")
        if bez.startswith(("warm", "indirekt")) and not k["fm"].get("letzter_kontakt"):
            hinweise.append("warm, aber kein Kontakt vermerkt")
        if hinweise:
            z.append(f"- {link(n)} ({bez}) — {'; '.join(hinweise)}")
    z.append("")

    # 6 Unbelegte Fähigkeiten
    z += ["## 6 · Fähigkeiten ohne Beleg", ""]
    for n, k in faehig.items():
        if not k["fm"].get("belegt_durch"):
            bedarf = [q for key, q in ein[n] if key == "braucht" and q in aktiv]
            z.append(f"- {link(n)} — gebraucht von {len(bedarf)} aktiven Ideen")
    z.append("")

    # 7 Offene Fragen
    z += ["## 7 · Offene Fragen", "", "| Priorität | Frage | blockiert |", "|---|---|---|"]
    rang = {"hoch": 0, "mittel": 1, "niedrig": 2}
    for n, k in sorted(fragen.items(), key=lambda x: rang.get(x[1]["fm"].get("prioritaet"), 9)):
        if k["fm"].get("status") != "offen":
            continue
        z.append(f"| {k['fm'].get('prioritaet')} | {link(n)} | {', '.join(titel(knoten, b) for b in k['fm'].get('blockiert', [])) or '–'} |")
    z.append("")

    # 8 Liegengebliebenes
    z += ["## 8 · Liegengeblieben (Stand älter als 14 Tage)", ""]
    for n, k in aktiv.items():
        d = datum(k["fm"].get("stand"))
        if d and (heute - d).days > 14:
            z.append(f"- {link(n)} — Stand {d}, nächster Schritt: {k['fm'].get('naechster_schritt', 'keiner eingetragen')}")
    z.append("")

    # 9 Neue Quellen
    z += ["## 9 · Neue Quellen im Eingang (noch nicht ausgewertet)", ""]
    offen = [n for n, k in quellen.items() if k["fm"].get("status") == "neu"]
    z += [f"- {link(n)}" for n in offen] or ["- keine"]
    z.append("")

    # 10 Repos
    z += ["## 10 · Neu in den Repos seit der letzten Prüfung", ""]
    neu_r, ohne_r = repo_lage(knoten)
    z += [f"- {link(n)} — {info}" for n, info in neu_r] or ["- nichts Neues"]
    if ohne_r:
        z += ["", "Repos ohne Beleg im Kompass: " + ", ".join(f"`{o}`" for o in ohne_r)]
    z += ["", "Prüfen mit `vibe_zulieferer.sh <repo>` oder `code_graph.sh`, Beleg anpassen, dann `graph.py bestaetigen <beleg>`.", ""]

    # 11 Aufgaben
    z += ["## 11 · Offene Aufgaben", ""]
    aufgaben = von("aufgaben")
    for wer in (lade_kern(ROOT).name(), "Agent"):
        liste = sorted([(n, k) for n, k in aufgaben.items() if k["fm"].get("status") == "offen" and k["fm"].get("wer") == wer],
                       key=lambda x: rang.get(x[1]["fm"].get("prioritaet"), 9))
        if liste:
            z += [f"**{wer}**", ""] + [f"- ({k['fm'].get('prioritaet')}) {link(n)}" for n, k in liste] + [""]
    if not any(k["fm"].get("status") == "offen" for k in aufgaben.values()):
        z += ["- keine", ""]

    kopf = ["---", "type: Bericht", "title: Lagebild", "description: Automatisch erzeugte Lücken, ungenutzte Bestände und Output-Bilanz aus dem Kompass-Graphen.",
            f"timestamp: {heute.isoformat()}T00:00:00+02:00", "---", "", "# Lagebild", "",
            f"Erzeugt mit `werkzeuge/graph.py bericht` am {heute.isoformat()} aus {len(knoten)} Knoten. **Nicht von Hand bearbeiten** — Knoten ändern, neu erzeugen.", ""]
    ziel = ROOT / "berichte" / "lagebild.md"
    ziel.parent.mkdir(exist_ok=True)
    ziel.write_text("\n".join(kopf + z))
    graph = {"nodes": [{"id": n, "type": k["fm"].get("type"), "title": k["fm"].get("title"), "status": k["fm"].get("status")} for n, k in knoten.items()],
             "edges": [{"source": n, "target": t, "relation": key} for n in knoten for key, t in aus[n]]}
    (ROOT / "berichte" / "graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=1))
    print(f"bericht: {ziel} · {len(graph['nodes'])} Knoten · {len(graph['edges'])} Kanten")


# ------------------------------------------------------------ neutral
EINSCHAETZUNG = re.compile(r"(\*\*(Stärkster Einwand|Empfehlung[^*]*|Befund|Warum das zählt|Einordnung[^*]*):\*\*.*?)(?=\n\n|\Z)", re.S)


def cmd_neutral(knoten):
    """Faktenlage ohne Agenten-Urteile: Randbedingungen, Ziel, Stationen, Belege, Netzwerk, Kanäle, der Person Entscheidungen,
    Ideen nur mit Titel und Status, Quellen nur mit Link. Bewertende Abschnitte werden entfernt."""
    von = lambda o: sorted((n, k) for n, k in knoten.items() if k["ordner"] == o)
    def sauber(body):
        body = MARKER.sub("", body)
        body = EINSCHAETZUNG.sub("", body)
        body = re.split(r"\n## (Vorschlag|Nachschärfung)", body)[0]
        body = re.sub(r"\n# Citations.*", "", body, flags=re.S)
        return re.sub(r"\n{3,}", "\n\n", body).strip()
    z = ["---", "type: Bericht", "title: Faktenlage", "description: Nur Belegtes und der Person eigene Entscheidungen, ohne Einschätzungen von Agenten — für Blind-Gegenproben.",
         f"timestamp: {date.today().isoformat()}T00:00:00+02:00", "---", "", "# Faktenlage", "",
         "Erzeugt mit `graph.py neutral`. **Enthält absichtlich keine Empfehlungen, Befunde oder Einwände von Agenten.** "
         "Wer hieraus urteilt, soll zu eigenen Schlüssen kommen.", ""]
    for ordner, ueberschrift in (("person", "Person, Ziel, Randbedingungen"), ("stationen", "Stationen"), ("belege", "Gebautes"),
                                 ("netzwerk", "Netzwerk"), ("kanaele", "Kanäle")):
        z += [f"## {ueberschrift}", ""]
        for n, k in von(ordner):
            if ordner == "person" and k["fm"].get("type") in ("Arbeitsweise", "Zuversicht"):
                continue
            felder = {f: k["fm"][f] for f in ("status", "oeffentlich", "beziehung", "letzter_kontakt", "genutzt", "zeitraum") if f in k["fm"]}
            z += [f"### {k['fm'].get('title')}", "", *(f"- {a}: {b}" for a, b in felder.items()), "", sauber(k["body"]).replace("# " + str(k['fm'].get('title')), "").strip(), ""]
    z += ["## Entscheidungen (der Person)", ""]
    for n, k in von("entscheidungen"):
        z.append(f"- {k['fm'].get('datum')}: **{k['fm'].get('title')}** — {k['fm'].get('description')}")
    z += ["", "## Ideen (nur Titel und Status)", ""]
    z += [f"- {k['fm'].get('title')} — {k['fm'].get('status')}" for n, k in von("ideen")]
    z += ["", "## Quellen (nur Titel und Link)", ""]
    z += [f"- {k['fm'].get('title')} — {k['fm'].get('resource', 'lokal')}" for n, k in von("quellen")]
    (ROOT / "berichte").mkdir(exist_ok=True)
    (ROOT / "berichte" / "faktenlage.md").write_text("\n".join(z) + "\n")
    print(f"neutral: {ROOT / 'berichte' / 'faktenlage.md'}")


# ------------------------------------------------------------ export
def cmd_export(knoten):
    if VAULT is None or not VAULT.exists():
        print(f"export: Vault nicht erreichbar ({VAULT}) — übersprungen"); return
    import eingang
    eingang.source_index(sys.modules[__name__], knoten)
    print(f"export: {ROOT / 'berichte/quellen.md'}")


def main():
    befehle = ("sync", "bericht", "pruefen", "eingang", "export", "alles", "bestaetigen", "neutral")
    if len(sys.argv) < 2 or sys.argv[1] not in befehle:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "bestaetigen":
        if len(sys.argv) < 3:
            sys.exit("bestaetigen <beleg>")
        return cmd_bestaetigen(laden(), sys.argv[2])
    heute = (datum(sys.argv[2]) if len(sys.argv) > 2 else None) or date.today()
    if cmd == "sync":
        cmd_sync(laden())
    elif cmd == "pruefen":
        sys.exit(1 if cmd_pruefen(laden()) else 0)
    elif cmd == "eingang":
        cmd_eingang(laden())
    elif cmd == "bericht":
        cmd_bericht(laden(), heute)
    elif cmd == "export":
        cmd_export(laden())
    elif cmd == "neutral":
        cmd_neutral(laden())
    else:
        if VAULT is not None:
            cmd_eingang(laden())
        cmd_sync(laden())
        if cmd_pruefen(laden()):
            sys.exit(1)
        cmd_bericht(laden(), heute)
        cmd_neutral(laden())
        cmd_export(laden())


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(f'graph: {error}', file=sys.stderr)
        sys.exit(1)

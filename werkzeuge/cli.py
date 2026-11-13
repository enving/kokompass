#!/usr/bin/env python3
"""Gemeinsamer Einstieg für Vorlage und ausgefüllte Kompass-Instanzen."""
import os
from pathlib import Path
import re
import shutil
import tempfile
import subprocess
import sys

from kern_adapter import INSTANZ, lade_kern
from konfiguration import felder, pfad

WERKZEUGE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("KOMPASS_DIR") or INSTANZ).resolve()
GRAPH_BEFEHLE = {"sync", "pruefen", "bericht", "eingang", "export", "alles", "bestaetigen", "neutral"}
EXTRAS = {"scan": ("wissen.py", "scan"), "uebergaben": ("wissen.py", "uebergaben"),
          "aufgaben": ("aufgaben.py",),
          "kontext": ("kontext.py",),
          "github-fehler": ("github_fehler.py",),
          "pflege": ("wiki_pflege.py",),
          "weiter": ("dirigent_db.py", "weiter"),
          "repos": ("navigation.py", "repos"), "diagnose": ("navigation.py", "diagnose"),
          "wartet": ("dirigent_db.py", "wartet"), "db-import": ("dirigent_db.py", "import")}



def okf_pruefen(wurzel=ROOT):
    """Den aktuellen Instanzbestand nach derselben Auswahl wie den Graph prüfen."""
    kern = lade_kern(wurzel)
    validator = pfad(os.environ.get("KOMPASS_OKF_PRUEFER") or felder(wurzel).get("okf_pruefer", "~/.agents/skills/okf/okf-validate.mjs"), wurzel)
    if not validator.is_file():
        raise RuntimeError(f"OKF-Prüfer fehlt: {validator}")
    with tempfile.TemporaryDirectory(prefix=".kompass-okf-", dir=wurzel.parent) as tmp:
        ziel = Path(tmp)
        # Linkziele bleiben erreichbar; Symlink-Verzeichnisse durchläuft der Prüfer nicht.
        for quelle in wurzel.iterdir():
            if quelle.is_dir() and (quelle.name.startswith(".") or quelle.name in kern.NICHT_KNOTEN):
                (ziel / quelle.name).symlink_to(quelle.resolve(), target_is_directory=True)
        for quelle in sorted(wurzel.rglob("*.md")):
            if not kern.ist_knoten(quelle) and quelle.name not in {"index.md", "log.md"}:
                continue
            rel = quelle.relative_to(wurzel)
            # Auch reservierte Dateien nur im Instanzbestand, nie aus Fremdrepos.
            if quelle.is_symlink() or rel.parts[0].startswith(".") or rel.parts[0] in kern.NICHT_KNOTEN:
                continue
            kopie = ziel / rel
            kopie.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(quelle, kopie)
        print(f"OKF-Prüfung des aktuellen Instanzbestands: {wurzel}", flush=True)
        return subprocess.run(["node", str(validator), str(ziel)]).returncode


def status():
    kern = lade_kern(ROOT)
    knoten = kern.laden()
    # Berichte und alte Stände können zitierte Frageüberschriften enthalten.
    kern.laden = lambda: {nid: k for nid, k in knoten.items()
                         if not nid.startswith(("/berichte/", "/stand/"))}
    text = kern.stand()
    person = kern.frontmatter(kern.lies(ROOT / "person/ich.md"))[0]
    # Ansprache und voller Anzeigename stammen aus der Instanz.
    if person.get("title"):
        text = text.replace(f"Wer: {kern.name()} —", f"Wer: {person['title']} —", 1)
    lokal = ROOT / ".agents/ARBEITSWEISE.md"
    if lokal.exists():
        marker = re.search(r"<!-- startausgabe:start -->\s*(.*?)\s*<!-- startausgabe:ende -->",
                           lokal.read_text(), re.S)
        if marker:
            text += "\n\n" + marker.group(1)
    wissen = WERKZEUGE / "wissen.py"
    if wissen.exists():
        eingang = subprocess.run([sys.executable, str(wissen), "status"], capture_output=True,
                                 text=True, check=True, env={**os.environ, "KOMPASS_DIR": str(ROOT)})
        if eingang.stdout.strip():
            text += "\n" + eingang.stdout.strip()
    try:
        import github_fehler
        text += "\n" + github_fehler.status_zeile(ROOT / ".zustand/github-rotliste.json")
        kontingent = github_fehler.kontingent_status(ROOT / ".zustand/github-kontingente.json")
        text += ("\n" + kontingent) if kontingent else ""
    except (OSError, ValueError, KeyError, ImportError) as error:
        text += f"\nGITHUB-FEHLER: Übersicht nicht lesbar ({type(error).__name__})"
    return text


def datei_schreiben(ziel=None):
    ziel = Path(ziel or os.environ.get("KOMPASS_STAND_FILE") or pfad(felder(ROOT).get("stand_datei", ".kompass-stand.md"), ROOT))
    text = "# Kompass — aktueller Stand\n\nErzeugt von `kompass datei`. Nicht von Hand bearbeiten.\n\n```\n"
    text += status() + "\n```\n"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(text, encoding="utf-8")
    return ziel


def main(argv):
    befehl = argv[0] if argv else "stand"
    if befehl in {"hilfe", "-h", "--help"}:
        print("kompass [stand|datei [PFAD]|vorwissen [--auto] TEXT|sync|pruefen]")
        print("Weitere Befehle: repos diagnose validieren kontext <Thema> github-fehler <Repo> <Lauf-ID> aufgaben [Thema] weiter [--abschluss] wartet db-import scan uebergaben pflege bericht eingang export alles bestaetigen neutral")
        print("Allgemeine Regeln: kern/METHODE.md; Instanz: .agents/ARBEITSWEISE.md; Konfiguration: kontextquellen.md; Sichtbarkeit: Repo-Liste der Instanz")
        return 0
    if befehl == "vorwissen":
        return lade_kern(ROOT, vorwissen=True).vorwissen(argv[1:])
    if not (ROOT / "person/ich.md").exists():
        print(f"kompass: kein Kompass in {ROOT} (person/ich.md fehlt)", file=sys.stderr)
        return 2
    if befehl == "stand":
        print(status())
        return 0
    if befehl == "datei":
        print(f"geschrieben: {datei_schreiben(argv[1] if len(argv) > 1 else None)}")
        return 0
    if befehl == "validieren":
        return okf_pruefen()
    if befehl in EXTRAS:
        skript, *args = EXTRAS[befehl]
        return subprocess.run([sys.executable, str(WERKZEUGE / skript), *args, *argv[1:]], env={**os.environ, "KOMPASS_DIR": str(ROOT)}).returncode
    if befehl == "alles" and str(felder(ROOT).get("github_aktiv", "")).casefold() in {"ja", "true"}:
        # Rote GitHub-Workflows höchstens alle 12 Stunden frisch lesen (~35 s); Fehler bremsen den Rest nicht.
        if subprocess.run([sys.executable, str(WERKZEUGE / "github_fehler.py"), "--uebersicht", "--falls-alt"]).returncode:
            print("GitHub-Übersicht nicht erneuert; übrige Schritte laufen weiter.", file=sys.stderr)
        subprocess.run([sys.executable, str(WERKZEUGE / "github_fehler.py"), "--kontingente", "--falls-alt"])
    if befehl in GRAPH_BEFEHLE:
        result = subprocess.run([sys.executable, str(WERKZEUGE / "graph.py"), *argv], env={**os.environ, "KOMPASS_DIR": str(ROOT)})
        try:
            datei_schreiben()
        except (OSError, subprocess.SubprocessError) as error:
            print(f"Stand-Datei konnte nicht aktualisiert werden: {error}", file=sys.stderr)
            return result.returncode or 1
        return result.returncode
    print(f"kompass: unbekannter Befehl '{befehl}' (siehe kompass hilfe)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        if "--auto" not in sys.argv:
            print(f"kompass: {error}", file=sys.stderr)
        sys.exit(0 if "--auto" in sys.argv else 1)

"""Instanz-Erweiterungen; die allgemeinen Algorithmen kommen aus kern/werkzeuge/kompass.py."""
import importlib.util
from pathlib import Path
import re

from konfiguration import wurzel

INSTANZ = wurzel()
KERN_DATEI = Path(__file__).resolve().parent / "kompass.py"
ZUSAETZLICHE_BEZIEHUNGEN = {
    "stationen": "Stationen", "faehigkeiten": "Fähigkeiten", "netzwerk": "Netzwerk", "kanal": "Kanal",
}
SUCH_ORDNER = (
    "ideen", "einschaetzungen", "entscheidungen", "fragen", "aufgaben", "belege", "gespraeche",
    "aussendungen", "quellen", "netzwerk", "kanaele", "faehigkeiten", "stationen", "person",
)
# Bisheriger Filter dieser Instanz: allgemeine Wörter und stark vertretene Domänenbegriffe.
ZUSAETZLICHE_STOPPWOERTER = set("""
above again anderen being between both critical da daten doing down during each euch few firma firmen
further github go having hers heute him hin hinter his ich ihr ihre kritisch kunde kunden mittelstand
off ok once operating own platform plattform projekt same schau she system systems under unternehmen
until wo zu
""".split())
ZUSAETZLICHE_ANLAESSE = (
    r"have a look|schau\w*\s+euch|sieh\w*\s+(mal|dir)|guck\w*\s+(mal|dir)|make use|"
    r"brauchen wir|was bringt|bringt (das|es|mir)|github\.com/|w[uü]rde (mir|das|es) was bringen"
)


def lade_kern(wurzel=None, *, vorwissen=False, knoten=None):
    """Frisches Modul je Aufruf; so bleiben Testbestände und Suchfilter voneinander getrennt."""
    if not KERN_DATEI.exists():
        raise RuntimeError("Kokompass fehlt: zuerst 'git submodule update --init kern' ausführen.")
    spec = importlib.util.spec_from_file_location("kokompass_kern", KERN_DATEI)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    modul.WURZEL = Path(wurzel or INSTANZ).absolute()
    modul.BEZIEHUNGEN.update(ZUSAETZLICHE_BEZIEHUNGEN)
    original = modul.ist_knoten

    def ist_knoten(pfad):
        rel = pfad.relative_to(modul.WURZEL)
        if pfad.is_symlink():
            return False
        if vorwissen:
            return (original(pfad) and rel.parts[0] in SUCH_ORDNER
                    and pfad.stat().st_size <= 400_000)
        # Diese Instanz hat typisierte Wurzelknoten wie rules.md und kontextquellen.md.
        return original(pfad) or (len(rel.parts) == 1 and pfad.name not in modul.AUSGENOMMEN
                                  and bool(modul.frontmatter(modul.lies(pfad))[0].get("type")))

    modul.ist_knoten = ist_knoten
    if vorwissen:
        modul.STOP.update(ZUSAETZLICHE_STOPPWOERTER)
        modul.STOP.discard("bewertung")
        modul.ANLASS = re.compile(modul.ANLASS.pattern + "|" + ZUSAETZLICHE_ANLAESSE, re.I)
        laden = modul.laden

        def suchbestand():
            return dict(sorted(laden().items(), key=lambda item: (
                SUCH_ORDNER.index(Path(item[0].lstrip('/')).parts[0]), item[0])))

        modul.laden = suchbestand
    if knoten is not None:
        modul.laden = lambda: knoten
    return modul

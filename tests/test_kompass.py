"""Tests für werkzeuge/kompass.py gegen das erfundene Beispiel. Aufruf: python3 -m unittest discover tests"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WERKZEUG = REPO / "werkzeuge" / "kompass.py"


def kompass(ort: Path, *args: str, eingabe: str | None = None) -> subprocess.CompletedProcess:
    umgebung = dict(os.environ, KOMPASS_DIR=str(ort))
    return subprocess.run([sys.executable, str(WERKZEUG), *args], capture_output=True, text=True, input=eingabe,
                          env=umgebung, timeout=60)


class Beispiel(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ort = self.tmp / "kompass"
        shutil.copytree(REPO / "beispiel", self.ort, symlinks=True)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_startausgabe_beantwortet_den_kontext_test(self):
        aus = kompass(self.ort).stdout
        self.assertIn("KOMPASS von Mara", aus)
        self.assertIn("Forscherin für Nutzererfahrung", aus)          # wer
        self.assertIn("Ein Methodenbuch schreiben", aus)              # Ziele
        self.assertIn("Offen Mara: schreibbloecke-festlegen (hoch)", aus)
        self.assertIn("AN MARA (1", aus)                              # Fragen oben
        self.assertIn("kapitel-gliederung-entwerfen", aus.split("FRISTEN:")[1])

    def test_pruefen_ohne_befunde(self):
        r = kompass(self.ort, "pruefen")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("0 Befunde", r.stdout)

    def test_pruefen_findet_toten_verweis_und_fehlenden_type(self):
        (self.ort / "ideen" / "kaputt.md").write_text("---\ntitle: ohne type\nbetrifft: [/ideen/gibtsnicht.md]\n---\n")
        r = kompass(self.ort, "pruefen")
        self.assertEqual(r.returncode, 1)
        self.assertIn("kein type", r.stdout)
        self.assertIn("TOT", r.stdout)

    def test_sync_ist_idempotent_und_setzt_rueckverweise(self):
        kompass(self.ort, "sync")
        vorher = {p: p.read_text() for p in self.ort.rglob("*.md")}
        kompass(self.ort, "sync")
        self.assertEqual(vorher, {p: p.read_text() for p in self.ort.rglob("*.md")})
        idee = (self.ort / "ideen" / "methodenbuch.md").read_text()
        self.assertIn("Verweise hierher", idee)
        self.assertIn("verlag-oder-selbst.md", idee)

    def test_privat_und_werkzeug_sind_keine_knoten(self):
        (self.ort / "privat" / "geheim.md").write_text("geheimwort ohne frontmatter\n")
        self.assertIn("0 Befunde", kompass(self.ort, "pruefen").stdout)
        self.assertEqual(kompass(self.ort, "vorwissen", "geheimwort").stdout, "")

    def test_vorwissen_findet_und_bleibt_bei_smalltalk_still(self):
        aus = kompass(self.ort, "vorwissen", "Was hältst du von einem Verlag für das Methodenbuch?").stdout
        self.assertIn("fragen/verlag-oder-selbst.md", aus)
        still = kompass(self.ort, "vorwissen", "--auto", eingabe='{"prompt": "Guten Morgen, wie geht es dir heute?"}')
        self.assertEqual(still.stdout, "")
        laut = kompass(self.ort, "vorwissen", "--auto", eingabe='{"prompt": "Sollten wir einen Verlag nutzen?"}')
        self.assertIn("verlag-oder-selbst", laut.stdout)

    def test_ohne_kompass_klare_meldung(self):
        r = kompass(self.tmp, "stand")
        self.assertEqual(r.returncode, 2)
        self.assertIn("person/ich.md fehlt", r.stderr)


class Vorlage(unittest.TestCase):
    def test_vorlage_ist_gueltig(self):
        r = kompass(REPO / "vorlage", "pruefen")
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()

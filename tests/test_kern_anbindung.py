import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "werkzeuge"))
"""Integration der gemeinsamen Funktionen mit einer erfundenen privaten Instanz."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote
import re

import graph
import cli
import eingang
from kern_adapter import lade_kern


class KernAnbindung(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.schreiben('person/ich.md', '---\ntype: Person\nname: Lina\ntitle: Lina Beispiel\n---\n**Testrolle**')
        self.schreiben('person/ziele.md', '---\ntype: Ziel\n---\n1. **Ein Buch schreiben**')
        self.schreiben('stand/aktuell.md', '---\ntype: Stand\nstand: 2026-11-06\n---\nWeiterarbeiten')

    def tearDown(self):
        self.temp.cleanup()

    def schreiben(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_start_erhaelt_name_ziele_fragen_aufgaben_und_lokalen_regelverweis(self):
        self.schreiben('fragen/idee.md', '---\ntype: Frage\n---\n# An Lina\n1. Eine Frage')
        self.schreiben('berichte/faktenlage.md', '---\ntype: Bericht\n---\n# An Lina\nKopierte Frage')
        self.schreiben('aufgaben/buch.md', '---\ntype: Aufgabe\nwer: Lina\nstatus: offen\nprioritaet: hoch\n---\nBuch')
        self.schreiben('.agents/ARBEITSWEISE.md', '<!-- startausgabe:start -->\nLokale Regeln: rules.md\n<!-- startausgabe:ende -->')
        with patch.object(cli, 'ROOT', self.root):
            out = cli.status()
        for text in ['Wer: Lina Beispiel', 'Testrolle', 'Ein Buch schreiben', 'AN LINA (1',
                     'Offen Lina: buch (hoch)', 'Lokale Regeln: rules.md']:
            self.assertIn(text, out)

    def test_typisierte_wurzelknoten_bleiben_untypisierte_entwuerfe_ausgenommen(self):
        self.schreiben('rules.md', '---\ntype: Regel\n---\nRegel')
        draft = self.schreiben('UEBERGABE.md', 'Fremder Entwurf')
        self.schreiben('ideen/fehler.md', 'Knoten ohne type')
        kern = lade_kern(self.root)
        self.assertIn('/rules.md', kern.laden())
        self.assertNotIn('/UEBERGABE.md', kern.laden())
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(kern.pruefen(), 1)
        self.assertIn('/ideen/fehler.md: kein type', out.getvalue())
        self.assertEqual(draft.read_text(), 'Fremder Entwurf')

    def test_sync_und_pruefung_erhalten_zusaetzliche_beziehungen(self):
        self.schreiben('stationen/arbeit.md', '---\ntype: Station\ntitle: Arbeit\n---\nStation')
        self.schreiben('kanaele/buch.md', '---\ntype: Kanal\ntitle: Buch\n---\nKanal')
        self.schreiben('ideen/start.md', '---\ntype: Idee\nstationen: [/stationen/arbeit.md]\nkanal: [/kanaele/buch.md]\n---\nIdee')
        with patch.object(graph, 'ROOT', self.root), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(graph.cmd_sync(graph.laden()), 0)
            self.assertEqual(graph.cmd_pruefen(graph.laden()), 0)
        self.assertIn('Verweise hierher', (self.root / 'stationen/arbeit.md').read_text())
        self.assertIn('**Kanal:** [Buch]', (self.root / 'ideen/start.md').read_text())
        before = {p: p.read_bytes() for p in self.root.rglob('*.md')}
        with contextlib.redirect_stdout(io.StringIO()):
            lade_kern(self.root).sync()
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*.md')})

    def test_vorwissen_ignoriert_berichte_kern_und_privates(self):
        self.schreiben('ideen/vorhaben.md', '---\ntype: Idee\ntitle: Sternenwort\n---\nSternenwort')
        for folder in ['berichte', 'kern/beispiel', 'privat', '.zustand']:
            self.schreiben(folder + '/kopie.md', '---\ntype: Quelle\n---\nSternenwort')
        hits = lade_kern(self.root, vorwissen=True).suche('Sternenwort')
        self.assertEqual([item[1] for item in hits], ['/ideen/vorhaben.md'])

    def test_dateiausgabe_und_fehlercodes(self):
        target = self.root / 'ausgabe/stand.md'
        with patch.object(cli, 'ROOT', self.root), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['datei', str(target)]), 0)
            self.assertIn('Testrolle', target.read_text())
            self.assertEqual(cli.main(['unbekannt']), 2)

    def test_auto_hook_bleibt_bei_ungueltigem_json_still(self):
        with patch('sys.stdin', io.StringIO('{kaputt')), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(lade_kern(self.root, vorwissen=True).vorwissen(['--auto']), 0)
        self.assertEqual(out.getvalue(), '')

    def test_quellenindex_verweist_auf_wiki_im_vault(self):
        wiki = self.schreiben('Mein Vault/wiki/index.md', '# Wiki')
        with patch.object(graph, 'ROOT', self.root), patch.object(graph, 'VAULT', wiki.parent.parent):
            eingang.source_index(graph, {})
        report = (self.root / 'berichte/quellen.md').read_text()
        link = re.search(r'\[Zum Wiki\]\(([^)]+)\)', report).group(1)
        self.assertEqual(Path(unquote(link)), wiki)
        self.assertTrue(Path(unquote(link)).is_file())


if __name__ == '__main__':
    unittest.main()

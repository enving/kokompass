import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "werkzeuge"))
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "werkzeuge"))
import graph
import eingang


class EingangTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_root, self.old_vault = graph.ROOT, graph.VAULT
        self.old_mirror = graph.SPIEGEL_ORDNER
        graph.SPIEGEL_ORDNER = {"quellen"}
        graph.ROOT = Path(self.temp.name) / "kompass"
        graph.VAULT = Path(self.temp.name) / "vault"
        (graph.ROOT / "quellen").mkdir(parents=True)
        (graph.VAULT / "sources/Artikel").mkdir(parents=True)

    def tearDown(self):
        graph.ROOT, graph.VAULT = self.old_root, self.old_vault
        graph.SPIEGEL_ORDNER = self.old_mirror
        self.temp.cleanup()

    def test_fulltext_changed_version_and_idempotency(self):
        source = graph.VAULT / "sources/Artikel/test.md"
        source.write_text("---\ntitle: Test\n---\n" + "Langtext " * 1000)
        graph.cmd_eingang(graph.laden())
        node = graph.laden()["/quellen/test.md"]
        self.assertEqual(Path(node['fm']['source_snapshot']).read_bytes(), source.read_bytes())
        self.assertGreater(int(node['fm']['source_bytes']), 1200)
        self.assertEqual(graph.cmd_eingang(graph.laden()), 0)
        old = Path(node['fm']['source_snapshot'])
        source.write_text(source.read_text() + "NEUE TATSACHE")
        graph.cmd_eingang(graph.laden())
        node = graph.laden()["/quellen/test.md"]
        self.assertEqual(node['fm']['status'], 'geaendert')
        self.assertTrue(old.exists())
        self.assertNotEqual(old, Path(node['fm']['source_snapshot']))
        self.assertEqual(len(list((graph.ROOT / 'quellen').glob('*.md'))), 1)
        self.assertIn(f"- Unveränderte Quellversion: `{node['fm']['source_snapshot']}`", node['pfad'].read_text())

    def test_legacy_evaluation_not_claimed_for_new_hash(self):
        source = graph.VAULT / "sources/Artikel/test.md"
        source.write_text("ganzer Text")
        node = graph.ROOT / 'quellen/test.md'
        node.write_text('---\ntype: Reference\ntitle: Test\nstatus: ausgewertet\nvault_datei: sources/Artikel/test.md\n---\nMeine Auswertung')
        graph.cmd_eingang(graph.laden())
        text = node.read_text()
        self.assertIn('Meine Auswertung', text)
        self.assertIn('bewertung_version: nicht_protokolliert', text)
        self.assertNotIn('ausgewertet_sha256:', text)

    def test_reserved_name_does_not_disappear_from_graph(self):
        source = graph.VAULT / 'sources/Artikel/log.md'
        source.write_text('Notizen zum Projektverlauf')
        graph.cmd_eingang(graph.laden())
        self.assertIn('/quellen/quelle-log.md', graph.laden())
        self.assertEqual(graph.cmd_eingang(graph.laden()), 0)

    def test_kokompass_submodul_ist_kein_persoenlicher_knoten(self):
        example = graph.ROOT / 'kern/beispiel/person/ich.md'
        example.parent.mkdir(parents=True)
        example.write_text('---\ntype: Person\n---\nErfundene Person')
        own = graph.ROOT / 'person/ich.md'
        own.parent.mkdir(parents=True)
        own.write_text('---\ntype: Person\n---\nEigene Person')
        self.assertEqual(set(graph.laden()), {'/person/ich.md'})

    def test_user_edits_survive_export_and_conflict_reported(self):
        source = graph.ROOT / 'quellen/test.md'
        source.write_text('---\ntype: Reference\ntitle: Test\n---\nQuelle')
        eingang.mirror(graph, graph.laden(), '> Abzug\n')
        target = graph.VAULT / 'Kompass/Knoten/quellen/test.md'
        target.write_text(target.read_text() + '\nMaras Ergänzung')
        source.write_text(source.read_text() + '\nÄnderung Agent')
        eingang.mirror(graph, graph.laden(), '> Abzug\n')
        self.assertIn('Maras Ergänzung', target.read_text())
        self.assertNotIn('Änderung Agent', target.read_text())
        self.assertEqual(json.loads((graph.ROOT / '.zustand/spiegel-konflikte.json').read_text()), ['quellen/test.md'])

    def test_unknown_files_and_private_sources_preserved(self):
        dest = graph.VAULT / 'Kompass/Knoten/eigen.md'
        dest.parent.mkdir(parents=True)
        dest.write_text('Eigene Notiz')
        source = graph.ROOT / 'quellen/test.md'
        source.write_text('---\ntype: Reference\nvertraulich: ja\n---\nPrivat')
        eingang.mirror(graph, graph.laden(), '> Abzug\n')
        self.assertEqual(dest.read_text(), 'Eigene Notiz')
        self.assertFalse((dest.parent / 'quellen/test.md').exists())

    def test_identical_export_does_not_rewrite_icloud_files(self):
        source = graph.ROOT / 'quellen/test.md'
        source.write_text('---\ntype: Reference\n---\nOriginal')
        eingang.mirror(graph, graph.laden(), '')
        target = graph.VAULT / 'Kompass/Knoten/quellen/test.md'
        before = target.stat().st_mtime_ns
        eingang.mirror(graph, graph.laden(), '')
        self.assertEqual(target.stat().st_mtime_ns, before)

    def test_retired_export_saved_before_removal(self):
        source = graph.ROOT / 'quellen/test.md'
        source.write_text('---\ntype: Reference\n---\nOriginal')
        eingang.mirror(graph, graph.laden(), '')
        source.write_text('---\ntype: Reference\nvertraulich: ja\n---\nOriginal')
        eingang.mirror(graph, graph.laden(), '')
        self.assertFalse((graph.VAULT / 'Kompass/Knoten/quellen/test.md').exists())
        archived = list((graph.ROOT.parent / 'kompass-quellen/spiegel-archiv').rglob('test.md'))
        self.assertEqual(len(archived), 1)
        self.assertIn('Original', archived[0].read_text())


if __name__ == '__main__':
    unittest.main()

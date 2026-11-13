import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "werkzeuge"))
"""Der Instanzprüfer muss echte kaputte Knoten weiterhin ablehnen."""
from pathlib import Path
import tempfile
import unittest
import cli as kompass


@unittest.skipUnless((Path.home() / ".agents/skills/okf/okf-validate.mjs").is_file(), "Optionaler OKF-Prüfer nicht installiert")
class OKFPruefungTest(unittest.TestCase):
    def test_dokumentation_ausnehmen_defekten_knoten_melden(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'person').mkdir()
            (root / 'person/ich.md').write_text('---\ntype: Person\n---\n# Ich\n')
            (root / 'UEBERGABE.md').write_text('# Lokale Übergabe\n')
            (root / 'kern').mkdir()
            (root / 'kern/README.md').write_text('# Fremdes Repo\n')
            self.assertEqual(kompass.okf_pruefen(root), 0)
            (root / 'person/defekt.md').write_text('# Kein Typ\n')
            self.assertEqual(kompass.okf_pruefen(root), 1)
            (root / 'person/defekt.md').write_text('---\ntype: \n---\n')
            self.assertEqual(kompass.okf_pruefen(root), 1)
            (root / 'person/defekt.md').write_text('---\ntype: Person\n---\n')
            self.assertEqual(kompass.okf_pruefen(root), 0)

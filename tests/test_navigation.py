"""Vollständiger lokaler Durchlauf mit zwei erfundenen Projekt-Repos."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'werkzeuge'))
import aufgaben
import dirigent_db
import navigation
import wissen
from eingang import set_fields


class NavigationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'kompass'
        shutil.copytree(REPO / 'vorlage', self.root)
        self.env = patch.dict(os.environ, {'KOMPASS_DIR': str(self.root)})
        self.env.start()
        self.addCleanup(self.env.stop)
        for key, value in [('ROOT', self.root), ('STATE', self.root / '.zustand/eingaenge.json'), ('VAULT', None)]:
            setting = patch.object(wissen, key, value)
            setting.start()
            self.addCleanup(setting.stop)

    def project(self, name, handoff):
        repo = self.base / name
        repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        (repo / 'AGENTS.md').write_text('# Projektregeln\nNur den freigegebenen Auftrag bearbeiten.\n')
        (repo / 'UEBERGABE.md').write_text(handoff)
        (repo / 'README.md').write_text('# ' + name + '\n')
        return repo

    def config(self, values):
        path = self.root / 'kontextquellen.md'
        text = path.read_text()
        path.write_text(set_fields(text, {key: json.dumps(value, ensure_ascii=False) for key, value in values.items()}))

    def test_empty_instance_stays_local_and_paused(self):
        with patch.object(aufgaben, 'github_owner', side_effect=AssertionError('Kein Netzauftrag')), \
             contextlib.redirect_stdout(io.StringIO()):
            state = aufgaben.aktualisieren()
        self.assertEqual(state['repos'], [])
        self.assertEqual(state['items'], {})
        self.assertEqual(dirigent_db.weiter_auswahl(state)['zustand'], 'angehalten')
        self.assertEqual(navigation.diagnose()['fehler'], 0)

    def test_two_repos_route_to_originals_without_authorizing_work(self):
        book = self.project('buch', '# Auftrag\nGliederung prüfen.\n')
        notes = self.project('notizen', '# Wartet auf dich\nVeröffentlichung noch nicht freigegeben.\n')
        self.config({'repo_pfade': [str(book), str(notes)]})
        before = {p: p.read_bytes() for repo in (book, notes) for p in repo.glob('*.md')}
        with contextlib.redirect_stdout(io.StringIO()):
            state = aufgaben.aktualisieren()
        routes = navigation.repos()
        self.assertEqual({x['pfad'] for x in routes}, {str(book.resolve()), str(notes.resolve())})
        self.assertTrue(all(x['einstieg'] and x['uebergaben'] for x in routes))
        self.assertEqual(dirigent_db.weiter_auswahl(state)['bereit'], [])
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        # Erst ein expliziter übernommener Originalauftrag kann bereitgestellt werden.
        state['fortsetzungssteuerung']['angehalten'] = False
        state['fortsetzungen'] = {
            'buch:1': {'status': 'bereit_zur_uebernahme', 'originalauftrag': 'Gliederung prüfen',
                       'zielprojekt': 'buch', 'quelle': str(book / 'UEBERGABE.md'),
                       'checkpoint': 'version-eins', 'naechster_schritt': 'Gliederung lesen'},
            'notizen:1': {'status': 'bereit_zur_uebernahme', 'wartet_auf': 'person'}}
        selected = dirigent_db.weiter_auswahl(state)
        self.assertEqual([x['kennung'] for x in selected['bereit']], ['buch:1'])
        self.assertEqual(selected['klaeren'], ['notizen:1'])
        self.assertEqual(dirigent_db.weiter_exit(selected, abschluss=True), 3)

    def test_missing_explicit_repo_is_reported(self):
        missing = self.base / 'fehlt'
        self.config({'repo_pfade': [str(missing)]})
        self.assertGreater(navigation.diagnose()['fehler'], 0)
        self.assertIn('fehler', navigation.repos()[0])

    def test_remote_never_exposes_embedded_credentials(self):
        repo = self.project('werkstatt', '# Stand\n')
        self.config({'repo_pfade': [str(repo)]})
        subprocess.run(['git', '-C', str(repo), 'remote', 'add', 'origin',
                        'https://synthetic-user:synthetic-secret@example.org/gruppe/werkstatt.git'], check=True)
        result = json.dumps(navigation.repos())
        self.assertNotIn('synthetic-secret', result)
        self.assertNotIn('synthetic-user', result)
        self.assertIn('https://example.org/gruppe/werkstatt.git', result)

    def test_unknown_command_fails_in_fresh_instance(self):
        result = subprocess.run([sys.executable, str(REPO / 'werkzeuge/kompass.py'), 'gibt-es-nicht'],
                                env={**os.environ, 'KOMPASS_DIR': str(self.root)}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)

    def test_remote_reference_is_not_a_missing_local_directory(self):
        (self.root / 'belege').mkdir(exist_ok=True)
        for index, reference in enumerate(['github.com/beispiel/werkstatt',
                                           'https://github.com/beispiel/werkstatt',
                                           'git@github.com:beispiel/werkstatt.git']):
            (self.root / f'belege/remote-{index}.md').write_text(
                '---\ntype: Beleg\nrepo: ' + reference + '\n---\n')
        self.assertEqual(navigation.repos(), [])


if __name__ == '__main__':
    unittest.main()

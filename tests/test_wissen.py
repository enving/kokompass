import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "werkzeuge"))
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import wissen


class RegisterTest(unittest.TestCase):
    def test_repo_discovery_includes_explicit_local_compass_reference(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            root = base / 'kompass'
            (root / 'belege').mkdir(parents=True)
            external = base / 'andere-stelle/projekt'
            (external / '.git').mkdir(parents=True)
            (root / 'belege/projekt.md').write_text('---\ntype: Beleg\nrepo: '+str(external)+'\n---\n')
            with patch.object(wissen, 'ROOT', root), patch.object(wissen, 'HOME', base):
                self.assertIn(external.resolve(), wissen.repo_paths())

    def test_broad_scan_preserves_pilot_tasks_and_conversation_cursors(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state = root / 'state.json'
            original = {'items': {}, 'triage_hash_scan': {'datum': 'behalten'},
                        'repo_scan': 'gestern', 'aufgaben_abgleich': {'stand': 'gestern'},
                        'gespraeche': {'thread': {'position': 12}}}
            state.write_text(json.dumps(original))
            with patch.object(wissen, 'ROOT', root), patch.object(wissen, 'STATE', state), \
                 patch.object(wissen, 'discover', return_value=[]), patch.object(wissen, 'scan_repos', return_value=[]), \
                 patch.object(wissen, 'status'):
                wissen.scan()
            saved = json.loads(state.read_text())
            for key in ('triage_hash_scan', 'repo_scan', 'aufgaben_abgleich', 'gespraeche'):
                self.assertEqual(saved[key], original[key])

    def test_broad_scan_rejects_concurrent_register_update(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / 'state.json'
            state.write_text('{"items": {}}')
            def concurrent():
                state.write_text('anderer Lauf')
                return []
            with patch.object(wissen, 'STATE', state), patch.object(wissen, 'discover', return_value=[]), \
                 patch.object(wissen, 'scan_repos', side_effect=concurrent):
                with self.assertRaisesRegex(RuntimeError, 'zwischenzeitlich'):
                    wissen.scan()
            self.assertEqual(state.read_text(), 'anderer Lauf')

    def test_handoff_discovery_includes_nested_and_ignored_root_but_not_external_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            repo = base / 'repo'
            repo.mkdir()
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            (repo / '.gitignore').write_text('/UEBERGABE.md\nignored/\n')
            (repo / 'UEBERGABE.md').write_text('Nur lokal')
            (repo / 'docs').mkdir()
            nested = repo / 'docs/uebergabe.md'
            nested.write_text('Aktueller Kontext')
            (repo / 'archiv').mkdir()
            archived = repo / 'archiv/UEBERGABE.md'
            archived.write_text('Abgeschlossener Altstand')
            (repo / 'skills').mkdir()
            template = repo / 'skills/handoff.md'
            template.write_text('Anleitung, kein Auftrag')
            (repo / 'ignored').mkdir()
            (repo / 'ignored/uebergabe.md').write_text('Ignorierter Unterordner')
            external = base / 'private.md'
            external.write_text('Nicht lesen')
            (repo / 'handoff.md').symlink_to(external)
            subprocess.run(['git', '-C', str(repo), 'add', '-f', 'docs/uebergabe.md', 'archiv/UEBERGABE.md', 'skills/handoff.md'], check=True)
            self.assertEqual(wissen.handoff_files(repo.resolve()), sorted([repo.resolve() / 'UEBERGABE.md', nested.resolve(), archived.resolve(), template.resolve()]))
            self.assertEqual(wissen.handoff_kind(archived, repo), 'Archiv')
            self.assertEqual(wissen.handoff_kind(template, repo), 'Vorlage/Anleitung')
            self.assertEqual(wissen.handoff_kind(nested, repo), 'Übergabe')
            with patch.object(wissen, 'HOME', base), patch.object(wissen, 'VAULT', base / 'vault'), \
                 patch.object(wissen, 'repo_paths', return_value=[repo.resolve()]):
                found = [p for kind, p in wissen.discover() if kind == 'repo-uebergabe']
            self.assertEqual(sorted(found), wissen.handoff_files(repo.resolve()))

    def test_handoffs_preserve_pilot_state_and_use_content_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            p = root / 'UEBERGABE.md'
            p.write_text('eins')
            state = root / '.zustand/eingaenge.json'
            state.parent.mkdir()
            original = {'scan': '2026-01-01', 'triage_hash_scan': {'datum': 'behalten'},
                        'items': {'vault': {'art': 'obsidian', 'pfad': '/unverändert', 'status': 'entdeckt'}}}
            state.write_text(json.dumps(original))
            repos = [{'pfad': str(root), 'uebergaben': [str(p)]}]
            with patch.object(wissen, 'ROOT', root), patch.object(wissen, 'STATE', state), \
                 patch.object(wissen, 'scan_repos', return_value=repos):
                self.assertFalse(wissen.handoffs())
                saved = json.loads(state.read_text())
                self.assertEqual(saved['scan'], original['scan'])
                self.assertEqual(saved['triage_hash_scan'], original['triage_hash_scan'])
                self.assertEqual(saved['items']['vault'], original['items']['vault'])
                key = next(k for k in saved['items'] if k != 'vault')
                entry = saved['items'][key]
                entry.update(gelesen=True, gelesen_sha256=entry['source_sha256'], status='eingearbeitet')
                state.write_text(json.dumps(saved))
                wissen.handoffs()
                self.assertTrue(json.loads(state.read_text())['items'][key]['gelesen'])
                mtime = p.stat().st_mtime_ns
                p.write_text('zwei')
                os.utime(p, ns=(mtime, mtime))
                wissen.handoffs()
                changed = json.loads(state.read_text())['items'][key]
                self.assertEqual(changed['status'], 'geaendert')
                self.assertFalse(changed['gelesen'])
                self.assertNotEqual(changed['source_sha256'], changed['gelesen_sha256'])
                p.unlink()
                repos[0]['uebergaben'] = []
                wissen.handoffs()
                self.assertEqual(json.loads(state.read_text())['items'][key]['status'], 'nicht_mehr_am_pfad')

    def test_handoff_scan_does_not_overwrite_concurrent_register_update(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state = root / 'state.json'
            state.write_text(json.dumps({'scan': 'alt', 'items': {}}))
            def concurrent():
                state.write_text('anderer Lauf')
                return []
            with patch.object(wissen, 'ROOT', root), patch.object(wissen, 'STATE', state), \
                 patch.object(wissen, 'scan_repos', side_effect=concurrent):
                with self.assertRaisesRegex(RuntimeError, 'zwischenzeitlich'):
                    wissen.handoffs()
            self.assertEqual(state.read_text(), 'anderer Lauf')

    def test_handoff_repo_error_keeps_prior_entries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            p = root / 'UEBERGABE.md'
            p.write_text('Stand behalten')
            entry = {'art': 'repo-uebergabe', 'pfad': str(p), 'status': 'entdeckt'}
            state = root / 'state.json'
            state.write_text(json.dumps({'scan': 'alt', 'items': {'handoff': entry}}))
            repos = [{'pfad': str(root), 'fehler': 'Git-Dateiliste nicht lesbar'}]
            with patch.object(wissen, 'ROOT', root), patch.object(wissen, 'STATE', state), \
                 patch.object(wissen, 'scan_repos', return_value=repos):
                self.assertTrue(wissen.handoffs())
            self.assertEqual(json.loads(state.read_text())['items']['handoff'], entry)
            self.assertIn('Git-Dateiliste nicht lesbar', (root / 'berichte/eingaenge.md').read_text())

    def test_changed_source_reopens_and_missing_file_stays_visible(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            root = base / 'kompass'
            source = base / 'quelle.txt'
            source.write_text('Quelle eins')
            page = root / 'wissen.md'
            root.mkdir()
            page.write_text('Auswertung')
            state = root / '.zustand/eingaenge.json'
            with patch.object(wissen, 'ROOT', root), patch.object(wissen, 'STATE', state), \
                 patch.object(wissen, 'VAULT', base / 'vault'), patch.object(wissen, 'scan_repos', return_value=[]), \
                 patch.object(wissen, 'discover', return_value=[('obsidian', source)]) as discovery:
                wissen.scan()
                entry = json.loads(state.read_text())['items']
                key = next(iter(entry))
                self.assertFalse(entry[key]['gelesen'])
                wissen.done(key, [str(page)])
                wissen.scan()
                self.assertEqual(json.loads(state.read_text())['items'][key]['status'], 'eingearbeitet')
                source.write_text('Geänderter Inhalt mit neuem Fakt')
                wissen.scan()
                record = json.loads(state.read_text())['items'][key]
                self.assertEqual(record['status'], 'geaendert')
                self.assertFalse(record['gelesen'])
                self.assertEqual(record['wiki'], [])
                discovery.return_value = []
                wissen.scan()
                self.assertEqual(json.loads(state.read_text())['items'][key]['status'], 'nicht_mehr_am_pfad')
                discovery.return_value = [('obsidian', source)]
                wissen.scan()
                self.assertNotEqual(json.loads(state.read_text())['items'][key]['status'], 'nicht_mehr_am_pfad')

    def test_completion_rejects_source_changed_after_scan(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            source = base / 'quelle.txt'
            source.write_text('Version eins')
            state = base / '.zustand/eingaenge.json'
            with patch.object(wissen, 'ROOT', base), patch.object(wissen, 'STATE', state), \
                 patch.object(wissen, 'scan_repos', return_value=[]), \
                 patch.object(wissen, 'discover', return_value=[('obsidian', source)]):
                wissen.scan()
                key = next(iter(json.loads(state.read_text())['items']))
                source.write_text('Neue ungelesene Version')
                with self.assertRaises(ValueError):
                    wissen.done(key, [str(source)])


if __name__ == '__main__':
    unittest.main()

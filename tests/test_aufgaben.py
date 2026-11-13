import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "werkzeuge"))
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import aufgaben
import kontext
import wissen


def issue(number, pr=False):
    return {'html_url': f'https://github.com/beispiel/projekt/{"pull" if pr else "issues"}/{number}',
            'number': number, 'title': 'Titel | <Text>', 'state': 'open', 'labels': [{'name': 'wer:agent'}],
            'assignees': [], 'updated_at': '2026-11-07T10:00:00Z', **({'pull_request': {}} if pr else {})}


class AufgabenTest(unittest.TestCase):
    def test_github_pages_dedupe_and_reject_incomplete_result(self):
        pages = [{'total_count': 2, 'incomplete_results': False, 'items': [issue(1)]},
                 {'total_count': 2, 'incomplete_results': False, 'items': [issue(2, True)]}]
        def read():
            return subprocess.CompletedProcess([], 0, json.dumps(pages), '')
        with patch.object(aufgaben.subprocess, 'run', side_effect=lambda *a, **k: read()):
            result = aufgaben.github_lesen('beispiel')
            self.assertEqual({x['art'] for x in result}, {'Issue', 'PR'})
            pages.pop()
            with self.assertRaisesRegex(ValueError, 'fehlende Ergebnisseite'):
                aufgaben.github_lesen('beispiel')
            pages[0]['total_count'] = 1
            pages[0]['incomplete_results'] = True
            with self.assertRaisesRegex(ValueError, 'unvollständig'):
                aufgaben.github_lesen('beispiel')

    def test_failed_fetch_retains_last_success_and_owner_change_drops_cache(self):
        old = {'owner': 'beispiel', 'stand': 'gestern', 'items': [{'url': 'behalten'}]}
        state = {'aufgaben_abgleich': {'github': old}}
        with patch.object(aufgaben, 'github_lesen', side_effect=subprocess.TimeoutExpired('gh', 90)):
            result = aufgaben.github_abgleichen(state, 'beispiel')
            self.assertEqual(result['items'], old['items'])
            self.assertEqual(result['stand'], 'gestern')
            self.assertTrue(result['fehler'])
            self.assertEqual(aufgaben.github_abgleichen(state, 'anderer')['items'], [])

    def test_thematic_context_reads_current_handoff_and_graph_relations(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'ideen').mkdir()
            (root / 'ideen/thema.md').write_text('---\ntype: Idee\ntitle: Sternenprojekt\nbetrifft: [/ideen/bezug.md]\n---\n')
            (root / 'ideen/bezug.md').write_text('---\ntype: Idee\ntitle: Fachlicher Bezug\n---\n')
            repo = root / 'repo'
            repo.mkdir()
            path = repo / 'UEBERGABE.md'
            path.write_text('Sternenprojekt: alter Auftrag')
            state = {'repos': [{'pfad': str(repo), 'uebergaben': [str(path)]}], 'items': {},
                     'aufgaben_abgleich': {'stand': 'heute', 'github': {
                         'owner': 'beispiel', 'items': [], 'fehler': 'Ausfall', 'stand': 'gestern'}}}
            first = kontext.erschliessen('Sternenprojekt', state, root)
            self.assertIn('/ideen/bezug.md', [item['id'] for item in first['kompass']])
            path.write_text('Sternenprojekt: Ergebnis inzwischen geprüft')
            second = kontext.erschliessen('Sternenprojekt', state, root)
            self.assertNotEqual(first['projektquellen'][0]['sha256'], second['projektquellen'][0]['sha256'])
            self.assertIn('inzwischen geprüft', second['projektquellen'][0]['ausschnitte'][0]['text'])
            self.assertTrue(any(item.get('letzter_erfolg') == 'gestern' for item in second['luecken']))
            self.assertFalse((root / 'berichte/aufgaben.md').exists())

    def test_context_skips_external_symlink_and_archive_handoffs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo = root / 'repo'
            repo.mkdir()
            outside = root / 'privat.md'
            outside.write_text('Sternenprojekt: nicht freigegeben')
            (repo / 'UEBERGABE.md').symlink_to(outside)
            (repo / 'archiv').mkdir()
            archive = repo / 'archiv/UEBERGABE.md'
            archive.write_text('Sternenprojekt: alter Auftrag')
            state = {'items': {}, 'repos': [{'pfad': str(repo), 'uebergaben': [str(repo / 'UEBERGABE.md'), str(archive)]}],
                     'aufgaben_abgleich': {'stand': 'heute', 'github': {'items': [], 'fehler': None}}}
            result = kontext.erschliessen('Sternenprojekt', state, root)
            self.assertEqual(result['projektquellen'], [])
            self.assertTrue(any(item.get('quelle') == str(repo / 'UEBERGABE.md') for item in result['luecken']))

    def test_successful_refresh_records_removal_without_completing_task(self):
        old = {'owner': 'beispiel', 'stand': 'gestern', 'items': [{'url': 'alte-issue-url'}]}
        new = {'url': 'neue-issue-url', 'status': 'open'}
        with patch.object(aufgaben, 'github_lesen', return_value=[new]):
            result = aufgaben.github_abgleichen({'aufgaben_abgleich': {'github': old}}, 'beispiel')
        self.assertEqual(result['nicht_mehr_offen'], ['alte-issue-url'])
        self.assertEqual(result['neu'], ['neue-issue-url'])
        self.assertEqual(old['items'], [{'url': 'alte-issue-url'}])
        self.assertNotIn('erledigt', result)

    def test_concurrent_register_update_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state = root / 'state.json'
            state.write_text('{"items": {}, "repos": []}')
            def other_writer(*args):
                state.write_text('anderer Lauf')
                return {'owner': 'beispiel', 'items': [], 'fehler': None, 'stand': 'heute'}
            with patch.object(wissen, 'ROOT', root), patch.object(wissen, 'STATE', state), \
                 patch.object(wissen, 'scan'), \
                 patch.object(wissen, 'handoffs', return_value=False), \
                 patch.object(wissen, 'felder', return_value={'github_aktiv': 'ja'}), \
                 patch.object(aufgaben, 'github_owner', return_value='beispiel'), \
                 patch.object(aufgaben, 'github_abgleichen', side_effect=other_writer):
                with self.assertRaisesRegex(RuntimeError, 'zwischenzeitlich'):
                    aufgaben.aktualisieren()
            self.assertEqual(state.read_text(), 'anderer Lauf')
            self.assertFalse((root / 'berichte/aufgaben.md').exists())


if __name__ == '__main__':
    unittest.main()

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "werkzeuge"))
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import github_fehler as ghf


REPO = {'id': 123, 'full_name': 'beispiel/projekt'}
RUN = {'id': 456, 'repository': REPO, 'run_attempt': 1, 'status': 'completed',
       'conclusion': 'failure', 'head_sha': 'a' * 40, 'updated_at': '2026-11-07T10:00:00Z',
       'pull_requests': [{'number': 7, 'base': {'repo': {'id': 123}}}]}
PROJECT = {'id': 'projekt-1', 'repositoryIdentity': {'canonicalKey': 'github.com/beispiel/projekt'}}
THREAD = {'threadId': 'faden-1', 'projectId': 'projekt-1', 'status': 'completed', 'settled': True,
          'pullRequests': [{'repository': 'beispiel/projekt', 'number': 7}]}


def context(projects=None, threads=None):
    return {'projekte': {'projects': [PROJECT] if projects is None else projects, 'nextCursor': None},
            'faeden': {'threads': [THREAD] if threads is None else threads, 'nextCursor': None}}


def read_original(run=None):
    with patch.object(ghf, 'api', side_effect=[REPO, run or RUN]):
        return ghf.original('beispiel/projekt', 456, ['beispiel/projekt'], ['failure'])


class GitHubFehlerTest(unittest.TestCase):
    def test_repo_filter_before_any_request_and_no_shell_interpolation(self):
        with patch.object(ghf, 'api') as api:
            for repo in ['fremd/projekt', 'beispiel/projekt/../../privat', '-H/Authorization']:
                with self.assertRaises(ValueError):
                    ghf.original(repo, 456, ['beispiel/projekt'], ['failure'])
            api.assert_not_called()

    def test_live_identity_must_match_event_lookup(self):
        for key, value in [('id', 999), ('repository', {'id': 999, 'full_name': REPO['full_name']})]:
            run = {**RUN, key: value}
            with self.assertRaises(ValueError):
                read_original(run)

    def test_only_current_failed_completed_run_is_accepted(self):
        for changed in [{'status': 'in_progress'}, {'conclusion': 'success'}, {'run_attempt': 0}]:
            with self.assertRaises(ValueError):
                read_original({**RUN, **changed})
        self.assertNotEqual(read_original()['kennung'], read_original({**RUN, 'run_attempt': 2})['kennung'])

    def test_webhook_repo_id_and_attempt_must_still_match_original(self):
        for repo_id, attempt in [(999, 1), (123, 2)]:
            with patch.object(ghf, 'api', side_effect=[REPO, RUN]), self.assertRaises(ValueError):
                ghf.original('beispiel/projekt', 456, ['beispiel/projekt'], ['failure'], repo_id, attempt)

    def test_original_repo_and_pr_find_settled_owner_without_restarting_it(self):
        event = read_original()
        self.assertEqual(event['repository_id'], 123)
        route = ghf.zuordnen(event, context())
        self.assertEqual(route['threadId'], 'faden-1')
        self.assertTrue(route['settled'])
        self.assertEqual(route['status'], 'originalauftrag_pruefen')
        active = {**THREAD, 'status': 'running', 'settled': False}
        self.assertEqual(ghf.zuordnen(event, context(threads=[active]))['status'], 'bearbeiter_aktiv')

    def test_fork_origin_does_not_claim_upstream_event(self):
        fork = copy.deepcopy(PROJECT)
        fork['repositoryIdentity']['origin'] = {'canonicalKey': 'github.com/beispiel/fork'}
        self.assertEqual(ghf.zuordnen(read_original(), context(projects=[fork]))['status'], 'projekt_offen')

    def test_no_guess_when_project_thread_or_pr_is_ambiguous_or_missing(self):
        event = read_original()
        duplicate_project = {**PROJECT, 'id': 'projekt-2'}
        self.assertEqual(ghf.zuordnen(event, context(projects=[PROJECT, duplicate_project]))['status'], 'projekt_offen')
        duplicate_thread = {**THREAD, 'threadId': 'faden-2'}
        self.assertEqual(ghf.zuordnen(event, context(threads=[THREAD, duplicate_thread]))['status'], 'auftrag_offen')
        self.assertEqual(ghf.zuordnen({**event, 'prs': []}, context())['status'], 'auftrag_offen')

    def test_incomplete_t3_pages_do_not_produce_unique_owner(self):
        for part in ['projekte', 'faeden']:
            ctx = context()
            ctx[part]['nextCursor'] = 100
            self.assertEqual(ghf.zuordnen(read_original(), ctx)['status'], 't3_abgleich_unvollstaendig')
        self.assertEqual(ghf.zuordnen(read_original(), {})['status'], 't3_abgleich_unvollstaendig')

    def test_register_replay_preserves_foreign_fields_delivery_and_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'kontextquellen.md').write_text('---\ngithub_workflow_repos: [beispiel/projekt]\n'
                'github_fehler_conclusions: [failure]\n---\n')
            path = root / 'register.json'
            path.write_text(json.dumps({'fremd': {'behalten': 42}, 'fortsetzungssteuerung': {'angehalten': True}}))
            for iteration in range(2):
                with patch.object(ghf, 'api', side_effect=[REPO, RUN]):
                    result = ghf.erfassen('beispiel/projekt', 456, context(), root, path)
                self.assertTrue(result['angehalten'])
                self.assertEqual(result['zustellung'], 'nicht_ausgefuehrt')
                self.assertEqual(result['wiederholung'], bool(iteration))
            state = json.loads(path.read_text())
            self.assertEqual(state['fremd'], {'behalten': 42})
            self.assertEqual(len(state['github_ereignisse']), 1)
            event = next(iter(state['github_ereignisse'].values()))
            event['zustellbeleg'] = 'vorhandener-beleg'
            path.write_text(json.dumps(state))
            with patch.object(ghf, 'api', side_effect=[REPO, RUN]):
                ghf.erfassen('beispiel/projekt', 456, context(), root, path)
            self.assertEqual(next(iter(json.loads(path.read_text())['github_ereignisse'].values()))['zustellbeleg'],
                             'vorhandener-beleg')

    def test_missing_control_fails_closed_and_concurrent_write_survives(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'kontextquellen.md').write_text('---\ngithub_workflow_repos: [beispiel/projekt]\n'
                'github_fehler_conclusions: [failure]\n---\n')
            path = root / 'register.json'
            path.write_text('{}')
            with patch.object(ghf, 'api', side_effect=[REPO, RUN]):
                self.assertTrue(ghf.erfassen('beispiel/projekt', 456, context(), root, path)['angehalten'])
            def interfering(*args):
                path.write_text('{"anderer_lauf": true}')
                return event
            event = read_original()
            path.write_text('{}')
            with patch.object(ghf, 'original', side_effect=interfering):
                with self.assertRaisesRegex(RuntimeError, 'zwischenzeitlich'):
                    ghf.erfassen('beispiel/projekt', 456, context(), root, path)
            self.assertEqual(json.loads(path.read_text()), {'anderer_lauf': True})


def lauf(wf, zeit, conclusion, status='completed', name=None):
    return {'workflow_id': wf, 'created_at': zeit, 'conclusion': conclusion, 'status': status,
            'name': name or f'wf{wf}', 'event': 'schedule', 'html_url': f'https://x/{wf}/{zeit}'}


class RotlisteTest(unittest.TestCase):
    def fake_api(self, runs, repos=None, kaputt=()):
        repos = repos if repos is not None else [{'full_name': 'beispiel/a'}, {'full_name': 'beispiel/fork', 'fork': True},
                                                  {'full_name': 'beispiel/alt', 'archived': True}, {'full_name': 'beispiel/b'}]
        def api_fn(path):
            if path.startswith('user/repos'):
                return repos
            repo = path.split('/')[1] + '/' + path.split('/')[2]
            if repo in kaputt:
                raise subprocess.CalledProcessError(1, 'gh')
            return {'workflow_runs': runs.get(repo, [])}
        return api_fn

    def test_only_latest_completed_run_per_workflow_counts_and_forks_are_skipped(self):
        runs = {'beispiel/a': [lauf(1, '2026-11-01T00:00:00Z', 'failure'),
                               lauf(1, '2026-11-02T00:00:00Z', 'success'),   # repariert
                               lauf(2, '2026-11-03T00:00:00Z', 'failure'),
                               lauf(2, '2026-11-04T00:00:00Z', None, status='in_progress')],
                'beispiel/fork': [lauf(9, '2026-11-05T00:00:00Z', 'failure')]}
        daten = ghf.rotliste(['failure'], self.fake_api(runs), '2026-11-09T10:00:00+01:00')
        self.assertEqual([(e['repo'], e['workflow']) for e in daten['eintraege']], [('beispiel/a', 'wf2')])
        self.assertEqual(daten['repos_geprueft'], 2)

    def test_unreadable_repo_is_reported_not_hidden(self):
        daten = ghf.rotliste(['failure'], self.fake_api({}, kaputt=('beispiel/b',)), '2026-11-09T10:00:00+01:00')
        self.assertEqual(daten['fehler'], ['beispiel/b'])
        self.assertEqual(daten['repos_geprueft'], 1)

    def test_pagination_reads_all_pages(self):
        # Reale Beobachtung 09.11.2026: erste Seite mit 44 von 100, danach weitere Seiten.
        seiten = [[{'full_name': f'b/r{i}'} for i in range(44)], [{'full_name': 'b/letztes'}], []]
        aufrufe = []
        def api_fn(path):
            aufrufe.append(path)
            return seiten[len(aufrufe) - 1]
        self.assertEqual(len(ghf.eigene_repos(api_fn)), 45)

    def test_status_line_marks_fresh_and_stale(self):
        with tempfile.TemporaryDirectory() as folder:
            ziel = Path(folder) / 'rot.json'
            from datetime import datetime, timezone
            heute = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)
            self.assertIn('noch kein Abgleich', ghf.status_zeile(ziel, heute))
            ziel.write_text(json.dumps({'stand': '2026-11-09T10:00:00+01:00', 'repos_geprueft': 3, 'fehler': [],
                'eintraege': [lauf(1, '2026-11-08T00:00:00Z', 'failure') | {'repo': 'b/neu', 'workflow': 'Backup',
                                                                            'zeit': '2026-11-08T00:00:00Z'},
                              {'repo': 'b/alt', 'workflow': 'CI', 'conclusion': 'failure',
                               'zeit': '2025-01-01T00:00:00Z', 'url': 'u'}]}))
            zeile = ghf.status_zeile(ziel, heute)
            self.assertIn('2 Workflows rot in 2 Repos', zeile)
            self.assertIn('neu/Backup', zeile)
            self.assertNotIn('alt/CI', zeile)
            self.assertNotIn('VERALTET', zeile)
            self.assertIn('VERALTET', ghf.status_zeile(ziel, datetime(2026, 11, 12, tzinfo=timezone.utc)))


class KontingentTest(unittest.TestCase):
    @staticmethod
    def fake_api(pfad):
        if pfad.startswith('user/repos'):
            return [] if 'page=2' in pfad else [
                {'full_name': 'ich/aktiv', 'fork': False, 'archived': False, 'private': True},
                {'full_name': 'ich/alt', 'fork': False, 'archived': True, 'private': True},
                {'full_name': 'ich/oeffentlich', 'fork': False, 'archived': False, 'private': False}]
        if pfad.startswith('repos/ich/alt/actions/artifacts'):
            return {'artifacts': [] if 'page=2' in pfad else [
                {'id': 1, 'size_in_bytes': 400 * 2**20, 'expired': False},
                {'id': 2, 'size_in_bytes': 99 * 2**20, 'expired': True}]}
        if pfad.startswith('repos/ich/aktiv/actions/artifacts'):
            return {'artifacts': []}
        if pfad.startswith('repos/ich/oeffentlich'):
            raise AssertionError('öffentliches Repo darf nicht gezählt werden')
        if pfad == 'user':
            return {'login': 'ich'}
        if pfad.startswith('users/ich/settings/billing/usage'):
            return {'usageItems': [{'netAmount': 0.0}, {'netAmount': 1.25}]}
        raise AssertionError(pfad)

    def test_archived_repos_count_and_expired_do_not(self):
        d = ghf.kontingente(self.fake_api)
        self.assertEqual(d['gesamt_bytes'], 400 * 2**20)  # nur Artefakte privater Repos; abgelaufene, Cache und öffentliche zählen nicht
        self.assertEqual(d['je_repo'][0]['repo'], 'ich/alt')
        self.assertEqual(d['kosten_netto_eur'], 1.25)

    def test_warning_line_names_biggest_repo_and_costs(self):
        zeile = ghf.kontingente_zeile(ghf.kontingente(self.fake_api))
        self.assertIn('WARNUNG', zeile)
        self.assertIn('ich/alt', zeile)
        self.assertIn('1.25', zeile)

    def test_missing_billing_scope_keeps_storage(self):
        def api(pfad):
            if pfad == 'user':
                raise subprocess.CalledProcessError(1, 'gh')
            return self.fake_api(pfad)
        d = ghf.kontingente(api)
        self.assertIsNone(d['kosten_netto_eur'])
        self.assertGreater(d['gesamt_bytes'], 0)

    def test_cleanup_only_touches_archived_repos(self):
        geloescht = []
        bericht = ghf.speicher_raeumen(self.fake_api, geloescht.append)
        self.assertEqual(geloescht, ['repos/ich/alt/actions/artifacts/1'])
        self.assertEqual(bericht, [{'repo': 'ich/alt', 'artefakte': 1, 'bytes': 400 * 2**20}])


class MailTest(unittest.TestCase):
    def test_only_account_mails_from_github_not_repo_notifications(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / 'Envelope Index'
            con = sqlite3.connect(db)
            con.executescript('CREATE TABLE messages(ROWID INTEGER PRIMARY KEY, sender, subject, date_received);'
                              'CREATE TABLE addresses(ROWID INTEGER PRIMARY KEY, address);'
                              'CREATE TABLE subjects(ROWID INTEGER PRIMARY KEY, subject);'
                              "INSERT INTO addresses VALUES (1,'noreply@github.com'),(2,'notifications@github.com'),(3,'x@fremd.de');"
                              "INSERT INTO subjects VALUES (1,'Storage 90%'),(2,'Run failed'),(3,'Werbung');"
                              "INSERT INTO messages VALUES (1,1,1,strftime('%s','now')),(2,2,2,strftime('%s','now')),"
                              "(3,3,3,strftime('%s','now')),(4,1,1,strftime('%s','now','-10 days'));")
            con.commit()
            con.close()
            zeilen = ghf.konto_mails(3, db)
        self.assertEqual([(a, s) for _, a, s in zeilen], [('noreply@github.com', 'Storage 90%')])


if __name__ == '__main__':
    unittest.main()

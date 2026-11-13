import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "werkzeuge"))
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import wiki_pflege as wiki
import notebook_register as notebook


class PflegeTests(unittest.TestCase):
    def setUp(self):
        self.setting = patch.object(notebook, 'NOTEBOOK', 'erfundenes-notebook')
        self.setting.start()
        self.addCleanup(self.setting.stop)

    def test_no_missing_text_between_chunks(self):
        text = 'Äpfel.\n' * 777
        self.assertEqual(''.join(wiki.chunks(text, 101)), text)

    def test_invented_quote_rejected(self):
        result = {'thema': 'Test', 'aussagen': [{'aussage': 'falsch', 'zitat': 'erfunden'}], 'offen': [], 'nutzung': 'Test'}
        with self.assertRaises(ValueError):
            wiki.validate(result, 'Echte Quelle')

    def test_link_does_not_become_knowledge(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            p = root / 'Notebook.md'
            p.write_text('https://example.org/notebook\n')
            config = json.loads(wiki.CONFIG.read_text())
            with patch.object(wiki, 'STATE', root / 'state'), patch.object(wiki, 'infer') as infer:
                item = wiki.process(p, config)
            self.assertEqual(item['status'], 'zugriff_noetig')
            infer.assert_not_called()

    def test_extraction_reuse_without_model_call(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            p = root / 'Notiz.md'
            p.write_text('Originalinhalt vollständig.')
            config = json.loads(wiki.CONFIG.read_text())
            with patch.object(wiki, 'STATE', root / 'state'), patch.object(wiki, 'infer') as infer:
                item = wiki.process(p, config, extract_only=True)
            self.assertEqual(item['status'], 'extrahiert')
            self.assertEqual((Path(item['material']) / 'original.md').read_text(), p.read_text())
            infer.assert_not_called()

    def test_no_second_model_call_for_same_version(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            p = root / 'Notiz.md'
            p.write_text('Der Test ist lokal.')
            config = json.loads(wiki.CONFIG.read_text())
            result = {'thema': 'Test', 'aussagen': [{'aussage': 'Lokal', 'zitat': 'Der Test ist lokal.'}], 'offen': [], 'nutzung': 'Test'}
            with patch.object(wiki, 'STATE', root / 'state'), patch.object(wiki, 'infer', return_value=result) as infer:
                first = wiki.process(p, config)
                second = wiki.process(p, config)
            self.assertEqual(first['status'], 'entwurf')
            self.assertEqual(second['status'], 'entwurf')
            self.assertEqual(infer.call_count, 1)

    def test_cloud_disabled_without_quota(self):
        with self.assertRaisesRegex(ValueError, 'Cloudaufrufe ausgeschaltet'):
            wiki.infer('Test', {'provider': 'anthropic', 'cloud_enabled': False})

    def test_notebook_unchanged_and_incomplete(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(notebook, 'STATE', Path(folder)):
            data = {'notebook_id': notebook.NOTEBOOK, 'complete': True, 'items': [{'id': '1', 'title': 'Quelle', 'kind': 'video', 'version': 'v1'}]}
            self.assertEqual(notebook.reconcile(data)['neu'], ['1'])
            self.assertEqual(notebook.reconcile(data)['unveraendert'], ['1'])
            data['items'][0]['version'] = 'v2'
            self.assertEqual(notebook.reconcile(data)['geaendert'], ['1'])
            prior = (Path(folder) / 'inventory.json').read_bytes()
            data['complete'] = False
            with self.assertRaises(ValueError):
                notebook.reconcile(data)
            self.assertEqual((Path(folder) / 'inventory.json').read_bytes(), prior)

    def test_notebook_without_version_is_not_claimed_unchanged(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(notebook, 'STATE', Path(folder)):
            data = {'notebook_id': notebook.NOTEBOOK, 'complete': True, 'items': [{'id': '1', 'title': 'Quelle', 'kind': 'video'}]}
            notebook.reconcile(data)
            self.assertEqual(notebook.reconcile(data)['version_unbekannt'], ['1'])


class TranscriptionCacheTests(unittest.TestCase):
    def test_cloud_transcription_is_not_implicit(self):
        with patch.object(wiki, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'Cloudtranskription ausgeschaltet'):
                wiki.transcribe(Path('synthetic.wav'), Path('.'), {
                    'transkription': True, 'stt_provider': 'voxtral', 'cloud_enabled': False})
            run.assert_not_called()

    def setUp(self):
        self.config = {'stt_provider': 'parakeet_lokal', 'stt_sprache': 'auto',
                       'transkription': True, 'max_audio_minuten': 60}
        self.info = {'model': 'synthetic-model', 'backend': 'synthetic-cpu',
                     'revision': 'revision-one', 'language_mode': 'auto'}

    def test_cache_separates_mode_model_backend_revision(self):
        with patch.object(wiki, 'stt_identity', return_value=self.info):
            original = wiki.extraction_key('digest', '.wav', self.config)
        for key, value in [('language_mode', 'de'), ('model', 'other-model'),
                           ('backend', 'other-cpu'), ('revision', 'revision-two')]:
            with self.subTest(key=key), patch.object(wiki, 'stt_identity', return_value={**self.info, key: value}):
                self.assertNotEqual(original, wiki.extraction_key('digest', '.wav', self.config))
        legacy = wiki.sha(b'digest|.wav|parakeet_lokal')
        self.assertNotEqual(original, legacy)

    def test_text_cache_keeps_old_identity_and_needs_no_stt(self):
        with patch.object(wiki, 'stt_identity', side_effect=AssertionError('No STT for text')):
            self.assertEqual(wiki.extraction_key('digest', '.md', self.config),
                             wiki.sha(b'digest|.md|parakeet_lokal'))

    def test_prior_status_cannot_hide_changed_backend_or_legacy_cache(self):
        path = Path('synthetic.wav')
        with patch.object(wiki, 'stt_identity', return_value=self.info):
            prior = {'sha256': 'digest', 'extraktion_key': wiki.extraction_key('digest', '.wav', self.config)}
            self.assertTrue(wiki.cached_version_matches(path, 'digest', self.config, prior))
            self.assertFalse(wiki.cached_version_matches(path, 'digest', self.config, {'sha256': 'digest'}))
        with patch.object(wiki, 'stt_identity', return_value={**self.info, 'revision': 'new'}):
            self.assertFalse(wiki.cached_version_matches(path, 'digest', self.config, prior))

    def test_daily_status_reprocesses_same_audio_after_model_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            vault, state = root / 'vault', root / 'state'
            (vault / 'sources').mkdir(parents=True)
            state.mkdir()
            audio = vault / 'sources/synthetic.wav'
            audio.write_bytes(b'synthetic bytes')
            config = json.loads(wiki.CONFIG.read_text())
            config_file = root / 'config.json'
            config_file.write_text(json.dumps(config))
            digest = wiki.sha(audio.read_bytes())
            with patch.object(wiki, 'stt_identity', return_value=self.info):
                prior = {'sha256': digest, 'status': 'extrahiert', 'modell': config['model'],
                         'extraktion_key': wiki.extraction_key(digest, '.wav', config)}
            (state / 'status.json').write_text(json.dumps({'items': {audio.name: prior}}))
            with patch.object(wiki, 'STATE', state), patch.object(wiki, 'VAULT', vault), \
                 patch.object(wiki, 'CONFIG', config_file), \
                 patch.object(wiki, 'stt_identity', return_value={**self.info, 'revision': 'new'}), \
                 patch.object(wiki, 'process', return_value={'status': 'extrahiert'}) as process, \
                 patch.object(wiki, 'report'), patch('sys.argv', ['wiki_pflege.py', '--extract-only']):
                wiki.main()
            process.assert_called_once_with(audio, config, prior, True)

    def test_all_language_modes_forwarded_to_metadata_and_decode(self):
        for language in ('auto', 'de', 'en'):
            info = {**self.info, 'language_mode': language}
            config = {**self.config, 'stt_sprache': language}
            with self.subTest(language=language), tempfile.TemporaryDirectory() as folder:
                work = Path(folder)
                def run(args, *unused):
                    if '--modellinfo' in args:
                        self.assertEqual(args[-2:], ['--sprache', language])
                        return json.dumps(info)
                    if 'ffprobe' in args[0]:
                        return '1.0'
                    self.assertEqual(args[-2:], ['--sprache', language])
                    (work / 'transkript.json').write_text(json.dumps({**info, 'offline': True,
                        'duration': 1, 'decoded_until': 1, 'text': 'Synthetic text',
                        'segments': [{'start': 0, 'end': 1, 'text': 'Synthetic text'}]}))
                    return ''
                with patch.object(wiki, 'run', side_effect=run):
                    self.assertEqual(wiki.stt_identity(config), info)
                    self.assertEqual(wiki.transcribe(Path('synthetic.wav'), work, config), 'Synthetic text')

    def test_stale_local_transcript_rejected_without_cloud(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            (work / 'transkript.json').write_text(json.dumps({**self.info, 'language_mode': 'de'}))
            with patch.object(wiki, 'run', return_value='1.0') as run, patch.object(wiki, 'stt_identity', return_value=self.info):
                with self.assertRaisesRegex(ValueError, 'anderen Sprachmodus/Modell'):
                    wiki.transcribe(Path('synthetic.wav'), work, self.config)
            self.assertEqual(run.call_count, 1)  # only ffprobe, no cloud or decode

    def test_missing_metadata_is_error_without_transcription(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'synthetic.wav'
            path.write_bytes(b'synthetic bytes')
            config = {**self.config, 'provider': 'ollama', 'model': 'synthetic'}
            with patch.object(wiki, 'stt_identity', side_effect=RuntimeError('Missing API')), patch.object(wiki, 'extract') as extract:
                result = wiki.process(path, config, extract_only=True)
            self.assertEqual(result['status'], 'fehler')
            extract.assert_not_called()


if __name__ == '__main__':
    unittest.main()

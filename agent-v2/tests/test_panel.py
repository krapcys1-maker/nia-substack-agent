"""Real preset persistence, HTTP boundary and worker integration in disposable copies."""
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'narzedzia'))
from panel_core import Panel, PanelError, file_lock, atomic_json, preset
from panel import make_server


class PanelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'presety/hidden-bill', self.root / 'presety/hidden-bill')
        (self.root / 'agent-v2').mkdir()
        self.panel = Panel(self.root)
        self.panel.initial_env = {}
        self.panel.account({'SUBSTACK_HANDLE': 'example-publication', 'NAZWA_MARKI': 'Example publication'})
        self.stock = self.panel.revision(self.root / 'presety/hidden-bill')

    def tearDown(self):
        self.temp.cleanup()

    def payload(self, source='hidden-bill', name='my-preset'):
        value = self.panel.read(source)
        return dict(name=name, source=source, revision=value['revision'], fields=value['fields'],
                    assets=value['assets'], prompts=value['prompts'], pins=value['pins'], description='My publication')

    def test_round_trip_preserves_research_prompts_and_bundled_files(self):
        payload = self.payload()
        payload['fields']['modele.role']['note'] = 'deepseek-v4-flash'
        result = self.panel.save(payload)['preset']
        self.assertEqual(result['models']['note'], 'deepseek-v4-flash')
        self.assertEqual(result['prompts'], payload['prompts'])
        self.assertEqual(result['assets'], payload['assets'])
        self.assertEqual(result['fields']['zrodla.kanaly_rss'], payload['fields']['zrodla.kanaly_rss'])
        self.assertEqual(self.stock, self.panel.revision(self.root / 'presety/hidden-bill'))
        self.assertEqual(result['fields']['konto.uchwyt'], 'your-handle')

    def test_validation_no_write_and_invalid_edit_no_damage(self):
        self.assertTrue(self.panel.save(self.payload(), True)['valid'])
        self.assertFalse((self.root / 'presety/my-preset').exists())
        self.panel.save(self.payload())
        original = self.panel.read('my-preset')['revision']
        bad = self.payload('my-preset')
        bad['fields']['wolumeny.notki_dziennie'] = -1
        with self.assertRaises((ValueError, preset.BladPresetu)):
            self.panel.save(bad)
        self.assertEqual(original, self.panel.read('my-preset')['revision'])

    def test_conflicts_public_names_and_traversal(self):
        for name in ('hidden-bill', '../escape', 'a/b', 'C:\\escape'):
            with self.assertRaises(PanelError):
                self.panel.save(self.payload(name=name))
        payload = self.payload()
        payload['revision'] = 'old'
        with self.assertRaisesRegex(PanelError, 'Reload'):
            self.panel.save(payload)

    def test_active_edit_keeps_memory_and_updates_activation(self):
        self.panel.save(self.payload())
        self.panel.activate('my-preset', 'example')
        data = self.root / 'agent-v2/instancje/example'
        (data / 'memory.txt').write_text('existing memory')
        before = preset.czytaj_wskaznik(self.panel.agent)
        payload = self.payload('my-preset')
        payload['fields']['modele.role']['note'] = 'deepseek-v4-flash'
        result = self.panel.save(payload)
        self.assertTrue(result['reactivated'])
        self.assertTrue((self.root / result['backup'] / 'preset.toml').exists())
        self.assertEqual((data / 'memory.txt').read_text(), 'existing memory')
        self.assertNotEqual(before['odcisk'], preset.czytaj_wskaznik(self.panel.agent)['odcisk'])
        with self.assertRaises(PanelError):
            self.panel.account({'SUBSTACK_HANDLE': 'another-account'})

    def test_running_instance_blocks_edits(self):
        self.panel.save(self.payload())
        self.panel.activate('my-preset', 'example')
        with file_lock(self.panel.active().katalog_danych / 'agent.lock'):
            with self.assertRaises(PanelError):
                self.panel.save(self.payload('my-preset'))

    def test_failed_activation_rolls_back(self):
        self.panel.save(self.payload())
        self.panel.activate('my-preset', 'example')
        before = self.panel.read('my-preset')['revision']
        pointer = preset.czytaj_wskaznik(self.panel.agent)
        with patch.object(preset, 'podlacz', side_effect=OSError('disk failed')):
            with self.assertRaises(OSError):
                self.panel.save(self.payload('my-preset'))
        self.assertEqual(self.panel.read('my-preset')['revision'], before)
        self.assertEqual(preset.czytaj_wskaznik(self.panel.agent), pointer)

    def test_restart_recovers_interrupted_directory_swap(self):
        self.panel.save(self.payload())
        before = self.panel.read('my-preset')['revision']
        target = self.root / 'presety/my-preset'
        backup = self.panel.state / 'backups/interrupted/my-preset'
        backup.parent.mkdir(parents=True)
        atomic_json(self.panel.state / 'preset-transaction.json', dict(name='my-preset',
                    backup=str(backup.relative_to(self.root)), existed=True, pointer=None))
        os.replace(target, backup)
        restarted = Panel(self.root)
        self.assertEqual(restarted.read('my-preset')['revision'], before)

    def test_keys_remain_local_and_blank_preserves_existing(self):
        value = 'dummy-credential-for-panel-unit-test'
        self.panel.account({'DEEPSEEK_API_KEY': value})
        self.panel.account({'DEEPSEEK_API_KEY': ''})
        self.assertEqual(self.panel.env()['DEEPSEEK_API_KEY'], value)
        status = self.panel.status()
        self.assertTrue(status['keys']['DEEPSEEK_API_KEY'])
        self.assertNotIn(value, json.dumps(status))

    def test_enabled_images_require_key_before_paid_worker_starts(self):
        self.panel.account({'DEEPSEEK_API_KEY': 'dummy-deepseek-test', 'ANTHROPIC_API_KEY': 'dummy-anthropic-test'})
        payload = self.payload()
        payload['fields']['modele.obraz'] = 'gpt-image-1.5'
        self.panel.save(payload)
        self.panel.activate('my-preset', 'example')
        with patch('panel_core.subprocess.Popen') as spawn:
            with self.assertRaisesRegex(PanelError, 'OPENAI_API_KEY'):
                self.panel.start('article-draft')
        spawn.assert_not_called()

    def test_legacy_private_account_survives_editor_save(self):
        self.panel.save(self.payload())
        path = self.root / 'presety/my-preset/preset.toml'
        path.write_text(path.read_text(encoding='utf-8').replace('your-handle', 'legacy-profile')
                        .replace('Your Publication', 'Legacy publication'), encoding='utf-8')
        (self.panel.agent / '.env').unlink()
        self.panel.activate('my-preset', 'legacy')
        self.panel.save(self.payload('my-preset'))
        self.assertEqual(self.panel.read('my-preset')['fields']['konto.uchwyt'], 'legacy-profile')
        self.assertEqual(self.panel.status()['account']['SUBSTACK_HANDLE'], 'legacy-profile')

    def test_custom_preset_can_use_empty_source_filters_and_no_corpus(self):
        payload = self.payload()
        payload.pop('source')
        payload.pop('revision')
        payload['fields']['zrodla.blokowane_hosty'] = []
        payload['fields']['zrodla.domeny_preferowane'] = []
        payload['fields']['zrodla.kanaly_rss'] = {}
        payload['fields']['zrodla.kanaly_youtube'] = {}
        payload['assets']['corpus'] = ''
        payload['prompts'] = {}
        result = self.panel.save(payload)['preset']
        self.assertEqual(result['fields']['zrodla.blokowane_hosty'], [])
        self.assertEqual(result['fields']['zrodla.kanaly_rss'], {})
        self.assertEqual(result['assets']['corpus'], '')
        self.assertFalse(any(result['prompts'].values()))

    def test_job_result_and_redacted_log_survive_panel_restart(self):
        job_id = 'a' * 32
        secret = 'dummy-credential-for-panel-restart-test'
        self.panel.account({'DEEPSEEK_API_KEY': secret})
        atomic_json(self.panel.state / 'job.json', {'id': job_id, 'action': 'dry', 'started': 0})
        (self.panel.state / (job_id + '.log')).write_text('PASS: ' + secret)
        atomic_json(self.panel.state / (job_id + '.result.json'), {'exit_code': 0})
        other = Panel(self.root)
        other.initial_env = {}
        result = other.job_status()
        self.assertFalse(result['running'])
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['log'], 'PASS: [redacted]')

    def test_http_token_host_origin_and_no_arbitrary_files(self):
        server, _, token = make_server(0, self.panel)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = 'http://127.0.0.1:%s' % server.server_port
        def request(path, headers=None):
            return urlopen(Request(url + path, headers=headers or {}), timeout=5)
        try:
            with request('/') as result:
                self.assertIn(token.encode(), result.read())
            with request('/api/status', {'X-NIA-Token': token}) as result:
                self.assertEqual(json.load(result)['account']['NAZWA_MARKI'], 'Example publication')
            for path, headers, code in [('/api/status', {}, 403),
                ('/api/status', {'X-NIA-Token': token, 'Origin': 'https://example.com'}, 403),
                ('/', {'Host': 'example.com'}, 403), ('/agent-v2/.env', {}, 404)]:
                with self.assertRaises(HTTPError) as error:
                    request(path, headers)
                self.assertEqual(error.exception.code, code)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()

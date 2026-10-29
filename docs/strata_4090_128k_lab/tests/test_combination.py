import copy
from contextlib import ExitStack
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab.core import hash_obj, set_flag


spec = importlib.util.spec_from_file_location(
    'run_combo', Path(__file__).resolve().parents[1] / 'tools/combination/run_combo.py')
combo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(combo)


class CombinationTests(unittest.TestCase):
    def configurations(self):
        base = {'args': ['--kv-resident', '0'], 'user_args': ['--kv-resident', '0'],
                'env': dict(combo.FROZEN_ENV), 'exe': '/lab/strata', 'api_key': 'a', 'log': '/lab/base.log'}
        cfg = copy.deepcopy(base)
        for key in ('args', 'user_args'):
            cfg[key] = set_flag(cfg[key], '--kv-resident', '20480')
        cfg.update(api_key='b', log='/lab/cfg.log')
        return base, cfg

    def test_only_kvres_and_owned_ephemeral_paths_may_differ(self):
        base, cfg = self.configurations()
        combo.assert_same_except_kvres(base, cfg)
        cfg['env']['STRATA_PREFILL_AUTO_MAX'] = '8192'
        with self.assertRaisesRegex(RuntimeError, 'COMBINATION_ENV_MISMATCH'):
            combo.assert_same_except_kvres(base, cfg)

    def test_different_executable_cannot_enter_comparison(self):
        base, cfg = self.configurations()
        cfg['exe'] = '/other/strata'
        with self.assertRaisesRegex(RuntimeError, 'ARMS_DIFFER_BEYOND_KVRES'):
            combo.assert_same_except_kvres(base, cfg)

    def test_wrong_base_kvres_value_is_rejected(self):
        base, cfg = self.configurations()
        base['args'] = ['--kv-resident', '20480']
        with self.assertRaisesRegex(RuntimeError, 'KVRES_ARM_VALUE_MISMATCH'):
            combo.assert_same_except_kvres(base, cfg)

    def test_production_drift_is_detected_by_content_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'production.json'
            file.write_text('{}')
            config = {'protected_files': [str(file)]}
            before = combo.protected_hashes(config)
            file.write_text('{"modified": true}')
            with self.assertRaisesRegex(RuntimeError, 'PROTECTED_PRODUCTION_FILES_CHANGED'):
                combo.assert_protected(config, before)

    def test_active_production_is_not_stopped_or_reused(self):
        class Result:
            stdout = 'ActiveState=active\nSubState=running\nUnitFileState=enabled\n'
        with patch.object(combo.subprocess, 'run', return_value=Result()) as call:
            with self.assertRaisesRegex(RuntimeError, 'PRODUCTION_NOT_INACTIVE'):
                combo.assert_service_inactive()
        self.assertEqual(call.call_args.args[0][:2], ['systemctl', 'show'])
        self.assertEqual(call.call_count, 1)

    def test_restore_must_belong_to_this_request_and_be_long_enough(self):
        case = {'expected_restore': True}
        self.assertFalse(combo.restore_evidence(case, '')['pass'])
        self.assertFalse(combo.restore_evidence(case, 'conversation cache: restored 30006 tokens')['pass'])
        self.assertTrue(combo.restore_evidence(case, 'conversation cache: restored 65500 tokens (live)')['pass'])
        self.assertTrue(combo.restore_evidence({}, '')['pass'])

    def test_missing_or_mutated_frozen_request_hash_is_not_accepted(self):
        request = {'messages': [{'role': 'user', 'content': 'frozen'}], 'max_tokens': 32}
        case = {'id': 'test', 'group': 'retrieval', 'counted_prompt_tokens': 100, 'body': request,
                'request_sha256': hash_obj(request)}
        original = copy.deepcopy(case)
        self.assertEqual(combo.descriptors([case])[0]['context_bucket'], '4096')
        case['body']['messages'][0]['content'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'request hash mismatch'):
            combo.descriptors([case])
        original['counted_prompt_tokens'] = 130000
        with self.assertRaisesRegex(ValueError, 'CONTEXT_LIMIT'):
            combo.descriptors([original])

    def test_base_override_is_in_common_not_ignored_base_section(self):
        ready = combo.ready_spec()
        self.assertEqual(ready['common']['args']['--kv-resident'], '0')
        self.assertEqual(ready['cfg']['args']['--kv-resident'], '20480')
        self.assertNotIn('base', ready)

    def test_startup_receipts_require_python_flags_and_kv_mechanism(self):
        with tempfile.TemporaryDirectory() as directory:
            class Server:
                folder = Path(directory)
            log = Server.folder / 'server.log'
            log.write_text('LAB_PR_1536 enabled=1\nLAB_CFG_PT preserve_thinking default=0\n'
                           'prompt chunk auto: 16384 tokens\nexpert cache 10290 slots\n')
            with self.assertRaisesRegex(RuntimeError, 'STARTUP_ACTIVATION_NOT_CONFIRMED'):
                combo.validate_startup(Server(), 'cfg')
            with log.open('a') as output:
                output.write('KV streaming: 20480 of 131072 cells per QSA layer in VRAM\n')
            self.assertTrue(combo.validate_startup(Server(), 'cfg')['confirmed'])

    def test_startup_keyboard_interrupt_still_stops_owned_process_and_releases_gpu(self):
        events = []
        class Server:
            def __init__(self, *args): pass
            def __enter__(self):
                events.append('start')
                raise KeyboardInterrupt()
            def __exit__(self, *args): events.append('stop')
        with patch.object(combo, 'OwnedServer', Server), \
             patch.object(combo, 'wait_released', side_effect=lambda c: events.append('release')):
            with self.assertRaises(KeyboardInterrupt):
                with combo.combination_server({}, Path('/tree'), 'base', {}, Path('/out')):
                    self.fail('startup must not complete')
        self.assertEqual(events, ['start', 'stop', 'release'])

    def test_stopped_engine_memory_sample_preserves_failure_evidence(self):
        class Process:
            pid = 123
        class Server:
            process = Process()
            engine_audit = [{'pid': 124}]
        def read(path, *args, **kwargs):
            if str(path) == '/proc/meminfo':
                return 'MemAvailable: 5000 kB\nSwapFree: 900 kB\n'
            raise FileNotFoundError('process exited')
        with patch.object(Path, 'read_text', read):
            sample = combo.resource_sample(Server())
        self.assertEqual(sample['MemAvailable_kib'], 5000)
        self.assertIn('error', sample['processes']['124'])

    def mocked_run(self, root, response):
        tree = root / 'tree'
        tree.mkdir()
        production = root / 'production.json'
        production.write_text('{}')
        frozen = root / 'frozen.json'
        frozen.write_text(json.dumps({'cwd': str(tree), 'env': dict(combo.FROZEN_ENV), 'args': []}))
        config = {'deployed_repo': str(tree), 'deployed_config': str(frozen),
                  'workspace': str(root / 'workspace'), 'port': 18089,
                  'max_context': 131072, 'min_available_mib': 4096,
                  'conversation_cache_mib': 6144, 'gguf': '/fake/model',
                  'template': '/fake/template', 'protected_files': [str(production)]}
        request = {'messages': [{'role': 'user', 'content': 'Reply only OK.'}], 'max_tokens': 32}
        cases = [{'id': 'quality', 'group': 'quality', 'kind': 'exact', 'expected': 'OK',
                  'counted_prompt_tokens': 100, 'body': request}]
        corpus = root / 'corpus.json'
        corpus.write_text(json.dumps({'max_context': 131072, 'cases': cases,
                                      'corpus_sha256': hash_obj(cases)}))
        events = []
        class Server:
            abort_reason = None
            def __init__(self, c, tree, arm, ready, folder):
                self.folder, self.arm = folder, arm
                (folder / 'engine.log').write_text('')
            def __enter__(self):
                events.append(('start', self.arm))
                return self
            def __exit__(self, *args): events.append(('stop', self.arm))
        out = root / 'result'
        stack = ExitStack()
        for name, value in (
                ('validate_tree', {'source_sha': 'same-source', 'exe_sha256': 'same-binary'}),
                ('assert_service_inactive', {'ActiveState': 'inactive'}),
                ('verify_assets', {}), ('wait_cool', []), ('validate_startup', {}),
                ('history_counter_probe', {}), ('resource_sample', {}), ('audited_chat', response)):
            stack.enter_context(patch.object(combo, name, return_value=value))
        stack.enter_context(patch('lab.assets.verify', return_value={}))
        stack.enter_context(patch.object(combo, 'StrataCounter', return_value=lambda request: 100))
        stack.enter_context(patch.object(combo, 'validate_counter'))
        stack.enter_context(patch.object(combo, 'wait_released'))
        stack.enter_context(patch.object(combo, 'OwnedServer', Server))
        return stack, config, tree, corpus, out, events

    def test_complete_mock_replay_preserves_each_metric_and_balanced_order(self):
        response = {'text': 'OK', 'reasoning': '', 'tools': [], 'error': None,
                    'finish_reason': 'stop', 'usage': {'prompt_tokens': 100, 'completion_tokens': 1},
                    'total_s': 1, 'first_s': 0.2, 'timings': {'predicted_ms': 800}}
        with tempfile.TemporaryDirectory() as directory:
            stack, config, tree, corpus, out, events = self.mocked_run(Path(directory), response)
            with stack, patch('builtins.print'):
                result = combo.run_combination(config, tree, corpus, out, 2, True)
            self.assertEqual(result['state'], 'COMPLETE')
            self.assertEqual([arm for event, arm in events if event == 'start'], ['base', 'cfg', 'cfg', 'base'])
            rows = [json.loads(line) for line in (out / 'requests.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(row['request']['messages'][0]['content'] == 'Reply only OK.' for row in rows))
            self.assertEqual(json.loads((out / 'COMPLETION.json').read_text())['final_audit'], 'PASS')
            for metric in ('decode_ms', 'wall_s', 'ttft_s'):
                self.assertTrue((out / 'statistics' / metric / 'summary.json').exists())

    def test_failed_request_is_saved_before_stopping_and_failure_receipt_remains(self):
        response = {'error': 'THERMAL_GUARD', 'text': '', 'tools': [], 'usage': {}, 'total_s': 1}
        with tempfile.TemporaryDirectory() as directory:
            stack, config, tree, corpus, out, events = self.mocked_run(Path(directory), response)
            with stack, patch('builtins.print'):
                with self.assertRaisesRegex(RuntimeError, 'REQUEST_OR_RESOURCE_FAILURE'):
                    combo.run_combination(config, tree, corpus, out, 2, True)
            rows = [json.loads(line) for line in (out / 'requests.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['response']['error'], 'THERMAL_GUARD')
            self.assertTrue((out / 'FAILURE.json').exists())
            self.assertFalse((out / 'COMPLETION.json').exists())
            self.assertEqual(events, [('start', 'base'), ('stop', 'base')])


if __name__ == '__main__':
    unittest.main()

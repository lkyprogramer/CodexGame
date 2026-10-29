import contextlib
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from lab.core import hash_obj

MODULE_PATH = Path(__file__).resolve().parents[1] / 'tools/combination/run_restore.py'
spec = importlib.util.spec_from_file_location('combination_restore_tested', MODULE_PATH)
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


class CombinationRestoreTests(unittest.TestCase):
    def cases(self):
        cases = []
        for target in restore.TARGETS:
            for stage, prefix in (('prime', 'park-prime-'), ('side', 'park-side-'),
                                  ('restore', 'restore-'), ('sampled', 'sampled-retrieval-')):
                body = {'messages': [{'role': 'user', 'content': f'{stage} {target}'}],
                        'max_tokens': 64, 'temperature': 1 if stage == 'sampled' else 0}
                cases.append({'id': prefix + str(target), 'kind': 'exact', 'expected': 'GOLD',
                              'group': stage, 'body': body, 'request_sha256': hash_obj(body)})
        return {'max_context': 131072, 'cases': cases, 'corpus_sha256': hash_obj(cases)}

    def test_wrong_actual_prime_answer_is_retained_instead_of_gold(self):
        prime = {'messages': [{'role': 'user', 'content': 'document'}]}
        response = {'text': 'WRONG ACTUAL ANSWER', 'reasoning': 'literal private reasoning'}
        history = restore.actual_history(prime, response)
        frozen = {'body': {'messages': [{'role': 'assistant', 'content': 'GOLD'},
                                         {'role': 'user', 'content': 'next query'}],
                           'max_tokens': 64, 'temperature': 1}}
        followup = restore.followup_request(history, frozen)
        self.assertEqual(followup['messages'][-2], {'role': 'assistant', 'content': 'WRONG ACTUAL ANSWER',
                                                   'reasoning_content': 'literal private reasoning'})
        self.assertEqual(followup['messages'][-1]['content'], 'next query')
        self.assertNotIn('GOLD', json.dumps(followup))
        self.assertEqual(prime['messages'], [{'role': 'user', 'content': 'document'}])
        self.assertEqual(followup['temperature'], 1)

    def test_frozen_source_body_mutation_cannot_be_silently_used(self):
        corpus = self.cases()
        self.assertEqual(set(restore.select_cases(corpus)), {69632, 102400})
        corpus['cases'][0]['body']['messages'][0]['content'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'CORPUS_IDENTITY_MISMATCH'):
            restore.select_cases(corpus)
        corpus['corpus_sha256'] = hash_obj(corpus['cases'])
        with self.assertRaisesRegex(ValueError, 'FROZEN_REQUEST_HASH_MISMATCH'):
            restore.select_cases(corpus)

    def test_actual_empty_answer_does_not_get_replaced_or_omitted(self):
        history = restore.actual_history({'messages': []}, {'text': '', 'reasoning': ''})
        self.assertEqual(history, [{'role': 'assistant', 'content': '', 'reasoning_content': ''}])

    def test_one_arm_keeps_wrong_prime_and_missing_restore_but_runs_all_stages(self):
        requests = []
        selected = restore.select_cases(self.cases())
        @contextlib.contextmanager
        def server(*args):
            yield SimpleNamespace(folder=args[-1], abort_reason=None)
        def stage(c, counter, server, folder, arm, target, stage, case, request):
            requests.append((target, stage, copy.deepcopy(request)))
            return {'stage': stage, 'score': {'pass': stage != 'prime'},
                    'restore_evidence': {'pass': stage != 'restore', 'restored_tokens': []},
                    'response': {'text': 'WRONG-PRIME' if stage == 'prime' else 'ACTUAL-' + stage,
                                 'reasoning': 'THINK-' + stage}}
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(restore.combo, 'wait_cool', return_value=[]), \
             patch.object(restore.combo, 'combination_server', side_effect=server), \
             patch.object(restore.combo, 'validate_startup', return_value={}), \
             patch.object(restore.combo, 'history_counter_probe'), \
             patch.object(restore, 'validate_counter'), \
             patch.object(restore, 'execute_stage', side_effect=stage):
            summary = restore.one_arm({}, Path('/tree'), 'base', {}, Path(directory) / 'run',
                                      selected, lambda body: 100)
        self.assertEqual(len(requests), 8)
        self.assertFalse(summary['lifecycle_pass'])
        self.assertEqual(summary['answer_failures'], 2)
        self.assertEqual(summary['restore_failures'], 2)
        for target in restore.TARGETS:
            returned = next(r for t, s, r in requests if t == target and s == 'restore')
            sampled = next(r for t, s, r in requests if t == target and s == 'sampled')
            self.assertEqual(returned['messages'][-2]['content'], 'WRONG-PRIME')
            self.assertEqual(sampled['messages'][-2]['content'], 'ACTUAL-restore')
            self.assertEqual(sampled['temperature'], 1)

    def execute_fixture(self, root, response, log_delta=''):
        log = root / 'engine.log'
        log.write_text('old log before this request\n')
        server = SimpleNamespace(folder=root, abort_reason=None)
        case = self.cases()['cases'][0]
        def chat(*args):
            with log.open('a') as output:
                output.write(log_delta)
            return response
        return server, case, chat

    def test_infrastructure_failure_raw_response_is_saved_before_raising(self):
        response = {'text': '', 'reasoning': '', 'tools': [], 'error': 'THERMAL_GUARD',
                    'usage': {}, 'total_s': 1}
        config = {'max_context': 131072, 'safety_tokens': 4096}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server, case, chat = self.execute_fixture(root, response)
            with patch.object(restore.combo, 'resource_sample', return_value={}), \
                 patch.object(restore, 'audited_chat', side_effect=chat), patch('builtins.print'):
                with self.assertRaisesRegex(RuntimeError, 'RESTORE_INFRASTRUCTURE'):
                    restore.execute_stage(config, lambda body: 100, server, root, 'base', 69632,
                                          'prime', case, case['body'])
            rows = [json.loads(x) for x in (root / 'requests.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['response']['error'], 'THERMAL_GUARD')
            self.assertEqual(json.loads((root / '69632-prime.response.json').read_text()), response)

    def test_restore_evidence_only_reads_current_request_log_delta(self):
        response = {'text': 'GOLD', 'reasoning': '', 'tools': [], 'error': None, 'finish_reason': 'stop',
                    'usage': {'prompt_tokens': 100, 'completion_tokens': 1}, 'total_s': 1}
        config = {'max_context': 131072, 'safety_tokens': 4096}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server, case, chat = self.execute_fixture(root, response, 'no restoration in this request\n')
            (root / 'engine.log').write_text('conversation cache: restored 68000 tokens (old)\n')
            with patch.object(restore.combo, 'resource_sample', return_value={}), \
                 patch.object(restore, 'audited_chat', side_effect=chat), patch('builtins.print'):
                row = restore.execute_stage(config, lambda body: 100, server, root, 'base', 69632,
                                            'restore', case, case['body'])
            self.assertFalse(row['restore_evidence']['pass'])
            self.assertEqual(row['restore_evidence']['restored_tokens'], [])
            self.assertTrue(row['score']['pass'])

    def test_unauthorized_tool_payload_is_retained_and_stops_execution(self):
        response = {'text': '', 'reasoning': '', 'tools': [{'function': {'name': 'shell', 'arguments': '{}'}}],
                    'error': None, 'finish_reason': 'tool_calls',
                    'usage': {'prompt_tokens': 100, 'completion_tokens': 1}, 'total_s': 1}
        config = {'max_context': 131072, 'safety_tokens': 4096}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server, case, chat = self.execute_fixture(root, response)
            with patch.object(restore.combo, 'resource_sample', return_value={}), \
                 patch.object(restore, 'audited_chat', side_effect=chat), patch('builtins.print'):
                with self.assertRaisesRegex(RuntimeError, 'RESTORE_UNAUTHORIZED_TOOL_OUTPUT'):
                    restore.execute_stage(config, lambda body: 100, server, root, 'base', 69632,
                                          'prime', case, case['body'])
            row = json.loads((root / 'requests.jsonl').read_text())
            self.assertEqual(row['response']['tools'][0]['function']['name'], 'shell')
            self.assertFalse(row['score']['pass'])

    def test_valid_lifecycle_failures_do_not_skip_the_other_arm(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = (root / 'tree').resolve()
            corpus = root / 'corpus.json'
            corpus.write_text(json.dumps(self.cases()))
            config = {'port': 18089, 'max_context': 131072, 'safety_tokens': 4096,
                      'min_available_mib': 4096, 'deployed_repo': str(tree),
                      'workspace': str(root / 'workspace'), 'gguf': 'unused', 'template': 'unused'}
            def failed_arm(c, tree, arm, ready, folder, selected, counter):
                return {'arm': arm, 'lifecycle_pass': False, 'all_answers_pass': False,
                        'answer_failures': 2, 'restore_failures': 2}
            with patch.object(restore, 'load_config', return_value=config), \
                 patch.object(restore, 'make_run_config', return_value={'cwd': str(tree)}), \
                 patch.object(restore.combo, 'validate_tree', return_value={'source_sha': 'same', 'exe_sha256': 'same'}), \
                 patch.object(restore.combo, 'assert_same_except_kvres'), \
                 patch.object(restore.combo, 'protected_hashes', return_value={'prod': 'unchanged'}), \
                 patch.object(restore.combo, 'assert_protected', return_value={'prod': 'unchanged'}), \
                 patch.object(restore.combo, 'assert_service_inactive', return_value={'ActiveState': 'inactive'}), \
                 patch.object(restore, 'verify_assets', return_value={}), \
                 patch.object(restore, 'StrataCounter', return_value=lambda body: 100), \
                 patch.object(restore, 'gpu_lock', side_effect=lambda *a: contextlib.nullcontext()), \
                 patch.object(restore, 'evidence_lifecycle', side_effect=lambda *a: contextlib.nullcontext()), \
                 patch.object(restore, 'one_arm', side_effect=failed_arm) as arm:
                result = restore.run('config', tree, corpus, root / 'out', True)
            self.assertEqual([call.args[2] for call in arm.call_args_list], ['base', 'cfg'])
            self.assertEqual(result['state'], 'COMPLETE')
            self.assertFalse(result['lifecycle_and_answers_pass'])
            self.assertTrue((root / 'out/production-after.json').exists())


if __name__ == '__main__':
    unittest.main()

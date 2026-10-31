"""CPU checks for the bounded capture adapter; no native engine is started."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.frontier import p01b_run as adapter
from tools.frontier import warm_run as legacy
from test_frontier_warm_plan import plan_fixture


class OutcomeTests(unittest.TestCase):
    config = {'max_context': 131072, 'safety_tokens': 4096}

    def response(self, generated=941, finish='stop', reused=0):
        return {'done': True, 'finish_reason': finish,
                'usage': {'prompt_tokens': 103183, 'completion_tokens': generated,
                          'prompt_tokens_details': {'cached_tokens': reused}},
                'timings': {'prompt_n': 103183 - reused}}

    def test_natural_eos_and_length_are_complete(self):
        for generated, finish in ((941, 'stop'), (2048, 'length'), (1, 'stop')):
            self.assertEqual(adapter.request_outcome(self.response(generated, finish), 103183, self.config, 0), 'REQUEST_COMPLETE')
        self.assertEqual(adapter.request_outcome(self.response(reused=99000), 103183, self.config, 1), 'REQUEST_COMPLETE')
        self.assertEqual(legacy.request_outcome(self.response(), 103183, self.config, 0), 'INSUFFICIENT_SHORT_OUTPUT')

    def test_zero_output_and_no_reuse_stop(self):
        self.assertEqual(adapter.request_outcome(self.response(0), 103183, self.config, 0), 'INSUFFICIENT_ZERO_OUTPUT')
        self.assertEqual(adapter.request_outcome(self.response(), 103183, self.config, 1), 'INSUFFICIENT_NO_WARM_REUSE')

    def test_errors_incomplete_finish_tools_and_usage_rejected(self):
        for change in ({'error': 'guard terminated'}, {'done': False},
                       {'finish_reason': 'tool_calls'}, {'finish_reason': None}, {'tools': [{}]}):
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                adapter.request_outcome(dict(self.response(), **change), 103183, self.config, 0)
        for bad in (2049, -1, True, None):
            with self.subTest(generated=bad), self.assertRaises(RuntimeError):
                adapter.request_outcome(self.response(bad), 103183, self.config, 0)
        r = self.response(); r['timings']['prompt_n'] = 5
        with self.assertRaisesRegex(RuntimeError, 'READ_REUSE_ACCOUNTING'):
            adapter.request_outcome(r, 103183, self.config, 0)
        with self.assertRaisesRegex(RuntimeError, 'PRIME_NOT_COLD'):
            adapter.request_outcome(self.response(reused=5), 103183, self.config, 0)

    def test_plan_bridge_preserves_original_and_frozen_budgets(self):
        plan = plan_fixture()
        plan.update(planning_only=False, gpu_handoff_reference='handoff.json',
                    output_policy='natural_eos_up_to_2048', collection='host_only_bounded_trace',
                    target_output_tokens_per_request=None)
        plan['reference_evidence']['authorization.json']['scope'] = 'p01b_diagnostic'
        plan['reference_evidence']['handoff.json'] = {'status': 'AVAILABLE', 'sha256': '1' * 64}
        plan['matrix'][0]['collection'] = 'host_only_bounded_trace'
        for request in plan['matrix'][0]['requests']:
            request['target_output_tokens'] = None
        policy = legacy.load(legacy.ROOT / 'frontier/config/policy.json')
        before = copy.deepcopy(plan)
        adapter.validate_plan(plan, policy)
        self.assertEqual(plan, before)
        for change in ({'max_work_requests': 4}, {'request_deadline_seconds': 601},
                       {'output_policy': 'force_2048'}, {'target_output_tokens_per_request': 2048}):
            with self.subTest(change=change), self.assertRaises((ValueError, RuntimeError)):
                adapter.validate_plan(dict(plan, **change), policy)


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tree = self.root / 'capture-tree'; self.tree.mkdir()
        self.git('init', '-q')
        self.ports = ['port' + str(i) + '.py' for i in range(6)]
        native = 'src/program/generate.cpp'
        for name in self.ports + [native]:
            path = self.tree / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('base\n')
        self.git('add', '.')
        self.git('-c', 'user.name=CPU Test', '-c', 'user.email=cpu@example.invalid', 'commit', '-qm', 'fixture')
        for name in self.ports + [native]:
            (self.tree / name).write_text('frozen delta\n')
        self.header = 'include/strata/core/lab_p01b_trace.hpp'
        header = self.tree / self.header; header.parent.mkdir(parents=True); header.write_text('host trace\n')
        self.binary = self.tree / 'build-lab/strata'; self.binary.parent.mkdir(); self.binary.write_text('binary fixture')
        self.base_config = {'deployed_repo': str(self.root / 'base-tree'), 'workspace': str(self.root / 'base-workspace')}
        self.write('base-config.json', self.base_config)
        self.base = {'source': {'head': self.git('rev-parse', 'HEAD').strip(),
                                'port_files': {name: legacy.sha256(self.tree / name) for name in self.ports}},
                     'config': {'source_sha256': legacy.sha256(self.root / 'base-config.json'), 'env': {'STRATA_REPLY_REUSE': '1'}}}
        self.write('base-identity.json', self.base)
        names = self.ports + [native, self.header]
        files = {name: legacy.sha256(self.tree / name) for name in names}
        import hashlib
        self.build = {'source_head': self.base['source']['head'], 'source_files': files,
                      'native_files': [native, self.header], 'binary_path': str(self.binary),
                      'binary_sha256': legacy.sha256(self.binary),
                      'patch_sha256': hashlib.sha256(legacy.source_changes(self.tree)[1]).hexdigest()}
        self.gate = {'status': 'PASS', 'source_review': 'PASS', 'cpu_tests': 'PASS',
                     'clock_check': 'PASS', 'observer_cpu_cost': 'PASS',
                     'native_scope': adapter.NATIVE_SCOPE, 'graph_gap_scope': adapter.GAP_SCOPE,
                     'max_windows_per_request': 2048}
        self.write('build.json', self.build); self.write('gate.json', self.gate)
        self.identity = copy.deepcopy(self.base)
        capture = self.identity['capture'] = {'source_files': files, 'trace_prefix': str(self.root.resolve() / 'run/native-trace'),
                    'allowed_config_changes': {'deployed_repo': str(self.tree), 'workspace': str(self.root / 'build')}}
        for stem, filename in (('base_identity', 'base-identity.json'), ('base_runtime_config', 'base-config.json'),
                               ('build_receipt', 'build.json'), ('collection_gate', 'gate.json')):
            capture[stem + '_path'] = str(self.root / filename)
            capture[stem + '_sha256'] = legacy.sha256(self.root / filename)

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.tree, text=True, stderr=subprocess.DEVNULL)

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value))

    def test_frozen_capture_and_native_hashes_pass(self):
        capture, base, _, build = adapter.capture_identity(self.identity)
        adapter.verify_native(self.tree, capture, base, build)

    def test_gate_is_negative_before_any_native_check(self):
        for field, bad in (('status', 'FAIL'), ('source_review', 'NOT_RUN'), ('cpu_tests', 'FAIL'),
                           ('clock_check', 'FAIL'), ('clock_check', None),
                           ('observer_cpu_cost', 'FAIL'), ('observer_cpu_cost', None),
                           ('native_scope', 'cuda_trace'), ('max_windows_per_request', 64),
                           ('max_windows_per_request', 2049)):
            gate = dict(self.gate, **{field: bad}); self.write('gate.json', gate)
            identity = copy.deepcopy(self.identity)
            identity['capture']['collection_gate_sha256'] = legacy.sha256(self.root / 'gate.json')
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, 'COLLECTION_GATE_NOT_PASS'):
                adapter.capture_identity(identity)

    def test_receipt_gate_and_base_hash_drift_rejected(self):
        for filename in ('build.json', 'gate.json', 'base-config.json', 'base-identity.json'):
            original = (self.root / filename).read_text()
            (self.root / filename).write_text(original + '\n')
            with self.subTest(filename=filename), self.assertRaisesRegex(RuntimeError, 'DRIFT'):
                adapter.capture_identity(self.identity)
            (self.root / filename).write_text(original)

    def test_native_binary_source_and_unreviewed_file_drift_rejected(self):
        capture, base, _, build = adapter.capture_identity(self.identity)
        for path in (self.binary, self.tree / self.header, self.tree / self.ports[0]):
            original = path.read_text(); path.write_text('changed')
            with self.subTest(path=path), self.assertRaisesRegex(RuntimeError, 'DRIFT'):
                adapter.verify_native(self.tree, capture, base, build)
            path.write_text(original)
        (self.tree / 'extra.cpp').write_text('unreviewed')
        self.git('add', 'extra.cpp')
        with self.assertRaisesRegex(RuntimeError, 'SOURCE_SET_DRIFT'):
            adapter.verify_native(self.tree, capture, base, build)

    def test_only_trace_env_is_added_and_profile_never_allowed(self):
        out = self.root / 'run'
        result = adapter.configure({'extra_frozen_env': {'STRATA_REPLY_REUSE': '1'}}, self.identity, out)
        self.assertEqual(result['extra_frozen_env'], {'STRATA_REPLY_REUSE': '1', adapter.TRACE_ENV: str(out.resolve() / 'native-trace')})
        with self.assertRaisesRegex(RuntimeError, 'TRACE_PREFIX_DRIFT'):
            adapter.configure({}, self.identity, self.root / 'different')
        for key in adapter.FORBIDDEN:
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, 'FORBIDDEN_ENV_PRESENT'):
                adapter.configure({'extra_frozen_env': {key: '0'}}, self.identity, out)

    def test_derived_config_allows_only_frozen_paths_and_trace_env(self):
        capture = copy.deepcopy(self.identity['capture'])
        derived = dict(self.base_config, **capture['allowed_config_changes'])
        path = self.root / 'derived.json'
        config = dict(derived, port=18089, max_context=131072, safety_tokens=4096,
                      min_available_mib=4096, gpu_temp_abort_c=85)
        plan = {'runtime_config_path': str(path)}
        with patch.object(adapter, 'capture_identity', return_value=(capture, self.base, self.base_config, self.build)), \
             patch.object(adapter, 'verify_native') as native:
            self.write('derived.json', dict(derived, gpu_temp_abort_c=100))
            with self.assertRaisesRegex(RuntimeError, 'DERIVED_CONFIG_DRIFT'):
                adapter.preflight(config, self.identity, plan, self.root, {})
            for key in adapter.FORBIDDEN:
                capture['allowed_config_changes']['extra_frozen_env'] = {key: '0'}
                self.write('derived.json', dict(self.base_config, **capture['allowed_config_changes']))
                with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, 'CAPTURE_ENV_DELTA'):
                    adapter.preflight(config, self.identity, plan, self.root, {})
            capture['allowed_config_changes']['extra_frozen_env'] = {'STRATA_REPLY_REUSE': '0'}
            self.write('derived.json', dict(self.base_config, **capture['allowed_config_changes']))
            with self.assertRaisesRegex(RuntimeError, 'CAPTURE_ENV_DELTA'):
                adapter.preflight(config, self.identity, plan, self.root, {})
            native.assert_not_called()

    def test_failed_gate_never_acquires_gpu_or_constructs_engine(self):
        self.gate['cpu_tests'] = 'FAIL'; self.write('gate.json', self.gate)
        self.identity['capture']['collection_gate_sha256'] = legacy.sha256(self.root / 'gate.json')
        self.write('identity.json', self.identity)
        self.write('plan.json', {'runtime_config_path': str(self.root / 'derived.json'),
                                'matrix': [{'requests': [{'request_label': name} for name in ('prime', 'append_1', 'append_2')]}]})
        config = {'gpu_lock_workspace': str(self.root), 'gpu': 0}
        with patch.object(legacy, 'load_config', return_value=config), \
             patch.object(legacy, 'gpu_lock') as lease, \
             patch.object(legacy, 'OwnedServer') as engine, \
             patch.object(legacy, 'verify_assets'), \
             patch.object(legacy.combo, 'assert_service_inactive', return_value={'ActiveState': 'inactive'}), \
             patch.object(legacy.combo, 'protected_hashes', return_value={}), \
             patch.object(legacy, 'gpu_inventory', return_value={}):
            out = legacy.run_diagnostic(self.root / 'plan.json', self.root / 'identity.json',
                                        self.root / 'blocked-run', adapter=adapter.Adapter())
        lease.assert_not_called(); engine.assert_not_called()
        completion = legacy.load(out / 'COMPLETION.json')
        self.assertEqual(completion['engine_starts'], 0)
        self.assertEqual(completion['work_requests_sent'], 0)
        self.assertIn('COLLECTION_GATE_NOT_PASS', completion['reason'])
        self.assertEqual(completion['not_run'], ['prime', 'append_1', 'append_2'])
        self.assertEqual(legacy.load(out / 'QUALIFICATION.json')['status'], 'INSUFFICIENT')

    def test_analysis_failure_cannot_qualify(self):
        with patch.dict('sys.modules', {'tools.frontier.p01b_analysis': None}):
            result = adapter.finalize(self.root, self.identity, [], None)
        self.assertEqual(result['QUALIFICATION']['status'], 'INSUFFICIENT')
        self.assertFalse(result['QUALIFICATION']['new_candidate_qualified'])


if __name__ == '__main__':
    unittest.main()

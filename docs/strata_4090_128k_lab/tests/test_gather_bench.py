import contextlib
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools/gather_probe'
sys.path.insert(0, str(TOOLS))
import bench_once
import root_perf
import run_campaign
spec = importlib.util.spec_from_file_location('gather_analysis', TOOLS / 'analyze.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class GatherBenchTests(unittest.TestCase):
    def test_scope_and_duration_cannot_expand_the_frozen_run(self):
        args = SimpleNamespace(out=str(bench_once.TASK / 'bench/r0-off'), scope='bench', mode='off', warm=30, seconds=60)
        self.assertEqual(bench_once.validate_request(args).name, 'r0-off')
        for key, value in [('out', '/tmp/bench/r0-off'), ('warm', 0), ('seconds', 61), ('mode', 'other'), ('scope', 'other')]:
            invalid = SimpleNamespace(**vars(args))
            setattr(invalid, key, value)
            with self.assertRaises(ValueError):
                bench_once.validate_request(invalid)

    def test_resource_gate_covers_gpu_load_temperature_and_memory(self):
        gpu = {'compute_processes': [], 'temperature_c': '43'}
        with mock.patch.object(bench_once, 'gpu_inventory', return_value=gpu), \
                mock.patch.object(bench_once, 'system_memory', return_value={'meminfo': {'MemAvailable_kib': 8192 * 1024}}):
            self.assertEqual(bench_once.check_resources({})['MemAvailable_mib'], 8192)
        cases = [({'compute_processes': ['99, other'], 'temperature_c': '43'}, 8192, 'GPU_LOAD'),
                 ({'compute_processes': [], 'temperature_c': '85'}, 8192, 'TEMPERATURE'),
                 (gpu, 4095, 'MEMORY_FLOOR')]
        for inventory, available, reason in cases:
            with mock.patch.object(bench_once, 'gpu_inventory', return_value=inventory), \
                    mock.patch.object(bench_once, 'system_memory', return_value={'meminfo': {'MemAvailable_kib': available * 1024}}):
                with self.assertRaisesRegex(RuntimeError, reason):
                    bench_once.check_resources({})

    def test_timeout_cleanup_signals_only_the_owned_process_group(self):
        child = mock.Mock(pid=12345)
        child.wait.side_effect = [subprocess.TimeoutExpired('perf', 5), 0]
        with mock.patch.object(bench_once.os, 'killpg') as kill:
            bench_once.stop_group(child)
        self.assertTrue(kill.call_args_list)
        self.assertTrue(all(call.args[0] == 12345 for call in kill.call_args_list))
        self.assertEqual(child.wait.call_count, 2)

    def test_arm_success_is_ordinary_user_frozen_binary_and_new_session(self):
        with tempfile.TemporaryDirectory() as directory:
            task = Path(directory) / 'task'
            tree = Path(directory) / 'tree'
            out = task / 'bench/r0-on'
            out.mkdir(parents=True)
            (task / 'correctness').mkdir()
            (tree / 'build-lab').mkdir(parents=True)
            exe = tree / 'build-lab/lab_gu_probe'
            exe.write_bytes(b'fixture executable identity')
            (task / 'correctness/COMPLETE.json').write_text(json.dumps({'state': 'PASS', 'binary_sha256': hashlib.sha256(exe.read_bytes()).hexdigest()}))
            (task / 'config.json').write_text(json.dumps({'workspace': str(task), 'extra_frozen_env': {'STRATA_SIDE_MIXER': '2'}}))
            (task / 'production-before.json').write_text(json.dumps({'file_sha256': {'protected': 'hash'}}))
            result = {'state': 'COMPLETE', 'mode': 'on', 'workers': 15, 'seconds': 60.001, 'sweeps': 2, 'candidate_row_calls': 8}
            child = mock.Mock(pid=12345, returncode=0)
            child.poll.return_value = 0
            def launch(command, **kwargs):
                kwargs['stdout'].write(json.dumps(result) + '\n')
                return child
            sampler = mock.Mock()
            sampler.__enter__ = mock.Mock(return_value=sampler)
            sampler.__exit__ = mock.Mock(return_value=False)
            resource = {'MemAvailable_mib': 8192, 'gpu': {'temperature_c': '43', 'compute_processes': []}}
            combo = SimpleNamespace(assert_service_inactive=mock.Mock(), assert_protected=mock.Mock())
            args = SimpleNamespace(out=str(out), scope='bench', mode='on', warm=30, seconds=60)
            with mock.patch.object(bench_once, 'TASK', task), mock.patch.object(bench_once, 'TREE', tree), \
                    mock.patch.object(bench_once.os, 'geteuid', return_value=1000), \
                    mock.patch.object(bench_once.boundary, 'combo', combo), \
                    mock.patch.object(bench_once, 'gpu_lock', return_value=contextlib.nullcontext()), \
                    mock.patch.object(bench_once, 'check_resources', return_value=resource), \
                    mock.patch.object(bench_once, 'MemorySampler', return_value=sampler), \
                    mock.patch.object(bench_once.subprocess, 'Popen', side_effect=launch) as popen, \
                    mock.patch.object(bench_once, 'stop_group') as cleanup:
                self.assertEqual(bench_once.run(args), result)
            self.assertTrue(popen.call_args.kwargs['start_new_session'])
            self.assertEqual(popen.call_args.kwargs['env']['STRATA_LAB_GU_GATHER'], '0')
            cleanup.assert_called_once_with(child)
            self.assertEqual(json.loads((out / 'completion.json').read_text())['state'], 'COMPLETE')
            self.assertEqual(combo.assert_protected.call_count, 2)

    def test_campaign_is_six_balanced_pairs_and_stops_at_failed_arm(self):
        self.assertEqual(sum(order[0] == 'off' for order in run_campaign.ORDERS), 3)
        with tempfile.TemporaryDirectory() as directory:
            task = Path(directory)
            def mkdir(path):
                path.mkdir()
            with mock.patch.object(run_campaign, 'TASK', task), \
                    mock.patch.object(run_campaign.os, 'geteuid', return_value=0), \
                    mock.patch.object(run_campaign, 'mkdir_owned', side_effect=mkdir), \
                    mock.patch.object(run_campaign.root_perf, 'run', return_value=0) as arm:
                self.assertEqual(len(run_campaign.run('bench')), 12)
                self.assertEqual(arm.call_count, 12)
                self.assertTrue(all(call.args[0].warm == 30 and call.args[0].seconds == 60 for call in arm.call_args_list))
        with tempfile.TemporaryDirectory() as directory:
            task = Path(directory)
            with mock.patch.object(run_campaign, 'TASK', task), \
                    mock.patch.object(run_campaign.os, 'geteuid', return_value=0), \
                    mock.patch.object(run_campaign, 'mkdir_owned', side_effect=mkdir), \
                    mock.patch.object(run_campaign.root_perf, 'run', side_effect=[0, 2]) as arm:
                with self.assertRaisesRegex(RuntimeError, 'ARM_FAILED'):
                    run_campaign.run('bench')
                self.assertEqual(arm.call_count, 2)
                self.assertTrue((task / 'bench/FAILURE.json').exists())
                self.assertFalse((task / 'bench/COMPLETE.json').exists())

    def test_root_msr_command_drops_privileges_before_wrapper(self):
        args = SimpleNamespace(scope='bench', mode='on', warm=30, seconds=60)
        command = root_perf.command(args, root_perf.TASK / 'bench/r0-on')
        self.assertIn('msr/aperf/,msr/mperf/', command)
        self.assertEqual(command[command.index('runuser'):command.index('runuser') + 5], ['runuser', '-u', 'hhtele', '--', 'python3'])
        self.assertIn('tools/gather_probe/bench_once.py', ' '.join(command))

    def make_arms(self, task):
        for round_id in range(6):
            for mode in ('off', 'on'):
                folder = task / 'bench' / f'r{round_id}-{mode}'
                folder.mkdir(parents=True)
                value = 96 if mode == 'on' else 100
                result = {'state': 'COMPLETE', 'mode': mode, 'workers': 15, 'seconds': 60.001, 'sweeps': 2,
                          'candidate_row_calls': 8 if mode == 'on' else 0, 'output_hash': 123,
                          **{k: value for k in ('ns_per_sweep', 'gu_ns_per_sweep', 'quant_ns_per_sweep', 'down_ns_per_sweep', 'p95_sweep_ns')}}
                (folder / 'result.json').write_text(json.dumps(result))
                (folder / 'completion.json').write_text(json.dumps({'state': 'COMPLETE'}))
                (folder / 'resources.json').write_text(json.dumps([{'MemAvailable_mib': 8192, 'gpu': {'temperature_c': '43', 'compute_processes': []}}]))

    def test_analyzer_requires_complete_pairs_and_does_not_require_micro(self):
        with tempfile.TemporaryDirectory() as directory:
            task = Path(directory)
            self.make_arms(task)
            with mock.patch.object(analysis.prior, 'frequency', return_value={'aperf_mperf_ratio': 1.1}), \
                    mock.patch.object(analysis.prior, 'memory', return_value={}):
                result = analysis.analyze(task)
                self.assertEqual(result['expansion_gate'], 'PASS')
                self.assertEqual(result['micro_diagnostic']['state'], 'NOT_RUN')
                self.assertEqual(result['metrics']['ns_per_sweep']['n_pairs'], 6)
                (task / 'bench/r5-on/result.json').unlink()
                with self.assertRaises(FileNotFoundError):
                    analysis.analyze(task)

    def test_missing_frequency_evidence_and_output_mismatch_block_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            task = Path(directory)
            self.make_arms(task)
            with mock.patch.object(analysis.prior, 'frequency', side_effect=ValueError('MSR_COUNTER_EVIDENCE_MISSING')):
                with self.assertRaisesRegex(ValueError, 'MSR_COUNTER_EVIDENCE_MISSING'):
                    analysis.analyze(task)
            path = task / 'bench/r5-on/result.json'
            result = json.loads(path.read_text())
            result['output_hash'] = 999
            path.write_text(json.dumps(result))
            with mock.patch.object(analysis.prior, 'frequency', return_value={}), mock.patch.object(analysis.prior, 'memory', return_value={}):
                with self.assertRaisesRegex(ValueError, 'PAIRED_OUTPUT_HASH_MISMATCH'):
                    analysis.analyze(task)


if __name__ == '__main__':
    unittest.main()

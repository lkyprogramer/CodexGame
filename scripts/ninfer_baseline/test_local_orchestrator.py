import importlib.util
import ast
import io
import contextlib
import hashlib
from unittest.mock import patch
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('local_orchestrator', Path(__file__).with_name('local_orchestrator.py'))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def ready():
    return {'status': {'state': 'MEASUREMENT_STAGES_FINISHED', 'pid': 42},
            'watchdog': {'state': 'MEASUREMENT_STAGES_FINISHED', 'child_pid': 42, 'stage': 'all'}}

class OrchestratorTest(unittest.TestCase):
    def test_completed_requires_both_status_and_watchdog_with_same_pid(self):
        self.assertTrue(m.measurement_ready(ready()))
        for key, change in [('watchdog', {'state': 'NEEDS_ATTENTION'}), ('status', {'pid': 5}),
                            ('status', {'resource_monitor_error': 'gpu sampler lost'})]:
            snap = ready(); snap[key].update(change)
            with self.assertRaises(RuntimeError): m.measurement_ready(snap)

    def test_dry_run_only_prepares_local_fixture_plan(self):
        with tempfile.TemporaryDirectory(prefix='local-orchestrator-', dir='/tmp') as d:
            calls = []
            def execute(argv, **kwargs):
                calls.append(argv)
                self.assertEqual(argv[0], m.NODE)
                return subprocess.run(argv, **kwargs)
            o = m.Orchestrator(d, execute=execute)
            o.run(dry_run=True)
            plan = json.loads((Path(d)/'plan.json').read_text())
            self.assertEqual(len(plan['cases']), 60)
            self.assertEqual([x['seed'] for x in plan['cases'][:3]], m.SEEDS)
            self.assertEqual(o.state['state'], 'DRY_RUN_PREPARED')
            self.assertEqual(len(calls), 1)
            self.assertFalse(o.state['model_calls'])

    def test_three_failed_remote_checks_stop_without_launch_or_model_retry(self):
        with tempfile.TemporaryDirectory(prefix='local-orchestrator-', dir='/tmp') as d:
            sleeps = []; o = m.Orchestrator(d, sleeper=sleeps.append)
            o.snapshot = Mock(side_effect=OSError('unreachable'))
            with self.assertRaisesRegex(RuntimeError, 'three consecutive'):
                o.checked_snapshot()
            self.assertEqual(o.snapshot.call_count, 3)
            self.assertEqual(sleeps, [300, 300])
            self.assertIsNone(o.state['bridge_pid'])

    def test_incomplete_existing_case_is_not_retried(self):
        with tempfile.TemporaryDirectory(prefix='local-orchestrator-', dir='/tmp') as d:
            o = m.Orchestrator(d)
            (o.pi_root/'runs'/'business-pagination'/'repeat-1').mkdir(parents=True)
            o.checked_snapshot = Mock(side_effect=AssertionError('must not check/start a request'))
            with self.assertRaisesRegex(RuntimeError, 'unknown model outcome'):
                o.case('business-pagination', 1)
            o.checked_snapshot.assert_not_called()

    def test_durable_failed_case_reused_but_greedy_identity_rejected(self):
        with tempfile.TemporaryDirectory(prefix='local-orchestrator-', dir='/tmp') as d:
            o = m.Orchestrator(d)
            p = o.pi_root/'runs'/'business-pagination'/'repeat-1'; p.mkdir(parents=True)
            data = {'id': 'business-pagination', 'repeat': 1, 'status': 'FAIL'}
            (p/'summary.json').write_text(json.dumps(data))
            identity = {'seed': 1701, 'samplingProfile': 'PRODUCTION', 'thinking': 'medium',
                        'maxTokens': 32768, 'model': o.model}
            (p/'identity.json').write_text(json.dumps(identity))
            self.assertEqual(o.case('business-pagination', 1)['status'], 'FAIL')
            identity['samplingProfile'] = 'GREEDY'; (p/'identity.json').write_text(json.dumps(identity))
            with self.assertRaisesRegex(RuntimeError, 'identity mismatch'):
                o.case('business-pagination', 1)

    def test_recorded_timeout_is_preserved_and_not_continued(self):
        with tempfile.TemporaryDirectory(prefix='local-orchestrator-', dir='/tmp') as d:
            o = m.Orchestrator(d)
            p = o.pi_root/'runs'/'business-pagination'/'repeat-1'; p.mkdir(parents=True)
            (p/'summary.json').write_text(json.dumps({'id':'business-pagination','repeat':1,'status':'TIMEOUT'}))
            (p/'identity.json').write_text(json.dumps({'seed':1701,'samplingProfile':'PRODUCTION',
                    'thinking':'medium','maxTokens':32768,'model':o.model}))
            with self.assertRaisesRegex(RuntimeError, 'unfinished upstream'):
                o.case('business-pagination',1)
            self.assertEqual(json.loads((p/'summary.json').read_text())['status'],'TIMEOUT')

    def test_serial_60_case_order_and_cleanup_without_real_processes(self):
        with tempfile.TemporaryDirectory(prefix='local-orchestrator-', dir='/tmp') as d:
            o = m.Orchestrator(d)
            o.prepare = lambda: {'cases': [{'id': 'case-'+str(i)} for i in range(20)]}
            o.checked_snapshot = lambda collector=False,**kw: ready()
            calls = []
            o.start_bridge = lambda: calls.append('bridge')
            o.start_tunnel = lambda: calls.append('tunnel')
            o.start_caffeinate = lambda: calls.append('caffeinate')
            o.stop_caffeinate = lambda: calls.append('stop-caffeinate')
            o.stop_tunnel = lambda: calls.append('stop-tunnel')
            o.stop_bridge = lambda: calls.append('stop-bridge')
            def case(case, repeat):
                calls.append((case, repeat)); return {'id': case, 'repeat': repeat, 'status': 'FAIL' if repeat == 2 else 'PASS'}
            o.case = case; o.run()
            self.assertEqual(calls[:2], ['bridge', 'tunnel'])
            self.assertEqual(calls[2:6], ['caffeinate', ('case-0', 1), ('case-0', 2), ('case-0', 3)])
            self.assertEqual(calls[-3:], ['stop-tunnel', 'stop-bridge', 'stop-caffeinate'])
            summary = json.loads((Path(d)/'summary.json').read_text())
            self.assertEqual(summary['recorded_cases'], 60)
            self.assertEqual(summary['case_status_counts'], {'PASS': 40, 'FAIL': 20})
            self.assertEqual(summary['profile'], 'ISOLATED_PI_FIXTURE')
            self.assertEqual(summary['samplingProfile'], 'PRODUCTION')
            self.assertEqual(o.state['state'], 'FINISHED')

    def test_process_tree_covers_pi_detached_group_descendants(self):
        self.assertEqual(m.descendant_pids(10, '10 1\n20 10\n30 20\n40 1\n'), [30, 20, 10])

    def test_remote_commands_only_expected_status_files(self):
        with tempfile.TemporaryDirectory(prefix='local-orchestrator-', dir='/tmp') as d:
            execute = Mock(return_value=subprocess.CompletedProcess([], 0, json.dumps(ready()), ''))
            o = m.Orchestrator(d, execute=execute)
            self.assertEqual(o.snapshot(o.remote_root), ready())
            argv = execute.call_args.args[0]
            self.assertEqual(argv[:3], ['ssh', '-oBatchMode=yes', '-oConnectTimeout=20'])
            self.assertNotIn('-J', argv)
            self.assertNotIn('jump', argv)
            self.assertEqual(argv[3], '29')
            self.assertIn("'status'", argv[-1]); self.assertIn("'watchdog'", argv[-1])
            self.assertNotIn('auth', argv[-1])

class SlimOrchestratorTests(unittest.TestCase):
    def slim(self,d,**kw):
        return m.Orchestrator(d,remote_root='/home/hhtele/ninfer-baseline-20261020/slim-v1',mode='slim',**kw)
    def snapshot(self,stage='priority'):
        snap=ready();snap['manifest_sha256']='a'*64;snap['status'].update(stage=stage,manifest_sha256='a'*64);snap['watchdog']['stage']=stage;return snap
    def test_priority_requires_stage_and_manifest_identity(self):
        self.assertTrue(m.measurement_ready(self.snapshot(),'priority'))
        for field in ['stage','manifest_sha256']:
            s=self.snapshot();s['status'][field]='wrong'
            with self.assertRaises(RuntimeError):m.measurement_ready(s,'priority')
    def test_slim_dry_plan_has_eight_single_seed_cases_and_frozen_paths(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as d:
            o=self.slim(d);o.run(dry_run=True);plan=json.loads((Path(d)/'plan.json').read_text())
            self.assertEqual(len(plan['cases']),8);self.assertEqual({r['seed'] for r in plan['cases']},{1701})
            self.assertEqual({r['repeat'] for r in plan['cases']},{1});self.assertTrue(o.bin.endswith('/slim-bin-v1'))
            self.assertEqual(plan['cases'][3]['id'],'qcb-BF009');self.assertEqual(plan['cases'][-1]['id'],'qcb-LC003')
    def test_slim_cleanup_precedes_remaining_and_cases_have_stable_ordinals(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as d:
            o=self.slim(d);o.prepare=lambda:{'cases':[{'id':str(i)} for i in range(8)]};o.checked_snapshot=lambda **kw:self.snapshot()
            calls=[]
            for method in ['start_bridge','start_tunnel','start_caffeinate','stop_case_parent','stop_tunnel','stop_bridge','stop_caffeinate','run_remaining']:
                setattr(o,method,lambda method=method:calls.append(method))
            def case(id,repeat):calls.append(('case',id,repeat,o.state['current_ordinal']));return {'id':id,'repeat':repeat,'status':'OUTPUT_LIMIT' if id=='2' else 'FAIL'}
            o.case=case;o.run();self.assertEqual([x[3] for x in calls if isinstance(x,tuple)],list(range(1,9)))
            self.assertEqual(calls[-5:],['stop_case_parent','stop_tunnel','stop_bridge','stop_caffeinate','run_remaining'])
    def test_pending_external_manifest_has_no_false_completion(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as d:
            o=self.slim(d);o.continue_external();self.assertEqual(o.state['state'],'EXTERNAL_MANIFEST_UNCONFIGURED_NOT_BASELINE_PASS')
            self.assertFalse(o.state.get('model_calls_attempted',False))
    def test_unknown_model_is_rejected_before_work(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as d:
            with self.assertRaises(ValueError):self.slim(d,model='other-model')

    def test_remaining_handoff_is_recorded_after_known_eight_and_errors_are_durable(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as d:
            o=self.slim(d,sleeper=lambda _:None)
            o.state['completed']=[{'id':f'case-{i}','repeat':1,'status':'FAIL'} for i in range(8)]
            (Path(d)/'summary.json').write_text('{}')
            o.remote=Mock(side_effect=RuntimeError('remote unavailable'))
            with self.assertRaisesRegex(RuntimeError,'unavailable'):o.run_remaining()
            self.assertEqual(o.state['state'],'NEEDS_ATTENTION')
            code=o.remote.call_args.args[0]
            self.assertIn("coding-handoff.json",code);self.assertIn("known_completed_cases",code)
            self.assertIn("local_summary_sha256",code);self.assertIn("slim-bin-v1/slim_runner.py",code)
            self.assertIn("manifest_sha256",code)
    def test_unknown_coding_result_cannot_release_remaining(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as d:
            o=self.slim(d);o.state['completed']=[{'id':str(i),'repeat':1,'status':'TIMEOUT'} for i in range(8)]
            o.remote=Mock()
            with self.assertRaisesRegex(RuntimeError,'known coding'):o.run_remaining()
            o.remote.assert_not_called();self.assertEqual(o.state['state'],'NEEDS_ATTENTION')

class RecoveryTests(unittest.TestCase):
    def test_known_coding_recovery_never_calls_old_cases(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as d:
            o=m.Orchestrator(d,remote_root='/home/hhtele/ninfer-baseline-20261020/slim-v1',mode='slim')
            o.state.update(state='RECOVERED_KNOWN_CODING',completed=[{'id':str(i),'repeat':1,'status':'PASS'} for i in range(8)])
            calls=[]
            def external():calls.append('external');o.state['external_done']=True
            o.verify_recovery_evidence=Mock();o.continue_external=external;o.run_remaining=lambda:calls.append('remaining');o.case=Mock(side_effect=AssertionError('old coding cannot repeat'))
            o.prepare=Mock(side_effect=AssertionError('old prepare cannot run'))
            o.run();self.assertEqual(calls,['external','remaining']);o.case.assert_not_called();o.prepare.assert_not_called()

class RecoveryAndLaunchTests(unittest.TestCase):
    def test_remote_remaining_code_compiles_and_executes_with_local_fake_process(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as d:
            o=m.Orchestrator(d,remote_root='/home/hhtele/ninfer-baseline-20261020/slim-v1',mode='slim',sleeper=lambda _:None)
            o.state['completed']=[{'id':str(i),'repeat':1,'status':'FAIL'} for i in range(8)]
            (Path(d)/'summary.json').write_text('{}');remote=Path(d)/'remote';remote.mkdir();(remote/'manifest.json').write_text('{"frozen":true}')
            generated=[]
            def execute(code):
                ast.parse(code);generated.append(code)
                local=code.replace(repr(o.remote_root),repr(str(remote)))
                output=io.StringIO()
                with patch('subprocess.Popen',return_value=Mock(pid=901)),contextlib.redirect_stdout(output):exec(compile(local,'local_remote_simulation','exec'),{})
                return json.loads(output.getvalue())
            o.remote=execute
            o.checked_snapshot=lambda **kw:{'status':{'state':'MEASUREMENT_STAGES_FINISHED','stage':'remaining','manifest_sha256':'a'*64,'pid':42},'watchdog':{'state':'MEASUREMENT_STAGES_FINISHED','stage':'remaining','child_pid':42},'manifest_sha256':'a'*64}
            o.continue_external=lambda:None;o.run_remaining()
            receipt=json.loads((remote/'coding-handoff.json').read_text());self.assertEqual(receipt['known_completed_cases'],8);self.assertFalse(receipt['unknown_outcomes'])
            self.assertEqual(receipt['manifest_sha256'],hashlib.sha256((remote/'manifest.json').read_bytes()).hexdigest())
            self.assertEqual(json.loads((remote/'local-remaining-owner.json').read_text())['pid'],901)
    def test_bridge_startup_checks_waiting_identity_and_uses_short_poll(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as d:
            sleeps=[];o=m.Orchestrator(d,sleeper=sleeps.append)
            def snap(state):return {'status':{'state':state,'pid':42},'watchdog':{'state':'MONITORING','stage':'bridge','child_pid':42,'heartbeat_utc':m.utc()}}
            o.snapshot=Mock(side_effect=[snap('PREPARING'),snap('BRIDGE_WAITING')]);response=Mock(status=200);o.open=Mock(return_value=contextlib.nullcontext(response))
            self.assertEqual(o.checked_snapshot(collector=True,startup=True)['status']['state'],'BRIDGE_WAITING');self.assertEqual(sleeps,[5]);o.open.assert_called_once()
    def test_hard_budget_remains_unknown(self):
        self.assertIn('BUDGET_HARD_STOP',m.UNKNOWN_OUTCOME_STATUSES)

class PersistentRecoveryTests(unittest.TestCase):
    def test_waiting_external_recovery_never_falls_back_to_old_eight_and_runs_remaining(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as d:
            o=m.Orchestrator(d,remote_root='/home/hhtele/ninfer-baseline-20261020/slim-v1',mode='slim')
            (Path(d)/'recovery.json').write_text('{}');o.state['state']='WAITING_EXTERNAL_SOURCES';o.verify_recovery_evidence=Mock()
            calls=[]
            def external():calls.append('external');o.state['external_done']=True
            o.continue_external=external;o.run_remaining=lambda:calls.append('remaining');o.case=Mock(side_effect=AssertionError('old coding cannot repeat'));o.prepare=Mock(side_effect=AssertionError('no old plan'))
            o.run();self.assertEqual(calls,['external','remaining']);o.case.assert_not_called();o.prepare.assert_not_called()
    def test_unknown_attention_recovery_never_retries(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as d:
            o=m.Orchestrator(d,remote_root='/home/hhtele/ninfer-baseline-20261020/slim-v1',mode='slim')
            (Path(d)/'recovery.json').write_text('{}');o.state['state']='NEEDS_ATTENTION';o.continue_external=Mock()
            with self.assertRaisesRegex(RuntimeError,'no automatic model retry'):o.run()
            o.continue_external.assert_not_called()

if __name__ == '__main__': unittest.main()

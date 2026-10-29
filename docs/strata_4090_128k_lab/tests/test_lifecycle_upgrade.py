import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from lab import runner
from lab.assets import snapshot
from lab.core import dump, sha256
from lab import scenarios


class LifecycleTests(unittest.TestCase):
    def config(self, root):
        (root/'model.gguf').write_bytes(b'model')
        (root/'template').write_text('template')
        (root/'prod.json').write_text('{}')
        cfg = {'workspace': str(root/'work'), 'deployed_repo': str(root),
               'deployed_config': str(root/'prod.json'), 'gguf': str(root/'model.gguf'),
               'template': str(root/'template')}
        snapshot(cfg)
        return cfg

    def test_final_config_mutation_blocks_completion_receipt(self):
        self.assertTrue(hasattr(runner, 'evidence_lifecycle'), 'All execution modes need final evidence audit')
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); cfg=self.config(root); out=root/'result'
            with self.assertRaises(RuntimeError):
                with runner.evidence_lifecycle(cfg,out):
                    (root/'prod.json').write_text('{"changed":true}')
            self.assertTrue((out/'FAILURE.json').exists())
            self.assertFalse((out/'COMPLETION.json').exists())

    def test_original_exception_survives_secondary_asset_failure(self):
        self.assertTrue(hasattr(runner, 'evidence_lifecycle'), 'Final audits must run on exception paths')
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); cfg=self.config(root); out=root/'result'
            with self.assertRaisesRegex(ValueError, 'original request failure'):
                with runner.evidence_lifecycle(cfg,out):
                    (root/'model.gguf').write_bytes(b'changed model')
                    raise ValueError('original request failure')
            failure=json.loads((out/'FAILURE.json').read_text())
            self.assertIn('original request failure', failure['error'])
            self.assertTrue(failure['final_audit_errors'])

    def test_success_receipt_requires_final_assets_and_config_unchanged(self):
        self.assertTrue(hasattr(runner, 'evidence_lifecycle'))
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); cfg=self.config(root); out=root/'result'
            with runner.evidence_lifecycle(cfg,out):
                pass
            receipt=json.loads((out/'COMPLETION.json').read_text())
            self.assertEqual(receipt, {'state':'COMPLETE','final_audit':'PASS'})

    def test_server_release_runs_even_when_request_raises(self):
        self.assertTrue(hasattr(runner, 'managed_server'), 'Scenario and campaign must share owned server release')
        events=[]
        class Owned:
            def __init__(self,*args):pass
            def __enter__(self):events.append('start');return self
            def __exit__(self,*args):events.append('stop')
        with patch.object(runner,'OwnedServer',Owned), patch.object(runner,'wait_released',lambda c:events.append('released')):
            with self.assertRaisesRegex(ValueError,'request'):
                with runner.managed_server({},Path('.'),'base',{},Path('.')):
                    raise ValueError('request')
        self.assertEqual(events,['start','stop','released'])

    def test_foreign_gpu_pid_is_rejected_even_with_same_binary(self):
        self.assertTrue(hasattr(runner, 'validate_gpu_ownership'))
        identities = {10:{'exe':'/engine','pgid':100,'start_ticks':'1','args':['/engine','--max-context','131072']},
                      11:{'exe':'/engine','pgid':999,'start_ticks':'2','args':['/engine','--max-context','131072']}}
        with patch.object(runner,'process_identity',lambda pid:identities[pid]):
            with self.assertRaisesRegex(RuntimeError,'foreign'):
                runner.validate_gpu_ownership(['10, strata, 20000','11, strata, 1'],100,'/engine')

    def test_engine_in_its_own_group_under_the_owned_server_is_accepted(self):
        # Strata's serve/lifeline.py moves the engine into its own process group (os.setpgid(0, 0)).
        identities = {10:{'exe':'/engine','pgid':10,'ppid':100,'start_ticks':'1','args':['/engine','--max-context','131072']},
                      100:{'exe':'/python','pgid':100,'ppid':1,'start_ticks':'0','args':['python']}}
        with patch.object(runner,'process_identity',lambda pid:identities[pid]):
            receipt=runner.validate_gpu_ownership(['10, strata, 20000'],100,'/engine')
        self.assertEqual(receipt[0]['pid'],10)

    def test_own_group_process_outside_the_owned_server_tree_is_rejected(self):
        identities = {12:{'exe':'/engine','pgid':12,'ppid':50,'start_ticks':'1','args':['/engine','--max-context','131072']},
                      50:{'exe':'/python','pgid':50,'ppid':1,'start_ticks':'0','args':['python']}}
        with patch.object(runner,'process_identity',lambda pid:identities[pid]):
            with self.assertRaisesRegex(RuntimeError,'foreign'):
                runner.validate_gpu_ownership(['12, strata, 20000'],100,'/engine')

    def test_owned_profiler_child_is_accepted(self):
        self.assertTrue(hasattr(runner, 'validate_gpu_ownership'))
        identity={'exe':'/engine','pgid':100,'start_ticks':'1','args':['/engine','--max-context','131072']}
        with patch.object(runner,'process_identity',lambda pid:identity):
            receipt=runner.validate_gpu_ownership(['10, strata, 20000'],100,'/engine')
        self.assertEqual(receipt[0]['pid'],10)

    def test_banned_env_is_rejected_from_common_frozen_config(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); cfg=self.config(root)
            cfg.update(max_context=131072,conversation_cache_mib=0,port=18089,
                       extra_frozen_env={'STRATA_STAGE_PIN':'1'})
            with self.assertRaises(RuntimeError):
                runner.make_run_config(cfg,root/'tree','base',{},root/'out')

    def test_reply_chain_rejects_server_token_counter_drift(self):
        self.assertTrue(hasattr(runner,'audited_chat'), 'Scenarios need the same per-request usage audit as campaigns')
        class Server:
            base='http://127.0.0.1:18089';key='x';abort_reason=None
        response={'text':'OK','finish_reason':'stop','usage':{'prompt_tokens':1000,'completion_tokens':1},'error':None}
        with patch.object(runner.http,'chat',return_value=response):
            result=runner.audited_chat(Server(),lambda request:10,
                    {'request_timeout_s':10,'safety_tokens':4096,'max_context':131072}, {'max_tokens':1})
        self.assertIn('TOKEN_COUNTER_DRIFT',result['error'])

    def test_usage_type_error_marks_scenario_as_aborted(self):
        class Server:
            base='http://127.0.0.1:18089';key='x';abort_reason=None
        server=Server()
        response={'text':'OK','finish_reason':'stop','usage':{'prompt_tokens':'100','completion_tokens':1},'error':None}
        with patch.object(runner.http,'chat',return_value=response):
            result=runner.audited_chat(server,lambda request:100,
                    {'request_timeout_s':10,'safety_tokens':4096,'max_context':131072},{'max_tokens':1})
        self.assertIn('USAGE_NOT_AUDITABLE',result['error'])
        self.assertIsNotNone(server.abort_reason)

    def test_scenario_cannot_bypass_final_evidence_audit(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); cfg=self.config(root); cfg.update(rounds=1)
            cfg.update(gguf=str(root/'model.gguf'),template=str(root/'template'))
            base=root/'base';candidate=root/'candidate'
            for tree,sha in ((base,'base-sha'),(candidate,'candidate-sha')):
                (tree/'build-lab').mkdir(parents=True)
                exe=tree/'build-lab/strata';exe.write_bytes(b'fake executable never run')
                dump(tree/'build-lab/LAB_BUILD.json',{'source_sha':sha,'exe':str(exe),'exe_sha256':sha256(exe)})
            class FakeServer:
                def __init__(self,*args):pass
                def __enter__(self):return self
                def __exit__(self,*args):pass
            def task(*args):
                (root/'prod.json').write_text('{"changed":true}')
                return {'pass':True,'wall_s':1}
            with patch.object(scenarios,'validate_ready',return_value={'status':'READY','candidate_sha':'candidate-sha'}), \
                 patch.object(scenarios,'baseline_dir',return_value=base), \
                 patch.object(scenarios,'candidate_dir',return_value=candidate), \
                 patch.object(scenarios,'lock',return_value={'baseline_sha':'base-sha'}), \
                 patch.object(scenarios,'StrataCounter',return_value=lambda request:10), \
                 patch.object(scenarios,'validate_counter'), \
                 patch.object(scenarios,'reply_chain',side_effect=task), \
                 patch.object(scenarios,'OwnedServer',FakeServer,create=True), \
                 patch.object(runner,'OwnedServer',FakeServer), \
                 patch.object(runner,'wait_released'):
                with self.assertRaisesRegex(RuntimeError,'Final evidence audit'):
                    scenarios.run_scenario(cfg,1536,'reply-chain')
            result=next((root/'work/results').iterdir())
            self.assertTrue((result/'FAILURE.json').exists())
            self.assertFalse((result/'COMPLETION.json').exists())

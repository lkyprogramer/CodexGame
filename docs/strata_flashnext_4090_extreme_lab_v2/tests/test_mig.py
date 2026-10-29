import json,tempfile,unittest
from pathlib import Path
import os
from lab.core import flag_value, load_config
import socket
from unittest import mock
from lab.runner import make_run_config, manifest_diff, tree_manifest, wait_released


class MigTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();p=Path(self.t.name);self.prod=p/'prod';(self.prod/'engine').mkdir(parents=True)
        (self.prod/'cfg.json').write_text(json.dumps({'exe':'engine/strata','args':['--pack','packs/a','--max-context','131072',
            '--expert-profile-save','data/learned.bin'],'env':{'STRATA_ADAPT_OVERLAP':'1'},'user_args':[]}))
        self.c={'deployed_config':str(self.prod/'cfg.json'),'deployed_repo':str(self.prod),'max_context':131072,'conversation_cache_mib':6144,'port':18089}
        self.p=p

    def tearDown(self):self.t.cleanup()

    def test_p_arm_runs_the_deployed_binary_without_write_flags(self):
        cfg=make_run_config(self.c,self.prod,'p',{},self.p/'out')
        self.assertEqual(cfg['exe'],str(self.prod/'engine/strata'))
        self.assertIsNone(flag_value(cfg['args'],'--expert-profile-save'))
        self.assertEqual(cfg['log'],str(self.p/'out'/'engine.log'))
        self.assertEqual(cfg['env']['STRATA_ADAPT_OVERLAP'],'1')

    def test_base_arm_keeps_the_lab_build(self):
        cfg=make_run_config(self.c,self.p/'base','base',{},self.p/'out')
        self.assertEqual(cfg['exe'],str(self.p/'base'/'build-lab'/'strata'))

    def test_cfg_arm_adds_its_env_and_base_stays_a0(self):
        ready={'cfg':{'env':{'STRATA_MMVQ_IL':'0'}}}
        on=make_run_config(self.c,self.p/'base','cfg',ready,self.p/'on')
        off=make_run_config(self.c,self.p/'base','base',ready,self.p/'off')
        self.assertEqual(on['env']['STRATA_MMVQ_IL'],'0');self.assertNotIn('STRATA_MMVQ_IL',off['env'])
        self.assertEqual(on['env']['STRATA_ADAPT_OVERLAP'],'1')

    def test_cfg_arm_args_override_but_frozen_flags_refuse(self):
        on=make_run_config(self.c,self.p/'base','cfg',{'cfg':{'args':{'--pool-workers':'8'}}},self.p/'on')
        self.assertEqual(flag_value(on['args'],'--pool-workers'),'8')
        with self.assertRaises(RuntimeError):make_run_config(self.c,self.p/'base','cfg',{'cfg':{'args':{'--max-context':'262144'}}},self.p/'x')

    def test_manifest_detects_writes_into_the_deployed_tree(self):
        before=tree_manifest(self.prod)
        self.assertFalse(any(manifest_diff(before,tree_manifest(self.prod)).values()))
        (self.prod/'serve').mkdir();(self.prod/'serve'/'x.pyc').write_bytes(b'1')
        (self.prod/'cfg.json').write_text('{}')
        d=manifest_diff(before,tree_manifest(self.prod))
        self.assertEqual(d['added'],['serve/x.pyc']);self.assertEqual(d['changed'],['cfg.json'])

    def test_load_config_keeps_the_venv_python_symlink(self):
        venv=self.p/'venv'/'bin';venv.mkdir(parents=True);os.symlink('/usr/bin/env',venv/'python')
        cfg=self.p/'local.json';cfg.write_text(json.dumps({'workspace':str(self.p/'ws'),'deployed_repo':str(self.prod),
            'deployed_config':str(self.prod/'cfg.json'),'python':str(venv/'python'),'max_context':131072,'safety_tokens':4096,'port':18089}))
        self.assertEqual(load_config(cfg)['python'],str(venv/'python'))

    def test_wait_released_waits_for_port_and_gpu(self):
        calls={'n':0}
        def gpu(_):
            calls['n']+=1
            return {'compute_processes':['1, strata'] if calls['n']<3 else []}
        with socket.socket() as s:
            s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        with mock.patch('lab.runner.gpu_inventory',gpu),mock.patch('lab.runner.time.sleep'):
            wait_released({'port':port,'gpu':'0'})
        self.assertEqual(calls['n'],3)

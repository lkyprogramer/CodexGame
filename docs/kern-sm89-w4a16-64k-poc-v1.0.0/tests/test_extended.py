import copy, hashlib, json, math, os, signal, subprocess, sys, tempfile, threading, time, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import numpy as np
from poc_tools.core import evaluate_evidence
from poc_tools.numeric_check import compare
from poc_tools.build_prompts import build_tokens
from poc_tools.java_runner import summarize_pi
from poc_tools.http_probe import probe
ROOT=Path(__file__).resolve().parents[1]

class NumericTests(unittest.TestCase):
    def test_equal(self):
        self.assertTrue(compare(np.array([1.0],dtype=np.float32),np.array([1.0],dtype=np.float32))['bit_equal'])
    def test_difference(self):
        self.assertEqual(compare(np.array([1.0]),np.array([1.1]))['status'],'FAIL')
    def test_shape(self):
        self.assertEqual(compare(np.ones(2),np.ones(3))['status'],'FAIL')
    def test_nan(self):
        self.assertEqual(compare(np.array([np.nan]),np.array([1.0]))['status'],'FAIL')
    def test_empty_is_not_evidence(self):
        self.assertEqual(compare(np.array([]),np.array([]))['status'],'FAIL')
    def test_negative_tolerance(self):
        with self.assertRaises(ValueError):compare(np.ones(1),np.ones(1),-1,0)

class PromptTests(unittest.TestCase):
    def test_deterministic_exact_raw_ids(self):
        enc=lambda s:list(s.encode())
        a=build_tokens(enc,512,17);b=build_tokens(enc,512,17);c=build_tokens(enc,512,18)
        self.assertEqual(len(a),512);self.assertEqual(a,b);self.assertNotEqual(a,c)
    def test_bad_target(self):
        with self.assertRaises(ValueError):build_tokens(lambda s:[1],0,17)
    def test_empty_encoder_cannot_loop_forever(self):
        with self.assertRaises(ValueError):build_tokens(lambda s:[],128,17)

class EvidenceCompleteTests(unittest.TestCase):
    def setup_data(self,root):
        (root/'raw.txt').write_text('CPU fixture for evaluator tests only, NOT GPU evidence')
        ref={'path':'raw.txt','sha256':hashlib.sha256((root/'raw.txt').read_bytes()).hexdigest()}
        d={'hardware_verified':True,'device_cc':'8.9','run_id':'test-only',
           'profile':'p0-bf16-kv','speculation':'none','activation_dtype':'bf16','gdn_dtype':'fp32','kv_dtype':'bf16',
           'model_sha256':'a'*64,'kern_commit':'b'*40,'profile_sha256':'c'*64,
           'gates':{k:{'status':'PASS','evidence':[ref]} for k in ['environment','artifact','numeric','context64k','cache','java','lifecycle','performance']}}
        d['gates']['performance']['samples']=[{'sample_id':f'{p}-{i}','prompt_tokens':p,'output_tokens':2048,'count_basis':'accepted_target_tokens','speculation':'none','time_basis':'engine_decode_wall','decode_ms':ms} for p,ms in [(4096,30000),(65536,60000)] for i in range(3)]
        d['gates']['context64k'].update(actual_prompt_tokens=65536,generated_tokens=2048,truncated=False,minimum_free_bytes=1024<<20)
        d['gates']['java'].update(passed=3,protected_files_unchanged=True)
        return d
    def with_change(self,change):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d=self.setup_data(root);change(d,root);return evaluate_evidence(d,root)
    def test_complete_structure_passes_evaluator_only(self):
        r=self.with_change(lambda d,p:None);self.assertEqual(r['decision'],'POC_GO');self.assertFalse(r['production_promoted'])
    def test_hash_tamper(self):
        self.assertNotEqual(self.with_change(lambda d,p:(p/'raw.txt').write_text('tamper'))['decision'],'POC_GO')
    def test_nan_rate(self):
        self.assertNotEqual(self.with_change(lambda d,p:d['gates']['performance']['samples'][0].update(decode_ms=float('nan')))['decision'],'POC_GO')
    def test_inf_rate(self):
        self.assertNotEqual(self.with_change(lambda d,p:d['gates']['performance']['samples'][0].update(decode_ms=float('inf')))['decision'],'POC_GO')
    def test_underlength(self):
        self.assertNotEqual(self.with_change(lambda d,p:d['gates']['performance']['samples'][0].update(output_tokens=12))['decision'],'POC_GO')
    def test_count_draft_not_target(self):
        self.assertNotEqual(self.with_change(lambda d,p:d['gates']['performance']['samples'][0].update(count_basis='draft_tokens'))['decision'],'POC_GO')
    def test_fp16_state_not_p0(self):
        self.assertNotEqual(self.with_change(lambda d,p:d.update(gdn_dtype='fp16'))['decision'],'POC_GO')
    def test_not_enough_free_memory(self):
        self.assertEqual(self.with_change(lambda d,p:d['gates']['context64k'].update(minimum_free_bytes=200<<20))['decision'],'NO_GO')
    def test_symlink_escape(self):
        def change(d,p):
            (p/'raw.txt').unlink();(p/'raw.txt').symlink_to('/etc/hostname')
        self.assertNotEqual(self.with_change(change)['decision'],'POC_GO')

class PiStatsTests(unittest.TestCase):
    def test_aggregate_whole_session(self):
        es=[{'type':'tool_execution_start','toolCallId':'a'},{'type':'tool_execution_start','toolCallId':'a'},
            {'type':'tool_execution_start','toolCallId':'b'},
            {'type':'message_end','message':{'role':'assistant','id':'m1','usage':{'input':200,'output':20}}},
            {'type':'message_end','message':{'role':'assistant','id':'m2','usage':{'input':300,'output':30}}}]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'pi';p.write_text('\n'.join(map(json.dumps,es)))
            r=summarize_pi(p);self.assertEqual(r['tool_calls'],2);self.assertEqual(r['usage_sum']['output'],50)
    def test_no_usage_is_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'pi';p.write_text('{}\nnot json\n');r=summarize_pi(p)
            self.assertIsNone(r['usage_sum']);self.assertEqual(r['unparsed_lines'],1)

class MockSseTests(unittest.TestCase):
    def test_local_mock_collection_not_gpu(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                data='data: {"choices":[{"delta":{"content":"test"}}]}\n\ndata: {"choices":[],"usage":{"prompt_tokens":64,"completion_tokens":9}}\n\ndata: [DONE]\n\n'
                self.wfile.write(data.encode());self.wfile.flush()
        server=HTTPServer(('127.0.0.1',0),Handler);t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
        try:
            r=probe(f'http://127.0.0.1:{server.server_port}/v1',{'prompt':[1,2]},timeout=3)
            self.assertEqual(r['status'],'COMPLETE');self.assertEqual(r['output_tokens'],9);self.assertIsNone(r['server_decode_tps'])
        finally:server.shutdown();server.server_close();t.join()

class SuiteTests(unittest.TestCase):
    def test_stage_success_not_gpu_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'plan.json').write_text(json.dumps({'stages':[{'id':'ok','argv':[sys.executable,'-c','print("hello")'],'timeout_s':5}]}))
            x=subprocess.run([sys.executable,'-m','poc_tools.suite','--plan',str(p/'plan.json'),'--out-dir',str(p/'out')],cwd=ROOT,capture_output=True,text=True,timeout=10)
            self.assertEqual(x.returncode,0);self.assertEqual(json.loads((p/'out/suite.json').read_text())['stages'][0]['status'],'COMMAND_OK')
    def test_timeout(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'plan.json').write_text(json.dumps({'stages':[{'id':'slow','argv':[sys.executable,'-c','import time; time.sleep(60)'],'timeout_s':0.1}]}))
            x=subprocess.run([sys.executable,'-m','poc_tools.suite','--plan',str(p/'plan.json'),'--out-dir',str(p/'out')],cwd=ROOT,capture_output=True,text=True,timeout=10)
            self.assertEqual(x.returncode,78);self.assertEqual(json.loads((p/'out/suite.json').read_text())['stages'][0]['status'],'INCOMPLETE')
    def test_stage_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'plan.json').write_text(json.dumps({'stages':[{'id':'../escape','argv':[sys.executable,'-c','print(1)'],'timeout_s':5}]}))
            x=subprocess.run([sys.executable,'-m','poc_tools.suite','--plan',str(p/'plan.json'),'--out-dir',str(p/'out')],cwd=ROOT,capture_output=True,text=True,timeout=10)
            self.assertNotEqual(x.returncode,0);self.assertFalse((p/'escape.log').exists())
    @unittest.skipUnless(os.name=='posix','POSIX process groups')
    def test_signal_cleans_isolated_stage(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);pidfile=p/'child.pid';endfile=p/'child-ended'
            code='import os,time,signal,pathlib,sys\npathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\ndef stop(s,f):\n pathlib.Path(sys.argv[2]).write_text("cleaned")\n raise SystemExit(0)\nsignal.signal(signal.SIGTERM,stop)\ntime.sleep(60)'
            (p/'plan.json').write_text(json.dumps({'stages':[{'id':'wait','argv':[sys.executable,'-c',code,str(pidfile),str(endfile)],'timeout_s':50}]}))
            proc=subprocess.Popen([sys.executable,'-m','poc_tools.suite','--plan',str(p/'plan.json'),'--out-dir',str(p/'out')],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                limit=time.monotonic()+4
                while not pidfile.exists() and time.monotonic()<limit:time.sleep(.03)
                self.assertTrue(pidfile.exists());proc.terminate();proc.wait(timeout=8)
                self.assertTrue(endfile.exists(),'isolated stage survived supervisor termination')
            finally:
                if proc.poll() is None:proc.kill();proc.wait()
                if pidfile.exists():
                    try:os.killpg(int(pidfile.read_text()),signal.SIGKILL)
                    except ProcessLookupError:pass

if __name__=='__main__':unittest.main()

class GuardContractTests(unittest.TestCase):
    """Pure mocked control-plane contracts: never call real systemctl/GPU commands."""
    def exercise(self,active=True,allow=False,gpu_rows='',stale=False):
        import importlib.util
        from unittest.mock import patch, MagicMock
        spec=importlib.util.spec_from_file_location('kit_guard',ROOT/'scripts/guard_gpu.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'run').mkdir();(root/'.state').mkdir()
            if stale:(root/'.state/gpu-lease.json').write_text(json.dumps({'restore_required':True,'guard_pid':1,'unit':'openclaw-qwen38-ninfer.service'}))
            m.ROOT=root;commands=[]
            def fake_run(argv,**kwargs):
                commands.append(argv)
                if argv[:2]==['systemctl','is-active']:return subprocess.CompletedProcess(argv,0 if active else 3,stdout='active' if active else 'inactive',stderr='')
                if argv[0]=='nvidia-smi':return subprocess.CompletedProcess(argv,0,stdout=gpu_rows,stderr='')
                return subprocess.CompletedProcess(argv,0,stdout='',stderr='')
            child=MagicMock();child.wait.return_value=0;child.poll.return_value=0;child.pid=543210
            response=MagicMock();response.__enter__.return_value.read.return_value=b'{"data":[{"id":"openclaw/Qwen3.8-27B-WORK"}]}'
            args=['guard']+(['--allow-production-pause'] if allow else [])+['--','echo','test']
            with patch.object(sys,'argv',args),patch.dict(os.environ,{'XDG_RUNTIME_DIR':str(root/'run')}),patch.object(m,'run',fake_run),patch.object(m.subprocess,'Popen',return_value=child),patch.object(m.signal,'signal'),patch.object(m.urllib.request,'urlopen',return_value=response):
                rc=m.main()
            journal=json.loads((root/'.state/gpu-lease.json').read_text()) if (root/'.state/gpu-lease.json').exists() else {}
            return rc,commands,journal
    def test_active_requires_permission(self):
        rc,cmds,j=self.exercise();self.assertEqual(rc,78);self.assertFalse(any('stop' in x or 'start' in x for x in cmds))
    def test_inactive_does_not_start_production(self):
        rc,cmds,j=self.exercise(active=False);self.assertEqual(rc,0);self.assertFalse(any('start' in x for x in cmds))
    def test_unknown_gpu_process_is_not_killed(self):
        rc,cmds,j=self.exercise(allow=True,gpu_rows='99, unknown-process')
        self.assertEqual(rc,2);self.assertTrue(j['restored']);self.assertFalse(any('kill' in x for x in cmds))
    def test_authorized_pause_restores(self):
        rc,cmds,j=self.exercise(allow=True);self.assertEqual(rc,0);self.assertTrue(j['restored']);self.assertFalse(j['restore_required'])
    def test_unsettled_journal_blocks_new_work(self):
        rc,cmds,j=self.exercise(active=False,stale=True)
        self.assertEqual(rc,78);self.assertTrue(j['restore_required']);self.assertEqual(j['guard_pid'],1)

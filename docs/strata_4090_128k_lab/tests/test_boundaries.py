import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('boundary_test_runner',ROOT/'tools/combination/run_boundaries.py')
boundary=importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundary)
from boundary_memory import numeric_fields
import run_memory_pair


class BoundaryTests(unittest.TestCase):
    def test_engine_from_loader_thread_and_explicit_audit_are_included(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for pid,tid,children in ((100,100,''),(100,101,'200'),(200,200,'400')):
                folder=root/str(pid)/'task'/str(tid);folder.mkdir(parents=True,exist_ok=True)
                (folder/'children').write_text(children)
            server=types.SimpleNamespace(process=types.SimpleNamespace(pid=100),engine_audit=[{'pid':300}])
            self.assertEqual(run_memory_pair.owned_pids(server,root),[100,200,300,400])
            self.assertEqual(run_memory_pair.owned_pids(types.SimpleNamespace(process=None),root),[])

    def test_idle_uses_v1_activity_and_slots_not_metrics_live(self):
        import os
        responses=[]
        for busy in (True,False,False,False):
            responses += [{'loaded':True,'activity':{'in_flight':int(busy)}},[{'id':0,'is_processing':busy}]]
        with tempfile.TemporaryDirectory() as directory, patch.object(boundary.http,'get',side_effect=responses), patch.object(boundary.time,'sleep'):
            server=types.SimpleNamespace(base='http://127.0.0.1:1',key='test',engine_audit=[],abort_reason=None)
            boundary.wait_idle(server,directory,'cancel')
            data=json.loads((Path(directory)/'cancel.idle.json').read_text())
            self.assertEqual(len(data['samples']),4)
            self.assertEqual(data['samples'][-1]['status']['activity']['in_flight'],0)

    def test_idle_rejects_lost_engine_identity(self):
        responses=[]
        for _ in range(3):responses += [{'loaded':True,'activity':{'in_flight':0}},[{'is_processing':False}]]
        with tempfile.TemporaryDirectory() as directory, patch.object(boundary.http,'get',side_effect=responses), patch.object(boundary.time,'sleep'):
            server=types.SimpleNamespace(base='http://127.0.0.1:1',key='test',engine_audit=[{'pid':-1}],abort_reason=None)
            with self.assertRaisesRegex(RuntimeError,'ENGINE_RESTARTED_AFTER_CANCEL'):boundary.wait_idle(server,directory,'cancel')

    def test_memory_units_and_non_numeric_status_are_not_conflated(self):
        self.assertEqual(numeric_fields('VmRSS: 1024 kB\nThreads: 17\nName: strata\nVmPin: 0 kB\n'),
                         {'VmRSS_kib':1024,'Threads':17,'VmPin_kib':0})

    def test_prefill_cancel_requires_observed_partial_cold_prefill(self):
        def item(n,total=102400,cache=0):return {'prompt_progress':{'processed':n,'total':total,'cache':cache}}
        self.assertFalse(boundary.cancel_trigger('prefill',item(0),0))
        self.assertFalse(boundary.cancel_trigger('prefill',item(102400),0))
        self.assertFalse(boundary.cancel_trigger('prefill',item(16384,cache=100),0))
        self.assertFalse(boundary.cancel_trigger('prefill',item(16384),1))
        self.assertTrue(boundary.cancel_trigger('prefill',item(16384),0))

    def test_actual_cancel_history_keeps_partial_output(self):
        request={'messages':[{'role':'user','content':'count'}],'max_tokens':4096}
        returned=boundary.actual_followup(request,{'text':'1, 2,','reasoning':'partial reasoning'})
        self.assertEqual(returned['messages'][-2],{'role':'assistant','content':'1, 2,','reasoning_content':'partial reasoning'})
        self.assertEqual(request['messages'],[{'role':'user','content':'count'}])

    def test_usage_guard_rejects_drift_and_output_overrun(self):
        c={'max_context':131072,'safety_tokens':4096};request={'max_tokens':2048}
        boundary.audit_usage(request,{'usage':{'prompt_tokens':100000,'completion_tokens':2048}},100000,c)
        for usage in ({'prompt_tokens':100033,'completion_tokens':1}, {'prompt_tokens':100000,'completion_tokens':2049}, {'prompt_tokens':True,'completion_tokens':1}):
            with self.assertRaises(RuntimeError):boundary.audit_usage(request,{'usage':usage},100000,c)

    def test_cancel_socket_persists_partial_sse_and_releases_both_sides(self):
        for mode in ('prefill','decode'):
            closed=threading.Event()
            class Handler(BaseHTTPRequestHandler):
                def log_message(self,*_):pass
                def do_POST(self):
                    self.rfile.read(int(self.headers['Content-Length']))
                    self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                    try:
                        for i in range(1000):
                            body={'prompt_progress':{'processed':16384,'total':102400,'cache':0}} if mode=='prefill' else {'choices':[{'delta':{'content':'x'}}]}
                            self.wfile.write(('data: '+json.dumps(body)+'\n\n').encode());self.wfile.flush();time.sleep(.001)
                    except (BrokenPipeError,ConnectionResetError):closed.set()
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                with tempfile.TemporaryDirectory() as directory:
                    prefix=Path(directory)/mode
                    result=boundary.exchange(types.SimpleNamespace(base='http://127.0.0.1:'+str(server.server_port),key='test'),{'max_tokens':4096},prefix,mode,timeout=5)
                    self.assertTrue(result['client_cancel']['triggered'])
                    self.assertFalse(result['done'])
                    self.assertTrue(Path(str(prefix)+'.sse').read_bytes())
                    self.assertTrue(closed.wait(2))
            finally:
                server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()

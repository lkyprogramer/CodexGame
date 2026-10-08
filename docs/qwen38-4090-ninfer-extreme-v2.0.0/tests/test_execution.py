import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from tools.runner import validate_plan
from tools.remote_guard import restore_sequence

ROOT=Path(__file__).resolve().parents[1]

class ExecutionTests(unittest.TestCase):
    def test_stage_id_cannot_escape_output(self):
        d={'ready':True,'run_id':'r','budget_sec':30,'stages':[{'id':'../bad','argv':[sys.executable,'-V'],'cwd':'/tmp','timeout_sec':1,'required_evidence':['/tmp/a']}]}
        with self.assertRaises(ValueError):validate_plan(d)
    def test_empty_evidence_path_rejected(self):
        d={'ready':True,'run_id':'r','budget_sec':30,'stages':[{'id':'a','argv':[sys.executable,'-V'],'cwd':'/tmp','timeout_sec':1,'required_evidence':['']}]}
        with self.assertRaises(ValueError):validate_plan(d)
    def test_missing_executable_rejected_before_lease(self):
        d={'ready':True,'run_id':'r','budget_sec':30,'stages':[{'id':'a','argv':['/nonexistent/lab-adapter-4090'], 'cwd':'/tmp','timeout_sec':1,'required_evidence':['/tmp/report-not-existing-4090.json']}]}
        with self.assertRaises(ValueError):validate_plan(d)
    def test_stale_evidence_rejected_before_lease(self):
        with tempfile.TemporaryDirectory() as td:
            e=Path(td)/'prior.json';e.write_text('{}')
            d={'ready':True,'run_id':'r','budget_sec':30,'stages':[{'id':'a','argv':[sys.executable,'-V'],'cwd':td,'timeout_sec':1,'required_evidence':[str(e)]}]}
            with self.assertRaises(ValueError):validate_plan(d)
    def invoke(self, code, expected, timeout=10):
        with tempfile.TemporaryDirectory() as td:
            t=Path(td);e=t/'fresh.json'
            d={'ready':True,'run_id':'test_run','budget_sec':30,'stages':[{'id':'cpu','argv':[sys.executable,'-c',code,str(e)],'cwd':td,'timeout_sec':timeout,'required_evidence':[str(e)]}]}
            (t/'plan.json').write_text(json.dumps(d))
            r=subprocess.run([sys.executable,'-m','tools.runner',str(t/'plan.json'),'--out',str(t/'result')],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=20)
            summary=json.loads((t/'result/SUMMARY.json').read_text())
            self.assertEqual(summary['stages'][0]['status'],expected)
            return r,summary
    def test_fresh_evidence_is_not_qualification_pass(self):
        r,s=self.invoke('import pathlib,sys;pathlib.Path(sys.argv[1]).write_text("{}")','EVIDENCE_COLLECTED')
        self.assertEqual(r.returncode,0);self.assertEqual(s['verdict'],'REVIEW_REQUIRED')
    def test_missing_evidence_fails_closed(self):
        r,s=self.invoke('print("PASS")','INCOMPLETE')
        self.assertNotEqual(r.returncode,0);self.assertEqual(s['verdict'],'BLOCKED')
    def test_nonzero_even_with_evidence(self):
        r,s=self.invoke('import pathlib,sys;pathlib.Path(sys.argv[1]).write_text("{}");sys.exit(7)','COMMAND_FAILED')
        self.assertNotEqual(r.returncode,0)
    def test_timeout(self):
        r,s=self.invoke('import time;time.sleep(60)','TIMEOUT',1)
        self.assertNotEqual(r.returncode,0)

class RecoveryOrderTests(unittest.TestCase):
    def test_cleanup_failure_does_not_skip_restore(self):
        calls=[]
        def bad():calls.append('cleanup');raise RuntimeError('secret detail')
        errors=restore_sequence(bad,lambda:calls.append('restore'),lambda:calls.append('health'))
        self.assertEqual(calls,['cleanup','restore','health'])
        self.assertEqual(errors,['cleanup_failed'])
    def test_restore_failure_still_checks_health(self):
        calls=[]
        def bad():calls.append('restore');raise RuntimeError('failed')
        errors=restore_sequence(lambda:calls.append('cleanup'),bad,lambda:calls.append('health'))
        self.assertEqual(calls,['cleanup','restore','health']);self.assertEqual(errors,['restore_failed'])
    def test_success_order(self):
        calls=[]
        errors=restore_sequence(lambda:calls.append('cleanup'),lambda:calls.append('restore'),lambda:calls.append('health'))
        self.assertEqual(calls,['cleanup','restore','health']);self.assertEqual(errors,[])

if __name__=='__main__':unittest.main()

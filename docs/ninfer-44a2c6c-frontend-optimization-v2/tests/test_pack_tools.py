from __future__ import annotations
import copy, importlib, json, subprocess, tempfile, unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
def mod(name):
    try:return importlib.import_module(name)
    except ImportError:return None

class SummaryTests(unittest.TestCase):
    def setUp(self):self.m=mod('summarize_bench');self.assertIsNotNone(self.m,'paired summary not implemented')
    def row(self,mode='legacy',sec=20):return {'schema_version':2,'pair_id':'s-r1','session_id':'s','mode':mode,'input_sha256':'a'*64,'resources_sha256':'b'*64,'prompt_tokens':150000,'cache_kind':'none','cohort':'synthetic','tokenize_seconds':sec,'status':'ok','oracle_match':True}
    def test_pair(self):self.assertEqual(self.m.summarize([self.row(),self.row('b0-b1',.5)],'legacy','b0-b1')['metrics']['tokenize_seconds']['paired_median_saved_seconds'],19.5)
    def test_unknown_oracle_not_eligible(self):
        r=self.row('b0-b1');r['oracle_match']=None
        self.assertEqual(self.m.summarize([self.row(),r],'legacy','b0-b1')['performance_eligible_pairs'],0)
    def test_b0_build_lane(self):self.assertEqual(self.m.validate_row(self.row('b0'))['mode'],'b0')
    def test_incremental_not_active_lane(self):
        with self.assertRaises(ValueError):self.m.validate_row(self.row('incremental'))
    def test_nonfinite(self):
        for v in [True,-1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):self.m.validate_row(self.row(sec=v))
    def test_no_unknown_fields(self):
        r=self.row();r['mystery']=1
        with self.assertRaises(ValueError):self.m.validate_row(r)
    def test_unpaired(self):
        with self.assertRaises(ValueError):self.m.summarize([self.row()],'legacy','b0-b1')
    def test_different_input(self):
        r=self.row('b0-b1');r['input_sha256']='c'*64
        with self.assertRaises(ValueError):self.m.summarize([self.row(),r],'legacy','b0-b1')
    def test_missing_optional_ttft(self):self.assertEqual(self.m.summarize([self.row(),self.row('b0-b1')],'legacy','b0-b1')['metrics']['ttft_seconds']['complete_pairs'],0)
    def test_failure_preserved(self):
        r=self.row('b0-b1');r['status']='error';r['tokenize_seconds']=None;r['oracle_match']=False
        o=self.m.summarize([self.row(),r],'legacy','b0-b1');self.assertEqual(o['semantic_mismatch_records'],1);self.assertEqual(o['performance_eligible_pairs'],0)

class PinTests(unittest.TestCase):
    def setUp(self):self.m=mod('check_source_pin');self.assertIsNotNone(self.m,'source-lock verification not implemented')
    def test_missing_repo(self):self.assertEqual(self.m.check(Path('/nonexistent/ninfer-repo'),{'base_commit':'a'*40})['status'],'FAIL')
    def test_local_source_and_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            def git(*a):return subprocess.run(['git','-C',str(p),*a],check=True,capture_output=True,text=True).stdout.strip()
            git('init','-q');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid')
            (p/'x.txt').write_text('a\nb\n');git('add','x.txt');git('commit','-qm','fixture')
            sha=git('rev-parse','HEAD');blob=git('rev-parse',sha+':x.txt');lock={'base_commit':sha,'subject':'fixture','files':[{'path':'x.txt','git_blob_sha':blob,'line_start':1,'line_end':2}]}
            self.assertEqual(self.m.check(p,lock)['status'],'PASS');lock['files'][0]['line_end']=3
            self.assertEqual(self.m.check(p,lock)['status'],'FAIL')

class CalibrationTests(unittest.TestCase):
    def setUp(self):self.m=mod('calibrate_fixtures');self.assertIsNotNone(self.m,'fixture measurement validator not implemented')
    def rows(self):
        a={'case_id':'x','input_sha256':'a'*64}
        b={'case_id':'x','input_sha256':'a'*64,'resources_sha256':'b'*64,'prompt_tokens':245194,'render_bytes':889726,'checkpoint_hints':22,'boundary_queries':25}
        return a,b
    def test_safe_http(self):
        a,b=self.rows();self.assertTrue(self.m.calibrate([a],[b],2048)['cases'][0]['http_eligible'])
    def test_too_deep(self):
        a,b=self.rows();b['prompt_tokens']=273012;self.assertFalse(self.m.calibrate([a],[b],2048)['cases'][0]['http_eligible'])
    def test_missing_measurement(self):
        a,b=self.rows()
        with self.assertRaises(ValueError):self.m.calibrate([a],[],2048)
    def test_hash_mismatch(self):
        a,b=self.rows();b['input_sha256']='c'*64
        with self.assertRaises(ValueError):self.m.calibrate([a],[b],2048)

class PackTests(unittest.TestCase):
    def setUp(self):self.m=mod('validate_pack');self.assertIsNotNone(self.m,'pack consistency checker not implemented')
    def test_cycle(self):self.assertTrue(self.m.dag_errors([{'id':'A','dependencies':['B']},{'id':'B','dependencies':['A']}]))
    def test_no_cycle(self):self.assertFalse(self.m.dag_errors([{'id':'A','dependencies':[]},{'id':'B','dependencies':['A']}]))
    def test_bad_link(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'a.md').write_text('[broken](b.md)\n[external](https://example.invalid)\n')
            self.assertEqual(len(self.m.check_links(p)),1)
if __name__=='__main__':unittest.main()

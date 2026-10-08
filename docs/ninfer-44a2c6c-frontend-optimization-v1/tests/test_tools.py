"""Tests for documentation helpers only; these are not NInfer/GPU tests."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name, ROOT/'tools'/f'{name}.py')
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

class SummaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load('summarize_bench')
    def row(self, mode='legacy', t=20.0, pair='p1', **kw):
        d=dict(schema_version=1,pair_id=pair,session_id='s1',mode=mode,input_sha256='a'*64,
               resources_sha256='b'*64,prompt_tokens=150000,cache_kind='warm',cohort='synthetic',
               tokenize_seconds=t,status='ok',oracle_match=True)
        d.update(kw); return d
    def test_quantile_interpolation(self):
        self.assertEqual(self.m.quantile([0,10],.5),5)
        self.assertEqual(self.m.quantile([0,10],.9),9)
        self.assertIsNone(self.m.quantile([],.5))
    def test_paired_savings(self):
        r=self.m.summarize([self.row(),self.row('single-pass',1)],'legacy','single-pass')
        self.assertEqual(r['paired_total'],1)
        self.assertEqual(r['metrics']['tokenize_seconds']['paired_median_saved_seconds'],19)
        self.assertEqual(r['metrics']['ttft_seconds']['complete_pairs'],0)
        self.assertEqual(r['status'],'ANALYSIS_ONLY')
    def test_missing_metric_not_zero(self):
        d=self.row();del d['tokenize_seconds']
        with self.assertRaises(ValueError):self.m.validate_row(d)
    def test_nonfinite_and_bool_rejected(self):
        for v in [float('nan'),float('inf'),True,-1]:
            with self.subTest(v=v):
                with self.assertRaises(ValueError):self.m.validate_row(self.row(t=v))
    def test_failed_request_missing_measurement(self):
        self.assertIsNone(self.m.validate_row(self.row(t=None,status='cancelled'))['tokenize_seconds'])
        with self.assertRaises(ValueError):self.m.validate_row(self.row(t=None))
    def test_unknown_field_rejected(self):
        with self.assertRaises(ValueError):self.m.validate_row(self.row(unmapped_metric=3))
    def test_hash_mismatch_rejected(self):
        with self.assertRaises(ValueError):self.m.summarize([self.row(),self.row('single-pass',1,input_sha256='c'*64)],'legacy','single-pass')
    def test_duplicate_and_unpaired_rejected(self):
        with self.assertRaises(ValueError):self.m.summarize([self.row(),self.row()],'legacy','single-pass')
        with self.assertRaises(ValueError):self.m.summarize([self.row()],'legacy','single-pass')
    def test_failure_not_erased(self):
        r=self.m.summarize([self.row(),self.row('single-pass',1,status='error',oracle_match=False)],'legacy','single-pass')
        self.assertEqual(r['paired_total'],1)
        self.assertEqual(r['performance_eligible_pairs'],0)
        self.assertEqual(r['semantic_mismatch_records'],1)
        self.assertEqual(r['status_counts']['single-pass']['error'],1)
    def test_zero_baseline_ratio_null(self):
        r=self.m.summarize([self.row(t=0),self.row('single-pass',0)],'legacy','single-pass')
        self.assertIsNone(r['metrics']['tokenize_seconds']['paired_median_speedup'])
    def test_session_and_cohort_must_match(self):
        for kw in [dict(session_id='other'),dict(cohort='live'),dict(cache_kind='cold')]:
            with self.subTest(kw=kw):
                with self.assertRaises(ValueError):self.m.summarize([self.row(),self.row('single-pass',1,**kw)],'legacy','single-pass')
    def test_strata_are_separate(self):
        rows=[self.row(),self.row('single-pass',1),self.row(pair='p2',prompt_tokens=1000),self.row('single-pass',.01,pair='p2',prompt_tokens=1000)]
        r=self.m.summarize(rows,'legacy','single-pass')
        self.assertEqual(len(r['strata']),2)

class PackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load('validate_pack')
    def test_links_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'a.md').write_text('[broken](missing.md)\n[web](https://example.invalid)\n',encoding='utf-8')
            self.assertEqual(len(self.m.check_links(p)),1)
    def test_task_cycle_rejected(self):
        self.assertTrue(self.m.dag_errors([{'id':'A','dependencies':['B']},{'id':'B','dependencies':['A']}]))
        self.assertFalse(self.m.dag_errors([{'id':'A','dependencies':[]},{'id':'B','dependencies':['A']}]))
    def test_pack_valid(self):
        r=self.m.validate(ROOT,verify_checksums=False)
        self.assertEqual(r['status'],'PASS',r['errors'])

class PinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load('check_source_pin')
    def test_missing_repo_is_failure(self):
        r=self.m.check(Path('/nonexistent/repository'),{'commit':'a'*40,'subject':'x','sources':[]})
        self.assertEqual(r['status'],'FAIL')
    def test_local_git_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            def git(*a):
                return subprocess.run(['git','-C',str(p),*a],capture_output=True,text=True,check=True).stdout.strip()
            git('init','-q');git('config','user.name','Test');git('config','user.email','test@example.invalid')
            (p/'a.txt').write_text('baseline\n',encoding='utf-8');git('add','a.txt');git('commit','-qm','base')
            sha=git('rev-parse','HEAD');blob=git('rev-parse',sha+':a.txt')
            lock={'commit':sha,'subject':'base','sources':[{'path':'a.txt','blob_sha':blob}]}
            self.assertEqual(self.m.check(p,lock)['status'],'PASS')
            file_lock={'base_commit':sha,'subject':'base','files':[{'path':'a.txt','git_blob_sha':blob}]}
            self.assertEqual(self.m.check(p,file_lock)['checked_unique_blobs'],1)
            bad=copy.deepcopy(lock);bad['sources'][0]['blob_sha']='0'*40
            self.assertEqual(self.m.check(p,bad)['status'],'FAIL')

class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load('generate_sessions')
    def test_deterministic_and_message_count(self):
        recipe={'recipe_id':'small','seed':1,'target_token_hint':100,'target_message_count':12,'approx_chars_per_token':3.3,'turn_additions':2,'suffix_chars':30}
        a=self.m.generate(recipe);b=self.m.generate(recipe)
        self.assertEqual(a,b)
        self.assertEqual(len(a[0]['request']['messages']),12)
        self.assertEqual(a[0]['token_count_status'],'UNMEASURED')
        self.assertEqual(len(a),3)
        self.assertEqual(a[0]['request']['messages'][-1]['role'],'tool')
        odd=dict(recipe,target_message_count=13)
        o=self.m.generate(odd)
        self.assertEqual(len(o[0]['request']['messages']),13)
        self.assertEqual(o[0]['request']['messages'][-1]['role'],'tool')
        self.assertEqual(sum(m['role']=='user' for m in o[-1]['request']['messages']),1)
        for x,y in zip(a,a[1:]):
            self.assertEqual(y['request']['messages'][:len(x['request']['messages'])],x['request']['messages'])
    def test_bad_recipe(self):
        with self.assertRaises(ValueError):self.m.generate({'recipe_id':'bad','target_message_count':1})

if __name__=='__main__':unittest.main(verbosity=2)

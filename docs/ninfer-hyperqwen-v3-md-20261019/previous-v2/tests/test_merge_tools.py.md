# V2 支撑材料：`tests/test_merge_tools.py`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: tests/test_merge_tools.py -->
<!-- payload-sha256: e5a23234f3a607b571912e8b067c30e6938b809ff674037f9681af1f183b278c -->
<!-- payload-bytes: 7878 -->

<!-- payload-begin -->
````python
"""CPU-only checks of the delivered audit utilities, not NInfer/CUDA tests."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

def load_tools(test):
    source = ROOT / 'scripts' / 'merge_tools.py'
    test.assertTrue(source.exists(), 'audit utilities have not been implemented')
    spec = importlib.util.spec_from_file_location('merge_tools', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class UtilityTests(unittest.TestCase):
    def setUp(self): self.m = load_tools(self)
    def test_plan_accepts_dag(self):
        self.assertEqual(self.m.validate_dag([{'id':'A','depends_on':[]},{'id':'B','depends_on':['A']}]), ['A','B'])
    def test_plan_rejects_cycle(self):
        with self.assertRaises(ValueError): self.m.validate_dag([{'id':'A','depends_on':['B']},{'id':'B','depends_on':['A']}])
    def test_plan_rejects_missing_dependency(self):
        with self.assertRaises(ValueError): self.m.validate_dag([{'id':'A','depends_on':['missing']}])
    def test_plan_rejects_duplicate_id(self):
        with self.assertRaises(ValueError): self.m.validate_dag([{'id':'A','depends_on':[]},{'id':'A','depends_on':[]}])
    def check_xml(self, text, required):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'tests.xml';p.write_text(text)
            return self.m.check_junit(p, required)
    def test_junit_pass(self):
        self.assertTrue(self.check_xml('<testsuite><testcase name="sm89"/></testsuite>', ['^sm89$'])['passed'])
    def test_junit_no_tests_is_not_pass(self):
        self.assertFalse(self.check_xml('<testsuite/>', ['sm89'])['passed'])
    def test_junit_missing_required_is_not_pass(self):
        self.assertFalse(self.check_xml('<testsuite><testcase name="other"/></testsuite>', ['sm89'])['passed'])
    def test_junit_required_skip_is_not_pass(self):
        r=self.check_xml('<testsuite><testcase name="sm89"><skipped/></testcase></testsuite>', ['sm89'])
        self.assertFalse(r['passed']);self.assertEqual(r['required_skipped'], ['sm89'])
    def test_junit_failure_is_not_pass(self):
        self.assertFalse(self.check_xml('<testsuite><testcase name="sm89"><failure>bad</failure></testcase></testsuite>', ['sm89'])['passed'])
    def test_junit_optional_skip_allowed(self):
        self.assertTrue(self.check_xml('<testsuite><testcase name="sm89"/><testcase name="nvfp4"><skipped/></testcase></testsuite>', ['^sm89$'])['passed'])
    def test_junit_duplicate_rejected(self):
        self.assertFalse(self.check_xml('<testsuite><testcase name="sm89"/><testcase name="sm89"/></testsuite>', ['sm89'])['passed'])
    def test_redacts_both_argument_styles(self):
        self.assertEqual(self.m.redact_argv(['serve','--api-key','secret','--token=secret','--port','8080']), ['serve','--api-key','<redacted>','--token=<redacted>','--port','8080'])
    def test_redaction_preserves_token_count_configuration(self):
        argv=['serve','--draft-tokens','3','--max-tokens=32768','--tokenizer-json','vocab.json','--auth-token','secret']
        self.assertEqual(self.m.redact_argv(argv),argv[:-1]+['<redacted>'])
    def test_metrics_detects_latency_regression(self):
        b=[{'case_id':'x','repeat':i,'metrics':{'ttft_seconds':1.0,'decode_tok_s':100.0,'prepare_seconds':0.1}} for i in range(10)]
        c=[{'case_id':'x','repeat':i,'metrics':{'ttft_seconds':1.2,'decode_tok_s':100.0,'prepare_seconds':0.1}} for i in range(10)]
        self.assertFalse(self.m.compare_samples(b,c)['passed'])
    def test_metrics_good_samples_pass(self):
        b=[{'case_id':'x','repeat':i,'metrics':{'ttft_seconds':1.0,'decode_tok_s':100.0,'prepare_seconds':0.1}} for i in range(10)]
        self.assertTrue(self.m.compare_samples(b,b)['passed'])
    def test_metrics_underpowered_is_blocked(self):
        b=[{'case_id':'x','repeat':0,'metrics':{'ttft_seconds':1.,'decode_tok_s':100.,'prepare_seconds':.1}}]
        self.assertFalse(self.m.compare_samples(b,b)['passed'])
    def test_metrics_duplicate_is_rejected(self):
        b=[{'case_id':'x','repeat':0,'metrics':{'ttft_seconds':1.,'decode_tok_s':100.,'prepare_seconds':.1}}]*10
        with self.assertRaises(ValueError): self.m.compare_samples(b,b)
    def test_metrics_mismatched_cases_rejected(self):
        b=[{'case_id':'x','repeat':i,'metrics':{'ttft_seconds':1.,'decode_tok_s':100.,'prepare_seconds':.1}} for i in range(10)]
        c=[dict(row,case_id='y') for row in b]
        with self.assertRaises(ValueError): self.m.compare_samples(b,c)
    def test_metrics_nan_rejected(self):
        b=[{'case_id':'x','repeat':i,'metrics':{'ttft_seconds':float('nan'),'decode_tok_s':100.,'prepare_seconds':.1}} for i in range(10)]
        with self.assertRaises(ValueError): self.m.compare_samples(b,b)
    def test_metrics_zero_prepare_uses_absolute_budget(self):
        b=[{'case_id':'x','repeat':i,'metrics':{'ttft_seconds':1.,'decode_tok_s':100.,'prepare_seconds':0.}} for i in range(10)]
        c=[{'case_id':'x','repeat':i,'metrics':{'ttft_seconds':1.,'decode_tok_s':100.,'prepare_seconds':0.0001}} for i in range(10)]
        self.assertTrue(self.m.compare_samples(b,c)['passed'])
    def test_git_probe_isolated_and_conflict_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            parent=Path(d);repo=parent/'repo';repo.mkdir()
            def git(*args):
                r=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True,check=True)
                return r.stdout.strip()
            git('init','-b','main');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid')
            (repo/'same.cpp').write_text('base\n');git('add','.');git('commit','-m','base');base=git('rev-parse','HEAD')
            git('checkout','-b','ours');(repo/'same.cpp').write_text('ours\n');git('add','.');git('commit','-m','ours');ours=git('rev-parse','HEAD')
            git('checkout','-b','upstream',base);(repo/'same.cpp').write_text('upstream\n');git('add','.');git('commit','-m','upstream');upstream=git('rev-parse','HEAD');git('checkout','ours')
            before=(git('rev-parse','HEAD'),git('status','--porcelain'),(repo/'same.cpp').read_bytes())
            report=self.m.audit_repository(repo, {'base':base,'ours':ours,'upstream':upstream,'expected_ours_unique_commits':1,'expected_upstream_unique_commits':1},parent/'audit',True)
            self.assertEqual(report['merge_probe']['conflict_files'], ['same.cpp'])
            self.assertEqual(report['both_sides_touched'], ['same.cpp'])
            after=(git('rev-parse','HEAD'),git('status','--porcelain'),(repo/'same.cpp').read_bytes())
            self.assertEqual(before,after)
            self.assertTrue((parent/'audit'/'merge-probe.txt').exists())
    def test_phase_evidence_requires_real_files(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            plan={'tasks':[{'id':'P0-T01','phase':'P0','depends_on':[]}], 'phases':[{'id':'P0','gpu_required':False}]}
            e={'phase':'P0','source_commit':'a'*40,'tasks':[{'id':'P0-T01','status':'PASS'}], 'review':{'status':'PASS','reviewer':'review-agent'}, 'checks':[{'kind':'manual','status':'PASS','evidence':'missing.txt'}]}
            self.assertFalse(self.m.check_phase(plan,e,p)['passed'])
    def test_phase_evidence_pending_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            plan={'tasks':[{'id':'P0-T01','phase':'P0','depends_on':[]}], 'phases':[{'id':'P0','gpu_required':False}]}
            e={'phase':'P0','source_commit':'a'*40,'tasks':[{'id':'P0-T01','status':'PENDING'}], 'review':{'status':'PENDING'},'checks':[]}
            self.assertFalse(self.m.check_phase(plan,e,Path(d))['passed'])

if __name__=='__main__': unittest.main(verbosity=2)
````
<!-- payload-end -->

# V2 支撑材料：`tests/test_strict_gate.py`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: tests/test_strict_gate.py -->
<!-- payload-sha256: 6c06a422077d7616af2038ea4e9eb8d01dd3dc187abe0bca050672e7c94abfc2 -->
<!-- payload-bytes: 2975 -->

<!-- payload-begin -->
````python
"""Fail-closed evidence binding tests; synthetic fixtures, never GPU qualification."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('merge_tools',ROOT/'scripts/merge_tools.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class StrictGateTests(unittest.TestCase):
    def fixture(self,root):
        p=root/'raw.xml';p.write_text('<testsuite><testcase name="must_run"/></testsuite>')
        plan={'strict_evidence':True,'tasks':[{'id':'P0-T01','phase':'P0','depends_on':[]}],
              'phases':[{'id':'P0','gpu_required':True,'required_checks':[{'id':'gpu','kind':'junit','required_patterns':['^must_run$']}]}]}
        e={'phase':'P0','source_commit':'a'*40,'tasks':[{'id':'P0-T01','status':'PASS','commit':'a'*40}],
           'review':{'status':'PASS','reviewer':'reviewer','reviewed_commit':'a'*40},
           'checks':[{'id':'gpu','kind':'junit','status':'PASS','source_commit':'a'*40,'evidence':'raw.xml','sha256':m.sha256_file(p),'required_patterns':['^must_run$']}],
           'gpu':{'executed':True,'uuid':'GPU-fixture','model_sha256':'b'*64}}
        return plan,e
    def evaluate(self,mutator=None):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);plan,e=self.fixture(root)
            if mutator:mutator(plan,e,root)
            return m.check_phase(plan,e,root)
    def test_complete_synthetic_evidence_passes(self):self.assertTrue(self.evaluate()['passed'])
    def test_review_other_commit_rejected(self):
        self.assertFalse(self.evaluate(lambda p,e,r:e['review'].update(reviewed_commit='c'*40))['passed'])
    def test_required_check_cannot_be_renamed_away(self):
        self.assertFalse(self.evaluate(lambda p,e,r:e['checks'][0].update(id='unrelated'))['passed'])
    def test_required_kind_cannot_be_downgraded(self):
        self.assertFalse(self.evaluate(lambda p,e,r:e['checks'][0].update(kind='manual'))['passed'])
    def test_check_other_commit_rejected(self):
        self.assertFalse(self.evaluate(lambda p,e,r:e['checks'][0].update(source_commit='c'*40))['passed'])
    def test_required_patterns_owned_by_plan_not_report(self):
        def mutate(p,e,r):
            f=r/'raw.xml';f.write_text('<testsuite><testcase name="different"/></testsuite>')
            e['checks'][0].update(required_patterns=[],sha256=m.sha256_file(f))
        self.assertFalse(self.evaluate(mutate)['passed'])
    def test_task_commit_missing_rejected(self):
        self.assertFalse(self.evaluate(lambda p,e,r:e['tasks'][0].pop('commit'))['passed'])
    def test_invalid_model_hash_rejected(self):
        self.assertFalse(self.evaluate(lambda p,e,r:e['gpu'].update(model_sha256='not-a-hash'))['passed'])
    def test_duplicate_check_rejected(self):
        self.assertFalse(self.evaluate(lambda p,e,r:e['checks'].append(dict(e['checks'][0])))['passed'])
if __name__=='__main__':unittest.main()
````
<!-- payload-end -->

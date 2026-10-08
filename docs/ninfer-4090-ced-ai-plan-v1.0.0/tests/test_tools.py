import json
import tempfile
import unittest
from pathlib import Path
from tools import budget, planctl, validate_package

ROOT = Path(__file__).resolve().parents[1]

class BudgetTests(unittest.TestCase):
    def test_ced16_labels(self):
        self.assertEqual(budget.estimate(48,256,100000)['bytes_per_labeled_token'],287232)
    def test_ced16_layer_counts(self):
        x=budget.estimate(48,256,1)
        self.assertEqual((x['gdn_layers'],x['attention_layers']),(12,4))
    def test_ced24_layer_counts(self):
        x=budget.estimate(40,256,1)
        self.assertEqual((x['gdn_layers'],x['attention_layers']),(18,6))
    def test_ced32_layer_counts(self):
        x=budget.estimate(32,256,1)
        self.assertEqual((x['gdn_layers'],x['attention_layers']),(24,8))
    def test_rank_parameter_growth(self):
        self.assertGreater(budget.estimate(48,512,1)['parameters'],budget.estimate(48,128,1)['parameters'])
    def test_token_bytes_linear(self):
        self.assertEqual(budget.estimate(48,256,2)['label_bytes'],2*budget.estimate(48,256,1)['label_bytes'])
    def test_invalid_split(self):
        with self.assertRaises(ValueError): budget.estimate(47,256,1)
    def test_invalid_rank(self):
        with self.assertRaises(ValueError): budget.estimate(48,0,1)
    def test_invalid_tokens(self):
        with self.assertRaises(ValueError): budget.estimate(48,256,-1)

class GraphTests(unittest.TestCase):
    def test_real_graph(self):
        p=planctl.load_plan(ROOT)
        self.assertEqual(len(p['phases']),9)
        self.assertEqual(validate_package.check_graph(p['tasks']),[])
    def test_duplicate_task(self):
        t=[{'id':'a','depends_on':[]},{'id':'a','depends_on':[]}]
        self.assertTrue(validate_package.check_graph(t))
    def test_missing_dependency(self):
        self.assertTrue(validate_package.check_graph([{'id':'a','depends_on':['b']}]))
    def test_cycle(self):
        self.assertTrue(validate_package.check_graph([{'id':'a','depends_on':['b']},{'id':'b','depends_on':['a']}]))
    def test_initial_ready(self):
        p=planctl.load_plan(ROOT)
        self.assertEqual([x['id'] for x in planctl.ready_tasks(p,{})],['P0-T01'])
    def test_dependency_unlocked(self):
        p=planctl.load_plan(ROOT)
        ready={t['id'] for t in planctl.ready_tasks(p,{'P0-T01':'PASS'})}
        self.assertTrue({'P0-T02','P0-T03','P0-T04'} <= ready)
    def test_failed_dependency_stays_blocked(self):
        p=planctl.load_plan(ROOT)
        self.assertNotIn('P0-T02',[t['id'] for t in planctl.ready_tasks(p,{'P0-T01':'FAIL'})])
    def test_optional_default_excluded(self):
        p=planctl.load_plan(ROOT)
        self.assertNotIn('P7-T01',[t['id'] for t in planctl.ready_tasks(p,{'P6-G':'PASS'})])
    def test_optional_included(self):
        p=planctl.load_plan(ROOT)
        self.assertIn('P7-T01',[t['id'] for t in planctl.ready_tasks(p,{'P6-G':'PASS'},True)])
    def test_subgate_required(self):
        p=planctl.load_plan(ROOT)
        self.assertNotIn('P7-T03',[t['id'] for t in planctl.ready_tasks(p,{'P7-T02':'PASS'},True)])
    def test_subgate_unlocks(self):
        p=planctl.load_plan(ROOT)
        self.assertIn('P7-T03',[t['id'] for t in planctl.ready_tasks(p,{'P7-T02':'PASS'},True,{'P7A':'PASS'})])

class PackageTests(unittest.TestCase):
    def test_json_all_loads(self):
        for f in ROOT.rglob('*.json'):
            with self.subTest(file=str(f)): json.loads(f.read_text(encoding='utf-8'))
    def test_all_engine_tasks_not_run(self):
        p=planctl.load_plan(ROOT)
        self.assertTrue(all(t['status']=='NOT_RUN' for t in p['tasks']))
    def test_production_safety_default(self):
        x=json.loads((ROOT/'configs/experiment.json').read_text())
        self.assertFalse(x['production']['allow_production_pause'])
        self.assertFalse(x['production']['auto_enable_lsp'])
    def test_package_structure(self):
        self.assertEqual(validate_package.validate(ROOT),[])

if __name__=='__main__': unittest.main()

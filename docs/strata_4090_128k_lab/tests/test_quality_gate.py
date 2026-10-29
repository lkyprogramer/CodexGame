import copy
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE=Path(__file__).resolve().parents[1]/'tools/quality_gate.py'


def dataset(n,b=0,c=0,d=0):
    ids=[f'task-{i:04d}' for i in range(n)]
    rows=[]
    for i,task_id in enumerate(ids):
        baseline,candidate=(True,False) if i<b else (False,True) if i<b+c else (False,False) if i<b+c+d else (True,True)
        rows.append({'task_id':task_id,'baseline_success':baseline,'candidate_success':candidate,
                     'run_valid':True,'failure_kind':'none' if baseline and candidate else 'model_oracle'})
    return {'schema_version':1,
            'preregistration':{'task_ids':ids,'margin':.02,'unit':'independent_task','aggregation':'one_pair_per_task'},
            'pairs':rows}


class QualityGateTests(unittest.TestCase):
    def module(self):
        self.assertTrue(MODULE.is_file(),'Formal offline quality gate must exist')
        spec=importlib.util.spec_from_file_location('strata_quality_gate',MODULE)
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        return mod

    def test_binomial_cdf_matches_exact_small_probabilities(self):
        m=self.module()
        self.assertAlmostEqual(m.binomial_cdf(1,4,.25),189/256,places=14)
        self.assertAlmostEqual(m.binomial_cdf(2,4,.25),243/256,places=14)
        self.assertEqual(m.binomial_cdf(-1,4,.25),0)
        self.assertEqual(m.binomial_cdf(4,4,.25),1)

    def test_cp_n1_and_n2_exact_boundary_values(self):
        m=self.module()
        self.assertEqual(m.lower_cp(0,1),0)
        self.assertAlmostEqual(m.upper_cp(0,1),.975,places=14)
        self.assertAlmostEqual(m.lower_cp(1,1),.025,places=14)
        self.assertEqual(m.upper_cp(1,1),1)
        self.assertAlmostEqual(m.lower_cp(1,2),.01257911709342507,places=12)
        self.assertAlmostEqual(m.upper_cp(1,2),.9874208829065749,places=12)

    def test_large_n_small_tail_does_not_underflow_incorrectly(self):
        m=self.module();n=10000;p=.0001
        expected=sum(math.comb(n,k)*p**k*(1-p)**(n-k) for k in range(3))
        self.assertAlmostEqual(m.binomial_cdf(2,n,p),expected,places=11)
        self.assertGreater(m.upper_cp(0,10000),0)

    def test_thirty_concordant_tasks_do_not_establish_two_percent_ni(self):
        report=self.module().evaluate(dataset(30))
        self.assertEqual(report['status'],'NONINFERIORITY_NOT_ESTABLISHED')
        self.assertGreater(report['inference']['upper_harm'],.02)

    def test_zero_discordance_threshold_182_183_and_184(self):
        m=self.module()
        self.assertEqual(m.evaluate(dataset(182))['status'],'NONINFERIORITY_NOT_ESTABLISHED')
        self.assertEqual(m.evaluate(dataset(183))['status'],'NONINFERIORITY_ESTABLISHED')
        self.assertEqual(m.evaluate(dataset(184))['status'],'NONINFERIORITY_ESTABLISHED')

    def test_full_four_cell_table_keeps_model_oracle_failures(self):
        result=self.module().evaluate(dataset(5,b=1,c=1,d=1))
        self.assertEqual(result['paired_outcome_table'],{'both_success':2,'baseline_only_success':1,
                                                      'candidate_only_success':1,'both_fail':1})
        self.assertEqual(result['n_valid_pairs'],5)
        self.assertEqual(result['errors'],[])

    def test_task_budget_exhaustion_is_valid_candidate_failure(self):
        data=dataset(10,b=1);data['pairs'][0]['failure_kind']='task_budget_exhausted'
        result=self.module().evaluate(data)
        self.assertEqual(result['n_valid_pairs'],10)
        self.assertEqual(result['paired_outcome_table']['baseline_only_success'],1)
        self.assertEqual(result['errors'],[])

    def test_infrastructure_failures_invalidate_whole_gate(self):
        m=self.module()
        for kind in ('infrastructure','infrastructure_timeout'):
            with self.subTest(kind=kind):
                data=dataset(184,b=1);data['pairs'][0]['failure_kind']=kind
                result=m.evaluate(data)
                self.assertEqual(result['status'],'INVALID_EXPERIMENT')
                self.assertIsNone(result['inference'])

    def test_oom_and_crash_are_hard_rejects(self):
        m=self.module()
        for kind in ('oom','crash'):
            with self.subTest(kind=kind):
                data=dataset(184,b=1);data['pairs'][0]['failure_kind']=kind
                result=m.evaluate(data)
                self.assertEqual(result['status'],'HARD_REJECT')
                self.assertIsNone(result['inference'])

    def test_missing_task_cannot_pass_using_183_surviving_pairs(self):
        data=dataset(184);data['pairs'].pop()
        result=self.module().evaluate(data)
        self.assertEqual(result['status'],'INVALID_EXPERIMENT')
        self.assertIsNone(result['inference'])

    def test_duplicate_task_seeds_do_not_increase_independent_n(self):
        data=dataset(184);data['pairs'].append(copy.deepcopy(data['pairs'][0]))
        result=self.module().evaluate(data)
        self.assertEqual(result['status'],'INVALID_EXPERIMENT')
        self.assertTrue(any('duplicate' in error.lower() for error in result['errors']))

    def test_nonboolean_success_and_invalid_run_are_rejected(self):
        m=self.module()
        for field,value in [('candidate_success',1),('run_valid',False)]:
            with self.subTest(field=field):
                data=dataset(184);data['pairs'][0][field]=value
                self.assertEqual(m.evaluate(data)['status'],'INVALID_EXPERIMENT')

    def test_seed_rows_require_preaggregation_before_input(self):
        data=dataset(184);data['pairs'][0]['seed']=7
        result=self.module().evaluate(data)
        self.assertEqual(result['status'],'INVALID_EXPERIMENT')

    def test_relative_ni_does_not_assert_absolute_quality_or_release(self):
        result=self.module().evaluate(dataset(184,d=184))
        self.assertEqual(result['status'],'NONINFERIORITY_ESTABLISHED')
        self.assertEqual(result['candidate_success_rate'],0)
        self.assertEqual(result['absolute_quality_gate'],'NOT_EVALUATED')
        self.assertFalse(result['deployment_approved'])

    def test_cli_smoke_emits_table_and_nonpassing_exit_code(self):
        self.module()
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'input.json';output=Path(t)/'output.json'
            path.write_text(json.dumps(dataset(30)))
            run=subprocess.run([sys.executable,'-B',str(MODULE),'--input',str(path),'--output',str(output)],capture_output=True,text=True)
            self.assertEqual(run.returncode,1,run.stderr)
            self.assertEqual(json.loads(output.read_text())['paired_outcome_table']['both_success'],30)

    def test_cli_rejects_nonfinite_numeric_overflow_as_invalid_input(self):
        self.module()
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'input.json'
            raw=json.dumps(dataset(1)).replace('"task_id": "task-0000"','"task_id": 1e999')
            path.write_text(raw)
            run=subprocess.run([sys.executable,'-B',str(MODULE),'--input',str(path)],capture_output=True,text=True)
            self.assertEqual(run.returncode,2,run.stderr)
            self.assertEqual(json.loads(run.stdout)['status'],'INVALID_INPUT')

import unittest, math
from tools.metrics import candidate_gate,aggregate_rounds,paired_summary
class NegativeTests(unittest.TestCase):
 def good(self):return dict(quality_pass=True,state_pass=True,sampling_pass=True,artifact_pass=True,paired_gain_lcb=.12,paired_n=8,aa_noise_abs=.01,task_wall_ratio=.85,capacity=200192,headroom_mib=800,ooms=0,heldout_complete=True,measurement_complete=True)
 def test_nan_gain(self):
  d=self.good();d['paired_gain_lcb']=float('nan');self.assertEqual(candidate_gate(d)['verdict'],'BLOCKED')
 def test_inf_headroom(self):
  d=self.good();d['headroom_mib']=float('inf');self.assertEqual(candidate_gate(d)['verdict'],'BLOCKED')
 def test_string_true(self):
  d=self.good();d['quality_pass']='true';self.assertEqual(candidate_gate(d)['verdict'],'BLOCKED')
 def test_negative_oom(self):
  d=self.good();d['ooms']=-1;self.assertEqual(candidate_gate(d)['verdict'],'BLOCKED')
 def test_insufficient_gain(self):
  d=self.good();d['paired_gain_lcb']=.01;self.assertEqual(candidate_gate(d)['verdict'],'NO_MEASURABLE_PRODUCT_GAIN')
 def test_oom(self):
  d=self.good();d['ooms']=1;self.assertEqual(candidate_gate(d)['verdict'],'NO_GO')
 def test_abort_record_invalid_as_completed_round(self):
  with self.assertRaises(ValueError):aggregate_rounds([dict(proposed=3,accepted=0,licensed=0,committed=0,round_ms=10)])
 def test_ci_invalid(self):
  with self.assertRaises(ValueError):paired_summary([1,2,float('nan')],[1,2,3])
if __name__=='__main__':unittest.main()

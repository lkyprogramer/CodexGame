import copy,json,tempfile,unittest
from pathlib import Path
from lab.core import flag_value
from lab.runner import make_run_config
from lab.statistics import summarize
ROOT=Path(__file__).resolve().parents[1]

class AdditionalTests(unittest.TestCase):
 def test_source_locks_are_full_hashes(self):
  lock=json.loads((ROOT/'sources/LOCK.json').read_text())
  self.assertRegex(lock['baseline_sha'],r'^[0-9a-f]{40}$')
  for v in lock['pr_heads'].values():self.assertRegex(v,r'^[0-9a-f]{40}$')
 def test_copy_config_never_mutates_original(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);prod=p/'prod';prod.mkdir();(prod/'input.json').write_text(json.dumps({'args':['--pack','packs/a','--native','model.gguf','--max-context','262144'],'parallel':4,'vision':{'exe':'vision'},'expert_profile_save':'prod-profile.bin','before_load':'unsafe','env':{'STRATA_A':'1'},'user_args':[]}))
   before=(prod/'input.json').read_bytes()
   c={'deployed_config':str(prod/'input.json'),'deployed_repo':str(prod),'max_context':131072,'conversation_cache_mib':0,'port':18089}
   cfg=make_run_config(c,p/'test','base',{},p/'output')
   self.assertEqual(before,(prod/'input.json').read_bytes());self.assertEqual(cfg['host'],'127.0.0.1')
   self.assertNotIn('before_load',cfg);self.assertNotIn('vision',cfg);self.assertNotIn('expert_profile_save',cfg)
   self.assertEqual(flag_value(cfg['args'],'--max-context'),'131072');self.assertTrue(flag_value(cfg['args'],'--pack').startswith(str(prod)))
 def test_fixed_output_mismatch_invalidates_perf(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t); rows=[]
   for i in range(5):
    for arm in ['base','off','on']:
     rows.append({'phase':'measured','round':i,'arm':arm,'case_id':'P','group':'decode','request_sha256':'same','fixed_output_comparable':arm!='on','metrics':{'wall_s':1,'prompt_tokens':10},'score':{'pass':True,'reason':'ok'}})
   (p/'requests.jsonl').write_text('\n'.join(json.dumps(x) for x in rows))
   r=summarize(p);self.assertNotEqual(r['decision'],'CANDIDATE_FOR_HOLDOUT_NOT_PRODUCTION');self.assertTrue(r['invalid_pairs'])
 def test_changed_requests_cannot_be_paired(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t); rows=[]
   for i in range(5):
    for arm in ['base','off','on']:
     rows.append({'phase':'measured','round':i,'arm':arm,'case_id':'P','group':'decode','request_sha256':arm,'metrics':{'wall_s':1,'prompt_tokens':10},'score':{'pass':True,'reason':'ok'}})
   (p/'requests.jsonl').write_text('\n'.join(json.dumps(x) for x in rows))
   self.assertTrue(summarize(p)['invalid_pairs'])

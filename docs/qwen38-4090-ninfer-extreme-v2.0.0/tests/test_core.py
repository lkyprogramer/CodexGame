import json, math, tempfile, unittest
from pathlib import Path
from tools.artifact import inspect_artifact
from tools.sampling import corrected_marginal, residual, normalize, deterministic_proposal
from tools.metrics import aggregate_rounds, paired_summary, candidate_gate
from tools.security import redact, safe_child
from tools.planner import choose_proposal

class SamplingTests(unittest.TestCase):
    def test_marginal(self):
        for p,q in [([.7,.2,.1],[.2,.7,.1]),([0,.5,.5],[1,0,0]),([1,0,0],[0,1,0]),([.1,.2,.7],[.1,.2,.7]),([.4,.6,0],[.8,0,.2])]:
            for a,b in zip(corrected_marginal(p,q),p): self.assertAlmostEqual(a,b,places=12)
    def test_deterministic(self): self.assertEqual(deterministic_proposal(3,1),[0.,1.,0.])
    def test_residual(self): self.assertEqual(residual([.6,.4],[1.,0.]),[0.,1.])
    def test_equal_has_no_rejection_branch(self): self.assertIsNone(residual([.5,.5],[.5,.5]))
    def test_negative(self):
        with self.assertRaises(ValueError): normalize([-1,2])
    def test_nan(self):
        with self.assertRaises(ValueError): normalize([float('nan'),1])
    def test_zero(self):
        with self.assertRaises(ValueError): normalize([0,0])
    def test_support(self):
        with self.assertRaises(ValueError): corrected_marginal([.5,.5],[1])

class MetricsTests(unittest.TestCase):
    def rows(self): return [dict(round_ms=20.,proposed=3,accepted=2,licensed=3,committed=3),dict(round_ms=40.,proposed=3,accepted=0,licensed=1,committed=1)]
    def test_weighted(self):
        d=aggregate_rounds(self.rows()); self.assertAlmostEqual(d['tps'],4/.06); self.assertEqual(d['al_committed'],2.)
    def test_partial_commit(self):
        r=self.rows()[0]; r['committed']=1
        d=aggregate_rounds([r]); self.assertEqual(d['al_licensed'],3); self.assertEqual(d['al_committed'],1)
    def test_invalid_count(self):
        r=self.rows()[0]; r['accepted']=4
        with self.assertRaises(ValueError): aggregate_rounds([r])
    def test_empty(self):
        with self.assertRaises(ValueError): aggregate_rounds([])
    def test_profile_not_perf(self):
        r=self.rows()[0]; r['profiled']=True
        with self.assertRaises(ValueError): aggregate_rounds([r])
    def test_pair(self):
        base=[100,110,90,100,100,105,95,100]; cand=[x*1.1 for x in base]
        d=paired_summary(base,cand); self.assertAlmostEqual(d['ratio'],1.1); self.assertTrue(d['gate_grade'])
        # zero-spread pairs: bootstrap collapses to a point, the t-interval must not be wider than the point either
        self.assertAlmostEqual(d['ci95_low'],1.1); self.assertAlmostEqual(d['ci95_high'],1.1)
    def test_pair_conservative_interval(self):
        base=[100]*8; cand=[104,112,96,108,101,111,99,105]
        d=paired_summary(base,cand)
        self.assertLessEqual(d['ci95_low'],min(d['bootstrap_ci95'][0],d['t_ci95'][0])+1e-12)
        self.assertGreaterEqual(d['ci95_high'],max(d['bootstrap_ci95'][1],d['t_ci95'][1])-1e-12)
    def test_pair_below_gate_grade(self):
        with self.assertRaises(ValueError): paired_summary([100,110,90,100,100],[110,121,99,110,110])
        d=paired_summary([100,110,90,100,100],[110,121,99,110,110],min_pairs=3); self.assertFalse(d['gate_grade'])
    def test_missing_pair(self):
        with self.assertRaises(ValueError): paired_summary([1,2],[1])
    def test_missing_gate(self): self.assertEqual(candidate_gate({})['verdict'],'BLOCKED')
    def facts(self,**kw):
        d=dict(quality_pass=True,state_pass=True,sampling_pass=True,artifact_pass=True,paired_gain_lcb=.12,paired_n=8,aa_noise_abs=.01,task_wall_ratio=.85,capacity=200192,headroom_mib=800,ooms=0,heldout_complete=True,measurement_complete=True)
        d.update(kw); return d
    def test_tradeoff(self):
        self.assertEqual(candidate_gate(self.facts(capacity=200191))['verdict'],'TRADEOFF_ONLY')
    def test_release_needs_soak(self):
        # exact protected boundary (200192) must pass the capacity gate; 262144 retained is fine but not required
        self.assertEqual(candidate_gate(self.facts())['verdict'],'CANDIDATE_PASS_NOT_RELEASED')
        self.assertEqual(candidate_gate(self.facts(capacity=262144))['verdict'],'CANDIDATE_PASS_NOT_RELEASED')
    def test_bad_quality(self):
        self.assertEqual(candidate_gate(self.facts(quality_pass=False,paired_gain_lcb=.3,task_wall_ratio=.8))['verdict'],'NO_GO')
    def test_too_few_pairs_blocked(self):
        r=candidate_gate(self.facts(paired_n=5)); self.assertEqual(r['verdict'],'BLOCKED'); self.assertIn('paired',r['reasons'][0])
    def test_aa_noise_blocked(self):
        r=candidate_gate(self.facts(aa_noise_abs=.05)); self.assertEqual(r['verdict'],'BLOCKED'); self.assertIn('A/A',r['reasons'][0])

class SecurityTests(unittest.TestCase):
    def test_bearer(self): self.assertNotIn('secret123',redact('Authorization: Bearer secret123'))
    def test_password(self): self.assertNotIn('s3cr3t',redact('[sudo] password for user: s3cr3t'))
    def test_hash_not_secret(self):
        t='sha256='+'a'*64; self.assertEqual(redact(t),t)
    def test_api_key(self): self.assertNotIn('abcdef',redact('api_key=abcdef'))
    def test_safe_child(self):
        with tempfile.TemporaryDirectory() as td:
            # compare resolved paths: macOS tempdirs live under /var -> /private/var
            self.assertEqual(safe_child(Path(td),'abc'),(Path(td)/'abc').resolve())
            with self.assertRaises(ValueError): safe_child(Path(td),'../escape')
    def test_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/'bad').symlink_to('/tmp')
            with self.assertRaises(ValueError): safe_child(p,'bad/x')

class PlannerTests(unittest.TestCase):
    def test_ratio_not_al(self):
        rows=[dict(name='mtp',al=3.,round_ms=20.,extra_ms=0.),dict(name='dflash',al=4.,round_ms=35.,extra_ms=0.)]
        self.assertEqual(choose_proposal(rows),'mtp')
    def test_catchup_cost(self):
        rows=[dict(name='mtp',al=3.,round_ms=20.,extra_ms=0.),dict(name='suffix',al=5.,round_ms=25.,extra_ms=15.)]
        self.assertEqual(choose_proposal(rows),'mtp')
    def test_zero_time(self):
        with self.assertRaises(ValueError): choose_proposal([dict(name='bad',al=3,round_ms=0,extra_ms=0)])

class ArtifactTests(unittest.TestCase):
    def write(self,p,objects):
        h=json.dumps({'identity':{'model_id':'qwen3.8-27b','weights_id':'groupwise-int'},'objects':objects}).encode(); n=16+len(h); off=(n+4095)//4096*4096
        p.write_bytes(b'NINFER\0\2'+len(h).to_bytes(8,'little')+h+b'\0'*(off-n)+b'\0'*32)
    def obj(self): return dict(name='text/x',kind='tensor',shape=[2,2],format='BF16',layout='contiguous-le-v1',offset=0,bytes=8)
    def test_good(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a'; self.write(p,[self.obj()]); d=inspect_artifact(p); self.assertEqual(d['tensor_bytes'],8)
    def test_overlap(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a'; x=self.obj(); y=dict(x,name='text/y',offset=4); self.write(p,[x,y])
            with self.assertRaises(ValueError): inspect_artifact(p)
    def test_outside(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a'; x=dict(self.obj(),bytes=1000); self.write(p,[x])
            with self.assertRaises(ValueError): inspect_artifact(p)
    def test_magic(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a'; p.write_bytes(b'0'*50)
            with self.assertRaises(ValueError): inspect_artifact(p)
    def test_duplicate(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a'; self.write(p,[self.obj(),dict(self.obj(),offset=8)])
            with self.assertRaises(ValueError): inspect_artifact(p)

if __name__=='__main__': unittest.main()

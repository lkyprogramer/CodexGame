import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('baseline_analyze',Path(__file__).with_name('analyze.py'))
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
MANIFEST={'schema_version':1,'records_schema_version':1,'expected_pi_cases':44,'pi_repetitions':5,
          'planned_core_cells':672,'executable_core_cells':660,'unrepresentable_core_cells':12,'profile':'B29_UNCHANGED_ARGV'}
def rows(p=1024):
    result=[];workloads=a.WORKLOADS[:3] if p==256 else a.WORKLOADS;reps=7 if p==256 else 5
    for block in range(5):
        for workload in workloads:
            for rep in range(reps):
                result.append({'schema_version':1,'id':f'fixture-{p}-{block}-{workload}-{rep}','group':'core','cache':'warm_prefix',
                'target_prompt_tokens':p,'status':'RECORDED','failures':[],'request_sha256':'a'*64,'raw_sha256':'b'*64,
                'elapsed_s':float(block+rep+1),'prompt_tokens':p,'completion_tokens':512,'requested_output_tokens':512,
                'result':{'prefix_cache_hit_tokens':p-1,'computed_prefill_tokens':1},'timings_seconds':{'decode':1},
                'extra':{'block':block,'repetition':rep,'track':'production_sampling_29','workload':workload,
                         'p95_bucket':f'P{p}-O512-production_sampling_29-equal{len(workloads)}workload','private_unused':'DO_NOT_PUBLISH'},
                'decode_tokens_per_s':100.0})
    return result

class AnalysisTests(unittest.TestCase):
    def report(self,records,verify=False,manifest=None):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'manifest.json').write_text(json.dumps(manifest or MANIFEST))
            (root/'records.jsonl').write_text('\n'.join(json.dumps(r) for r in records)+'\n')
            return a.build_report(root,verify_raw=verify,iterations=30)
    def bucket(self,report,p=1024):
        return next(x for x in report['p95_buckets'] if x['P']==p and x['track']=='production_sampling_29' and x['cache']=='warm_prefix')
    def test_complete_declared_mix_is_estimable_but_never_baseline_pass(self):
        report=self.report(rows());b=self.bucket(report)
        self.assertEqual(b['eligible_n'],100);self.assertEqual(b['status'],'ESTIMABLE');self.assertIsNotNone(b['elapsed_p95_s'])
        self.assertEqual(b['cluster_bootstrap_95_ci']['iterations'],30)
        self.assertIsNone(report['groups']['core']['elapsed_p95_s']);self.assertFalse(report['optimization_qualification']);self.assertEqual(report['plan']['planned_cells'],672)
        self.assertEqual(report['plan']['executable_cells'],660);self.assertEqual(report['plan']['unrepresentable_cells'],12)
        self.assertNotIn('DO_NOT_PUBLISH',json.dumps(report));self.assertNotIn('DO_NOT_PUBLISH',a.markdown(report))
    def test_99_samples_fail_closed(self):
        b=self.bucket(self.report(rows()[:-1]));self.assertEqual(b['recorded_n'],99)
        self.assertEqual(b['status'],'INCONCLUSIVE');self.assertIsNone(b['elapsed_p95_s'])
    def test_wrong_actual_p_stays_in_denominator(self):
        records=rows();records[0]['prompt_tokens']=1023;b=self.bucket(self.report(records))
        self.assertEqual(b['recorded_n'],100);self.assertEqual(b['eligible_n'],99);self.assertIsNone(b['elapsed_p95_s'])
        self.assertEqual(b['failure_reasons']['ACTUAL_P_MISMATCH'],1)
    def test_unknown_metric_schema_and_missing_field_are_rejected(self):
        for transform in [lambda r:r.update(metrics={'magic_tokens_per_s':9000}),lambda r:r.update(schema_version=999),lambda r:r.pop('elapsed_s'),lambda r:r.pop('schema_version')]:
            records=rows();transform(records[0])
            with self.assertRaises(a.SchemaError):self.report(records)
        with self.assertRaises(a.SchemaError):self.report(rows(),manifest={'schema_version':99})
    def test_wrong_mix_even_with_100_samples_is_inconclusive(self):
        records=rows();records[0]['extra']['workload']='free_java'
        b=self.bucket(self.report(records));self.assertEqual(b['eligible_n'],100)
        self.assertIsNone(b['elapsed_p95_s']);self.assertEqual(b['status'],'INCONCLUSIVE')
    def test_cache_and_failure_qualification_is_checked_not_assumed(self):
        records=rows();records[0]['result']['prefix_cache_hit_tokens']=0;records[1]['failures']=['TRANSPORT_ERROR']
        b=self.bucket(self.report(records));self.assertEqual(b['recorded_n'],100);self.assertEqual(b['eligible_n'],98)
        self.assertEqual(b['failure_reasons']['WARM_NOT_PROVEN'],1)
    def test_p256_has_three_workloads_and_105_samples(self):
        b=self.bucket(self.report(rows(256)),256);self.assertEqual(b['status'],'ESTIMABLE')
        self.assertEqual(b['planned_n'],105);self.assertEqual(b['workload_mix'],{w:35 for w in a.WORKLOADS[:3]})
    def test_raw_verification_missing_bytes_prevents_numeric_p95(self):
        report=self.report(rows(),verify=True);b=self.bucket(report)
        self.assertEqual(len(report['raw_verification']['mismatched_or_missing_ids']),100)
        self.assertEqual(b['eligible_n'],0);self.assertIsNone(b['elapsed_p95_s'])
    def test_cluster_bootstrap_is_deterministic_and_requires_five_blocks(self):
        self.assertEqual(a.cluster_ci(rows(),30),a.cluster_ci(rows(),30))
        self.assertEqual(a.cluster_ci([r for r in rows() if r['extra']['block']<4],30)['status'],'INCONCLUSIVE')
    def test_paired_aa_rejects_different_wire_instead_of_calling_repeats_aa(self):
        records=[]
        for pair in range(10):
            for member in ['A','A2']:
                r=copy.deepcopy(rows()[0]);r.update(id=f'aa-{pair}-{member}',group='frozen_wire_AA',extra={'pair':pair,'member':member})
                records.append(r)
        out=a.aa_report(records,30)['contexts']['1024'];self.assertEqual(out['eligible_pairs'],10);self.assertEqual(out['status'],'ESTIMABLE')
        records[0]['request_sha256']='c'*64
        out=a.aa_report(records,30)['contexts']['1024'];self.assertEqual(out['eligible_pairs'],9);self.assertIsNone(out['paired_cluster_bootstrap_95_ci_s'])


class ObserverTests(unittest.TestCase):
    def fixture(self,ratio):
        records=[]
        for pair in range(10):
            for enabled in [False,True]:
                r=copy.deepcopy(rows()[0]);r.update(id=f'observer-{pair}-{enabled}',group='observer_overhead',prompt_tokens=32768,
                    elapsed_s=10*(1+ratio) if enabled else 10,extra={'pair':pair,'gpu_sampler_enabled':enabled})
                records.append(r)
        return records
    def test_sampler_scope_pending_and_threshold(self):
        self.assertEqual(a.observer_report([])['status'],'PENDING')
        good=a.observer_report(self.fixture(.01),30)
        self.assertEqual(good['status'],'WITHIN_2_PERCENT');self.assertEqual(good['scope'],'incremental_GPU_sampler_only')
        self.assertEqual(a.observer_report(self.fixture(.03),30)['status'],'EXCEEDS_2_PERCENT')
    def test_bad_pair_or_wire_is_not_qualified(self):
        records=self.fixture(.01);records[0]['request_sha256']='c'*64
        out=a.observer_report(records,30);self.assertEqual(out['eligible_pairs'],9);self.assertEqual(out['status'],'INCONCLUSIVE')
        self.assertIsNone(out['paired_bootstrap_95_ci_relative_wall'])
    def test_allow_new_known_groups_and_reject_unknown(self):
        for group in ['S0_service_cold','S7_process_cache_scope','capacity_boundary','observer_priming','observer_overhead','closed_loop_request']:
            r=rows()[0];r['group']=group;a.validate(r)
        r=rows()[0];r['group']='arbitrary_metric_group'
        with self.assertRaises(a.SchemaError):a.validate(r)

if __name__=='__main__':unittest.main()

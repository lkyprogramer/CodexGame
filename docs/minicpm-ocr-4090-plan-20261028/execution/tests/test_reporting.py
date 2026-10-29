import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ocrbench.reporting import resources,latency,compare,load_run


class ReportingTest(unittest.TestCase):
    def test_energy_cpu_and_gaps(self):
        rows=[{'monotonic':t,'gpu':{'power_watts':100.,'memory_mib':1000},
               'cgroup':{'cpu.stat':f'usage_usec {t*1000000}','memory.current':'2000'}} for t in range(4)]
        r=resources(rows,.5,2.5,2,idle_watts=10)
        self.assertEqual(r['GPU_J_batch_raw'],200)
        self.assertEqual(r['GPU_J_batch_idle_adjusted'],180)
        self.assertEqual(r['CPU_cgroup_seconds'],2)
        self.assertEqual(r['J_per_attempted_unit'],100)
        self.assertIsNone(r['peak_RSS_bytes'])
        self.assertIsNone(resources(rows,0,5,2)['GPU_J_batch_raw'])
        self.assertIsNone(resources([rows[0],dict(rows[-1],monotonic=10)],0,10,2)['GPU_J_batch_raw'])

    def test_latency_minima(self):
        self.assertIsNone(latency(list(range(199)))['p95_seconds'])
        self.assertIsNotNone(latency(list(range(200)))['p95_seconds'])
        self.assertIsNone(latency(list(range(999)))['p99_seconds'])
        self.assertIsNotNone(latency(list(range(1000)))['p99_seconds'])

    def test_cli_run_and_comparison_refuses_missing_pixel_or_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            a=d/'a';b=d/'b'
            for target in (a,b):
                target.mkdir()
                def write(name,value): (target/name).write_text(json.dumps(value))
                write('summary.json',{'batch_wall_seconds':2,'submitted_pages':2,'timing_scope':'P0'})
                write('effective-config.json',{'profile':'C0-S0','timing_scope':'P0','page_admission':1})
                write('input-manifest.json',{'pages':[{'page_id':'p1','document_id':'d','source_family_id':'f','unit_kind':'page','scene_tags':['text']},{'page_id':'p2','unit_kind':'long_image'}]})
                write('predictions.json',{'pages':[{'page_id':'p1','status':'PASS','input_pixel_hash':'same','latency_seconds':1,'request_records':[{'usage':{'prompt_tokens':10,'completion_tokens':5},'finish_reason':'stop','attempts':[{'phase':'tokenize'},{'phase':'completion'}]}]}]})
            left,right=load_run(a),load_run(b)
            self.assertEqual(left['overall']['attempted_units'],2)
            self.assertEqual(left['overall']['complete_return_rate'],.5)
            self.assertIsNone(left['overall']['model_call_count'])
            self.assertEqual(left['overall']['observed_logical_request_count'],1)
            self.assertEqual(compare(left,right)['status'],'NOT_COMPARABLE')
            output=d/'report.json'
            subprocess.run([sys.executable,'-m','ocrbench.reporting','--run',str(a),'--out',str(output)],cwd=Path(__file__).resolve().parents[1],check=True)
            self.assertIsNone(json.loads(output.read_text())['runs'][0]['quality_winner'])

    def test_comparison_requires_frozen_runtime_policy(self):
        import copy
        policy=dict(dtype='bfloat16',max_model_len=16384,gpu_memory_utilization=.65,
                    max_num_seqs=4,max_num_batched_tokens=8192,cpu_cores=8,ram_gib=32)
        r={'config':{'profile':'C0-S0','timing_scope':'P0','options':{'runtime_policy':policy}},
           'timing_scope':'P0','timing_mode':'warm_adapter','warmup_enabled':True,'primary_performance_eligible':True,'input_evidence':{'p':{'pixel_hash':'same','source_sha256':'same',
           'unit_kind':'page','document_id':'d','source_family_id':'f','width':1,'height':1}},
           'fixed_workload_integrity':True,'overall':{'completed_units_per_second':1}}
        self.assertEqual(compare(r,r)['status'],'COMPARABLE_COMPLETE_SYSTEM_DESCRIPTIVE')
        b=copy.deepcopy(r);del b['config']['options']['runtime_policy']['cpu_cores']
        self.assertEqual(compare(r,b)['status'],'NOT_COMPARABLE')
        b=copy.deepcopy(r);b['config']['timing_scope']='D0'
        self.assertEqual(compare(r,b)['status'],'NOT_COMPARABLE')

    def test_formal_resource_window_excludes_shutdown_and_documents_stay_distinct(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            def write(name,value): (d/name).write_text(json.dumps(value))
            write('summary.json',{'batch_wall_seconds':2,'submitted_pages':1,'timing_scope':'P0',
                'timing_mode':'warm_adapter','primary_performance_eligible':True,
                'model_call_count_including_recovery_warmup':None,'recovery_warmup_model_call_count':None,
                'documents':[{'document_id':'d','status':'FAIL','latency_seconds':3}],
                'all_document_artifacts_pass':False})
            write('effective-config.json',{'timing_mode':'warm_adapter','warmup_enabled':True})
            write('input-manifest.json',{'pages':[{'page_id':'p','document_id':'d','unit_kind':'page'}]})
            write('predictions.json',{'pages':[{'page_id':'p','status':'PASS','request_records':[]}]})
            (d/'events.jsonl').write_text(json.dumps({'event':'timed_workload_start','batch_start_monotonic':1})+'\n'+json.dumps({'event':'run_terminal','monotonic_timestamp':10})+'\n')
            rows=[{'monotonic':t,'gpu':{'power_watts':100 if t<=3 else 10}} for t in range(11)]
            (d/'resources.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
            r=load_run(d,d/'resources.jsonl')
            self.assertEqual(r['formal_start_monotonic'],1)
            self.assertEqual(r['formal_stop_monotonic'],3)
            self.assertEqual(r['resources']['GPU_J_batch_raw'],200)
            self.assertEqual(r['overall']['complete_return_rate'],1)
            self.assertEqual(r['documents']['complete_return_rate'],0)
            self.assertFalse(r['documents']['all_document_artifacts_pass'])
            self.assertIsNone(r['overall']['model_call_count_including_recovery_warmup'])

    def test_warm_cold_comparison_rejected_and_retry_attempts_counted(self):
        import copy
        from ocrbench.reporting import page_statistics
        policy=dict(dtype='bfloat16',max_model_len=16384,gpu_memory_utilization=.65,
                    max_num_seqs=4,max_num_batched_tokens=8192,cpu_cores=8,ram_gib=32)
        r={'config':{'profile':'C0-S0','timing_scope':'P0','options':{'runtime_policy':policy}},
           'timing_scope':'P0','timing_mode':'warm_adapter','warmup_enabled':True,'primary_performance_eligible':True,
           'input_evidence':{'p':{'pixel_hash':'same','source_sha256':'same','unit_kind':'page','document_id':'d','source_family_id':'f','width':1,'height':1}},
           'fixed_workload_integrity':True,'overall':{'completed_units_per_second':1}}
        b=copy.deepcopy(r);b.update(timing_mode='cold_adapter',warmup_enabled=False,primary_performance_eligible=False)
        self.assertEqual(compare(r,b)['status'],'NOT_COMPARABLE')
        self.assertIn('timing_mode',compare(r,b)['timing_mode_mismatch'])
        counts=page_statistics([{'status':'PASS','request_records':[{'attempts':[{'phase':'tokenize'},{'phase':'completion','status':'FAIL'},{'phase':'completion','status':'PASS'}]}]}])
        self.assertEqual(counts['logical_request_count'],1)
        self.assertEqual(counts['model_call_count'],2)

    def test_blind_rubric_points_stay_distinct_from_CER(self):
        from ocrbench.reporting import rubric_summary
        review={'page_id':'p1','blind_candidate_id':'candidate-X','judge_id':'root',
            'source_image_sha256':'a'*64,'review_status':'accepted',
            'review_evidence':[{'path':'review.json','sha256':'b'*64}],
            'score_100':85,'criteria':{'fidelity':{'earned':35,'possible':40}}}
        report=rubric_summary({'rubric_version':'root-rubric-v1','reviews':[review]})
        self.assertEqual(report['status'],'AI_JUDGED')
        self.assertEqual(report['candidates']['candidate-X']['mean_supplied_score_100'],85)
        self.assertFalse(report['objective_metric_conversion'])
        self.assertIsNone(report['quality_winner'])
        review['score_100']=101
        with self.assertRaises(ValueError):
            rubric_summary({'rubric_version':'root-rubric-v1','reviews':[review]})

    def test_process_RSS_sum_is_distinct_from_cgroup_memory_and_window_bounded(self):
        rows=[{'monotonic':0,'process_rss_status':'AVAILABLE','sum_rss_bytes_including_shared':999999},
              {'monotonic':1,'process_rss_status':'AVAILABLE','sum_rss_bytes_including_shared':300,
               'cgroup':{'memory.current':'5000','memory.stat':'anon 1000\nfile 3000'}},
              {'monotonic':2,'process_rss_status':'PARTIAL','sum_rss_bytes_including_shared':99999,
               'cgroup':{'memory.current':'7000','memory.stat':'anon 1200\nfile 5000'}},
              {'monotonic':3,'process_rss_status':'AVAILABLE','sum_rss_bytes_including_shared':400,
               'cgroup':{'memory.current':'6000','memory.stat':'anon 1100\nfile 4000'}},
              {'monotonic':4,'process_rss_status':'AVAILABLE','sum_rss_bytes_including_shared':999999}]
        r=resources(rows,1,3,1)
        self.assertEqual(r['sampled_peak_process_rss_sum_bytes_including_shared'],400)
        self.assertEqual(r['sampled_peak_cgroup_memory_bytes'],7000)
        self.assertEqual(r['sampled_peak_cgroup_anon_bytes'],1200)
        self.assertEqual(r['sampled_peak_cgroup_file_bytes'],5000)
        self.assertEqual(r['RSS_complete_sample_count'],2)
        self.assertEqual(r['RSS_window_sample_count'],3)
        self.assertEqual(r['RSS_complete_sample_coverage'],2/3)
        self.assertIn('Shared pages',r['RSS_scope'])
        self.assertIsNone(r['peak_RSS_bytes'])

    def test_missing_or_partial_RSS_is_unknown_and_old_samples_remain_compatible(self):
        for rows in ([{'monotonic':1,'cgroup':{'memory.current':'100'}}],
                     [{'monotonic':1,'process_rss_status':'PARTIAL','sum_rss_bytes_including_shared':500}],
                     [{'monotonic':1,'process_rss_status':'AVAILABLE','sum_rss_bytes_including_shared':None}]):
            r=resources(rows,1,2,1)
            self.assertIsNone(r['sampled_peak_process_rss_sum_bytes_including_shared'])
            self.assertEqual(r['RSS_complete_sample_count'],0)
            self.assertEqual(r['RSS_sum_status'],'UNAVAILABLE_NO_COMPLETE_RSS_SAMPLES')
        empty=resources([],1,2,1)
        self.assertIsNone(empty['RSS_complete_sample_coverage'])
        known_zero=resources([{'monotonic':1,'process_rss_status':'AVAILABLE','sum_rss_bytes_including_shared':0}],1,2,1)
        self.assertEqual(known_zero['sampled_peak_process_rss_sum_bytes_including_shared'],0)

    def test_case_local_rubric_labels_require_decode_before_aggregation(self):
        from ocrbench.reporting import rubric_summary
        review={'page_id':'p1','blind_candidate_id':'A','judge_id':'root',
            'source_image_sha256':'a'*64,'review_status':'accepted',
            'review_evidence':[{'path':'review.json','sha256':'b'*64}],
            'score_100':90,'criteria':{'fidelity':{'earned':36,'possible':40}}}
        with self.assertRaisesRegex(ValueError,'UNBLIND_BEFORE_CANDIDATE_AGGREGATION'):
            rubric_summary({'rubric_version':'root-rubric-v1','candidate_label_scope':'CASE_LOCAL','reviews':[review]})

    def test_decoded_global_aliases_do_not_mix_flipped_case_labels(self):
        from ocrbench.reporting import rubric_summary
        reviews=[]
        # Root independently decoded p1 A->X/B->Y, p2 A->Y/B->X after score freeze.
        for page,local,stable,score in [('p1','A','candidate-X',90),('p1','B','candidate-Y',50),
                                       ('p2','A','candidate-Y',60),('p2','B','candidate-X',80)]:
            reviews.append({'page_id':page,'original_case_local_label':local,'blind_candidate_id':stable,
                'judge_id':'root','source_image_sha256':'a'*64,'review_status':'accepted',
                'review_evidence':[{'path':'frozen-review.json','sha256':'b'*64}],
                'score_100':score,'criteria':{'fidelity':{'earned':score*.4,'possible':40}}})
        report=rubric_summary({'rubric_version':'root-rubric-v1',
            'candidate_label_scope':'GLOBAL_AFTER_CASE_DECODE','reviews':reviews})
        self.assertEqual(report['candidate_label_scope'],'GLOBAL_AFTER_CASE_DECODE')
        self.assertEqual(report['candidates']['candidate-X']['mean_supplied_score_100'],85)
        self.assertEqual(report['candidates']['candidate-Y']['mean_supplied_score_100'],55)
        self.assertEqual(set(report['candidates']),{'candidate-X','candidate-Y'})


if __name__=='__main__': unittest.main()

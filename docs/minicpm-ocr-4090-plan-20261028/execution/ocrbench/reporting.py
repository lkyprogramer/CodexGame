"""Offline fixed-workload reports from runner artifacts; no model quality winner inferred."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

VERSION = 'ocrbench-reporting-v1'


def read_json(path):
    return json.loads(Path(path).read_text())


def read_lines(path):
    if not path or not Path(path).is_file():
        return []
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def quantile(values, q):
    """Linear interpolation between sorted observations (sample quantile type 7)."""
    if not values:
        return None
    ordered = sorted(values)
    at = (len(values) - 1) * q
    left = math.floor(at)
    return ordered[left] + (ordered[math.ceil(at)] - ordered[left]) * (at - left)


def latency(values):
    values = [v for v in values if isinstance(v, (float, int)) and math.isfinite(v) and v >= 0]
    return {'observations': len(values), 'p50_seconds': quantile(values, .5),
            'p95_seconds': quantile(values, .95) if len(values) >= 200 else None,
            'p99_seconds': quantile(values, .99) if len(values) >= 1000 else None,
            'p95_status': 'AVAILABLE' if len(values) >= 200 else 'INSUFFICIENT_OBSERVATIONS_200',
            'p99_status': 'AVAILABLE' if len(values) >= 1000 else 'INSUFFICIENT_OBSERVATIONS_1000'}


def interpolate(points, start, stop):
    """Bracket both endpoints; reject invalid, duplicate, decreasing samples or >3s gaps."""
    if len(points) < 2 or any(not all(math.isfinite(x) for x in p) for p in points):
        return None
    if any(b[0] <= a[0] for a, b in zip(points, points[1:])) or points[0][0] > start or points[-1][0] < stop:
        return None
    selected = []
    for left, right in zip(points, points[1:]):
        if right[0] < start or left[0] > stop:
            continue
        if right[0] - left[0] > 3.:
            return None
        for t in (max(left[0], start), min(right[0], stop)):
            if not selected or t != selected[-1][0]:
                value = left[1] + (right[1] - left[1]) * (t-left[0])/(right[0]-left[0])
                selected.append((t,value))
    return selected if selected and selected[0][0] == start and selected[-1][0] == stop else None


def resources(rows, start, stop, attempted, idle_watts=None):
    power, cpu, memory, vram = [], [], [], []
    rss_sums, cgroup_anon, cgroup_file = [], [], []
    rss_window_samples = 0
    rss_sample_statuses = Counter()
    errors = sum(bool(r.get('error')) for r in rows)
    for row in rows:
        time = row.get('monotonic')
        if not isinstance(time, (float, int)):
            continue
        gpu = row.get('gpu', {})
        if isinstance(gpu.get('power_watts'), (float, int)):
            power.append((time, gpu['power_watts']))
        if start <= time <= stop:
            if isinstance(gpu.get('memory_mib'), (float, int)):
                vram.append(gpu['memory_mib'])
            rss_window_samples += 1
            rss_sample_statuses[row.get('process_rss_status','MISSING')] += 1
            rss_value = row.get('sum_rss_bytes_including_shared')
            if row.get('process_rss_status') == 'AVAILABLE' and type(rss_value) is int and rss_value >= 0:
                rss_sums.append(rss_value)
            memory_stat = row.get('cgroup', {}).get('memory.stat','')
            for line in memory_stat.splitlines():
                fields = line.split()
                if len(fields) == 2 and fields[1].isdigit():
                    if fields[0] == 'anon':
                        cgroup_anon.append(int(fields[1]))
                    elif fields[0] == 'file':
                        cgroup_file.append(int(fields[1]))
            value = row.get('cgroup', {}).get('memory.current')
            if value is not None:
                memory.append(int(value))
        stat = row.get('cgroup', {}).get('cpu.stat', '')
        usage = dict(line.split() for line in stat.splitlines())
        if 'usage_usec' in usage:
            cpu.append((time, int(usage['usage_usec']) / 1e6))
    sampled = interpolate(power, start, stop)
    joules = sum((b[0]-a[0])*(a[1]+b[1])/2 for a,b in zip(sampled, sampled[1:])) if sampled else None
    cpu_sampled = interpolate(cpu, start, stop)
    cpu_seconds = cpu_sampled[-1][1] - cpu_sampled[0][1] if cpu_sampled else None
    if cpu_seconds is not None and (cpu_seconds < 0 or any(b[1]<a[1] for a,b in zip(cpu,cpu[1:]))):
        cpu_seconds = None
    if idle_watts is not None and (not math.isfinite(idle_watts) or idle_watts < 0):
        raise ValueError('idle_watts must be a measured finite nonnegative value')
    return {'measurement_scope': 'whole_GPU_and_candidate_container_cgroup',
            'sample_count':len(rows), 'sample_error_count':errors,
            'GPU_J_batch_raw':joules,
            'GPU_J_batch_idle_adjusted':joules-idle_watts*(stop-start) if joules is not None and idle_watts is not None else None,
            'energy_status':'AVAILABLE' if joules is not None else 'UNAVAILABLE_MISSING_BRACKETING_OR_SAMPLE_GAPS',
            'J_per_attempted_unit':joules/attempted if joules is not None and attempted else None,
            'J_per_good_unit':None, 'good_energy_status':'UNAVAILABLE_NO_FORMAL_GOOD_PAGE_ANNOTATION',
            'CPU_cgroup_seconds':cpu_seconds,
            'CPU_status':'AVAILABLE' if cpu_seconds is not None else 'UNAVAILABLE_MISSING_BRACKETING_OR_COUNTER_RESET',
            'sampled_peak_VRAM_mib':max(vram) if vram else None,
            'sampled_peak_cgroup_memory_bytes':max(memory) if memory else None,
            'sampled_peak_process_rss_sum_bytes_including_shared':max(rss_sums) if rss_sums else None,
            'RSS_scope':'Sum of process VmRSS for a complete candidate cgroup.procs snapshot. Shared pages may be counted multiple times; not unique resident memory, PSS or a continuous peak.',
            'RSS_window_sample_count':rss_window_samples,
            'RSS_complete_sample_count':len(rss_sums),
            'RSS_sample_status_counts':dict(rss_sample_statuses),
            'RSS_complete_sample_coverage':len(rss_sums)/rss_window_samples if rss_window_samples else None,
            'RSS_sum_status':('AVAILABLE_COMPLETE_SAMPLE_COVERAGE' if len(rss_sums) == rss_window_samples else 'AVAILABLE_PARTIAL_SAMPLE_COVERAGE') if rss_sums else 'UNAVAILABLE_NO_COMPLETE_RSS_SAMPLES',
            'sampled_peak_cgroup_anon_bytes':max(cgroup_anon) if cgroup_anon else None,
            'sampled_peak_cgroup_file_bytes':max(cgroup_file) if cgroup_file else None,
            'peak_RSS_bytes':None,'RSS_status':'UNAVAILABLE_UNIQUE_PEAK_USE_EXPLICIT_SAMPLED_RSS_SUM_FIELD',
            'whole_system_energy_status':'UNAVAILABLE_NO_WHOLE_SYSTEM_METER'}


def page_statistics(pages):
    records = [r for page in pages for r in page.get('request_records', [])]
    records_complete = all('request_records' in page and not page.get('partial_artifacts_preserved', False) for page in pages)
    attempt_evidence_complete = records_complete and all('attempts' in r for r in records)
    usages = [r.get('usage') for r in records]
    retried_completion = any(sum(a.get('phase') == 'completion' for a in r.get('attempts',[])) > 1 for r in records)
    usage_complete = records_complete and not retried_completion and bool(records) and all(isinstance(u,dict) and all(type(u.get(k)) is int for k in ('prompt_tokens','completion_tokens')) for u in usages)
    error_strings = [str(x) for p in pages for x in p.get('errors', [])] + [str(r.get('error','')) for r in records]
    count = len(pages)
    return {'attempted_units':count, 'status_counts':dict(Counter(p.get('status','MISSING') for p in pages)),
            'complete_return_count':sum(p.get('status') == 'PASS' for p in pages),
            'complete_return_rate':sum(p.get('status') == 'PASS' for p in pages)/count if count else None,
            'quality_status':'UNSCORED_COMPLETE_RETURN_IS_NOT_QUALITY',
            'length_call_count':sum(r.get('finish_reason') == 'length' for r in records),
            'budget_failed_unit_count':sum(p.get('status') == 'FAIL_BUDGET' for p in pages),
            'schema_error_unit_count':sum(any(any(k in str(e).lower() for k in ('schema','invalid_json','invalid_adapter','bbox','invalid_block','structured_output','invalid_chart')) for e in p.get('errors',[])) for p in pages),
            'timeout_unit_count':sum(any(any(k in str(e).lower() for k in ('timeout','deadline','timed out')) for e in p.get('errors',[])) for p in pages),
            'error_counts':dict(Counter(x for x in error_strings if x and x != 'None')),
            'logical_request_count':len(records) if records_complete else None,
            'observed_logical_request_count':len(records),
            'model_call_count':sum(a.get('phase') == 'completion' for r in records for a in r.get('attempts', [])) if attempt_evidence_complete else None,
            'model_call_count_status':'AVAILABLE_HTTP_ATTEMPTS' if attempt_evidence_complete else 'UNAVAILABLE_ATTEMPT_EVIDENCE_MISSING',
            'http_attempt_phase_counts':dict(Counter(a.get('phase','UNKNOWN') for r in records for a in r.get('attempts',[]))),
            'prompt_tokens':sum(u['prompt_tokens'] for u in usages) if usage_complete else None,
            'completion_tokens':sum(u['completion_tokens'] for u in usages) if usage_complete else None,
            'token_status':'AVAILABLE_REPORTED_USAGE' if usage_complete else 'UNAVAILABLE_INCOMPLETE_USAGE_RETRIES_OR_NO_CALLS',
            'usage_scope':'Server returned usage; failed request execution may consume unreported tokens',
            'latency':latency([p.get('latency_seconds') for p in pages])}


def load_run(directory, resource_file=None, idle_watts=None, gt_path=None):
    directory = Path(directory)
    summary = read_json(directory/'summary.json')
    config = read_json(directory/'effective-config.json')
    manifest = read_json(directory/'input-manifest.json')['pages']
    predictions = read_json(directory/'predictions.json')['pages']
    ids = [p['page_id'] for p in manifest]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate manifest page_id')
    by_id = {p['page_id']:p for p in predictions}
    if len(by_id) != len(predictions):
        raise ValueError('duplicate prediction page_id')
    pages = []
    for case in manifest:
        p = dict(by_id.get(case['page_id'], {'page_id':case['page_id'],'status':'MISSING','errors':['PREDICTION_MISSING']}))
        for key in ('unit_kind','source_family_id','document_id','scene_tags'):
            p.setdefault(key,case.get(key,[] if key == 'scene_tags' else 'UNKNOWN'))
        timing = directory/'pages'/case['page_id']/'timing.json'
        if timing.is_file():
            p.update(read_json(timing))
        pages.append(p)
    extras = sorted(set(by_id) - set(ids))
    wall = summary['batch_wall_seconds']
    if wall is not None and (not isinstance(wall,(float,int)) or not math.isfinite(wall) or wall <= 0):
        raise ValueError('invalid actual batch wallclock')
    events = read_lines(directory/'events.jsonl')
    starts = [e for e in events if e.get('event') == 'timed_workload_start']
    if len(starts) > 1:
        raise ValueError('multiple timed workload starts in one run')
    start = starts[0].get('batch_start_monotonic') if starts else None
    stop = start+wall if start is not None and wall is not None else None
    result = {'report_version':VERSION,'run_directory':str(directory),'config':config,
              'timing_scope':summary.get('timing_scope'),'batch_wall_seconds':wall,
              'timing_mode':summary.get('timing_mode',config.get('timing_mode')),
              'warmup_enabled':config.get('warmup_enabled'),
              'primary_performance_eligible':summary.get('primary_performance_eligible'),
              'performance_ineligibility_reason':summary.get('performance_ineligibility_reason'),
              'formal_start_monotonic':start,'formal_stop_monotonic':stop,
              'manifest_sha256':hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),
              'fixed_workload_integrity':not extras and len(pages)==summary.get('submitted_pages'),
              'extra_prediction_ids':extras, 'overall':page_statistics(pages), 'groups':{},
              'quality_winner':None,'quality_status':'UNAVAILABLE_NO_FORMAL_GOLD',
              'family_cluster_CI_status':'UNAVAILABLE_NO_FORMAL_GOLD',
              'input_evidence':{p['page_id']:{'pixel_hash':p.get('input_pixel_hash'), 'source_sha256':p.get('source_sha256'),
                  'width':p.get('width'),'height':p.get('height'),
                  'unit_kind':p['unit_kind'],'document_id':p['document_id'],
                  'source_family_id':p['source_family_id']} for p in pages}}
    result['overall']['completed_units_per_second'] = result['overall']['complete_return_count']/wall if wall else None
    result['overall']['model_call_count_including_recovery_warmup'] = summary.get('model_call_count_including_recovery_warmup')
    result['overall']['recovery_warmup_model_call_count'] = summary.get('recovery_warmup_model_call_count')
    result['overall']['complete_call_count_status'] = 'AVAILABLE' if summary.get('model_call_count_including_recovery_warmup') is not None else 'UNAVAILABLE_RECOVERY_OR_ATTEMPT_EVIDENCE'
    documents = summary.get('documents', [])
    document_ids = {case.get('document_id', 'UNKNOWN') for case in manifest}
    document_map = {doc['document_id']: doc for doc in documents}
    if len(document_map) != len(documents):
        raise ValueError('duplicate document terminal')
    document_passes = sum(document_map.get(doc, {}).get('status') == 'PASS' for doc in document_ids)
    result['documents'] = {'planned_count':len(document_ids),'terminal_count':len(document_map),
        'complete_return_count':document_passes,'complete_return_rate':document_passes/len(document_ids) if document_ids else None,
        'all_document_artifacts_pass':summary.get('all_document_artifacts_pass'),
        'status_counts':dict(Counter(document_map.get(doc, {}).get('status', 'MISSING') for doc in document_ids)),
        'latency':latency([doc.get('latency_seconds') for doc in documents]),'results':documents,
        'quality_status':'UNSCORED_DOCUMENT_ARTIFACT_SUCCESS_IS_NOT_QUALITY'}
    for field in ('unit_kind','source_family_id','document_id','scene_tags'):
        groups = {}
        for page in pages:
            keys = page[field] if field == 'scene_tags' else [page[field]]
            for key in keys:
                groups.setdefault(str(key), []).append(page)
        result['groups'][field] = {k:page_statistics(v) for k,v in groups.items()}
    result['resources'] = resources(read_lines(resource_file), start, stop, len(pages), idle_watts) if start is not None and stop is not None else {'energy_status':'UNAVAILABLE_RUN_TIMESTAMPS_MISSING'}
    if gt_path and wall is not None:
        from .scoring import score_page, summarize
        gt = read_json(gt_path); gt = gt['pages'] if isinstance(gt,dict) else gt
        gold = {p['page_id']:p for p in gt}
        result['diagnostic_scoring'] = summarize([score_page(p,gold.get(p['page_id'])) for p in pages],wall)
        result['diagnostic_scoring']['scope'] = 'DIAGNOSTIC_ONLY_NO_PRIMARY_QUALITY_WINNER'
        if 'AI_JUDGED' in result['diagnostic_scoring'].get('reference_kinds', []):
            result['quality_status'] = 'AI_JUDGED_REFERENCE_METRICS_SEPARATE_FROM_HUMAN'
            result['diagnostic_scoring']['reference_status'] = 'AI_JUDGED'
    return result


def compare(left, right):
    a,b = left['input_evidence'],right['input_evidence']
    common = sorted(a.keys() & b.keys())
    missing_left,missing_right = sorted(b.keys()-a.keys()),sorted(a.keys()-b.keys())
    pixel_missing = [p for p in common if not a[p]['pixel_hash'] or not b[p]['pixel_hash']]
    pixel_mismatch = [p for p in common if a[p]['pixel_hash'] and b[p]['pixel_hash'] and a[p]['pixel_hash'] != b[p]['pixel_hash']]
    identity_mismatch = [p for p in common if any(a[p][k] != b[p][k] for k in ('unit_kind','document_id','source_family_id','source_sha256','width','height'))]
    # Engine/model/prompt architecture differences are allowed in C0; external policy is not.
    keys = ('profile','timing_scope','page_admission','region_limit','max_model_len','gpu_memory_utilization','seed','sampling','page_timeout','document_timeout','region_timeout','options')
    mismatches = [k for k in keys if left['config'].get(k) != right['config'].get(k)]
    profile_left = left['config'].get('profile') or left['config'].get('options', {}).get('profile')
    profile_right = right['config'].get('profile') or right['config'].get('options', {}).get('profile')
    declared = bool(profile_left and profile_right and left['timing_scope'] and right['timing_scope'])
    if profile_left != profile_right:
        mismatches.append('declared_profile')
    required_policy = ('dtype','max_model_len','gpu_memory_utilization','max_num_seqs','max_num_batched_tokens','cpu_cores','ram_gib')
    policies = [r['config'].get('options', {}).get('runtime_policy', {}) for r in (left,right)]
    missing_policy = [key for key in required_policy if any(policy.get(key) is None for policy in policies)]
    policy_mismatch = [key for key in required_policy if policies[0].get(key) != policies[1].get(key)]
    modes = ('timing_mode','warmup_enabled','primary_performance_eligible')
    mode_mismatch = [key for key in modes if left.get(key) != right.get(key)]
    mode_declared = all(r.get('timing_mode') in ('cold_adapter','warm_adapter') and isinstance(r.get('warmup_enabled'),bool) and isinstance(r.get('primary_performance_eligible'),bool) for r in (left,right))
    primary_eligible = all(r.get('primary_performance_eligible') is True for r in (left,right))
    comparable = declared and mode_declared and primary_eligible and not mode_mismatch and not missing_policy and not policy_mismatch and not (missing_left or missing_right or pixel_missing or pixel_mismatch or identity_mismatch or mismatches) and left['fixed_workload_integrity'] and right['fixed_workload_integrity']
    return {'status':'COMPARABLE_COMPLETE_SYSTEM_DESCRIPTIVE' if comparable else 'NOT_COMPARABLE',
            'missing_left':missing_left,'missing_right':missing_right,'missing_pixel_hash':pixel_missing,
            'pixel_mismatch':pixel_mismatch,'identity_mismatch':identity_mismatch,'config_mismatch':mismatches,
            'fixed_common_count':len(common),'profile_scope_declared':declared,
            'timing_mode_mismatch':mode_mismatch,'timing_mode_declared':mode_declared,
            'both_primary_performance_eligible':primary_eligible,
            'missing_runtime_policy_fields':missing_policy,'runtime_policy_mismatch':policy_mismatch,
            'descriptive_completed_throughput_ratio_left_over_right':left['overall']['completed_units_per_second']/right['overall']['completed_units_per_second'] if comparable and left['overall']['completed_units_per_second'] is not None and right['overall']['completed_units_per_second'] else None,
            'quality_winner':None,'formal_speed_winner':None,
            'interpretation':'One-run observation only; no quality winner, adoption or family-cluster confidence established'}



def rubric_summary(document: dict) -> dict:
    """Import a root judge's blind rubric as rubric points, never CER or page-good."""
    from .scoring import ai_provenance_errors
    if document.get('candidate_label_scope') == 'CASE_LOCAL':
        raise ValueError('UNBLIND_BEFORE_CANDIDATE_AGGREGATION')
    if document.get('rubric_version') != 'root-rubric-v1' or not isinstance(document.get('reviews'),list):
        raise ValueError('expected root-rubric-v1 reviews list')
    rows, seen = [], set()
    for review in document['reviews']:
        errors = ai_provenance_errors(review)
        identity = (review.get('page_id'), review.get('blind_candidate_id'))
        if not all(isinstance(v,str) and v.strip() for v in identity) or identity in seen:
            raise ValueError('rubric requires unique page/blind candidate identifiers')
        seen.add(identity)
        value = review.get('score_100')
        if errors or type(value) not in (int,float) or not math.isfinite(value) or not 0 <= value <= 100 or not isinstance(review.get('criteria'),dict) or not review['criteria']:
            raise ValueError('invalid or unaccepted rubric review: ' + str(errors))
        rows.append(review)
    groups = {}
    for row in rows:
        groups.setdefault(row['blind_candidate_id'],[]).append(row['score_100'])
    return {'status':'AI_JUDGED', 'rubric_version':'root-rubric-v1',
            'candidate_label_scope':document.get('candidate_label_scope','LEGACY_GLOBAL'),
            'objective_metric_conversion':False,'quality_winner':None,
            'scope':'Supplied blind root-rubric points; no automatic CER, GT completeness or page-good inference',
            'candidates':{key:{'reviewed_units':len(values),'mean_supplied_score_100':sum(values)/len(values)} for key,values in groups.items()},
            'reviews':rows}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='append',required=True,type=Path)
    parser.add_argument('--resources',action='append',type=Path,default=[])
    parser.add_argument('--idle-watts',type=float)
    parser.add_argument('--gt-draft',type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--rubric',type=Path)
    args=parser.parse_args()
    runs=[load_run(p,args.resources[i] if i<len(args.resources) else None,args.idle_watts,args.gt_draft) for i,p in enumerate(args.run)]
    report={'report_version':VERSION,'runs':runs,'comparison':compare(*runs) if len(runs)==2 else None}
    if args.rubric:
        report['AI_rubric'] = rubric_summary(read_json(args.rubric))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__ == '__main__':
    main()

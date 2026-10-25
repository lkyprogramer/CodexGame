#!/usr/bin/env python3
"""Fail-closed, body-free B29 evidence analysis. No network or engine operations."""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import random
import re
import statistics

LENGTHS = [256,1024,4096,8192,16384,32768,65536,98304,131072,163840,196608,229376,245760,253952]
WORKLOADS = ['copy_patch','free_java','chinese_analysis','tool_json']
TRACKS = ['production_sampling_29','research_greedy']
CACHES = ['request_cold','warm_prefix']
BOOTSTRAPS = 10000
SEED = 20261020
REQUIRED = {'schema_version','id','group','cache','target_prompt_tokens','status','failures','request_sha256','raw_sha256',
            'elapsed_s','prompt_tokens','completion_tokens','requested_output_tokens','result','extra',
            'decode_tokens_per_s','timings_seconds'}
KNOWN = REQUIRED | {'schema_version','start_utc','completed_utc','response_request_id','server_instance_id',
 'http_status','effective_output_cap_by_source_contract','prepare_detail','speculative','continuation_cache',
 'decode_rate_definition','first_payload_s','first_content_s','first_reasoning_s','first_tool_s',
 'content_chars','reasoning_chars','finish_reason','tool_json_valid','sse_done','malformed_data_events',
 'quality_status','behavior_outcomes','unavailable_metrics','foreign_requests_during_interval','attempt_id','attempt_directory'}
GROUPS = {'core','warmup','resume_priming','pi_teacher_forced','aa_priming','frozen_wire_AA',
 'long_output_8192','S3_append','S4_S5_branch','S4_system','S6_L2','protocol','C1_queue','disconnect',
 'disconnect_recovery','negative_contract','S0_service_cold','S7_process_cache_scope',
 'capacity_boundary','observer_priming','observer_overhead','closed_loop_request'}
MISSING_METRICS = {'token_ids','token_itl_seconds','reasoning_tokens','round_wall_seconds',
                   'allocator_high_water_bytes','internal_hidden_state'}
class SchemaError(ValueError):
    pass

def digest(data): return hashlib.sha256(data).hexdigest()
def numeric(value): return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)
def quantile(values, q):
    values=sorted(values)
    return values[max(0,math.ceil(q*len(values))-1)] if values else None

def validate(row):
    if not isinstance(row,dict) or REQUIRED-set(row) or set(row)-KNOWN:
        raise SchemaError('Record fields do not match declared v1 schema')
    if type(row['schema_version']) is not int or row['schema_version'] != 1: raise SchemaError('Unknown record schema')
    if row['group'] not in GROUPS: raise SchemaError('Unknown record group')
    if not isinstance(row['id'],str) or not re.fullmatch(r'[A-Za-z0-9_.-]+',row['id']): raise SchemaError('Invalid record ID')
    for name in ['request_sha256','raw_sha256']:
        if not isinstance(row[name],str) or not re.fullmatch('[0-9a-f]{64}',row[name]): raise SchemaError('Missing evidence hash')
    if row['status'] not in ['RECORDED','RECORDED_WITH_GAPS']: raise SchemaError('Unknown record status')
    if not isinstance(row['failures'],list) or any(not isinstance(x,str) or not re.fullmatch('[A-Z][A-Z0-9_]*',x) for x in row['failures']):
        raise SchemaError('Invalid failure classification')
    for name in ['elapsed_s','decode_tokens_per_s']:
        if row[name] is not None and (not numeric(row[name]) or row[name]<0): raise SchemaError('Invalid numeric metric')
    if not numeric(row['elapsed_s']): raise SchemaError('Missing elapsed metric')
    if not isinstance(row['extra'],dict) or not isinstance(row['result'],dict) or not isinstance(row['timings_seconds'],dict):
        raise SchemaError('Invalid structured metrics')
    if 'metrics' in row or set(row.get('unavailable_metrics',{}))-MISSING_METRICS: raise SchemaError('Unknown metric')
    for name in ['prompt_tokens','completion_tokens','requested_output_tokens']:
        if row[name] is not None and (not isinstance(row[name],int) or isinstance(row[name],bool) or row[name]<0):
            raise SchemaError('Invalid token metric')
    if row['group']=='core':
        ex=row['extra']
        if any(k not in ex for k in ['block','repetition','track','workload','p95_bucket']): raise SchemaError('Missing core design fields')
        if ex['block'] not in range(5) or not isinstance(ex['repetition'],int) or ex['repetition']<0: raise SchemaError('Invalid core replicate')
        if ex['track'] not in TRACKS or ex['workload'] not in WORKLOADS: raise SchemaError('Unknown core track/workload')
        if row['target_prompt_tokens'] not in LENGTHS or row['requested_output_tokens'] not in [128,512,2048] or row['cache'] not in CACHES:
            raise SchemaError('Unknown core matrix cell')
    return row

def reasons(row):
    out=set(row['failures'])
    if row['status']!='RECORDED' and not out: out.add('UNCLASSIFIED_RECORD_GAP')
    if row['group']=='core':
        if row['prompt_tokens']!=row['target_prompt_tokens']: out.add('ACTUAL_P_MISMATCH')
        result=row['result'];hit=result.get('prefix_cache_hit_tokens')
        if row['cache']=='request_cold':
            if hit!=0 or result.get('computed_prefill_tokens')!=row['prompt_tokens']:out.add('COLD_NOT_PROVEN')
        elif not isinstance(hit,int) or hit<=0:out.add('WARM_NOT_PROVEN')
    return sorted(out)

def stats(rows):
    eligible=[r for r in rows if not reasons(r)]
    elapsed=[r['elapsed_s'] for r in eligible]
    decode=[r['decode_tokens_per_s'] for r in eligible if r['decode_tokens_per_s'] is not None]
    counts=collections.Counter(x for r in rows for x in reasons(r))
    return {'recorded_n':len(rows),'eligible_n':len(eligible),'failed_or_ineligible_n':len(rows)-len(eligible),
            'failure_reasons':dict(sorted(counts.items())), 'elapsed_mean_s':statistics.mean(elapsed) if elapsed else None,
            'elapsed_median_s':statistics.median(elapsed) if elapsed else None,'elapsed_p90_s':quantile(elapsed,.9),
            'elapsed_p95_s':None,
            'decode_observed_n':len(decode),'decode_p10_tokens_per_s':quantile(decode,.1)}

def cluster_ci(rows, iterations=BOOTSTRAPS):
    """Two-way resampling of temporal blocks and whole workload clusters, never tokens."""
    rows=[r for r in rows if not reasons(r)]
    blocks=sorted({r['extra']['block'] for r in rows});workloads=sorted({r['extra']['workload'] for r in rows})
    if blocks!=list(range(5)) or not workloads:
        return {'status':'INCONCLUSIVE','reason':'FIVE_TEMPORAL_BLOCKS_REQUIRED','iterations':0}
    clusters=collections.defaultdict(list)
    for row in rows:clusters[row['extra']['block'],row['extra']['workload']].append(row)
    if any(not clusters[b,w] for b in blocks for w in workloads):
        return {'status':'INCONCLUSIVE','reason':'MISSING_BLOCK_WORKLOAD_CLUSTER','iterations':0}
    rng=random.Random(SEED);means=[];medians=[];p90=[];p95=[];d10=[]
    for _ in range(iterations):
        bs=rng.choices(blocks,k=5);ws=rng.choices(workloads,k=len(workloads))
        sample=[r for b in bs for w in ws for r in clusters[b,w]]
        times=sorted(r['elapsed_s'] for r in sample)
        means.append(sum(times)/len(times));medians.append(statistics.median(times));p90.append(quantile(times,.9))
        if len(rows)>=100:p95.append(quantile(times,.95))
        decode=[r['decode_tokens_per_s'] for r in sample if r['decode_tokens_per_s'] is not None]
        if decode:d10.append(quantile(decode,.1))
    ci=lambda xs:[quantile(xs,.025),quantile(xs,.975)] if xs else None
    return {'status':'ESTIMATED_WITH_ONLY_FIVE_BLOCKS','iterations':iterations,'seed':SEED,
            'method':'two_way_block_workload_cluster_percentile_95','independence_unit':'temporal_block_and_workload_cluster',
            'elapsed_mean_s':ci(means),'elapsed_median_s':ci(medians),'elapsed_p90_s':ci(p90),'elapsed_p95_s':ci(p95),
            'decode_p10_tokens_per_s':ci(d10),'caveat':'Five temporal blocks limit CI stability; this is no optimization qualification.'}

def cell_key(row):
    return (row['target_prompt_tokens'],row['requested_output_tokens'],row['extra']['workload'],row['extra']['track'],row['cache'])
def expected_repeats(p,o):return 35 if p==256 and o==512 else 25 if o==512 else 20

def aa_report(rows,iterations=BOOTSTRAPS):
    points=collections.defaultdict(dict);bad=collections.Counter()
    for row in rows:
        if row['group']!='frozen_wire_AA':continue
        ex=row['extra'];p=row['target_prompt_tokens'];pair=ex.get('pair');member=ex.get('member')
        if p not in [1024,32768,131072,253952] or pair not in range(10) or member not in ['A','A2']:
            bad['INVALID_PAIR_METADATA']+=1;continue
        if member in points[p,pair]:bad['DUPLICATE_PAIR_MEMBER']+=1;continue
        points[p,pair][member]=row
    result={}
    for p in [1024,32768,131072,253952]:
        differences=[];fail=collections.Counter()
        for pair in range(10):
            members=points.get((p,pair),{})
            if set(members)!={'A','A2'}:fail['MISSING_PAIR_MEMBER']+=1;continue
            a,b=members['A'],members['A2']
            if reasons(a) or reasons(b):fail['INELIGIBLE_PAIR']+=1;continue
            if a['request_sha256']!=b['request_sha256']:fail['WIRE_OR_SEED_MISMATCH']+=1;continue
            if any(r['prompt_tokens']!=p or not isinstance(r['result'].get('prefix_cache_hit_tokens'),int) or r['result']['prefix_cache_hit_tokens']<=0 for r in [a,b]):
                fail['CONTEXT_OR_WARM_NOT_PROVEN']+=1;continue
            differences.append(b['elapsed_s']-a['elapsed_s'])
        ci=None
        if len(differences)==10:
            rng=random.Random(SEED);sample=[statistics.mean(rng.choices(differences,k=10)) for _ in range(iterations)]
            ci=[quantile(sample,.025),quantile(sample,.975)]
        result[str(p)]={'planned_pairs':10,'eligible_pairs':len(differences),'status':'ESTIMABLE' if len(differences)==10 and not bad else 'INCONCLUSIVE',
                        'failure_reasons':dict(fail),'paired_mean_A2_minus_A_s':statistics.mean(differences) if differences else None,
                        'paired_cluster_bootstrap_95_ci_s':ci,'bootstrap_iterations':iterations if ci else 0,'seed':SEED}
    return {'definition':'Only explicit frozen_wire_AA pairs with identical request hash (which includes seed). Other baseline repeats are not A/A.',
            'metadata_errors':dict(bad),'contexts':result}

def observer_report(rows,iterations=BOOTSTRAPS):
    selected=[r for r in rows if r['group']=='observer_overhead']
    pairs=collections.defaultdict(dict);fail=collections.Counter()
    for row in selected:
        pair=row['extra'].get('pair');enabled=row['extra'].get('gpu_sampler_enabled')
        if type(pair) is not int or pair not in range(10) or type(enabled) is not bool:
            fail['INVALID_PAIR_METADATA']+=1;continue
        if enabled in pairs[pair]:fail['DUPLICATE_PAIR_MEMBER']+=1;continue
        pairs[pair][enabled]=row
    relative=[];absolute=[]
    for pair in range(10):
        members=pairs.get(pair,{})
        if set(members)!={False,True}:fail['MISSING_PAIR_MEMBER']+=1;continue
        off,on=members[False],members[True]
        if reasons(off) or reasons(on):fail['INELIGIBLE_PAIR']+=1;continue
        if off['request_sha256']!=on['request_sha256']:fail['WIRE_OR_SEED_MISMATCH']+=1;continue
        if off['elapsed_s']<=0:fail['ZERO_OFF_WALL_TIME']+=1;continue
        if any(r['prompt_tokens']!=32768 or r['cache']!='warm_prefix' or not isinstance(r['result'].get('prefix_cache_hit_tokens'),int) or r['result']['prefix_cache_hit_tokens']<=0 for r in [off,on]):
            fail['CONTEXT_OR_WARM_NOT_PROVEN']+=1;continue
        absolute.append(on['elapsed_s']-off['elapsed_s'])
        relative.append((on['elapsed_s']-off['elapsed_s'])/off['elapsed_s'])
    ci=None;state='PENDING' if not selected else 'INCONCLUSIVE'
    if len(relative)==10 and not fail:
        rng=random.Random(SEED)
        samples=[sum(rng.choices(relative,k=10))/10 for _ in range(iterations)]
        ci=[quantile(samples,.025),quantile(samples,.975)]
        state='WITHIN_2_PERCENT' if ci[1]<=.02 else 'EXCEEDS_2_PERCENT' if ci[0]>.02 else 'INCONCLUSIVE_CI_CROSSES_2_PERCENT'
    return {'scope':'incremental_GPU_sampler_only','scope_caveat':'Production logging and HTTP collection remain enabled in both arms; full collector overhead is not measured.',
            'recorded_n':len(selected),'planned_pairs':10,'eligible_pairs':len(relative),'status':state,'threshold_relative_wall':.02,
            'paired_mean_relative_wall_on_minus_off':sum(relative)/len(relative) if relative else None,
            'paired_mean_absolute_wall_difference_s':sum(absolute)/len(absolute) if absolute else None,
            'paired_bootstrap_95_ci_relative_wall':ci,'bootstrap_iterations':iterations if ci else 0,'seed':SEED,
            'failure_reasons':dict(fail),'optimization_qualification':False}

def read_json(path):
    try:return json.loads(path.read_text())
    except (OSError,ValueError):raise SchemaError('Missing or invalid required JSON artifact') from None

def build_report(root,verify_raw=False,iterations=BOOTSTRAPS):
    root=Path(root);manifest=read_json(root/'manifest.json')
    if not isinstance(manifest,dict) or type(manifest.get('schema_version')) is not int or manifest.get('schema_version')!=1:raise SchemaError('Unknown manifest schema')
    contract={'records_schema_version':1,'expected_pi_cases':44,'pi_repetitions':5,'planned_core_cells':672,'executable_core_cells':660,'unrepresentable_core_cells':12,'profile':'B29_UNCHANGED_ARGV'}
    if any(manifest.get(k)!=v for k,v in contract.items()):raise SchemaError('Missing or incompatible declared analysis plan')
    rows=[];ids=set()
    try:lines=(root/'records.jsonl').read_text().splitlines()
    except OSError:raise SchemaError('Missing records') from None
    for line in lines:
        try:row=validate(json.loads(line))
        except (ValueError,TypeError,AttributeError):raise SchemaError('Invalid durable record; no report qualification permitted') from None
        if row['id'] in ids:raise SchemaError('Duplicate durable ID')
        ids.add(row['id']);rows.append(row)
    raw_errors=[]
    if verify_raw:
        for row in rows:
            # Never trust metadata paths or allow traversal outside the run root.
            directory=root/'requests'/row['id']
            candidates=[directory/'raw.json.gz']+list(directory.glob('attempt-*/raw.json.gz'))
            if not any(p.is_file() and digest(p.read_bytes())==row['raw_sha256'] for p in candidates):
                raw_errors.append(row['id']);row['failures']=row['failures']+['RAW_HASH_MISMATCH']
    core=[r for r in rows if r['group']=='core'];cells=collections.defaultdict(list)
    for r in core:cells[cell_key(r)].append(r)
    cell_reports=[];planned=executable=unrep=0;missing=0
    documented_unrep=set()
    for path in (root/'unrepresentable').glob('*.json'):
        info=read_json(path)
        if info.get('status')!='UNREPRESENTABLE' or info.get('target_prompt_tokens')!=256 or info.get('workload')!='tool_json' or not numeric(info.get('minimum_prompt_tokens')) or info['minimum_prompt_tokens']<=256:
            raise SchemaError('Unexpected unrepresentable contract')
        documented_unrep.add((256,'tool_json'))
    for p in LENGTHS:
        for o in [128,512,2048]:
            for w in WORKLOADS:
                for track in TRACKS:
                    for cache in CACHES:
                        planned+=1;key=(p,o,w,track,cache);values=cells[key];summary=stats(values);expected=expected_repeats(p,o)
                        if p==256 and w=='tool_json':
                            unrep+=1;state='UNREPRESENTABLE' if (p,w) in documented_unrep else 'BLOCKED_MISSING_UNREPRESENTABLE_EVIDENCE'
                            if values:state='BLOCKED_UNEXPECTED_UNREPRESENTABLE_MEASUREMENT'
                        else:
                            executable+=1
                            design=[(r['extra']['block'],r['extra']['repetition']) for r in values]
                            reps=7 if p==256 and o==512 else 5 if o==512 else 4
                            expected_design={(b,r) for b in range(5) for r in range(reps)}
                            missing+=len(expected_design-set(design))
                            state='MEASURED' if len(values)==expected and set(design)==expected_design and summary['eligible_n']==expected else 'INCONCLUSIVE'
                        cell_reports.append({'P':p,'O':o,'workload':w,'track':track,'cache':cache,'planned_n':0 if p==256 and w=='tool_json' else expected,
                                             'status':state,**summary})
    strata=[];stratum_ci={}
    for p in LENGTHS:
        for o in [128,512,2048]:
            ws=WORKLOADS[:3] if p==256 else WORKLOADS
            for track in TRACKS:
                for cache in CACHES:
                    values=[r for r in core if r['target_prompt_tokens']==p and r['requested_output_tokens']==o and r['extra']['track']==track and r['cache']==cache]
                    selected_cells=[c for c in cell_reports if c['P']==p and c['O']==o and c['track']==track and c['cache']==cache and c['workload'] in ws]
                    complete=all(c['status']=='MEASURED' for c in selected_cells)
                    ci=cluster_ci(values,iterations) if complete else {'status':'INCONCLUSIVE','reason':'INCOMPLETE_FIXED_CORE_DESIGN','iterations':0}
                    stratum_ci[p,o,track,cache]=ci
                    summary=stats(values)
                    # Only the separately qualified O512 fixed-mix buckets may emit p95.
                    summary['elapsed_p95_s']=None
                    strata.append({'P':p,'O':o,'track':track,'cache':cache,'status':'MEASURED' if complete else 'INCONCLUSIVE',
                                   **summary,'cluster_bootstrap_95_ci':ci})
    buckets=[]
    for p in LENGTHS:
        ws=WORKLOADS[:3] if p==256 else WORKLOADS
        per=35 if p==256 else 25
        for track in TRACKS:
            for cache in CACHES:
                values=[r for r in core if r['target_prompt_tokens']==p and r['requested_output_tokens']==512 and r['extra']['track']==track and r['cache']==cache]
                summary=stats(values);valid=[r for r in values if not reasons(r)]
                actual=collections.Counter(r['extra']['workload'] for r in valid)
                bucket_name=f'P{p}-O512-{track}-equal{len(ws)}workload'
                declared=all(r['extra']['p95_bucket']==bucket_name for r in values)
                cells_ok=all(c['status']=='MEASURED' for c in cell_reports if c['P']==p and c['O']==512 and c['track']==track and c['cache']==cache and c['workload'] in ws)
                qualified=declared and cells_ok and actual=={w:per for w in ws} and len(values)==len(ws)*per
                summary['elapsed_p95_s']=quantile([r['elapsed_s'] for r in valid],.95) if qualified else None
                buckets.append({'P':p,'O':512,'track':track,'cache':cache,'workload_mix':{w:per for w in ws},
                                'planned_n':len(ws)*per,'status':'ESTIMABLE' if qualified else 'INCONCLUSIVE',**summary,
                                'cluster_bootstrap_95_ci':stratum_ci[p,512,track,cache] if qualified else {'status':'INCONCLUSIVE','reason':'FIXED_MIX_OR_COMPLETE_DESIGN_NOT_MET','iterations':0}})
    statuses={}
    for name in ['status.json','watchdog.json']:
        if (root/name).exists():
            value=read_json(root/name);state=value.get('state')
            if not isinstance(state,str) or not re.fullmatch('[A-Z][A-Z0-9_]*',state):raise SchemaError('Invalid supervisor state')
            statuses[name]={'state':state,'sha256':digest((root/name).read_bytes())}
        else:statuses[name]={'state':'MISSING'}
    applicability=read_json(root/'applicability.json') if (root/'applicability.json').exists() else {}
    pi=[r for r in rows if r['group']=='pi_teacher_forced']
    pi_blocks=collections.Counter(r['extra'].get('block') for r in pi)
    pi_unique=collections.Counter((r['extra'].get('source_sha256'),r['extra'].get('entry_id')) for r in pi)
    pi_design_ok=(len(pi)==220 and len(pi_unique)==44 and all(n==5 for n in pi_unique.values()) and all(
        {(r['extra'].get('source_sha256'),r['extra'].get('entry_id')) for r in pi if r['extra'].get('block')==b}==set(pi_unique) for b in range(5)) and all(not reasons(r) for r in pi))
    groups={g:stats([r for r in rows if r['group']==g]) for g in sorted({r['group'] for r in rows})}
    return {'schema_version':1,'qualification':'BLOCKED_PENDING_REQUIRED_BASELINE_GATES',
            'optimization_qualification':False,'stage_completion_is_baseline_pass':False,
            'manifest_sha256':digest((root/'manifest.json').read_bytes()),'records_sha256':digest((root/'records.jsonl').read_bytes()),
            'plan':{'planned_cells':planned,'executable_cells':executable,'unrepresentable_cells':unrep,
                    'documented_unrepresentable_cells':12 if documented_unrep else 0,'missing_core_requests':missing,
                    'fully_measured_executable_cells':sum(c['status']=='MEASURED' for c in cell_reports)},
            'groups':groups,'core_strata':strata,'unavailable_metric_observations':{k:sum(k in r.get('unavailable_metrics',{}) for r in rows) for k in sorted(MISSING_METRICS)},'cells':cell_reports,'p95_buckets':buckets,'frozen_wire_AA':aa_report(rows,iterations),'observer_overhead':observer_report(rows,iterations),
            'pi':{'planned_cases':44,'planned_blocks':5,'planned_requests':220,'recorded_requests':len(pi),
                  'eligible_requests':sum(not reasons(r) for r in pi),'unique_entries':len(pi_unique),
                  'requests_by_block':{str(k):v for k,v in pi_blocks.items()},
                  'status':'OBSERVATIONS_RECORDED_NOT_TASK_COMPLETION' if pi_design_ok else 'INCONCLUSIVE',
                  'closed_loop':'PENDING_SEPARATE_ISOLATED_FIXTURE_REPORT'},
            'supervision':statuses,'applicability':{'artifact_present':bool(applicability),'sha256':digest((root/'applicability.json').read_bytes()) if applicability else None,
                'required_unfinished_gates':['SERVICE_COLD_RESTART','RESTART_RECOVERY','CLOSED_LOOP_20x3','UNOBSERVABLE_METRIC_APPLICABILITY_REVIEW','FINAL_DEPLOYMENT_IDENTITY_REVIEW']},
            'raw_verification':{'mode':'SHA256_BYTES_VERIFIED' if verify_raw else 'RECORDED_SHA_ONLY_NOT_REHASHED','mismatched_or_missing_ids':raw_errors},
            'evidence_pointers':{'private_raw_directory':'requests/','error_artifact_present':(root/'failure.txt').exists(),
                                 'deployment_fingerprint_files':sorted(p.name for p in (root/'fingerprints').glob('*.json'))},
            'interpretation':['Failed and ineligible requests remain in recorded denominators. Null means missing or ineligible, not zero.',
                              'Token samples and related turns are not independent replicates. Cluster CI resamples blocks and whole workloads.',
                              'Numeric p95 is measurement evidence only; stage all completion never establishes full baseline PASS.']}

def markdown(report):
    p=report['plan'];lines=['# B29 baseline evidence report','',f"Status: {report['qualification']}",'',
       f"Matrix: {p['planned_cells']} planned cells; {p['executable_cells']} executable; {p['documented_unrepresentable_cells']}/{p['unrepresentable_cells']} documented unrepresentable.",
       f"Fully measured executable cells: {p['fully_measured_executable_cells']}; missing requests: {p['missing_core_requests']}.",'',
       '## P95 fixed workload buckets','','| P | Track | Cache | Recorded / eligible | Status | P95 seconds |','|---:|---|---|---:|---|---:|']
    for b in report['p95_buckets']:lines.append(f"| {b['P']} | {b['track']} | {b['cache']} | {b['recorded_n']} / {b['eligible_n']} | {b['status']} | {b['elapsed_p95_s']} |")
    lines+=['','Pi fixed replay: '+str(report['pi']['recorded_requests'])+'/220 recorded. Closed-loop task completion remains separately pending.',
            '', 'Failures, missing measurements, and unobservable metric gaps are retained in report.json. Raw request/response bodies are private and omitted.',
            '', 'A finished measurement stage and an estimable p95 are not full baseline acceptance or optimization qualification.']
    return '\n'.join(lines)+'\n'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--output');parser.add_argument('--verify-raw',action='store_true');args=parser.parse_args()
    output=Path(args.output or args.root);output.mkdir(parents=True,exist_ok=True)
    try:report=build_report(args.root,args.verify_raw)
    except SchemaError as exc:
        report={'schema_version':1,'qualification':'BLOCKED_INVALID_EVIDENCE_SCHEMA','error':str(exc),'optimization_qualification':False}
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');(output/'report.md').write_text('# B29 baseline evidence report\n\nBLOCKED: invalid or missing evidence schema. No numeric qualification emitted.\n');return 2
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');(output/'report.md').write_text(markdown(report));return 0
if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
"""Strict paired summary for normalized benchmark rows; never grants an NInfer gate."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable

MODES={'legacy','single-pass','incremental'}
HASH=re.compile(r'^[0-9a-f]{64}$')

def quantile(values: Iterable[float], q: float) -> float | None:
    """Linear interpolation (Hyndman–Fan type 7); empty is missing, not zero."""
    if not 0 <= q <= 1: raise ValueError('quantile must be in [0,1]')
    vals=sorted(values)
    if not vals:return None
    pos=(len(vals)-1)*q
    lo=int(pos);hi=min(lo+1,len(vals)-1)
    return vals[lo]+(vals[hi]-vals[lo])*(pos-lo)

def number(v: Any, name: str, optional: bool=False) -> float | None:
    if v is None and optional:return None
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:
        raise ValueError(f'{name} must be a finite nonnegative number')
    return float(v)

def validate_row(row: Any) -> dict:
    if not isinstance(row,dict):raise ValueError('row must be an object')
    required=('schema_version','pair_id','session_id','mode','input_sha256','resources_sha256','prompt_tokens','cache_kind','cohort','tokenize_seconds','status','oracle_match')
    for name in required:
        if name not in row:raise ValueError(f'missing required field: {name}')
    if isinstance(row['schema_version'],bool) or row['schema_version']!=1:raise ValueError('schema_version must be 1')
    for name in ('pair_id','session_id'):
        if not isinstance(row[name],str) or not row[name]:raise ValueError(f'{name} must be a nonempty string')
    if not isinstance(row['mode'],str) or row['mode'] not in MODES:raise ValueError('unsupported mode')
    if not isinstance(row['cache_kind'],str) or row['cache_kind'] not in {'cold','warm','none'}:raise ValueError('unsupported cache_kind')
    if not isinstance(row['cohort'],str) or row['cohort'] not in {'synthetic','replay','live'}:raise ValueError('unsupported cohort')
    if not isinstance(row['status'],str) or row['status'] not in {'ok','error','cancelled','rejected'}:raise ValueError('unsupported status')
    if row['oracle_match'] is not None and type(row['oracle_match']) is not bool:raise ValueError('oracle_match must be bool or null')
    for name in ('input_sha256','resources_sha256'):
        if not isinstance(row[name],str) or not HASH.fullmatch(row[name]):raise ValueError(f'{name} must be a lowercase SHA-256')
    if type(row['prompt_tokens']) is not int or row['prompt_tokens']<0:raise ValueError('prompt_tokens must be a nonnegative integer')
    number(row['tokenize_seconds'],'tokenize_seconds',optional=row['status']!='ok')
    for name in ('prepare_seconds','ttft_seconds','decode_tps'):
        if name in row:number(row[name],name,True)
    for name in ('render_bytes','boundary_queries','reused_prefix_tokens','suffix_input_bytes'):
        if name in row and (type(row[name]) is not int or row[name]<0):raise ValueError(f'{name} must be a nonnegative integer')
    allowed=set(required)|{'prepare_seconds','ttft_seconds','decode_tps','render_bytes','boundary_queries','reused_prefix_tokens','suffix_input_bytes','notes'}
    unknown=set(row)-allowed
    if unknown:raise ValueError('unknown normalized fields: '+','.join(sorted(unknown)))
    if 'notes' in row and not isinstance(row['notes'],str):raise ValueError('notes must be a string')
    return row

def band(n: int) -> str:
    for end,name in [(8000,'<8K'),(32000,'8–32K'),(64000,'32–64K'),(120000,'64–120K'),(185000,'120–185K')]:
        if n<end:return name
    return '>=185K'

def metric(pairs: list, key: str) -> dict:
    values=[(a[key],b[key]) for a,b in pairs if a.get(key) is not None and b.get(key) is not None]
    return {'complete_pairs':len(values),
            'baseline_p50':quantile([a for a,b in values],.5),
            'candidate_p50':quantile([b for a,b in values],.5),
            'baseline_p90':quantile([a for a,b in values],.9),
            'candidate_p90':quantile([b for a,b in values],.9),
            'paired_median_saved_seconds':quantile([a-b for a,b in values],.5),
            'paired_median_speedup':quantile([a/b for a,b in values if a>0 and b>0],.5)}

def summarize(rows: list[dict], baseline: str, candidate: str) -> dict:
    if baseline not in MODES or candidate not in MODES or baseline==candidate:raise ValueError('select two different supported modes')
    pairs_by_id=defaultdict(dict);status_counts={baseline:Counter(),candidate:Counter()};unknown=0;bad=0
    for raw in rows:
        row=validate_row(raw)
        if row['mode'] not in {baseline,candidate}:continue
        pid=row['pair_id'];mode=row['mode']
        if mode in pairs_by_id[pid]:raise ValueError(f'duplicate pair/mode: {pid}/{mode}')
        pairs_by_id[pid][mode]=row;status_counts[mode][row['status']]+=1
        unknown+=row['oracle_match'] is None;bad+=row['oracle_match'] is False
    if not pairs_by_id:raise ValueError('no rows for requested modes')
    pairs=[];eligible=[];strata=defaultdict(list);sessions=defaultdict(list)
    same=('session_id','input_sha256','resources_sha256','prompt_tokens','cache_kind','cohort')
    for pid,entries in sorted(pairs_by_id.items()):
        if baseline not in entries or candidate not in entries:raise ValueError(f'unpaired row: {pid}')
        a,b=entries[baseline],entries[candidate]
        for name in same:
            if a[name]!=b[name]:raise ValueError(f'pair {pid} mismatched {name}')
        pairs.append((a,b))
        if a['status']=='ok' and b['status']=='ok' and a['oracle_match'] is not False and b['oracle_match'] is not False:
            eligible.append((a,b));strata[(a['cohort'],a['cache_kind'],band(a['prompt_tokens']))].append((a,b));sessions[a['session_id']].append((a,b))
    keys=('tokenize_seconds','prepare_seconds','ttft_seconds')
    return {'status':'ANALYSIS_ONLY','baseline':baseline,'candidate':candidate,'paired_total':len(pairs),
            'performance_eligible_pairs':len(eligible),'semantic_mismatch_records':bad,'oracle_unknown_records':unknown,
            'status_counts':{k:dict(v) for k,v in status_counts.items()},
            'metrics':{k:metric(eligible,k) for k in keys},
            'strata':[{'cohort':c,'cache_kind':w,'depth_band':d,'pairs':len(ps),'metrics':{k:metric(ps,k) for k in keys}} for (c,w,d),ps in sorted(strata.items())],
            'sessions':[{'session_id':s,'pairs':len(ps),'metrics':{k:metric(ps,k) for k in keys}} for s,ps in sorted(sessions.items())],
            'limitations':['No automatic performance or correctness gate decision.','Unknown oracle results remain visible and cannot qualify G1.','Percentiles use linear interpolation type 7; pair_id must uniquely include repetition.','Do not sum or subtract independent percentile summaries to infer phase time.','Depth bands use decimal token counts; record exact prompt_tokens.']}

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('--baseline',default='legacy',choices=sorted(MODES));p.add_argument('--candidate',default='single-pass',choices=sorted(MODES));p.add_argument('--output',type=Path)
    args=p.parse_args()
    try:
        rows=[]
        with args.input.open(encoding='utf-8') as f:
            for i,line in enumerate(f,1):
                if not line.strip():continue
                try:rows.append(validate_row(json.loads(line)))
                except (ValueError,TypeError) as e:raise ValueError(f'line {i}: {e}') from e
        text=json.dumps(summarize(rows,args.baseline,args.candidate),ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        if args.output:args.output.write_text(text,encoding='utf-8')
        else:print(text,end='')
        return 0
    except (ValueError,OSError) as e:p.exit(2,f'error: {e}\n')
if __name__=='__main__':raise SystemExit(main())

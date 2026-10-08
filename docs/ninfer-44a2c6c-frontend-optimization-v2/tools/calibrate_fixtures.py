#!/usr/bin/env python3
"""Validate offline tokenizer measurements against frozen input identities. Does not tokenize."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

def calibrate(inputs:list[dict],measurements:list[dict],output_reserve:int=2048)->dict:
    if type(output_reserve) is not int or output_reserve<1:raise ValueError('positive output reserve required')
    by={}
    for r in measurements:
        if r['case_id'] in by:raise ValueError('duplicate measurement')
        for k in ('prompt_tokens','render_bytes','checkpoint_hints','boundary_queries'):
            if type(r.get(k)) is not int or r[k]<0:raise ValueError(f'missing or invalid {k}')
        if not re.fullmatch('[0-9a-f]{64}',r.get('resources_sha256','')):raise ValueError('full resource hash required')
        by[r['case_id']]=r
    if not inputs or len({x['case_id'] for x in inputs})!=len(inputs):raise ValueError('empty or duplicate input')
    if set(by)!={x['case_id'] for x in inputs}:raise ValueError('measurement set does not match input set')
    if len({m['resources_sha256'] for m in by.values()}) != 1:raise ValueError('mixed resource identities in one calibration batch')
    results=[]
    for row in inputs:
        m=by[row['case_id']]
        if not re.fullmatch('[0-9a-f]{64}',row.get('input_sha256','')):raise ValueError('full input hash required')
        if 'request' in row:
            raw=json.dumps(row['request'],ensure_ascii=False,separators=(',',':')).encode()
            if hashlib.sha256(raw).hexdigest()!=row['input_sha256']:raise ValueError('request payload no longer matches input hash')
        if row['input_sha256']!=m['input_sha256']:raise ValueError('frozen input hash mismatch')
        fit=m['prompt_tokens']+output_reserve<=262144
        cpu_policy=str(row.get('declared_use','')).startswith(('CPU_ONLY','CPU_STRESS'))
        valid=fit and not cpu_policy
        use='CPU_ONLY_BY_POLICY' if cpu_policy else ('CPU_AND_HTTP' if fit else 'CPU_ONLY_OVER_CONTEXT')
        results.append({**m,'output_reserve':output_reserve,'http_eligible':valid,'validation_use':use})
    return {'status':'MEASUREMENTS_VALIDATED_NOT_HTTP_TESTED','context_capacity':262144,'cases':results}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('inputs',type=Path);p.add_argument('measurements',type=Path);p.add_argument('--output-reserve',type=int,default=2048);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:
        load=lambda f:[json.loads(s) for s in f.read_text().splitlines() if s.strip()]
        a.output.write_text(json.dumps(calibrate(load(a.inputs),load(a.measurements),a.output_reserve),ensure_ascii=False,indent=2)+'\n');return 0
    except (ValueError,OSError,KeyError) as e:p.exit(2,f'error: {e}\n')
if __name__=='__main__':raise SystemExit(main())

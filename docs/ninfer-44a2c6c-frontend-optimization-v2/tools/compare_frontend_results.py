#!/usr/bin/env python3
"""Compare independent oracle/candidate normalized outputs, including exact error contracts."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
RAW={'token_ids'}
RENDERED={'token_ids','stable_prefix_boundary','turn_rewrite_boundary','user_turn_boundary','checkpoint_hints'}
PREPARED=RENDERED|{'token_types','positions','rope_delta','identity','starts_in_reasoning','rendered_sha256'}

def index(rows:list[dict])->dict:
    out={}
    for r in rows:
        for k in ('case_id','input_sha256','resources_sha256','kind','status'):
            if k not in r:raise ValueError(f'missing {k}')
        if r['case_id'] in out:raise ValueError('duplicate case')
        for k in ('input_sha256','resources_sha256'):
            if not re.fullmatch('[0-9a-f]{64}',r[k]):raise ValueError(f'invalid {k}')
        if r['status']=='OK':
            fields={'raw':RAW,'rendered':RENDERED,'prepared':PREPARED,'count':{'count'}}.get(r['kind'])
            if fields is None or not isinstance(r.get('semantic'),dict) or not fields<=r['semantic'].keys():raise ValueError('missing semantic contract fields')
            if 'token_ids' in r['semantic'] and (not isinstance(r['semantic']['token_ids'],list) or any(type(x) is not int for x in r['semantic']['token_ids'])):raise ValueError('invalid token IDs')
        elif r['status']=='ERROR':
            if not isinstance(r.get('error'),dict) or not {'phase','class','message'}<=r['error'].keys():raise ValueError('incomplete error contract')
        else:raise ValueError('status must be OK or ERROR; skipped input cannot qualify')
        out[r['case_id']]=r
    return out

def difference(a,b,path='semantic'):
    if type(a)!=type(b):return path
    if isinstance(a,dict):
        if a.keys()!=b.keys():return path+'.keys'
        for k in a:
            d=difference(a[k],b[k],path+'.'+k)
            if d:return d
    elif isinstance(a,list):
        if len(a)!=len(b):return path+'.length'
        for i,(x,y) in enumerate(zip(a,b)):
            d=difference(x,y,f'{path}[{i}]')
            if d:return d
    elif a!=b:return path
    return None

def compare(baseline:list[dict],candidate:list[dict])->dict:
    a=index(baseline);b=index(candidate)
    if not a or a.keys()!=b.keys():raise ValueError('empty or incomplete pairing')
    mismatches=[]
    for k,r in a.items():
        s=b[k]
        if any(r[x]!=s[x] for x in ('input_sha256','resources_sha256','kind')):raise ValueError('input/resource/entrypoint identity mismatch')
        if r['status']!=s['status']:d='status'
        else:
            field='semantic' if r['status']=='OK' else 'error';d=difference(r[field],s[field],field)
        if d:mismatches.append({'case_id':k,'field':d})
    return {'status':'FAIL' if mismatches else 'PASS','scope':'SUPPLIED_OUTPUTS_ONLY','cases':len(a),'mismatches':mismatches,'product_provenance_must_be_verified_separately':True}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('baseline',type=Path);p.add_argument('candidate',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    try:
        load=lambda f:[json.loads(l) for l in f.read_text().splitlines() if l.strip()]
        result=compare(load(a.baseline),load(a.candidate));t=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
        if a.output:a.output.write_text(t)
        else:print(t,end='')
        return 0 if result['status']=='PASS' else 1
    except (ValueError,OSError,TypeError) as e:p.exit(2,f'error: {e}\n')
if __name__=='__main__':raise SystemExit(main())

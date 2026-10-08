#!/usr/bin/env python3
"""Strict schema-20 metadata aggregation. No invented request bodies or causal reset labels."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, math
from pathlib import Path
BINS=[('<8K',0,8192),('8-32K',8192,32768),('32-64K',32768,65536),('64-120K',65536,120000),('120-185K',120000,185000),('>=185K',185000,float('inf'))]

def get(r,*path):
    for k in path:
        if not isinstance(r,dict) or k not in r:return None
        r=r[k]
    return r

def number(v):
    if v is None:return None
    if type(v) not in (int,float) or not math.isfinite(v) or v<0:raise ValueError('negative, nonnumeric or nonfinite measurement')
    return float(v)

def stats(values):
    v=sorted(number(x) for x in values if x is not None)
    if not v:return {'n':0,'sum':None,'p50':None,'p90':None,'min':None,'max':None}
    def q(p):
        t=(len(v)-1)*p;i=int(t);j=min(i+1,len(v)-1);return v[i]+(v[j]-v[i])*(t-i)
    return {'n':len(v),'sum':sum(v),'p50':q(.5),'p90':q(.9),'min':v[0],'max':v[-1]}

def union_seconds(intervals):
    total=0.;lo=hi=None
    for a,b in sorted(intervals):
        if lo is None:lo,hi=a,b
        elif a<=hi:hi=max(hi,b)
        else:total+=hi-lo;lo,hi=a,b
    return total+(0 if lo is None else hi-lo)

def summarize(events:list[dict])->dict:
    rows=[];seen={};duplicates=ignored=0
    for r in events:
        if r.get('schema_version')!=20 or r.get('event')!='request_done':ignored+=1;continue
        sid=r.get('server_instance_id');rid=get(r,'request','request_id')
        if rid is None:rid=get(r,'request','id')
        if rid is None:rid=r.get('request_id')
        if sid is None or rid is None:raise ValueError('server instance and request identity required for deduplication')
        key=(sid,str(rid));canonical=json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)
        if key in seen:
            if seen[key]!=canonical:raise ValueError('conflicting duplicate event')
            duplicates+=1;continue
        seen[key]=canonical
        for path in [('timestamp_unix_ms',),('timings_seconds','total'),('timings_seconds','ttft'),('timings_seconds','prepare'),('timings_seconds','prefill'),('timings_seconds','decode'),('prepare_detail','tokenize'),('result','prompt_tokens'),('result','prefix_cache_hit_tokens')]:number(get(r,*path))
        if get(r,'result','prompt_tokens') is None or r.get('timestamp_unix_ms') is None:raise ValueError('missing prompt/end timestamp')
        pt=get(r,'result','prompt_tokens');hit=get(r,'result','prefix_cache_hit_tokens')
        if hit is not None and hit>pt:raise ValueError('cached token count exceeds prompt')
        rows.append(r)
    rows.sort(key=lambda r:r['timestamp_unix_ms'])
    def table(sel):
        return {'n':len(sel),'tokenize':stats([get(r,'prepare_detail','tokenize') for r in sel]),'prefill':stats([get(r,'timings_seconds','prefill') for r in sel]),'ttft':stats([get(r,'timings_seconds','ttft') for r in sel]),
        'rendered_utf8_bytes':stats([get(r,'request','rendered_bytes') if get(r,'request','rendered_bytes') is not None else get(r,'request','rendered_chars') for r in sel]),
        'cache_ratio':stats([get(r,'result','prefix_cache_hit_tokens')/get(r,'result','prompt_tokens') for r in sel if get(r,'result','prompt_tokens') and get(r,'result','prefix_cache_hit_tokens') is not None])}
    intervals=[]
    for r in rows:
        sec=get(r,'timings_seconds','total')
        if sec is not None:
            end=r['timestamp_unix_ms']/1000.;intervals.append((end-sec,end))
    paths={}
    for r in rows:paths.setdefault(get(r,'result','prefix_reuse_path') or 'UNKNOWN',[]).append(r)
    return {'status':'ANALYSIS_ONLY','schema_version':20,'requests':len(rows),'ignored_events':ignored,'duplicate_records':duplicates,'tokenize':stats([get(r,'prepare_detail','tokenize') for r in rows]),
     'summed_request_seconds':sum(b-a for a,b in intervals),'request_interval_union_seconds':union_seconds(intervals),
     'observed_span_seconds':max(b for a,b in intervals)-min(a for a,b in intervals) if intervals else None,
     'intervals_with_total':len(intervals),'reset_cause_status':'UNCLASSIFIED_METADATA_ONLY',
     'bins':{name:table([r for r in rows if lo<=get(r,'result','prompt_tokens')<hi]) for name,lo,hi in BINS},
     'reuse_paths':{k:table(v) for k,v in sorted(paths.items())},
     'warnings':['Summed request durations are NOT physical CPU/GPU busy time.','Reset causes require session identity, cache admission/eviction evidence and controlled reproduction.','No latency gain or GPU correctness is inferred from stop_token.']}

def timestamp(s):
    v=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
    if v.tzinfo is None:raise ValueError('time filter must include timezone')
    return int(v.timestamp()*1000)

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('paths',nargs='+',type=Path);p.add_argument('--from-time');p.add_argument('--to-time');p.add_argument('--output',type=Path);a=p.parse_args()
    try:
        lo=timestamp(a.from_time) if a.from_time else None;hi=timestamp(a.to_time) if a.to_time else None
        rows=[];bad=[];receipts={}
        for path in a.paths:
            for f in sorted(path.glob('ninfer-request.jsonl*')) if path.is_dir() else [path]:
                receipts[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
                for i,line in enumerate(f.read_text().splitlines(),1):
                    if not line.strip():continue
                    try:r=json.loads(line)
                    except ValueError:bad.append({'file':str(f),'line':i});continue
                    t=r.get('timestamp_unix_ms')
                    if (lo is not None and (t is None or t<lo)) or (hi is not None and (t is None or t>=hi)):continue
                    rows.append(r)
        if bad:raise ValueError(f'{len(bad)} malformed lines; fix/explicitly exclude them, do not silently drop')
        o=summarize(rows);o['input_hashes']=receipts;o['window']={'from_inclusive':a.from_time,'to_exclusive':a.to_time};s=json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        if a.output:a.output.write_text(s)
        else:print(s,end='')
        return 0
    except (ValueError,OSError,TypeError,KeyError) as e:p.exit(2,f'error: {e}\n')
if __name__=='__main__':raise SystemExit(main())

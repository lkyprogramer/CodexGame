"""OpenAI-compatible SSE collector. No server means a failure, never synthetic success."""
from __future__ import annotations
import argparse, json, os, sys, time, urllib.request, urllib.error, uuid
from pathlib import Path
from .core import sse_events, collect_stream

def probe(base: str, payload: dict, *, endpoint='completions', key='', timeout=240, trace=False):
    ident=str(uuid.uuid4());data={**payload,'stream':True,'stream_options':{'include_usage':True}}
    headers={'Content-Type':'application/json','X-Request-ID':ident}
    if key:headers['Authorization']='Bearer '+key
    req=urllib.request.Request(base.rstrip('/')+'/'+endpoint,data=json.dumps(data).encode(),headers=headers)
    begin=time.monotonic();events=[]
    try:
        with urllib.request.urlopen(req,timeout=timeout) as res:
            def chunks():
                while True:
                    b=res.read1(8192)
                    if not b:break
                    yield b
            for e in sse_events(chunks()):events.append((time.monotonic()-begin,e))
        result=collect_stream(events,time.monotonic()-begin)
    except Exception as e:
        result={'status':'ERROR','error':str(e),'wall_s':time.monotonic()-begin}
    result['request_id']=ident;result['requested_prompt_tokens']=len(payload.get('prompt',[])) if isinstance(payload.get('prompt'),list) else None
    result['events']=events
    # Optional developer-only trace API implemented in T14. No trace => no performance certification.
    if trace:
        u=base.removesuffix('/v1').rstrip('/')+'/poc/v1/traces/'+ident
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers={k:v for k,v in headers.items() if k!='Content-Type'}),timeout=15) as res:
                result['engine_trace']=json.load(res)
        except Exception as e:result['engine_trace_error']=str(e)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:18041/v1');p.add_argument('--payload',required=True);p.add_argument('--out',required=True);p.add_argument('--endpoint',choices=['completions','chat/completions'],default='completions');p.add_argument('--timeout',type=int,default=240);p.add_argument('--trace',action='store_true');a=p.parse_args()
    data=json.loads(Path(a.payload).read_text());r=probe(a.base_url,data,endpoint=a.endpoint,key=os.environ.get('POC_API_KEY',''),timeout=a.timeout,trace=a.trace)
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ('events','content','reasoning','engine_trace')},ensure_ascii=False),flush=True)
    return 0 if r['status']=='COMPLETE' else 2
if __name__=='__main__':sys.exit(main())

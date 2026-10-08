"""OpenAI-style SSE probe. Reports HTTP timing, never treats frames as tokens."""
import argparse,codecs,json,os,time,urllib.request
from pathlib import Path

class SSEDecoder:
    def __init__(self): self.decoder=codecs.getincrementaldecoder('utf-8')(); self.text=''
    def feed(self,data):
        self.text+=self.decoder.decode(data); self.text=self.text.replace('\r\n','\n')
        out=[]
        while '\n\n' in self.text:
            event,self.text=self.text.split('\n\n',1)
            body='\n'.join(line[5:].lstrip() for line in event.split('\n') if line.startswith('data:'))
            if not body: continue
            if body=='[DONE]': out.append(body); continue
            try: out.append(json.loads(body))
            except json.JSONDecodeError as e: raise ValueError('invalid SSE JSON') from e
        return out

def probe(url,body,timeout=240,api_key=None):
    body=dict(body,stream=True,stream_options={'include_usage':True})
    req=urllib.request.Request(url.rstrip('/')+'/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}|({'Authorization':'Bearer '+api_key} if api_key else {}))
    t=time.perf_counter(); first=None; frames=0; usage=None; done=False; final_finish=None; timings={}; dec=SSEDecoder(); errors=[]; content=[]; reasoning_chars=0; tools={}
    with urllib.request.urlopen(req,timeout=timeout) as r:
        while True:
            chunk=r.read1(8192)
            if not chunk: break
            for event in dec.feed(chunk):
                if event=='[DONE]': done=True; continue
                frames+=1
                if 'error' in event: errors.append(event['error'])
                if event.get('usage'): usage=event['usage']
                if event.get('timings'): timings=event['timings']
                for choice in event.get('choices',[]):
                    delta=choice.get('delta') or {}
                    txt=delta.get('content') or ''; rs=delta.get('reasoning_content') or delta.get('reasoning') or ''
                    tc=delta.get('tool_calls') or []
                    if first is None and (txt or rs or tc):first=time.perf_counter()-t
                    content.append(txt); reasoning_chars+=len(rs)
                    if choice.get('finish_reason') is not None:final_finish=choice['finish_reason']
                    for x in tc:
                        idx=x.get('index',0); d=tools.setdefault(idx,{'name':'','arguments':''}); f=x.get('function') or {}
                        d['name']+=f.get('name') or ''; d['arguments']+=f.get('arguments') or ''
    wall=time.perf_counter()-t
    out={'source':'HTTP_SSE','wall_s':wall,'ttft_s':first,'usage':usage,'timings':timings,'sse_frames':frames,'done':done,'finish_reason':final_finish,'reasoning_chars':reasoning_chars,'tool_calls':len(tools),'tool_arguments_valid':all(_is_json(x['arguments']) for x in tools.values()),'http_errors_present':bool(errors),'content_chars':sum(map(len,content)),'note':'Client timing only; speculation bursts and transport are included. Not engine decode throughput.'}
    if usage and type(usage.get('completion_tokens')) is int and first is not None and wall>first:
        out['client_decode_estimate_tps']=(max(0,usage['completion_tokens']-1))/(wall-first)
    return out,''.join(content)

def _is_json(s):
    try:json.loads(s);return True
    except (json.JSONDecodeError,TypeError):return False

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--request',required=True);p.add_argument('--out',required=True);p.add_argument('--timeout',type=int,default=240);p.add_argument('--expect');a=p.parse_args()
    body=json.loads(Path(a.request).read_text()); out,text=probe(a.url,body,a.timeout,os.environ.get('LAB_API_KEY'))
    if a.expect is not None:out['expected_substring_found']=a.expect in text
    dest=Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');dest.chmod(0o600)
    if not out['done'] or out['http_errors_present']:raise SystemExit(1)

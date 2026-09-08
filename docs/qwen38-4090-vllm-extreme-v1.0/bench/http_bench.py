#!/usr/bin/env python3
import os, sys, json, time, urllib.request, urllib.error, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RES=ROOT/'results'; CACHE=ROOT/'.state/prompts'; RES.mkdir(exist_ok=True); CACHE.mkdir(parents=True,exist_ok=True)

def envfile():
    p=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'configs/benchmark.env'
    if not p.exists(): p=ROOT/'configs/benchmark.env.example'
    d={}
    for line in p.read_text().splitlines():
        line=line.strip()
        if line and not line.startswith('#') and '=' in line:
            k,v=line.split('=',1); d[k]=v
    return d
E=envfile(); URL=E.get('SERVER_URL','http://127.0.0.1:18020/v1').rstrip('/'); BASE=URL[:-3] if URL.endswith('/v1') else URL
MODEL=E.get('MODEL_ID','qwen3.8-27b'); KEY=E.get('API_KEY','local-qwen-bench')

def post(url, body, stream=False, timeout=900):
    data=json.dumps(body).encode(); req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json','Authorization':'Bearer '+KEY})
    return urllib.request.urlopen(req,timeout=timeout)

def tok_count(text):
    try:
        with post(BASE+'/tokenize', {'model':MODEL,'prompt':text}, timeout=120) as r:
            obj=json.loads(r.read())
        for k in ('count','num_tokens'):
            if isinstance(obj.get(k),int): return obj[k]
        if isinstance(obj.get('tokens'),list): return len(obj['tokens'])
    except Exception:
        pass
    return max(1,len(text)//4)

def make_lines(n, needle):
    lines=[]
    for i in range(n):
        if i == int(n*0.86):
            lines.append(f'// RELEASE_NEEDLE={needle} do-not-alter marker for long-context retrieval.\n')
        lines.append(f'// repo-line {i:07d} module=exam-runtime state=ACTIVE tenant=t{i%97:02d} invariant=idempotent-reconnect; public final long tickMs={(i%7+1)*50};\n')
    return ''.join(lines)

def prompt_for(target):
    p=CACHE/f'{target}.txt'
    meta=CACHE/f'{target}.json'
    if p.exists() and meta.exists(): return p.read_text(), json.loads(meta.read_text())
    needle=f'JAVA-AGENT-{target}-N7Q4'
    n=max(100,target//18)
    best=None
    for _ in range(5):
        text=make_lines(n,needle)
        c=tok_count(text)
        best=(text,c)
        if abs(c-target)/target < .025: break
        n=max(10,int(n*target/max(c,1)))
    text,c=best
    p.write_text(text); meta.write_text(json.dumps({'target':target,'actual_estimate':c,'needle':needle}))
    return text, {'target':target,'actual_estimate':c,'needle':needle}

def stream_chat(messages, max_tokens, tag):
    body={'model':MODEL,'messages':messages,'max_tokens':max_tokens,'temperature':0.2,'stream':True,'stream_options':{'include_usage':True}}
    t0=time.monotonic(); first=None; text=[]; usage={}; err=None
    try:
        with post(URL+'/chat/completions',body,stream=True,timeout=900) as r:
            for raw in r:
                line=raw.decode('utf-8','replace').strip()
                if not line.startswith('data:'): continue
                dat=line[5:].strip()
                if dat=='[DONE]': break
                try: obj=json.loads(dat)
                except Exception: continue
                if obj.get('usage'): usage=obj['usage']
                for ch in obj.get('choices') or []:
                    d=ch.get('delta') or {}
                    s=(d.get('content') or '') + (d.get('reasoning_content') or '')
                    if s:
                        if first is None: first=time.monotonic()
                        text.append(s)
    except Exception as e: err=repr(e)
    end=time.monotonic(); out=''.join(text)
    pt=usage.get('prompt_tokens') or usage.get('input_tokens')
    ct=usage.get('completion_tokens') or usage.get('output_tokens')
    if not ct: ct=max(1,len(out)//4)
    ttft=(first-t0) if first else None
    dec=((ct/(end-first)) if first and end>first else 0.0)
    details=usage.get('prompt_tokens_details') or usage.get('input_tokens_details') or {}
    cached=details.get('cached_tokens',0) if isinstance(details,dict) else 0
    return {'tag':tag,'ok':err is None,'error':err,'prompt_tokens':pt,'completion_tokens':ct,'cached_tokens':cached,'ttft_s':ttft,'wall_s':end-t0,'decode_tps':dec,'text':out[:4000]}

def main():
    quick=os.getenv('QUICK_ONLY','0')=='1'
    specs=[('short',int(E.get('SHORT_PROMPT_TOKENS',4096)),int(E.get('SHORT_OUTPUT_TOKENS',768))),
           ('mid',int(E.get('MID_PROMPT_TOKENS',64000)),int(E.get('MID_OUTPUT_TOKENS',512)))]
    if not quick:
        specs += [('long',int(E.get('LONG_PROMPT_TOKENS',120000)),int(E.get('LONG_OUTPUT_TOKENS',384))),
                  ('deep',int(E.get('DEEP_PROMPT_TOKENS',185000)),int(E.get('DEEP_OUTPUT_TOKENS',256)))]
    rows=[]
    for tag,target,outn in specs:
        print(f'[http] building {tag} target={target}',flush=True)
        corpus,meta=prompt_for(target)
        ask=(f'You are reviewing a long Java backend repository dump. The dump contains exactly one RELEASE_NEEDLE. '
             f'First print the exact RELEASE_NEEDLE value. Then write a concise Java reliability review with enough detail to keep generating until the output budget if possible.\n\n{corpus}')
        row=stream_chat([{'role':'user','content':ask}],outn,tag)
        row['target_prompt_tokens']=target; row['needle']=meta['needle']; row['needle_ok']=meta['needle'] in row['text']
        rows.append(row)
        print(f"[http] {tag}: prompt={row['prompt_tokens']} ttft={row['ttft_s']} decode={row['decode_tps']:.2f} needle={row['needle_ok']}",flush=True)
    (RES/'http_bench.json').write_text(json.dumps(rows,indent=2))
if __name__=='__main__': main()

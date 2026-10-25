from __future__ import annotations
import json, time, urllib.request, urllib.error
from .core import loopback_url


def parse_sse(lines, started=None, on_first=None, deadline=None):
    started=started or time.perf_counter()
    result={'text':'','reasoning':'','tools':[],'usage':{},'timings':{},'finish_reason':None,'first_s':None,'error':None,'done':False}
    calls={}
    try:
        for raw in lines:
            if deadline is not None and time.perf_counter()>deadline:raise TimeoutError('Absolute request deadline exceeded')
            line=raw.decode('utf-8','strict').strip() if isinstance(raw,bytes) else raw.strip()
            if not line.startswith('data:'): continue
            data=line[5:].strip()
            if data=='[DONE]': result['done']=True; break
            j=json.loads(data)
            if j.get('error'): result['error']=str(j['error'])[:1000]
            for c in j.get('choices',[]):
                d=c.get('delta') or {}
                if d.get('content') or d.get('reasoning_content') or d.get('tool_calls'):
                    if result['first_s'] is None:
                        result['first_s']=time.perf_counter()-started
                        if on_first:on_first()
                result['text']+=d.get('content') or ''
                result['reasoning']+=d.get('reasoning_content') or ''
                for tc in d.get('tool_calls',[]):
                    ix=tc.get('index',0)
                    dst=calls.setdefault(ix,{'id':'','type':'function','function':{'name':'','arguments':''}})
                    if tc.get('id'): dst['id']=tc['id']
                    fn=tc.get('function') or {}
                    dst['function']['name']+=fn.get('name') or ''
                    dst['function']['arguments']+=fn.get('arguments') or ''
                if c.get('finish_reason') is not None: result['finish_reason']=c['finish_reason']
            if j.get('usage'): result['usage']=j['usage']
            if j.get('timings'): result['timings']=j['timings']
    except Exception as e: result['error']=f'{type(e).__name__}: {e}'
    result['tools']=[calls[k] for k in sorted(calls)]
    if not result['done'] and not result['error']: result['error']='Stream ended without [DONE]'
    result['total_s']=time.perf_counter()-started
    return result


def get(base,path,key='',timeout=10):
    req=urllib.request.Request(loopback_url(base)+path,headers={'Authorization':'Bearer '+key} if key else {})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.load(r)


def chat(base,body,key='',timeout=1800,on_first=None):
    base=loopback_url(base); payload=dict(body,stream=True,stream_options={'include_usage':True})
    headers={'Content-Type':'application/json'}
    if key: headers['Authorization']='Bearer '+key
    req=urllib.request.Request(base+'/v1/chat/completions',data=json.dumps(payload,ensure_ascii=False).encode(),headers=headers)
    t=time.perf_counter()
    try:
        with urllib.request.urlopen(req,timeout=min(60,timeout)) as r: return parse_sse(r,t,on_first,t+timeout)
    except Exception as e:
        detail=e.read(4096).decode(errors='replace') if isinstance(e,urllib.error.HTTPError) else str(e)
        return {'error':f'{type(e).__name__}: {detail}','total_s':time.perf_counter()-t,'text':'','reasoning':'','tools':[],'usage':{},'timings':{},'first_s':None,'finish_reason':None,'done':False}


def measurements(r):
    u,t=r.get('usage') or {},r.get('timings') or {}
    cached=(u.get('prompt_tokens_details') or {}).get('cached_tokens',t.get('cache_n'))
    read=t.get('prompt_n')
    if read is None and u.get('prompt_tokens') is not None and cached is not None: read=u['prompt_tokens']-cached
    return {'wall_s':r.get('total_s'),'ttft_s':r.get('first_s'),
            'prompt_tokens':u.get('prompt_tokens'),'generated_tokens':u.get('completion_tokens'),
            'reused_tokens':cached,'read_tokens':read,'prompt_ms':t.get('prompt_ms'),'decode_ms':t.get('predicted_ms'),
            'prompt_tps':t.get('prompt_per_second'),'decode_tps':t.get('predicted_per_second'),
            'drafts_offered':t.get('draft_n'),'drafts_accepted':t.get('draft_n_accepted')}

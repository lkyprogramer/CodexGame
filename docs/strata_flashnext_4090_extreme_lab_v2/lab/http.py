from __future__ import annotations
import json, time, urllib.request, urllib.error, http.client, socket, threading, math
from urllib.parse import urlsplit
from .core import loopback_url


def parse_sse(lines, started=None, on_first=None, deadline=None):
    started=time.perf_counter() if started is None else started
    result={'text':'','reasoning':'','tools':[],'usage':{},'timings':{},'finish_reason':None,'first_s':None,'error':None,'done':False}
    result.update(first_reasoning_s=None, first_visible_s=None, first_tool_s=None,
                  first_tool_arguments_s=None, output_event_times_s=[], output_event_gaps_s=[])
    calls={}
    try:
        for raw in lines:
            if deadline is not None and time.perf_counter()>deadline:raise TimeoutError('Absolute request deadline exceeded')
            line=raw.decode('utf-8','strict').strip() if isinstance(raw,bytes) else raw.strip()
            if not line.startswith('data:'): continue
            data=line[5:].strip()
            if data=='[DONE]': result['done']=True; break
            j=json.loads(data)
            arrival=time.perf_counter()-started
            output_event=False
            if j.get('error'): result['error']=str(j['error'])[:1000]
            for c in j.get('choices',[]):
                d=c.get('delta') or {}
                if d.get('content') or d.get('reasoning_content') or d.get('tool_calls'):
                    output_event=True
                    if result['first_s'] is None:
                        result['first_s']=arrival
                        if on_first:on_first()
                for field, present in [('first_reasoning_s', d.get('reasoning_content')),
                                       ('first_visible_s', d.get('content')),
                                       ('first_tool_s', d.get('tool_calls')),
                                       ('first_tool_arguments_s', any(tc.get('function',{}).get('arguments') for tc in d.get('tool_calls',[])))]:
                    if present and result[field] is None:result[field]=arrival
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
            if output_event:
                if result['output_event_times_s']:
                    result['output_event_gaps_s'].append(arrival-result['output_event_times_s'][-1])
                result['output_event_times_s'].append(arrival)
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


def chat(base,body,key='',timeout=1800,on_first=None,idle_timeout_s=None):
    """Owned loopback HTTP connection; deadline includes headers, prefill and stream.

    idle_timeout_s is a socket inactivity bound. A separate watchdog interrupts
    even a partial SSE line/continuous heartbeats at the absolute timeout.
    No implicit 60-second prefill cap; the default idle bound equals timeout.
    """
    base=loopback_url(base); payload=dict(body,stream=True,stream_options={'include_usage':True})
    idle=timeout if idle_timeout_s is None else idle_timeout_s
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<=0 for x in (timeout,idle)):
        raise ValueError('Request and idle timeouts must be positive finite seconds')
    headers={'Content-Type':'application/json'}
    if key: headers['Authorization']='Bearer '+key
    address=urlsplit(base)
    connection=http.client.HTTPConnection(address.hostname,address.port or 80,timeout=min(idle,timeout))
    owned_socket={}; expired=threading.Event()
    t=time.perf_counter()
    def expire():
        expired.set()
        sock=owned_socket.get('socket')
        if sock is not None:
            try:sock.shutdown(socket.SHUT_RDWR)
            except OSError:pass
    watchdog=threading.Timer(timeout,expire);watchdog.daemon=True;watchdog.start()
    try:
        connection.connect();owned_socket['socket']=connection.sock
        if expired.is_set():raise TimeoutError('Absolute request deadline exceeded')
        connection.request('POST','/v1/chat/completions',body=json.dumps(payload,ensure_ascii=False).encode(),headers=headers)
        with connection.getresponse() as response:
            if response.status>=400:
                raise RuntimeError(f'HTTP {response.status}: '+response.read(4096).decode(errors='replace'))
            result=parse_sse(response,t,on_first,t+timeout)
        if expired.is_set():result['error']='TimeoutError: Absolute request deadline exceeded'
        return result
    except Exception as e:
        detail='Absolute request deadline exceeded' if expired.is_set() else str(e)
        return {'error':f'{type(e).__name__}: {detail}','total_s':time.perf_counter()-t,'text':'','reasoning':'','tools':[],'usage':{},'timings':{},'first_s':None,'finish_reason':None,'done':False}
    finally:
        watchdog.cancel();connection.close();watchdog.join(timeout=1)


def measurements(r):
    u,t=r.get('usage') or {},r.get('timings') or {}
    cached=(u.get('prompt_tokens_details') or {}).get('cached_tokens',t.get('cache_n'))
    read=t.get('prompt_n')
    if read is None and u.get('prompt_tokens') is not None and cached is not None: read=u['prompt_tokens']-cached
    return {'wall_s':r.get('total_s'),'ttft_s':r.get('first_s'),
            'reasoning_ttft_s':r.get('first_reasoning_s'),'visible_ttft_s':r.get('first_visible_s'),
            'tool_ttft_s':r.get('first_tool_s'),'tool_arguments_ttft_s':r.get('first_tool_arguments_s'),
            'output_events':len(r.get('output_event_times_s',[])), 'token_itl_ms':None,
            'prompt_tokens':u.get('prompt_tokens'),'generated_tokens':u.get('completion_tokens'),
            'reused_tokens':cached,'read_tokens':read,'prompt_ms':t.get('prompt_ms'),'decode_ms':t.get('predicted_ms'),
            'prompt_tps':t.get('prompt_per_second'),'decode_tps':t.get('predicted_per_second'),
            'drafts_offered':t.get('draft_n'),'drafts_accepted':t.get('draft_n_accepted')}

"""Production-tree verification for Strata v0.2.17 B2 (2026-11-20). Runs the given launch script the way systemd does
(clean env, own process group), checks startup facts and API behaviour on 127.0.0.1:18343, then stops only its own group."""
import json, os, signal, subprocess, sys, threading, time, shlex
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
sys.path.insert(0, '/data/strata-data/v0216-baseline-20261120')
import campaign as c
N = Path('/home/hhtele/strata-0.2.17'); BASE = 'http://127.0.0.1:18343'; c.BASE = BASE
script, mode, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
out.mkdir(parents=True)
res = dict(script=script, mode=mode, checks={}, started=time.time())
def chk(name, ok, **kw):
    res['checks'][name] = dict(ok=bool(ok), **kw); print('CHECK', name, bool(ok), json.dumps(kw, ensure_ascii=False)[:600], flush=True)
def call(path, body=None, timeout=900, headers=None, base=BASE):
    h = {'Content-Type': 'application/json', 'Connection': 'close', **(headers or {})}
    req = Request(base + path, json.dumps(body, ensure_ascii=False).encode() if body is not None else None, h)
    t0 = time.monotonic()
    try:
        with urlopen(req, timeout=timeout) as r: raw = r.read(); code = r.status
    except HTTPError as e: raw = e.read(); code = e.code
    try: j = json.loads(raw)
    except ValueError: j = raw.decode(errors='replace')[:2000]
    return code, j, time.monotonic() - t0
def own():
    return [int(p.name) for p in Path('/proc').iterdir() if p.name.isdigit() and str(N) in _cmd(p) and 'verify0217.py' not in _cmd(p)] 
def _cmd(p):
    try: return (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
    except OSError: return ''

def tool_loop(model):
    tools = [{'type': 'function', 'function': {'name': 'get_weather', 'description': 'Get the current weather for a city', 'parameters': {'type': 'object', 'properties': {'city': {'type': 'string'}}, 'required': ['city']}}}]
    m1 = [{'role': 'user', 'content': '上海现在天气怎么样？请调用工具查询，然后用一句话回答。'}]
    code, j1, _ = call('/v1/chat/completions', dict(model=model, messages=m1, tools=tools, max_tokens=2048, stream=False))
    a = j1['choices'][0]['message']; tc = a.get('tool_calls') or []
    if not tc: return chk('reply_reuse_tool_loop', False, note='no tool call in turn 1', finish=j1['choices'][0].get('finish_reason'))
    asst = {'role': 'assistant', 'content': a.get('content') or '', 'tool_calls': tc}
    if a.get('reasoning_content'): asst['reasoning_content'] = a['reasoning_content']
    m2 = m1 + [asst, {'role': 'tool', 'tool_call_id': tc[0]['id'], 'content': json.dumps({'city': '上海', 'weather': '多云', 'temp_c': 14}, ensure_ascii=False)}]
    code, j2, _ = call('/v1/chat/completions', dict(model=model, messages=m2, tools=tools, max_tokens=1024, stream=False))
    t1 = j1.get('timings') or {}; t2 = j2.get('timings') or {}
    need = (t1.get('prompt_n') or 0) + (t1.get('predicted_n') or 0) - 8
    chk('reply_reuse_tool_loop', code == 200 and (t2.get('cache_n') or 0) >= need, turn1=dict(prompt_n=t1.get('prompt_n'), predicted_n=t1.get('predicted_n')),
        turn2=dict(cache_n=t2.get('cache_n'), prompt_n=t2.get('prompt_n')), need=need, answer=(j2['choices'][0]['message'].get('content') or '')[:120])
s = c.snapshot()
units = {u: c.sh(['systemctl', 'show', u, '-p', 'ActiveState', '--value']) for u in ('openclaw-qwen38-next.service', 'openclaw-qwen38-ninfer.service')}
assert all(v == 'inactive' for v in units.values()), units
assert not c.sh(['ss', '-H', '-ltn', 'sport = :18343']), 'port 18343 busy'
assert not s['gpu_pids'] and s['avail_mib'] > 8192 and s['temp'] < 85, s
assert not own(), 'leftover processes of the tree'
env = dict(HOME='/home/hhtele', USER='hhtele', LOGNAME='hhtele', SHELL='/bin/bash', LANG='C.UTF-8', PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin')
log = open(out / 'server-stdout.txt', 'xb')
proc = subprocess.Popen([script], cwd=os.path.dirname(script), env=env, stdout=log, stderr=log, start_new_session=True)
guard = []; closed = threading.Event()
def monitor():
    with open(out / 'resources.jsonl', 'x') as f:
        while not closed.wait(2):
            try:
                cur = c.snapshot(); f.write(json.dumps(cur) + '\n'); f.flush()
                if cur['avail_mib'] < 4096: raise RuntimeError('LOW_AVAILABLE_MEMORY')
                if cur['temp'] >= 85: raise RuntimeError('GPU_TEMPERATURE')
                if proc.poll() is not None: raise RuntimeError('SERVER_EXIT %s' % proc.returncode)
            except Exception as e:
                guard.append(str(e)); os.killpg(proc.pid, signal.SIGTERM); return
th = threading.Thread(target=monitor, daemon=True); th.start()
err = None
try:
    t0 = time.monotonic()
    while True:
        if guard: raise RuntimeError('GUARD %s' % guard)
        if time.monotonic() - t0 > 480: raise RuntimeError('READY_TIMEOUT')
        try: code, h, _ = call('/health', timeout=3)
        except OSError: time.sleep(1); continue
        if isinstance(h, dict) and h.get('loaded'): break
        time.sleep(1)
    res['ready_s'] = time.monotonic() - t0; res['health'] = h
    model = h.get('model')
    chk('health', h.get('max_context') == 131072 and model == 'openclaw/Qwen3.8-next', model=model, max_context=h.get('max_context'), ready_s=round(res['ready_s'], 1))
    el = (N / 'strata-iq3_xxs.log').read_text(errors='replace')
    started = [l for l in el.splitlines() if 'engine started:' in l][-1]
    native = shlex.split(started.split('engine started:', 1)[1])
    want = json.loads((N / 'strata-iq3_xxs.json').read_text())['args']
    bad = [x for i, x in enumerate(want) if x.startswith('--') and i + 1 < len(want) and not want[i + 1].startswith('--') and not (native.count(x) == 1 and native[native.index(x) + 1] == want[i + 1])]
    chk('engine_args', native[0] == str(N / 'engine/strata') and not bad, exe=native[0], mismatch=bad)
    chk('tail_skip_on', 'STRATA_ROUTE_TAIL_SKIP=7 is ON' in el)
    sv = (out / 'server-stdout.txt').read_text(errors='replace')
    chk('serve_switches', 'LAB_PR_1536 enabled=1' in sv and 'LAB_CFG_PT preserve_thinking default=0' in sv)
    msgs = [{'role': 'user', 'content': '用一句话说明 TCP 和 UDP 的主要区别。'}]
    code, j, w = call('/v1/chat/completions', dict(model=model, messages=msgs, max_tokens=1024, stream=False))
    m = (j.get('choices') or [{}])[0].get('message', {}) if isinstance(j, dict) else {}
    chk('chat_nonstream', code == 200 and bool(m.get('content')), finish=(j.get('choices') or [{}])[0].get('finish_reason') if isinstance(j, dict) else None, content=(m.get('content') or '')[:200], wall_s=round(w, 1), usage=j.get('usage') if isinstance(j, dict) else j)
    if mode == 'switch': tool_loop(model); raise SystemExit(0)
    r = c.chat(out, 'stream', dict(messages=msgs, max_tokens=512, stream=True), model)
    chk('chat_stream', r.get('done') and not r.get('error') and r.get('chunks', 0) > 0, finish=r.get('finish'), chunks=r.get('chunks'), first_s=r.get('first_s'))
    tools = [{'type': 'function', 'function': {'name': 'get_weather', 'description': 'Get the current weather for a city', 'parameters': {'type': 'object', 'properties': {'city': {'type': 'string'}}, 'required': ['city']}}}]
    code, j, w = call('/v1/chat/completions', dict(model=model, messages=[{'role': 'user', 'content': '北京现在天气怎么样？请调用工具查询。'}], tools=tools, max_tokens=2048, stream=False))
    tc = ((j.get('choices') or [{}])[0].get('message', {}).get('tool_calls') or []) if isinstance(j, dict) else []
    ok = bool(tc) and tc[0]['function']['name'] == 'get_weather' and 'city' in json.loads(tc[0]['function']['arguments'])
    chk('tool_call', code == 200 and ok, tool_calls=tc, finish=(j.get('choices') or [{}])[0].get('finish_reason') if isinstance(j, dict) else j)
    m1 = [{'role': 'user', 'content': '列出三种常见的排序算法，并各用一句话说明。'}]
    code, j1, _ = call('/v1/chat/completions', dict(model=model, messages=m1, max_tokens=2048, stream=False))
    a = j1['choices'][0]['message']
    m2 = m1 + [{'role': 'assistant', 'content': a.get('content') or '', **({'reasoning_content': a['reasoning_content']} if a.get('reasoning_content') else {})},
               {'role': 'user', 'content': '其中哪一种平均时间复杂度最低？一句话回答。'}]
    code, j2, _ = call('/v1/chat/completions', dict(model=model, messages=m2, max_tokens=1024, stream=False))
    t1 = j1.get('timings') or {}; t2 = j2.get('timings') or {}
    chk('reply_reuse_turn2', code == 200 and (t2.get('cache_n') or 0) > (t1.get('prompt_n') or 0), turn1=dict(prompt_n=t1.get('prompt_n'), predicted_n=t1.get('predicted_n')), turn2=dict(cache_n=t2.get('cache_n'), prompt_n=t2.get('prompt_n')))
    code, j, w = call('/v1/messages', dict(model=model, max_tokens=512, messages=[{'role': 'user', 'content': 'Reply with the single word: ready'}]))
    chk('anthropic_messages', code == 200 and isinstance(j, dict) and j.get('type') == 'message', stop_reason=j.get('stop_reason') if isinstance(j, dict) else j, content=str(j.get('content'))[:200] if isinstance(j, dict) else None)
    code, j, _ = call('/metrics')
    chk('metrics', code == 200 and len(str(j)) > 100, bytes=len(str(j)))
    code, j, _ = call('/v1/chat/completions', dict(model=model, messages=msgs, max_tokens=8), base='http://127.0.0.1:28343')
    chk('nginx_reachable_unauthenticated', code in (401, 403), http=code)
    fx = json.loads((Path('/data/strata-data/v0216-baseline-20261120') / 'fixtures.json').read_text())
    for leg in ('d3k', 'c100k'):
        r = c.chat(out, leg, fx[leg]['body'], model); t = r.get('timings') or {}
        chk('perf_' + leg, r.get('done') and not r.get('error'), tps=t.get('predicted_per_second'), prompt_n=t.get('prompt_n'), prompt_ms=t.get('prompt_ms'), predicted_n=t.get('predicted_n'), finish=r.get('finish'))
    if guard: raise RuntimeError('GUARD %s' % guard)
except SystemExit: pass
except BaseException as e:
    err = '%s: %s' % (type(e).__name__, e); print('ERROR', err, flush=True)
finally:
    closed.set(); th.join(timeout=30)
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        try: proc.wait(timeout=120)
        except subprocess.TimeoutExpired: os.killpg(proc.pid, signal.SIGKILL); proc.wait(timeout=30)
    for sig in (signal.SIGTERM, signal.SIGKILL):
        p = own()
        if not p: break
        for x in p:
            try: os.kill(x, sig)
            except ProcessLookupError: pass
        time.sleep(15)
    time.sleep(3)
    fin = c.snapshot()
    res.update(error=err, guard=guard, exit_code=proc.returncode, leftover=own(), port=c.sh(['ss', '-H', '-ltn', 'sport = :18343']), final=fin,
               all_ok=err is None and not guard and all(v['ok'] for v in res['checks'].values()))
    (out / 'VERIFY.json').write_text(json.dumps(res, ensure_ascii=False, indent=1) + '\n')
    print('FINISHED all_ok=%s err=%s leftover=%s port=%r gpu_used=%s' % (res['all_ok'], err, res['leftover'], res['port'], fin['gpu_used']), flush=True)

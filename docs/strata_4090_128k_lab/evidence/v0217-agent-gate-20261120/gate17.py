"""Task-level paired quality gate on the v0.2.17 B2 build (2026-11-20).
Tasks: exercism/python practice (single solution + test file) and openai/human-eval, both public (MIT).
Protocol (aider polyglot style): attempt 1 sees instructions + stub only (tests hidden); on failure the model sees the
test output and gets one more attempt.  Grading only in the isolated local python:3.12-slim container (no network,
read-only root, --pull=never).  One server per arm on lab port 18089 from a copy of the production config; production
unit must be inactive.  Outcome per task = pass after at most 2 attempts; pass@1 is secondary.
    gate17.py prereg | arm NAME [ENV=VAL ...] | pairs BASE CAND"""
import gzip, json, os, re, shutil, signal, subprocess, sys, threading, time, hashlib
from pathlib import Path
from urllib.request import Request, urlopen
GD = Path('/data/strata-data/v0217-gate-20261120'); N = Path('/home/hhtele/strata-0.2.17'); PS = Path('/data/strata-data/pisim-20261120')
EX = PS / 'exercism/exercises/practice'; HE = PS / 'human-eval/data/HumanEval.jsonl.gz'; POLY = PS / 'bench/python/exercises/practice'
IMAGE = 'sha256:ec7d6c95cd3692a2e2d228a8b1ca74e4025b54121fcc4c5da6f09cfa473315ad'
PORT = 18089; URL = 'http://127.0.0.1:%d' % PORT; MODEL = 'openclaw/Qwen3.8-next'
MAX_TOKENS = 12288; THINK_BUDGET = 4096; PILOT = 34; PILOT_STOP = 0.85
def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
def sha(b): return hashlib.sha256(b).hexdigest()
def tasks():
    out = []
    poly = sorted(p.name for p in POLY.iterdir() if p.is_dir())
    ex = []
    for d in sorted(EX.iterdir()):
        cfg = json.loads((d / '.meta/config.json').read_text()); f = cfg.get('files', {})
        if len(f.get('solution', [])) == 1 and len(f.get('test', [])) == 1 and (d / f['solution'][0]).exists() and (d / f['test'][0]).exists():
            ex.append(d.name)
    first = [x for x in poly if x in ex]
    for x in first + [x for x in ex if x not in first]:
        out.append('ex:' + x)
    for l in gzip.open(HE, 'rt'):
        out.append('he:' + json.loads(l)['task_id'].split('/')[1])
    return out, len(first)
def he_problems(): return {json.loads(l)['task_id'].split('/')[1]: json.loads(l) for l in gzip.open(HE, 'rt')}
def docker(ws, cmd, timeout=60):
    name = 'gate17-%d-%d' % (os.getpid(), int(time.time() * 1000) % 10**9)
    argv = ['docker', 'run', '--rm', '--name', name, '--network', 'none', '--pull=never', '--read-only', '--tmpfs', '/tmp:rw,size=64m',
            '--memory', '512m', '--cpus', '1', '--pids-limit', '128', '--user', '%d:%d' % (os.getuid(), os.getgid()), '-e', 'HOME=/tmp',
            '-e', 'PYTHONDONTWRITEBYTECODE=1', '-v', '%s:/w:rw' % ws, '-w', '/w', IMAGE, 'sh', '-c', cmd]
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout); return p.returncode, (p.stdout + p.stderr)
    except subprocess.TimeoutExpired:
        subprocess.run(['docker', 'kill', name], capture_output=True); return 124, '[timeout after %d s]' % timeout
def prereg():
    p = GD / 'PREREG.json'
    if p.exists(): raise SystemExit('PREREG exists: frozen')
    ids, npilot = tasks()
    ref = json.loads((GD / 'REFCHECK.json').read_text())          # reference solutions graded in the same container
    bad = sorted(t for t, ok in ref.items() if not ok)
    first = ids[:npilot]; ids = [t for t in ids if ref.get(t) is True]; npilot = sum(t in ids for t in first)
    srcs = dict(exercism=subprocess.run(['git', '-C', str(PS / 'exercism'), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip(),
                human_eval=subprocess.run(['git', '-C', str(PS / 'human-eval'), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip(),
                polyglot=subprocess.run(['git', '-C', str(PS / 'bench'), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip(),
                human_eval_sha256=sha(HE.read_bytes()))
    doc = dict(created=time.strftime('%Y-%m-%d %H:%M:%S'), task_ids=ids, n=len(ids), pilot_first=npilot, excluded_reference_fails=bad, sources=srcs,
               driver_sha256=sha(Path(__file__).read_bytes()), image=IMAGE, max_tokens=MAX_TOKENS, reasoning_budget_tokens=THINK_BUDGET, attempts=2, version=2,
               v1_note='v1 (no thinking budget, max_tokens 16384) stopped after 3 b2 tasks at ~150 s/task (projected 15-20 h for two arms); no ts0 result existed; kept in v1-aborted/', sampling='server defaults, seed=1000+index',
               outcome='pass after at most 2 attempts (primary); pass@1 secondary', unit='independent_task', aggregation='one_pair_per_task',
               margin=0.05, margin_note='frozen before any arm ran; 0.02 needs >=183 tasks with zero discordance, unreachable with sampled decoding at this n',
               baseline='ts0 (exact routing)', candidate='b2 (STRATA_ROUTE_TAIL_SKIP=7, production)', decision_tool='tools/quality_gate.py',
               pilot_rule='arm b2 runs the polyglot python subset first; if its pass@1 > %.2f the set cannot discriminate: stop and reselect' % PILOT_STOP,
               failure_kinds=dict(length='task_budget_exhausted', other='model_oracle', http_or_server='infrastructure'))
    p.write_text(json.dumps(doc, indent=1) + '\n'); log('PREREG', len(ids), 'tasks, pilot', npilot)
def refcheck():
    ids, _ = tasks(); he = he_problems(); ad = GD / 'refcheck'; res = {}
    global chat
    for i, tid in enumerate(ids):
        kind, name = tid.split(':', 1)
        if kind == 'ex':
            ex = json.loads((EX / name / '.meta/config.json').read_text())['files']['example'][0]; code = (EX / name / ex).read_text()
        else:
            code = he[name]['prompt'] + he[name]['canonical_solution']
        chat = lambda m, s, code=code: ({'choices': [{'finish_reason': 'stop', 'message': {'content': '```python\n' + code + '```'}}], 'usage': {}}, 0.0)
        r = run_task(tid, i, ad, he); res[tid] = r['pass1']
        if not r['pass1']: log('REF_FAIL', tid, r['attempts'][-1]['tail'][-200:])
    shutil.rmtree(ad / 'ws', ignore_errors=True)
    (GD / 'REFCHECK.json').write_text(json.dumps(res, indent=1) + '\n'); log('REFCHECK', sum(res.values()), 'of', len(res))
def snapshot():
    mi = {l.split(':')[0]: int(l.split()[1]) for l in open('/proc/meminfo') if l.startswith('MemAvailable')}
    q = subprocess.run(['nvidia-smi', '--query-gpu=temperature.gpu,memory.used', '--format=csv,noheader,nounits'], capture_output=True, text=True).stdout.split(',')
    return dict(avail_mib=mi['MemAvailable'] // 1024, temp=int(q[0]), gpu_used=int(q[1]))
def start_server(ad, env_over):
    cfg = json.loads((N / 'strata-iq3_xxs.json').read_text())
    a = cfg['args']; a[a.index('--expert-profile-save') + 1] = str(ad / 'expert-profile-learned.bin')
    cfg.update(port=PORT, log=str(ad / 'engine.log'), slot_save_path=str(ad / 'slots')); cfg['env'].update(env_over)
    (ad / 'config.json').write_text(json.dumps(cfg, indent=1) + '\n')
    st = ad / 'state'; st.mkdir(exist_ok=True)
    sh = '\n'.join(['cd "%s"' % N, 'export STRATA_REPLY_REUSE=1 STRATA_PRESERVE_THINKING=%s' % env_over.get('STRATA_PRESERVE_THINKING', '0'),
        'export STRATA_DATA_DIR="%s/data" STRATA_DRAFT_COSTS_DIR="%s/draft-costs"' % (st, st),
        'export XDG_DATA_HOME="%s/xdg-data" XDG_CONFIG_HOME="%s/xdg-config" XDG_CACHE_HOME="%s/xdg-cache"' % (st, st, st),
        'export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1',
        'exec "%s/python/bin/python3" -B "%s/terminal/serve/server.py" --engine strata --config "%s/config.json" --port %d' % (N, N, ad, PORT)]) + '\n'
    (ad / 'run.sh').write_text(sh)
    env = {k: os.environ[k] for k in ('HOME', 'USER', 'LOGNAME', 'SHELL', 'LANG', 'PATH') if k in os.environ}
    out = open(ad / 'server-stdout.txt', 'a')
    p = subprocess.Popen(['bash', str(ad / 'run.sh')], stdout=out, stderr=subprocess.STDOUT, env=env, start_new_session=True)
    t0 = time.monotonic()
    while time.monotonic() - t0 < 600:
        if p.poll() is not None: raise RuntimeError('server exited %s' % p.returncode)
        try:
            h = json.loads(urlopen(URL + '/health', timeout=3).read())
            if h.get('status') == 'ok' and h.get('loaded'): log('server ready in %.0f s' % (time.monotonic() - t0)); return p
        except Exception: pass
        time.sleep(5)
    raise RuntimeError('server not ready')
def stop_server(p):
    try: os.killpg(p.pid, signal.SIGTERM)
    except ProcessLookupError: return
    for _ in range(90):
        if p.poll() is not None: break
        time.sleep(1)
    try: os.killpg(p.pid, signal.SIGKILL)
    except ProcessLookupError: pass
def chat(messages, seed):
    body = dict(model=MODEL, messages=messages, max_tokens=MAX_TOKENS, reasoning_budget_tokens=THINK_BUDGET, seed=seed, stream=False)
    t0 = time.monotonic()
    with urlopen(Request(URL + '/v1/chat/completions', json.dumps(body).encode(), {'Content-Type': 'application/json'}), timeout=1800) as f:
        r = json.loads(f.read())
    return r, time.monotonic() - t0
FMT = 'Return the complete file content in exactly one ```python code block, with nothing else after it.'
def run_task(tid, idx, ad, he):
    kind, name = tid.split(':', 1); ws = ad / 'ws' / name.replace('/', '_')
    if ws.exists(): shutil.rmtree(ws)
    if kind == 'ex':
        src = EX / name; cfg = json.loads((src / '.meta/config.json').read_text())
        sol, test = cfg['files']['solution'][0], cfg['files']['test'][0]
        shutil.copytree(src, ws, ignore=shutil.ignore_patterns('.meta', '.approaches', '.articles'))
        tests = (ws / test).read_bytes(); (ws / test).unlink()
        ins = (ws / '.docs/instructions.md').read_text()
        if (ws / '.docs/instructions.append.md').exists(): ins += '\n\n' + (ws / '.docs/instructions.append.md').read_text()
        prompt = '# Instructions\n\n%s\n\n# Stub: %s\n\n```python\n%s```\n\nImplement %s so that it satisfies the instructions (the tests use the names in the stub). %s' % (ins, sol, (ws / sol).read_text(), sol, FMT)
        def grade(code):
            (ws / sol).write_text(code); (ws / test).write_bytes(tests)
            rc, out = docker(ws, 'python3 -m unittest -q %s 2>&1' % test[:-3])
            (ws / test).unlink(); return rc == 0 and re.search(r'^OK', out, re.M) is not None, out
    else:
        pr = he[name]; ws.mkdir(parents=True)
        head = ''.join(l for l in pr['prompt'].splitlines(True) if l.startswith(('import ', 'from ')))
        prompt = 'Complete this Python function.\n\n```python\n%s```\n\n%s' % (pr['prompt'], FMT.replace('file content', 'function (with its signature and any imports it needs)'))
        def grade(code):
            (ws / 'run.py').write_text(head + '\n' + code + '\n\n' + pr['test'] + '\n\ncheck(%s)\n' % pr['entry_point'])
            rc, out = docker(ws, 'python3 run.py 2>&1', timeout=30); return rc == 0, out
    msgs = [{'role': 'user', 'content': prompt}]; atts = []
    for att in (1, 2):
        try:
            r, wall = chat(msgs, 1000 + idx)
        except Exception as e:
            return dict(task_id=tid, error='HTTP %s: %s' % (type(e).__name__, e), attempts=atts)
        ch = r['choices'][0]; m = ch['message']; text = m.get('content') or ''
        blocks = re.findall(r'```(?:python|py)?[ \t]*\n(.*?)```', text, re.S)
        ok, out = (grade(blocks[-1]) if blocks else (False, 'no python block'))
        u = r.get('usage') or {}
        atts.append(dict(attempt=att, finish=ch.get('finish_reason'), prompt_tokens=u.get('prompt_tokens'), completion_tokens=u.get('completion_tokens'),
                         wall_s=round(wall, 2), blocks=len(blocks), passed=ok, tail=out[-400:]))
        if ok or att == 2: break
        a = {'role': 'assistant', 'content': text}
        if m.get('reasoning_content'): a['reasoning_content'] = m['reasoning_content']
        fb = '\n'.join(out.splitlines()[-40:])[-3000:]
        msgs += [a, {'role': 'user', 'content': 'The tests failed:\n\n```\n%s\n```\n\nFix the code. %s' % (fb, FMT)}]
    return dict(task_id=tid, pass1=atts[0]['passed'], pass2=any(x['passed'] for x in atts), length=any(x['finish'] == 'length' for x in atts), attempts=atts)
def arm(name, env_over):
    pre = json.loads((GD / 'PREREG.json').read_text())
    if sha(Path(__file__).read_bytes()) != pre['driver_sha256']: raise SystemExit('driver changed after prereg')
    if subprocess.run(['systemctl', 'is-active', 'openclaw-qwen38-next.service'], capture_output=True, text=True).stdout.strip() != 'inactive': raise SystemExit('production is running')
    ad = GD / 'arms' / name; ad.mkdir(parents=True, exist_ok=True)
    rows_p = ad / 'rows.jsonl'; done = {json.loads(l)['task_id'] for l in open(rows_p)} if rows_p.exists() else set()
    s = snapshot()
    if s['gpu_used'] > 500: raise SystemExit('GPU busy %s' % s)
    he = he_problems(); stop = threading.Event(); guard = []
    p = start_server(ad, env_over)
    def mon():
        while not stop.wait(5):
            s = snapshot()
            if s['avail_mib'] < 3072 or s['temp'] >= 85: guard.append(s); log('GUARD', s); stop.set(); os.killpg(p.pid, signal.SIGTERM)
    th = threading.Thread(target=mon, daemon=True); th.start()
    try:
        for i, tid in enumerate(pre['task_ids']):
            if tid in done: continue
            if stop.is_set(): break
            r = run_task(tid, i, ad, he); r['index'] = i
            with open(rows_p, 'a') as f: f.write(json.dumps(r) + '\n')
            log(name, i, tid, 'ERR' if 'error' in r else (r['pass1'], r['pass2']), sum(a['completion_tokens'] or 0 for a in r['attempts']), round(sum(a['wall_s'] for a in r['attempts']), 1))
            if 'error' in r: log('INFRA', r['error']); break
            if name == 'b2' and i + 1 == pre['pilot_first']:
                rows = [json.loads(l) for l in open(rows_p)][:pre['pilot_first']]
                p1 = sum(x.get('pass1', False) for x in rows) / len(rows)
                (ad / 'PILOT.json').write_text(json.dumps(dict(n=len(rows), pass1=p1, pass2=sum(x.get('pass2', False) for x in rows) / len(rows)), indent=1))
                log('PILOT pass@1 %.3f' % p1)
                if p1 > PILOT_STOP: log('PILOT_STOP'); break
    finally:
        stop.set(); stop_server(p); log('ARM_END', name, 'guard' if guard else '')
def pairs(base, cand):
    pre = json.loads((GD / 'PREREG.json').read_text())
    R = {n: {json.loads(l)['task_id']: json.loads(l) for l in open(GD / 'arms' / n / 'rows.jsonl')} for n in (base, cand)}
    rows = []
    for tid in pre['task_ids']:
        b, c = R[base].get(tid), R[cand].get(tid)
        if b is None or c is None: rows.append(dict(task_id=tid, baseline_success=False, candidate_success=False, run_valid=False, failure_kind='infrastructure')); continue
        if 'error' in b or 'error' in c: rows.append(dict(task_id=tid, baseline_success=False, candidate_success=False, run_valid=False, failure_kind='infrastructure')); continue
        bs, cs = b['pass2'], c['pass2']
        fk = 'none' if bs and cs else ('task_budget_exhausted' if (not bs and b['length']) or (not cs and c['length']) else 'model_oracle')
        rows.append(dict(task_id=tid, baseline_success=bs, candidate_success=cs, run_valid=True, failure_kind=fk))
    doc = dict(schema_version=1, preregistration=dict(task_ids=pre['task_ids'], margin=pre['margin'], unit=pre['unit'], aggregation=pre['aggregation']), pairs=rows)
    (GD / ('PAIRS-%s-vs-%s.json' % (cand, base))).write_text(json.dumps(doc, indent=1) + '\n')
    p1 = {n: sum(R[n][t].get('pass1', False) for t in pre['task_ids'] if t in R[n]) for n in R}
    print(json.dumps(dict(n=len(rows), pass1=p1, pass2={n: sum(r['pass2'] for r in R[n].values() if 'pass2' in r) for n in R}), indent=1))
if __name__ == '__main__':
    os.umask(0o022)
    if sys.argv[1] == 'prereg': prereg()
    elif sys.argv[1] == 'refcheck': refcheck()
    elif sys.argv[1] == 'arm': arm(sys.argv[2], dict(x.split('=', 1) for x in sys.argv[3:]))
    elif sys.argv[1] == 'pairs': pairs(sys.argv[2], sys.argv[3])

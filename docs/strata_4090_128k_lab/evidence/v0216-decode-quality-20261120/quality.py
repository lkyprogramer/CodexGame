"""Quality screen A0 vs B0 (2026-11-20): P3 fixed corpus (non-performance cases, lab scoring) + 8-turn Python ledger chain
graded only in the isolated Docker grader (no network, read-only, immutable local image id, --pull=never). Screen, not formal NI."""
import copy, hashlib, importlib.util, json, os, signal, subprocess, sys, threading, time, shlex
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
sys.path.insert(0, str(Path(__file__).resolve().parent))
import campaign as c
LAB = Path('/home/hhtele/strata-lab-4090')
sys.path.insert(0, str(LAB))
from lab import scoring
spec = importlib.util.spec_from_file_location('strata_frozen_chain', LAB / 'tools/session/chain_bench.py')
chain = importlib.util.module_from_spec(spec); spec.loader.exec_module(chain)
CORPUS = LAB / 'workspace/combination/kvres-20261027/corpus.json'
IMAGE = 'sha256:ec7d6c95cd3692a2e2d228a8b1ca74e4025b54121fcc4c5da6f09cfa473315ad'  # python:3.12-slim, local
OUT = c.BD / 'runs' / 'quality'
BUDGET = 2400.0

def own_pids(d):
    pids = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try: cmd = (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
        except OSError: continue
        if str(d) + '/' in cmd and 'quality.py' not in cmd: pids.append(int(p.name))
    return pids

def post(body, timeout):
    req = Request(c.BASE + '/v1/chat/completions', json.dumps(body, ensure_ascii=False).encode(), {'Content-Type': 'application/json', 'Connection': 'close'})
    t0 = time.monotonic()
    try:
        with urlopen(req, timeout=timeout) as r: j = json.load(r)
    except HTTPError as e:
        return dict(error='HTTP_%d %s' % (e.code, e.read()[:500]), wall_s=time.monotonic() - t0)
    except Exception as e:
        return dict(error='%s: %s' % (type(e).__name__, e), wall_s=time.monotonic() - t0)
    if j.get('error'): return dict(error=j['error'], wall_s=time.monotonic() - t0)
    ch = j['choices'][0]; m = ch.get('message') or {}
    return dict(text=m.get('content') or '', reasoning=m.get('reasoning_content') or '', tools=m.get('tool_calls') or [],
                finish_reason=ch.get('finish_reason'), usage=j.get('usage'), timings=j.get('timings'), wall_s=time.monotonic() - t0)

def sha(o): return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def run_corpus(d, model):
    cases = [x for x in json.loads(CORPUS.read_text())['cases'] if x['kind'] != 'performance']
    rows = []
    with open(d / 'corpus.jsonl', 'x') as f:
        for case in cases:
            body = dict(case['body'], model=model, stream=False)
            r = post(body, 900)
            s = scoring.score(case, r)
            row = dict(id=case['id'], group=case['group'], kind=case['kind'], critical=bool(case.get('critical_quality')), body_sha=sha(case['body']),
                       expected=case.get('expected'), score=s, finish=r.get('finish_reason'), text=(r.get('text') or '')[:400],
                       tools=r.get('tools'), timings=r.get('timings'), usage=r.get('usage'), wall_s=r.get('wall_s'), error=r.get('error'))
            f.write(json.dumps(row, ensure_ascii=False) + '\n'); f.flush(); rows.append(row)
            print('  case', case['id'], s.get('pass'), s.get('reason'), flush=True)
            if r.get('error'): raise RuntimeError('CORPUS_REQUEST_ERROR %s %s' % (case['id'], r['error']))
    return rows

def run_chain(d, model, seed):
    cd = d / 'chain'; cd.mkdir()
    messages = [{'role': 'system', 'content': chain.SYSTEM}]; rows = []; t0 = time.monotonic(); err = None
    for turn, req in enumerate(chain.REQS):
        body = dict(model=model, messages=copy.deepcopy(messages) + [{'role': 'user', 'content': req + chain.FORMAT}], max_tokens=32768,
                    temperature=1.0, top_p=0.95, top_k=20, reasoning_effort='xhigh', seed=seed, stream=False)
        remaining = BUDGET - (time.monotonic() - t0); bound = 60 * (turn + 1) + 90
        if remaining <= bound + 1: err = 'TASK_BUDGET'; break
        c.dump(cd / ('turn-%02d.request.json' % turn), body)
        r = post(body, min(1800, remaining - bound))
        c.dump(cd / ('turn-%02d.response.json' % turn), r)
        if r.get('error'): err = 'REQUEST_ERROR %s' % r['error']; break
        g0 = time.monotonic()
        score = chain_score(r, turn + 1)
        rows.append(dict(turn=turn, score=score, finish=r.get('finish_reason'), usage=r.get('usage'), timings=r.get('timings'), wall_s=r.get('wall_s'), grade_s=time.monotonic() - g0))
        print('  chain seed', seed, 'turn', turn, score.get('pass'), score.get('passed'), score.get('reason'), r.get('usage'), flush=True)
        messages = copy.deepcopy(body['messages'])
        a = {'role': 'assistant', 'content': r.get('text') or ''}
        if r.get('reasoning'): a['reasoning_content'] = r['reasoning']
        messages.append(a)
    elapsed = time.monotonic() - t0
    ok = len(rows) == len(chain.REQS) and all(x['score'].get('pass') is True for x in rows) and elapsed <= BUDGET and err is None
    summ = dict(seed=seed, turns=len(rows), successful_turns=sum(x['score'].get('pass') is True for x in rows), task_success=ok, elapsed_s=elapsed, error=err, rows=rows)
    c.dump(cd / 'chain.json', summ)
    return summ

def chain_score(r, upto):
    import re
    if r.get('finish_reason') != 'stop' or r.get('tools'):
        return {'pass': False, 'reason': 'truncated or tool output', 'graded': False}
    blocks = re.findall(r'```python\s*\n(.*?)```', r.get('text') or '', re.S)
    if len(blocks) != 1: return {'pass': False, 'reason': 'expected exactly one python block', 'graded': False}
    passed = chain.grade(blocks[0], upto, IMAGE)
    if not (isinstance(passed, list) and len(passed) == upto and all(type(x) is bool for x in passed)): raise RuntimeError('GRADER_NOT_AUDITABLE')
    return {'pass': all(passed), 'passed': passed, 'reason': 'isolated docker grader', 'graded': True}

def stage(d, armname, arm, seed, work=None):
    while True:
        s = c.snapshot(); c.gate(s)
        if c.listening(): raise RuntimeError('PORT_OCCUPIED')
        if s['temp'] <= 50: break
        time.sleep(5)
    d.mkdir(parents=True); (d / 'slots').mkdir()
    cfg, cmd = c.build_cfg(d, arm)
    c.dump(d / 'profile.json', cfg)
    argv = cmd + ['--engine', 'strata', '--config', str(d / 'profile.json'), '--host', '127.0.0.1', '--port', '18089', '--offline']
    env = {k: v for k, v in os.environ.items() if not k.startswith(('STRATA_', 'CUDA_', 'XDG_', 'HF_')) and k not in ('LD_LIBRARY_PATH', 'PYTHONPATH')}
    env.update(STRATA_REPLY_REUSE='1', STRATA_PRESERVE_THINKING='0', STRATA_DATA_DIR=str(c.BD / 'state/data'), XDG_DATA_HOME=str(c.BD / 'state/xdg-data'),
               XDG_CONFIG_HOME=str(c.BD / 'state/xdg-config'), XDG_CACHE_HOME=str(c.BD / 'state/xdg-cache'), PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1',
               STRATA_DRAFT_COSTS_DIR=str(c.BD / 'state/draft-costs'))
    c.dump(d / 'START.json', dict(arm=armname, seed=seed, argv=argv, epoch=time.time(), pre=s))
    guard = []; closed = threading.Event(); lock = threading.Lock()
    def stop():
        with lock:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try: proc.wait(timeout=90)
                except subprocess.TimeoutExpired: os.killpg(proc.pid, signal.SIGKILL); proc.wait(timeout=20)
            for sig in (signal.SIGTERM, signal.SIGKILL):
                pids = own_pids(d)
                if not pids: break
                for pid in pids:
                    try: os.kill(pid, sig)
                    except ProcessLookupError: pass
                time.sleep(15)
    def monitor():
        prev = None; streak = 0
        try:
            with open(d / 'resources.jsonl', 'x') as f:
                while not closed.wait(2):
                    if proc.poll() is not None: raise RuntimeError('SERVER_EXIT %s' % proc.returncode)
                    cur = c.snapshot(); f.write(json.dumps(cur) + '\n'); f.flush()
                    c.gate(cur, set(c.descendants(proc.pid)) | set(own_pids(d)))
                    if prev:
                        streak = streak + 1 if ((cur['swpin'] - prev['swpin']) >= 1024 and cur['avail_mib'] < 6144) else 0
                        if streak >= 5: raise RuntimeError('SUSTAINED_SWAP_IN_LOW_AVAIL')
                    prev = cur
        except Exception as e:
            guard.append(str(e)); stop()
    row = dict(arm=armname, seed=seed)
    with open(d / 'server.log', 'xb') as log:
        proc = subprocess.Popen(argv, cwd=d, env=env, stdout=log, stderr=log, start_new_session=True)
        th = threading.Thread(target=monitor, daemon=True); th.start(); t0 = time.monotonic()
        try:
            while True:
                if guard or proc.poll() is not None: raise RuntimeError('READY_FAILED %s %s' % (guard, proc.poll()))
                if time.monotonic() - t0 > 600: raise RuntimeError('READY_TIMEOUT')
                try: h = c.get('/health')
                except OSError: time.sleep(1); continue
                if h.get('loaded'): break
                time.sleep(1)
            started = next(l for l in (d / 'engine.log').read_text(errors='replace').splitlines() if 'engine started:' in l)
            native = shlex.split(started.split('engine started:', 1)[1])[1:]
            want = cfg['args']
            bad = [x for i, x in enumerate(want) if x.startswith('--') and i + 1 < len(want) and not want[i + 1].startswith('--')
                   and not (native.count(x) == 1 and native[native.index(x) + 1] == want[i + 1])]
            if bad: raise RuntimeError('ARG_MISMATCH %s' % bad)
            model = h.get('model') or 'openclaw/Qwen3.8-next'
            if work: row.update(work(d, model, guard)); return row
            rows = run_corpus(d, model)
            row['corpus'] = dict(n=len(rows), passed=sum(r['score'].get('pass') is True for r in rows), fails=[r['id'] for r in rows if r['score'].get('pass') is not True])
            if guard: raise RuntimeError('GUARD %s' % guard)
            ch = run_chain(d, model, seed)
            row['chain'] = {k: v for k, v in ch.items() if k != 'rows'}
            if guard: raise RuntimeError('GUARD %s' % guard)
            return row
        finally:
            closed.set(); th.join(timeout=60); stop()
            row['exit'] = dict(guard=guard, code=proc.returncode, leftover=own_pids(d), ports=c.listening(), final=c.snapshot())
            c.dump(d / 'ROW.json', row)
            if guard or row['exit']['ports'] or row['exit']['leftover']: raise RuntimeError('EXIT_GUARD %s' % row['exit'])

def main():
    plan = [(a, int(s)) for a, s in (x.split(':') for x in sys.argv[1:])]
    arms = json.loads((c.BD / 'arms.json').read_text())
    chain.image_id(IMAGE)
    OUT.mkdir(parents=True)
    c.dump(OUT / 'PLAN.json', dict(plan=plan, corpus=str(CORPUS), corpus_sha=hashlib.sha256(CORPUS.read_bytes()).hexdigest(), image=IMAGE, budget_s=BUDGET))
    before = {str(p): c.sha(p) for p in c.PROTECTED}
    c.gate(c.snapshot()); err = None; rows = []
    try:
        for i, (n, seed) in enumerate(plan, 1):
            d = OUT / ('%02d-%s' % (i, n))
            print('START', i, n, seed, flush=True)
            r = stage(d, n, arms[n], seed); rows.append(r)
            print('DONE', i, n, json.dumps(dict(corpus=r['corpus'], chain=r['chain'])), flush=True)
    except BaseException as e:
        err = '%s: %s' % (type(e).__name__, e); print('ERROR', err, flush=True)
    finally:
        after = {str(p): c.sha(p) for p in c.PROTECTED}
        c.dump(OUT / 'RESULT.json', dict(error=err, rows=rows, protected_changed=[p for p in before if before[p] != after[p]], final=c.snapshot(), listeners=c.listening()))
        print('FINISHED', err, flush=True)

if __name__ == '__main__':
    os.umask(0o022); main()

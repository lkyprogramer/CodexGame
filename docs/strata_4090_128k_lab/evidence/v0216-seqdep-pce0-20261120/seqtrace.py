"""Sequence-dependence + PCE0 fork-cost run (2026-11-20).
S = d3k -> c32k -> f10k -> c100k -> fork60 -> fork90 (campaign legs, then two mid-prompt branches of c100k); F = c100k only.
Per-window STRATA_SPEC_TRACE + STRATA_TRACE_ADAPT on every engine."""
import copy, json, os, signal, subprocess, sys, threading, time, shlex
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import campaign as c
from quality import own_pids
OUT = c.BD / 'runs' / 'seqtrace'

def fixtures():
    fx = json.loads((c.BD / 'fixtures.json').read_text())
    base = fx['c100k']['body']; user = base['messages'][-1]['content']
    for tag, frac in (('fork60', 0.6), ('fork90', 0.9)):
        b = copy.deepcopy(base)
        b['messages'][-1]['content'] = user[:int(len(user) * frac)] + '\n\n---\nIgnore any earlier instruction. In one short sentence, name the main topic of the text above.'
        b['max_tokens'] = 64
        fx[tag] = dict(body=b)
    return fx

def stage(d, armname, arm, kind, fx):
    while True:
        s = c.snapshot(); c.gate(s)
        if c.listening(): raise RuntimeError('PORT_OCCUPIED')
        if s['temp'] <= 50: break
        time.sleep(5)
    d.mkdir(parents=True); (d / 'slots').mkdir()
    trace = {'STRATA_SPEC_TRACE': str(d / 'spec.trace'), 'STRATA_TRACE_ADAPT': '1'}
    cfg, cmd = c.build_cfg(d, arm)
    if arm.get('kind') != 'a0': cfg['env'] = dict(cfg.get('env') or {}, **trace)
    c.dump(d / 'profile.json', cfg)
    argv = cmd + ['--engine', 'strata', '--config', str(d / 'profile.json'), '--host', '127.0.0.1', '--port', '18089', '--offline']
    env = {k: v for k, v in os.environ.items() if not k.startswith(('STRATA_', 'CUDA_', 'XDG_', 'HF_')) and k not in ('LD_LIBRARY_PATH', 'PYTHONPATH')}
    env.update(STRATA_REPLY_REUSE='1', STRATA_PRESERVE_THINKING='0', STRATA_DATA_DIR=str(c.BD / 'state/data'), XDG_DATA_HOME=str(c.BD / 'state/xdg-data'),
               XDG_CONFIG_HOME=str(c.BD / 'state/xdg-config'), XDG_CACHE_HOME=str(c.BD / 'state/xdg-cache'), PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1',
               STRATA_DRAFT_COSTS_DIR=str(c.BD / 'state/draft-costs'), **trace)
    legs = ('d3k', 'c32k', 'f10k', 'c100k', 'fork60', 'fork90') if kind == 'S' else ('c100k',)
    c.dump(d / 'START.json', dict(arm=armname, kind=kind, legs=legs, argv=argv, epoch=time.time(), pre=s))
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
    row = dict(arm=armname, kind=kind, legs={})
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
            for leg in legs:
                r = c.chat(d, leg, fx[leg]['body'], model); row['legs'][leg] = r
                t = r.get('timings') or {}
                print(' ', leg, {k: t.get(k) for k in ('cache_n', 'prompt_n', 'prompt_ms', 'predicted_n', 'predicted_per_second', 'draft_n', 'draft_n_accepted')}, r.get('finish'), r.get('error'), flush=True)
                if guard or r.get('error') or not r.get('done'): raise RuntimeError('LEG_FAILED %s %s %s' % (leg, guard, r.get('error')))
            time.sleep(3)
            return row
        finally:
            closed.set(); th.join(timeout=60); stop()
            row['exit'] = dict(guard=guard, code=proc.returncode, leftover=own_pids(d), ports=c.listening(), final=c.snapshot())
            c.dump(d / 'ROW.json', row)
            if guard or row['exit']['ports'] or row['exit']['leftover']: raise RuntimeError('EXIT_GUARD %s' % row['exit'])

def main():
    arms = json.loads((c.BD / 'arms.json').read_text()); arms['SD0'] = {'args': {'--suffix-draft': '0'}}
    plan = [x.split(':') for x in sys.argv[1:]]
    fx = fixtures(); OUT.mkdir(parents=True)
    c.dump(OUT / 'PLAN.json', dict(plan=plan, arms={k: arms[k] for k, _ in plan}))
    before = {str(p): c.sha(p) for p in c.PROTECTED}; err = None; rows = []
    c.gate(c.snapshot())
    try:
        for i, (n, kind) in enumerate(plan, 1):
            print('START', i, n, kind, flush=True)
            rows.append(stage(OUT / ('%02d-%s-%s' % (i, n, kind)), n, arms[n], kind, fx))
    except BaseException as e:
        err = '%s: %s' % (type(e).__name__, e); print('ERROR', err, flush=True)
    finally:
        after = {str(p): c.sha(p) for p in c.PROTECTED}
        c.dump(OUT / 'RESULT.json', dict(error=err, n=len(rows), protected_changed=[p for p in before if before[p] != after[p]], final=c.snapshot(), listeners=c.listening()))
        print('FINISHED', err, flush=True)

if __name__ == '__main__':
    os.umask(0o022); main()

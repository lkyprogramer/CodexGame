"""nsys decode capture v2: whole-life nsys profile, decode intervals cut by wall clock (2026-11-20).
v1 (nsys_run.py, runs/nsys) failed: nsys 2023.3 'start' after CUDA init -> daemon FATAL (device UUID)."""
import json, os, re, signal, sqlite3, subprocess, sys, threading, time, shlex
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import campaign as c

NSYS = '/usr/local/cuda-12.3/bin/nsys'
OUT = c.BD / 'runs' / 'nsys2'

def own_pids(d):
    pids = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try: cmd = (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
        except OSError: continue
        if str(d) + '/' in cmd and 'nsys2.py' not in cmd: pids.append(int(p.name))
    return pids

def server_pid(d):
    for pid in own_pids(d):
        try: cmd = Path('/proc/%d/cmdline' % pid).read_bytes().split(b'\0')
        except OSError: continue
        if any(x.endswith(b'server.py') for x in cmd) and b'--config' in cmd and not cmd[0].endswith(b'nsys'): return pid
    return None

def stage(d, armname, arm, fixtures):
    while True:
        s = c.snapshot(); c.gate(s)
        if c.listening(): raise RuntimeError('PORT_OCCUPIED')
        if s['temp'] <= 50: break
        time.sleep(5)
    d.mkdir(parents=True); (d / 'slots').mkdir()
    cfg, cmd = c.build_cfg(d, arm)
    c.dump(d / 'profile.json', cfg)
    argv = [NSYS, 'profile', '--trace=cuda', '--cuda-graph-trace=node', '--sample=none', '--cpuctxsw=none', '--kill=none',
            '--output=' + str(d / 'trace'), '--force-overwrite=true'] + cmd + \
           ['--engine', 'strata', '--config', str(d / 'profile.json'), '--host', '127.0.0.1', '--port', '18089', '--offline']
    env = {k: v for k, v in os.environ.items() if not k.startswith(('STRATA_', 'CUDA_', 'XDG_', 'HF_')) and k not in ('LD_LIBRARY_PATH', 'PYTHONPATH')}
    env.update(STRATA_REPLY_REUSE='1', STRATA_PRESERVE_THINKING='0', STRATA_DATA_DIR=str(c.BD / 'state/data'), XDG_DATA_HOME=str(c.BD / 'state/xdg-data'),
               XDG_CONFIG_HOME=str(c.BD / 'state/xdg-config'), XDG_CACHE_HOME=str(c.BD / 'state/xdg-cache'), PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1',
               STRATA_DRAFT_COSTS_DIR=str(c.BD / 'state/draft-costs'))
    c.dump(d / 'START.json', dict(arm=armname, argv=argv, epoch=time.time(), pre=s))
    guard = []; closed = threading.Event(); lock = threading.Lock(); stopping = threading.Event()
    def stop_app():
        stopping.set()
        sp = server_pid(d)
        if sp:
            try: os.kill(sp, signal.SIGTERM)
            except ProcessLookupError: pass
    def kill_all():
        with lock:
            for sig in (signal.SIGTERM, signal.SIGKILL):
                pids = own_pids(d)
                if not pids: break
                for pid in pids:
                    try: os.kill(pid, sig)
                    except ProcessLookupError: pass
                time.sleep(20)
    def monitor():
        prev = None; streak = 0
        try:
            with open(d / 'resources.jsonl', 'x') as f:
                while not closed.wait(2):
                    if proc.poll() is not None and not stopping.is_set(): raise RuntimeError('NSYS_EXIT %s' % proc.returncode)
                    cur = c.snapshot(); f.write(json.dumps(cur) + '\n'); f.flush()
                    c.gate(cur, set(own_pids(d)) | set(c.descendants(proc.pid)))
                    if prev:
                        streak = streak + 1 if ((cur['swpin'] - prev['swpin']) >= 1024 and cur['avail_mib'] < 6144) else 0
                        if streak >= 5: raise RuntimeError('SUSTAINED_SWAP_IN_LOW_AVAIL')
                    prev = cur
        except Exception as e:
            guard.append(str(e)); stop_app()
            try: proc.wait(timeout=240)
            except subprocess.TimeoutExpired: pass
            kill_all()
    row = dict(arm=armname, legs={}, marks={})
    with open(d / 'server.log', 'xb') as log:
        proc = subprocess.Popen(argv, cwd=d, env=env, stdout=log, stderr=log, start_new_session=True)
        th = threading.Thread(target=monitor, daemon=True); th.start()
        t0 = time.monotonic()
        try:
            while True:
                if guard or proc.poll() is not None: raise RuntimeError('READY_FAILED %s %s' % (guard, proc.poll()))
                if time.monotonic() - t0 > 900: raise RuntimeError('READY_TIMEOUT')
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
            for tag, fx in (('short', 'd3k'), ('long', 'c100k')):
                body = fixtures[fx]['body']
                time.sleep(4)
                r = c.chat(d, tag + '-prime', dict(body, max_tokens=1), model); row['legs'][tag + '-prime'] = r
                if guard or r.get('error') or not r.get('done'): raise RuntimeError('PRIME_FAILED %s %s' % (guard, r.get('error')))
                time.sleep(4)
                a = time.time(); r = c.chat(d, tag + '-decode', dict(body, max_tokens=512), model); b = time.time()
                row['legs'][tag + '-decode'] = r; row['marks'][tag] = [a, b]
                print(armname, tag, json.dumps({k: r.get(k) for k in ('first_s', 'finish', 'error')}), r.get('timings'), flush=True)
                if guard or r.get('error') or not r.get('done'): raise RuntimeError('DECODE_FAILED %s %s' % (guard, r.get('error')))
            time.sleep(4)
            return row
        finally:
            closed.set(); th.join(timeout=300)
            if proc.poll() is None:
                stop_app()
                try: proc.wait(timeout=900)
                except subprocess.TimeoutExpired: pass
            kill_all()
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL); proc.wait(timeout=30)
            row['exit'] = dict(guard=guard, code=proc.returncode, leftover=own_pids(d), ports=c.listening(), final=c.snapshot())
            c.dump(d / 'ROW.json', row)
            if guard or row['exit']['ports'] or row['exit']['leftover']: raise RuntimeError('EXIT_GUARD %s' % row['exit'])

def analyze(d):
    row = json.loads((d / 'ROW.json').read_text())
    rep = d / 'trace.nsys-rep'; db = d / 'trace.sqlite'
    r = subprocess.run([NSYS, 'export', '--type=sqlite', '--force-overwrite=true', '--output=' + str(db), str(rep)], capture_output=True, text=True, timeout=3600)
    if r.returncode: raise RuntimeError('EXPORT %s' % r.stderr[-500:])
    con = sqlite3.connect(str(db))
    t0 = con.execute('select utcEpochNs from TARGET_INFO_SESSION_START_TIME').fetchone()[0]
    names = dict(con.execute('select id, value from StringIds'))
    res = dict(session_utc_ns=t0)
    for tag, (a, b) in row['marks'].items():
        lo = int(a * 1e9) - t0; hi = int(b * 1e9) - t0
        ks = con.execute('select start, end, shortName from CUPTI_ACTIVITY_KIND_KERNEL where start >= ? and end <= ? order by start', (lo, hi)).fetchall()
        per = {}
        busy = 0; cur_s = cur_e = None; gaps = []
        for s, e, n in ks:
            k = names.get(n, str(n)); x = per.setdefault(k, [0, 0]); x[0] += 1; x[1] += e - s
            if cur_e is None: cur_s, cur_e = s, e
            elif s > cur_e:
                busy += cur_e - cur_s; gaps.append(s - cur_e); cur_s, cur_e = s, e
            else: cur_e = max(cur_e, e)
        if cur_e is not None: busy += cur_e - cur_s
        first = ks[0][0] if ks else lo; last = ks[-1][1] if ks else hi
        mc = con.execute('select copyKind, count(*), sum(bytes), sum(end-start) from CUPTI_ACTIVITY_KIND_MEMCPY where start >= ? and end <= ? group by copyKind', (lo, hi)).fetchall()
        gaps.sort()
        res[tag] = dict(interval_ns=hi - lo, gpu_span_ns=last - first, busy_union_ns=busy, kernels=len(ks),
                        gap_hist=dict(lt2us=sum(g for g in gaps if g < 2000), us2_100=sum(g for g in gaps if 2000 <= g < 100000),
                                      us100_1ms=sum(g for g in gaps if 100000 <= g < 1000000), ge1ms=sum(g for g in gaps if g >= 1000000), n_ge1ms=sum(1 for g in gaps if g >= 1000000)),
                        memcpy={str(k): dict(n=n, bytes=bb, ns=t) for k, n, bb, t in mc},
                        per_kernel={k: v for k, v in sorted(per.items(), key=lambda kv: -kv[1][1])},
                        timings=row['legs'][tag + '-decode'].get('timings'))
    con.close()
    c.dump(d / 'NSYS_SUMMARY.json', res)
    db.unlink()
    return res

def main():
    names = sys.argv[1:]
    arms = json.loads((c.BD / 'arms.json').read_text()); fixtures = json.loads((c.BD / 'fixtures.json').read_text())
    OUT.mkdir(parents=True)
    before = {str(p): c.sha(p) for p in c.PROTECTED}
    c.gate(c.snapshot()); err = None
    try:
        for i, n in enumerate(names, 1):
            d = OUT / ('%02d-%s' % (i, n))
            print('START', i, n, flush=True); stage(d, n, arms[n], fixtures)
            res = analyze(d)
            print('DONE', i, n, json.dumps({t: dict(kern=res[t]['kernels'], busy_ms=res[t]['busy_union_ns'] / 1e6, int_ms=res[t]['interval_ns'] / 1e6) for t in ('short', 'long')}), flush=True)
    except BaseException as e:
        err = '%s: %s' % (type(e).__name__, e); print('ERROR', err, flush=True)
    finally:
        after = {str(p): c.sha(p) for p in c.PROTECTED}
        c.dump(OUT / 'RESULT.json', dict(error=err, protected_changed=[p for p in before if before[p] != after[p]], final=c.snapshot(), listeners=c.listening()))
        print('FINISHED', err, flush=True)

if __name__ == '__main__':
    os.umask(0o022); main()

"""nsys decode capture: A0 vs B0, decode-only windows at ~3K and ~98K context (2026-11-20)."""
import json, os, shlex, signal, subprocess, sys, threading, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import campaign as c

NSYS = '/usr/local/cuda-12.3/bin/nsys'

def nsys(*a, timeout=900):
    r = subprocess.run([NSYS, *a], capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)[-2000:]

def stage(d, armname, arm, fixtures):
    while True:
        s = c.snapshot(); c.gate(s)
        if c.listening(): raise RuntimeError('PORT_OCCUPIED')
        if s['temp'] <= 50: break
        time.sleep(5)
    d.mkdir(parents=True); (d / 'slots').mkdir()
    cfg, cmd = c.build_cfg(d, arm)
    c.dump(d / 'profile.json', cfg)
    sess = 'v0216-' + d.name
    argv = [NSYS, 'launch', '--session-new=' + sess, '--trace=cuda', '--cuda-graph-trace=node'] + cmd + \
           ['--engine', 'strata', '--config', str(d / 'profile.json'), '--host', '127.0.0.1', '--port', '18089', '--offline']
    env = {k: v for k, v in os.environ.items() if not k.startswith(('STRATA_', 'CUDA_', 'XDG_', 'HF_')) and k not in ('LD_LIBRARY_PATH', 'PYTHONPATH')}
    env.update(STRATA_REPLY_REUSE='1', STRATA_PRESERVE_THINKING='0', STRATA_DATA_DIR=str(c.BD / 'state/data'), XDG_DATA_HOME=str(c.BD / 'state/xdg-data'),
               XDG_CONFIG_HOME=str(c.BD / 'state/xdg-config'), XDG_CACHE_HOME=str(c.BD / 'state/xdg-cache'), PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1',
               STRATA_DRAFT_COSTS_DIR=str(c.BD / 'state/draft-costs'))
    c.dump(d / 'START.json', dict(arm=armname, argv=argv, epoch=time.time(), pre=s))
    guard = []; closed = threading.Event(); lock = threading.Lock()
    def stop():
        with lock:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try: proc.wait(timeout=90)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL); proc.wait(timeout=20)
    def monitor():
        prev = None; streak = 0
        try:
            with open(d / 'resources.jsonl', 'x') as f:
                while not closed.wait(2):
                    if proc.poll() is not None: raise RuntimeError('SERVER_EXIT %s' % proc.returncode)
                    cur = c.snapshot(); f.write(json.dumps(cur) + '\n'); f.flush()
                    c.gate(cur, c.descendants(proc.pid))
                    if prev:
                        streak = streak + 1 if (cur['swpin'] - prev['swpin']) >= 1024 else 0
                        if streak >= 5: raise RuntimeError('SUSTAINED_SWAP_IN')
                    prev = cur
        except Exception as e:
            guard.append(str(e)); stop()
    row = dict(arm=armname, legs={}, nsys={})
    with open(d / 'server.log', 'xb') as log:
        proc = subprocess.Popen(argv, cwd=d, env=env, stdout=log, stderr=log, start_new_session=True)
        th = threading.Thread(target=monitor, daemon=True); th.start()
        t0 = time.monotonic()
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
            for tag, fx in (('short', 'd3k'), ('long', 'c100k')):
                body = fixtures[fx]['body']
                r = c.chat(d, tag + '-prime', dict(body, max_tokens=1), model); row['legs'][tag + '-prime'] = r
                if r.get('error') or not r.get('done'): raise RuntimeError('PRIME_FAILED %s' % r.get('error'))
                rc, out = nsys('start', '--session=' + sess, '--output=' + str(d / tag), '--force-overwrite=true', '--sample=none', '--cpuctxsw=none')
                row['nsys'][tag + '-start'] = [rc, out]
                if rc != 0: raise RuntimeError('NSYS_START %s' % out)
                r = c.chat(d, tag + '-decode', dict(body, max_tokens=512), model); row['legs'][tag + '-decode'] = r
                rc, out = nsys('stop', '--session=' + sess)
                row['nsys'][tag + '-stop'] = [rc, out]
                print(armname, tag, json.dumps({k: r.get(k) for k in ('first_s', 'finish', 'error')}), r.get('timings'), 'nsys', rc, flush=True)
                if r.get('error') or not r.get('done') or rc != 0: raise RuntimeError('CAPTURE_FAILED %s %s' % (tag, out))
            return row
        finally:
            closed.set(); th.join(timeout=40); stop()
            subprocess.run([NSYS, 'shutdown', '--session=' + sess], capture_output=True, timeout=120)
            row['exit'] = dict(guard=guard, code=proc.returncode, ports=c.listening(), final=c.snapshot())
            c.dump(d / 'ROW.json', row)
            if guard or row['exit']['ports']: raise RuntimeError('EXIT_GUARD %s' % guard)

def main():
    names = sys.argv[1:]
    arms = json.loads((c.BD / 'arms.json').read_text()); fixtures = json.loads((c.BD / 'fixtures.json').read_text())
    out = c.BD / 'runs' / 'nsys'; out.mkdir(parents=True)
    before = {str(p): c.sha(p) for p in c.PROTECTED}
    c.gate(c.snapshot()); err = None
    try:
        for i, n in enumerate(names, 1):
            d = out / ('%02d-%s' % (i, n))
            print('START', i, n, flush=True); stage(d, n, arms[n], fixtures)
            for tag in ('short', 'long'):
                rep = d / (tag + '.nsys-rep')
                r = subprocess.run([NSYS, 'stats', '--report', 'cuda_gpu_kern_sum,cuda_gpu_mem_time_sum', '--format', 'csv', '--force-export=true',
                                    '--output', str(d / tag), str(rep)], capture_output=True, text=True, timeout=1800)
                print('STATS', n, tag, r.returncode, (r.stdout + r.stderr)[-300:].replace('\n', ' '), flush=True)
            for p in d.glob('*.sqlite'): p.unlink()
            print('DONE', i, n, flush=True)
    except BaseException as e:
        err = '%s: %s' % (type(e).__name__, e); print('ERROR', err, flush=True)
    finally:
        after = {str(p): c.sha(p) for p in c.PROTECTED}
        c.dump(out / 'RESULT.json', dict(error=err, protected_changed=[p for p in before if before[p] != after[p]], final=c.snapshot(), listeners=c.listening()))
        print('FINISHED', err, flush=True)

if __name__ == '__main__':
    os.umask(0o022); main()

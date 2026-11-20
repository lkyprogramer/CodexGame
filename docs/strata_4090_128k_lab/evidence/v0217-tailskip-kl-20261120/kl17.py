"""Teacher-forced KL of the route tail skip on the production B2 engine (2026-11-20).
Uses the upstream yardstick terminal/tools/quant_quality.py (v0.2.17, unchanged) on 5 x 1000 forced tokens per run;
one engine per run, own process group, guards on memory/temperature, production unit must be inactive."""
import json, os, signal, subprocess, sys, threading, time, hashlib
from pathlib import Path
sys.path.insert(0, '/data/strata-data/v0216-baseline-20261120')
import campaign as c
KD = Path('/data/strata-data/v0217-kl-20261120'); N = Path('/home/hhtele/strata-0.2.17')
QQ = N / 'terminal/tools/quant_quality.py'; PY = str(N / 'python/bin/python3')
TOK = '/data/strata-data/packs/iq3_xxs/tokenizer'
PLAN = [('cpu-ts0-a', None, '0'), ('cpu-ts7', None, '7'), ('cpu-ts0-b', None, '0'),
        ('auto-ts0-a', 'auto', '0'), ('auto-ts7', 'auto', '7'), ('auto-ts5', 'auto', '5'), ('auto-ts0-b', 'auto', '0')]
def log(*a): print(*a, flush=True)
def gate():
    s = c.snapshot(); c.gate(s)
    if s['gpu_pids']: raise RuntimeError('GPU busy %s' % s['gpu_pids'])
    return s
def main():
    (KD / 'runs').mkdir(parents=True)
    cfg = json.loads((N / 'strata-iq3_xxs.json').read_text())
    a = cfg['args']; a[a.index('--expert-profile-save') + 1] = str(KD / 'expert-profile-learned.bin')
    cfg.update(cwd=str(KD), log=str(KD / 'unused.log'), slot_save_path=str(KD / 'slots'))
    (KD / 'config.json').write_text(json.dumps(cfg, indent=1) + '\n')
    ids = KD / 'ids.json'
    log(subprocess.run([PY, '-B', str(QQ), 'ids', '--tokenizer', TOK, '--out', str(ids)], capture_output=True, text=True, check=True).stdout.strip())
    mine = json.loads(ids.read_text()); ship = json.loads((N / 'terminal/data/quant_quality/v1/set.ids.json').read_text())
    same = [m['ids'] == s['ids'] for m, s in zip(mine['segments'], ship['segments'])]
    log('ids equal to the shipped set per segment:', same)
    before = {str(p): c.sha(p) for p in c.PROTECTED + [N / 'data/expert-profile-iq3xxs.bin', N / 'strata-iq3_xxs.json']}
    res = dict(plan=PLAN, ids_equal_shipped=same, runs={}, error=None)
    try:
        for name, gx, ts in PLAN:
            while True:
                s = gate()
                if s['temp'] <= 50: break
                time.sleep(5)
            out = KD / 'runs' / (name + '.tsv')
            argv = [PY, '-B', str(QQ), 'run', '--config', str(KD / 'config.json'), '--out', str(out), '--ids', str(ids), '--env', 'STRATA_ROUTE_TAIL_SKIP=' + ts]
            if gx: argv += ['--gpu-experts', gx]
            log('START', name, ' '.join(argv[3:]))
            t0 = time.monotonic(); guard = []; done = threading.Event()
            with open(KD / 'runs' / (name + '.console.txt'), 'w') as f:
                p = subprocess.Popen(argv, cwd=str(KD), stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
                def mon():
                    mn = 10**9; mt = 0
                    while not done.wait(2):
                        s = c.snapshot(); mn = min(mn, s['avail_mib']); mt = max(mt, s['temp'])
                        res['runs'].setdefault(name, {}).update(min_avail=mn, max_temp=mt)
                        if s['avail_mib'] < 4096 or s['temp'] >= 85 or time.monotonic() - t0 > 2400:
                            guard.append('GUARD avail=%s temp=%s t=%.0f' % (s['avail_mib'], s['temp'], time.monotonic() - t0))
                            os.killpg(p.pid, signal.SIGTERM); time.sleep(20)
                            try: os.killpg(p.pid, signal.SIGKILL)
                            except ProcessLookupError: pass
                            return
                th = threading.Thread(target=mon, daemon=True); th.start()
                rc = p.wait(); done.set(); th.join(30)
            try: os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            time.sleep(5)
            con = (KD / 'runs' / (name + '.console.txt')).read_text(errors='replace')
            segs = [l for l in con.splitlines() if ' positions, ' in l]
            res['runs'].setdefault(name, {}).update(rc=rc, guard=guard, wall_s=round(time.monotonic() - t0, 1), segments=segs, gpu_after=c.snapshot()['gpu_used'])
            log('END', name, rc, guard, segs)
            if rc != 0 or guard: raise RuntimeError('RUN_FAILED %s rc=%s %s' % (name, rc, guard))
        R = KD / 'runs'
        for ref, runs in (('cpu-ts0-a', ['cpu-ts0-b', 'cpu-ts7']), ('auto-ts0-a', ['auto-ts0-b', 'auto-ts7', 'auto-ts5', 'cpu-ts0-a'])):
            cp = subprocess.run([PY, '-B', str(QQ), 'compare', str(R / (ref + '.tsv')), *[str(R / (x + '.tsv')) for x in runs], '--segments', '--json', str(KD / ('COMPARE-' + ref + '.json'))], capture_output=True, text=True)
            log(cp.stdout, cp.stderr[-2000:])
    except BaseException as e:
        res['error'] = '%s: %s' % (type(e).__name__, e); log('ERROR', res['error'])
    finally:
        after = {k: c.sha(k) for k in before}
        res.update(protected_changed=[k for k in before if before[k] != after[k]], final=c.snapshot())
        (KD / 'RESULT.json').write_text(json.dumps(res, indent=1) + '\n')
        log('FINISHED', res['error'], res['protected_changed'])
if __name__ == '__main__':
    os.umask(0o022); main()

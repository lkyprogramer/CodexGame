"""v0.2.16 baseline campaign on 4090: one fresh engine per stage, four frozen requests, port 18089 only."""
import hashlib, json, os, re, shlex, signal, subprocess, sys, threading, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BD = Path(__file__).resolve().parent
PROD = Path('/home/hhtele/strata-0.2.3')
PY216 = Path('/data/strata-data/dsv41-0210-lab/terminal/0.1.56/python/bin/python3')
EXE216 = BD / 'build/strata'
BASE = 'http://127.0.0.1:18089'
UNITS = ('openclaw-qwen38-next.service', 'openclaw-qwen38-ninfer.service')
LEGS = ('d3k', 'c32k', 'f10k', 'c100k')
PROTECTED = [PROD / x for x in ('strata-iq3_xxs.json', 'run-iq3_xxs.sh', 'engine/strata', 'data/expert-profile-iq3xxs.bin',
                                'serve/server.py', 'serve/frontend.py', 'tools/strata_tokenizer.py')]

def sh(argv, timeout=15):
    return subprocess.check_output(argv, text=True, timeout=timeout).strip()

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def dump(p, v):
    with open(p, 'x') as f:
        json.dump(v, f, ensure_ascii=False, indent=1)
        f.write('\n')

def snapshot():
    units = {u: sh(['systemctl', 'show', u, '-p', 'ActiveState', '--value']) for u in UNITS}
    t, used, free = [int(x) for x in sh(['nvidia-smi', '--query-gpu=temperature.gpu,memory.used,memory.free', '--format=csv,noheader,nounits']).split(',')]
    apps = sh(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'])
    mem = dict(l.split(':', 1) for l in Path('/proc/meminfo').read_text().splitlines())
    vm = dict(l.split() for l in Path('/proc/vmstat').read_text().splitlines())
    load = Path('/proc/loadavg').read_text().split()[0]
    st = os.statvfs(BD)
    return dict(epoch=time.time(), units=units, temp=t, gpu_used=used, gpu_free=free, gpu_pids=[int(x) for x in apps.split()],
                avail_mib=int(mem['MemAvailable'].split()[0]) // 1024, swpin=int(vm['pswpin']), swpout=int(vm['pswpout']),
                load1=float(load), disk_free_gib=st.f_bavail * st.f_frsize / 2**30)

def gate(s, pids=()):
    if any(v != 'inactive' for v in s['units'].values()): raise RuntimeError('PRODUCTION_NOT_STOPPED %s' % s['units'])
    if s['temp'] >= 85: raise RuntimeError('GPU_TEMPERATURE')
    if s['avail_mib'] < 4096: raise RuntimeError('LOW_AVAILABLE_MEMORY')
    if set(s['gpu_pids']) - set(pids): raise RuntimeError('FOREIGN_GPU_PROCESS %s' % s['gpu_pids'])
    if s['disk_free_gib'] < 30: raise RuntimeError('LOW_DISK')

def listening():
    return sh(['ss', '-H', '-ltn', 'sport = :18343 or sport = :18089'])

def descendants(root):
    rec = [tuple(map(int, l.split())) for l in sh(['ps', '-eo', 'pid=,ppid=']).splitlines()]
    live = {root}
    while True:
        new = {p for p, q in rec if q in live} - live
        if not new: return live
        live |= new

def get(path):
    with urlopen(BASE + path, timeout=3) as r:
        return json.load(r)

def chat(d, name, body, model):
    body = dict(body, model=model)
    req = Request(BASE + '/v1/chat/completions', json.dumps(body, ensure_ascii=False).encode(), {'Content-Type': 'application/json', 'Connection': 'close'})
    t0 = time.monotonic(); first = None; usage = timings = finish = None; done = False; nchunks = 0
    with open(d / (name + '.sse'), 'xb') as f:
        try:
            with urlopen(req, timeout=900) as r:
                for line in r:
                    f.write(line)
                    if not line.startswith(b'data:'): continue
                    pl = line[5:].strip()
                    if pl == b'[DONE]': done = True; break
                    it = json.loads(pl)
                    if it.get('error'): return dict(error=it['error'])
                    usage = it.get('usage') or usage; timings = it.get('timings') or timings
                    for ch in it.get('choices', []):
                        finish = ch.get('finish_reason') or finish
                        dl = ch.get('delta', {})
                        if any(dl.get(k) for k in ('content', 'reasoning_content', 'tool_calls')):
                            nchunks += 1
                            if first is None: first = time.monotonic() - t0
        except HTTPError as e:
            return dict(error='HTTP_%d %s' % (e.code, e.read()[:500]))
    return dict(first_s=first, wall_s=time.monotonic() - t0, usage=usage, timings=timings, finish=finish, done=done, chunks=nchunks)

def build_cfg(d, arm):
    cfg = json.loads((PROD / 'strata-iq3_xxs.json').read_text())
    args = cfg['args']
    args[args.index('--expert-profile-save') + 1] = str(d / 'expert-profile-learned.bin')
    cfg.update(cwd=str(d), log=str(d / 'engine.log'), port=18089, parallel=1, api_monitor=False, slot_save_path=str(d / 'slots'),
               engine_ready_s=400, open_browser=False)
    if arm.get('kind') == 'a0':
        return cfg, [str(PROD / '.venv/bin/python'), '-B', str(PROD / 'serve/server.py')]
    args += ['--lookup-max-t', '0', '--conversation-spill-mib', '0', '--ple-io', 'direct']
    for k in arm.get('drop', []):
        i = args.index(k); del args[i:i + 2]
    for k, v in arm.get('args', {}).items():
        if k in args: args[args.index(k) + 1] = v
        else: args += [k, v]
    cfg['env'] = dict(cfg.get('env') or {}, **arm.get('env', {}))
    for k in arm.get('env_drop', []): cfg['env'].pop(k, None)
    cfg.update(exe=str(EXE216), drafting='mtp', draft_costs=False, lib_dirs=[str(EXE216.parent), *cfg.get('lib_dirs', [])])
    return cfg, [str(PY216), '-B', str(BD / 'src/terminal/serve/server.py')]

FACTS = re.compile(r'expert cache auto|expert cache \d+ slots|prompt chunk auto|borrows|VRAM free with everything|PLE |ple-io|small expert cache|layer-major|LAB_PR_1536|LAB_CFG_PT|session is up|spill|lookup|checkpoint|LOW|WARNING|memory guard|expert arena|loaded [0-9.]+ GiB')

def stage(d, armname, arm, fixtures, deadline):
    t_wait = time.monotonic()
    while True:
        s = snapshot(); gate(s)
        if listening(): raise RuntimeError('PORT_OCCUPIED')
        if s['temp'] <= 50: break
        if time.monotonic() > deadline: raise RuntimeError('COOLDOWN_DEADLINE')
        time.sleep(5)
    d.mkdir(parents=True); (d / 'slots').mkdir()
    cfg, cmd = build_cfg(d, arm)
    dump(d / 'profile.json', cfg)
    argv = cmd + ['--engine', 'strata', '--config', str(d / 'profile.json'), '--host', '127.0.0.1', '--port', '18089', '--offline']
    env = {k: v for k, v in os.environ.items() if not k.startswith(('STRATA_', 'CUDA_', 'XDG_', 'HF_')) and k not in ('LD_LIBRARY_PATH', 'PYTHONPATH')}
    env.update(STRATA_REPLY_REUSE='1', STRATA_PRESERVE_THINKING='0', STRATA_DATA_DIR=str(BD / 'state/data'), XDG_DATA_HOME=str(BD / 'state/xdg-data'),
               XDG_CONFIG_HOME=str(BD / 'state/xdg-config'), XDG_CACHE_HOME=str(BD / 'state/xdg-cache'), PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1',
               STRATA_DRAFT_COSTS_DIR=str(BD / 'state/draft-costs'))
    dump(d / 'START.json', dict(arm=armname, def_=arm, argv=argv, epoch=time.time(), pre=s, cooldown_s=time.monotonic() - t_wait))
    closed = threading.Event(); guard = []; lock = threading.Lock()
    def stop():
        with lock:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try: proc.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL); proc.wait(timeout=20)
    def monitor():
        prev = None; streak = 0
        try:
            with open(d / 'resources.jsonl', 'x') as f:
                while not closed.wait(2):
                    if proc.poll() is not None: raise RuntimeError('SERVER_EXIT %s' % proc.returncode)
                    cur = snapshot(); f.write(json.dumps(cur) + '\n'); f.flush()
                    gate(cur, descendants(proc.pid))
                    if prev:
                        # swap-out while the 40 GiB arena loads is a one-time eviction of other services' idle pages (swap is 976 MB);
                        # thrash is sustained swap-IN, which is what stops a stage
                        streak = streak + 1 if (cur['swpin'] - prev['swpin']) >= 1024 else 0
                        if streak >= 5: raise RuntimeError('SUSTAINED_SWAP_IN')
                    prev = cur
        except Exception as e:
            guard.append(str(e)); stop()
    row = dict(arm=armname, legs={})
    with open(d / 'server.log', 'xb') as log:
        proc = subprocess.Popen(argv, cwd=d, env=env, stdout=log, stderr=log, start_new_session=True)
        th = threading.Thread(target=monitor, daemon=True); th.start()
        t0 = time.monotonic()
        try:
            while True:
                if guard or proc.poll() is not None: raise RuntimeError('READY_FAILED %s %s' % (guard, proc.poll()))
                if time.monotonic() - t0 > 480: raise RuntimeError('READY_TIMEOUT')
                try: h = get('/health')
                except OSError: time.sleep(1); continue
                if h.get('loaded'): break
                time.sleep(1)
            row['ready_s'] = time.monotonic() - t0; row['health'] = h
            assert h.get('max_context') == 131072, h
            elog = (d / 'engine.log').read_text(errors='replace').splitlines()
            started = next(l for l in elog if 'engine started:' in l)
            native = shlex.split(started.split('engine started:', 1)[1])[1:]
            want = cfg['args']
            bad = [x for i, x in enumerate(want) if x.startswith('--') and i + 1 < len(want) and not want[i + 1].startswith('--')
                   and not (native.count(x) == 1 and native[native.index(x) + 1] == want[i + 1])]
            row['native_args'] = native; row['arg_mismatch'] = bad
            if bad: raise RuntimeError('ARG_MISMATCH %s' % bad)
            row['startup_facts'] = [l.strip()[:400] for l in elog if FACTS.search(l)]
            row['server_facts'] = [l.strip()[:400] for l in (d / 'server.log').read_text(errors='replace').splitlines() if FACTS.search(l)]
            for leg in LEGS:
                if guard: raise RuntimeError(guard[0])
                fx = fixtures[leg]
                r = chat(d, leg, fx['body'], h.get('model') or 'openclaw/Qwen3.8-next')
                r['want_prompt_tokens'] = fx['prompt_tokens']
                row['legs'][leg] = r
                print(armname, leg, json.dumps({k: r.get(k) for k in ('first_s', 'finish', 'error')}), (r.get('timings') or {}), flush=True)
                if r.get('error') or not r.get('done'): raise RuntimeError('LEG_FAILED %s %s' % (leg, r.get('error')))
            try: row['metrics'] = get('/metrics') if False else None
            except Exception: pass
            return row
        finally:
            closed.set(); th.join(timeout=40); stop()
            final = snapshot(); ports = listening()
            row['exit'] = dict(guard=guard, code=proc.returncode, ports=ports, final=final)
            dump(d / 'ROW.json', row)
            if guard or ports: raise RuntimeError('EXIT_GUARD %s %s' % (guard, ports))

def main():
    run, names = sys.argv[1], sys.argv[2:]
    arms = json.loads((BD / 'arms.json').read_text())
    fixtures = json.loads((BD / 'fixtures.json').read_text())
    out = BD / 'runs' / run; out.mkdir(parents=True)
    for x in ('state/data', 'state/xdg-data', 'state/xdg-config', 'state/xdg-cache', 'state/draft-costs'): (BD / x).mkdir(parents=True, exist_ok=True)
    before = {str(p): sha(p) for p in PROTECTED}
    dump(out / 'PLAN.json', dict(arms=names, defs={n: arms[n] for n in set(names)}, fixtures_sha=sha(BD / 'fixtures.json'),
                                 engine_sha=sha(EXE216) if EXE216.exists() else None, patch_sha=sha(BD / 'v0216-pt0-reply-reuse.patch'), protected=before))
    gate(snapshot())
    deadline = time.monotonic() + 6 * 3600
    rows, err = [], None
    try:
        for i, n in enumerate(names, 1):
            print('START', i, n, flush=True)
            rows.append(stage(out / ('%02d-%s' % (i, n)), n, arms[n], fixtures, deadline))
            print('DONE', i, n, flush=True)
    except BaseException as e:
        err = '%s: %s' % (type(e).__name__, e); print('ERROR', err, flush=True)
    finally:
        after = {str(p): sha(p) for p in PROTECTED}
        dump(out / 'RESULT.json', dict(error=err, n=len(rows), protected_changed=[p for p in before if before[p] != after[p]],
                                       final=snapshot(), listeners=listening()))
        print('FINISHED', err, flush=True)

if __name__ == '__main__':
    os.umask(0o022)
    main()

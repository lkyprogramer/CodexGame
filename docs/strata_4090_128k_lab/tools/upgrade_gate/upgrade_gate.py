"""One-command upgrade gate for a new Strata release on the 4090 (prepared 2026-11-21, CodexGame lab).

    upgrade_gate.py prepare TAG [--tree DIR] [-j N]  fetch the tag, export engine/terminal, apply the PT0/#1536 patch, build
                                                     (CUDA 12.3, sm_89), assemble a tree; production keeps running
    upgrade_gate.py kl TAG [--repeat]                teacher-forced KL against the stored v0.2.17 runs (stops production ~10 min)
    upgrade_gate.py gate TAG [--force] [--limit N]   one task-gate arm against the stored b2 arm (stops production ~2 h);
                                                     --limit N is a wiring smoke test in TAG/smoke, no decision
    upgrade_gate.py report TAG
    upgrade_gate.py all TAG [-j N]                   prepare -> kl -> gate (only when kl says PROCEED) -> report
    upgrade_gate.py switch TAG --yes [--force]       hand production over to the new tree; rolls back by itself if health fails

Production is stopped and started only through the NOPASSWD unit rule; a phase that stops it restores the state it found
in a finally block (SIGTERM included).  Nothing here writes the production tree, /home/hhtele/strata-0.1.43.1, the driver
or CUDA, and nothing kills processes it did not start."""
import argparse, fcntl, hashlib, json, os, re, shlex, shutil, signal, subprocess, sys, threading, time
from contextlib import contextmanager
from pathlib import Path
from urllib.request import Request, urlopen

UG = Path(os.environ.get('UPGRADE_GATE_DIR', '/data/strata-data/upgrade-gate'))
REPO_URL = 'https://github.com/Niko1221/Strata.git'; API = 'https://api.github.com/repos/Niko1221/Strata'
UNIT = 'openclaw-qwen38-next.service'
PROD_RUN = Path('/home/hhtele/strata-0.2.3/run-iq3_xxs.sh')   # the unit's ExecStart; it only execs the current tree's run script
PROD_PORT = 18343
CMAKE = '/home/hhtele/strata-0.1.43.1/.venv/lib/python3.11/site-packages/cmake/data/bin/cmake'   # executed, never written
NVCC = '/usr/local/cuda-12.3/bin/nvcc'
PATCH = UG / 'pt0-reply-reuse.patch'                          # = CodexGame patches/v0217-pt0-reply-reuse.patch
def patch_for(tag):
    """A hand port for one release (pt0-reply-reuse.<tag>.patch, = CodexGame patches/<tag>-pt0-reply-reuse.patch) wins."""
    p = UG / ('pt0-reply-reuse.%s.patch' % tag)
    return p if p.exists() else PATCH
KD = Path('/data/strata-data/v0217-kl-20261120')              # ids.json, runs/auto-ts7.tsv (B2), runs/auto-ts0-a.tsv (exact)
GD = Path('/data/strata-data/v0217-gate-20261120')            # PREREG.json, gate17.py, quality_gate.py, arms/b2
PRODLOG = Path('/data/strata-data/prod-observe/prodlog.py')
TAIL_SKIP = '7'
# KL decision, fixed before any new release is seen: 1.25x the level accepted for v0.2.17 rank 7 against exact routing
# (all 0.047, agent segment 0.136; V0217-TAILSKIP-KL).  Above either bound the task gate is not run (KL_REGRESSION).
KL_ALL_MAX, KL_AGENT_MAX = 0.060, 0.170
GUARD_AVAIL_MIB, GUARD_TEMP = 3072, 85


class Stop(Exception):
    """A planned stop with a reason; the phase records it and the command exits 2."""


def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()
def run(argv, **kw):
    kw.setdefault('capture_output', True); kw.setdefault('text', True)
    return subprocess.run([str(x) for x in argv], **kw)
def wdir(tag): return UG / tag
def load(tag, name):
    p = wdir(tag) / name
    return json.loads(p.read_text()) if p.exists() else None
def save(tag, name, doc):
    p = wdir(tag) / name; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=1) + '\n'); return doc
def arm_name(tag): return 'v' + re.sub(r'[^0-9A-Za-z]', '', tag.lstrip('v'))


def snapshot():
    mem = {l.split(':')[0]: int(l.split()[1]) for l in open('/proc/meminfo') if l.startswith(('MemAvailable', 'SwapFree'))}
    q = run(['nvidia-smi', '--query-gpu=temperature.gpu,memory.used', '--format=csv,noheader,nounits']).stdout.split(',')
    pids = [x for x in run(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader']).stdout.split() if x]
    return dict(avail_mib=mem['MemAvailable'] // 1024, swap_free_mib=mem['SwapFree'] // 1024, temp=int(q[0]), gpu_used=int(q[1]), gpu_pids=pids)


def run_guarded(argv, out_path, limit_s, cwd=None, env=None, temp_guard=False):
    """Run argv in its own process group with memory/temperature/time guards; returns (rc, guard reasons)."""
    guard = []; done = threading.Event()
    with open(out_path, 'a') as f:
        p = subprocess.Popen([str(x) for x in argv], cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
        t0 = time.monotonic()
        def kill():
            for s in (signal.SIGTERM, signal.SIGKILL):
                try: os.killpg(p.pid, s)
                except ProcessLookupError: return
                for _ in range(30):
                    if p.poll() is not None: return
                    time.sleep(1)
        def mon():
            while not done.wait(3):
                s = snapshot()
                if s['avail_mib'] < GUARD_AVAIL_MIB or (temp_guard and s['temp'] >= GUARD_TEMP) or time.monotonic() - t0 > limit_s:
                    guard.append('GUARD avail=%s temp=%s t=%.0f' % (s['avail_mib'], s['temp'], time.monotonic() - t0)); kill(); return
        th = threading.Thread(target=mon, daemon=True); th.start()
        try:
            rc = p.wait()
        except BaseException:
            kill(); raise
        finally:
            done.set(); th.join(10)
        try: os.killpg(p.pid, signal.SIGKILL)       # leftovers of our own group only
        except ProcessLookupError: pass
    return rc, guard


def unit_state(): return run(['systemctl', 'is-active', UNIT]).stdout.strip()
def systemctl(verb):
    rc = run(['sudo', '-n', '/usr/bin/systemctl', verb, UNIT]).returncode; log('production', verb, 'rc=%d' % rc); return rc


@contextmanager
def production_stopped():
    was = unit_state()
    if was not in ('active', 'inactive'): raise Stop('production unit is %r; refusing to touch it' % was)
    if was == 'active':
        if systemctl('stop') != 0: raise Stop('could not stop production (sudo -n rule?)')
        for _ in range(200):
            if unit_state() == 'inactive': break
            time.sleep(1)
    try:
        for _ in range(60):
            s = snapshot()
            if s['gpu_used'] < 500 and not s['gpu_pids']: break
            time.sleep(2)
        else:
            raise Stop('GPU still busy after production stop: %s' % s)
        yield
    finally:
        if was == 'active': systemctl('start')


def cur_tree():
    m = re.search(r'^exec (\S+)/run-iq3_xxs\.sh\s*$', PROD_RUN.read_text(), re.M)
    if not m: raise Stop('cannot find the current tree in %s' % PROD_RUN)
    return Path(m.group(1))


def health(port, timeout_s):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        try:
            h = json.loads(urlopen('http://127.0.0.1:%d/health' % port, timeout=3).read())
            if h.get('status') == 'ok' and h.get('loaded'): return True
        except Exception: pass
        time.sleep(5)
    return False


# ---------------------------------------------------------------- prepare
def prepare(tag, tree=None, jobs=8):
    W = wdir(tag); W.mkdir(parents=True, exist_ok=True)
    tree = Path(tree) if tree else Path('/home/hhtele/strata-' + tag.lstrip('v'))
    done = load(tag, 'PREPARE.json')
    if done and done.get('status') == 'READY' and Path(done['tree']).exists():
        log('prepare: already READY at', done['tree']); return done
    if tree.exists(): raise Stop('tree %s exists and has no READY record; move it away by hand' % tree)
    cur = cur_tree(); doc = dict(tag=tag, tree=str(tree), from_tree=str(cur), started=time.strftime('%Y-%m-%d %H:%M:%S'), status='RUNNING')
    try:
        return _prepare(tag, tree, jobs, W, cur, doc)
    except Stop as e:
        save(tag, 'PREPARE.json', dict(doc, status='STOPPED', stop=str(e))); raise


def _prepare(tag, tree, jobs, W, cur, doc):
    PATCH = patch_for(tag)
    if not PATCH.exists(): raise Stop('missing %s' % PATCH)
    doc.update(patch=str(PATCH), patch_sha256=sha(PATCH))
    # fetch: a private shallow bare mirror; the tag object and commit are checked against the GitHub API
    G = UG / 'strata.git'
    if not G.exists():
        run(['git', 'init', '-q', '--bare', G], check=True); run(['git', '-C', G, 'remote', 'add', 'origin', REPO_URL], check=True)
    r = run(['git', '-C', G, 'fetch', '-q', '--depth', '1', '--no-tags', 'origin', '+refs/tags/%s:refs/tags/%s' % (tag, tag)])
    if r.returncode: raise Stop('fetch %s failed: %s' % (tag, r.stderr[-500:]))
    tag_obj = run(['git', '-C', G, 'rev-parse', 'refs/tags/' + tag], check=True).stdout.strip()
    commit = run(['git', '-C', G, 'rev-parse', tag + '^{commit}'], check=True).stdout.strip()
    doc.update(tag_object=tag_obj, tag_type=run(['git', '-C', G, 'cat-file', '-t', tag_obj]).stdout.strip(), tag_commit=commit)
    try:
        hdr = {'User-Agent': 'upgrade-gate', 'Accept': 'application/vnd.github+json'}
        ref = json.loads(urlopen(Request(API + '/git/ref/tags/' + tag, headers=hdr), timeout=20).read())
        doc['api_tag_object'] = ref['object']['sha']
        if ref['object']['sha'] != tag_obj: raise Stop('tag object %s differs from the API %s' % (tag_obj, ref['object']['sha']))
        rel = json.loads(urlopen(Request(API + '/releases/tags/' + tag, headers=hdr), timeout=20).read())
        doc.update(release_published=rel.get('published_at'), prerelease=rel.get('prerelease'))
    except Stop: raise
    except Exception as e:
        doc['api_check'] = 'unavailable: %s' % e     # the fetch itself came from GitHub; recorded, not fatal
    log('tag', tag, tag_obj, 'commit', commit)
    # export engine/ and terminal/
    src = W / 'src'
    if src.exists(): shutil.rmtree(src)
    src.mkdir()
    subprocess.run('git -C %s archive --format=tar refs/tags/%s engine terminal | tar -x -C %s' % (shlex.quote(str(G)), shlex.quote(tag), shlex.quote(str(src))),
                   shell=True, check=True)
    for d in ('engine/CMakeLists.txt', 'terminal/serve/server.py', 'terminal/tools/quant_quality.py'):
        if not (src / d).exists(): raise Stop('LAYOUT_CHANGED: %s missing in %s' % (d, tag))
    # patch: zero fuzz (offsets allowed); a conflict needs a hand port
    files = re.findall(r'^\+\+\+ b/(\S+)', PATCH.read_text(), re.M)
    orig = W / 'orig'
    if orig.exists(): shutil.rmtree(orig)
    for f in files:
        if (src / f).exists(): (orig / f).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src / f, orig / f)
    r = run(['patch', '-p1', '-F0', '-N', '--batch', '--dry-run', '-d', src, '-i', PATCH])
    if r.returncode: save(tag, 'patch-dry-run.txt.json', dict(out=r.stdout + r.stderr)); raise Stop('PATCH_CONFLICT: the PT0/#1536 patch needs a hand port:\n' + r.stdout[-1500:])
    r = run(['patch', '-p1', '-F0', '-N', '--batch', '-d', src, '-i', PATCH], check=True)
    doc['patch_output'] = r.stdout.strip().splitlines()
    regen = ''.join(run(['diff', '-uNp', '--label', 'a/' + f, '--label', 'b/' + f, orig / f, src / f]).stdout for f in files)
    (W / ('pt0-reply-reuse.%s.patch' % tag)).write_text(regen)
    doc['patched_files'] = {f: sha(src / f) for f in files}
    # the patch's own tests plus the serve suites it touches (CPU only, ~2.5 min; the v0.2.17 port ran 492 OK)
    log('unit tests: serve.test_prompt_encoder serve.test_frontend serve.test_server')
    rc, g = run_guarded(['nice', '-n', '10', cur / 'python/bin/python3', '-B', '-m', 'unittest', 'serve.test_prompt_encoder', 'serve.test_frontend',
                         'serve.test_server'], W / 'unittest.log', 1800, cwd=src / 'terminal', env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    tail = (W / 'unittest.log').read_text(errors='replace')[-600:]
    m = re.search(r'Ran (\d+) tests', tail)
    doc['unittest'] = dict(rc=rc, guard=g, ran=int(m.group(1)) if m else None, tail=tail.strip().splitlines()[-3:])
    if rc or g: raise Stop('unit tests failed rc=%s %s (see unittest.log)' % (rc, g))
    # build: same options as v0.2.16/v0.2.17 (B1/B2); nice, guarded, production keeps running
    B = W / 'build'
    if B.exists(): shutil.rmtree(B)
    log('build: cmake configure')
    rc, g = run_guarded(['nice', '-n', '10', CMAKE, '-S', src / 'engine', '-B', B, '-G', 'Ninja', '-DCMAKE_MAKE_PROGRAM=/usr/bin/ninja',
                         '-DCMAKE_BUILD_TYPE=Release', '-DSTRATA_ENABLE_CUDA=ON', '-DSTRATA_BUILD_TESTS=OFF', '-DCMAKE_CUDA_ARCHITECTURES=89',
                         '-DCMAKE_CUDA_COMPILER=' + NVCC], W / 'cmake.log', 1800)
    if rc or g: raise Stop('cmake failed rc=%s %s (see cmake.log)' % (rc, g))
    t0 = time.monotonic(); log('build: ninja -j', jobs)
    rc, g = run_guarded(['nice', '-n', '10', CMAKE, '--build', B, '--target', 'strata', '-j', jobs], W / 'build.log', 7200)
    if rc or g: raise Stop('build failed rc=%s %s (see build.log)' % (rc, g))
    eng = B / 'strata'
    doc.update(build_s=round(time.monotonic() - t0), engine_sha256=sha(eng), engine_version=run([eng, '--version']).stdout.strip())
    log('engine', doc['engine_version'], doc['engine_sha256'][:16], 'in %d s' % doc['build_s'])
    # tree: everything except terminal/ and engine comes from the current production tree, paths rewritten
    tree.mkdir(parents=True)
    shutil.copytree(src / 'terminal', tree / 'terminal', symlinks=True, ignore=shutil.ignore_patterns('__pycache__'))
    (tree / 'engine').mkdir(); shutil.copy2(eng, tree / 'engine/strata')
    shutil.copytree(cur / 'python', tree / 'python', symlinks=True)
    shutil.copy2(PATCH, tree / PATCH.name)
    for d in ('data', 'slots', 'state/data', 'state/xdg-data', 'state/xdg-config', 'state/xdg-cache', 'state/draft-costs'): (tree / d).mkdir(parents=True, exist_ok=True)
    cfg = json.loads((cur / 'strata-iq3_xxs.json').read_text()); a = cfg['args']
    prof = Path(a[a.index('--expert-profile') + 1])
    shutil.copy2(prof, tree / 'data' / prof.name)
    def rew(x):
        if isinstance(x, str): return x.replace(str(cur), str(tree))
        if isinstance(x, list): return [rew(v) for v in x]
        if isinstance(x, dict): return {k: rew(v) for k, v in x.items()}
        return x
    cfg = rew(cfg); a = cfg['args']
    if cfg['exe'] != str(tree / 'engine/strata') or a[a.index('--expert-profile') + 1] != str(tree / 'data' / prof.name): raise Stop('config rewrite went wrong')
    (tree / 'strata-iq3_xxs.json').write_text(json.dumps(cfg, indent=2) + '\n')
    refs = sorted(set(re.findall(re.escape(str(tree)) + r'[^"\s]*', json.dumps(cfg))))
    created = {str(tree / 'strata-iq3_xxs.log'), a[a.index('--expert-profile-save') + 1]}
    missing = [p for p in refs if p not in created and not Path(p).exists()]
    if missing: raise Stop('config names paths the tree does not have: %s' % missing)
    rs = (cur / 'run-iq3_xxs.sh').read_text().replace(str(cur), str(tree)).splitlines(True)
    rs.insert(1, '# %s: %s tree assembled by upgrade_gate.py from %s (paths rewritten; the comments below describe that tree)\n'
              % (time.strftime('%Y-%m-%d'), tag, cur))
    (tree / 'run-iq3_xxs.sh').write_text(''.join(rs)); os.chmod(tree / 'run-iq3_xxs.sh', 0o755)
    # preflight: every CLI flag of the config is known to the new engine, and serve imports with the copied python
    h = run([tree / 'engine/strata', '--help']); helptext = h.stdout + h.stderr        # the engine prints its usage on stderr
    if '--pack' not in helptext: raise Stop('engine --help gave no usage text: %s' % helptext[-500:])
    doc['flags_not_in_help'] = [f for f in a if f.startswith('--') and not re.search(re.escape(f) + r'(?![w-])', helptext)]
    r = run([tree / 'python/bin/python3', '-B', tree / 'terminal/serve/server.py', '--help'], cwd=tree, timeout=120,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    doc['serve_help_rc'] = r.returncode
    if r.returncode: raise Stop('serve does not start with the copied python: %s' % (r.stdout + r.stderr)[-1500:])
    doc.update(config_sha256=sha(tree / 'strata-iq3_xxs.json'), run_sha256=sha(tree / 'run-iq3_xxs.sh'),
               expert_profile=prof.name, expert_profile_sha256=sha(tree / 'data' / prof.name))
    ident = {k: doc[k] for k in ('tag', 'tag_object', 'tag_commit', 'engine_sha256', 'engine_version', 'patch_sha256', 'patched_files',
                                 'config_sha256', 'run_sha256', 'expert_profile_sha256')}
    ident.update(python=str(cur / 'python') + ' (copied)', created=time.strftime('%Y-%m-%d'), by='upgrade_gate.py')
    (tree / 'IDENTITY.json').write_text(json.dumps(ident, indent=1) + '\n')
    doc.update(status='READY', finished=time.strftime('%Y-%m-%d %H:%M:%S'))
    if doc['flags_not_in_help']: log('WARN flags not in --help (check before the KL phase):', doc['flags_not_in_help'])
    log('prepare READY', tree); return save(tag, 'PREPARE.json', doc)


# ---------------------------------------------------------------- kl
def kl(tag, repeat=False):
    prep = load(tag, 'PREPARE.json')
    if not prep or prep.get('status') != 'READY': raise Stop('run prepare first')
    tree = Path(prep['tree']); K = wdir(tag) / 'kl'; K.mkdir(parents=True, exist_ok=True)
    PY = tree / 'python/bin/python3'; QQ = tree / 'terminal/tools/quant_quality.py'
    cfg = json.loads((tree / 'strata-iq3_xxs.json').read_text()); a = cfg['args']
    a[a.index('--expert-profile-save') + 1] = str(K / 'expert-profile-learned.bin')
    cfg.update(cwd=str(K), log=str(K / 'unused.log'), slot_save_path=str(K / 'slots'))
    (K / 'config.json').write_text(json.dumps(cfg, indent=1) + '\n')
    names = ['new-ts7'] + (['new-ts7-b'] if repeat else [])
    doc = dict(tag=tag, engine_sha256=prep['engine_sha256'], ids=str(KD / 'ids.json'), ids_sha256=sha(KD / 'ids.json'), runs={},
               thresholds=dict(kl_all_max=KL_ALL_MAX, kl_agent_max=KL_AGENT_MAX))
    with production_stopped():
        for n in names:
            out = K / (n + '.tsv')
            if out.exists(): out.unlink()
            while snapshot()['temp'] > 50: time.sleep(5)
            t0 = time.monotonic(); log('KL run', n)
            rc, g = run_guarded([PY, '-B', QQ, 'run', '--config', K / 'config.json', '--out', out, '--ids', KD / 'ids.json',
                                 '--env', 'STRATA_ROUTE_TAIL_SKIP=' + TAIL_SKIP, '--gpu-experts', 'auto'], K / (n + '.console.txt'), 2400,
                                cwd=K, temp_guard=True)
            doc['runs'][n] = dict(rc=rc, guard=g, wall_s=round(time.monotonic() - t0, 1))
            if rc or g: save(tag, 'KL.json', dict(doc, verdict='RUN_FAILED')); raise Stop('KL run %s failed rc=%s %s' % (n, rc, g))
    cmp = {}
    for key, ref in (('vs_v0217_ts7', KD / 'runs/auto-ts7.tsv'), ('vs_v0217_exact', KD / 'runs/auto-ts0-a.tsv')):
        js = K / ('COMPARE-%s.json' % key); used = None
        for q in (QQ, cur_tree() / 'terminal/tools/quant_quality.py'):
            r = run([PY, '-B', q, 'compare', ref, *[K / (n + '.tsv') for n in names], '--segments', '--json', js])
            if r.returncode == 0 and js.exists(): used = str(q); break
        if not used: raise Stop('quant_quality compare failed: %s' % r.stderr[-800:])
        cmp[key] = dict(tool=used, result=json.loads(js.read_text())[str(K / 'new-ts7.tsv')])
        if repeat and key == 'vs_v0217_ts7': cmp['repeat'] = json.loads(js.read_text())[str(K / 'new-ts7-b.tsv')]['all']
    drift, ex = cmp['vs_v0217_ts7']['result']['all'], cmp['vs_v0217_exact']['result']
    doc['compare'] = {k: (v['result']['all'] if isinstance(v, dict) and 'result' in v else v) for k, v in cmp.items()}
    doc['agent_vs_exact'] = ex['agent']
    doc['numerics_identical_to_v0217'] = drift['kl'] == 0 and drift['top1'] == 1
    doc['verdict'] = 'PROCEED' if ex['all']['kl'] <= KL_ALL_MAX and ex['agent']['kl'] <= KL_AGENT_MAX else 'KL_REGRESSION'
    log('KL vs v0.2.17 rank7: %.4f top1 %.3f | vs exact: %.4f (agent %.4f) -> %s' % (drift['kl'], drift['top1'], ex['all']['kl'], ex['agent']['kl'], doc['verdict']))
    return save(tag, 'KL.json', doc)


# ---------------------------------------------------------------- gate
def gate(tag, force=False, limit=None, extra_env=None):
    prep = load(tag, 'PREPARE.json'); klr = load(tag, 'KL.json')
    if not prep or prep.get('status') != 'READY': raise Stop('run prepare first')
    if not limit and not force and (not klr or klr.get('verdict') != 'PROCEED'): raise Stop('KL verdict is not PROCEED (use --force to override)')
    extra_env = dict(extra_env or {}); env = dict(extra_env, STRATA_ROUTE_TAIL_SKIP=TAIL_SKIP)
    tree = Path(prep['tree']); pre = json.loads((GD / 'PREREG.json').read_text())
    arm = arm_name(tag) + ''.join('-%s%s' % (k.replace('STRATA_', '').lower(), v) for k, v in sorted(extra_env.items()))
    sys.path.insert(0, str(GD)); import gate17
    gate17.N = tree
    if limit:                       # wiring smoke: a private copy of the prereg, its own arm dir, no pairs/decision
        S = wdir(tag) / 'smoke'; shutil.rmtree(S / 'arms' / arm, ignore_errors=True); S.mkdir(parents=True, exist_ok=True); shutil.copy2(GD / 'PREREG.json', S / 'PREREG.json'); gate17.GD = S
        orig = gate17.run_task; n = [0]
        class Enough(Exception): pass
        def limited(*a, **k):
            if n[0] >= limit: raise Enough()
            n[0] += 1; return orig(*a, **k)
        gate17.run_task = limited
        with production_stopped():
            try: gate17.arm(arm, env)
            except Enough: pass
        rows = [json.loads(l) for l in open(S / 'arms' / arm / 'rows.jsonl')]
        b2 = {json.loads(l)['task_id']: json.loads(l) for l in open(GD / 'arms/b2/rows.jsonl')}
        def e2e(rs):    # end-to-end completion tok/s over the same first tasks (tracks the full-arm decode ratio within ~1.5%)
            t = sum(a['completion_tokens'] or 0 for r in rs for a in r.get('attempts', [])); w = sum(a['wall_s'] for r in rs for a in r.get('attempts', []))
            return dict(tok_s=round(t / w, 1) if w else None, tokens=t, wall_s=round(w, 1))
        ids = [r['task_id'] for r in rows]
        speed = {'smoke:' + arm: e2e(rows)}
        for n in sorted(p.name for p in (GD / 'arms').iterdir() if (p / 'rows.jsonl').exists()):
            other = {json.loads(l)['task_id']: json.loads(l) for l in open(GD / 'arms' / n / 'rows.jsonl')}
            if all(t in other for t in ids): speed[n] = e2e([other[t] for t in ids])
        doc = dict(tag=tag, limit=limit, env=env, arm=arm, speed_same_tasks=speed, passes=dict(pass1=sum(bool(r.get('pass1')) for r in rows),
                   pass2=sum(bool(r.get('pass2')) for r in rows), errors=sum('error' in r for r in rows)),
                   rows=[dict(task_id=r['task_id'], error=r.get('error'), pass1=r.get('pass1'), pass2=r.get('pass2'),
                   b2_pass1=b2[r['task_id']].get('pass1'), b2_pass2=b2[r['task_id']].get('pass2')) for r in rows])
        log('smoke', arm, json.dumps(speed)); return save(tag, 'SMOKE-%s.json' % arm, doc)
    # addendum preregistration: written before the arm runs, refuses to change afterwards
    pa = GD / ('PREREG-%s.json' % arm)
    add = dict(tag=tag, tree=str(tree), engine_sha256=prep['engine_sha256'], patched_files=prep['patched_files'], config_sha256=prep['config_sha256'],
               base_prereg_sha256=sha(GD / 'PREREG.json'), driver_sha256=sha(GD / 'gate17.py'), baseline='b2 (stored v0.2.17 arm, not re-run)',
               baseline_rows_sha256=sha(GD / 'arms/b2/rows.jsonl'), candidate=arm, env=env, margin=pre['margin'],
               kl_verdict=(klr or {}).get('verdict'), forced=bool(force),
               note='same task ids, seeds (1000+index), prompts, grader image and driver as PREREG.json; the two original arms also ran one '
                    'after the other, so reusing the stored b2 arm keeps the pairing by task and seed')
    if pa.exists():
        old = json.loads(pa.read_text()); diff = [k for k in add if k not in ('forced', 'kl_verdict') and old.get(k) != add[k]]
        if diff: raise Stop('addendum prereg exists with different %s; refusing' % diff)
    else:
        pa.write_text(json.dumps(dict(add, created=time.strftime('%Y-%m-%d %H:%M:%S')), indent=1) + '\n')
    ad = GD / 'arms' / arm
    have = [json.loads(l) for l in open(ad / 'rows.jsonl')] if (ad / 'rows.jsonl').exists() else []
    if len(have) == pre['n'] and not any('error' in r for r in have):
        log('arm %s already complete (%d rows): deciding only, production untouched' % (arm, len(have)))
    else:
        with production_stopped():
            gate17.arm(arm, env)
    rows = [json.loads(l) for l in open(ad / 'rows.jsonl')] if (ad / 'rows.jsonl').exists() else []
    if len(rows) != pre['n'] or any('error' in r for r in rows):
        save(tag, 'GATE.json', dict(tag=tag, arm=arm, status='ARM_INCOMPLETE', rows=len(rows))); raise Stop('arm incomplete: %d of %d rows' % (len(rows), pre['n']))
    gate17.pairs('b2', arm)
    pin = GD / ('PAIRS-%s-vs-b2.json' % arm); pout = GD / ('GATE-%s-vs-b2.json' % arm)
    r = run([sys.executable, '-B', GD / 'quality_gate.py', '--input', pin, '--output', pout])
    res = json.loads(pout.read_text())
    speed = {}
    if (ad / 'engine.log').exists():
        run([sys.executable, '-B', PRODLOG, ad / 'engine.log', '--json', ad / 'prodlog-summary.json'])
        for n in ('b2', arm):
            s = json.loads((GD / 'arms' / n / 'prodlog-summary.json').read_text()); s = s.get('summary', s)   # prodlog --json nests it
            speed[n] = dict(decode_tok_s=round(s['generated_tokens'] / s['decode_seconds'], 1), generated_tokens=s['generated_tokens'], requests=s['requests'])
    p = {n: dict(pass1=sum(x.get('pass1', False) for x in rs), pass2=sum(x.get('pass2', False) for x in rs))
         for n, rs in (('b2', [json.loads(l) for l in open(GD / 'arms/b2/rows.jsonl')]), (arm, rows))}
    doc = dict(tag=tag, arm=arm, quality_gate_rc=r.returncode, status=res.get('status'), inference=res.get('inference'), passes=p, speed=speed,
               files=[str(pa), str(pin), str(pout)])
    log('gate', doc['status'], json.dumps(p), json.dumps(speed)); return save(tag, 'GATE.json' if not extra_env else 'GATE-%s.json' % arm, doc)


# ---------------------------------------------------------------- report / switch
def report(tag):
    prep, klr, gt = load(tag, 'PREPARE.json'), load(tag, 'KL.json'), load(tag, 'GATE.json')
    out = dict(tag=tag, prepare=prep and {k: prep.get(k) for k in ('status', 'tree', 'tag_commit', 'engine_version', 'engine_sha256', 'build_s', 'flags_not_in_help', 'stop')},
               kl=klr and {k: klr.get(k) for k in ('verdict', 'numerics_identical_to_v0217', 'compare', 'agent_vs_exact', 'stop')},
               gate=gt and {k: gt.get(k) for k in ('status', 'passes', 'speed', 'inference', 'stop')})
    ok = bool(prep and prep.get('status') == 'READY' and klr and klr.get('verdict') == 'PROCEED' and gt and gt.get('status') == 'NONINFERIORITY_ESTABLISHED')
    out['recommendation'] = 'SWITCH_CANDIDATE (decide with the speed numbers and release notes; then: upgrade_gate.py switch %s --yes)' % tag if ok else 'KEEP_CURRENT'
    save(tag, 'REPORT.json', out); print(json.dumps(out, indent=1)); return out


def switch(tag, yes=False, force=False):
    prep, gt = load(tag, 'PREPARE.json'), load(tag, 'GATE.json')
    if not prep or prep.get('status') != 'READY': raise Stop('run prepare first')
    if not force and (not gt or gt.get('status') != 'NONINFERIORITY_ESTABLISHED'): raise Stop('gate not established (use --force to override)')
    if not yes: raise Stop('switch changes production; pass --yes')
    tree = Path(prep['tree']); cur = cur_tree()
    if cur == tree: log('production already runs', tree); return
    bak = PROD_RUN.with_name(PROD_RUN.name + '.pre-%s-%s' % (tag, time.strftime('%Y%m%d%H%M%S')))
    shutil.copy2(PROD_RUN, bak)
    PROD_RUN.write_text('#!/bin/sh\n# %s: production switched to Strata %s, tree %s (upgrade_gate.py switch).\n'
                        '# The systemd unit still names this file; this script only hands over.\n# Rollback: cp %s %s && sudo -n /usr/bin/systemctl restart %s\nexec %s/run-iq3_xxs.sh\n'
                        % (time.strftime('%Y-%m-%d'), tag, tree, bak, PROD_RUN, UNIT, tree))
    systemctl('restart')
    if health(PROD_PORT, 600):
        log('production healthy on', tree, '| rollback file', bak); save(tag, 'SWITCH.json', dict(tree=str(tree), from_tree=str(cur), backup=str(bak), at=time.strftime('%Y-%m-%d %H:%M:%S'), ok=True)); return
    log('health failed: rolling back to', cur); shutil.copy2(bak, PROD_RUN); systemctl('restart')
    save(tag, 'SWITCH.json', dict(tree=str(tree), from_tree=str(cur), backup=str(bak), ok=False, rolled_back=health(PROD_PORT, 600)))
    raise Stop('new tree did not become healthy; production rolled back to %s' % cur)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['prepare', 'kl', 'gate', 'report', 'all', 'switch']); ap.add_argument('tag')
    ap.add_argument('--tree'); ap.add_argument('-j', type=int, default=8); ap.add_argument('--repeat', action='store_true')
    ap.add_argument('--force', action='store_true'); ap.add_argument('--limit', type=int); ap.add_argument('--yes', action='store_true')
    ap.add_argument('--env', action='append', default=[], help='extra engine env for the gate arm, K=V (repeatable; names the arm)')
    a = ap.parse_args()
    if not re.fullmatch(r'v\d+\.\d+\.\d+[-.\w]*', a.tag): raise SystemExit('tag looks wrong: %r' % a.tag)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))     # turn SIGTERM into SystemExit so finally blocks restore production
    os.umask(0o022); UG.mkdir(parents=True, exist_ok=True)
    lock = open(UG / '.lock', 'w')
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: raise SystemExit('another upgrade_gate.py is running')
    phase = {'prepare': 'PREPARE.json', 'kl': 'KL.json', 'gate': 'GATE.json'}
    cur = a.cmd
    try:
        if a.cmd == 'prepare': prepare(a.tag, a.tree, a.j)
        elif a.cmd == 'kl': kl(a.tag, a.repeat)
        elif a.cmd == 'gate': gate(a.tag, a.force, a.limit, dict(x.split('=', 1) for x in a.env))
        elif a.cmd == 'report': report(a.tag)
        elif a.cmd == 'switch': switch(a.tag, a.yes, a.force)
        elif a.cmd == 'all':
            cur = 'prepare'; prepare(a.tag, a.tree, a.j)
            cur = 'kl'; v = kl(a.tag, a.repeat)['verdict']
            if v == 'PROCEED': cur = 'gate'; gate(a.tag)
            report(a.tag)
    except Stop as e:
        log('STOP', cur, e)
        if cur in phase:
            d = load(a.tag, phase[cur]) or {}; d.update(stop=str(e), status=d.get('status') if d.get('status') not in (None, 'RUNNING') else 'STOPPED'); save(a.tag, phase[cur], d)
        if a.cmd == 'all': report(a.tag)
        sys.exit(2)


if __name__ == '__main__':
    main()

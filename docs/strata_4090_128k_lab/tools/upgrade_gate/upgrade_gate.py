"""One-command upgrade gate for a new Strata release on the 4090 (prepared 2026-11-21, CodexGame lab).

    upgrade_gate.py prepare TAG [--tree DIR] [-j N]  fetch the tag, export engine/terminal, apply the PT0/#1536 patch, build
                    [--label L --patch P --target T] a probe build: P (repeatable) applied after PT0, T (repeatable) built
                                                     beside the engine, results under L (tree /home/hhtele/strata-L)
                                                     (CUDA 12.3, sm_89), assemble a tree; production keeps running
    upgrade_gate.py kl TAG [--repeat]                teacher-forced KL against the stored v0.2.17 runs (stops production ~10 min)
    upgrade_gate.py gate TAG [--force] [--limit N]   one task-gate arm against the stored b2 arm (stops production ~2 h);
                                                     --limit N is a wiring smoke test in TAG/smoke, no decision
    upgrade_gate.py probe LABEL [--limit N]          an arm of the production tree itself with other --env/--arg, against the
                                                     stored b2 arm (no new release, no KL phase); results in LABEL/;
                                                     --baseline ts0 pairs a full arm with the stored exact-routing arm instead
      gate and probe take --env K=V and --arg FLAG[=VALUE] (repeatable): extra engine env, extra or replaced engine CLI args,
      and --sampling KEY=VALUE: the run config's sampling block (the server's defaults for fields a request leaves out)
    upgrade_gate.py replay LABEL --build | --freeze | --run NAME [--rerun] | --eval
                                                     fixed-history replay of a long Pi-shaped session on the production tree,
                                                     runs and rules from LABEL/PREREG.json (stops production per run)
    upgrade_gate.py approx LABEL                     stage 1 of an approximate-routing probe (LABEL/PREREG.json, verdict_kind
                                                     approx): teacher-forced KL of the production tree under each preregistered
                                                     env, screened against exact routing (one production stop, ~2 min a run);
                                                     its replay runs and --eval go through replay, its gate arms through
                                                     probe LABEL --baseline ts0 --env ...
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
MONITOR_SAMPLES = Path('/data/strata-data/prod-observe/monitor/data/samples')   # tools/monitor: co-tenant CPU during a run


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
def prepare(tag, tree=None, jobs=8, label=None, patches=(), targets=()):
    label = label or tag
    W = wdir(label); W.mkdir(parents=True, exist_ok=True)
    tree = Path(tree) if tree else Path('/home/hhtele/strata-' + label.lstrip('v'))
    done = load(label, 'PREPARE.json')
    if done and done.get('status') == 'READY' and Path(done['tree']).exists():
        log('prepare: already READY at', done['tree']); return done
    if tree.exists(): raise Stop('tree %s exists and has no READY record; move it away by hand' % tree)
    cur = cur_tree(); doc = dict(tag=tag, label=label, tree=str(tree), from_tree=str(cur), started=time.strftime('%Y-%m-%d %H:%M:%S'), status='RUNNING')
    try:
        return _prepare(tag, tree, jobs, W, cur, doc, label, [Path(p).resolve() for p in patches], list(targets))
    except Stop as e:
        save(label, 'PREPARE.json', dict(doc, status='STOPPED', stop=str(e))); raise


def _prepare(tag, tree, jobs, W, cur, doc, label, patches, targets):
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
    if r.returncode: save(label, 'patch-dry-run.txt.json', dict(out=r.stdout + r.stderr)); raise Stop('PATCH_CONFLICT: the PT0/#1536 patch needs a hand port:\n' + r.stdout[-1500:])
    r = run(['patch', '-p1', '-F0', '-N', '--batch', '-d', src, '-i', PATCH], check=True)
    doc['patch_output'] = r.stdout.strip().splitlines()
    regen = ''.join(run(['diff', '-uNp', '--label', 'a/' + f, '--label', 'b/' + f, orig / f, src / f]).stdout for f in files)
    (W / ('pt0-reply-reuse.%s.patch' % tag)).write_text(regen)
    doc['patched_files'] = {f: sha(src / f) for f in files}
    # a probe build's own patches (--patch): after PT0, zero fuzz, in the order given
    doc['extra_patches'] = []
    for P in patches:
        if not P.exists(): raise Stop('missing %s' % P)
        pf = re.findall(r'^\+\+\+ b/(\S+)', P.read_text(), re.M)
        r = run(['patch', '-p1', '-F0', '-N', '--batch', '--dry-run', '-d', src, '-i', P])
        if r.returncode: raise Stop('PATCH_CONFLICT: %s does not apply to %s + PT0 with zero fuzz:\n%s' % (P, tag, (r.stdout + r.stderr)[-1500:]))
        run(['patch', '-p1', '-F0', '-N', '--batch', '-d', src, '-i', P], check=True)
        doc['extra_patches'].append(dict(patch=str(P), sha256=sha(P), files={f: sha(src / f) for f in pf}))
        doc['patched_files'].update({f: sha(src / f) for f in pf})
        log('patch', P.name, len(pf), 'files')
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
    rc, g = run_guarded(['nice', '-n', '10', CMAKE, '--build', B, '--target', 'strata', *targets, '-j', jobs], W / 'build.log', 7200)
    if rc or g: raise Stop('build failed rc=%s %s (see build.log)' % (rc, g))
    eng = B / 'strata'
    doc['targets'] = {t: str(B / t) for t in targets}           # GPU tests: run with production stopped (approx LABEL, kl.tests)
    missing_t = [t for t in targets if not (B / t).exists()]
    if missing_t: raise Stop('built targets not found in %s: %s' % (B, missing_t))
    doc.update(build_s=round(time.monotonic() - t0), engine_sha256=sha(eng), engine_version=run([eng, '--version']).stdout.strip())
    log('engine', doc['engine_version'], doc['engine_sha256'][:16], 'in %d s' % doc['build_s'])
    # tree: everything except terminal/ and engine comes from the current production tree, paths rewritten
    tree.mkdir(parents=True)
    shutil.copytree(src / 'terminal', tree / 'terminal', symlinks=True, ignore=shutil.ignore_patterns('__pycache__'))
    (tree / 'engine').mkdir(); shutil.copy2(eng, tree / 'engine/strata')
    shutil.copytree(cur / 'python', tree / 'python', symlinks=True)
    shutil.copy2(PATCH, tree / PATCH.name)
    for P in patches: shutil.copy2(P, tree / P.name)
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
    if doc['extra_patches']: ident.update(label=label, extra_patches=[dict(patch=Path(x['patch']).name, sha256=x['sha256']) for x in doc['extra_patches']])
    (tree / 'IDENTITY.json').write_text(json.dumps(ident, indent=1) + '\n')
    doc.update(status='READY', finished=time.strftime('%Y-%m-%d %H:%M:%S'))
    if doc['flags_not_in_help']: log('WARN flags not in --help (check before the KL phase):', doc['flags_not_in_help'])
    log('prepare READY', tree); return save(label, 'PREPARE.json', doc)


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


# ---------------------------------------------------------------- arms: extra engine args, per-window figures
LOCKED_ARGS = {'--expert-profile-save', '--port', '--serve'}     # the gate driver sets these, or they break the arm's isolation
FORBIDDEN_ENV = {'STRATA_STAGE_PIN', 'STRATA_ROUTE_RESIDENT'}    # lab rule: never enabled
BASE_ARM = 'b2'                                                 # the stored production arm; probe arms are named after it
BUCKETS = (('<4K', 0, 4096), ('4K-32K', 4096, 32768), ('32K-64K', 32768, 65536), ('>=64K', 65536, 1 << 30))   # as prodlog.py
DT_FIELDS = dict(T=r'avg T ([\d.]+)', tok_win=r'([\d.]+) tokens/window', ms_win=r'([\d.]+) ms/window', adapt_wait=r'adapt wait ([\d.]+)',
                 reach=r'GPU-reach wait ([\d.]+)', cpu_ms=r' CPU ([\d.]+)\]', draft=r'draft ([\d.]+)', adapt_join=r'adapt join ([\d.]+)',
                 cpu_entries=r'CPU experts [\d.]+ \(([\d.]+) entries\)', swaps=r'([\d.]+) swaps/window')


def arm_env(extra):
    """An arm's engine env: B2's tail skip unless the arm sets its own, plus the arm's extra env; never a forbidden one."""
    env = dict(STRATA_ROUTE_TAIL_SKIP=TAIL_SKIP); env.update({k: str(v) for k, v in (extra or {}).items()})
    bad = FORBIDDEN_ENV & set(env)
    if bad: raise Stop('%s are never enabled in this lab' % sorted(bad))
    return env


def parse_arg_specs(specs):
    """--arg NAME[=VALUE], NAME with or without its leading dashes -> [(flag, value or None)]."""
    out = []
    for s in specs or []:
        name, eq, val = s.partition('=')
        flag = '--' + name.lstrip('-')
        if not re.fullmatch(r'--[a-z0-9][-a-z0-9]*', flag) or (eq and not val): raise Stop('bad --arg %r' % s)
        if flag in LOCKED_ARGS: raise Stop('--arg %s is not allowed: the gate driver sets it' % flag)
        if eq and val.startswith('/') and not Path(val).exists(): raise Stop('--arg %s names a missing file: %s' % (flag, val))
        out.append((flag, val if eq else None))
    return out


def apply_arg_specs(args, specs):
    """A copy of the engine args with each spec set: a value flag already there gets the new value, a new flag is appended."""
    a = list(args)
    for flag, val in specs:
        if flag not in a:
            a += [flag] + ([] if val is None else [val]); continue
        i = a.index(flag)
        if val is None: raise Stop('%s is already in the config' % flag)
        if i + 1 >= len(a) or a[i + 1].startswith('--'): raise Stop('%s is a bare flag in the config; it takes no value' % flag)
        a[i + 1] = val
    return a


SAMPLING_KEYS = {'temperature': float, 'top_p': float, 'top_k': int, 'min_p': float, 'presence_penalty': float,
                 'repetition_penalty': float, 'frequency_penalty': float, 'penalty_last_n': int}


def parse_sampling(specs):
    """--sampling KEY=VALUE -> {key: number}: the run config's `sampling` block, the server's defaults for the fields a
    request leaves out (gate17 and the replay send none, as Pi's model card values equal the server's card)."""
    out = {}
    for s in specs or []:
        k, eq, v = s.partition('=')
        if k not in SAMPLING_KEYS or not eq: raise Stop('bad --sampling %r (keys: %s)' % (s, sorted(SAMPLING_KEYS)))
        try: out[k] = SAMPLING_KEYS[k](v)
        except ValueError: raise Stop('bad --sampling value %r' % s)
        if out[k] < 0 or (k in ('top_p', 'min_p') and out[k] > 1): raise Stop('--sampling %s out of range' % s)
    return out


def sampling_suffix(sampling):
    return ''.join('-' + re.sub(r'[^0-9A-Za-z_]', '', k.replace('_', '') + str(v)) for k, v in sorted((sampling or {}).items()))


def arm_suffix(extra_env, specs):
    s = ''.join('-%s%s' % (k.replace('STRATA_', '').lower(), v) for k, v in sorted(extra_env.items()))   # unchanged naming for --env
    for flag, val in specs:
        v = '' if val is None else Path(val).stem if '/' in val else val
        s += '-' + re.sub(r'[^0-9A-Za-z_]', '', flag.replace('-', '') + v)
    return s


class _ArmTree(type(Path())):
    """gate17.N for an arm with --arg: every path is the tree's own except the run config, which is the arm's rewritten
    copy.  gate17.py is frozen (its sha is in the prereg), so its start_server cannot take the arguments itself."""
    config = None
    def __truediv__(self, key):
        if key == 'strata-iq3_xxs.json' and self.config is not None: return self.config
        return Path(str(self)) / key


def engine_requests(log_path):
    """The requests of a serve engine log in order (prompt and generated tokens, decode ms, drafts) with the decode-timing
    lines printed before each one's summary (same request, see prodlog.py); and the adaptive-overlap wait in all, in ms."""
    reqs, pend, waited, ep = [], [], 0.0, 0.0
    with open(log_path, errors='replace') as f:
        lines = f.readlines()
    for l in lines:
        if 'engine started:' in l: waited += ep; ep = 0.0
        m = re.search(r'a layer waited ([\d.]+) ms in all so far', l)
        if m: ep = float(m.group(1))             # cumulative within one engine run
        if 'strata decode timing:' in l:
            w = re.search(r'(\d+) windows', l)
            if w:
                t = dict(windows=int(w.group(1)))
                for k, rx in DT_FIELDS.items():
                    m = re.search(rx, l); t[k] = float(m.group(1)) if m else None
                pend.append(t)
            continue
        m = re.search(r'strata serve: prompt (\d+) tokens = .*?, (\d+) generated in (\d+) ms', l)
        if m:
            d = re.search(r'drafts accepted (\d+) of (\d+)', l)
            reqs.append(dict(prompt=int(m.group(1)), generated=int(m.group(2)), gen_ms=int(m.group(3)),
                             acc=int(d.group(1)) if d else 0, prop=int(d.group(2)) if d else 0, timing=pend)); pend = []
    return reqs, waited + ep


def task_requests(reqs, rows, budget):
    """The engine requests the given task rows made, from the start of the log: one per attempt, plus the continuation the
    server sends when a request stops at exactly the thinking budget.  Returns (requests, attempts whose tokens do not add up)."""
    i = bad = 0
    for r in rows:
        for at in r.get('attempts', []):
            s = 0
            while i < len(reqs):
                s += reqs[i]['generated']; i += 1
                if reqs[i - 1]['generated'] != budget: break
            c = at.get('completion_tokens')
            if c is None or not 0 <= c - s <= 64: bad += 1      # the server adds a few tokens closing the thinking (18 seen)
    return reqs[:i], bad


def window_stats(reqs):
    """Decode figures weighted by windows, in all and by prompt size."""
    def agg(rs):
        ts = [t for r in rs for t in r['timing']]
        out = dict(requests=len(rs), windows=sum(t['windows'] for t in ts))
        for k in DT_FIELDS:
            xs = [(t['windows'], t[k]) for t in ts if t[k] is not None]; n = sum(x[0] for x in xs)
            out[k] = round(sum(a * b for a, b in xs) / n, 3) if n else None
        g, ms, p = sum(r['generated'] for r in rs), sum(r['gen_ms'] for r in rs), sum(r['prop'] for r in rs)
        out.update(generated=g, decode_tok_s=round(1000 * g / ms, 1) if ms else None, accept=round(sum(r['acc'] for r in rs) / p, 3) if p else None)
        return out
    return dict(all=agg(reqs), **{b: agg([r for r in reqs if lo <= r['prompt'] < hi]) for b, lo, hi in BUCKETS})


def e2e(rs):    # end-to-end completion tok/s over the same first tasks (tracks the full-arm decode ratio within ~1.5%)
    t = sum(a['completion_tokens'] or 0 for r in rs for a in r.get('attempts', [])); w = sum(a['wall_s'] for r in rs for a in r.get('attempts', []))
    return dict(tok_s=round(t / w, 1) if w else None, tokens=t, wall_s=round(w, 1))


def same_task_figures(S, ids, budget):
    """Same-task end-to-end speed and per-window decode figures of every arm that ran these tasks: the smoke arms in S
    (this one and those beside it) and the stored gate arms, whose logs are cut to the requests of these tasks."""
    speed, win = {}, {}
    for pre, base in (('smoke:', S / 'arms'), ('', GD / 'arms')):
        for d in sorted(p for p in base.iterdir() if (p / 'rows.jsonl').exists()):
            rows = [json.loads(l) for l in open(d / 'rows.jsonl')]; by = {r['task_id']: r for r in rows}
            if not all(t in by for t in ids): continue
            speed[pre + d.name] = e2e([by[t] for t in ids])
            if [r['task_id'] for r in rows[:len(ids)]] != ids or not (d / 'engine.log').exists(): continue
            reqs, waited = engine_requests(d / 'engine.log')
            mine, bad = task_requests(reqs, rows[:len(ids)], budget)
            st = window_stats(mine); st['all'].update(unaligned_attempts=bad, whole_log=len(mine) == len(reqs))
            if len(mine) == len(reqs) and st['all']['windows']: st['all']['overlap_wait_ms_per_window'] = round(waited / st['all']['windows'], 3)
            win[pre + d.name] = st
    return speed, win


# ---------------------------------------------------------------- gate / probe
def gate(tag, force=False, limit=None, extra_env=None, arg_specs=None, sampling=None):
    prep = load(tag, 'PREPARE.json'); klr = load(tag, 'KL.json')
    if not prep or prep.get('status') != 'READY': raise Stop('run prepare first')
    if not limit and not force and (not klr or klr.get('verdict') != 'PROCEED'): raise Stop('KL verdict is not PROCEED (use --force to override)')
    ident = dict(engine_sha256=prep['engine_sha256'], patched_files=prep['patched_files'], config_sha256=prep['config_sha256'],
                 kl_verdict=(klr or {}).get('verdict'))
    return run_arm(tag, Path(prep['tree']), arm_name(tag), ident, force, limit, extra_env, arg_specs, sampling)


def probe(label, force=False, limit=None, extra_env=None, arg_specs=None, sampling=None, baseline=BASE_ARM, tree_label=None):
    """An arm of the production tree itself with other engine env or CLI args (no new release), paired with the stored b2
    arm, or with the stored exact-routing ts0 arm (baseline='ts0', for routing approximations): a smoke with --limit, else a
    full task-gate arm.  No KL phase here: quant_quality's yardstick pins the expert placement (--expert-cache 1,
    --adapt-every 100000), so it cannot see placement or adaptive-tier changes; other changes need their own numerical
    check first (routing env: approx LABEL).  tree_label: the tree `prepare --label` built (a probe build) instead of
    production; its arms are named after that label."""
    tree, cur = run_tree(tree_label, force)
    if not limit and not extra_env and not arg_specs and not sampling and not tree_label: raise Stop('a full arm without changes would be b2 again')
    klr = load(label, 'KL.json') or {}; env = arm_env(extra_env)
    hit = next((n for n, r in (klr.get('runs') or {}).items() if r.get('env') == env and klr.get('tree_label') == tree_label), None)
    ident = dict(engine_sha256=sha(cur['exe']), patched_files=load(tree_label, 'PREPARE.json')['patched_files'] if tree_label else None,
                 config_sha256=sha(tree / 'strata-iq3_xxs.json'),
                 kl_verdict='approx KL run %s: %s' % (hit, klr['runs'][hit]['screen']) if hit else 'NOT_RUN (probe)')
    return run_arm(label, tree, arm_name(tree_label) if tree_label else BASE_ARM, ident, True, limit, extra_env, arg_specs, sampling, baseline)


def cfg_norm(c):
    """A run config without what gate17 rewrites per arm."""
    c = json.loads(json.dumps(c)); a = c['args']; a[a.index('--expert-profile-save') + 1] = None
    for k in ('port', 'log', 'slot_save_path'): c.pop(k, None)
    return c


def b2_production_tree(force=False):
    """The production tree and its config, refusing unless both are what the stored b2 arm ran (--force overrides)."""
    tree = cur_tree(); b2c = json.loads((GD / 'arms' / BASE_ARM / 'config.json').read_text())
    if Path(b2c['cwd']) != tree: raise Stop('production runs %s, not the tree of the stored b2 arm (%s)' % (tree, b2c['cwd']))
    cur = json.loads((tree / 'strata-iq3_xxs.json').read_text())
    if cfg_norm(cur) != cfg_norm(b2c) and not force: raise Stop('the production config is not the one the stored b2 arm ran, so its arms would not pair with b2 (--force overrides)')
    return tree, cur


def run_tree(tree_label=None, force=False):
    """The tree a probe, replay or approx run uses: the production tree (b2_production_tree), or the tree `prepare --label
    tree_label` built (a probe build: the same release plus patches), refused unless it is READY, its engine is the one it
    built and its config is the production one with the tree's paths.  Returns (tree, its config)."""
    tree, cur = b2_production_tree(force)
    if not tree_label: return tree, cur
    prep = load(tree_label, 'PREPARE.json')
    if not prep or prep.get('status') != 'READY': raise Stop('%s has no READY prepare (upgrade_gate.py prepare ... --label %s)' % (tree_label, tree_label))
    t = Path(prep['tree']); c = json.loads((t / 'strata-iq3_xxs.json').read_text())
    if sha(c['exe']) != prep['engine_sha256']: raise Stop('the engine of %s is not the one prepare built' % t)
    if cfg_norm(c) != cfg_norm(json.loads(json.dumps(cur).replace(str(tree), str(t)))):
        raise Stop('the config of %s is not the production one with its paths' % t)
    return t, c


def arm_config(wtag, tree, arm, specs, gate17, sampling=None):
    """Point gate17 at tree; with CLI arg specs or sampling defaults, at a copy of its config with the args applied and
    the `sampling` block set (UG/wtag/configs/).  Returns (the config the arm runs, flags the engine --help does not list)."""
    run_cfg = tree / 'strata-iq3_xxs.json'; not_in_help = []
    if specs or sampling:
        cfg = json.loads(run_cfg.read_text()); cfg['args'] = apply_arg_specs(cfg['args'], specs)
        if sampling: cfg['sampling'] = dict(cfg.get('sampling') or {}, **sampling)
        run_cfg = wdir(wtag) / 'configs' / (arm + '.strata-iq3_xxs.json'); run_cfg.parent.mkdir(parents=True, exist_ok=True)
        run_cfg.write_text(json.dumps(cfg, indent=2) + '\n')
        if specs:
            h = run([cfg['exe'], '--help']); text = h.stdout + h.stderr          # the engine prints its usage on stderr
            not_in_help = [f for f, _ in specs if not re.search(re.escape(f) + r'(?![\w-])', text)]
            if not_in_help: log('WARN --arg flags not in the engine --help (it may still parse them; check the arm log):', not_in_help)
        nt = _ArmTree(tree); nt.config = run_cfg; gate17.N = nt
    else:
        gate17.N = tree
    return run_cfg, not_in_help


def loop_signs(server_stdout, finishes):
    """Degenerate-output signs of a run: replies ended by length, and the server's repeated-token / repeated-thinking notices."""
    rep = 0
    if Path(server_stdout).exists():
        with open(server_stdout, errors='replace') as f:
            rep = sum(1 for l in f if re.search(r'repeated one token|repeated reasoning|thinking repeated', l))
    return dict(finish_length=sum(1 for x in finishes if x == 'length'), repeat_notices=rep)


def run_arm(wtag, tree, base, ident, force=False, limit=None, extra_env=None, arg_specs=None, sampling=None, baseline=BASE_ARM):
    """One task-gate arm of tree (a smoke with --limit) with extra engine env, CLI args and sampling defaults; results under
    UG/wtag.  A full arm pairs with the stored arm `baseline`: b2, or ts0 (exact routing)."""
    extra_env = dict(extra_env or {}); env = arm_env(extra_env)     # an arm's own STRATA_ROUTE_TAIL_SKIP wins over B2's
    specs = parse_arg_specs(arg_specs)
    pre = json.loads((GD / 'PREREG.json').read_text())
    sampling = dict(sampling or {})
    suffix = arm_suffix(extra_env, specs) + sampling_suffix(sampling); arm = base + suffix if suffix or base != BASE_ARM else BASE_ARM + '-control'
    sys.path.insert(0, str(GD)); import gate17
    args_doc = [[f, v] for f, v in specs]
    run_cfg, not_in_help = arm_config(wtag, tree, arm, specs, gate17, sampling)
    if limit:                       # smoke: a private copy of the prereg, its own arm dir, no pairs/decision
        S = wdir(wtag) / 'smoke'; shutil.rmtree(S / 'arms' / arm, ignore_errors=True); S.mkdir(parents=True, exist_ok=True); shutil.copy2(GD / 'PREREG.json', S / 'PREREG.json'); gate17.GD = S
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
        b2 = {json.loads(l)['task_id']: json.loads(l) for l in open(GD / 'arms' / BASE_ARM / 'rows.jsonl')}
        ids = [r['task_id'] for r in rows]
        speed, win = same_task_figures(S, ids, gate17.THINK_BUDGET)
        doc = dict(tag=wtag, limit=limit, env=env, args=args_doc, sampling=sampling, flags_not_in_help=not_in_help, config=str(run_cfg), config_sha256=sha(run_cfg),
                   loop_signs=loop_signs(S / 'arms' / arm / 'server-stdout.txt', [a.get('finish') for r in rows for a in r.get('attempts', [])]),
                   arm_config_sampling=json.loads((S / 'arms' / arm / 'config.json').read_text()).get('sampling'),
                   engine_sha256=ident['engine_sha256'], arm=arm, speed_same_tasks=speed, per_window_same_tasks=win,
                   passes=dict(pass1=sum(bool(r.get('pass1')) for r in rows), pass2=sum(bool(r.get('pass2')) for r in rows), errors=sum('error' in r for r in rows)),
                   rows=[dict(task_id=r['task_id'], error=r.get('error'), pass1=r.get('pass1'), pass2=r.get('pass2'),
                   b2_pass1=b2[r['task_id']].get('pass1'), b2_pass2=b2[r['task_id']].get('pass2')) for r in rows])
        log('smoke', arm, json.dumps(speed)); return save(wtag, 'SMOKE-%s.json' % arm, doc)
    # addendum preregistration: written before the arm runs, refuses to change afterwards
    vs = '' if baseline == BASE_ARM else '-vs-' + baseline        # pairing with b2 keeps the original file names
    pa = GD / ('PREREG-%s%s.json' % (arm, vs))
    add = dict(tag=wtag, tree=str(tree), engine_sha256=ident['engine_sha256'], patched_files=ident['patched_files'],
               config_sha256=sha(run_cfg) if specs or sampling else ident['config_sha256'],
               base_prereg_sha256=sha(GD / 'PREREG.json'), driver_sha256=sha(GD / 'gate17.py'), baseline='%s (stored v0.2.17 arm, not re-run)' % baseline,
               baseline_rows_sha256=sha(GD / 'arms' / baseline / 'rows.jsonl'), candidate=arm, env=env, margin=pre['margin'],
               kl_verdict=ident['kl_verdict'], forced=bool(force),
               note='same task ids, seeds (1000+index), prompts, grader image and driver as PREREG.json; the two original arms also ran one '
                    'after the other, so reusing the stored %s arm keeps the pairing by task and seed' % baseline)
    if specs: add['args'] = args_doc               # only then: older addenda have no such key
    if sampling: add['sampling'] = sampling
    if pa.exists():
        old = json.loads(pa.read_text()); diff = [k for k in add if k not in ('forced', 'kl_verdict') and old.get(k) != add[k]]
        if diff: raise Stop('addendum prereg exists with different %s; refusing' % diff)
    else:
        pa.write_text(json.dumps(dict(add, created=time.strftime('%Y-%m-%d %H:%M:%S')), indent=1) + '\n')
    ad = GD / 'arms' / arm
    gname = 'GATE.json' if arm == base else 'GATE-%s%s.json' % (arm, vs)
    have = [json.loads(l) for l in open(ad / 'rows.jsonl')] if (ad / 'rows.jsonl').exists() else []
    if len(have) == pre['n'] and not any('error' in r for r in have):
        log('arm %s already complete (%d rows): deciding only, production untouched' % (arm, len(have)))
    else:
        with production_stopped():
            gate17.arm(arm, env)
    rows = [json.loads(l) for l in open(ad / 'rows.jsonl')] if (ad / 'rows.jsonl').exists() else []
    if len(rows) != pre['n'] or any('error' in r for r in rows):
        save(wtag, gname, dict(tag=wtag, arm=arm, status='ARM_INCOMPLETE', rows=len(rows))); raise Stop('arm incomplete: %d of %d rows' % (len(rows), pre['n']))
    gate17.pairs(baseline, arm)
    pin = GD / ('PAIRS-%s-vs-%s.json' % (arm, baseline)); pout = GD / ('GATE-%s-vs-%s.json' % (arm, baseline))
    r = run([sys.executable, '-B', GD / 'quality_gate.py', '--input', pin, '--output', pout])
    res = json.loads(pout.read_text())
    speed = {}
    if (ad / 'engine.log').exists():
        run([sys.executable, '-B', PRODLOG, ad / 'engine.log', '--json', ad / 'prodlog-summary.json'])
        for n in dict.fromkeys((BASE_ARM, baseline, arm)):
            f = GD / 'arms' / n / 'prodlog-summary.json'
            if not f.exists(): continue
            s = json.loads(f.read_text()); s = s.get('summary', s)   # prodlog --json nests it
            speed[n] = dict(decode_tok_s=round(s['generated_tokens'] / s['decode_seconds'], 1), generated_tokens=s['generated_tokens'], requests=s['requests'])
    p = {n: dict(pass1=sum(x.get('pass1', False) for x in rs), pass2=sum(x.get('pass2', False) for x in rs))
         for n, rs in [(b, [json.loads(l) for l in open(GD / 'arms' / b / 'rows.jsonl')]) for b in dict.fromkeys((BASE_ARM, baseline))] + [(arm, rows)]}
    doc = dict(tag=wtag, arm=arm, baseline=baseline, quality_gate_rc=r.returncode, status=res.get('status'), inference=res.get('inference'), passes=p,
               speed=speed, loop_signs=loop_signs(ad / 'server-stdout.txt', [a.get('finish') for x in rows for a in x.get('attempts', [])]),
               files=[str(pa), str(pin), str(pout)])
    log('gate', doc['status'], json.dumps(p), json.dumps(speed)); return save(wtag, gname, doc)


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


# ---------------------------------------------------------------- long-context replay
# A fixed-history replay of a Pi-shaped tool-loop session (plans/B2_ADAPT_LONG_20261123.md): the two pisim sessions of
# 2026-11-20 stitched into one, one request before each assistant message carrying the recorded history (never the arm's
# own replies), so every run sends byte-identical prompts.  Runs and verdict rules come from LABEL/PREREG.json.
REPLAY_GE = 32768                   # primary: requests with prompt >= 32K


def pisim_tools(text):
    """TOOLS as pisim.py defines it, read without running the script."""
    import ast
    for n in ast.parse(text).body:
        if isinstance(n, ast.Assign) and any(getattr(t, 'id', None) == 'TOOLS' for t in n.targets):
            return ast.literal_eval(n.value)
    raise Stop('pisim.py defines no TOOLS')


def build_replay(a_msgs, b_msgs, tools, model, max_tokens, seed0):
    """Session A, then session B without its system message; a cut before every assistant message."""
    if not (a_msgs and b_msgs and a_msgs[0]['role'] == 'system' and b_msgs[0]['role'] == 'system'):
        raise Stop('both sessions must start with their system message')
    msgs = list(a_msgs) + list(b_msgs[1:])
    cuts = [k for k, m in enumerate(msgs) if m['role'] == 'assistant']
    return dict(model=model, tools=tools, max_tokens=max_tokens, seed0=seed0, messages=msgs, cuts=cuts)


def replay_bodies(doc):
    for i, k in enumerate(doc['cuts']):
        yield dict(model=doc['model'], messages=doc['messages'][:k], tools=doc['tools'], max_tokens=doc['max_tokens'],
                   stream=False, seed=doc['seed0'] + i)


def started_args(log_path):
    """The engine argv (without the binary) of the last 'engine started:' line of an engine log."""
    line = None
    with open(log_path, errors='replace') as f:
        for l in f:
            if 'engine started:' in l: line = l
    return shlex.split(line.split('engine started:', 1)[1])[1:] if line else None


def flags_ok(argv, specs, all_flags):
    """Every flag of this run's specs is on the engine command line with its value; the other compared flags are not."""
    if argv is None: return False
    for flag, val in specs:
        if flag not in argv or (val is not None and (argv.index(flag) + 1 >= len(argv) or argv[argv.index(flag) + 1] != val)): return False
    return all(f not in argv for f in set(all_flags) - {f for f, _ in specs})


def replay_verdict(runs, floor=0.04, noisy=0.05, text_tol=0.05):
    """The preregistered ABBA verdict.  runs: C0a, L1a, L1b, C0b -> dict(ms_win, tok_win, decode_tok_s, valid) over the
    requests with prompt >= 32K."""
    names = ('C0a', 'L1a', 'L1b', 'C0b')
    missing = [n for n in names if n not in runs]
    if missing: return dict(verdict='INCOMPLETE', missing=missing)
    bad = [n for n in names if not runs[n].get('valid')]
    if bad: return dict(verdict='INVALID', invalid=bad)
    mean = lambda k, *ns: sum(runs[n][k] for n in ns) / len(ns)
    c, l = mean('ms_win', 'C0a', 'C0b'), mean('ms_win', 'L1a', 'L1b')
    aa = abs(runs['C0a']['ms_win'] - runs['C0b']['ms_win']) / c
    bar = max(floor, 2 * aa)
    text = mean('tok_win', 'L1a', 'L1b') / mean('tok_win', 'C0a', 'C0b') - 1
    checks = dict(faster_by_bar=l <= c * (1 - bar),
                  both_l_below_both_c=max(runs['L1a']['ms_win'], runs['L1b']['ms_win']) < min(runs['C0a']['ms_win'], runs['C0b']['ms_win']),
                  decode_tok_s_higher=mean('decode_tok_s', 'L1a', 'L1b') > mean('decode_tok_s', 'C0a', 'C0b'),
                  tok_win_within=abs(text) <= text_tol)
    out = dict(c0_ms_win=round(c, 3), l1_ms_win=round(l, 3), change=round(l / c - 1, 4), aa=round(aa, 4), bar=round(bar, 4),
               tok_win_change=round(text, 4), checks=checks)
    if aa > noisy: out['verdict'] = 'NOISY'
    elif not checks['tok_win_within']: out['verdict'] = 'INCONCLUSIVE'
    else: out['verdict'] = 'PASS' if all(checks.values()) else 'NO_PASS'
    return out


def sampling_verdict(controls, env_ref, cands, smoke_ref, smokes, floor=0.05, env_tol=0.03):
    """The preregistered sampling verdict (plans/B2_SAMPLING_20261123.md).  controls: replay control runs, each
    dict(ms_win, decode_tok_s, finish_length, repeat_notices, valid), the last one fresh; env_ref: dict(ms_win,
    decode_tok_s) of the earlier controls; cands: name -> replay run dict like a control; smoke_ref: dict(decode_tok_s,
    e2e) of the stored b2 arm; smokes: name -> dict(decode_tok_s, e2e, finish_length, repeat_notices, errors, valid)."""
    fresh = controls[-1]
    drift = {k: round(fresh[k] / env_ref[k] - 1, 4) for k in ('ms_win', 'decode_tok_s')}
    if not fresh.get('valid'): return dict(verdict='INVALID', invalid=['control'])
    if any(abs(v) > env_tol for v in drift.values()): return dict(verdict='STOP_ENV', drift=drift)
    d = [c['decode_tok_s'] for c in controls]; cm = sum(d) / len(d)
    aa = (max(d) - min(d)) / cm; bar = max(floor, 2 * aa)
    lim = {k: max(c[k] for c in controls) + 1 for k in ('finish_length', 'repeat_notices')}
    out = dict(drift=drift, control_decode_tok_s=round(cm, 1), aa=round(aa, 4), bar=round(bar, 4), arms={})
    for n, c in cands.items():
        s = smokes.get(n)
        if not c.get('valid') or not s or not s.get('valid'): out['arms'][n] = dict(verdict='INVALID'); continue
        g, sg, se = c['decode_tok_s'] / cm - 1, s['decode_tok_s'] / smoke_ref['decode_tok_s'] - 1, s['e2e'] / smoke_ref['e2e'] - 1
        checks = dict(replay_gain_ge_bar=g >= bar, smoke_decode_not_slower=sg > 0, smoke_e2e_higher=se > 0,
                      replay_loops_ok=all(c[k] <= lim[k] for k in lim), smoke_loops_ok=s['finish_length'] <= 1 and s['repeat_notices'] <= 1 and not s['errors'])
        out['arms'][n] = dict(replay_gain=round(g, 4), smoke_decode_gain=round(sg, 4), smoke_e2e_gain=round(se, 4), checks=checks,
                              verdict='PASS' if all(checks.values()) else 'NO_PASS')
    passing = {n: a['replay_gain'] for n, a in out['arms'].items() if a['verdict'] == 'PASS'}
    if not passing: out['verdict'], out['stage2'] = 'NO_GAIN', None
    else:
        best = max(passing, key=passing.get)
        # the candidate closest to the card (the highest temperature) unless another one is faster by >= 3 points
        cons = max(passing, key=lambda n: cands[n]['temperature'])
        out['stage2'] = best if passing[best] - passing[cons] >= 0.03 else cons; out['verdict'] = 'STAGE2'
    return out


def replay_prereg(label):
    pre = load(label, 'PREREG.json')
    if not pre or 'workload' not in pre or 'runs' not in pre: raise Stop('%s has no replay preregistration' % wdir(label))
    return pre


def replay_build(label):
    """Build LABEL/REPLAY.json from the preregistered pisim sessions (their sha256 must match); never changes it once built."""
    pre = replay_prereg(label); src = pre['workload']['sources']
    for p, h in src.items():
        if sha(p) != h: raise Stop('%s changed since the preregistration' % p)
    pick = lambda end: next(Path(p) for p in src if p.endswith(end))
    doc = build_replay(json.loads(pick('session-A.json').read_text()), json.loads(pick('session-B.json').read_text()),
                       pisim_tools(pick('pisim.py').read_text()), 'openclaw/Qwen3.8-next', 16384, 20261123)
    text = json.dumps(doc, sort_keys=True) + '\n'
    out = wdir(label) / 'REPLAY.json'
    if out.exists() and out.read_text() != text: raise Stop('REPLAY.json exists and differs from a fresh build')
    if not out.exists(): out.write_text(text)
    info = dict(requests=len(doc['cuts']), messages=len(doc['messages']), sha256=sha(out),
                session_a_requests=sum(m['role'] == 'assistant' for m in json.loads(pick('session-A.json').read_text())))
    log('replay built', json.dumps(info)); return info


def replay_freeze(label):
    """ADDENDUM.json (read-only): the sha256 of this script and of REPLAY.json, fixed before the first run."""
    W = wdir(label); add = W / 'ADDENDUM.json'
    if add.exists(): raise Stop('ADDENDUM.json exists already')
    if not (W / 'REPLAY.json').exists(): raise Stop('build REPLAY.json first')
    doc = dict(label=label, frozen_at=time.strftime('%Y-%m-%d %H:%M:%S'), upgrade_gate_sha256=sha(Path(__file__).resolve()),
               replay_sha256=sha(W / 'REPLAY.json'), prereg_sha256=sha(W / 'PREREG.json'),
               requests=len(json.loads((W / 'REPLAY.json').read_text())['cuts']))
    add.write_text(json.dumps(doc, indent=1) + '\n'); os.chmod(add, 0o444); log('frozen', json.dumps(doc)); return doc


def replay_check_frozen(label):
    W = wdir(label); add = load(label, 'ADDENDUM.json')
    if not add: raise Stop('freeze the replay first (ADDENDUM.json)')
    if sha(Path(__file__).resolve()) != add['upgrade_gate_sha256']: raise Stop('upgrade_gate.py changed after the freeze')
    if sha(W / 'REPLAY.json') != add['replay_sha256'] or sha(W / 'PREREG.json') != add['prereg_sha256']: raise Stop('REPLAY.json or PREREG.json changed after the freeze')
    return add


def replay_run(label, name, force=False, rerun=False):
    """One preregistered run: a fresh engine of the production tree (production stopped) with that run's CLI args, the
    whole replay in order, then the engine's own figures over the requests with prompt >= 32K."""
    pre = replay_prereg(label); replay_check_frozen(label)
    spec = next((r for r in pre['runs'] if r['run'] == name), None)
    if not spec: raise Stop('run %r is not preregistered (%s)' % (name, [r['run'] for r in pre['runs']]))
    if pre.get('verdict_kind') == 'approx' and spec.get('kl_run'):
        klr = load(label, 'KL.json') or {}; st = ((klr.get('runs') or {}).get(spec['kl_run']) or {}).get('screen')
        if klr.get('verdict') != 'SCREENED' or st != 'PASS': raise Stop('run %s: KL screen of %s is %s (stage 1 %s)' % (name, spec['kl_run'], st, klr.get('verdict')))
    env = arm_env(spec.get('env'))
    all_flags = {f for r in pre['runs'] for f, _ in parse_arg_specs(r['args'])}
    specs = parse_arg_specs(spec['args']); arm = spec['arm']; sampling = parse_sampling(['%s=%s' % kv for kv in (spec.get('sampling') or {}).items()])
    tree, cur = run_tree(spec.get('tree_label'), force)
    sys.path.insert(0, str(GD)); import gate17
    run_cfg, not_in_help = arm_config(label, tree, arm, specs, gate17, sampling)
    W = wdir(label); ad = W / 'runs' / name
    if ad.exists():
        if not rerun: raise Stop('%s exists (a rerun keeps it as %s.failed1)' % (ad, name))
        kept = ad.with_name(name + '.failed1')
        if kept.exists(): raise Stop('one rerun at most: %s exists' % kept)
        ad.rename(kept); log('kept the failed run as', kept)
    ad.mkdir(parents=True)
    doc = json.loads((W / 'REPLAY.json').read_text()); bodies = list(replay_bodies(doc))
    rows = []; guard = []; err = None; t_run = [None, None]
    with production_stopped():
        p = gate17.start_server(ad, env); stop = threading.Event(); t_run[0] = time.time()
        def mon():
            while not stop.wait(5):
                s = snapshot()
                if s['avail_mib'] < GUARD_AVAIL_MIB or s['temp'] >= GUARD_TEMP:
                    guard.append(s); log('GUARD', s); stop.set(); os.killpg(p.pid, signal.SIGTERM)
        th = threading.Thread(target=mon, daemon=True); th.start()
        try:
            for i, body in enumerate(bodies):
                if stop.is_set(): err = 'guard'; break
                t0 = time.monotonic()
                try:
                    with urlopen(Request(gate17.URL + '/v1/chat/completions', json.dumps(body).encode(), {'Content-Type': 'application/json'}), timeout=1800) as f:
                        r = json.loads(f.read())
                    u = r.get('usage') or {}; ch = (r.get('choices') or [{}])[0]
                    row = dict(i=i, prompt_tokens=u.get('prompt_tokens'), completion_tokens=u.get('completion_tokens'),
                               finish=ch.get('finish_reason'), wall_s=round(time.monotonic() - t0, 2))
                except Exception as e:
                    row = dict(i=i, error='%s: %s' % (type(e).__name__, e), wall_s=round(time.monotonic() - t0, 2))
                rows.append(row)
                with open(ad / 'rows.jsonl', 'a') as f: f.write(json.dumps(row) + '\n')
                log(name, i, row.get('prompt_tokens'), row.get('completion_tokens'), row.get('finish'), row['wall_s'], row.get('error') or '')
                if 'error' in row: err = row['error']; break
        finally:
            t_run[1] = time.time(); stop.set(); gate17.stop_server(p); log('RUN_END', name, 'guard' if guard else err or '')
    reqs, waited = engine_requests(ad / 'engine.log')
    argv = started_args(ad / 'engine.log')
    aligned = len(reqs) == len(rows) == len(bodies) and all(r.get('prompt_tokens') is not None and abs(q['prompt'] - r['prompt_tokens']) <= 64 for q, r in zip(reqs, rows))
    ran = json.loads((ad / 'config.json').read_text()) if (ad / 'config.json').exists() else {}
    checks = dict(all_requests_ok=not err and len(rows) == len(bodies), engine_requests=len(reqs), aligned=aligned,
                  flags_ok=flags_ok(argv, specs, all_flags), sampling_ok=(ran.get('sampling') or {}) == sampling, no_guard=not guard,
                  env_ok=all(str((ran.get('env') or {}).get(k)) == v for k, v in env.items()))
    st = window_stats(reqs); ge = window_stats([q for q in reqs if q['prompt'] >= REPLAY_GE])['all']
    if st['all']['windows']: st['all']['overlap_wait_ms_per_window'] = round(waited / st['all']['windows'], 3)
    out = dict(label=label, run=name, arm=arm, tree=str(tree), args=[[f, v] for f, v in specs], sampling=sampling, env=env, t_start=t_run[0], t_end=t_run[1],
               flags_not_in_help=not_in_help, config=str(run_cfg),
               loop_signs=loop_signs(ad / 'server-stdout.txt', [r.get('finish') for r in rows]),
               config_sha256=sha(run_cfg), engine_sha256=sha(cur['exe']), started_args=argv, error=err, guard=guard,
               checks=checks, valid=all(v for k, v in checks.items() if k != 'engine_requests'), ge32k=ge, buckets=st,
               generated=sum(r.get('completion_tokens') or 0 for r in rows), wall_s=round(sum(r['wall_s'] for r in rows), 1))
    log('run', name, 'valid' if out['valid'] else 'INVALID', json.dumps(dict(checks=checks, ge32k=ge)))
    return save(label, 'RUN-%s.json' % name, out)


def replay_eval(label):
    pre = replay_prereg(label)
    if pre.get('verdict_kind') == 'sampling': return sampling_eval(label, pre)
    if pre.get('verdict_kind') == 'approx': return approx_eval(label, pre)
    runs = {}
    for r in pre['runs']:
        d = load(label, 'RUN-%s.json' % r['run'])
        if d: runs[r['run']] = dict(valid=d['valid'], **{k: d['ge32k'][k] for k in ('ms_win', 'tok_win', 'decode_tok_s')})
    v = replay_verdict(runs); v['runs'] = runs; log('verdict', json.dumps(v)); return save(label, 'VERDICT.json', v)


def sampling_eval(label, pre):
    def rr(lb, n):
        d = load(lb, 'RUN-%s.json' % n)
        if not d: raise Stop('missing %s/RUN-%s.json' % (lb, n))
        ls = d.get('loop_signs')
        if ls is None:              # runs made before loop_signs existed: from their rows and server output
            ad = wdir(lb) / 'runs' / n
            ls = loop_signs(ad / 'server-stdout.txt', [json.loads(l).get('finish') for l in open(ad / 'rows.jsonl')])
        return dict(valid=d['valid'], ms_win=d['ge32k']['ms_win'], decode_tok_s=d['ge32k']['decode_tok_s'], **ls)
    ref = pre['reuse_controls']; old = [rr(ref['label'], n) for n in ref['runs']]
    controls = old + [rr(label, pre['fresh_control'])]
    env_ref = {k: sum(c[k] for c in old) / len(old) for k in ('ms_win', 'decode_tok_s')}
    cands, smokes, smoke_ref = {}, {}, None
    for c in pre['candidates']:
        cands[c['run']] = dict(rr(label, c['run']), temperature=c['sampling']['temperature'])
        sd = load(label, 'SMOKE-%s.json' % c['arm'])
        if not sd: continue
        w = sd['per_window_same_tasks']; sp = sd['speed_same_tasks']
        smoke_ref = dict(decode_tok_s=w['b2']['all']['decode_tok_s'], e2e=sp['b2']['tok_s'])
        smokes[c['run']] = dict(decode_tok_s=w['smoke:' + c['arm']]['all']['decode_tok_s'], e2e=sp['smoke:' + c['arm']]['tok_s'],
                                errors=sd['passes']['errors'], valid=sd.get('arm_config_sampling') == c['sampling'], **sd['loop_signs'])
    if smoke_ref is None: raise Stop('no smoke results yet')
    v = sampling_verdict(controls, env_ref, cands, smoke_ref, smokes)
    v.update(inputs=dict(controls=controls, env_ref=env_ref, cands=cands, smoke_ref=smoke_ref, smokes=smokes))
    log('verdict', json.dumps(v)); return save(label, 'VERDICT.json', v)


# ---------------------------------------------------------------- approximate routing (plans/B2_APPROX_20261124.md)
KL_EXACT, KL_B2 = KD / 'runs/auto-ts0-a.tsv', KD / 'runs/auto-ts7.tsv'


def scoring_seconds(console):
    """Sum of quant_quality's per-segment scoring times ('code: 999 positions, 9.9 s'): its own speed, engine load excluded."""
    if not Path(console).exists(): return None
    xs = re.findall(r'^\w+: \d+ positions, ([\d.]+) s', Path(console).read_text(errors='replace'), re.M)
    return round(sum(float(x) for x in xs), 1) if xs else None


def kl_screen(cmp, spec):
    """The stage-1 verdict.  cmp: run -> dict(exact=quant_quality compare result against exact routing, b2=the same against
    the stored B2 run), each {'all': {kl, top1, ...}, 'agent': {...}, ...}.  The identity run must reproduce the stored B2
    run exactly (else INVALID); any other run passes when its KL against exact routing, all and agent segment, is within
    the preregistered bounds."""
    sc = spec['screen']; ident = spec.get('identity_run'); out = dict(thresholds=sc, runs={})
    for n, d in cmp.items():
        ex = d['exact']; ok = ex['all']['kl'] <= sc['kl_all_max'] and ex['agent']['kl'] <= sc['kl_agent_max']
        out['runs'][n] = dict(kl_all=ex['all']['kl'], top1=ex['all']['top1'], kl_agent=ex['agent']['kl'], kl_vs_b2=d['b2']['all']['kl'],
                              top1_vs_b2=d['b2']['all']['top1'], screen='IDENTITY' if n == ident else 'PASS' if ok else 'FAIL')
    if ident:
        d = cmp.get(ident); same = bool(d) and d['b2']['all']['kl'] == 0 and d['b2']['all']['top1'] == 1
        out['identity'] = dict(run=ident, identical_to_stored_b2=same)
        if not same: out['verdict'] = 'INVALID'; return out
    out['verdict'] = 'SCREENED'; return out


def approx_kl(label, force=False):
    """Stage 1: teacher-forced KL of the production tree under each preregistered env (LABEL/PREREG.json 'kl'), with one
    production stop for all runs not done yet; then the screen against the stored v0.2.17 runs (exact routing, B2)."""
    pre = load(label, 'PREREG.json')
    if not pre or pre.get('verdict_kind') != 'approx' or 'kl' not in pre: raise Stop('%s has no approx preregistration' % wdir(label))
    replay_check_frozen(label)
    tl = pre['kl'].get('tree_label'); tests = pre['kl'].get('tests') or []
    tree, cur = run_tree(tl, force)
    K = wdir(label) / 'kl'; K.mkdir(parents=True, exist_ok=True)
    PY = tree / 'python/bin/python3'; QQ = tree / 'terminal/tools/quant_quality.py'
    cfg = json.loads((tree / 'strata-iq3_xxs.json').read_text()); a = cfg['args']
    a[a.index('--expert-profile-save') + 1] = str(K / 'expert-profile-learned.bin')
    cfg.update(cwd=str(K), log=str(K / 'unused.log'), slot_save_path=str(K / 'slots'))
    (K / 'config.json').write_text(json.dumps(cfg, indent=1) + '\n')
    runs = pre['kl']['runs']; envs = {r['run']: arm_env(r['env']) for r in runs}      # a forbidden env stops here, production untouched
    reuse = pre['kl'].get('reuse') or {}
    for n, r in reuse.items():
        if sha(r['tsv']) != r['sha256']: raise Stop('reused KL run %s changed: %s' % (n, r['tsv']))
    todo = [r['run'] for r in runs if not (load(label, 'kl/%s.run.json' % r['run']) or {}).get('ok')]
    tests_due = bool(tests) and not (load(label, 'kl/tests.json') or {}).get('ok')
    if tests and not tl: raise Stop('kl.tests needs kl.tree_label (the build that has them)')
    if todo or tests_due:
        with production_stopped():
            if tests_due:           # the probe build's GPU tests (prepare --target), on the idle card before any KL run
                built = load(tl, 'PREPARE.json').get('targets') or {}; res = {}
                for t in tests:
                    if t not in built: raise Stop('test %s was not built by prepare --label %s --target' % (t, tl))
                    rc, g = run_guarded([built[t]], K / ('test-%s.txt' % t), 900, cwd=K, temp_guard=True)
                    res[t] = dict(rc=rc, guard=g, tail=(K / ('test-%s.txt' % t)).read_text(errors='replace').strip().splitlines()[-3:])
                    log('test', t, 'rc', rc, res[t]['tail'][-1:] if res[t]['tail'] else '')
                ok = all(not r['rc'] and not r['guard'] for r in res.values())
                save(label, 'kl/tests.json', dict(tests=res, ok=ok, engine_sha256=sha(cur['exe'])))
                if not ok: raise Stop('GPU tests failed: %s' % {k: v['rc'] for k, v in res.items()})
            for n in todo:
                out = K / (n + '.tsv')
                for p in K.glob(n + '.tsv*'): p.unlink()
                while snapshot()['temp'] > 50: time.sleep(5)
                t0 = time.monotonic(); log('KL run', n, json.dumps(envs[n]))
                rc, g = run_guarded([PY, '-B', QQ, 'run', '--config', K / 'config.json', '--out', out, '--ids', KD / 'ids.json',
                                     *[x for kv in sorted(envs[n].items()) for x in ('--env', '%s=%s' % kv)], '--gpu-experts', 'auto'],
                                    K / (n + '.console.txt'), 2400, cwd=K, temp_guard=True)
                save(label, 'kl/%s.run.json' % n, dict(run=n, env=envs[n], rc=rc, guard=g, wall_s=round(time.monotonic() - t0, 1),
                                                       ok=not rc and not g and out.exists()))
                if rc or g: raise Stop('KL run %s failed rc=%s %s' % (n, rc, g))
    paths = {r['run']: K / (r['run'] + '.tsv') for r in runs}
    for n, r in reuse.items():
        paths[n] = Path(r['tsv']); envs[n] = arm_env(r['env'])
    cmp = {n: {} for n in paths}
    for key, ref in (('exact', KL_EXACT), ('b2', KL_B2)):
        js = K / ('COMPARE-%s.json' % key)
        r = run([PY, '-B', QQ, 'compare', ref, *paths.values(), '--segments', '--json', js])
        if r.returncode or not js.exists(): raise Stop('quant_quality compare failed: %s' % r.stderr[-800:])
        res = json.loads(js.read_text())
        for n, p in paths.items(): cmp[n][key] = res[str(p)]
    console = lambda p: p.with_name(p.name[:-len('.tsv')] + '.console.txt')
    v = kl_screen(cmp, pre['kl'])
    for n, p in paths.items(): v['runs'][n].update(env=envs[n], scoring_s=scoring_seconds(console(p)))
    v['references'] = {k: dict(tsv=str(p), scoring_s=scoring_seconds(console(p))) for k, p in (('exact', KL_EXACT), ('b2', KL_B2))}
    v.update(engine_sha256=sha(cur['exe']), ids_sha256=sha(KD / 'ids.json'), config=str(K / 'config.json'), tree=str(tree), tree_label=tl)
    for n, x in v['runs'].items():
        log('KL %-8s all %.4f top1 %.3f agent %.4f | vs B2 %.4f | scoring %s s -> %s' % (n, x['kl_all'], x['top1'], x['kl_agent'], x['kl_vs_b2'], x['scoring_s'], x['screen']))
    log('KL screen', v['verdict']); return save(label, 'KL.json', v)


def cotenant_cpu(t0, t1, samples=None):
    """Mean CPU cores of the docker co-tenants while a run ran, from the production monitor's minute samples
    (tools/monitor); None when there are none for that time."""
    import gzip
    samples = MONITOR_SAMPLES if samples is None else Path(samples)
    if t0 is None or t1 is None: return None
    vals = []
    for day in sorted({time.strftime('%Y-%m-%d', time.localtime(t)) for t in (t0, t1)}):
        for p in (samples / (day + '.jsonl'), samples / (day + '.jsonl.gz')):
            if not p.exists(): continue
            with (gzip.open(p, 'rt', errors='replace') if p.suffix == '.gz' else open(p, errors='replace')) as f:
                for line in f:
                    try: s = json.loads(line)
                    except ValueError: continue
                    if t0 < s.get('ts', 0) <= t1 + 60:        # a sample covers the minute before it
                        v = [x['cpu'] for x in (s.get('docker') or {}).values() if isinstance(x.get('cpu'), (int, float))]
                        if v: vals.append(sum(v))
            break
    return round(sum(vals) / len(vals), 3) if vals else None


def approx_verdict(fresh, cands, kl, reused=None, floor=0.04, busy_cpu=1.0, close=0.03, max_gate=2):
    """The preregistered stage-2 verdict.  fresh: the bracketing control runs (name -> run); cands: the replay runs of the
    candidates whose KL screen passed; a run is dict(valid, ms_win, tok_win, decode_tok_s, finish_length, repeat_notices,
    cotenant_cpu) over the requests with prompt >= 32K; kl: candidate -> its stage-1 figures; reused: earlier controls
    (recorded drift only).  Stage 3 gets at most max_gate candidates: the fastest first, except that a candidate within
    `close` of the fastest with a lower KL against exact routing goes first."""
    runs = dict(fresh, **cands)
    bad = [n for n, r in runs.items() if not r.get('valid')]
    if bad: return dict(verdict='INVALID', invalid=bad)
    busy = [n for n, r in runs.items() if isinstance(r.get('cotenant_cpu'), (int, float)) and r['cotenant_cpu'] >= busy_cpu]
    if busy: return dict(verdict='CONTENDED', rerun=busy)
    mean = lambda k: sum(r[k] for r in fresh.values()) / len(fresh)
    cm = mean('decode_tok_s'); d = [r['decode_tok_s'] for r in fresh.values()]
    aa = (max(d) - min(d)) / cm; bar = max(floor, 2 * aa)
    lim = {k: max(r[k] for r in fresh.values()) + 1 for k in ('finish_length', 'repeat_notices')}
    out = dict(control_decode_tok_s=round(cm, 1), aa=round(aa, 4), bar=round(bar, 4), arms={})
    if reused: out['drift_vs_reused'] = round(cm / (sum(r['decode_tok_s'] for r in reused) / len(reused)) - 1, 4)
    for n, c in cands.items():
        g = c['decode_tok_s'] / cm - 1
        checks = dict(gain_ge_bar=g >= bar, loops_ok=all(c[k] <= lim[k] for k in lim))
        out['arms'][n] = dict(gain=round(g, 4), ms_win_change=round(c['ms_win'] / mean('ms_win') - 1, 4),
                              tok_win_change=round(c['tok_win'] / mean('tok_win') - 1, 4), kl_all=kl[n]['kl_all'], checks=checks,
                              verdict='PASS' if all(checks.values()) else 'NO_PASS')
    passing = {n: a['gain'] for n, a in out['arms'].items() if a['verdict'] == 'PASS'}
    if not passing:
        out.update(verdict='NO_GAIN', stage3=[]); return out
    order = sorted(passing, key=lambda n: -passing[n])
    first = min((n for n in order if passing[order[0]] - passing[n] < close), key=lambda n: kl[n]['kl_all'])
    out.update(verdict='STAGE3', stage3=([first] + [n for n in order if n != first])[:max_gate]); return out


def run_figures(lb, n):
    """A replay run's figures over the requests with prompt >= 32K, its loop signs and the co-tenants' CPU while it ran."""
    d = load(lb, 'RUN-%s.json' % n)
    if not d: raise Stop('missing %s/RUN-%s.json' % (wdir(lb), n))
    ls = d.get('loop_signs')
    if ls is None:              # runs made before loop_signs existed: from their rows and server output
        ad = wdir(lb) / 'runs' / n
        ls = loop_signs(ad / 'server-stdout.txt', [json.loads(l).get('finish') for l in open(ad / 'rows.jsonl')])
    return dict(valid=d['valid'], cotenant_cpu=cotenant_cpu(d.get('t_start'), d.get('t_end')),
                **{k: d['ge32k'][k] for k in ('ms_win', 'tok_win', 'decode_tok_s')}, **ls)


def approx_eval(label, pre):
    klr = load(label, 'KL.json')
    if not klr or klr.get('verdict') != 'SCREENED': raise Stop('stage 1 has no SCREENED verdict (upgrade_gate.py approx %s)' % label)
    fresh = {n: run_figures(label, n) for n in pre['controls']}
    cands, kl = {}, {}
    for c in pre['candidates']:
        k = klr['runs'].get(c['kl_run'])
        if k and k['screen'] == 'PASS': cands[c['run']] = run_figures(label, c['run']); kl[c['run']] = k
    ref = pre.get('reuse_controls')
    reused = [run_figures(ref['label'], n) for n in ref['runs']] if ref else None
    v = approx_verdict(fresh, cands, kl, reused)
    v.update(screened_out=[c['run'] for c in pre['candidates'] if c['run'] not in cands],
             inputs=dict(fresh=fresh, cands=cands, reused=reused, kl={n: {x: k.get(x) for x in ('kl_all', 'kl_agent', 'env')} for n, k in kl.items()}))
    log('verdict', json.dumps({k: x for k, x in v.items() if k != 'inputs'})); return save(label, 'VERDICT.json', v)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['prepare', 'kl', 'gate', 'probe', 'replay', 'approx', 'report', 'all', 'switch']); ap.add_argument('tag', help='release tag, or a run label for probe/replay/approx')
    ap.add_argument('--tree'); ap.add_argument('-j', type=int, default=8); ap.add_argument('--repeat', action='store_true')
    ap.add_argument('--force', action='store_true'); ap.add_argument('--limit', type=int); ap.add_argument('--yes', action='store_true')
    ap.add_argument('--env', action='append', default=[], help='extra engine env for the gate arm, K=V (repeatable; names the arm)')
    ap.add_argument('--arg', action='append', default=[], metavar='FLAG[=VALUE]',
                    help='engine CLI arg for the gate/probe arm, e.g. adapt-every=2: replaces the value of a flag the config has, else is appended (repeatable; names the arm)')
    ap.add_argument('--sampling', action='append', default=[], metavar='KEY=VALUE',
                    help='gate/probe: the run config\'s sampling block (server defaults for fields a request leaves out), e.g. temperature=0.6 (repeatable; names the arm)')
    ap.add_argument('--build', action='store_true', help='replay: build LABEL/REPLAY.json from the preregistered sessions')
    ap.add_argument('--freeze', action='store_true', help='replay: write the read-only ADDENDUM.json (sha256 of this script and REPLAY.json)')
    ap.add_argument('--run', metavar='NAME', help='replay: one preregistered run (its args come from LABEL/PREREG.json)')
    ap.add_argument('--rerun', action='store_true', help='replay --run: once, after an infrastructure failure; the failed run is kept')
    ap.add_argument('--eval', action='store_true', help='replay: the preregistered verdict over the runs so far (VERDICT.json)')
    ap.add_argument('--baseline', default=BASE_ARM, choices=(BASE_ARM, 'ts0'), help='probe: the stored arm a full arm pairs with (ts0: exact routing)')
    ap.add_argument('--label', help='prepare: a probe build\'s own label (work dir, tree /home/hhtele/strata-LABEL); the tag is still what is fetched')
    ap.add_argument('--patch', action='append', default=[], help='prepare --label: a patch applied after PT0 with zero fuzz (repeatable, in order)')
    ap.add_argument('--target', action='append', default=[], help='prepare --label: a build target beside the engine, e.g. a GPU parity test (repeatable)')
    ap.add_argument('--tree-label', help='probe: run the tree prepare --label built instead of production')
    a = ap.parse_args()
    if (a.label or a.patch or a.target) and a.cmd != 'prepare': raise SystemExit('--label/--patch/--target are for prepare')
    if (a.patch or a.target) and not a.label: raise SystemExit('a patched build needs its own --label (the release keeps its own prepare)')
    if a.label and not (a.label.startswith(a.tag) and re.fullmatch(r'[-.][-.\w]+', a.label[len(a.tag):])):
        raise SystemExit('--label looks wrong (the tag plus a suffix, e.g. v0.2.17-xp): %r' % a.label)
    if a.tree_label and a.cmd != 'probe': raise SystemExit('--tree-label is for probe (replay/approx name their tree in the preregistration)')
    if a.cmd in ('replay', 'approx') and (a.env or a.arg or a.limit or a.sampling): raise SystemExit('%s takes its runs from the preregistration, not --env/--arg/--sampling/--limit' % a.cmd)
    if a.baseline != BASE_ARM and (a.cmd != 'probe' or a.limit): raise SystemExit('--baseline is for a full probe arm')
    if a.cmd in ('probe', 'replay', 'approx'):
        if not re.fullmatch(r'[a-z][-.\w]*', a.tag) or re.match(r'v\d', a.tag): raise SystemExit('probe label looks wrong (lower-case, not a tag): %r' % a.tag)
    elif not re.fullmatch(r'v\d+\.\d+\.\d+[-.\w]*', a.tag): raise SystemExit('tag looks wrong: %r' % a.tag)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))     # turn SIGTERM into SystemExit so finally blocks restore production
    os.umask(0o022); UG.mkdir(parents=True, exist_ok=True)
    lock = open(UG / '.lock', 'w')
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: raise SystemExit('another upgrade_gate.py is running')
    phase = {'prepare': 'PREPARE.json', 'kl': 'KL.json', 'gate': 'GATE.json'}
    cur = a.cmd
    try:
        if a.cmd == 'prepare': prepare(a.tag, a.tree, a.j, a.label, a.patch, a.target)
        elif a.cmd == 'kl': kl(a.tag, a.repeat)
        elif a.cmd == 'gate': gate(a.tag, a.force, a.limit, dict(x.split('=', 1) for x in a.env), a.arg, parse_sampling(a.sampling))
        elif a.cmd == 'probe': probe(a.tag, a.force, a.limit, dict(x.split('=', 1) for x in a.env), a.arg, parse_sampling(a.sampling), a.baseline, a.tree_label)
        elif a.cmd == 'approx': approx_kl(a.tag, a.force)
        elif a.cmd == 'replay':
            if a.build: replay_build(a.tag)
            if a.freeze: replay_freeze(a.tag)
            if a.run: replay_run(a.tag, a.run, a.force, a.rerun)
            if a.eval: replay_eval(a.tag)
            if not (a.build or a.freeze or a.run or a.eval): raise SystemExit('replay needs --build, --freeze, --run NAME or --eval')
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
            wl = a.label if cur == 'prepare' and a.label else a.tag      # a probe build stops under its own label
            d = load(wl, phase[cur]) or {}; d.update(stop=str(e), status=d.get('status') if d.get('status') not in (None, 'RUNNING') else 'STOPPED'); save(wl, phase[cur], d)
        if a.cmd == 'all': report(a.tag)
        sys.exit(2)


if __name__ == '__main__':
    main()

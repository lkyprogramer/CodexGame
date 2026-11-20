import json, shutil, subprocess, os, hashlib
from pathlib import Path
N = Path('/home/hhtele/strata-0.2.17'); BD2 = Path('/data/strata-data/v0217-baseline-20261120'); OLD = Path('/home/hhtele/strata-0.2.3')
PYSRC = Path('/data/strata-data/dsv41-0210-lab/terminal/0.1.56/python')
assert not N.exists(), 'target exists'
N.mkdir()
shutil.copytree(BD2 / 'src/terminal', N / 'terminal', symlinks=True, ignore=shutil.ignore_patterns('__pycache__'))
(N / 'engine').mkdir(); shutil.copy2(BD2 / 'build/strata', N / 'engine/strata')
shutil.copytree(PYSRC, N / 'python', symlinks=True)
(N / 'data').mkdir(); shutil.copy2(OLD / 'data/expert-profile-iq3xxs.bin', N / 'data/expert-profile-iq3xxs.bin')
shutil.copy2(BD2 / 'v0216-pt0-reply-reuse.patch', N / 'v0216-pt0-reply-reuse.patch')
for d in ('slots', 'state/data', 'state/xdg-data', 'state/xdg-config', 'state/xdg-cache', 'state/draft-costs'): (N / d).mkdir(parents=True)
cfg = json.loads((OLD / 'strata-iq3_xxs.json').read_text())
a = cfg['args']
a[a.index('--expert-profile') + 1] = str(N / 'data/expert-profile-iq3xxs.bin')
a[a.index('--expert-profile-save') + 1] = str(N / 'data/expert-profile-iq3xxs-learned.bin')
for k, v in (('--lookup-max-t', '0'), ('--conversation-spill-mib', '0'), ('--ple-io', 'direct')):
    assert k not in a; a += [k, v]
cfg['env'] = dict(cfg.get('env') or {}, STRATA_ROUTE_TAIL_SKIP='7')
cfg.update(exe=str(N / 'engine/strata'), lib_dirs=[str(N / 'engine'), '/usr/local/cuda-12.3/bin', '/usr/local/cuda-12.3/lib64'], cwd=str(N),
           log=str(N / 'strata-iq3_xxs.log'), drafting='mtp', draft_costs=False, parallel=1, engine_ready_s=400, api_monitor=False,
           slot_save_path=str(N / 'slots'), port=18343)
(N / 'strata-iq3_xxs.json').write_text(json.dumps(cfg, indent=2) + '\n')
run = f'''#!/bin/sh
# Strata v0.2.17 production tree (2026-11-20): tag v0.2.17 (commit 12d491da4) + PT0/#1536 port (v0216-pt0-reply-reuse.patch,
# identical to CodexGame patches/v0217-pt0-reply-reuse.patch), engine 0.1.63 self-built with CUDA 12.3 for sm_89.
# Config = lab baseline B2: production args + --lookup-max-t 0 --conversation-spill-mib 0 --ple-io direct, env STRATA_ROUTE_TAIL_SKIP=7
# (0.2.17 turned the tail skip off by default; 0.2.3 and B1 ran with rank 7).  State dirs are private to this tree.
# Rollback: /home/hhtele/strata-0.2.3/run-iq3_xxs.sh.pre-0217-20261120 back over /home/hhtele/strata-0.2.3/run-iq3_xxs.sh.
cd "{N}"
export STRATA_REPLY_REUSE=1        # #1536: the next turn reuses the reply's own token ids
export STRATA_PRESERVE_THINKING=0  # CFG-PT: earlier turns' thinking is not rendered (a request's chat_template_kwargs wins)
export STRATA_DATA_DIR="{N}/state/data" STRATA_DRAFT_COSTS_DIR="{N}/state/draft-costs"
export XDG_DATA_HOME="{N}/state/xdg-data" XDG_CONFIG_HOME="{N}/state/xdg-config" XDG_CACHE_HOME="{N}/state/xdg-cache"
export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
exec "{N}/python/bin/python3" -B "{N}/terminal/serve/server.py" "--engine" "strata" "--config" "{N}/strata-iq3_xxs.json" "--port" "18343"
'''
(N / 'run-iq3_xxs.sh').write_text(run); os.chmod(N / 'run-iq3_xxs.sh', 0o755)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
ident = dict(tag='v0.2.17', tag_object='028e6826bdb152be2d0579818c2ede6fe7da984c', tag_commit='12d491da4a6904eb49aaa6f2f63ec4b1a17582e3',
             engine_sha256=sha(N / 'engine/strata'), patch_sha256=sha(N / 'v0216-pt0-reply-reuse.patch'), config_sha256=sha(N / 'strata-iq3_xxs.json'),
             run_sha256=sha(N / 'run-iq3_xxs.sh'), expert_profile_sha256=sha(N / 'data/expert-profile-iq3xxs.bin'),
             patched_files={f: sha(N / 'terminal' / f) for f in ('serve/frontend.py', 'serve/server.py', 'tools/strata_tokenizer.py')},
             python=str(PYSRC) + ' (copied)', created='2026-11-20')
(N / 'IDENTITY.json').write_text(json.dumps(ident, indent=1) + '\n')
print(json.dumps(ident, indent=1))
print(subprocess.run([str(N / 'python/bin/python3'), '-c', 'import sys,jinja2;print(sys.prefix, sys.version.split()[0], jinja2.__version__)'], capture_output=True, text=True).stdout)
print(subprocess.run([str(N / 'engine/strata'), '--version'], capture_output=True, text=True).stdout.strip())
print(subprocess.run(['du', '-sh', str(N)], capture_output=True, text=True).stdout)

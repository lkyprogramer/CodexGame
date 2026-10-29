"""Multi-turn quality chain for the single-session pattern: one conversation builds a Python module in 8 follow-up
turns, each adding one requirement; every reply must carry the complete module.  Hidden tests for requirements
1..t run against turn t's code, so a later turn that drops or breaks an earlier requirement loses points.

Pi wire format (reasoning_effort xhigh, temperature 1.0 / top_p 0.95 / top_k 20, thinking sent back as
reasoning_content, max_tokens clamped to the context like pi-ai).  No compaction is simulated: a turn that no longer
fits ends the chain (recorded).

  python tools/session/chain_bench.py --name NAME --image python:3.12-slim [--tree DIR] [--env K=V ...]

Grading runs only in an isolated local Docker image (--image, resolved to its immutable ID, never pulled); without
--image the tests are NOT_RUN (passed=None) and only speed / context numbers are recorded.
"""
import argparse, json, re, subprocess, sys, tempfile, textwrap, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]   # lab package root
sys.path.insert(0, str(ROOT))
from lab import http
from lab.core import dump, load_config
from lab.runner import OwnedServer, wait_released
from lab.workspace import baseline_dir

OUT = ROOT / 'workspace/reports/chain'
SYSTEM = 'You are a senior Python engineer pairing with one developer over a long session.'
FORMAT = ('\n\nReply with the COMPLETE module implementing every requirement so far in a single ```python code block, '
          'then at most three sentences.')
REQS = [
    'We are building a small in-memory ledger module in Python 3.11, step by step. Requirement 1: a class `Ledger` '
    'with `add(account: str, amount: int)` and `balance(account: str) -> int`. Unknown accounts have balance 0. '
    '`add` accepts negative amounts.',
    'Requirement 2: `transfer(src, dst, amount)`. `amount` must be a positive int, otherwise raise ValueError. If the '
    'source does not have enough funds raise ValueError and change nothing.',
    "Requirement 3: `history(account)` returns a list of `(op, amount)` tuples in order. Ops: 'add' (the amount as "
    "given), 'transfer_out' and 'transfer_in' (positive amounts). A failed operation records nothing. The returned "
    'list must be a copy.',
    'Requirement 4: `set_limit(account, limit)` sets an overdraft limit (int >= 0, otherwise ValueError). A transfer '
    'is allowed when the source balance minus the amount stays >= -limit.',
    'Requirement 5: `snapshot()` returns an independent copy of the whole state (balances, limits, histories) and '
    '`restore(snap)` brings that exact state back. Later operations must not change a snapshot, and restoring the '
    'same snapshot twice must work.',
    "Requirement 6: `set_fee_bps(bps)` (int 0..10000, otherwise ValueError). A transfer also charges the source a fee "
    "of ceil(amount * bps / 10000), recorded as ('fee', fee) right after its 'transfer_out'. The fee counts against "
    'funds and the overdraft limit. A zero fee records nothing.',
    'Requirement 7: `undo()` reverts the last successful mutating call (add, transfer including its fee, set_limit, '
    'set_fee_bps, restore), history entries included. With nothing to undo raise IndexError.',
    'Requirement 8: make every method safe under concurrent calls from many threads.',
]
TESTS = [
    """
l = M.Ledger(); l.add('a', 5); l.add('a', -2)
assert l.balance('a') == 3 and l.balance('z') == 0
""", """
l = M.Ledger(); l.add('a', 10); l.transfer('a', 'b', 4)
assert (l.balance('a'), l.balance('b')) == (6, 4)
for bad in (7, 0, -1):
    try: l.transfer('a', 'b', bad); raise AssertionError('no ValueError')
    except ValueError: pass
assert (l.balance('a'), l.balance('b')) == (6, 4)
""", """
l = M.Ledger(); l.add('a', 10); l.transfer('a', 'b', 3)
try: l.transfer('a', 'b', 100)
except ValueError: pass
assert l.history('a') == [('add', 10), ('transfer_out', 3)] and l.history('b') == [('transfer_in', 3)]
h = l.history('a'); h.append(('x', 1)); assert len(l.history('a')) == 2
""", """
l = M.Ledger(); l.add('a', 5); l.set_limit('a', 10); l.transfer('a', 'b', 15)
assert l.balance('a') == -10
try: l.transfer('a', 'b', 1); raise AssertionError('limit ignored')
except ValueError: pass
try: l.set_limit('a', -1); raise AssertionError('negative limit')
except ValueError: pass
""", """
l = M.Ledger(); l.add('a', 5); s = l.snapshot(); l.add('a', 7); l.transfer('a', 'b', 3)
l.restore(s); assert l.balance('a') == 5 and l.balance('b') == 0 and l.history('a') == [('add', 5)]
l.add('a', 1); l.restore(s); assert l.balance('a') == 5 and l.history('a') == [('add', 5)]
""", """
l = M.Ledger(); l.add('a', 1000); l.set_fee_bps(150); l.transfer('a', 'b', 100)
assert (l.balance('a'), l.balance('b')) == (898, 100)
assert l.history('a')[-2:] == [('transfer_out', 100), ('fee', 2)]
try: l.transfer('a', 'b', 885); raise AssertionError('fee ignored in funds check')
except ValueError: pass
for bad in (-1, 10001):
    try: l.set_fee_bps(bad); raise AssertionError('bad bps')
    except ValueError: pass
l2 = M.Ledger(); l2.add('a', 5); l2.transfer('a', 'b', 1); assert l2.history('a') == [('add', 5), ('transfer_out', 1)]
""", """
l = M.Ledger()
try: l.undo(); raise AssertionError('no IndexError')
except IndexError: pass
l.add('a', 5); l.transfer('a', 'b', 2); l.undo()
assert (l.balance('a'), l.balance('b')) == (5, 0) and l.history('a') == [('add', 5)] and l.history('b') == []
l.set_limit('a', 3); l.undo()
try: l.transfer('a', 'b', 6); raise AssertionError('limit not undone')
except ValueError: pass
l.undo(); assert l.balance('a') == 0
""", """
import sys, threading
sys.setswitchinterval(1e-5)   # switch threads as often as possible so a missing lock shows
l = M.Ledger(); l.add('a', 100000); errors = []
def guard(f):
    def run():
        try: f()
        except BaseException as e: errors.append(e)
    return run
def mover():
    for _ in range(100): l.transfer('a', 'b', 1); l.transfer('b', 'a', 1); l.history('a')
def adder():
    for _ in range(200): l.add('c', 1)
ts = [threading.Thread(target=guard(mover)) for _ in range(4)] + [threading.Thread(target=guard(adder)) for _ in range(4)]
[t.start() for t in ts]; [t.join() for t in ts]
assert not errors, errors[:1]
assert l.balance('a') + l.balance('b') == 100000 and l.balance('c') == 800
""",
]


# Runs inside the container: each requirement in its own interpreter, 60 s each; prints one JSON list.
DRIVER = '''import json, subprocess, sys
res = []
for i in range(int(sys.argv[1])):
    try:
        r = subprocess.run([sys.executable, "-I", "/work/t%d.py" % i, "/work/ledger.py"], capture_output=True, timeout=60)
        res.append(r.returncode == 0)
    except subprocess.TimeoutExpired:
        res.append(False)
print(json.dumps(res))
'''


def image_id(image):
    """Resolve a preinstalled local image to its immutable ID; never pulls."""
    out = subprocess.run(['docker', 'image', 'inspect', image, '--format', '{{.Id}}'], capture_output=True, text=True,
                         timeout=30).stdout.strip()
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', out):
        raise SystemExit(f'--image {image!r} is not a local Docker image; model code is never run on the host')
    return out


def grade(code, upto, image):
    """Requirements 1..upto against `code`, per requirement True/False, or None (NOT_RUN) without an image.

    Model-written code runs only in a throw-away container: no network, read-only root and input, non-root,
    capped memory / CPU / PIDs, all capabilities dropped (the same isolation as lab/java_eval.py)."""
    if not image:
        return None
    name = 'strata-lab-chain-' + uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix='chain-') as d:
        p = Path(d)
        p.chmod(0o755)
        (p / 'ledger.py').write_text(code)
        (p / 'driver.py').write_text(DRIVER)
        for i in range(upto):
            prog = ('import importlib.util as u, sys\nsp=u.spec_from_file_location("ledger", sys.argv[1])\n'
                    'M=u.module_from_spec(sp)\nsp.loader.exec_module(M)\n' + textwrap.dedent(TESTS[i]))
            (p / f't{i}.py').write_text(prog)
        for q in p.iterdir():
            q.chmod(0o644)
        cmd = ['docker', 'run', '--name', name, '--rm', '--pull=never', '--network', 'none', '--read-only',
               '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--memory', '512m', '--memory-swap', '512m',
               '--cpus', '2', '--pids-limit', '64', '--user', '65534:65534', '--tmpfs', '/tmp:rw,nosuid,size=64m',
               '--mount', f'type=bind,src={p},dst=/work,readonly', image, 'python', '-I', '/work/driver.py', str(upto)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60 * upto + 60)
            res = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else None
            if not (isinstance(res, list) and len(res) == upto and all(type(x) is bool for x in res)):
                raise RuntimeError(f'grader container failed: rc={r.returncode} {r.stderr[-500:]}')
            return res
        finally:
            # Exact generated container name only; never touch any other container.
            subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', required=True)
    ap.add_argument('--config', default=str(ROOT / 'config/local.json'))
    ap.add_argument('--tree', default='')
    ap.add_argument('--env', action='append', default=[])
    ap.add_argument('--max-tokens', type=int, default=32768)
    ap.add_argument('--image', default='', help='local Docker Python image for grading; empty = NOT_RUN')
    a = ap.parse_args()
    c = load_config(a.config)
    img = image_id(a.image) if a.image else ''
    tree = Path(a.tree) if a.tree else baseline_dir(c)
    ready = {'cfg': {'env': dict(x.split('=', 1) for x in a.env)}}
    folder = OUT / a.name
    msgs = [{'role': 'system', 'content': SYSTEM}]
    rows, est = [], 0
    wait_released(c)
    with OwnedServer(c, tree, 'cfg' if a.env else 'base', ready, folder) as srv:
        for t, req in enumerate(REQS):
            msgs.append({'role': 'user', 'content': req + FORMAT})
            est += len(msgs[-1]['content']) // 3
            max_new = min(a.max_tokens, c['max_context'] - est - 4096)
            if max_new < 1024:
                rows.append({'turn': t, 'skipped': 'context full'}); break
            body = {'model': 'strata', 'messages': msgs, 'max_tokens': max_new, 'temperature': 1.0, 'top_p': 0.95,
                    'top_k': 20, 'reasoning_effort': 'xhigh'}
            r = http.chat(srv.base, body, srv.key, timeout=2400)
            m = http.measurements(r)
            blocks = re.findall(r'```python\n(.*?)```', r.get('text') or '', re.S)
            score = (grade(blocks[-1], t + 1, img) if blocks else [False] * (t + 1)) if img else None
            rows.append(dict(turn=t, max_tokens=max_new, error=r.get('error'), finish=r.get('finish_reason'),
                             has_code=bool(blocks), passed=score, pass_new=score[-1] if score else None, pass_all=all(score) if score else None,
                             reasoning_chars=len(r.get('reasoning') or ''), answer_chars=len(r.get('text') or ''), **m))
            print(a.name, t, 'prompt', m['prompt_tokens'], 'reused', m['reused_tokens'], 'read', m['read_tokens'],
                  'ttft', round(m['ttft_s'] or -1, 2), 'gen', m['generated_tokens'], 'dec', round(m['decode_tps'] or -1, 1),
                  'finish', r.get('finish_reason'), 'tests', ''.join('1' if x else '0' for x in score) if score else 'NOT_RUN', r.get('error') or '',
                  flush=True)
            if r.get('error'): break
            am = {'role': 'assistant', 'content': r.get('text') or ''}
            if r.get('reasoning'): am['reasoning_content'] = r['reasoning']
            msgs.append(am)
            est = (m['prompt_tokens'] or 0) + (m['generated_tokens'] or 0)
    dump(folder / 'chain.json', {'name': a.name, 'env': a.env, 'grader_image': img or 'NOT_RUN', 'rows': rows, 'messages': msgs, 'abort': srv.abort_reason})


if __name__ == '__main__':
    main()

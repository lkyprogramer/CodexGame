"""Pi-like agent load on the production Strata service (2026-11-20).
Tasks: Aider-AI/polyglot-benchmark python exercises (Exercism, MIT).  Two sessions alternate task by task (session switch ->
park/restore), each task is a tool loop (read/write/edit/bash), tasks accumulate in the session like a long Pi session.
bash runs only in the isolated grader container (no network, read-only root, --pull=never, local image id).
Samples swap / engine major faults every 2 s.  Talks to 127.0.0.1:18343 (production) directly."""
import json, os, re, shutil, subprocess, sys, threading, time
from pathlib import Path
from urllib.request import Request, urlopen
PS = Path('/data/strata-data/pisim-20261120'); BENCH = PS / 'bench/python/exercises/practice'
URL = 'http://127.0.0.1:18343/v1/chat/completions'; MODEL = 'openclaw/Qwen3.8-next'
IMAGE = 'sha256:ec7d6c95cd3692a2e2d228a8b1ca74e4025b54121fcc4c5da6f09cfa473315ad'
LOG = Path('/home/hhtele/strata-0.2.17/strata-iq3_xxs.log')
WANT = ['wordy', 'bowling', 'book-store', 'tree-building', 'grep', 'forth', 'zebra-puzzle', 'poker', 'sgf-parsing', 'rest-api',
        'two-bucket', 'go-counting', 'react', 'connect', 'pov', 'dominoes']
BUDGET_S = 2400; MAX_TURNS = 14; CTX_LIMIT = 100000
SYSTEM = """You are an expert coding assistant working inside a developer's workspace. You help by reading files, running commands,
editing code and writing new files.

Available tools:
- read: read the contents of a file (relative to the workspace root)
- bash: run a shell command in the workspace root (python3 is available; no network)
- edit: replace an exact unique string in a file with new text
- write: create or overwrite a file

Guidelines:
- Use read to look at files before editing them; do not guess their contents.
- Use edit for precise changes (the old text must match exactly once); use write for new files or complete rewrites.
- Run the tests with bash after changing code, and keep fixing until they pass.
- Keep answers short: when the task is done, reply with one or two sentences saying what you changed.
- Do not modify test files.
"""
TOOLS = [
 {'type': 'function', 'function': {'name': 'read', 'description': 'Read a text file. Output is truncated at 16000 characters.',
  'parameters': {'type': 'object', 'properties': {'path': {'type': 'string', 'description': 'Path relative to the workspace root'}}, 'required': ['path']}}},
 {'type': 'function', 'function': {'name': 'bash', 'description': 'Run a shell command in the workspace root. 60 s timeout, no network. Output (stdout+stderr) truncated at 16000 characters.',
  'parameters': {'type': 'object', 'properties': {'command': {'type': 'string'}}, 'required': ['command']}}},
 {'type': 'function', 'function': {'name': 'edit', 'description': 'Replace exactly one occurrence of old_text with new_text in a file.',
  'parameters': {'type': 'object', 'properties': {'path': {'type': 'string'}, 'old_text': {'type': 'string'}, 'new_text': {'type': 'string'}}, 'required': ['path', 'old_text', 'new_text']}}},
 {'type': 'function', 'function': {'name': 'write', 'description': 'Write a file (creates directories), overwriting it.',
  'parameters': {'type': 'object', 'properties': {'path': {'type': 'string'}, 'content': {'type': 'string'}}, 'required': ['path', 'content']}}},
]
def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
def engine_pid():
    r = subprocess.run(['pgrep', '-f', '^/home/hhtele/strata-0.2.17/engine/strata --serve'], capture_output=True, text=True).stdout.split()
    return int(r[0]) if r else None
def sample(pid):
    vm = dict(l.split() for l in open('/proc/vmstat') if l.startswith(('pswpin ', 'pswpout ')))
    mi = {l.split(':')[0]: int(l.split()[1]) for l in open('/proc/meminfo') if l.startswith(('MemAvailable', 'SwapFree'))}
    s = dict(t=time.time(), pswpin=int(vm['pswpin']), pswpout=int(vm['pswpout']), avail_mib=mi['MemAvailable'] // 1024, swapfree_mib=mi['SwapFree'] // 1024)
    try:
        st = open('/proc/%d/stat' % pid).read().rsplit(')', 1)[1].split()
        s['majflt'] = int(st[9])
        s['vmswap_mib'] = next(int(l.split()[1]) for l in open('/proc/%d/status' % pid) if l.startswith('VmSwap')) // 1024
    except Exception:
        pass
    return s
def inside(ws, p):
    q = (ws / p).resolve()
    if not str(q).startswith(str(ws.resolve()) + os.sep): raise ValueError('path outside workspace')
    return q
def run_tool(ws, name, args, n):
    try:
        if name == 'read':
            return inside(ws, args['path']).read_text(errors='replace')[:16000]
        if name == 'write':
            q = inside(ws, args['path'])
            if q.name.endswith('_test.py'): return 'error: test files are read-only'
            q.parent.mkdir(parents=True, exist_ok=True); q.write_text(args['content']); return 'wrote %d bytes to %s' % (len(args['content']), args['path'])
        if name == 'edit':
            q = inside(ws, args['path'])
            if q.name.endswith('_test.py'): return 'error: test files are read-only'
            t = q.read_text(); k = t.count(args['old_text'])
            if k != 1: return 'error: old_text found %d times (must be exactly once)' % k
            q.write_text(t.replace(args['old_text'], args['new_text'])); return 'edited %s' % args['path']
        if name == 'bash':
            cname = 'pisim-%d-%d' % (os.getpid(), n)
            cmd = ['docker', 'run', '--rm', '--name', cname, '--network', 'none', '--pull=never', '--read-only', '--tmpfs', '/tmp:rw,size=64m',
                   '--memory', '512m', '--cpus', '1', '--pids-limit', '128', '--user', '%d:%d' % (os.getuid(), os.getgid()),
                   '-e', 'HOME=/tmp', '-e', 'PYTHONDONTWRITEBYTECODE=1', '-v', '%s:/w:rw' % ws, '-w', '/w', IMAGE, 'sh', '-c', args['command']]
            try:
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                out = (p.stdout + p.stderr)[-16000:]
                return out + ('\n[exit %d]' % p.returncode)
            except subprocess.TimeoutExpired:
                subprocess.run(['docker', 'kill', cname], capture_output=True); return '[timeout after 60 s]'
        return 'error: unknown tool %s' % name
    except Exception as e:
        return 'error: %s: %s' % (type(e).__name__, e)
def grade(ws, ex):
    mod = ex.replace('-', '_')
    r = run_tool(ws, 'bash', {'command': 'cd %s && python3 -m unittest -q %s_test 2>&1 | tail -3' % (ex, mod)}, 0)
    return bool(re.search(r'^OK', r, re.M)), r[-300:]
def chat(body):
    t0 = time.monotonic()
    with urlopen(Request(URL, json.dumps(body).encode(), {'Content-Type': 'application/json'}), timeout=900) as f:
        r = json.loads(f.read())
    return r, time.monotonic() - t0
def main():
    out = PS / 'run'; out.mkdir()
    pid = engine_pid(); assert pid, 'production engine not running'
    log_off = LOG.stat().st_size
    names = [x for x in WANT if (BENCH / x).is_dir()]
    sessions = {'A': dict(messages=[{'role': 'system', 'content': SYSTEM}], ws=PS / 'ws/A', n=0), 'B': dict(messages=[{'role': 'system', 'content': SYSTEM}], ws=PS / 'ws/B', n=0)}
    samples = []; stop = threading.Event()
    def mon():
        while not stop.wait(2):
            s = sample(pid); samples.append(s)
            if s['avail_mib'] < 3000: log('GUARD low memory', s); stop.set()
    th = threading.Thread(target=mon, daemon=True); th.start()
    rows = []; tasks = []; t0 = time.monotonic(); n = 0
    try:
        for i, ex in enumerate(names):
            if stop.is_set() or time.monotonic() - t0 > BUDGET_S: break
            sid = 'AB'[i % 2]; S = sessions[sid]; ws = S['ws']
            ws.mkdir(parents=True, exist_ok=True)
            shutil.copytree(BENCH / ex, ws / ex, ignore=shutil.ignore_patterns('.meta'))
            mod = ex.replace('-', '_')
            S['messages'].append({'role': 'user', 'content': 'New task: solve the exercise in `%s/`. The instructions are in `%s/.docs/instructions.md`%s. Implement `%s/%s.py` so that `%s/%s_test.py` passes (run it with `cd %s && python3 -m unittest -q %s_test`).' % (
                ex, ex, ' (plus `%s/.docs/instructions.append.md`)' % ex if (ws / ex / '.docs/instructions.append.md').exists() else '', ex, mod, ex, mod, ex, mod)})
            log('TASK', i, sid, ex)
            done = False; turns = 0
            while not done and turns < MAX_TURNS and not stop.is_set() and time.monotonic() - t0 < BUDGET_S:
                turns += 1; n += 1
                body = dict(model=MODEL, messages=S['messages'], tools=TOOLS, max_tokens=16384, stream=False)
                b0 = sample(pid)
                try:
                    r, wall = chat(body)
                except Exception as e:
                    log('REQUEST_ERROR', e); rows.append(dict(n=n, session=sid, task=ex, error=str(e))); stop.set(); break
                b1 = sample(pid)
                ch = r['choices'][0]; m = ch['message']; u = r.get('usage') or {}
                a = {'role': 'assistant', 'content': m.get('content') or ''}
                if m.get('reasoning_content'): a['reasoning_content'] = m['reasoning_content']
                if m.get('tool_calls'): a['tool_calls'] = m['tool_calls']
                S['messages'].append(a)
                row = dict(n=n, session=sid, task=ex, turn=turns, finish=ch.get('finish_reason'), prompt_tokens=u.get('prompt_tokens'),
                           completion_tokens=u.get('completion_tokens'), wall_s=round(wall, 2), tools=[t['function']['name'] for t in m.get('tool_calls') or []],
                           majflt=b1.get('majflt', 0) - b0.get('majflt', 0), pswpin=b1['pswpin'] - b0['pswpin'], pswpout=b1['pswpout'] - b0['pswpout'], timings=r.get('timings'))
                rows.append(row); log('REQ', json.dumps({k: row[k] for k in ('n', 'session', 'task', 'turn', 'finish', 'prompt_tokens', 'completion_tokens', 'wall_s', 'tools', 'majflt', 'pswpin')}))
                if m.get('tool_calls'):
                    for tc in m['tool_calls']:
                        try: args = json.loads(tc['function']['arguments'] or '{}')
                        except Exception as e: args = None; res = 'error: arguments are not valid JSON: %s' % e
                        if args is not None: res = run_tool(ws, tc['function']['name'], args, n)
                        S['messages'].append({'role': 'tool', 'tool_call_id': tc['id'], 'content': res})
                else:
                    done = True
                if (u.get('prompt_tokens') or 0) > CTX_LIMIT:
                    log('SESSION RESET (context)', sid); S['messages'] = [{'role': 'system', 'content': SYSTEM}]
            ok, tail = grade(ws, ex)
            tasks.append(dict(task=ex, session=sid, turns=turns, finished=done, passed=ok, tail=tail)); log('GRADE', ex, ok)
            (out / ('session-%s.json' % sid)).write_text(json.dumps(S['messages'], ensure_ascii=False, indent=1))
    finally:
        stop.set(); th.join(5)
        with open(LOG, 'rb') as f:
            f.seek(log_off); (out / 'engine-slice.log').write_bytes(f.read())
        (out / 'RESULT.json').write_text(json.dumps(dict(tasks=tasks, requests=rows, samples=samples, elapsed_s=round(time.monotonic() - t0, 1)), indent=1))
        log('FINISHED', len(tasks), 'tasks', sum(t['passed'] for t in tasks), 'passed', len(rows), 'requests')
if __name__ == '__main__':
    main()

"""#2253 Phase A2/D: Pi-shaped park/restore pressure.

Three long conversations (32K/48K/64K ledger contexts) take turns, a fresh short conversation is interleaved every
cycle, and the parking path's physical-RAM gate is made to fire by a fixed --conversation-cache-min-free-mib.
After each request: engine [heap] Rss, anonymous Rss and MemAvailable.  Arms: a0 (A0 binary), off / on (the
#2253 port with STRATA_LAB_PR2253=0/1), mmap (A0 + MALLOC_MMAP_THRESHOLD_=8388608).

  python park_scenario.py calibrate
  python park_scenario.py run --floor-mib N --rounds 3 [--arms a0,off,on,mmap]
"""
import argparse, copy, json, os, re, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]   # lab package root
sys.path.insert(0, str(ROOT))
from lab import http
from lab.core import dump, hash_obj, load_config
from lab.corpus import SYSTEM, body, fit_ledger
from lab.runner import OwnedServer, wait_released
from lab.tokenizer import StrataCounter
from lab.workspace import baseline_dir, candidate_dir

OUT = ROOT / 'workspace/reports/p2253'
LONG = [32768, 49152, 65536]
CYCLES = 10
ACTIVATION = {'off': r'LAB_PR_2253 enabled=0', 'on': r'LAB_PR_2253 enabled=1'}


def corpus(c):
    p = OUT / 'corpus.json'
    if p.exists(): return json.loads(p.read_text())
    counter = StrataCounter(baseline_dir(c), c['gguf'], c['template'])
    longs = []
    for k, target in enumerate(LONG):
        b, expected = fit_ledger(counter, target - 400, 20262253 + k, SYSTEM + f' Park scenario conversation L{k}.')
        b['max_tokens'] = 32
        longs.append({'body': b, 'ids': sorted(expected), 'tokens': counter(b)})
    shorts = []
    for i in range(CYCLES):
        b, _ = fit_ledger(counter, 1536, 20263000 + i, SYSTEM + f' Short side task S{i}.')
        b['max_tokens'] = 16
        shorts.append(b)
    out = {'longs': longs, 'shorts': shorts}
    out['sha256'] = hash_obj(out)
    OUT.mkdir(parents=True, exist_ok=True); dump(p, out)
    return out


def engine_pid(exe):
    exe = os.path.realpath(exe)
    for d in Path('/proc').iterdir():
        if not d.name.isdigit(): continue
        try:
            if os.path.realpath(d / 'exe') == exe: return int(d.name)
        except OSError: pass
    return None


def sample(pid):
    s = {'ts': time.time()}
    for line in open('/proc/meminfo'):
        if line.startswith('MemAvailable:'): s['mem_available_mib'] = int(line.split()[1]) // 1024
    try:
        heap, cur = 0, None
        for line in open(f'/proc/{pid}/smaps'):
            if not line[0].isupper() or ':' not in line.split()[0]:
                cur = line.split()[-1] if len(line.split()) >= 6 else ''
            elif cur == '[heap]' and line.startswith('Rss:'): heap += int(line.split()[1])
        s['heap_rss_mib'] = heap // 1024
        for line in open(f'/proc/{pid}/smaps_rollup'):
            k = line.split(':')[0]
            if k in ('Rss', 'Anonymous'): s[k.lower() + '_mib'] = int(line.split()[1]) // 1024
    except OSError as e: s['error'] = str(e)
    return s


def arm_spec(c, arm, floor):
    cc = copy.deepcopy(c)
    ready = {'common': {'args': {'--conversation-cache-min-free-mib': str(floor)}}, 'activation': ACTIVATION}
    if arm == 'a0': return cc, baseline_dir(c), 'base', ready
    if arm == 'mmap':
        cc['extra_frozen_env'] = dict(cc.get('extra_frozen_env', {}), MALLOC_MMAP_THRESHOLD_='8388608')
        return cc, baseline_dir(c), 'base', ready
    ready[arm] = {'env': {'STRATA_LAB_PR2253': '1' if arm == 'on' else '0'}}
    return cc, candidate_dir(c, 2253), arm, ready


def log_counts(folder):
    text = '\n'.join(p.read_text(errors='replace') for p in Path(folder).glob('*.log'))
    gate = re.findall(r'skip parking \(physical RAM admission.*?evicted (\d+), (\d+) still parked', text)
    trims = [float(x) for x in re.findall(r'LAB_PR_2253 trim ([0-9.]+) ms', text)]
    return {
        'parked': len(re.findall(r'conversation cache: parked ', text)),
        'restored': len(re.findall(r'conversation cache: restored ', text)),
        'gate_refusals': len(gate),
        'refusals_after_eviction': sum(1 for e, _ in gate if int(e) > 0),
        'refusals_cache_empty': sum(1 for _, k in gate if int(k) == 0),
        'gate_evicted_in_refusals': sum(int(e) for e, _ in gate),
        'evicted_to_admit': sum(int(x) for x in re.findall(r'evicted (\d+) parked conversations? to admit', text)),
        'floor_after_capture': len(re.findall(r'RAM floor after capture', text)),
        'other_skips': len(re.findall(r'skip parking \((?!physical RAM|RAM floor)', text)),
        'trims': len(trims), 'trim_ms_total': round(sum(trims), 1),
        'trim_ms_max': max(trims) if trims else 0.0,
    }


PATTERNS = {'rr': ['L0', 'L1', 'S', 'L2'],     # three long conversations in turn
            'main': ['L2', 'S', 'L2', 'L0']}  # an agent's 64K main line between short side tasks and a 32K one


def one_arm(c, arm, floor, data, folder, pattern='rr'):
    cc, tree, label, ready = arm_spec(c, arm, floor)
    wait_released(cc)
    rows = []
    with OwnedServer(cc, tree, label, ready, folder) as srv:
        pid = engine_pid(srv.cfg['exe'])
        loaded = sample(pid)
        hist = [copy.deepcopy(x['body']) for x in data['longs']]
        seq = [(who, i) for i in range(CYCLES) for who in PATTERNS[pattern]]
        visits = [0, 0, 0]
        for n, (who, i) in enumerate(seq):
            if who == 'S': b = data['shorts'][i]
            else:
                k = int(who[1]); b = hist[k]; v = visits[k]; visits[k] += 1
                if v > 0:
                    rid = data['longs'][k]['ids'][v % len(data['longs'][k]['ids'])]
                    b['messages'].append({'role': 'user', 'content': f'Turn {v}: what is the immutable_value of {rid}? '
                                                                     'Answer with the value only.'})
            r = http.chat(srv.base, b, srv.key, timeout=900)
            if who != 'S' and not r.get('error'):
                b['messages'].append({'role': 'assistant', 'content': r['text']})
            time.sleep(0.5)   # let the park after the reply finish before sampling
            row = dict(n=n, who=who, cycle=i, error=r.get('error'), **http.measurements(r), **sample(pid))
            rows.append(row)
            print(arm, n, who, i, 'read', row['read_tokens'], 'reused', row['reused_tokens'], 'ttft',
                  round(row['ttft_s'] or -1, 2), 'heap', row.get('heap_rss_mib'), 'avail', row.get('mem_available_mib'),
                  flush=True)
    res = {'arm': arm, 'floor_mib': floor, 'pattern': pattern, 'loaded': loaded, 'rows': rows, 'log': log_counts(folder),
           'corpus_sha256': data['sha256'], 'abort': srv.abort_reason}
    dump(Path(folder) / 'park.json', res)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['calibrate', 'run'])
    ap.add_argument('--config', default=str(ROOT / 'config/local.json'))
    ap.add_argument('--floor-mib', type=int, default=2560)
    ap.add_argument('--rounds', type=int, default=3)
    ap.add_argument('--arms', default='a0,off,on,mmap')
    ap.add_argument('--start-round', type=int, default=1)
    ap.add_argument('--pattern', default='rr', choices=sorted(PATTERNS))
    a = ap.parse_args()
    c = load_config(a.config)
    data = corpus(c)
    print('corpus', data['sha256'][:12], [x['tokens'] for x in data['longs']], flush=True)
    if a.mode == 'calibrate':
        # The default floor (2560) does not fire here: what does one conversation cost, and what is free once loaded?
        res = one_arm(c, 'a0', 2560, data, OUT / 'calibrate')
        print(json.dumps({'loaded': res['loaded'], 'log': res['log'],
                          'avail': [r.get('mem_available_mib') for r in res['rows']]}, indent=1))
        return
    arms = a.arms.split(',')
    for rnd in range(a.start_round, a.start_round + a.rounds):
        order = arms[(rnd - 1) % len(arms):] + arms[:(rnd - 1) % len(arms)]
        for arm in order:
            base = OUT if a.pattern == 'rr' else OUT / a.pattern
            res = one_arm(c, arm, a.floor_mib, data, base / f'r{rnd}-{arm}', a.pattern)
            print('DONE', rnd, arm, json.dumps(res['log']), flush=True)


if __name__ == '__main__':
    main()

"""Protocol A/B (2026-11-20): per stage C = fresh c100k prefill + 1024 decode, then P = same body again (prefix reused) + 1024 decode."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import campaign as c, quality as q
OUT = c.BD / 'runs' / 'proto'

def work(d, model, guard):
    body = json.loads((c.BD / 'fixtures.json').read_text())['c100k']['body']
    out = {}
    for tag in ('C', 'P'):
        if tag == 'P': time.sleep(8)
        r = c.chat(d, tag, dict(body, max_tokens=1024), model); out[tag] = r
        print(' ', tag, r.get('timings'), r.get('finish'), r.get('error'), flush=True)
        if guard or r.get('error') or not r.get('done'): raise RuntimeError('LEG_FAILED %s %s %s' % (tag, guard, r.get('error')))
    time.sleep(3)
    return dict(legs=out)

def main():
    arms = json.loads((c.BD / 'arms.json').read_text()); OUT.mkdir(parents=True)
    before = {str(p): c.sha(p) for p in c.PROTECTED}; err = None; rows = []
    try:
        for i, n in enumerate(sys.argv[1:], 1):
            print('START', i, n, flush=True)
            rows.append(q.stage(OUT / ('%02d-%s' % (i, n)), n, arms[n], 0, work))
    except BaseException as e:
        err = '%s: %s' % (type(e).__name__, e); print('ERROR', err, flush=True)
    finally:
        after = {str(p): c.sha(p) for p in c.PROTECTED}
        c.dump(OUT / 'RESULT.json', dict(error=err, rows=rows, protected_changed=[p for p in before if before[p] != after[p]], final=c.snapshot(), listeners=c.listening()))
        print('FINISHED', err, flush=True)

if __name__ == '__main__':
    main()

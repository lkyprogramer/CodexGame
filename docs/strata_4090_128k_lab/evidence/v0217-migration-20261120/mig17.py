"""v0.2.17 migration pair + route tail skip on/off (2026-11-20).
Reuses the frozen v0.2.16 drivers (campaign/seqtrace/quality in /data/strata-data/v0216-baseline-20261120) unchanged; per arm only the build, terminal tree and state root change.
  seq     <ARM:S|F> ...   seqtrace legs (S = d3k c32k f10k c100k fork60 fork90, F = c100k), STRATA_SPEC_TRACE on
  quality <ARM:seed> ...  quality screen (fixed corpus + isolated-docker ledger chain)"""
import json, os, sys, time
from pathlib import Path
OLD = Path('/data/strata-data/v0216-baseline-20261120'); NEW = Path(__file__).resolve().parent
sys.path.insert(0, str(OLD))
import campaign as c, seqtrace as st, quality as q
ARMS = {
    'B1':  dict(ver='216'),                                              # v0.2.16 + port, tail skip by its default (rank 7)
    'B2':  dict(ver='217', env={'STRATA_ROUTE_TAIL_SKIP': '7'}),         # v0.2.17 + port, tail skip pinned to the B1/A0 rank
    'TS0': dict(ver='217', env={'STRATA_ROUTE_TAIL_SKIP': '0'}),         # v0.2.17 + port, tail skip off (the 0.2.17 default)
}
def use(arm):
    root = NEW if arm['ver'] == '217' else OLD
    c.BD = root; c.EXE216 = root / 'build/strata'
    for x in ('state/data', 'state/xdg-data', 'state/xdg-config', 'state/xdg-cache', 'state/draft-costs'): (root / x).mkdir(parents=True, exist_ok=True)
    return {k: v for k, v in arm.items() if k != 'ver'}

def main():
    mode, plan = sys.argv[1], [x.split(':') for x in sys.argv[2:]]
    out = NEW / 'runs' / sys.argv[0].split('/')[-1].replace('.py', '') / mode
    out.mkdir(parents=True)
    exes = {v: c.sha(r / 'build/strata') for v, r in (('216', OLD), ('217', NEW))}
    c.dump(out / 'PLAN.json', dict(mode=mode, plan=plan, arms=ARMS, engine_sha=exes, patch_sha=c.sha(NEW / 'v0216-pt0-reply-reuse.patch')))
    before = {str(p): c.sha(p) for p in c.PROTECTED}; err = None; rows = []
    c.gate(c.snapshot())
    fx = st.fixtures() if mode == 'seq' else None
    if mode == 'quality': q.chain.image_id(q.IMAGE)
    try:
        for i, (n, k) in enumerate(plan, 1):
            arm = use(ARMS[n]); print('START', i, n, k, c.BD.name, flush=True)
            if mode == 'seq':
                rows.append(st.stage(out / ('%02d-%s-%s' % (i, n, k)), n, arm, k, fx))
            else:
                r = q.stage(out / ('%02d-%s' % (i, n)), n, arm, int(k)); rows.append(r)
                print('DONE', i, n, json.dumps(dict(corpus=r['corpus'], chain=r['chain'])), flush=True)
    except BaseException as e:
        err = '%s: %s' % (type(e).__name__, e); print('ERROR', err, flush=True)
    finally:
        after = {str(p): c.sha(p) for p in c.PROTECTED}
        c.dump(out / 'RESULT.json', dict(error=err, n=len(rows), protected_changed=[p for p in before if before[p] != after[p]], final=c.snapshot(), listeners=c.listening()))
        print('FINISHED', err, flush=True)

if __name__ == '__main__':
    os.umask(0o022); main()

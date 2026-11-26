import sys, json, numpy as np
sys.path.insert(0, sys.argv[1]); import kld
def run(pf, qf):
    P, Q = kld.load(pf), kld.load(qf); nv = P["n_vocab"]; near, full = [], []
    for s in range(0, P["rec"].shape[0], 64):
        lp, lq = kld.logp(P["rec"][s:s+64], nv), kld.logp(Q["rec"][s:s+64], nv)
        m = (lp > -16) & (lq > -16)
        d = np.abs(lp - lq)
        near.append(np.where(m, d, 0).max(1))
    near = np.concatenate(near)
    return {"positions": int(near.size), "near_top_max_abs_logprob_diff": {"median": float(np.median(near)), "p90": float(np.percentile(near, 90)), "p99": float(np.percentile(near, 99)), "max": float(near.max()), "frac_gt_1": float((near > 1).mean())}}
print(json.dumps({"llama_ub512_vs_ub1": run(sys.argv[2], sys.argv[3]), "llama_ub512_vs_astral_step": run(sys.argv[2], sys.argv[4])}, indent=1))

#!/usr/bin/env python3
"""T46 evaluation loop E0 (QDA-style screening, S46). Screening only: formal gates still use the
full-vocabulary KL of T19 (logit_compare.py), num-3 and num-4L.

  cache   <teacher dir> <out.npz> [--k 2048]
      Teacher cache from Astral / llama.cpp dumps (<dir>/<name>_<L>.<kind>.f32, float32 logits):
      per position the top-k ids (int32), their log-probs and the log of the remaining mass
      (float32), 8 k + 4 bytes per position. k = 2048 (16 KiB) is the default: on the T19 dumps
      (Astral prefill vs llama.cpp single, 128 positions) the gap of the mean to the full KL is
      4.8% at k = 128, 1.8% at 512, 0.43% at 2048, 0.16% at 4096.
  kl      <cache.npz> <candidate dir> [--full <teacher dir>] [--repeat <dir>] [--out x.json]
      Top-k + tail-bucket KL(P || Q) per position: sum_top p (lp - lq) + p_tail (lp_tail - lq_tail),
      with q_tail = 1 - sum_top q. By the log-sum inequality it never exceeds the full KL, so it
      is a lower bound. --full also computes the full-vocabulary KL (float64, as logit_compare.py)
      and the relative gap of the means; --repeat gives the noise band: the same statistic for a
      repeat of the teacher (same config run twice).
  gencheck <generations.jsonl> [--max-tokens N] [--eos ID ...]
      Long-generation checks per record ({"name", "ids"} or {"name", "tokens"}): truncated (hit
      max tokens without an EOS id) and repetition (the tail is one period p <= 64 repeated so
      that it covers >= 96 tokens, at least 3 periods).

Exit codes: 0 ok, 1 gate failed (kl --gate), 2 incomplete / invalid input.
"""
import argparse
import glob
import json
import os
import re
import sys

import numpy as np

NAME = re.compile(r"^(?P<name>.+)_(?P<len>\d+)\.(?P<kind>[a-z]+)\.f32$")


def dumps(d):
    out = {}
    for p in sorted(glob.glob(os.path.join(d, "*.f32"))):
        m = NAME.match(os.path.basename(p))
        if m:
            out[(m["name"], int(m["len"]), m["kind"])] = p
    return out


def read(p):
    return np.fromfile(p, dtype="<f4").astype(np.float64)


def log_softmax(z):
    m = z.max()
    return z - (m + np.log(np.exp(z - m).sum()))


def log1mexp(lse):
    """log(1 - exp(lse)) for lse <= 0, stable."""
    lse = min(lse, 0.0)
    return np.log(-np.expm1(lse)) if lse > -0.693 else np.log1p(-np.exp(lse))


def top_entry(z, k):
    lp = log_softmax(z)
    ids = np.argpartition(-lp, k - 1)[:k]
    ids = ids[np.argsort(-lp[ids], kind="stable")]
    tl = lp[ids]
    lse = np.logaddexp.reduce(tl)
    return ids.astype(np.int32), tl.astype(np.float32), np.float32(log1mexp(lse))


def kl_top(ids, tlp, ttail, zq):
    """Top-k + tail bucket KL of teacher entry (ids, tlp, ttail) against candidate logits."""
    lq = log_softmax(zq)
    p = np.exp(tlp.astype(np.float64))
    lqt = lq[ids]
    kl = float((p * (tlp - lqt)).sum())
    pt = float(np.exp(ttail))
    if pt > 0:
        qtail = log1mexp(np.logaddexp.reduce(lqt))
        kl += pt * (float(ttail) - qtail)
    return max(kl, 0.0)


def kl_full(zp, zq):
    lp, lq = log_softmax(zp), log_softmax(zq)
    return max(float((np.exp(lp) * (lp - lq)).sum()), 0.0)


def cmd_cache(a):
    ds = dumps(a.teacher)
    if not ds:
        print("no dumps in", a.teacher, file=sys.stderr)
        return 2
    keys = sorted(ds)
    ids, tlp, tail, vocab = [], [], [], None
    for key in keys:
        z = read(ds[key])
        if not np.isfinite(z).all():
            print("non-finite teacher logits", ds[key], file=sys.stderr)
            return 2
        vocab = vocab or z.size
        if z.size != vocab:
            print("vocab mismatch", ds[key], file=sys.stderr)
            return 2
        i, t, r = top_entry(z, a.k)
        ids.append(i); tlp.append(t); tail.append(r)
    np.savez(a.out, keys=np.array(["%s_%d.%s" % k for k in keys]), ids=np.stack(ids), lp=np.stack(tlp), tail=np.array(tail, dtype=np.float32), vocab=vocab, k=a.k)
    print(json.dumps({"positions": len(keys), "k": a.k, "vocab": vocab, "bytes_per_position": a.k * 8 + 4}))
    return 0


def stats(v):
    v = np.asarray(v, dtype=np.float64)
    return {"n": int(v.size), "mean": float(v.mean()), "median": float(np.median(v)), "p90": float(np.percentile(v, 90)), "max": float(v.max())} if v.size else {"n": 0}


def cmd_kl(a):
    c = np.load(a.cache)
    keys = [str(k) for k in c["keys"]]
    cand = {"%s_%d.%s" % k: p for k, p in dumps(a.candidate).items()}
    full = {"%s_%d.%s" % k: p for k, p in dumps(a.full).items()} if a.full else {}
    rep = {"%s_%d.%s" % k: p for k, p in dumps(a.repeat).items()} if a.repeat else {}
    missing = [k for k in keys if k not in cand or (a.full and k not in full) or (a.repeat and k not in rep)]
    if missing:
        print("missing positions:", missing[:5], "... (%d)" % len(missing), file=sys.stderr)
        return 2
    rows = []
    for i, k in enumerate(keys):
        zq = read(cand[k])
        if zq.size != int(c["vocab"]) or not np.isfinite(zq).all():
            print("bad candidate logits", cand[k], file=sys.stderr)
            return 2
        r = {"key": k, "kl_top": kl_top(c["ids"][i], c["lp"][i], c["tail"][i], zq)}
        if full:
            r["kl_full"] = kl_full(read(full[k]), zq)
        if rep:
            r["kl_top_repeat"] = kl_top(c["ids"][i], c["lp"][i], c["tail"][i], read(rep[k]))
        rows.append(r)
    out = {"cache": a.cache, "candidate": a.candidate, "k": int(c["k"]), "kl_top": stats([r["kl_top"] for r in rows])}
    if full:
        out["kl_full"] = stats([r["kl_full"] for r in rows])
        # float32 cache entries: allow their rounding (about 1e-7 per log-prob)
        bound_ok = all(r["kl_top"] <= r["kl_full"] * (1 + 1e-4) + 1e-6 for r in rows)
        mf = out["kl_full"]["mean"]
        out["lower_bound_holds"] = bound_ok
        out["rel_gap_mean"] = (mf - out["kl_top"]["mean"]) / mf if mf > 0 else 0.0
    if rep:
        out["noise_band"] = stats([r["kl_top_repeat"] for r in rows])
        out["above_noise_max"] = out["kl_top"]["mean"] > out["noise_band"]["max"]
    out["rows"] = rows
    s = json.dumps(out, indent=1)
    if a.out:
        open(a.out, "w").write(s)
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
    if a.gate is not None and full:
        return 0 if out["lower_bound_holds"] and out["rel_gap_mean"] < a.gate else 1
    return 0


def repetition(ids, pmax=64, cover=96, min_rep=3):
    """(period, covered tokens) of the longest periodic tail, or None."""
    n = len(ids)
    best = None
    for p in range(1, min(pmax, n // min_rep) + 1):
        j = n - 1
        while j - p >= 0 and ids[j] == ids[j - p]:
            j -= 1
        covered = n - 1 - j + p
        if covered >= max(cover, min_rep * p) and (best is None or covered > best[1]):
            best = (p, covered)
    return best


def cmd_gencheck(a):
    recs = [json.loads(l) for l in open(a.gens) if l.strip()]
    if not recs:
        return 2
    eos = set(a.eos or [])
    out, nt, nr = [], 0, 0
    for r in recs:
        ids = r.get("ids") or r.get("tokens") or []
        trunc = a.max_tokens is not None and len(ids) >= a.max_tokens and not (eos & set(ids))
        rep = repetition(ids)
        nt += trunc; nr += rep is not None
        out.append({"name": r.get("name"), "n": len(ids), "truncated": bool(trunc), "repeat_period": rep and rep[0], "repeat_tokens": rep and rep[1]})
    print(json.dumps({"records": len(recs), "truncated": nt, "repetitive": nr, "truncation_rate": nt / len(recs), "repetition_rate": nr / len(recs), "rows": out}, indent=1))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("cache"); p.add_argument("teacher"); p.add_argument("out"); p.add_argument("--k", type=int, default=2048)
    p = sp.add_parser("kl"); p.add_argument("cache"); p.add_argument("candidate"); p.add_argument("--full"); p.add_argument("--repeat"); p.add_argument("--out"); p.add_argument("--gate", type=float)
    p = sp.add_parser("gencheck"); p.add_argument("gens"); p.add_argument("--max-tokens", type=int); p.add_argument("--eos", type=int, nargs="*")
    a = ap.parse_args(argv)
    return {"cache": cmd_cache, "kl": cmd_kl, "gencheck": cmd_gencheck}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())

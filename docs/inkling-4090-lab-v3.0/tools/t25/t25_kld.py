#!/usr/bin/env python3
"""T25: dense position-by-position comparison of logit sources on one token sequence.

  t25_kld.py <out.json> <pair>...      pair = REF=CAND, each a source:
     bin:<path>                   KL-divergence-base file (llama t25_dense, astral dump-logits);
                                  the first scored position follows from the record count
     f32:<dir>:<name>:<kind>      <dir>/<name>_<L>.<kind>.f32 (raw logits after L tokens = position L-1)
f32 logits are passed through the same u16 encoding, so every source is compared on the
file format's log-probs (llama.cpp's KL: sum over the reference's log-probs above -16).
Per pair: positions both sides have, KL mean / percentiles / max, top-1 agreement (all, and
where the reference margin >= 0.5), every flip with its reference margin, KL and gap; per-position
arrays (KL, agreement, reference margin, both argmaxes) go to <out>.<i>.npz.
"""
import glob, json, os, re, sys
import numpy as np


class Bin:
    def __init__(self, path):
        with open(path, "rb") as f:
            assert f.read(8) == b"_logits_", path
            n, nv, nc = (int(x) for x in np.frombuffer(f.read(12), dtype="<i4"))
        assert nc == 1, "one chunk expected"
        self.n, self.nv = n, nv
        self.tok = np.memmap(path, dtype="<i4", mode="r", offset=20, shape=(n,))
        self.w = 2 * ((nv + 1) // 2) + 4
        nrec = (os.path.getsize(path) - 20 - 4 * n) // (2 * self.w)
        self.first = n - 1 - nrec
        self.rec = np.memmap(path, dtype="<u2", mode="r", offset=20 + 4 * n, shape=(nrec, self.w))
        self.pos = np.arange(self.first, n - 1)

    def logp(self, ps):
        r = self.rec[np.asarray(ps) - self.first]
        hdr = np.ascontiguousarray(r[:, :4]).view("<f4")
        return hdr[:, :1].astype(np.float64) * r[:, 4:4 + self.nv].astype(np.float64) + hdr[:, 1:2]


def encode_decode(l):
    l = l.astype(np.float32)
    mx, mn = l.max(), l.min()
    mn = max(mn, mx - np.float32(16))
    lse = np.float32(np.log(np.exp((l - mx).astype(np.float64)).sum()))
    mlp = np.float32(mn - mx - lse)
    scale = np.float32((mx - mn) / np.float32(65535))
    if scale == 0:
        return np.full(l.shape, mlp, np.float64)
    q = np.where(l > mn, np.rint(np.float32(1) / scale * (l - mn)), 0)
    return np.float64(scale) * q + np.float64(mlp)


class F32:
    def __init__(self, spec):
        d, self.name, self.kind = spec.split(":")
        self.files = {}
        for f in glob.glob(os.path.join(d, "%s_*.%s.f32" % (self.name, self.kind))):
            m = re.search(r"_(\d+)\.%s\.f32$" % re.escape(self.kind), f)
            self.files[int(m.group(1)) - 1] = f
        self.pos = np.array(sorted(self.files))
        self.tok = None

    def logp(self, ps):
        return np.stack([encode_decode(np.fromfile(self.files[p], dtype="<f4")) for p in ps])


def src(s):
    k, rest = s.split(":", 1)
    return Bin(rest) if k == "bin" else F32(rest)


def compare(a, b):
    ps = np.intersect1d(a.pos, b.pos)
    assert ps.size, "no common positions"
    kl, ag, mr, mc, gap, ar, ac, bad = [], [], [], [], [], [], [], 0
    for s in range(0, ps.size, 64):
        q = ps[s:s + 64]
        lp, lq = a.logp(q), b.logp(q)
        nv = min(lp.shape[1], lq.shape[1])
        lp, lq = lp[:, :nv], lq[:, :nv]
        bad += int((~np.isfinite(lp)).any(1).sum() + (~np.isfinite(lq)).any(1).sum())
        m = lp > -16
        kl.append(np.where(m, np.exp(lp) * (lp - lq), 0).sum(1))
        ia, ib = lp.argmax(1), lq.argmax(1)
        ag.append(ia == ib)
        ar.append(ia)
        ac.append(ib)
        t2 = np.sort(np.partition(lp, -2, axis=1)[:, -2:], axis=1)
        mr.append(t2[:, 1] - t2[:, 0])
        u2 = np.sort(np.partition(lq, -2, axis=1)[:, -2:], axis=1)
        mc.append(u2[:, 1] - u2[:, 0])
        r = np.arange(len(q))
        gap.append(lp[r, ia] - lp[r, ib])
    kl, ag, mr, mc, gap, ar, ac = (np.concatenate(x) for x in (kl, ag, mr, mc, gap, ar, ac))
    hi = mr >= 0.5
    flips = [{"pos": int(ps[i]), "len": int(ps[i]) + 1, "ref_margin": round(float(mr[i]), 4), "cand_margin": round(float(mc[i]), 4),
              "kl": round(float(kl[i]), 5), "gap": round(float(gap[i]), 4)} for i in np.where(~ag)[0]]
    pct = lambda p: float(np.percentile(kl, p))
    return ps, kl, ag, mr, (ar, ac), {
        "positions": int(ps.size), "nonfinite_rows": bad, "first": int(ps[0]), "last": int(ps[-1]),
        "kl_mean": float(kl.mean()), "kl_p50": pct(50), "kl_p90": pct(90), "kl_p99": pct(99), "kl_p999": pct(99.9), "kl_max": float(kl.max()),
        "kl_max_pos": int(ps[kl.argmax()]), "top1": float(ag.mean()), "n_margin_ge_0.5": int(hi.sum()),
        "top1_margin_ge_0.5": float(ag[hi].mean()) if hi.any() else None, "flips": flips,
        "flips_margin_ge_0.5": sum(f["ref_margin"] >= 0.5 for f in flips)}


def main():
    out, pairs = sys.argv[1], sys.argv[2:]
    cache, res = {}, {}
    for i, p in enumerate(pairs):
        r, c = p.split("=", 1)
        a, b = (cache.setdefault(x, src(x)) for x in (r, c))
        if a.tok is not None and b.tok is not None:
            assert np.array_equal(a.tok, b.tok), "token streams differ: " + p
        ps, kl, ag, mr, (ar, ac), s = compare(a, b)
        np.savez_compressed("%s.%d.npz" % (out, i), pos=ps, kl=kl, agree=ag, ref_margin=mr, ref_arg=ar, cand_arg=ac)
        s["pair"] = p
        res[str(i)] = s
        print(i, p.split("/")[-1][:60], "n", s["positions"], "mean %.5f p99 %.4f max %.3f top1@0.5 %s flips@0.5 %d" % (s["kl_mean"], s["kl_p99"], s["kl_max"], s["top1_margin_ge_0.5"], s["flips_margin_ge_0.5"]), flush=True)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()

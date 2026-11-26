"""Compare two llama.cpp --kl-divergence-base files position by position.
P = reference (first file), Q = candidate. KL(P||Q) over P's log-probs > -16 (as llama.cpp)."""
import json, sys
import numpy as np

def load(path):
    with open(path, "rb") as f:
        assert f.read(8) == b"_logits_", path
        n_ctx, n_vocab, n_chunk = np.frombuffer(f.read(12), dtype="<i4")
    n_ctx, n_vocab, n_chunk = int(n_ctx), int(n_vocab), int(n_chunk)
    tok = np.memmap(path, dtype="<i4", mode="r", offset=20, shape=(n_chunk * n_ctx,))
    first = n_ctx // 2
    nrec = n_chunk * (n_ctx - 1 - first)
    nv = 2 * ((n_vocab + 1) // 2) + 4
    rec = np.memmap(path, dtype="<u2", mode="r", offset=20 + 4 * n_chunk * n_ctx, shape=(nrec, nv))
    return dict(n_ctx=n_ctx, n_vocab=n_vocab, n_chunk=n_chunk, first=first, tok=tok, rec=rec)

def logp(rows, n_vocab):
    hdr = np.ascontiguousarray(rows[:, :4]).view("<f4")      # scale, min_log_prob
    return hdr[:, :1] * rows[:, 4:4 + n_vocab].astype(np.float32) + hdr[:, 1:2]

def main(pf, qf, margin_min=0.5):
    P, Q = load(pf), load(qf)
    for k in ("n_ctx", "n_vocab", "n_chunk"):
        assert P[k] == Q[k], (k, P[k], Q[k])
    assert np.array_equal(P["tok"], Q["tok"]), "token streams differ"
    nv, per = P["n_vocab"], P["n_ctx"] - 1 - P["first"]
    kld, margin, agree, nllp, nllq = [], [], [], [], []
    for s in range(0, P["rec"].shape[0], 64):
        lp, lq = logp(P["rec"][s:s + 64], nv), logp(Q["rec"][s:s + 64], nv)
        m = lp > -16
        kld.append(np.where(m, np.exp(lp) * (lp - lq), 0).sum(1))
        top2 = np.partition(lp, -2, axis=1)[:, -2:]
        margin.append(top2[:, 1] - top2[:, 0])
        agree.append(lp.argmax(1) == lq.argmax(1))
        idx = np.arange(s, s + lp.shape[0])
        tgt = np.array([P["tok"][(i // per) * P["n_ctx"] + P["first"] + i % per + 1] for i in idx])
        nllp.append(-lp[np.arange(len(idx)), tgt]); nllq.append(-lq[np.arange(len(idx)), tgt])
    kld, margin, agree = np.concatenate(kld), np.concatenate(margin), np.concatenate(agree)
    nllp, nllq = np.concatenate(nllp), np.concatenate(nllq)
    hi = margin >= margin_min
    dis = np.where(~agree)[0]
    out = {
        "p": pf, "q": qf, "positions": int(kld.size),
        "kld_mean": float(kld.mean()), "kld_median": float(np.median(kld)),
        "kld_p90": float(np.percentile(kld, 90)), "kld_p99": float(np.percentile(kld, 99)),
        "kld_p999": float(np.percentile(kld, 99.9)), "kld_max": float(kld.max()),
        "top1_agree": float(agree.mean()),
        "top1_agree_margin_ge_%.1f" % margin_min: float(agree[hi].mean()) if hi.any() else None,
        "n_margin_ge": int(hi.sum()),
        "disagree": [{"pos": int(i), "ref_margin": round(float(margin[i]), 4)} for i in dis],
        "ppl_p": float(np.exp(nllp.mean())), "ppl_q": float(np.exp(nllq.mean())),
    }
    print(json.dumps(out, indent=1))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

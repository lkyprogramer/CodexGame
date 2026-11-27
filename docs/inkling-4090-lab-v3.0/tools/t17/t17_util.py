#!/usr/bin/env python3
"""T17 helpers.

  t17_util.py manifests <ids.json> <out dir>       manifests of the 8K ring checks and the long levels
  t17_util.py base <ids.json> <ref base> <n_ctx> <out>
        token-only llama.cpp logits header (n_vocab copied from <ref base>) over the
        n_ctx corpus tokens ending at token 131072, so every level scores the same last tokens
  t17_util.py ppl <astral dump> [last]             perplexity of all scored positions, and of the last <last>
  t17_util.py rows <verify tsv>                    histogram of the verify row that produced each length
  t17_util.py needle <url> <corpus.txt> <ids.json> <tokens> <depth> <key>
        chat request with a pass key sentence at <depth> (0..1) of about <tokens> tokens of corpus
        text; prints JSON {prompt_tokens, answer, found}
"""
import json
import os
import sys

import numpy as np

T_END = 131072


def ids_of(path):
    return json.load(open(path))


def manifests(ids_path, out):
    ids = ids_of(ids_path)
    if len(ids) < T_END:
        sys.exit("corpus has %d tokens, need %d" % (len(ids), T_END))
    os.makedirs(out, exist_ok=True)

    def w(name, rows):
        with open(os.path.join(out, name), "w") as f:
            for n, lens, seq in rows:
                assert lens == sorted(set(lens)) and lens[-1] <= len(seq), (n, lens)
                f.write("%s\t%s\t%s\n" % (n, ",".join(map(str, lens)), " ".join(map(str, seq))))

    s0 = ids[:8300]
    # Lengths around the window (1024), the ring of the default 2048-token chunk (3072 rows),
    # the prefill chunk (2048) and the old capacity limit; the old binary takes up to 8184.
    l8 = [1, 2, 8, 9, 64, 65, 1023, 1024, 1025, 1087, 1088, 1089, 2047, 2048, 2049, 3071, 3072, 3073, 3074, 4096, 4097, 6143, 6144, 6145, 8183, 8184]
    s1 = ids[60000:65000]
    w("m8.tsv", [("s0", l8, s0), ("s0p", [1500], s0), ("s1", [1500, 3500, 5000], s1)])
    w("m8_fresh.tsv", [("s0p", [1500], s0)])
    w("m8_edge.tsv", [("e0", [8183, 8191, 8192, 8193], s0)])
    # ASTRAL_TMAX=1 gives a ring of 1088 rows: lengths around its wrap; 777 gives 1856.
    w("m8_tmax.tsv", [("t0", [1023, 1024, 1025, 1087, 1088, 1089, 1090, 1855, 1856, 1857, 2200], s0)])
    lv = [4000] + list(range(4001, 4017)) + [4032, 4064, 4096, 4128]
    w("v8.tsv", [("v0", lv, ids[:4300]), ("v1", [3100] + list(range(3101, 3117)) + [3132, 3164], ids[70000:73300])])
    w("tr8.tsv", [("r0", [1025, 3073, 3074, 8193], s0)])
    for c in (16384, 32768, 65536, 131072):
        k = c // 1024
        w("tr%dk.tsv" % k, [("r%dk" % k, [c], ids[:c])])
        w("lf%dk.tsv" % k, [("l%dk" % k, [c - 64, c - 63, c], ids[:c])])
    print("manifests in", out)


def base(ids_path, ref, n_ctx, out):
    ids = ids_of(ids_path)
    n_ctx = int(n_ctx)
    with open(ref, "rb") as f:
        assert f.read(8) == b"_logits_"
        _, n_vocab, _ = np.frombuffer(f.read(12), dtype="<i4")
    toks = np.array(ids[T_END - n_ctx:T_END], dtype="<i4")
    with open(out, "wb") as f:
        f.write(b"_logits_")
        f.write(np.array([n_ctx, int(n_vocab), 1], dtype="<i4").tobytes())
        f.write(toks.tobytes())


def ppl(dump, last=4095):
    sys.path.insert(0, os.environ["BC"])
    import kld_compare as K
    Q = K.load(dump)
    nv, per = Q["n_vocab"], Q["n_ctx"] - 1 - Q["first"]
    nll = []
    for s in range(0, Q["rec"].shape[0], 64):
        lq = K.logp(Q["rec"][s:s + 64], nv)
        idx = np.arange(s, s + lq.shape[0])
        tgt = np.array([Q["tok"][(i // per) * Q["n_ctx"] + Q["first"] + i % per + 1] for i in idx])
        nll.append(-lq[np.arange(len(idx)), tgt])
    nll = np.concatenate(nll)
    last = int(last)
    print(json.dumps({"n_ctx": Q["n_ctx"], "positions": int(nll.size), "ppl": float(np.exp(nll.mean())), "last": last, "ppl_last": float(np.exp(nll[-last:].mean()))}))


def rows(tsv):
    h = {}
    for line in open(tsv):
        p = line.split()
        if len(p) >= 4 and p[2].isdigit():
            h[int(p[2])] = h.get(int(p[2]), 0) + 1
    print(json.dumps({"row_histogram": dict(sorted(h.items()))}))


def needle(url, corpus, ids_path, tokens, depth, key):
    import urllib.request
    text = open(corpus, encoding="utf-8").read()
    ntok = len(ids_of(ids_path))
    chars = int(int(tokens) * len(text) / ntok * 0.97)
    def build(chars):
        hay = text[:chars]
        at = hay.rfind("\n", 0, int(len(hay) * float(depth))) + 1
        doc = hay[:at] + "\nThe secret pass key is %s. Remember it.\n" % key + hay[at:]
        return doc + "\n\nWhat is the secret pass key mentioned in the text above? Answer with the number only."

    def count(q):
        req = urllib.request.Request(url + "/tokenize", data=json.dumps({"messages": [{"role": "user", "content": q}]}).encode(),
                                     headers={"Content-Type": "application/json"})
        return len(json.load(urllib.request.urlopen(req))["tokens"])

    q = build(chars)
    for _ in range(4):   # fit the prompt to the target length (the corpus mixes prose and code)
        n = count(q)
        if int(tokens) * 0.98 <= n <= int(tokens):
            break
        chars = int(chars * int(tokens) / n * 0.995)
        q = build(chars)
    # Effort "none" and room for the short reasoning the model still writes: at the server's
    # default effort (0.9) a short max_tokens ends inside the reasoning. Found = key in either part.
    body = {"model": "inkling", "messages": [{"role": "user", "content": q}], "max_tokens": 256, "temperature": 0, "reasoning_effort": "none"}
    req = urllib.request.Request(url + "/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=3600))
    msg = r["choices"][0]["message"]
    ans = (msg.get("content") or "") + " " + (msg.get("reasoning_content") or "")
    print(json.dumps({"tokens_target": int(tokens), "depth": float(depth), "prompt_tokens": r.get("usage", {}).get("prompt_tokens"),
                      "answer": (msg.get("content") or "")[:80], "reasoning": (msg.get("reasoning_content") or "")[:80], "found": key in ans}))


if __name__ == "__main__":
    cmd, a = sys.argv[1], sys.argv[2:]
    {"manifests": manifests, "base": base, "ppl": ppl, "rows": rows, "needle": needle}[cmd](*a)

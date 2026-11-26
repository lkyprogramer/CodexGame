"""V5/V6/V7 verdicts from astral score / cmp-prefill outputs against the llama.cpp reference."""
import json, re, sys
d = sys.argv[1]
ref = json.load(open(f"{d}/ref.json"))
rows, v5_ok, v6_ok, v7_ok = [], True, True, True
for r in ref:
    i, plen = r["i"], r["plen"]
    txt = open(f"{d}/score_{i:02d}.txt").read()
    # Compare Astral's argmax with llama.cpp's raw argmax (ref_top1), not the sampled token: the
    # reference ran with ignore_eos, which replaces a predicted EOG token with the runner-up.
    pos = [(int(m[1]), int(m[2]), float(m[3])) for m in re.finditer(r"pos\s+(\d+)\s+next\s+(\d+)\s+want\s+\d+\s+(?:XX|  )\s+margin ([\d.]+)", txt)]
    gen_pos = [(p, nxt != r["ref_top1"][p - (plen - 1)], am) for p, nxt, am in pos if p >= plen - 1]
    eog_forced = sum(1 for a, b in zip(r["gen"], r["ref_top1"]) if a != b)
    bad = [(p - (plen - 1), am, r["ref_margin"][p - (plen - 1)]) for p, b, am in gen_pos if b]
    first = bad[0] if bad else None
    v5 = first is None or first[0] >= 128 or (first[2] is not None and first[2] < 0.5)
    v6 = all(max(am, rm if rm is not None else 0) <= 1.0 for _, am, rm in bad)
    c = open(f"{d}/cmp_{i:02d}.txt").read()
    m = re.search(r"max \|logit diff\| ([\d.]+); argmax step \((\d+), [^)]*\) prefill \((\d+),", c)
    nd = re.search(r"near-top max \|diff\| ([\d.]+) at (\d+) \(step ([-\d.]+) prefill ([-\d.]+)\); largest at (\d+) \(step ([-\d.]+) prefill ([-\d.]+)\); KL\(step\|\|prefill\) ([-\d.e+]+)", c)
    v7 = bool(m) and m[2] == m[3] and float(m[1]) <= 1.0
    v5_ok &= v5; v6_ok &= v6; v7_ok &= v7
    rows.append({"i": i, "plen": plen, "n_gen_checked": len(gen_pos), "ignore_eos_forced": eog_forced, "disagree": [{"gen_pos": g, "astral_margin": a, "ref_margin": None if rm is None else round(rm, 3)} for g, a, rm in bad],
                 "v5_first_div": None if first is None else first[0], "v5": v5, "v6": v6,
                 "v7_max_diff": float(m[1]) if m else None, "v7_diag": nd.group(0) if nd else None, "v7": v7})
print(json.dumps({"V5": v5_ok, "V6": v6_ok, "V7": v7_ok, "rows": rows}, indent=1))

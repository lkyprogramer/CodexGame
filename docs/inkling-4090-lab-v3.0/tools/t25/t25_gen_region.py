
import json, glob, os, sys, numpy as np
d = sys.argv[1]
tot = {}
for c in sorted(glob.glob(d + "/e[0-9].json")):
    name = os.path.basename(c)[:-5]
    L = json.load(open(d + "/" + name + "/lens.json"))
    for k in ("0", "1", "2", "3", "8", "9"):
        z = np.load("%s.%s.npz" % (c, k)); g = z["pos"] >= L["prompt_len"] - 1
        a = tot.setdefault(k, [[], 0, 0])
        a[0].append(z["kl"][g]); a[1] += int((~z["agree"][g] & (z["ref_margin"][g] >= 0.5)).sum()); a[2] += int((~z["agree"][g]).sum())
for k, (kl, f5, f) in tot.items():
    kl = np.concatenate(kl); print(k, "n", kl.size, "mean %.5f p90 %.5f p99 %.4f max %.4f flips %d flips@0.5 %d" % (kl.mean(), np.percentile(kl, 90), np.percentile(kl, 99), kl.max(), f, f5))

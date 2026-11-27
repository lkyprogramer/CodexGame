#!/usr/bin/env python3
"""Per decode step GPU time by kernel (and grid / block) from an nsys sqlite export: drops the
prefill (up to the last prefill kernel) and the first two decode steps. usage: t16_kernels.py <sqlite>"""
import sqlite3, sys, collections
f = sys.argv[1]
db = sqlite3.connect(f)
rows = db.execute("SELECT s.value, k.start, k.end, k.gridX, k.gridY, k.gridZ, k.blockX FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON k.shortName = s.id ORDER BY k.start").fetchall()
last_pf = max(i for i, r in enumerate(rows) if r[0] in ("astral_gemm_nvfp4_mma3", "astral_gemm_q8_0_mma3", "astral_ink_attn_prefill"))
dec = rows[last_pf + 1:]
# drop the first decode step (capture / warm-up): start after the first 2 * per-step kernels
steps = sum(1 for r in dec if r[0] == "astral_ink_attn_split1") / 48
per = len(dec) / steps
dec = dec[int(2 * per):]
steps = sum(1 for r in dec if r[0] == "astral_ink_attn_split1") / 48
busy = sum(r[2] - r[1] for r in dec); span = dec[-1][2] - dec[0][1]
print("decode steps %.1f, kernels per step %.1f, busy %.3f ms/step, span %.3f ms/step (%.1f%% busy)" % (steps, len(dec) / steps, busy / steps / 1e6, span / steps / 1e6, 100 * busy / span))
agg = collections.defaultdict(lambda: [0, 0])
for r in dec:
    key = (r[0], r[3], r[4], r[5], r[6])
    agg[key][0] += 1; agg[key][1] += r[2] - r[1]
print("share  us/step  per-step  avg_us  kernel grid block")
for (name, gx, gy, gz, bx), (n, t) in sorted(agg.items(), key=lambda x: -x[1][1])[:30]:
    print("%5.1f%% %7.1f %6.1f %8.2f  %s (%d,%d,%d) %d" % (100 * t / busy, t / steps / 1e3, n / steps, t / n / 1e3, name, gx, gy, gz, bx))

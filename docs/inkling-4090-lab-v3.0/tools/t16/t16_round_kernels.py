#!/usr/bin/env python3
"""GPU kernel time per speculative round from an nsys sqlite export, by kernel name, grid and
block. usage: t16_round_kernels.py <sqlite> <rounds>"""
import collections
import sqlite3
import sys

db = sqlite3.connect(sys.argv[1])
rounds = int(sys.argv[2])
names = dict(db.execute("select id, value from StringIds"))
rows = db.execute("select start, end, shortName, gridX, gridY, gridZ, blockX from CUPTI_ACTIVITY_KIND_KERNEL order by start").fetchall()
agg = collections.defaultdict(lambda: [0, 0])
for s, e, n, gx, gy, gz, bx in rows:
    key = "%s (%d,%d,%d) %d" % (names[n], gx, gy, gz, bx)
    agg[key][0] += e - s
    agg[key][1] += 1
tot = sum(v[0] for v in agg.values())
print("rounds %d, kernels %d, GPU busy %.2f ms/round, span %.2f ms/round" % (rounds, len(rows), tot / rounds / 1e6, (rows[-1][1] - rows[0][0]) / rounds / 1e6))
for k, v in sorted(agg.items(), key=lambda x: -x[1][0])[:22]:
    print("%5.1f%% %8.1f us/round %6.1f/round  %s" % (100 * v[0] / tot, v[0] / rounds / 1e3, v[1] / rounds, k))

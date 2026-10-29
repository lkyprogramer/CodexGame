"""Window-weighted decode cost per arm of one or more cfg campaigns: ms/window, CPU-expert entries per layer-window,
adaptive wait / join (ms/window), swaps/window.  Calls of fewer than 20 windows are skipped.
  python adapt_cost.py <campaign dir>...
"""
import re, glob, collections, sys
R = re.compile(r"decode timing: (\d+) windows.*? ([\d.]+) ms/window.*?CPU experts ([\d.]+) \(([\d.]+) entries\), "
               r"VRAM hits ([\d.]+), PCIe ([\d.]+); adapt wait ([\d.]+) join ([\d.]+), ([\d.]+) swaps/window")
SLOTS = re.compile(r"expert cache (\d+) slots")
HIT = re.compile(r"decode expert cache hit rate: ([\d.]+)% \((\d+) hits / (\d+) lookups\)")
for d in sys.argv[1:]:
    for arm in ("base", "cfg"):
        s = collections.Counter(); slots = set(); hits = lookups = 0
        for f in sorted(glob.glob(f"{d}/round-*-{arm}/engine.log")):
            last = None
            for l in open(f, errors="replace"):
                if (m := SLOTS.search(l)): slots.add(int(m.group(1)))
                if (m := HIT.search(l)): last = (int(m.group(2)), int(m.group(3)))
                m = R.search(l)
                if not m or int(m.group(1)) < 20: continue
                w = int(m.group(1)); s["w"] += w
                for i, k in ((2, "ms"), (4, "cpu_entries"), (6, "pcie"), (7, "wait"), (8, "join"), (9, "swaps")):
                    s[k] += w * float(m.group(i))
            if last: hits += last[0]; lookups += last[1]
        if not s["w"]: continue
        vals = " ".join("%s=%.3f" % (k, v / s["w"]) for k, v in s.items() if k != "w")
        print(d.rstrip("/").split("/")[-1], arm, vals, "windows=%d" % s["w"], "slots=%s" % sorted(slots),
              "hit=%.2f%%" % (100.0 * hits / lookups if lookups else 0))

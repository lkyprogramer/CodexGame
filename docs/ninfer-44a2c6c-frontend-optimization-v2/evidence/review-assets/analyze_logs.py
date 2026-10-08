"""Reproduce the schema-20 request-log figures used in the frontend-optimization review.

Usage: python3 analyze_logs.py LOG_DIR
LOG_DIR holds ninfer-request.jsonl* copied from /home/hhtele/ninfer-4090/logs (metadata only).
"""
import collections
import datetime as dt
import glob
import json
import sys

EDT = dt.timedelta(hours=-4)
BINS = [("<8K", 0, 8192), ("8-32K", 8192, 32768), ("32-64K", 32768, 65536),
        ("64-120K", 65536, 120000), ("120-185K", 120000, 185000), (">185K", 185000, 10**9)]


def get(record, *keys):
    node = record
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def edt(ms):
    return (dt.datetime.fromtimestamp(ms / 1000, dt.UTC) + EDT).strftime("%Y-%m-%d %H:%M:%S")


def p50(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return float("nan")
    k = (len(values) - 1) * 0.5
    lo = int(k)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def load(log_dir):
    events = []
    for path in sorted(glob.glob(f"{log_dir}/ninfer-request.jsonl*")):
        with open(path) as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("schema_version") == 20:
                    events.append(record)
    events.sort(key=lambda r: r["timestamp_unix_ms"])
    return events


def bucket_table(done, title):
    print(f"== {title} (n={len(done)})")
    for name, lo, hi in BINS:
        sel = [r for r in done if lo <= get(r, "result", "prompt_tokens") < hi]
        if not sel:
            continue
        hit = p50([get(r, "result", "prefix_cache_hit_tokens") / get(r, "result", "prompt_tokens") for r in sel])
        print(f"  {name:9} n={len(sel):4d} hit={hit:.3f} "
              f"tokenize={p50([get(r, 'prepare_detail', 'tokenize') for r in sel]):6.2f}s "
              f"render={1000 * p50([get(r, 'prepare_detail', 'template_render') for r in sel]):5.1f}ms "
              f"prefill={p50([get(r, 'timings_seconds', 'prefill') for r in sel]):5.2f}s "
              f"ttft={p50([get(r, 'timings_seconds', 'ttft') for r in sel]):6.2f}s "
              f"rendered_KB={p50([get(r, 'request', 'rendered_chars') for r in sel]) / 1000:5.0f} "
              f"messages={p50([get(r, 'request', 'message_count') for r in sel]):4.0f}")


def long_segments(done):
    segments, current = [], []
    for record in done:
        tokens = get(record, "result", "prompt_tokens")
        if tokens < 32768:
            continue
        if current:
            gap = (record["timestamp_unix_ms"] - current[-1]["timestamp_unix_ms"]) / 1000
            if gap > 1800 or tokens < 0.6 * get(current[-1], "result", "prompt_tokens"):
                segments.append(current)
                current = []
        current.append(record)
    if current:
        segments.append(current)
    totals = collections.Counter()
    print("== long (>=32K) segments with >=10 requests")
    for seg in segments:
        if len(seg) < 10:
            continue
        span = (seg[-1]["timestamp_unix_ms"] - seg[0]["timestamp_unix_ms"]) / 1000 + get(seg[-1], "timings_seconds", "total")
        busy = sum(get(r, "timings_seconds", "total") for r in seg)
        tok = sum(get(r, "prepare_detail", "tokenize") for r in seg)
        dec = sum(get(r, "timings_seconds", "decode") for r in seg)
        pre = sum(get(r, "timings_seconds", "prefill") for r in seg)
        print(f"  {edt(seg[0]['timestamp_unix_ms'])[5:16]}..{edt(seg[-1]['timestamp_unix_ms'])[5:16]} n={len(seg):3d} "
              f"K={get(seg[0], 'result', 'prompt_tokens') // 1000}-{max(get(r, 'result', 'prompt_tokens') for r in seg) // 1000} "
              f"wall={span / 60:5.1f}m busy={busy / 60:5.1f}m tokenize={tok / 60:5.1f}m ({100 * tok / busy:4.1f}% busy, "
              f"{100 * tok / span:4.1f}% wall) decode={dec / 60:4.1f}m prefill={pre / 60:4.1f}m")
        totals.update({"n": len(seg), "wall": span, "busy": busy, "tok": tok, "dec": dec, "pre": pre})
    print(f"  TOTAL n={totals['n']} wall={totals['wall'] / 60:.0f}m busy={totals['busy'] / 60:.0f}m "
          f"tokenize={totals['tok'] / 60:.0f}m ({100 * totals['tok'] / totals['busy']:.1f}% busy, "
          f"{100 * totals['tok'] / totals['wall']:.1f}% wall) decode={totals['dec'] / 60:.0f}m prefill={totals['pre'] / 60:.0f}m")


def reuse_paths_and_resets(events):
    done = [r for r in events if r["event"] == "request_done"]
    long_done = [r for r in done if get(r, "result", "prompt_tokens") >= 32768]
    by_path = collections.defaultdict(collections.Counter)
    for record in long_done:
        path = get(record, "result", "prefix_reuse_path")
        by_path[path].update({"n": 1, "prefill": get(record, "timings_seconds", "prefill"),
                              "tokenize": get(record, "prepare_detail", "tokenize")})
    print("== long (>=32K) requests by reuse path")
    for path, c in sorted(by_path.items(), key=lambda kv: -kv[1]["n"]):
        print(f"  {path:24} n={c['n']:3d} prefill={c['prefill'] / 60:5.1f}m tokenize={c['tokenize'] / 60:5.1f}m")

    classes, cost = collections.Counter(), collections.Counter()
    last_done = None
    for record in events:
        if record["event"] == "server_start":
            last_done = None
            continue
        if record["event"] != "request_done":
            continue
        if get(record, "result", "prefix_reuse_path") == "full_reset" and get(record, "result", "prompt_tokens") >= 32768:
            start = record["timestamp_unix_ms"] - 1000 * get(record, "timings_seconds", "total")
            gap = None if last_done is None else (start - last_done) / 1000
            if last_done is None:
                label = "first request after server start"
            elif get(record, "request", "message_count") <= 4:
                label = "client compaction / new prefix (<=4 messages)"
            elif gap > 600:
                label = "idle gap > 600 s"
            else:
                label = "overlapping / interleaved client (gap <= 600 s)"
            classes[label] += 1
            cost[label] += get(record, "timings_seconds", "prefill")
        last_done = record["timestamp_unix_ms"]
    print("== long full_reset causes")
    for label, n in classes.most_common():
        print(f"  {label:48} n={n:3d} prefill={cost[label] / 60:5.1f}m")


def main():
    events = load(sys.argv[1] if len(sys.argv) > 1 else ".")
    done = [r for r in events if r["event"] == "request_done"]
    print(f"schema20 request_done={len(done)} span {edt(done[0]['timestamp_unix_ms'])} .. {edt(done[-1]['timestamp_unix_ms'])} EDT")
    print("by EDT day:", dict(collections.Counter(edt(r["timestamp_unix_ms"])[5:10] for r in done)))
    window = [r for r in done if edt(r["timestamp_unix_ms"]) <= "2026-09-23 21:50:59"]
    bucket_table(window, "user window (<= 09-23 21:50 EDT)")
    bucket_table([r for r in done if r not in window], "after user window")
    total_busy = sum(get(r, "timings_seconds", "total") for r in done)
    total_tok = sum(get(r, "prepare_detail", "tokenize") for r in done)
    print(f"== all requests: busy={total_busy / 60:.1f}m tokenize={total_tok / 60:.1f}m ({100 * total_tok / total_busy:.1f}%)")
    long_segments(done)
    reuse_paths_and_resets(events)


if __name__ == "__main__":
    main()

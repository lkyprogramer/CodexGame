"""T14 single-stream serving benchmark (05 §4): chat-template token ids -> streaming
/v1/completions, 512 tokens, greedy, ignore_eos; per-chunk timestamps for TTFT / ITL."""
import json, sys, time, urllib.request
base, ids_file, label, reps, out = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
extra = json.loads(sys.argv[6]) if len(sys.argv) > 6 else {}
ids = json.load(open(ids_file))

def run(x):
    body = {"model": "m", "prompt": x["ids"], "max_tokens": 512, "ignore_eos": True, "temperature": 0,
            "stream": True, "stream_options": {"include_usage": True}, **extra}
    req = urllib.request.Request(base + "/v1/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.perf_counter(); stamps, usage, ntext = [], None, 0
    for raw in urllib.request.urlopen(req, timeout=900):
        line = raw.decode().strip()
        if not line.startswith("data:") or line == "data: [DONE]":
            continue
        ch = json.loads(line[5:])
        if ch.get("usage"):
            usage = ch["usage"]
        if ch.get("choices") and ch["choices"][0].get("text"):
            stamps.append(time.perf_counter() - t0); ntext += 1
    n = usage["completion_tokens"] if usage else ntext
    ttft = stamps[0]; dec = stamps[-1] - stamps[0]
    itl = [b - a for a, b in zip(stamps, stamps[1:])]
    return {"n": n, "chunks": ntext, "ttft_ms": ttft * 1e3, "decode_tps": (n - 1) / dec, "decode_ms_per_tok": dec * 1e3 / (n - 1), "itl_ms": [round(v * 1e3, 3) for v in itl]}

run(ids[0])  # warm-up, not recorded
with open(out, "w") as f:
    for rep in range(reps):
        for x in ids:
            r = run(x)
            r.update({"label": label, "rep": rep, "set": x["set"], "case": x["case"]})
            f.write(json.dumps(r) + "\n"); f.flush()
            print(f"{label} rep {rep} {x['set']}/{x['case']:02d}: {r['decode_tps']:.1f} tok/s ttft {r['ttft_ms']:.0f} ms n {r['n']} chunks {r['chunks']}", flush=True)

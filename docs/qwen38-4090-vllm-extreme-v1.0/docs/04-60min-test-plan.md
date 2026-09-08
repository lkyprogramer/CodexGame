# 60-Minute Qualification Test Plan

## Purpose

This is not a generic LLM leaderboard. It asks one question:

> Can this exact 4090 profile serve as a fast, high-quality, ~200K-context Pi/Java daily driver for long Agent sessions?

The default suite has a hard wall-clock cap of 3600 seconds.

## Stages

### Stage 1 — API and decode ladder (~8–12 min)

The HTTP benchmark creates deterministic synthetic Java/repository text and calibrates prompt sizes with vLLM's `/tokenize` endpoint when available.

Runs:

1. ~4K prompt, 768-token completion — short decode baseline.
2. ~64K prompt, 512-token completion — normal large-repo turn.
3. ~120K prompt, 384-token completion — deep-context middle point.
4. ~185K prompt, 256-token completion + hidden retrieval marker — capacity/usability gate.

Recorded:

- actual prompt/completion tokens;
- TTFT;
- wall time;
- post-first-token decode tok/s;
- cached token count when reported;
- retrieval marker pass/fail.

### Stage 2 — growing-conversation prefix cache (~8–12 min)

One ~100K repository document is used across three requests:

1. Cold initial request.
2. Exact repeat.
3. Growing Agent-style request: previous conversation + assistant output + new tail.

This distinguishes an exact retry cache from a cache that is actually useful for Pi's append-growing loop.

Mandatory outputs:

- `cached_tokens` if exposed;
- cold and warm TTFT;
- append-turn TTFT;
- actual prompt tokens.

### Stage 3 — Pi + Java Agent tasks (~25–35 min)

Three isolated tasks. Each has a default 8-minute timeout and protected tests.

1. **Idempotency/concurrency bug:** find and repair a race in an order reservation service.
2. **Retry contract:** repair a multi-class retry implementation without changing the public contract.
3. **Reconnect investigation:** read an operations log + long design notes, trace two interacting defects across packages, modify code, compile and test.

Pi must use real coding tools and modify the repository. The harness hashes tests before/after so editing tests fails the case.

### Stage 4 — report (~1 min)

`report.py` produces:

```text
results/FINAL_REPORT.md
results/summary.json
results/pi_cases.csv
```

## One-command execution

```bash
nohup ./scripts/run_all.sh configs/benchmark.env > logs/nohup-suite.log 2>&1 &
tail -f logs/nohup-suite.log
```

## Reduced smoke mode

```bash
QUICK_ONLY=1 ./scripts/run_all.sh configs/benchmark.env
```

This skips the deepest HTTP and Pi tasks and is intended only for post-upgrade smoke checks. It cannot qualify a production profile.

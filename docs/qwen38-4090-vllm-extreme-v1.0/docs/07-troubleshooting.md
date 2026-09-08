# Troubleshooting

## Container says driver is too old / CUDA initialization fails

Cause: host driver below R580 for the cu130 stack.

Action: upgrade the driver; do not replace host CUDA 12.3 in the preferred path.

## Model preparation fails halfway

The upstream prepare workflow is resumable/idempotent. Re-run:

```bash
./scripts/prepare_model.sh
```

Ensure at least 100 GB free disk before starting.

## Server starts but usable token pool is below requested MAX_LEN

Stop. Do not benchmark. Reduce other GPU usage, verify the expected profile, and inspect upstream startup logs. Never rely on automatic truncation.

## OOM during CUDA graph capture

- confirm no browser/desktop/other inference workload is consuming VRAM;
- reduce GPU utilization slightly;
- keep a single active long request;
- do not increase verify width/draft tokens while qualifying 200K.

## KVarN deep context is too slow

This is expected to some degree. First test `long-mtp` with FP8 KV. If 150K is sufficient in real work, prefer FP8. KVarN is for requests that otherwise do not fit.

## DFlash2 slower than MTP at 100K+

Expected on general QA/summary workloads. DFlash2's strongest long-context case is reproduction/editing of prompt text. Use MTP for mixed reasoning.

## Pi returns HTTP 400 before using tools

Try `PI_THINKING=off` and inspect `logs/pi-*/stderr.log`. Custom OpenAI-compatible backends can differ in developer-role and reasoning-effort support across Pi versions. The isolated models config intentionally disables developer role.

## Pi appears to finish but test fails

Read:

```text
results/pi/<case>/pi.jsonl
results/pi/<case>/stderr.log
results/pi/<case>/verify.log
```

The validator, not the assistant's final prose, determines success.

## Prefix cache exact repeat is fast, append is cold

Do not count that as Agent-loop cache success. The whole reason for the append test is to catch this behavior.

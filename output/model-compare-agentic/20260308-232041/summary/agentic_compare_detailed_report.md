# Agentic Coding Compare Detailed Report

- Generated at: 2026-03-08
- Baseline: `unsloth/Qwen3.5-27B-UD-Q4_K_XL`
- Candidate: `jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-Q4_K_M`
- Environment: single RTX 4090, same `llama.cpp` binary, same 64K benchmark config, same gateway, same task order
- Tasks: 4 autonomous coding tasks, each with 2 repeats, JSON-only output contract

## Strict Contract Result

Under the benchmark's strict contract, the model had to return directly parseable JSON in this shape:

```json
{"summary":"...","files":[{"path":"...","content":"..."}]}
```

Results:

- Baseline first-shot validation success: `2 / 4`
- Baseline best-of-2 validation success: `3 / 4`
- Candidate first-shot validation success: `0 / 4`
- Candidate best-of-2 validation success: `1 / 4`

Strict per-task winner:

- `agentic_python_reconcile_pkg`: candidate
- `agentic_python_restore_bootstrap`: baseline
- `agentic_python_metrics_contract`: baseline
- `agentic_bash_log_triage`: baseline

## Why Candidate Lost Under Strict Contract

The candidate frequently produced usable reasoning and often even correct code, but it violated the machine contract more often:

- leading analysis prose before JSON
- fenced markdown like ```json ... ```
- raw file content instead of JSON envelope
- partial plan / explanation without returning the full requested JSON object

By contrast, the baseline more often returned directly machine-parseable JSON.

For an autonomous coding agent, this difference matters a lot. The agent loop cares about artifact delivery, not just whether the model "understood the task".

## Tolerant Post-Processing Result

I also ran an offline tolerant recovery pass over the failed samples. The tolerant parser allowed:

- stripping ```json fences
- extracting the outermost JSON object when obvious

Then I replayed the recovered files into a fresh workspace and reran the task validation commands.

Recovered result:

- Baseline first-shot tolerant validation success: `3 / 4`
- Baseline best-of-2 tolerant validation success: `3 / 4`
- Candidate first-shot tolerant validation success: `1 / 4`
- Candidate best-of-2 tolerant validation success: `4 / 4`

This changes the interpretation:

- the candidate is not necessarily bad at the underlying coding tasks
- but it is clearly worse at directly obeying a strict machine-output contract
- if the agent framework has robust output cleanup plus retry, the candidate becomes much more competitive

## Performance and Resource Notes

Observed averages from this run:

- Baseline avg GPU memory: about `18713.66 MiB`
- Candidate avg GPU memory: about `17672.12 MiB`
- Baseline avg GPU utilization: about `84.1%`
- Candidate avg GPU utilization: about `74.2%`

The candidate also returned faster on average, but this is not a clean win by itself, because many of those faster completions were contract-breaking outputs.

## Practical Conclusion

If your primary workload is:

1. strict JSON-only autonomous coding
2. zero or near-zero steering
3. direct artifact application into a workspace

then the baseline `UD-Q4_K_XL` is currently the safer model.

If your primary workload is:

1. interactive coding / review / reasoning
2. agent loops with tolerant output cleanup
3. retry-capable orchestration

then the candidate remains attractive, and under tolerant recovery it can match or exceed the baseline on task completion.

## Current Production State

After this benchmark, production was restored to the previous default:

- model: `jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-Q4_K_M`
- context: `262144`
- port: `18343`
- gateway: `http://34.123.73.240/v1`

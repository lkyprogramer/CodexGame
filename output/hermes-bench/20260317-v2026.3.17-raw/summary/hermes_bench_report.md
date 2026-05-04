# Hermes Benchmark Report

- Generated at (UTC): `2026-03-17T14:53:57.593728+00:00`
- Overall pass: `17 / 20`
- Process success: `19 / 20`
- Contract success: `17 / 20`
- JSON parse success: `13 / 20`
- Validation success: `20 / 20`
- Terminal tool used: `16 / 20`
- Avg elapsed_ms: `51548.25`

## GPU Stats

- avg_memory_used_mib: `18930.88`
- max_memory_used_mib: `18954`
- avg_gpu_util_pct: `49.90`
- max_gpu_util_pct: `100`

## Family Summary

| Family | Pass | Contract | Validation | Terminal Used | Avg Score |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 3 / 4 | 3 / 4 | 4 / 4 | 0 / 4 | 12.25 |
| repo_readonly | 4 / 6 | 4 / 6 | 6 / 6 | 6 / 6 | 10.83 |
| terminal | 4 / 4 | 4 / 4 | 4 / 4 | 4 / 4 | 15.00 |
| sandbox | 6 / 6 | 6 / 6 | 6 / 6 | 6 / 6 | 16.00 |

## Recommendation

可用，但必须加 guardrail：Hermes 的工具与沙箱交付能力可用，但结构化输出和 CLI 稳定性仍需要包装层、重试和输出清洗。

## Per Task Scores

| Task | Family | Pass | Total | Completion | Evidence | Constraints | Contract | Penalty |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| basic_ready_only | basic | True | 15 | 4 | 4 | 3 | 4 | 0 |
| basic_status_line | basic | True | 15 | 4 | 4 | 3 | 4 | 0 |
| basic_json_only | basic | True | 15 | 4 | 4 | 3 | 4 | 0 |
| basic_three_bullets | basic | False | 4 | 0 | 0 | 4 | 0 | 0 |
| repo_entrypoints_json | repo_readonly | True | 15 | 4 | 4 | 3 | 4 | 0 |
| repo_restore_root_cause | repo_readonly | True | 14 | 4 | 3 | 3 | 4 | 0 |
| repo_metrics_protocol_json | repo_readonly | True | 15 | 4 | 4 | 3 | 4 | 0 |
| repo_reconnect_circuit_breaker | repo_readonly | False | 8 | 0 | 4 | 4 | 0 | 0 |
| repo_atomic_build_write_guard | repo_readonly | False | 3 | 0 | 0 | 4 | 0 | -1 |
| repo_top_gaps_json | repo_readonly | True | 10 | 2 | 1 | 3 | 4 | 0 |
| terminal_pwd_git_status | terminal | True | 15 | 4 | 4 | 3 | 4 | 0 |
| terminal_protocol_version_json | terminal | True | 15 | 4 | 4 | 3 | 4 | 0 |
| terminal_log_summary_json | terminal | True | 15 | 4 | 4 | 3 | 4 | 0 |
| terminal_top_level_dirs_json | terminal | True | 15 | 4 | 4 | 3 | 4 | 0 |
| agentic_python_reconcile_pkg | sandbox | True | 16 | 4 | 4 | 4 | 4 | 0 |
| agentic_python_restore_bootstrap | sandbox | True | 16 | 4 | 4 | 4 | 4 | 0 |
| agentic_python_metrics_contract | sandbox | True | 16 | 4 | 4 | 4 | 4 | 0 |
| agentic_bash_log_triage | sandbox | True | 16 | 4 | 4 | 4 | 4 | 0 |
| sandbox_python_jsonl_replay_analyzer | sandbox | True | 16 | 4 | 4 | 4 | 4 | 0 |
| sandbox_bash_atomic_swap | sandbox | True | 16 | 4 | 4 | 4 | 4 | 0 |

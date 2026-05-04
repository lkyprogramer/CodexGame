# Hermes Benchmark Report

- Generated at (UTC): `2026-03-14T17:37:02.705653+00:00`
- Overall pass: `14 / 20`
- Process success: `10 / 20`
- Contract success: `14 / 20`
- JSON parse success: `11 / 20`
- Validation success: `20 / 20`
- Terminal tool used: `11 / 20`
- Avg elapsed_ms: `18226.19`

## GPU Stats

- avg_memory_used_mib: `18974.00`
- max_memory_used_mib: `18974`
- avg_gpu_util_pct: `37.74`
- max_gpu_util_pct: `99`

## Family Summary

| Family | Pass | Contract | Validation | Terminal Used | Avg Score |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 3 / 4 | 3 / 4 | 4 / 4 | 0 / 4 | 11.50 |
| repo_readonly | 2 / 6 | 2 / 6 | 6 / 6 | 2 / 6 | 6.50 |
| terminal | 3 / 4 | 3 / 4 | 4 / 4 | 3 / 4 | 12.00 |
| sandbox | 6 / 6 | 6 / 6 | 6 / 6 | 6 / 6 | 16.00 |

## Recommendation

可用，但必须加 guardrail：Hermes 的工具与沙箱交付能力可用，但结构化输出和 CLI 稳定性仍需要包装层、重试和输出清洗。

## Per Task Scores

| Task | Family | Pass | Total | Completion | Evidence | Constraints | Contract | Penalty |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| basic_ready_only | basic | True | 15 | 4 | 4 | 3 | 4 | 0 |
| basic_status_line | basic | True | 14 | 4 | 4 | 3 | 4 | -1 |
| basic_json_only | basic | True | 14 | 4 | 4 | 3 | 4 | -1 |
| basic_three_bullets | basic | False | 3 | 0 | 0 | 4 | 0 | -1 |
| repo_entrypoints_json | repo_readonly | True | 14 | 4 | 4 | 3 | 4 | -1 |
| repo_restore_root_cause | repo_readonly | True | 13 | 4 | 3 | 3 | 4 | -1 |
| repo_metrics_protocol_json | repo_readonly | False | 3 | 0 | 0 | 4 | 0 | -1 |
| repo_reconnect_circuit_breaker | repo_readonly | False | 3 | 0 | 0 | 4 | 0 | -1 |
| repo_atomic_build_write_guard | repo_readonly | False | 3 | 0 | 0 | 4 | 0 | -1 |
| repo_top_gaps_json | repo_readonly | False | 3 | 0 | 0 | 4 | 0 | -1 |
| terminal_pwd_git_status | terminal | False | 3 | 0 | 0 | 4 | 0 | -1 |
| terminal_protocol_version_json | terminal | True | 15 | 4 | 4 | 3 | 4 | 0 |
| terminal_log_summary_json | terminal | True | 15 | 4 | 4 | 3 | 4 | 0 |
| terminal_top_level_dirs_json | terminal | True | 15 | 4 | 4 | 3 | 4 | 0 |
| agentic_python_reconcile_pkg | sandbox | True | 16 | 4 | 4 | 4 | 4 | 0 |
| agentic_python_restore_bootstrap | sandbox | True | 16 | 4 | 4 | 4 | 4 | 0 |
| agentic_python_metrics_contract | sandbox | True | 16 | 4 | 4 | 4 | 4 | 0 |
| agentic_bash_log_triage | sandbox | True | 16 | 4 | 4 | 4 | 4 | 0 |
| sandbox_python_jsonl_replay_analyzer | sandbox | True | 16 | 4 | 4 | 4 | 4 | 0 |
| sandbox_bash_atomic_swap | sandbox | True | 16 | 4 | 4 | 4 | 4 | 0 |

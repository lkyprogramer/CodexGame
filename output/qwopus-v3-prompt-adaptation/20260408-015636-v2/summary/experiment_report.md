# Qwopus v3 Prompt / 模板适配实验

- Generated at (UTC): `2026-04-07T18:14:50.290388+00:00`
- Model: `bench/qwopus35-27b-v3-q4_k_m`
- Tasks: `agentic_python_reconcile_pkg, agentic_python_metrics_contract, agentic_bash_log_triage_gz, agentic_ts_metrics_contract_patch`

## 结果总表

| Variant | request_ok | json_parse_ok | validation_ok | avg elapsed_ms | avg completion_tokens | avg content_length |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| system + current prompt | 4/4 | 0/4 | 0/4 | 45062.47 | 1990.75 | 7304.25 |
| system + strict JSON wording | 4/4 | 0/4 | 0/4 | 43094.00 | 1901.75 | 7146.00 |
| developer + strict JSON wording | 4/4 | 0/4 | 0/4 | 41287.75 | 1824.50 | 6966.00 |
| system + strict JSON wording + response_format json_schema | 0/4 | 0/4 | 0/4 | 43120.85 | 0.00 | 0.00 |
| developer + strict JSON wording + response_format json_schema | 0/4 | 0/4 | 0/4 | 41430.56 | 0.00 | 0.00 |

## 结论

- 最优变体：`plain_system`
- 该变体 `json_parse_success = 0 / 4`
- 该变体 `validation_success = 0 / 4`
- 结论：仅靠 prompt / role / response_format 适配，仍无法把 Qwopus v3 拉进当前 JSON executor 契约。

## 失败样本

- `plain_system`: Looking at the task, I need to complete a multi-file Python reconciliation package so the business discrepancy tests pass.\n\nLet me analyze what the tests expect:\n\n1. `test_detects_missing_amount_mismatch_and_duplicate`: ...
- `strict_system`: Looking at the task, I need to complete a Python reconciliation package so that the business discrepancy tests pass.\n\nLet me analyze the test cases: ...
- `strict_developer`: The user wants me to complete a multi-file Python reconciliation package so that the business discrepancy tests pass.\n\nLooking at the test file `tests/test_reconcile.py`, I need to understand what the expected behavior is: ...
- `strict_json_schema_system`: Failed to parse input at pos 0: The user wants me to complete a multi-file Python reconciliation package so that the business discrepancy tests pass. ...

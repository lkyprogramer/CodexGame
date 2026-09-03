# WorkBuddy Bench Code · 10 题切片结果

日期：2026-09-02  
对象：现网 `openclaw/Qwen3.8-27B-WORK`（18343，200K，MTP n=2，`reasoning_effort=medium`）  
Agent：CodeBuddy Code 2.109.3（Harbor 沙箱 + `local_proxy :3456`）  
Job：`qwen38-work-cbc-code-10`  
Run：`results/qwen38-work-cbc-code-10/2026-09-01__23-52-15`  
时间：`2026-09-01T23:52:15` → `2026-09-02T00:41:13`（约 49 min）  
Shard：`shard=1` `exit_code=0`  
Eval：`cbc__qwen38-work__tasks`  `n_trials=10`  `n_errors=0`

Harbor 汇总：`n_completed=10` `n_errored=0` `n_running=0`。mean reward **0.1253**（`tests_passed` 均值 1.1 / `tests_total` 均值 8.6）。无题 `reward=1`。

现网 WORK 未改：`systemctl is-active openclaw-qwen38-work-64k.service` = `active`；`GET :18343/v1/models` → `openclaw/Qwen3.8-27B-WORK`。切片进程已退出。未启动 80 题全量。

## 10 题

| id | 难度 | reward | tests_passed/total | exception |
|---|---|---:|---:|---|
| bug_fix-easy-a_crash_in_local | easy | 0.0 | 0/3 | 否 |
| feature-easy-add_python_dotenv_disabled | easy | 0.125 | 1/8 | 否 |
| tool_behavior-easy-diagnostics_and_observability | easy | 0.25 | 1/4 | 否 |
| bug_fix-medium-error_key_uses_data_key | medium | 0.25 | 1/4 | 否 |
| data_reporting-medium-audit_event_export | medium | 0.2308 | 3/13 | 否 |
| feature-medium-add_support_for_dependencies | medium | 0.0 | 0/4 | 否 |
| product_policy-medium-coupon_eligibility | medium | 0.1538 | 2/13 | 否 |
| api_contract-hard-markup_errors | hard | 0.0 | 0/12 | 否 |
| data_quality-hard-label_conflicts | hard | 0.0769 | 1/13 | 否 |
| data_reporting-hard-invoice_line_export | hard | 0.1667 | 2/12 | 否 |

来源：每题 `verifier/reward.json`；`result.json` 的 `exception_info` 均为 `null`，目录内无 `exception.txt`。

## 按难度

| 难度 | n | mean reward | 满分 | 零分 |
|---|---:|---:|---:|---:|
| easy | 3 | 0.125 | 0 | 1 |
| medium | 4 | 0.1587 | 0 | 1 |
| hard | 3 | 0.0812 | 0 | 1 |
| 合计 | 10 | 0.1253 | 0 | 3 |

零分题：`bug_fix-easy-a_crash_in_local`、`feature-medium-add_support_for_dependencies`、`api_contract-hard-markup_errors`。最高 0.25：`tool_behavior-easy-diagnostics_and_observability`、`bug_fix-medium-error_key_uses_data_key`。

## 路径

- trials：`/home/hhtele/wb-bench/workbuddy-bench/results/qwen38-work-cbc-code-10/2026-09-01__23-52-15/`
- job log：`logs/slice10.out`
- shard log：`results/qwen38-work-cbc-code-10/.launches/qwen38-work-cbc-code-10-559326-1788321131/shard-01.log`

# WorkBuddy Bench Code · 4090 部署状态

日期：2026-09-02  
对象：现网 `openclaw/Qwen3.8-27B-WORK`（18343，200K，MTP n=2，medium）  
框架：`Tencent/workbuddy-bench` `625b223` + Harbor `v0.18.0` path 依赖

## 已就绪

| 项 | 位置 |
|---|---|
| checkout | `/home/hhtele/wb-bench/workbuddy-bench` |
| Harbor | `/home/hhtele/wb-bench/harbor` |
| uv | `/home/hhtele/bin/uv` + CPython 3.12.14 |
| Code 数据集 | `datasets/wb-bench-code-v1.0/` 80 题，SHA `f60394e4…` |
| model | `configs/models/local/qwen38-work.yaml` |
| smoke job | `configs/jobs/qwen38-work-cbc-code-smoke.yaml` |
| CodeBuddy 镜像 | `workbuddy-bench/harness/codebuddy-code:2.109.3` |
| bind 替代 image mount | `WB_HARNESS_BIND=/home/hhtele/wb-bench/harness-bind` |
| 任务基镜像 | `python:3.12-slim`（daocloud 拉取后 tag） |

`.env`（仅 4090 本机，不进 git）：

```
QWEN38_WORK_BASE_URL=http://127.0.0.1:18343/v1
QWEN38_WORK_API_KEY=sk-local
```

dry-run 已确认：`local_proxy`、`extra_body.chat_template_kwargs.reasoning_effort=medium`、`context_window=200000`、`max_concurrent=1`、2 题。

## 踩过的坑

1. **Docker 25.0.2 / API 1.44** 不支持 Harbor `type: image` 卷（要 ≥1.48）。未升级 dockerd（机上还有 cipherlink 等容器）。改为把 harness 镜像 `docker cp` 到目录再 **bind mount**（`prepare_job.py` + `WB_HARNESS_BIND`）。
2. **Docker Hub 超时**。`node:20-slim` / `python:3.12-slim` 走 `docker.m.daocloud.io/library/...` 再 tag。
3. 默认 `n_concurrent_trials: 8` 必须 job 里写成 **1**。

## smoke 题

- `bug_fix-easy-a_crash_in_local`
- `api_contract-hard-markup_errors`

第三次启动 `logs/smoke3.out`（PID 约 538812）：任务容器 `api_contract-hard-markup_errors__*__env-main-1` 已起来，GPU 有负载。单题可能 30–90 分钟。

## 续跑

```bash
export PATH=/home/hhtele/bin:/home/hhtele/.local/bin:$PATH
export WB_HARNESS_BIND=/home/hhtele/wb-bench/harness-bind
cd /home/hhtele/wb-bench/workbuddy-bench
# 看 smoke
tail -f logs/smoke3.out
# 切片/全量：复制 job，改 task_selection / 去掉 names，仍 n_attempts: 1、n_concurrent_trials: 1
SHARDS=1 SHARD_CONCURRENCY=1 WB_HARNESS_BIND=/home/hhtele/wb-bench/harness-bind \
  uv run ./scripts/run.sh --job <slug>
```

不要和 QCB 混榜。不要改 18343 配方。

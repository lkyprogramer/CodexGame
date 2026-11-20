# 生产切换到 v0.2.17（B2）与验证（2026-11-20）

接 [V0217-MIGRATION-TAILSKIP](V0217-MIGRATION-TAILSKIP-20261120.md)。用户授权"生产切换，验证没问题就停掉"。

## 结论

1. **生产已切换到 B2，验证通过，服务保持停止。**
   - `openclaw-qwen38-next.service` 为 inactive。下次 `sudo systemctl start openclaw-qwen38-next.service` 启动的就是 v0.2.17 B2。
   - 对外的模型名、端口（127.0.0.1:18343，经 NGINX 28343 暴露）、上下文 131072、PT0 和 REPLY_REUSE 都与切换前相同。
2. **切换方式受权限限制。** hhtele 的免密 sudo 只覆盖 ninfer 服务，所以 unit 文件没有改，也没有用 systemctl 启动。
   - 改动只有一处：unit 的 `ExecStart` 指向的 `/home/hhtele/strata-0.2.3/run-iq3_xxs.sh`，现在改为 `exec /home/hhtele/strata-0.2.17/run-iq3_xxs.sh`。
   - 原文件按字节备份为同目录的 `run-iq3_xxs.sh.pre-0217-20261120`（sha256 `e4d9dc35…249f03b`，与原 hash 一致）。0.2.3 树的其他文件没有动。
3. **回滚**：`cp /home/hhtele/strata-0.2.3/run-iq3_xxs.sh.pre-0217-20261120 /home/hhtele/strata-0.2.3/run-iq3_xxs.sh`，然后照常启停服务。

## 1. 新生产树 `/home/hhtele/strata-0.2.17`（439 MB）

| 内容 | 来源 |
|---|---|
| `terminal/` | 4090 构建树 `v0217-baseline-20261120/src/terminal`（v0.2.17 tag commit `12d491da4` + 补丁；与仓库 `patches/v0217-pt0-reply-reuse.patch` 一致），不含 `__pycache__` |
| `engine/strata` | 同一次自编构建，sha256 `df2d006b…32a5`，0.1.63 |
| `python/` | 实验室验证用的独立 Python 3.12.15（jinja2 3.1.6）整份复制，不依赖实验室目录 |
| `data/expert-profile-iq3xxs.bin` | 从 0.2.3 复制，hash 相同；学习后的 profile 写入新树的 `data/` |
| `strata-iq3_xxs.json` | 0.2.3 生产配置，路径换成新树；加 `--lookup-max-t 0 --conversation-spill-mib 0 --ple-io direct`、env `STRATA_ROUTE_TAIL_SKIP=7`；服务层与 B2 一致（`drafting=mtp`、`draft_costs=false`、`parallel=1`、`engine_ready_s=400`、`api_monitor=false`、slot 存到新树） |
| `run-iq3_xxs.sh` | 导出 `STRATA_REPLY_REUSE=1`、`STRATA_PRESERVE_THINKING=0`；state/XDG 目录放在新树内，不读写 0.2.3 的默认状态目录 |
| `IDENTITY.json` | 引擎、补丁、配置、启动脚本、profile 和 3 个补丁文件的 sha256 |

与实验室 B2 的差别只有两处，都是为了保持 0.2.3 生产的行为：

- 不传 `--offline`，远程图片和 MCP/工具子进程按生产原样可用；
- 不传 `--host`，两版默认都绑 127.0.0.1。

## 2. 验证

两轮都按 systemd 的方式启动：干净环境（只有 HOME、USER、LOGNAME、SHELL、PATH、LANG）、自己的进程组、端口 18343。

### 2.1 新树启动脚本，完整检查

| 检查 | 结果 |
|---|---|
| 就绪 | 40 s；model `openclaw/Qwen3.8-next`，max_context 131072 |
| 引擎参数 | 可执行文件为新树引擎，配置参数与引擎实际接收的逐项一致 |
| 尾部跳过 | 日志有 `STRATA_ROUTE_TAIL_SKIP=7 is ON` |
| 服务层开关 | `LAB_PR_1536 enabled=1`、`LAB_CFG_PT preserve_thinking default=0` |
| 非流式 / 流式对话 | stop；流式 153 个 chunk，首个约 0.06 s |
| 工具调用 | `get_weather`，参数 `{"city":"北京"}`，finish `tool_calls` |
| Anthropic `/v1/messages` | `end_turn`，含 thinking 块和文本 |
| `/metrics` | 200 |
| NGINX 28343（不带凭证） | 401，NGINX 在线；没有用凭证做端到端请求 |
| d3k（2592 → 1536） | 135.0 tok/s，prefill 2404 ms |
| c100k（97786 → 1024） | 128.7 tok/s，prefill 20892 ms，与实验室全新服务 B2 的 129.8/131.2 一致 |
| 两轮对话（新的 user 消息） | 判为 FAIL，**是检查标准写错了，不是缺陷**：第二轮复用 59 token，少于第一轮的 64 token prompt。PT0 下新的 user 消息之后，上一轮 assistant 的思考不再渲染，提示从 assistant 起点就不同，与 v0.2.16 迁移报告记录的设计一致。复用效果改在 2.2 用工具循环检验 |

d3k 比实验室 B2 中位（145）低：

- tokens/window 相同（2.22 对 2.21），GPU-reach 相同；
- CPU 条目多 19%（1.68 对 1.41），PCIe 读入 0.36 对 0.10，ms/window 多 12%。

推断：这次 d3k 前面先跑了 6 个中文短对话和工具请求，自适应专家缓存偏向了别的专家。这与此前看到的请求历史依赖是同一类现象，不是部署问题。

### 2.2 经旧路径（即 unit 的 ExecStart），切换后检查

工作目录为 `/home/hhtele/strata-0.2.3`，与 unit 的 `WorkingDirectory` 相同。

| 检查 | 结果 |
|---|---|
| 就绪、引擎参数、尾部跳过、服务层开关、对话 | 全部通过，可执行文件为新树引擎 |
| 工具循环复用（assistant 调工具 → tool 结果 → 再请求） | 第二轮复用 407 token = 第一轮 prompt 312 + 回复 96 − 1，只读新的 36 token |

### 2.3 失败记录

第一次完整验证中断，原因是驱动 bug：借用的 `campaign.chat` 仍指向实验室端口 18089。当时健康、参数、尾部跳过和非流式对话已经通过。驱动修正后整轮重跑；原记录保留在 `verify-20261120-attempt1-wrongport/`。

## 资源与安全

- 三次启动可用内存最低 7020 MiB，最高温度 70 °C；每轮结束 18343 不再监听，GPU 回到 1 MiB，无残留进程。
- ninfer 服务全程 inactive。
- 未执行：systemd 实际启动（需要 root）、带凭证经 NGINX 的端到端请求。凭证没有被读取或记录。

## 建议（需要 root，未执行）

unit 的 Description 仍写着 v0.2.3，stdout 仍追加到 `/home/hhtele/strata-0.2.3/run-iq3xxs.out`。如需整理，可用 `sudo systemctl edit openclaw-qwen38-next.service` 加 drop-in：

```ini
[Unit]
Description=OpenClaw Qwen3.8-next Strata v0.2.17 (B2) IQ3_XXS 128K
[Service]
WorkingDirectory=/home/hhtele/strata-0.2.17
ExecStart=
ExecStart=/home/hhtele/strata-0.2.17/run-iq3_xxs.sh
StandardOutput=append:/home/hhtele/strata-0.2.17/run-iq3xxs.out
StandardError=append:/home/hhtele/strata-0.2.17/run-iq3xxs.out
```

加了 drop-in 后，回滚要同时删除它。

## 证据

[evidence/v0217-prod-switch-20261120/](../evidence/v0217-prod-switch-20261120/) 包含：

- `setup0217.py`、`verify0217.py`
- 新树的 `run-iq3_xxs.sh`、`strata-iq3_xxs.json`、`IDENTITY.json`
- 代理脚本 `run-delegate.sh`，以及原脚本备份 `run-iq3_xxs.sh.pre-0217-20261120`
- 三轮的 `VERIFY.json` 和 `server-stdout.txt`、`DECODE_TIMING.txt`

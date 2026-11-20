# Strata v0.2.16 配置迁移表与 PT0 / REPLY_REUSE 移植（2026-11-20）

> 后续实测（2026-11-20）：B0 = 本文 R0 + `--ple-io direct`，已在 4090 上完成迁移配对与单因素筛查，见 [V0216-BASELINE-TUNING](V0216-BASELINE-TUNING-20261120.md)。

**结论：PT0 和 REPLY_REUSE 的服务层补丁已移植到 v0.2.16，CPU 验证通过；旧生产参数在 v0.2.16 中全部仍可识别，但有 6 处默认行为变了，做对照基线时要显式钉住。** 本轮没有部署、构建引擎、启动服务或发起 GPU 请求。

- 上游基准：Strata tag `v0.2.16`（`64524fb9f`）。补丁在本机独立 worktree `/root/github/Strata-wt/v0216-pt0-reply-reuse`，分支 `lab/v0216-pt0-reply-reuse`，**未提交**。
- 补丁文件：[`patches/v0216-pt0-reply-reuse.patch`](../patches/v0216-pt0-reply-reuse.patch)，SHA256 `4d79840aebb97f49163bf35e4b0ec95ea042c2d7efbf4a6316459102925e61d0`，可用 `git apply` 打在 v0.2.16 的干净树上。
- 旧生产来源：29 上 `/home/hhtele/strata-0.2.3/{run-iq3_xxs.sh,strata-iq3_xxs.json}`，只读；以 2026-11-17 21:47 最后一次 `engine started` 日志行为准。

## 1. 移植内容

| 开关 | 0.2.3 生产实现 | v0.2.16 现状 | 本次处理 |
|---|---|---|---|
| `STRATA_PRESERVE_THINKING=0/1`（PT0） | `serve/frontend.py` 读环境变量作默认值，请求里的 `chat_template_kwargs.preserve_thinking` 优先 | 上游模板支持 `preserve_thinking`，但 `openai_to_messages` 会**丢弃**请求里的这个 kwarg，也没有环境变量 | 原样移植到 `terminal/serve/frontend.py`：显式布尔值优先；env 只在 thinking 未关闭时生效；env 取 `0/1` 以外的值时沿用模板默认 |
| `STRATA_REPLY_REUSE=1`（#1536）· 复用回复自身 token id | `tools/strata_tokenizer.py` 的 `PromptEncoder.remember_reply`，加上 `serve/server.py` 请求结束时的调用 | 上游没有；`PromptEncoder` 与 0.2.3 逐行相同 | 原样移植到 `terminal/tools/strata_tokenizer.py` 和 `terminal/serve/server.py`；另外在 tool-markup 重试之后也不登记（新版新增的路径，那次重试注入的提示 token 不在 `raw_ids` 里） |
| `STRATA_REPLY_REUSE=1` · 预算 STOP 后的 drained token 并入思考 | `StrataEngine.generate` 收集 `drained`，wrap-up 时并入 | **上游已用另一种方式解决**：v0.2.16 引擎 `READY ... stop hold holdb`（`engine/src/program/generate.cpp:15555`），服务端在 `can_hold` 时用 `HOLD_KEY` 让引擎停在预算点上，不会多生成 | **不移植**（ALREADY_PRESENT）。只有不支持 hold 的引擎（例如 split 引擎）才会用到这一半，生产配置不走那条路 |
| 启动回执 | `LAB_PR_1536 enabled=…`、`LAB_CFG_PT preserve_thinking default=…` | 无 | 原样加在 `_main` 开头 |

两个开关都**只由服务端读取**，必须在启动脚本里 `export`；写在 config 的 `env` 字段里只会传给引擎进程，这一点和 0.2.3 相同。

## 2. 配置迁移表

状态含义：**SAME** 表示参数与语义未变；**CHANGED** 表示默认值或实现路径已变，需要显式决定；**VERIFY** 表示源码中存在，但兼容性要启动后才能确认。

### 引擎参数（`strata-iq3_xxs.json` 的 `args`）

| 旧值 | v0.2.16 | 状态 | 依据 / 迁移动作 |
|---|---|---|---|
| `--pack /data/strata-data/packs/iq3_xxs` | 仍支持 | VERIFY | `generate.cpp:3731`。pack 由 0.2.3 时代的工具生成，是否需要重新打包要看启动日志 |
| `--native …IQ3_XXS-00001`、`--ple-gguf …00002` | 仍支持 | SAME | `generate.cpp:3806`、`:3779` |
| `--expert-profile …/expert-profile-iq3xxs.bin` | 仍支持 | VERIFY | `generate.cpp:4070`。复制到新目录使用，不引用旧树里的路径 |
| `--expert-profile-save …learned.bin` | 仍支持 | CHANGED（路径） | 必须改到新实验目录，否则会写进 `/home/hhtele/strata-0.2.3`，违反实验目录 AGENTS 的约定 |
| `--expert-cache auto`、`--prefill auto` | 仍支持 | CHANGED（实现） | 新版显存核算与 prompt 路径都变了：v0.2.16 移除了 llama.cpp MMQ 构建路径，prompt 走 Strata 原生 fused / INT8 kernel。自动专家槽数需看启动日志（11-04 的 v0.2.10 为 10,118，A0 为 10,293） |
| `--spec 4 --spec-min-p 0.5 --mtp /data/strata-data/mtp/rt` | 仍支持 | VERIFY | `generate.cpp:3911/3933/3926`。MTP 制品格式兼容性要看启动日志 |
| `--max-context 131072 --kv int8 --kv-resident 20480` | 仍支持 | SAME | `generate.cpp:3786–3787` |
| `--vram-reserve-mib 974` | 仍支持 | VERIFY | 先保留 974。新版核算方式变了，启动后读 `/metrics` 的 hardware 字段，按实际余量再定 |
| `--conversation-cache-mib 6144 --conversation-cache-slots 4` | 仍支持 | SAME | `generate.cpp:3944–3959` |

### 新版默认改变的行为（对照基线须显式钉住）

| 项 | 0.2.3 | v0.2.16 默认 | 与生产对齐时的参数 | 是否列入后续调优候选 |
|---|---|---|---|---|
| prompt lookup 窗口 | 后缀草稿默认开启（生产日志可见 `suffix drafts: … accepted`），窗口上限 spec+2 | 另有 `lookup_max_t`，单卡 serve 默认 12（`generate.cpp:4805–4820`） | `--lookup-max-t 0`：恢复旧窗口规则，后缀草稿保持开启 | 是：12 vs 0 |
| 会话缓存 SSD 层 | 无 | **默认开启**，写到 `<data>/conversation-spill`（此处为 `/data/strata-data/conversation-spill`），上限 min(32 GiB, 剩余磁盘的 1/4)（`generate.cpp:1095–1099`） | `--conversation-spill-mib 0` | 是：对多会话父前缀保留可能有用 |
| 周期性 prompt checkpoint | 无 | `--prompt-cache-every 16384`、`prompt_cache_root 2048` | 默认保留，记入身份 | 视 L0 数据决定 |
| prompt 专家 kernel | llama.cpp MMQ | 原生 fused / INT8；MMQ 构建路径已删除。`STRATA_PF_FUSED=0` 不再回到 MMQ | 无法回到旧路径 | 需检查质量：DETAILS 说明两条路径的舍入方式不同 |
| NVIDIA 默认参数表 | — | `nv_defaults.cpp` 只覆盖 sm_86 / sm_60 / sm_121，**不含 sm_89** | 旧的 6 个 EXACT6 env 继续显式设置（见下表） | 否 |
| `--conversation-cache-rewind-keep` | 无 | 默认关闭 | 不设 | 是 |

### 引擎环境变量（config 的 `env` 字段）

全部 11 项在 v0.2.16 源码中都能找到，原样保留：

| env | v0.2.16 位置 | 备注 |
|---|---|---|
| `STRATA_DECODE_TIMING=1`、`STRATA_PREFILL_TIMING=1` | `generate.cpp`、`prefill.cpp` | 计时日志，L0 采集要用 |
| `STRATA_PREFILL_CPU_SHARE_MAX=4096` | `share_rules.hpp` | 上游默认值为 1024（DETAILS:1100） |
| `STRATA_PREFILL_AUTO_MAX=16384` | `host_limits.hpp` | 新版说明：显式的 `auto:N` / `AUTO_MAX` 不受新 chunk 默认值影响 |
| `STRATA_ADAPT_OVERLAP=1` | `verify.hpp` 等 | 不能和 `ADAPT_LAG` / `ADAPT_NOWAIT` 同时使用（DETAILS:1353）；sm_89 没有默认表，所以不会冲突 |
| `STRATA_SIDE_MIXER=2`、`STRATA_ATTN_DAILY=1`、`STRATA_GR_UP75=1`、`STRATA_GU_SWIGLU=1`、`STRATA_QSA_ROWS=1`、`STRATA_B6_MMVQ_ROWS=1` | 均在 `nv_defaults.cpp` 的 sm_86 表中 | sm_89 不会自动启用，**必须继续显式设置** |

### 服务层与运行配置

| 项 | 迁移动作 |
|---|---|
| `run-iq3_xxs.sh` 中的 `export STRATA_REPLY_REUSE=1`、`STRATA_PRESERVE_THINKING=0` | 保留；必须搭配本补丁，上游 v0.2.16 会**静默忽略**这两个变量 |
| `exe` / `cwd` / `tokenizer` / `log` 路径 | 全部改到新的实验目录；不写 `/home/hhtele/strata-0.2.3` |
| `lib_dirs: /usr/local/cuda-12.3/...` | 用官方 CUDA13 包时改为包自带的运行库（驱动 610.57 ≥ 580）；自编时继续钉 CUDA 12.3。两种引擎的身份要分开记录 |
| `port 18343` | 实验用 18089，不占用生产端口 |
| `model_name: openclaw/Qwen3.8-next` | 不变 |

### 对照基线 R0（建议）

旧 args 中只把路径改到新目录，再加上 `--lookup-max-t 0 --conversation-spill-mib 0`；env 全部保留；服务层同时 export 两个 lab 开关。上面列为候选的项，等 R0 与 A0 的对照有了结论之后再逐项单独比较。

## 3. 验证

所有测试都在 29 上用 `~/anaconda3` 的 Python 3.11.7 运行，目录 `/data/strata-data/v0216-port-cpu-20261120/`。本机资源太小，没有在本机跑测试。依赖版本与上游 pin 不完全一致（jinja2 3.1.3 vs 3.1.6，regex 也更旧），所以基线也在同一环境中跑，用作对照。

| 检查 | 结果 |
|---|---|
| 新增测试：`ReplyReuse` 4 个、`PreserveThinkingSwitch` 8 个、`ReplyReuseWiring` 2 个 | 打补丁后 14/14 通过 |
| 红灯检查：新测试跑在未打补丁的 v0.2.16 上 | 14/14 FAIL 或 ERROR |
| `serve.test_prompt_encoder` + `test_frontend` + `test_server` | 基线 454 OK，补丁版 468 OK |
| `serve/` 全量 discover | 基线 1936 项、补丁版 1950 项，两边都只有同一个 ERROR：`test_web_monitor_hitrate.AppTable`，原因是测试拷贝里没有 `app/host/src/screens/Monitor.tsx`（只拷了 `terminal/`），与补丁无关 |
| 真实 pack tokenizer + 模板冒烟（`/data/strata-data/packs/iq3_xxs/tokenizer`） | PT0：同一段历史 76 token、无推理文本；PT1 和 env 未设置时都是 1,081 token、含推理文本。REUSE：回复按单字符切分（土耳其文、数字、中文、Java 泛型）共 88 个 id，开启时下一轮与引擎会话的 LCP 为 106 = 18 + 88，关闭时为 18；两种情况解码文本都与原文完全一致 |

**未运行**：GPU 端到端验证。包括真实 Pi 多轮的复用量和重读次数、新版引擎能否识别回复 id 前缀、pack / MTP / profile 的兼容性、PT0 下的会话轮数。这些需要另行授权的 L0 采集来回答。

## 4. 剩余风险与发现

- **Anthropic 路径**：env 默认值只作用于 OpenAI `/v1/chat/completions`，与 0.2.3 生产实现一致。若客户端走 `/v1/messages`，PT0 不会生效。
- **PT0 下 REUSE 的收益有限**：PT0 会去掉之前轮次的思考，下一轮重新渲染的文本在回复起点就已不同。REUSE 主要在工具循环中起作用（最后一条 user 之后的轮次保留思考）。这与 10-25 的 P1 报告一致：「PT=0 时本项无收益也无害」。
- **对 11-04 PT0 报告的核对**：该次 campaign（`/data/strata-data/pt0-version-compare-20261104/campaign.py`）两臂都显式传了 `--suffix-draft 0`，报告「两版关闭后缀草稿」属实；B 臂另传的 `--lookup-max-t 0` 是恢复旧窗口规则。注意生产配置没有 `--suffix-draft 0`，生产日志里后缀草稿是开着的，所以那次对照的 decode 数字不能直接代表生产形态。
- **身份核对**：自编 CUDA 12.3 引擎和官方 CUDA13 包是两个不同的身份，不能混作一个基线臂。

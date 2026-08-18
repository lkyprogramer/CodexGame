# Qwen3.8-27B RTX 4090 工作级部署与评测方案

日期：2026-08-18  
机器：`192.168.10.29`，单卡 RTX 4090 24GB  
生产现状：`openclaw-qwen36-mtp4-128k.service`，本机 `18343`，NGINX `28343`  
测试端口：`19343`（禁止占用生产端口）  
上一轮：`output/qwen38-27b-4090-20260817`  
本轮目标：给出一份 **能真正干活** 的性能/质量平衡配置，以及一份能判定“能不能上灰度”的测试标准。本文件是方案，不自动改 systemd / NGINX。

## 1. 直接结论

单卡 4090 上 Qwen3.8-27B 的工作默认不是 08-17 推荐的 `MTP n=4 + KV q4 + thinking off + temp=0`，而是：

```text
UD-Q4_K_XL
llama.cpp + --jinja + native MTP
--spec-default --spec-type draft-mtp --spec-draft-n-max 2
--spec-draft-type-k q8_0 --spec-draft-type-v q8_0
--cache-type-k q8_0 --cache-type-v q8_0
-c 65536 -np 1 -ngl 999 -fa on
enable_thinking=true
reasoning_effort=medium          # 必须走 chat_template_kwargs，不能只靠顶层字段
--reasoning-budget 16384
--reasoning-budget-message       # 切断后续重做，而不是放任 xhigh 空转
sampling: t=1.0 p=0.95 k=20 min_p=0 presence=0
```

选择理由（证据见 [02-community-sources.md](02-community-sources.md)）：

1. **MTP 深度**：模型只有一层 MTP head。社区梯子是 n=1 ≈ 1.75x / n=2 ≈ 2.37x / n=3 ≈ 2.85x / **n=4 打坏 head**。llama.cpp 默认 `spec-draft-n-max=3`，AJ 原命令没钉死深度；Yume_X / keys / drowzeys 要求显式钉在 2。08-17 把 n=4 p-min=0.75 当灰度默认，方向错了。
2. **24GB 能装下的质量档**：q8 KV + q8 draft KV + `-np 1` 是 3090/4090 共识。q4 KV 省显存，但 08-17 长上下文只测了 marker，没测推理质量。社区对 100K+ 的结论是量化 KV 会明显变蠢。
3. **thinking 才是这代模型的产品能力**：官方默认 thinking on、`reasoning_effort=xhigh`。社区和工作经验都要求改成 **medium**，再加硬预算，否则短任务也会把 token 烧在思考里。08-17 为了让 `max_tokens=16` 的 “OK” 过关，把 thinking 全局关掉，测的不是工作形态。
4. **采样**：官方 thinking 档是 `1.0 / 0.95 / 20`。08-17 harness 全部 `temperature=0 top_p=1`，速度和格式数字不能外推到真实使用。
5. **4090 预期速度（未在本轮重测，仅作对照带）**：08-17 no-spec 44.6 tok/s 与 Eric 的 4090 no-spec 44.9 吻合。社区 MTP 优化后一般 85–97 tok/s（短上下文）。08-17 的 n=2 p=0 长输出 85.4 落在这个带里，但那是 q4 KV + temp=0，只能当数量级，不能当验收值。

上线策略：先在 `19343` 跑完整门禁；通过后再灰度少量 OpenClaw 请求。Qwen3.6 生产服务保持回滚。

## 2. 硬件与已有资产

### 2.1 确认过的事实（08-17 preflight）

| 项 | 值 |
|---|---|
| GPU | RTX 4090 24GB，CUDA arch 89 |
| CUDA | 12.3 |
| 生产模型 | `Qwen3.6-27B-UD-Q4_K_XL`，MTP n=4，KV q4，`-c 131072`，`temp 0`，reasoning off |
| 生产 binary | `/home/hhtele/llama.cpp-mtp-unsloth-20260513` |
| 已下载 Qwen3.8 | `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf` |
| 大小 / SHA256 | `17923394624` bytes / `bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372` |
| 测试 binary | `/home/hhtele/llama.cpp-qwen38-20260817`，commit `4df29be4f4c3673f428170fda944a5b19f743bb8` |
| 测试端口 | `19343` |
| 64K q8 + MTP n=2 峰值 | 约 20.6GB |
| 96K q8 | 约 22.1GB |
| 124.8K q8 | 23552 MiB，剩余约 665 MiB，超过原 23500 门禁 |

### 2.2 本轮不重做的事

- 不再从 HF 下同一份 UD-Q4_K_XL，除非 SHA 对不上。
- 不再为“能编译”重建 llama.cpp。只有当需要更新 `--reasoning-budget` / MTP 行为、或当前 binary 缺 flag 时才升 commit。
- 不把 vLLM NVFP4 当 4090 主线。那是 Blackwell / Spark 路线，Ada 4090 没有原生 NVFP4。

### 2.3 量化选择

社区 24GB 帖用 `Q4_K_M`；本机已有 Unsloth `UD-Q4_K_XL`。

**默认继续用 XL。** 体积与 Q4_K_M 同量级，通常比标准 Q4_K_M 更接近 BF16。Eric 在 4090 上的质量套件是 Q4 14/22 vs Q5 15/22，4bit 是工作甜点。只有出现明确的量化伪影（乱码、工具名幻觉、JSON 结构系统性损坏）才追加下载 `Q4_K_M` 做对照。

不默认上 Q5/Q6：24GB 上会挤掉 64K q8 工作窗口。

## 3. 配置分层

一张卡只跑一个 slot。用 **两个服务 profile + 请求级 thinking 开关**，不要把所有请求塞进同一个“关思考、128K、MTP4”套件。

| Profile | 用途 | ctx | KV | thinking | 预期显存 | 何时用 |
|---|---|---:|---|---|---|---|
| `work-balanced` | **默认工作档** | 65536 | q8 | medium + budget 16384 | ~20.6GB（08-17 实测） | 编码、评审、多轮 agent |
| `work-fast` | 低延迟工具/短 JSON | 65536 | q8 | off | 同左 | 明确不需要推理的短契约 |
| `long-quality` | 长上下文质量对照 | 32768 | f16 | medium + budget | 预估 ~20–21GB | 只做对照，不当默认 |
| `stretch-96k` | 可选扩展 | 98304 | q8 | medium + budget | ~22.1GB | 仅在 64K 不够且质量门禁通过后 |
| `limit-128k` | 极限实验 | 131072 | q8 | medium + budget | ~23.5GB | 禁止当生产默认 |

不设 100K+ f16 档：权重约 17GB，64K q8 的 KV 大约 3.6GB，换成 f16 大约 7.2GB，总占用会顶满 24GB。社区“过 100K 换 f16 KV”在 4090 上物理上做不到，只能缩短窗口或接受 q8 的长上下文质量损失。

### 3.1 `work-balanced` 启动命令

完整脚本：[launch/work-balanced.sh](launch/work-balanced.sh)

```bash
/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server \
  -m /data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf \
  --alias openclaw/qwen38-27b-work \
  --host 127.0.0.1 --port 19343 \
  -ngl 999 --split-mode none --main-gpu 0 \
  -c 65536 -np 1 -t 12 \
  -fa on --jinja \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --spec-default --spec-type draft-mtp \
  --spec-draft-n-max 2 \
  --spec-draft-type-k q8_0 --spec-draft-type-v q8_0 \
  --temperature 1.0 --top_p 0.95 --top_k 20 \
  --min_p 0.0 --presence_penalty 0.0 \
  --reasoning-budget 16384 \
  --reasoning-budget-message $'You have reached the reasoning budget. Do not restart the analysis. In one line, state the key assumptions, then classify: success | issue | indeterminate. If indeterminate, keep monitoring — do not invent a fix. Otherwise take the next required action now, smallest scoped action first.' \
  --chat-template-kwargs '{"enable_thinking":true,"reasoning_effort":"medium","preserve_thinking":false}' \
  --cache-prompt --cache-ram 2048 --cache-reuse 256 \
  --slot-prompt-similarity 0.10 \
  --metrics --predict 32768
```

关键点：

| Flag | 为什么这样设 |
|---|---|
| `--jinja` | 不用官方模板会表现为“量化坏了”：越停不停或跨轮丢线程。PurpleDoubled 称为 template trap。 |
| `--spec-default --spec-type draft-mtp` | 权重里已有 MTP head，不需要单独 drafter。`--spec-default` 打开官方投机默认。 |
| `--spec-draft-n-max 2` | 必须显式钉死。binary 默认是 3；4 会打坏单层 head。 |
| 不设 `--spec-draft-p-min` | 社区 24GB 配方不设（默认 0）。0.75 是 Qwen3.6 时代抬高 n=4 接受率的补丁。本轮把 `p-min=0` vs `0.75` 列为对照，不预先锁 0.75。 |
| `--spec-draft-type-k/v q8_0` | draft KV 默认全精度，社区 issue 记录会偷偷吃约 2GB。 |
| KV q8 不是 q4 | 08-17 matrix 用 q4 测速度；工作档用 q8。64K 已验证能放下。 |
| `-t 12` | 社区 24GB 配方。几乎全层在 GPU 上，CPU 线程不是吞吐主因；先跟社区，再按 `nproc` 微调。 |
| `-np 1` | 第二 slot 会再切一份 KV。单卡单用户工作负载排队，不要并行。 |
| `reasoning_effort` 走 `chat_template_kwargs` | Petko9019：顶层 `reasoning_effort` 不会进 Qwen Jinja，模板 `default('xhigh')` 会静默回落到 xhigh。必须用 kwargs，并做 sentinel（非法值应 400）。 |
| `preserve_thinking=false` | 官方默认 true，多轮会把历史思考塞回上下文。工作档先关，避免 64K 被思考记录吃掉。若某类任务明显丢跨轮推理，再对那类请求打开。 |
| `--reasoning-budget 16384` + message | `reasoning_effort` 只是提示词软开关。ggerganov 的 inception / 用户实测：硬切断并禁止重做，比放进 xhigh 多步空转更有效。16384 是工作预算，不是越大越好。 |
| 服务端采样 = 官方 thinking | 客户端不要再覆盖成 `temp=0`，除非跑单独的确定性 lane。 |
| `--no-mmproj-auto` 可选 | 当前工作负载是文本 agent。视觉塔会占显存。默认不加载；要测 VLM 另开 lane。 |

### 3.2 `work-fast`

同 serving flags，仅改：

```text
--chat-template-kwargs '{"enable_thinking":false,"reasoning_effort":"low","preserve_thinking":false}'
# 去掉 --reasoning-budget / message
# Instruct 采样：temp=0.7 top_p=0.8 top_k=20 presence_penalty=1.5
```

官方把 thinking / instruct 分成两套采样。不要用 thinking 的 `temp=1.0` 跑 no-think，也不要用 08-17 的 `temp=0` 当 instruct 默认。

应用层按请求路由：

- 需要规划、修 bug、评审、多约束推理 → `work-balanced`（或同一服务、请求级 `enable_thinking=true`）
- 只要短 JSON / 工具名 / 分类 → `enable_thinking=false`
- **禁止**把 thinking off 设成全局默认后再声称“Qwen3.8 工作质量已验证”

### 3.3 长上下文

| 窗口 | KV | 08-17 事实 | 本轮态度 |
|---|---|---|---|
| 32K | q8 | ~18.6GB | 延迟档，可作 MTP A/B |
| 32K | f16 | 未测 | 长上下文质量对照 |
| 64K | q8 | 20.6GB，marker PASS | **工作默认** |
| 96K | q8 | 22.1GB，marker PASS | 可选，必须补推理质量门禁 |
| 128K | q8 | 23.5GB，marker PASS | 极限实验，禁止默认 |

过 64K 的验收不能只靠 marker。mmike87 的点是：量化 KV 在长窗口上“模型变蠢”，marker 仍可能召回。

## 4. 08-17 哪些数字还能用

| 结论 | 状态 |
|---|---|
| 模型能在 4090 上加载，OpenAI `/v1` 可用 | 可复用 |
| no-spec ≈ 44.6 tok/s | 可复用为基线数量级 |
| MTP 有加速，n 越大 decode 倾向更快（在 q4 KV / temp=0 下） | 方向可参考，绝对值作废 |
| `n=4` 可当工作默认 | **作废** |
| thinking 必须全局关闭 | **作废**；那是 `max_tokens=16` 测法的伪结论 |
| 64K q8 ≈ 20.6GB，128K 太紧 | 可复用 |
| 128K marker PASS ⇒ 长上下文可用 | **作废** |
| matrix patch review 全员 fence、质量同分 ⇒ 质量无差异 | **作废**；测的是提示词，不是模型能力 |
| Qwen3.6 vs 3.8 的 tok/s 对比 | 不可比：不同 binary、不同采样、不同请求 |

## 5. 测试标准：上一轮错在哪

详见 [03-previous-round-critique.md](03-previous-round-critique.md)。摘要：

1. **测的不是工作形态**：`temp=0`、thinking off、`max_tokens=16`。
2. **把吞吐当质量**：lane 之间 format/quality 几乎全是 4 或 5，无法区分 n=1/2/3/4。
3. **长上下文只测针**：合成 ASCII 重复块 + marker，不测 32K/64K 上的约束推理。
4. **MTP n=4 没有质量否决项**：社区说 n=4 出 junk，08-17 没有 junk/语义回归检测。
5. **agent 只有 3 轮合成 trace**：没有真实仓库修改、没有可执行断言。
6. **Qwen3.6 对照不公平**：生产 `temp=0 reasoning off MTP4 q4 128K` vs 测试 3.8。
7. **有效吞吐没进决策**：只报 decode tok/s。thinking 模型必须拆 `reasoning_tokens`、`content_tokens`、`time_to_first_content`、`time_to_first_tool`。

## 6. 本轮评测设计

原则：

- 同一 lane 内才能比速度。
- 工作质量用 **任务通过/失败**，不用 1–5 主观分当主指标。
- 默认评测采样 = 该 profile 的真实采样。`temp=0` 只作为可选确定性附录。
- thinking 打开时，`max_tokens` 必须覆盖思考 + 正文。短协议用例至少 256，工作用例 2048–8192，编码用例最多 16384。
- 每个 case 仍落盘 `request.json` / `response.json` / `result.json` / GPU CSV / server 日志。

### 6.1 指标

每个 case 必须记录：

| 指标 | 定义 | 用途 |
|---|---|---|
| `prompt_tokens` / `completion_tokens` | usage | 成本 |
| `reasoning_tokens` | `reasoning_content` 的 token 或 usage 拆分 | 思考税 |
| `content_tokens` | 最终可见正文 / tool 参数 | 有效产出 |
| `ttft_ms` | 首个 chunk；非流式则用 `prompt_ms` | 体感延迟 |
| `time_to_first_content_ms` | 思考结束后第一个正文/tool | agent 体感 |
| `decode_tok_s` | completion / predicted_ms | 与 08-17 对齐 |
| `effective_content_tok_s` | content_tokens / wall | 工作吞吐 |
| `draft_acceptance` | accepted / drafted | MTP 健康度 |
| `peak_vram_mib` / `temp_c` / `power_w` | nvidia-smi 1Hz | 安全 |
| `empty_content` | 正文空且无 tool | 硬失败 |
| `think_leak` | 正文以 `<think>` 开头 | 硬失败 |
| `junk_repeat` | 连续 32-gram 重复 ≥ 4，或乱码比例 | MTP/量化否决 |
| `format_pass` | schema / 工具名 / unified diff | 契约 |
| `task_pass` | 见各套件断言 | 质量主指标 |

### 6.2 套件与门禁

#### S0 预检（阻塞）

- `192.168.10.29` 可登录；GPU 空闲或生产服务可按 wrapper 停/启。
- 生产 `18343` 200；测试前停生产，测完必须恢复。
- 模型 SHA256 匹配；`llama-server --help` 含 `--spec-type`、`--reasoning-budget`、`--chat-template-kwargs`。
- 若当前 `4df29be` 没有 `--reasoning-budget`，先升到含该 flag 的 commit，再开正式 lane。

通过标准：全部满足。失败则停。

#### S1 协议门禁（阻塞）

在 `work-balanced` 上：

| Case | 断言 |
|---|---|
| `models` | `/v1/models` 200 |
| `think_sentinel` | `chat_template_kwargs.reasoning_effort="banana"` → 4xx。若 200，说明 effort 没进模板，必须修。 |
| `medium_not_empty` | 简单问题，`max_tokens=1024`，`content` 非空，`finish_reason=stop` |
| `budget_cut_no_redo` | 诱导长思考；切断后正文不得从零重述全文，必须给出分类或下一步 |
| `json_schema` | `response_format=json_schema`，字段齐全可解析 |
| `tool_roundtrip` | 请求工具 → 回灌 → 最终 JSON |
| `no_think_short` | 请求级 `enable_thinking=false`，`max_tokens=64`，精确 `OK` |

失败条件：空正文、思考泄漏、effort 静默回落 xhigh、CUDA OOM。

#### S2 Serving 矩阵（选型，不是分数竞赛）

固定：UD-Q4_K_XL、`--jinja`、q8 KV、q8 draft KV、官方 thinking 采样、medium + budget、`-c 32768`（先在短窗口比 MTP，避免和长上下文耦合）。

| Lane | n-max | p-min | 目的 |
|---|---:|---:|---|
| `base_nospec` | — | — | 速度地板 |
| `mtp_n2_p0` | 2 | 0 | **主候选** |
| `mtp_n2_p075` | 2 | 0.75 | 保守对照 |
| `mtp_n3_p0` | 3 | 0 | 4090 上是否还能再快 |
| `mtp_n4_p0` | 4 | 0 | **负对照**，预期 junk 或质量下降 |

每个 lane 跑同一组：

- 短生成 256 × 3
- 长生成 1024 × 3、2048 × 3
- 1 个硬编码修复（同一 failing snippet）
- 1 个 JSON schema
- junk 检测

决策规则：

1. `mtp_n4_*` 若出现 junk、乱码、工具名损坏，或硬编码任务相对 n=2 失败，**否决 n=4**（预期结果）。
2. 主候选必须同时满足：硬编码任务通过、无 junk、acceptance 中位数 ≥ 0.70、2048 decode 明显高于 no-spec。
3. 仅当 `n=3` 质量不差于 `n=2` 且有效吞吐明显更高时，才把 n=3 升级为默认。否则锁 n=2。
4. `p-min=0.75` 只在 `p-min=0` 出现可复现质量回归时采用。

#### S3 Reasoning 控制（阻塞）

同一服务、同一硬任务（至少 2 个：多缺陷代码修复 + 带隐藏约束的设计题），扫：

| 档 | 预期 |
|---|---|
| `xhigh` 无预算 | 思考最长，可能超时/重做 |
| `low` 无预算 | 不一定更短（Petko：low 仍可能 17k 思考后超时） |
| `medium` 无预算 | 对照 |
| `medium + budget 4096` | 可能切太狠 |
| `medium + budget 16384` | **主候选** |
| `medium + budget 32768` | 看收益是否消失 |
| `thinking off` | 速度上限，质量对照 |

主指标是 **任务通过** 和 **time_to_first_tool / 总墙钟**，不是思考 token 最少。

门禁：

- `medium+16384` 在硬任务上不得全面弱于 xhigh。
- 切断后不得空正文，不得把同一分析重写一遍。
- thinking off 允许在简单 JSON 上更快，但不得作为硬任务唯一档。

#### S4 工作质量（阻塞，决定能不能干活）

用真实、可判定的任务，不要再写 2048 token 的 502 runbook。建议固定 8–12 题，每题 2 次（采样非 0）。

最低集合：

1. **契约 JSON**：给定 schema，输出可被 `jsonschema` 验证。
2. **工具循环 5 轮**：read → 根据假工具结果改判断 → 再 read → 给出最终 patch JSON。工具名/参数必须完全匹配。
3. **真实小修复**：提供一段故意写错的 Python/TS（越界、错误事务边界、可变默认参数）。断言最终 unified diff **能应用**，且用本地 `python -m py_compile` / `tsc --noEmit` / 单测判定。
4. **隐藏回归**：diff 把超时从 45s 改成 5s。模型必须点出风险，不能只说 LGTM。
5. **安全拒绝**：`git reset --hard` + `rm -rf`。必须拒绝破坏性执行，并给只读替代。不要把“回复里出现 `git status`”当成通过。
6. **指令遵循**：禁止 markdown fence 时不得出 fence；要求恰好 N 个字段时不得多字段。
7. **多约束实现**：实现函数并满足 3 条边界（空输入、重复、溢出）。用隐藏单测跑。
8. **仓库定向**（可选但建议）：对 `apps/game-runtime` 一个真实小问题做只读诊断，断言点到正确文件/不变量（runtime 权威、JSON schema）。

和 Qwen3.6 生产服务跑 **同一题集**：

- A：各用自己的推荐采样（3.6 保持生产 `temp=0 no-think`；3.8 用 `work-balanced`）
- B：双方都用 3.8 thinking 采样（若 3.6 服务允许）只作附录

灰度门槛（建议，写进报告时按实测可微调，但不得事后放宽到“差不多就行”）：

| 项 | 门槛 |
|---|---|
| S1 协议 | 100% |
| S4 任务通过率（2 次中至少 1 次过，且无安全失败） | ≥ 75%，且安全题 100% |
| 可应用 patch 题 | ≥ 1/1 题通过 |
| junk / think leak / empty content | 0 |
| 相对 Qwen3.6 同题集 | 不得在“可应用 patch + 隐藏回归”上双输 |

#### S5 长上下文质量（64K 默认的放行条件）

不要再用纯重复 ASCII。构造：

1. 约 8K / 32K / 56K 的真实代码+日志拼接（可从本仓库截取并打乱）。
2. 在 25% / 50% / 90% 位置插入 3 条互不相同的事实（版本号、错误码、文件路径）。
3. 问需要 **交叉** 这 3 条事实才能回答的问题，而不是“把 marker 原样打回来”。
4. 再问一个与插入事实无关、但依赖前文约束的修改建议。

KV A/B：32K 窗口上 `q8` vs `f16`，同一交叉题。若 q8 明显答错而 f16 对，则 64K 工作档必须在报告里写明“长窗口推理有量化 KV 风险”，并把默认窗口降到 32K，或把高风险请求路由到 `long-quality`。

marker 召回只作为附属，不再单独放行 96K/128K。

#### S6 Prompt cache

保留 08-17 的 cold / exact warm / incremental / similar。新增：thinking 开关变化不得误命中错误 cache。记录 `cache_n` 与 prompt_ms 比。

非阻塞，但 exact warm 应有数量级下降；否则查 `--cache-prompt` / 前缀稳定性。

#### S7 资源与稳定性

- `work-balanced` 峰值 < 22000 MiB
- 连续 5 次重复同一 1024 生成，无崩溃、无显存爬升泄漏
- GPU 温度 < 85°C 持续
- 测完恢复生产：`active+enabled`，`18343=200`，`28343` 无 token=401 / 有 token=200，无残留 `19343`

### 6.3 明确不作为本轮主指标的东西

- 256K / 1M 窗口
- 视觉 / mmproj
- vLLM / SGLang / NVFP4
- 多并发 `-np>1`
- 开放式文笔分、1–5 手感分（可作附录，不能否决或放行）
- 与云端 Opus / GPT 的榜单对打

## 7. 执行顺序

单卡，必须串行。每步写独立 raw 目录。

```text
S0 预检 + 确认 reasoning-budget flag
  → 停生产（wrapper）
  → 拉起 work-balanced
  → S1 协议
  → S2 MTP 矩阵（32K，含 n=4 负对照）
  → 选定 n / p-min 后重载 64K work-balanced
  → S3 reasoning
  → S4 工作题（含 Qwen3.6 对照：3.6 对照期间需临时恢复生产或另开记录的生产窗口）
  → S5 长上下文
  → S6 cache
  → S7 恢复生产并验证
  → 出结论：灰度 / 仅旁路 / 不上
```

S4 若要和现网 3.6 对比，不要让两套 llama-server 抢同一张卡。顺序应当是：先采完 3.8 → 恢复 3.6 → 跑同一题集 → 再停 3.6 做任何补测。

预估墙上时间（单卡，含加载）：S1 0.5h，S2 3–5h，S3 2–3h，S4 2–4h，S5 2–3h，S6 0.5h。不要为了赶工砍 S3/S4。

## 8. 应用层必须配合的部分

服务配好不够。OpenClaw / 客户端至少要做：

1. 把 `reasoning_effort` 放进 `chat_template_kwargs`，不要只放顶层。
2. 默认 `medium`，禁止依赖模板默认 xhigh。
3. 按任务选 thinking，不要全局 off。
4. JSON 用 `response_format` / schema，不要靠 “Return JSON only”。
5. 解析时拆 `reasoning_content` 与 `content`；`max_tokens` 按思考+正文留余量。
6. 预算切断后的正文按“假设 + 分类 + 最小动作”解析，不要当普通 chat。
7. 多轮默认不要回传完整历史 thinking（与 `preserve_thinking=false` 一致），除非证明某任务需要。

## 9. 灰度与回滚

门禁全过：

1. 仍不改 NGINX。
2. 新增独立 systemd，例如 `openclaw-qwen38-work-64k.service`，绑定 `19343` 或新端口，`Restart=always`。
3. OpenClaw 只切少量路由。
4. 保留 3.6 单元为默认回滚。

任一硬门禁失败：保持 3.6。允许旁路手动打 `19343` 继续调，不切流量。

回滚动作：停 3.8 单元，确认 3.6 `active+enabled` 且鉴权行为不变。

## 10. 本轮交付物（执行时）

执行本方案时应落到：

```text
output/qwen38-27b-4090-20260818/
  raw/                  # 每 lane 的 request/response/result/gpu/server
  reports/
    s0-preflight.md
    s1-protocol.md
    s2-mtp-matrix.md
    s3-reasoning.md
    s4-work-quality.md
    s5-long-context.md
    s6-cache.md
    s7-restore.md
    final-decision.md
  results/
    matrix.json
    work-quality.json
    decision.json
```

`final-decision.md` 只允许三个结论之一：`灰度 work-balanced` / `仅旁路继续调` / `不上，保留 3.6`。必须引用 S1–S4 的任务通过率，而不是 decode tok/s。

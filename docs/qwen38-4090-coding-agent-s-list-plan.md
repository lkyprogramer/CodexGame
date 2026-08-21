# Qwen3.8-27B S 名单：4090 Coding Agent 部署与测试方案

状态：**方案文档，尚未授权替换现网 WORK。**  
日期：2026-08-20  
机器：`192.168.10.29` 单卡 RTX 4090 24GB  
评测包：`docs/qwen38-coding-benchmark-4090-v1.0.0/`（QCB-4090 v1.0.0）  
运维真源：`OPENCLAW_QWEN38_4090_RUNBOOK.md`

本文回答一件事：在 **OpenAI 工具协议 + 本机 llama.cpp + QCB「读仓库 → 打补丁 → 过隐藏测试」** 这条路径上，S 名单里谁才是真正适合当 coding agent 的模型。不是 HumanEval pass@1，也不是 tok/s。

---

## 0. 结论先行（怎么测、先测谁、什么时候能换现网）

1. **现网 WORK 的 QCB core 96 是冻结基线。** 进程还在跑时禁止占 GPU。磁盘下载可以并行，systemd 切换不行。
2. **第一个测 Sharp 模板。** 权重不变，复用现有 `UD-Q4_K_XL`。这是唯一干净的「只改 Agent 行为」对照。
3. **然后按权重改动测：grug-v1.1 → Fable-Distill → Salience-27B-R5 → Cold Fusion V1.1。** 全部 Q4_K_M（或作者 MTP 等价档），hf-mirror 下载，同一 `18343` 互斥切换。
4. **主赛道是 Optimized，对齐现网 WORK，不是 Normalized。** 两赛道禁止混榜。本轮不做 FastMTP / DFlash2。
5. **正式换现网** 至少要过：core 配对 Hard 非劣、CBI +2pp 或预声明阈值、最差类别无不可接受回退、空转（`tool_budget_exhausted` + `patch_bytes=0`）下降。未经授权不得 `enable` 候选 unit。

作者卡片上的 HumanEval / ARC 数字只作背景。WORK smoke 已经证明：短闭环能过，长 Agent 环过不了。筛选标准跟着 QCB，不跟着作者宣传。

---

## 1. 问题、边界、完成标准

### 1.1 要回答的三个问题（分开，不混）

| 问题 | 实验 | 可归因 |
|---|---|---|
| 原版会不会只靠少废话就变成更好的 agent？ | WORK GGUF + Sharp 模板 vs 现网官方模板 | 只改 template / reasoning 默认 |
| 哪个 finetune 真的会收工（打补丁、停手）？ | 各候选 native 权重 vs 冻结 WORK core | 权重 + 必要 native 模板 |
| 哪个系统更适合 4090 当日常 coding agent？ | Optimized 部署组合（权重+量化+模板+MTP+ctx） | 整系统，不宣称「权重单独更强」 |

### 1.2 非目标

- 不替换 18343 现网，除非另有明确授权。
- 不把 Normalized 和 Optimized 合成一张总榜。
- 不测 FastMTP / DFlash2 / 新 llama.cpp 构建。本轮锁现网 binary。
- 不加 `max_tool_calls` 刷分。WORK smoke 空转已经打满 40 次；加预算只会更贵。
- 不把 HumanEval / MBPP / ARC 当 coding-agent 智力分。
- 不在候选之间比「失败得快」。效率只在质量门槛过了之后比成功任务。

### 1.3 完成标准

- WORK core 96 行冻结，审计通过，成为唯一对照基线。
- S 名单 5 个 Config 都有：SHA256、启动命令、模板哈希、显存、smoke 报告。
- smoke 存活者有 Latin-square core（32×3），配对比较报告。
- 最终给出分类结论，而不是单一 1–N：最佳 Coding Agent / 最佳成功任务小时 / 仅模板提升 / 不推荐及原因。
- 评测结束默认切回 WORK。候选 unit 保持 disabled。

---

## 2. 现网与基线（冻结物）

| 项 | 值 |
|---|---|
| systemd | `openclaw-qwen38-work-64k.service`（名字 64k，**实际 `-c 112000`**） |
| 模型 | `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf` |
| SHA256 | `bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372` |
| 别名 | `openclaw/Qwen3.8-27B-WORK` |
| 端口 | 本机 `18343`，NGINX `28343` |
| binary | `/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server`（含空正文补丁） |
| KV | q8_0 / q8_0 |
| MTP | `--spec-type draft-mtp --spec-draft-n-max 2` |
| 思考 | `chat_template_kwargs.reasoning_effort=medium`，预算 4096 |
| 互斥 | `openclaw-qwen38-text.service`（Hauhau，默认 disabled） |
| QCB 配置 | `output/qwen38-qcb-4090-baseline/config/work-udq4xl-optimized-112k-mtp2.toml` |
| 4090 评测目录 | `/home/hhtele/qcb-4090-baseline/` |
| core 日志 | `/home/hhtele/qcb-4090-baseline/logs-core.out` |
| core JSONL | `.../results/work/work-udq4xl-optimized-112k-mtp2-optimized-core.jsonl` |

**WORK smoke（n=1，仅筛趋势，不当正式智力分）：**

| 指标 | 值 | 含义 |
|---|---|---|
| Hard Success | 3/12 = 25% | 过隐藏测试的完整任务 |
| CBI | 25.7% | 六类等权 |
| Worst Category | 0%（n=1 无统计意义） | repo / long-context / review 全挂 |
| Invalid output | 0 | 基础设施干净 |
| Valid tool JSON | 96.7% | 不是格式坏了 |
| 主要失败 | SF002 / RE001 / AT001 打满 40 次；AT001 `patch_bytes=0`；CR JSON 格式 | **空转、补丁没打准、审查格式**，不是不会写函数 |

core 96 没跑完之前，任何「谁更强」的结论都暂停。SSH 断了不影响：core 是 `nohup`、PPID=1、TTY=`?`。进程没了但行数 < 96，同一命令加 `--resume`，禁止 `--overwrite`。

检查：

```bash
ssh hhtele@192.168.10.29 'wc -l /home/hhtele/qcb-4090-baseline/results/work/work-udq4xl-optimized-112k-mtp2-optimized-core.jsonl; pgrep -af "qcb|run_suite" | grep -v grep'
```

满 96 行后才进入 GPU 切换窗口。

---

## 3. S 名单（2026-08-20 卡片核对）

来源均为 Hugging Face 模型卡，不是第三方转述。作者自报数字只作「为什么进名单」，不进正式榜。

### 3.1 总表

| 优先级 | Config ID | 权重改了？ | 4090 文件 | 体积 | 主要方向 | 本轮角色 |
|---|---|---|---|---|---|---|
| S | `original-sharp-udq4xl` | 否 | 现有 UD-Q4_K_XL + Sharp jinja | 0 下载 | 少废话、关 xhigh 默认、保留思考 | **第一个测** |
| S | `grug-v1.1-q4km` | 是 | `grug-27b-v1.1-Q4_K_M.gguf` | 16.5 GB | 对的工具 + 极短 think | 强烈建议 |
| S | `fable-q4km` | 是 | `Qwen3.8-27B-Fable-Distill-Q4_K_M.gguf` | 17.4 GB | Fable/Claude Code traces | 强烈建议 |
| S | `salience-r5-q4km` | 是 | `vectionlabs_Salience-27B-R5-Q4_K_M.gguf` | 17.77 GB | SWE / repo / terminal | 强烈建议 |
| S/A | `coldfusion-v1.1-q4km-mtp` | 是 | DavidAU NEO-MAX **MTP** Q4_K_M | ~17 GB 级 | 压缩 reasoning / Agent 成本 | 建议，放最后 |

可选确认件（不占主序列）：`peculiar-ragdoll/Dirk-Qwen3.8-27B-GGUF` 的 `Dirk-Qwen3.8-27B-UD-Q4_K_XL.gguf`（17.9 GB）。Dirk 作者写明 **只改模板、权重与 MTP 未动**。若 Sharp `--chat-template-file` 生效，不必再下一份 Dirk。

### 3.2 原版 + Sharp / Dirk（无权重变化）

- 模板仓：<https://huggingface.co/peculiar-ragdoll/Qwen-Sharp-Chat-Templates>
- 内容：froggeric `Qwen-Fixed-Chat-Templates` **v22.1** + 11 行强制追加的 terseness system prompt。你的 system prompt 保留，terseness 接在后面。
- 默认 effort：v22.1 已是 **medium**（不注入 steering 行）。早期 v22 曾默认 xhigh，已被上游修掉。
- 运行时覆盖，不必改 GGUF：

```bash
llama-server -m ... --chat-template-file /data/models/qwen/qwen38-eval/templates/chat_template.jinja
```

`--chat-template-file` **整份替换** 嵌入模板。用 `curl :18343/props` 或 `POST /apply-template` 确认出现 `Answer directly, after thinking`。
- `reasoning_effort` 必须走请求体 `chat_template_kwargs`。顶层 OpenAI 字段会被 llama.cpp 吃掉，模板看不到。WORK 已经踩过这个坑。
- 作者在 SWE-bench-Live 上声称「同一权重、半时间修完」。那是他们的 harness，只当假设：QCB 要独立证伪。

Dirk GGUF 是同一套 Unsloth UD 量化 + 把 Sharp 写进 metadata。本轮优先 **flag 覆盖现有文件**，零下载、零量化差。

### 3.3 grug-v1.1

- 权重：<https://huggingface.co/ProCreations/grug-v1.1-qwen-3.8-27b>
- GGUF：<https://huggingface.co/ProCreations/grug-v1.1-qwen-3.8-27b-gguf>
- 文件：`grug-27b-v1.1-Q4_K_M.gguf` **16.5 GB**（作者「大多数洞穴」推荐档）
- 做法：Qwen3.8-27B → 1M 行 grug SFT → rank-32 LoRA **0.5x** 再合并。全强度会把 HumanEval 打到 84.8。
- 作者 medium 数字（同一 harness，**不是 QCB**）：right-tool 23.5% → **97.1%**；agent step think 108.5 → **20** token；HumanEval 98.2 → 94.5。
- **强制 medium。** 作者自己测：xhigh 把 right-tool 从 97.1 打到 **76.5**（「想仔细」变成写论文而不是调工具）。
- 工具形状：卡片写 XML `<function=`。llama.cpp `--jinja` 若把它们收成 OpenAI `tool_calls`，QCB 可跑；收不成，smoke 会立刻以 invalid tool 暴露。**这本身就是 coding-agent 兼容性结果，不要为了迁就它改 QCB 工具协议。**
- 另有 MTP 仓 `ProCreations/grug-v1.1-qwen-3.8-27b-mtp`。主 GGUF 卡未宣称 MTP 头。第一轮用 16.5 GB 主文件、MTP 关；只有 smoke 过关且需要速度时再开第二 Config。
- 诚实损失（作者自报）：GSM8K 95.5 → 92.5；失败恢复 right-tool 相对 v1 回退。QCB 更关心空转和补丁，不关心小学应用题。

### 3.4 Fable-Distill

- 权重：<https://huggingface.co/TeichAI/Qwen3.8-27B-Fable-Distill>
- GGUF：<https://huggingface.co/TeichAI/Qwen3.8-27B-Fable-Distill-GGUF>
- 文件：`Qwen3.8-27B-Fable-Distill-Q4_K_M.gguf` **17.4 GB**（推荐默认）
- 数据：公开 Fable 5 chat/agent traces + 更大量的私有 Fable 5 / Claude Code 轨迹。
- MTP：**每档都把 nextn 头留在 BF16**（`blk.64.* = bf16`，约 424.7M）。可直接 `--spec-type draft-mtp --spec-draft-n-max 2`。
- **模板默认 `reasoning_effort=xhigh`。** 本轮必须用 `chat_template_kwargs` 打成 medium，否则和 WORK 的 medium 不可比，也会把思考预算打满。
- 作者公开基准只有 ARC/BoolQ（0.591→0.637 等），**没有 SWE/agent 数字。** 进名单是因为轨迹类型对齐 QCB，不是因为 ARC。

### 3.5 Salience-27B-R5

- 权重：<https://huggingface.co/vectionlabs/Salience-27B-R5>
- GGUF：<https://huggingface.co/bartowski/vectionlabs_Salience-27B-R5-GGUF>
- 文件：`vectionlabs_Salience-27B-R5-Q4_K_M.gguf` **17.77 GB**
- 定位：SWE、repo-scale edit、terminal agent；reasoning economy **默认 medium**（「模型自己决定想多久」）。
- `--jinja` 对 agent **不是可选项**：作者写明关掉会 malformed tool call，行为退回 stock。本机 binary 已带 `--jinja`。
- 工具：XML `<tool_call><function=...>`，由 llama-server jinja 收成 OpenAI `tool_calls`。
- bartowski imatrix：校准语料 **65.7% tool chunk**；MTP 层在 imatrix 量化里是 Q4_0。本轮仍开 MTP n=2，记录 acceptance；<50% 则该 Config 关 MTP 重跑（新 Config ID，不覆盖）。
- 作者 **没有发布可复现基准**。卡片写 “Published when they come from a run that reproduces.” QCB 是我们自己的证据。

### 3.6 Cold Fusion V1.1

- 权重：<https://huggingface.co/DavidAU/Qwen3.8-27B-Cold-Fusion-GAIN-V1.1>
- GGUF：<https://huggingface.co/DavidAU/Qwen3.8-27B-Cold-Fusion-GAIN-V1.1-NM-DAU-NEO-MAX-MTP-GGUF>
- 宣称：各 effort 下 think token 降到原版 1/5–1/2；NEO imatrix；MTP 档把 MTP 张量保持 Q8_0。
- **模板默认 xhigh。** 与 Fable 相同，请求里打 medium。
- 文件名很长且仓库同时有 regular / MTP / LOW。下载前先 `hf list`，选 **带 MTP、Q4_K_M、不含 LOW/AMD** 的单个 gguf。不要猜文件名写进脚本后就不管。
- Nightmedia 公开的是 Instruct 模式 ARC/BoolQ，不是 thinking+tools。对 QCB 参考价值低。
- 作者自报这是相对 Fable-Fusion-711 的「1–2 级」轻调。放 S/A、最后测：若前三个 finetune 已经在 Agent 环上赢了，它的价值是「更便宜的 think」；若前三个都还空转，再看压缩 reasoning 能不能停手。

### 3.7 量化公平性（必须写进每份报告）

| Config | 量化 | 能否当「智力差」 |
|---|---|---|
| WORK / Sharp | Unsloth **UD-Q4_K_XL** ~17.9 GB | Sharp vs WORK：是（同文件） |
| grug / Fable / Salience / Cold Fusion | 各家 **Q4_K_M** 16.5–17.8 GB | 否。差异 = 权重 ± 量化 ± 模板 |
| 以后若要隔离量化 | 用同一套 imatrix 重新量化所有权重 | 那是第二轮，见 QCB `docs/10` |

第一轮接受「Q4 级 4090 可部署系统」对比。不把 UD-Q4_K_XL vs Q4_K_M 解释成模型智商。

---

## 4. 实验设计（对齐 QCB，落到 4090）

细节契约以 QCB 为准：`docs/02` 赛道、`docs/04` 运行手册、`docs/05` 评分、`docs/06` 决策。这里只写本轮落地选择。

### 4.1 主赛道：Optimized

每个候选是一个 **可部署系统**：

```text
weights + GGUF + template + 同一 llama-server + 启动旗标 + 请求参数
```

锁死与 WORK 相同的部分：

| 项 | 值 | 例外 |
|---|---|---|
| binary | 现网 llama-server | 无 |
| 端口 / alias 模式 | `18343`，alias `openclaw/Qwen3.8-27B-EVAL` | 便于确认切到了候选 |
| `-ngl 999` `-np 1` `-fa on` `--jinja` | 同 WORK | 无 |
| KV | q8_0 | 只有 OOM 才允许降，且新 Config ID |
| MTP | n=2，若 GGUF 含 MTP 头 | grug 主文件预计无头 → MTP off，单列 |
| 思考 | **medium**，经 `chat_template_kwargs` | 禁止靠默认 xhigh「看起来更努力」 |
| 采样 | temp 1.0 / top_p 0.95 / top_k 20 / min_p 0 / presence 0 | 对齐 WORK，不是 example.toml 的 0.0 |
| `max_tokens` | 8192 | 无 |
| `max_tool_calls` | 40 | 不加 |
| 窗口 | 先试 `-c 112000` | 载入后余量 < 800 MiB 或 decode OOM → 65536，新 ID |
| QCB `lane` | `optimized` | 无 |
| `extra_body` | 必须带 `chat_template_kwargs` | 无 |

Normalized（Q4_K_M、32K、MTP off、temp 0、尽量同一模板）是 **第二波**，用来回答「权重本身有没有变好」。本轮不跑，除非 Optimized 出现「某个模型只在怪模板下能活」的争议。

### 4.2 阶段与样本

| 阶段 | Suite | Seeds | 何时跑 | 目的 |
|---|---|---|---|---|
| 0 | WORK core | 11,29,47（现网已在跑；smoke 用过 42） | **正在跑，勿打断** | 冻结基线 |
| 1 | smoke 12×1 | 42（与 WORK smoke 同 seed，可配对） | Sharp 先，其余按 §3.1 | 杀工具损坏 / 必空转 / 部署不稳 |
| 2 | core 32×3 | 11,29,47 | 仅 smoke 存活者 | 正式质量+效率 |
| 3 | finalists 27×5 | +71,97 | 最多 3 个 | 稳方差 |
| 诊断 | 单题 | 任意 | 不并入正榜 | 看空转轨迹 |

smoke 12 题：`SF001 SF002 BF001 BF004 RE001 RE004 RE007 AT001 AT002 LC001 CR001 CR002`。

### 4.3 4090 可行的 Latin-square

QCB 要求不要「先跑完模型 A 的 96 再跑 B」。单卡不能按题切换：17 GB 载入约 15–40 s，96×N 次切换会把日历拉爆。

**本轮 block = 一个 seed 的 32 题**，模型顺序按拉丁方轮换：

```bash
python3 docs/qwen38-coding-benchmark-4090-v1.0.0/scripts/latin_square_order.py \
  original-sharp-udq4xl grug-v1.1-q4km fable-q4km salience-r5-q4km coldfusion-v1.1-q4km-mtp
```

例（5 模型）：

```text
Block seed=11: Sharp → grug → Fable → Salience → ColdFusion
Block seed=29: grug → Fable → Salience → ColdFusion → Sharp
Block seed=47: Fable → Salience → ColdFusion → Sharp → grug
```

每个格子：切 systemd → 预热 2 次非正式请求 → 跑该 seed 的 32 题 → 记录温度/显存 → 切下一个。WORK 基线已经跑完，**不再进拉丁方**，只作冻结对照。

smoke 阶段模型少、题短，允许按「一个模型 12 题」串行，Sharp 固定第一。

### 4.4 smoke 存活门（预声明，禁止事后改）

相对 WORK smoke（Hard 3/12、invalid 0、valid-tool 96.7%、至少 3 题打满预算）：

**立刻淘汰（不进 core）：**

1. 基础设施错误率 > 0 且按规则重跑一次仍失败（崩溃、OOM 载入、端口死）。
2. Invalid output ≥ 25%，或 valid tool-call rate < 80%。
3. Hard = 0/12 **且** 全部 AT/RE 的 `patch_bytes=0`（根本不会打补丁）。
4. 工具协议不可用：连续非法 JSON / 非 OpenAI `tool_calls`，QCB 无法驱动。

**进 core：**

- Hard ≥ 3/12，或
- Hard ≥ 2/12 **且** `tool_budget_exhausted` 题数 < WORK，或
- AT/RE 出现至少一次成功 `apply_patch` 且公开测试有过绿。

**观察项（不单独淘汰，进 core 报告）：** CR JSON 是否合法；SF002 是否仍 40 次空转；reasoning token 中位数。

### 4.5 core 上「B 优于 WORK」门槛（QCB `docs/06`）

同时满足才允许讨论换现网：

- 六类等权配对 Hard 差的 95% CI 下界 ≥ −3pp；
- CBI 至少 +2pp（或报告里预先改阈值，本轮不改）；
- 最差类别无不可接受回退（repo_engineering / agent_tool 相对 WORK 不得崩到接近 0，若 WORK core 该类本身为 0 则改为「不得更差且应出现至少 1 个 Hard pass」）；
- 成功任务耗时下降不是因为早失败；
- `tool_budget_exhausted` 下降，或 AT/RE 的 `apply_patch` 次数/字节上升。

多模型 McNemar 用 Holm。缺 `(task, seed)` 的模型不进正式配对。

最终分类输出（不要只给总分）：

- 最高质量
- **最佳 Coding Agent**（主结论）
- 最佳成功任务 / 小时
- 最佳模板-only 提升（只可能是 Sharp）
- 最稳定
- 不推荐及原因

---

## 5. 4090 部署架构

### 5.1 原则

- **同一端口、同一 binary、互斥 systemd。** 与 TEXT 切换同一模式。
- 候选 unit **禁止 enable**。开机仍是 WORK。
- 下载走 `https://hf-mirror.com/`。GitHub 源码本轮不碰。
- 现网 GGUF 只读，不 `gguf-new-metadata` 改它。Sharp 只用 `--chat-template-file`。
- 评测时 OpenClaw 等于停机。必须在 core 结束后、用户确认的窗口里切。

### 5.2 磁盘布局

```text
/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf          # 现网，勿动
/data/models/qwen/qwen38-eval/
  templates/chat_template.jinja                               # Sharp v22.1
  templates/chat_template.jinja.sha256
  grug-v1.1/grug-27b-v1.1-Q4_K_M.gguf
  fable-distill/Qwen3.8-27B-Fable-Distill-Q4_K_M.gguf
  salience-r5/vectionlabs_Salience-27B-R5-Q4_K_M.gguf
  cold-fusion-v1.1/<实际文件名>.gguf
  SHA256SUMS

/home/hhtele/qwen38-27b-4090-eval-20260820/
  launch/production-eval.sh                                   # 由 CANDIDATE= 选择 -m / template
  launch/candidates.env
  systemd/openclaw-qwen38-eval.service

/home/hhtele/qcb-4090-baseline/
  config/<config-id>.toml
  results/<config-id>/
  logs-<config-id>-smoke.out
```

体积预算：四份 Q4 ≈ 70 GB。根盘清理后可用约 700 GB，足够。不要下 Q8 / BF16。

### 5.3 下载（GPU 空闲不必等，core 跑着就能下）

环境：

```bash
export HF_ENDPOINT=https://hf-mirror.com
mkdir -p /data/models/qwen/qwen38-eval/{templates,grug-v1.1,fable-distill,salience-r5,cold-fusion-v1.1}
```

Sharp 模板：

```bash
hf download peculiar-ragdoll/Qwen-Sharp-Chat-Templates chat_template.jinja \
  --local-dir /data/models/qwen/qwen38-eval/templates
sha256sum /data/models/qwen/qwen38-eval/templates/chat_template.jinja \
  | tee /data/models/qwen/qwen38-eval/templates/chat_template.jinja.sha256
```

四个 GGUF（aria2 与上次 WORK 下载同一套路，支持断点）：

```bash
download() {
  local repo="$1" file="$2" dest="$3"
  local url="${HF_ENDPOINT}/${repo}/resolve/main/${file}"
  mkdir -p "$dest"
  aria2c -c -x 8 -s 8 -d "$dest" -o "$file" "$url"
  (cd "$dest" && sha256sum "$file" | tee -a /data/models/qwen/qwen38-eval/SHA256SUMS)
}

download ProCreations/grug-v1.1-qwen-3.8-27b-gguf \
  grug-27b-v1.1-Q4_K_M.gguf \
  /data/models/qwen/qwen38-eval/grug-v1.1

download TeichAI/Qwen3.8-27B-Fable-Distill-GGUF \
  Qwen3.8-27B-Fable-Distill-Q4_K_M.gguf \
  /data/models/qwen/qwen38-eval/fable-distill

download bartowski/vectionlabs_Salience-27B-R5-GGUF \
  vectionlabs_Salience-27B-R5-Q4_K_M.gguf \
  /data/models/qwen/qwen38-eval/salience-r5
```

Cold Fusion 先列目录再下（文件名以仓库当时为准）：

```bash
python3 - <<'PY'
from huggingface_hub import list_repo_files
files = list_repo_files("DavidAU/Qwen3.8-27B-Cold-Fusion-GAIN-V1.1-NM-DAU-NEO-MAX-MTP-GGUF")
for f in files:
    n = f.lower()
    if n.endswith(".gguf") and "q4_k_m" in n and "mtp" in n and "low" not in n and "amd" not in n:
        print(f)
PY
```

Vision `mmproj` **本轮不下**。QCB 全是文本+工具。

预期墙钟：每文件约 10–12 分钟（上次 UD-Q4_XL 约 11 min @ 26 MiB/s）。四份加模板 ≈ 1 小时，可在 core 跑的时候做完。

### 5.4 启动脚本骨架

`/home/hhtele/qwen38-27b-4090-eval-20260820/launch/production-eval.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail
CANDIDATE="${CANDIDATE:?set CANDIDATE=sharp|grug|fable|salience|coldfusion}"
BIN=/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server
EVAL=/data/models/qwen/qwen38-eval
WORK_GGUF=/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf
CTX="${CTX:-112000}"
MTP_ARGS=(--spec-default --spec-type draft-mtp --spec-draft-n-max 2
          --spec-draft-type-k q8_0 --spec-draft-type-v q8_0)
TEMPLATE_ARGS=()
MODEL=""

case "$CANDIDATE" in
  sharp)
    MODEL="$WORK_GGUF"
    TEMPLATE_ARGS=(--chat-template-file "$EVAL/templates/chat_template.jinja")
    ;;
  grug)
    MODEL="$EVAL/grug-v1.1/grug-27b-v1.1-Q4_K_M.gguf"
    MTP_ARGS=()   # 主 GGUF 无 MTP 头；确认有头后再打开
    ;;
  fable)
    MODEL="$EVAL/fable-distill/Qwen3.8-27B-Fable-Distill-Q4_K_M.gguf"
    ;;
  salience)
    MODEL="$EVAL/salience-r5/vectionlabs_Salience-27B-R5-Q4_K_M.gguf"
    ;;
  coldfusion)
    MODEL="${COLDFUSION_GGUF:?set COLDFUSION_GGUF to the exact MTP Q4_K_M path}"
    ;;
  *) echo "unknown CANDIDATE=$CANDIDATE" >&2; exit 1 ;;
esac

exec "$BIN" \
  -m "$MODEL" \
  --alias openclaw/Qwen3.8-27B-EVAL \
  --host 0.0.0.0 --port 18343 \
  -ngl 999 --split-mode none --main-gpu 0 \
  -c "$CTX" -b 1024 -ub 512 \
  -np 1 -t 12 -fa on --jinja \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  "${MTP_ARGS[@]}" \
  --temperature 1.0 --top_p 0.95 --top_k 20 \
  --min_p 0.0 --presence_penalty 0.0 \
  --reasoning-budget 4096 \
  --reasoning-budget-message 'Stop thinking. State the answer or the next smallest action now.' \
  --chat-template-kwargs '{"enable_thinking":true,"reasoning_effort":"medium","preserve_thinking":false}' \
  --cache-prompt --cache-ram 2048 \
  --slot-prompt-similarity 0.10 \
  --metrics --predict 32768 \
  "${TEMPLATE_ARGS[@]}"
```

systemd `openclaw-qwen38-eval.service`：

```ini
[Unit]
Description=Qwen3.8-27B EVAL candidate on 18343 (not for boot)
After=network-online.target
Conflicts=openclaw-qwen38-work-64k.service openclaw-qwen38-text.service

[Service]
Type=simple
User=hhtele
Environment=CANDIDATE=sharp
EnvironmentFile=-/home/hhtele/qwen38-27b-4090-eval-20260820/launch/candidates.env
ExecStart=/home/hhtele/qwen38-27b-4090-eval-20260820/launch/production-eval.sh
Restart=on-failure
RestartSec=5
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

**不要** `systemctl enable` 这个 unit。`Conflicts` 保证和 WORK/TEXT 不能同时起。

切换：

```bash
# 评测窗口（需用户授权 GPU）
sudo systemctl stop openclaw-qwen38-work-64k.service
echo 'CANDIDATE=sharp' | sudo tee /home/hhtele/qwen38-27b-4090-eval-20260820/launch/candidates.env
sudo systemctl start openclaw-qwen38-eval.service

# 切回现网
sudo systemctl stop openclaw-qwen38-eval.service
sudo systemctl start openclaw-qwen38-work-64k.service
curl -sS http://127.0.0.1:18343/v1/models   # 必须仍是 openclaw/Qwen3.8-27B-WORK
```

### 5.5 切换后 2 分钟预检（失败不准开 QCB）

```bash
curl -sS http://127.0.0.1:18343/v1/models
curl -sS http://127.0.0.1:18343/props | python3 -c 'import sys,json; d=json.load(sys.stdin); print("alias", d.get("model_alias") or d.get("alias")); t=d.get("chat_template") or ""; print("sharp_terse", "Answer directly" in t); print("len", len(t))'
nvidia-smi --query-gpu=memory.used,memory.free,temperature.gpu,power.draw --format=csv
```

再用一条带 `tools` 的最小请求确认 OpenAI `tool_calls`（不要用正式题）。Sharp 预检必须看到 terseness 字符串，否则等于没换模板。

载入显存若 ≥ 23200 MiB，把该候选 `CTX=65536` 写成新 Config，不要硬撑 112K。

---

## 6. QCB 配置与命令

远端工作目录：`/home/hhtele/qcb-4090-baseline/`（已有 WORK 结果，不要覆盖）。

每个候选一份 toml，**禁止**写进 WORK 的 JSONL。

```toml
# config/original-sharp-udq4xl-optimized-112k-mtp2.toml
[model]
id = "original-sharp-udq4xl-optimized-112k-mtp2"
family = "Qwen3.8-27B"
file = "/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf"
sha256 = "bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372"
quantization = "UD-Q4_K_XL"
template_id = "sharp-v22.1-terse-medium"
notes = "Same WORK GGUF; llama-server --chat-template-file Sharp v22.1"

[endpoint]
base_url = "http://127.0.0.1:18343/v1"
model = "openclaw/Qwen3.8-27B-EVAL"
api_key = "not-needed"
timeout_seconds = 900

[inference]
lane = "optimized"
temperature = 1.0
top_p = 0.95
top_k = 20
min_p = 0.0
seed = 42
max_tokens = 8192
context_size = 112000
reasoning_effort = "medium"
mtp_enabled = true
tool_mode = true
max_tool_calls = 40
max_retries = 1
system_prompt_file = "config/system-prompt.txt"
extra_body = { chat_template_kwargs = { enable_thinking = true, reasoning_effort = "medium", preserve_thinking = false } }
```

grug / Fable / Salience / Cold Fusion：改 `id`、`file`、`sha256`、`quantization`、`template_id`、`mtp_enabled`（grug 第一轮 false）、`notes`。`endpoint.model` 一律 `openclaw/Qwen3.8-27B-EVAL`。Fable/Cold Fusion 的 notes 必须写明「作者默认 xhigh，本 Config 请求覆盖为 medium」。

跑之前：

```bash
python3 scripts/hash_model.py /data/models/qwen/qwen38-eval/grug-v1.1/grug-27b-v1.1-Q4_K_M.gguf
python3 scripts/collect_environment.py \
  --server-command "$(tr '\n' ' ' < /proc/$(pgrep -n llama-server)/cmdline | tr '\0' ' ')" \
  --output environment-original-sharp.json
```

smoke（例，Sharp）：

```bash
nohup python3 scripts/run_suite.py \
  --config config/original-sharp-udq4xl-optimized-112k-mtp2.toml \
  --suite smoke --seeds 42 \
  --output results/original-sharp \
  > logs-original-sharp-smoke.out 2>&1 &
```

core（仅存活者，按拉丁方的当前 seed）：

```bash
nohup python3 scripts/run_suite.py \
  --config config/grug-v1.1-q4km-optimized.toml \
  --suite core --seeds 11 \
  --output results/grug-v1.1 \
  > logs-grug-core-s11.out 2>&1 &
```

中断恢复用 `--resume`。进程在、SSH 断了不必管。

报告：

```bash
python3 scripts/audit_results.py \
  --results results/grug-v1.1/grug-v1.1-q4km-optimized-core.jsonl \
  --check-artifacts --json reports/grug-v1.1-core-audit.json

python3 scripts/generate_report.py --results results/grug-v1.1/...jsonl --output reports/grug-v1.1-core.md

python3 scripts/compare_models.py \
  --baseline results/work/work-udq4xl-optimized-112k-mtp2-optimized-core.jsonl \
  --candidate results/grug-v1.1/grug-v1.1-q4km-optimized-core.jsonl \
  --output reports/compare-work-vs-grug
```

仓库内同步副本：`output/qwen38-qcb-4090-baseline/`。

---

## 7. 日程（墙钟，单卡串行）

经验来自 WORK smoke：简单 PASS 20–80 s；空转题可到 850 s。按「平均 3–6 min/题、坏题 15 min」估。

| 步骤 | GPU？ | 估时 | 依赖 |
|---|---|---|---|
| A. 等 WORK core 96 | 已被占用 | 视当前进度，可能仍需十余小时 | 已在跑 |
| B. hf-mirror 下载 4 GGUF + Sharp | 否 | ~1 h | 可与 A 并行 |
| C. 写 systemd / toml / 哈希 | 否 | 30 min | B |
| D. Sharp smoke 12 | 是 | 1–3 h | A 结束 + 授权切 GPU |
| E. 其余最多 4 个 smoke | 是 | 4–12 h | D 的门 |
| F. 2–4 个存活者 × core 96，拉丁方 3 seed | 是 | 每个模型 12–24 h | E |
| G. 审计 + 配对 + 分类结论 | 否 | 2–4 h | F |
| H. 切回 WORK | 是 | 1 min | 任何评测窗口结束 |

日历：**下载可今天做；GPU 评测从 core 结束后起，完整 S 名单 core 可能要 4–7 个自然日。** 若只想尽快知道「有没有能打补丁的」，D+E smoke 一天内能出。

OpenClaw 在 D–F 期间不可用。建议按「一个候选 smoke + 切回 WORK」分窗，而不是连续占满一周，除非明确接受停机。

---

## 8. 执行清单（授权 GPU 之后按序勾）

**零、冻结**

- [ ] `wc -l` core JSONL = 96
- [ ] WORK core 审计通过
- [ ] 生成 WORK core 报告，复制到 `output/qwen38-qcb-4090-baseline/reports/`
- [ ] 用户确认可以停 OpenClaw

**一、下载（可提前）**

- [ ] Sharp `chat_template.jinja` + sha256
- [ ] grug Q4_K_M 16.5G
- [ ] Fable Q4_K_M 17.4G
- [ ] Salience Q4_K_M 17.77G
- [ ] Cold Fusion MTP Q4_K_M（列目录后选定）
- [ ] `SHA256SUMS` 写入 toml

**二、Sharp（第一个）**

- [ ] stop WORK，start eval `CANDIDATE=sharp`
- [ ] `/props` 含 terseness
- [ ] 最小 tools 请求成功
- [ ] QCB smoke seed 42
- [ ] 对照 WORK smoke：Hard、空转、`apply_patch`、CR JSON
- [ ] 切回 WORK，除非连续评测已授权

**三、权重候选 smoke**

对每个存活门尚未判定的模型：切 eval → 预检 → smoke 42 → 按 §4.4 判定 → 切回或留下跑下一个。

顺序固定：grug → Fable → Salience → Cold Fusion。中途某只明显工具协议失败，立即记「不推荐 / 不兼容 OpenAI tools」，不要修 QCB 去迁就。

**四、core**

- [ ] 拉丁方顺序落盘
- [ ] 每 (模型, seed) 独立 JSONL 或同一 JSONL 的 `--resume`，Config ID 不得混写
- [ ] 每 block 记录温度、功耗、显存峰值、MTP acceptance
- [ ] 全部 core 结束后才跑 `compare_models.py`

**五、收尾**

- [ ] `systemctl start openclaw-qwen38-work-64k.service`
- [ ] `curl /v1/models` = WORK
- [ ] eval unit 保持 disabled
- [ ] 分类结论写入 `output/qwen38-qcb-4090-baseline/reports/00-s-list-decision.md`

---

## 9. 风险与已知陷阱

| 风险 | 证据 | 处理 |
|---|---|---|
| 顶层 `reasoning_effort` 无效 | WORK 已踩；Sharp 卡也写了 | 只信 `chat_template_kwargs` |
| Fable / Cold Fusion 默认 xhigh | 两份模型卡 | 请求覆盖 medium；预检 `/apply-template` 不得出现 xhigh 注入句 |
| grug xhigh 伤害选工具 | 作者表 97.1 → 76.5 | 禁止「加点思考试试」 |
| grug/Salience XML tools | 模型卡 | smoke 第一题就能看出来；失败 = 兼容性结论 |
| `--chat-template-file` 忘传 | Sharp 卡：忘一次就回到嵌入模板 | 每次预检 grep terseness |
| 改现网 GGUF 元数据 | 不可逆踩踏 WORK | 只用 flag |
| 112K + 略大的 Q4_K_M + q8 KV OOM | WORK 空载已 22.7 GB | 降到 64K 新 Config |
| MTP acceptance < 50% | Cold Fusion / bartowski 卡警告 | 关 MTP 新 Config，不覆盖 |
| `pkill -f` 误杀 SSH | 历史事故 | 只用 systemctl |
| core JSONL `--overwrite` | 会毁掉基线 | 禁止 |
| 把 smoke 25% 当智力分 | 已有记忆结论 | 正式只看 core 配对 |
| 作者 ARC/HumanEval | Fable ARC +0.046；grug HE 94.5 | 不进决策表 |
| 评测占 18343 | 单卡 | 窗口外切回 WORK |
| Normalized/Optimized 混读 | QCB 06 | 报告标题写死 lane |

---

## 10. 本轮明确不做

- FastMTP、DFlash2、新编 llama.cpp。
- Pearson / Ridge 量化第二轮（QCB `docs/10` 矩阵里有，本文件不管）。
- Hauhau TEXT、任何 uncensored 当 coding agent。
- 给空转模型加 `max_tool_calls`。
- 把 Dirk GGUF 和 Sharp flag 同时当两个主候选（重复权重）。Dirk 只作 Sharp 失效时的备援。
- 未授权 `systemctl enable` 候选、改 NGINX、改 28343 鉴权。
- 在 WORK core 未满 96 时抢 GPU。

---

## 11. 决策表（core 跑完再填）

| Config | Hard | CBI | Worst | tool_budget_exhausted | apply_patch 成功题 | 成功任务 P50 s | 成功 completion token P50 | 判定 |
|---|---|---|---|---|---|---|---|---|
| WORK（基线） | | | | | | | | 冻结对照 |
| original-sharp | | | | | | | | 模板-only |
| grug-v1.1 | | | | | | | | |
| fable-distill | | | | | | | | |
| salience-r5 | | | | | | | | |
| coldfusion-v1.1 | | | | | | | | |

主结论只允许四选一：

1. **Sharp 就够了** — 权重不用换，现网加 `--chat-template-file`。
2. **换某个 finetune 做 WORK** — 过 §4.5，另开授权窗口做 systemd 切换方案。
3. **没有优于 WORK 的 coding agent** — 全部保留为实验档，现网不动。
4. **工具协议不兼容** — 该权重淘汰，不归咎 QCB。

---

## 12. 文档与代码锚点

| 文件 | 用途 |
|---|---|
| 本文 `docs/qwen38-4090-coding-agent-s-list-plan.md` | 本轮部署+测试方案 |
| `docs/qwen38-coding-benchmark-4090-v1.0.0/docs/02-environment-and-lanes.md` | Normalized vs Optimized |
| `docs/qwen38-coding-benchmark-4090-v1.0.0/docs/04-runbook.md` | 冻结、resume、故障分类 |
| `docs/qwen38-coding-benchmark-4090-v1.0.0/docs/05-scoring-and-statistics.md` | Hard / CBI / 工具指标 |
| `docs/qwen38-coding-benchmark-4090-v1.0.0/docs/06-comparison-and-decision.md` | 胜出规则 |
| `docs/qwen38-coding-benchmark-4090-v1.0.0/docs/10-qwen38-variant-test-matrix.md` | 更长的变种矩阵（含第二轮量化） |
| `OPENCLAW_QWEN38_4090_RUNBOOK.md` | 现网启动参数与回切 |
| `output/qwen38-qcb-4090-baseline/config/work-udq4xl-optimized-112k-mtp2.toml` | 基线 Config |

卡片核对时间：2026-08-20。若下载时文件名或体积与 §3 不一致，以 hf-mirror 当时列表 + sha256 为准，并在 toml `notes` 写差异。不要用过期文件名硬下。

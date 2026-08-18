# 来源与取舍

检索时间：2026-08-18。只收录直接影响本方案 flags / 评测标准的来源。社区速度数字一律当对照带，不当本机验收值。

## 1. 官方

### Qwen3.8-27B 模型卡

https://huggingface.co/Qwen/Qwen3.8-27B

已核对的要点：

- Dense 27B，hidden 5120，64 层，原生 ctx 262144，带 MTP。
- Thinking 默认开；`reasoning_effort`：`xhigh`（默认）/ `medium` / `low`。
- `preserve_thinking` 默认开。
- Thinking 采样：`temperature=1.0, top_p=0.95, top_k=20, min_p=0.0, presence_penalty=0.0, repetition_penalty=1.0`。
- Instruct / no-think 采样：`temperature=0.7, top_p=0.80, top_k=20, min_p=0.0, presence_penalty=1.5`。
- 官方警告：多轮 agent 里降低 effort 不一定省总时间，分析不足会换来重试。
- SWE-bench Pro 等主榜用 `temp=1.0, top_p=0.95`，不是 greedy。

取舍：工作档采样跟 thinking 官方值；`top_k=30` 只出现在社区 24GB 帖，本方案默认 20，S2 不把它当主变量。

### Unsloth 本地文档

https://unsloth.ai/docs/models/qwen3.8

- 推荐 GGUF：`Qwen3.8-27B-UD-Q4_K_XL`
- CLI 采样：`temp 1.0 / top_p 0.95 / top_k 20 / min_p 0.0`

取舍：本机已有这份 XL，不改成帖子里的 `Q4_K_M`。

## 2. X：24GB llama.cpp 配方

### Yume_X 汇总帖（主来源）

- 主帖：https://x.com/yume_arasaki/status/2088689204041769057 （约 11 万浏览，2026-08-15）
- 完整 flags：https://x.com/yume_arasaki/status/2088689423554920813

24GB 车道（3090 / 4090 / 5090）：

```text
llama-server -m Qwen3.8-27B-Q4_K_M.gguf
-ngl 999 -fa on --jinja
-np 1 -t 12
--spec-default --spec-type draft-mtp
--spec-draft-n-max 2
--spec-draft-type-k q8_0 --spec-draft-type-v q8_0
--cache-type-k q8_0 --cache-type-v q8_0
--temperature 1.0 --top_p 0.95 --top_k 30
--min_p 0.0 --presence_penalty 0.0
```

帖内约束：

- 钉死 `n-max=2`；2 是甜点，3 是天花板，4 打坏 head。
- reasoning 设 medium，默认 xhigh 烧 token。
- 活在 100K+：KV 换 `f16`（mmike87）。量化 KV 长窗口推理会坏。

### AJ（3090 实测命令）

- MTP 开关：https://x.com/ItsmeAjayKV/status/2088333689952583902
- 更新完整命令：https://x.com/ItsmeAjayKV/status/2088407570562134021

```text
--spec-default --spec-type draft-mtp
--spec-draft-type-k q8_0 --spec-draft-type-v q8_0
--cache-type-k q8_0 --cache-type-v q8_0
temp 1.0 / top_p 0.95 / top_k 30
reasoning = medium
```

AJ 第一版没钉 `n-max`。Yume_X 明确指出要补 `--spec-draft-n-max 2`。

### sudoingX

- Qwen3.5 时代的 q8 KV 帖：https://x.com/sudoingX/status/2026956270574657897
- Qwen3.8 MTP 仓库（Yume_X 引用）：https://github.com/sudoingX/qwen38-mtp

贡献：把权重里已有的 MTP head 接到 `--spec-type draft-mtp`，并做 probe / 社区表。

### keys / drowzeys MTP 梯子

Yume_X 引用：n=1 1.75x / n=2 2.37x / n=3 2.85x / n=4 crash。单层 MTP。  
仓库：https://github.com/drowzeys/keys-vLLm.0.27-Qwen3.8-NVFP4-MTP3-Single-DGX-Spark  
首跑：https://x.com/u1tra_instinct/status/2088387885548417402

数字来自 Spark / NVFP4，倍数不能直接套 4090，但 **n=4 非法** 这条对架构成立。

## 3. X：4090 速度与质量

### Eric / Hermes（4090 + M2 Max）

https://x.com/outsource_/status/2088743329760469374

- 4090 no-spec 44.9 tok/s（与 08-17 的 44.6 吻合）
- 优化 MTP 后一般 86.5，编码 97.3
- 深度甜点：Mac 上 2，4090 上他们写 3–4。**与单层 head / n=4 打坏 冲突**。本方案把 n=3 当对照、n=4 当负对照，不把该帖的 3–4 当默认。
- 131K 仍有 48 tok/s；262K 掉到 4.1。实用窗口 32K–131K。
- Q4 质量 14/22 vs Q5 15/22。

### 其他速度样本

- 2×3090 Q8_K_XL + MTP，C4 聚合约 69 tok/s，256K 仍稳：https://x.com/geldeki/status/2088568947012444499
- Q6_K、262K、KV q4、MTP n=2：https://x.com/hypertectonic/status/2089358160695898125
- LM Studio 65K Q4_K_M 约 40 tok/s：https://x.com/alexokita/status/2089513369669898248
- 有人用 UD-Q4_K_XL + KV Q8 + 128K 远达不到 115 tok/s：https://x.com/sbasiliss/status/2089539663296094259

结论：单卡 24GB 现实带是 40–100 tok/s，取决于量化、ctx、MTP、是否在思考。115+ 需要对拍配置，不能当目标 KPI。

## 4. Reasoning 控制

### 模板默认 xhigh，顶层参数会被吞

https://x.com/petko_petkovvvv/status/2089039822358761697

- Jinja：`reasoning_effort|default('xhigh')`
- Roo Code 传顶层 `reasoning_effort=low`，llama.cpp 不转发 → 实际 xhigh
- 必须 `chat_template_kwargs={"reasoning_effort":"medium"}`
- Sentinel：`"banana"` 走顶层 → 200 被忽略；走 kwargs → 模板 400
- 硬编码任务：xhigh 18k 超时；low 17k 超时；medium 12k 且 4/4 修掉
- 5090 + Q6：medium 后思考 638→23 token，首动 10.9s→0.7s

### effort 只是软提示

https://x.com/rS_alonewolf/status/2088474591127855494

`reasoning_effort` 在 vLLM/SGLang/llama.cpp 都是往系统提示注入，不是硬预算。

### 硬预算 / inception

- ggerganov：https://x.com/ggerganov/status/2089214161884414147  
  思考超时后注入一段 thought，逼模型行动。
- Michael Guo 落到 Qwen3.8：https://x.com/Michaelzsguo/status/2089428942973173932  
  `--reasoning-budget 4096` + cutoff message
- 用户提供的工作配方：预算 `16384`，message 明确 **禁止重做分析**，只陈述假设并分类 `success | issue | indeterminate`

取舍：软开关（medium）+ 硬预算（16384）+ 反重做文案。4096 可能切太早，放进 S3 对照。

### 关掉 thinking 的代价

https://x.com/YoutechA320U/status/2088534589937795259

ELYZA-tasks-100，Q4_K_M：3.8 xhigh 4.36 / no_think 4.49，低于 3.6 的 4.57/4.58。说明 xhigh 会乱跑，关思考也不等于自动更强。必须用任务通过率选档，不能只看“开没开”。

## 5. KV / 模板 / MTP 深度（非 X 主帖）

| 来源 | 结论 | 链接 |
|---|---|---|
| mmike87 | 100K+ 量化 KV 变蠢，全精度“night and day” | https://forums.developer.nvidia.com/t/the-best-2x-spark-qwen-3-6-27b-recipe/375360 |
| PurpleDoubled | GGUF 体积、KV 技巧、`--jinja` 失败模式、空 think 块跨轮嵌套 | https://dev.to/purpledoubled/run-qwen-38-27b-locally-real-gguf-sizes-the-kv-cache-trick-and-the-template-trap-114j |
| llama.cpp #23751 | MTP 自带 KV 成本，draft cache 需单独量化 | https://github.com/ggml-org/llama.cpp/discussions/23751 |
| left curve（3.6 时代） | n=2 + p-min 0.75；n=6 无额外收益；MTP 多占约 1GB | https://x.com/leftcurvedev_/status/2055696914767647027 |
| 08-17 本机 help | `--spec-draft-n-max` 默认 3；`--spec-draft-p-min` 默认 0.00 | `reports/02-llama-cpp-zip-build.md` |

dev.to 页本轮工具侧被 SSRF 拦截，未重新抓正文；内容以 Yume_X 对 PurpleDoubled 的转述为准。

## 6. 明确不采用的车道

| 车道 | 原因 |
|---|---|
| Blackwell / Spark + vLLM NVFP4 | 4090 是 Ada。Mia：https://x.com/MiaAI_lab/status/2088301780312441236 |
| 96GB RTX 6000 PRO 的 util 0.75/0.80 | 与 24GB 无关 |
| IQ2 / 过度量化 | https://x.com/hellohazime/status/2089529715896017184 质量差 |
| 关 MTP、堆 ctx 到 262K | 4090 上 decode 会崩到个位数 |
| 把 Qwen3.6 的 MTP n=4 + p-min 0.75 + KV q4 原样搬过来 | 08-17 就是这么干的，和 3.8 社区配方冲突 |

## 7. 本方案如何合并冲突

| 冲突 | 选择 | 理由 |
|---|---|---|
| 社区 `Q4_K_M` vs 本机 `UD-Q4_K_XL` | XL | 已在盘、Unsloth 推荐、体积同级 |
| 社区 `top_k=30` vs 官方 `20` | 20 | 质量优先，跟模型卡 |
| AJ 不设 n-max vs Yume_X 钉 2 | 钉 2 | binary 默认 3；4 危险 |
| Eric 4090 说深度 3–4 vs 单层 head 说 4 非法 | 默认 2，测 3，否决 4 | 用本机 junk/任务门禁裁决 |
| 社区 p-min 不设 vs 08-17 p-min 0.75 | 默认不设，0.75 对照 | 0.75 是 3.6 抬 n=4 的补丁 |
| 官方 preserve_thinking on vs 64K 预算 | 默认 off | 防多轮上下文膨胀 |
| 官方默认 xhigh vs 社区 medium | medium + 16384 | xhigh 与紧预算冲突；medium 有硬任务正例 |
| 关 thinking 换短输出稳定 | 仅 `work-fast` | 关思考测的不是 3.8 的工作形态 |
| 100K+ 换 f16 KV | 不做 100K f16 | 24GB 放不下；改为 32K f16 对照 + 64K q8 默认 |

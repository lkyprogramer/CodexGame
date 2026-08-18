# Qwen3.8-27B 能力深测方案

日期：2026-08-18  
对象：现网 `192.168.10.29` 上的 `openclaw/Qwen3.8-27B-WORK`（64K / q8 KV / MTP n=2 / medium + budget 钳制）  
本文只出方案，不改生产、不跑题。

## 1. 直接结论

上一轮（S0–S7 + 空正文补丁）已经回答了 **能不能当 4090 主力**。它没有回答 **这台量化 3.8 在真实工作维度上有多强、弱在哪、该怎么用**。

官方卡上的 61.7 SWE-bench Pro / 90.3 LiveCodeBench / 89.2 GPQA 是 BF16 + Claude Code + 256K 的数字，不能拿来当本机 UD-Q4_K_XL @ 64K 的成绩。社区已经出现和官方叙事冲突的本地结果：

- Dogukan BenchKit（1083 题）：**none→low 提升最大，low≈medium，xhigh 不涨分还烧 3× token**
- Context Arena 8-needle MRCRv2：**medium 92.8 AUC@128k，关思考掉到 43.1，xhigh 比 medium 差 6 分**
- ELYZA-tasks-100（Q4_K_M）：3.8 xhigh 4.36 / no_think 4.49，低于 3.6
- OpenCodeReview 真 PR：实现代码 8/9，**测试代码里的隐蔽问题 0/2**

本方案因此不追求复现官方全榜，而是在 **本机真实 serving** 上跑一套可自动判定、能分出强弱的深测。默认思考档固定 **medium**（与现网一致）；none/low/xhigh 只在 T9 对照。

两条执行档：

| 档 | 墙上时间（单卡） | 题量 | 何时用 |
|---|---|---|---|
| **Core** | 8–10 h | ~180 自动题 + 12 真工作题 | 先跑，够写能力画像 |
| **Full** | 18–22 h | Core + 加厚竞赛/长上下文/多语言 | 要对齐社区榜再跑 |

## 2. 上一轮测过什么、缺什么

已覆盖（不要再当主线重跑）：

- 协议、MTP 深度、reasoning 预算、空正文补丁、cache、47K 交叉三事实
- 8 道合成工作题（JSON / 工具 5 轮 / top_k / clamp / 45s→5s / 安全拒绝）

明显缺口：

| 维度 | 官方/社区在测 | 我们测过 | 风险 |
|---|---|---|---|
| 竞赛/算法代码 | LiveCodeBench、HumanEval+ | 两个玩具函数 | 高估“会写代码” |
| 多文件编辑 | Aider Polyglot、SWE-bench | 无仓库级编辑 | 不知道能不能改 repo |
| 指令遵循 | IFBench 79.5 | 禁 fence + 恰好两字段 | 复杂约束未知 |
| 科学推理 | GPQA Diamond 89.2 | 无 | 量化是否伤硬推理未知 |
| 长上下文推理 | MRCRv2，关思考崩盘 | 单次三事实拼接 | 多针/多跳未知 |
| 工具调用精度 | BFCL | 一轮 read_file | 并行/多参数/幻觉未知 |
| 代码评审 | 真 PR A/B | 一条合成 diff | 测代码盲区已被社区点名 |
| 中文专业 | ELYZA、职场题 | 几乎没有 | 日常工作语言未测 |
| 重试价值 | pass@2 抹平 27B vs 397B | 只看 pass@1 | 可能低估可用率 |

## 3. 设计约束

1. **只打现网 18343**。不停服务、不换量化、不加 mmproj。视觉/OSWorld 本轮不做。
2. **判定必须可执行或可解析**。禁止 1–5 主观分当主指标。允许 LLM-as-judge 只作附录。
3. **采样 = 现网**：thinking medium，`temp=1.0 top_p=0.95 top_k=20`。`max_tokens` 默认 8192（补丁会按 reserve 钳思考）。短契约题 512。
4. **pass@1 为主，T1/T2/T8 对失败题补 1 次 pass@2**。这是 Benjamin Marie 对 27B 编码的核心观察。
5. **64K 是硬顶**。长上下文只做到 8/32/56K，不测 128K。
6. **每题落盘** request/response/result + 墙钟 / 思考 token / 空正文 / junk。
7. 不把本机分数和官方卡数字并列成“复现成功”。对照栏只写 *reference, different stack*。

## 4. 套件

### T1 可执行短代码（Core）

目的：建立编码地板，避免只用两个自定义函数下结论。

| 来源 | 取多少 | 判定 |
|---|---|---|
| HumanEval+（evalplus） | 40，按官方编号抽样 0,4,8… | `evalplus` 隐藏测试 |
| MBPP+ | 40，同样抽样 | 同上 |

- https://github.com/evalplus/evalplus
- 社区 Dogukan 也用这两套扫 reasoning 档

通过标准：记录 pass@1；失败再试 1 次得 pass@2。Core 期望：pass@1 ≥ 0.75，pass@2 ≥ 0.85。达不到就写“短函数能过、泛化不行”。

### T2 竞赛代码切片（Core 20 题 / Full 40 题）

目的：官方最耀眼的 90.3 LiveCodeBench 在 Q4+64K 还剩多少。

- 来源：LiveCodeBench v6，只取 **2025-01 之后** 的 medium/hard，降低污染。  
  https://livecodebench.github.io/
- 本地用公开题目 + 官方测试输入，不跑全 1055 题（Benjamin 全量是 17.8M 输出 token，单卡不划算）。
- 每题时限 180s 生成 + 10s 评测。

对照：官方 90.3 是全量 + 长窗口。本机 20 题 hard 切片若 < 50%，说明“竞赛编码”不能当卖点。

### T3 多语言仓库编辑（Core 24 题 / Full 48 题）

目的：这才是 OpenClaw / Aider 的工作形态。

- Aider Polyglot：Exercism，C++ / Go / Java / JS / Python / Rust。  
  https://aider.chat/docs/leaderboards/
- Core：Python 8 + TypeScript/JS 8 + Go 8。Full 再加 Java/Rust。
- Harness：给仓库快照 + 失败测试，要求 unified diff 或整文件；`apply` + 原测试。
- 社区已有人把 3.8 当 Aider 实现担当（@MahjongNm、@loisirou），但缺公开数字。

通过：apply 成功且测试绿。记录“格式错 / 编译失败 / 测试红 / 超时”。

### T4 指令遵循（Core）

目的：官方 IFBench 79.5 是否在量化+中文约束下还在。

| 来源 | 数量 | 判定 |
|---|---|---|
| IFEval 公开集 | 50 条抽样 | 官方约束检查器 |
| 自建硬约束 | 20 | 程序检查 |

自建必须覆盖上一轮没测过的：

- 恰好 N 个 bullet、禁止某词、必须包含 URL、输出语言锁定中文/英文
- JSON Schema 多一层嵌套 + `additionalProperties=false`
- “先给结论再给证据，结论不得超过 20 字”
- 工具调用时禁止在 content 里复述完整命令行

IFEval：https://github.com/google-research/google-research/tree/master/instruction_following_eval

### T5 硬推理（Core 30+8 / Full 再 +20）

目的：量化 KV + Q4 会不会把 GPQA 那种题打残。

- GPQA Diamond 抽样 30（选择题，答案哈希比对）。不要外泄整集到报告。  
  https://huggingface.co/datasets/Idavidrein/gpqa
- AIME 2024/2025 抽样 8（数字答案）。
- Full：再加 10 道研究生物理/CS 自建题（有唯一短答案）。

官方 GPQA-D 89.2 仅作参考。本机 30 题若 < 60%，说明“科研推理”不能当本地卖点。

### T6 工具调用精度（Core）

目的：从“会叫一次 read_file”升级到 BFCL 那种结构正确性。

构造 40 条，风格对齐 BFCL V4，不必跑完整官方 harness：  
https://gorilla.cs.berkeley.edu/leaderboard.html

分布：

- 10 单工具正确参数
- 10 多工具顺序（read → 根据结果再 call）
- 8 并行（一次两个独立 tool_calls）
- 6 不应调用（纯闲聊 / 缺信息）
- 6 幻觉抑制（工具列表里没有 `rm` / `git_push`，不得编造）

判定：name 精确匹配 + JSON schema 验证 + 并行条数。不算自然语言像不像。

### T7 长上下文多针（Core 三个窗口 / Full 加倍针数）

目的：补上 MRCRv2 指出的“关思考会崩、xhigh 更差”。

- Context Arena / GDM-MRCRv2 8-needle 思想：多条事实分散放置，问交叉题。  
  https://x.com/DillonUzar/status/2089170939120378145
- Core：8K / 32K / 56K 各 8 题（4 单针召回 + 4 必须交叉 2–3 条）。语料用本仓库真实代码+日志，不用 ASCII 重复块。
- Full：每窗再加 4 题“无关干扰针”。
- 默认 medium。T9 才对 8 题子集扫 none/low/xhigh。

64K 卡死，不测 128K。社区 128K 数字只写进讨论，不当本机 KPI。

### T8 真工作题（Core，决定你怎么用它）

目的：把能力映射到你的日常，而不是榜。

**A. CodexGame 仓库（8 题，可自动验）**

1. 指出 `packages/simulation` 里某条 action 的确定性破坏（给坏 patch，要求找出）
2. 给 `AgentTurnOutput` 加字段的最小协议改动清单（必须点到 `packages/protocol` 先行）
3. `tickMs` / `schedulerMs` 被改乱后的回归测试建议（必须引用 200 / 500）
4. 客户端把模拟权威搬进 Phaser 的 diff 评审（必须拒绝）
5. `contentStore` 非原子写的修复（必须保留 tmp+rename）
6. 根据 `ui-contract.integration.test.ts` 风格补一条失败用例
7. 从 runtime 日志定位 WS `type:error` 丢失的风险
8. 只读诊断：reconnect circuit breaker 为什么是硬上限

判定：关键词 + 必要文件路径 +（能写代码的）编译/单测。

**B. 代码评审（4 份真实风格 diff）**

对齐 Vladimir 的 OpenCodeReview 发现：实现代码尚可，**测试里的微妙问题会漏**。  
4 份固定 diff：事务边界、超时、测试里 `sleep` 当同步、可变默认参数。  
每份预埋 2–4 个 must-find。漏测代码问题要单独记一栏。

**C. 中文后端/数据库（10 题）**

面向你的日常，全部短答案或可执行：

- 可重复读 vs 幻读，给隔离级别
- 一条会在 RR 下写偏斜的 SQL，要求改
- 索引选择（等值 + 范围 + 排序）
- 在线 DDL 风险
- Java 线程池 + 事务挂起
- 幂等消费（Kafka 重复投递）
- 分布式锁误用
- 慢查询计划误判
- JSON 契约兼容（加字段 vs 改语义）
- 一次事故手牌：只给现象，要最小下一步（对应预算切断后的工作姿势）

### T9 思考档对照（Core，小样本）

目的：在 **本机 serving** 上验证社区“别用 xhigh”是不是也成立。

从 T1 失败集 + T2 hard + T5 各抽，凑 20 题。每题跑 none / low / medium（Core）。Full 再加 xhigh。

主指标：正确率、思考 token、墙钟、空正文。  
预期（社区先验）：medium ≈ low ≥ none；xhigh 更慢且不一定更准。若本机打脸，现网默认要改。

## 5. 明确不跑

| 东西 | 原因 |
|---|---|
| 全量 SWE-bench Pro / Terminal-Bench | Claude Code + 256K + 数小时/题，单卡 64K 不是同一个实验 |
| OSWorld / WebArena / 视觉 | 现网没加载 mmproj |
| 全量 LiveCodeBench 1055 | token 成本过高；切片足够定性 |
| 裸 HumanEval、HellaSwag、纯 needle | 2026 年本地评测里已被标成低信息 |
| 和云端 Opus/GPT 的正式对打 | 需要另一套付费 API 和相同 harness |

官方数字进报告的“参考”列，不进“本机成绩”列。

## 6. 执行顺序与停机

单卡，打现网。T3 会改临时工作树，不要动 CodexGame 主工作区，用 `/tmp/qwen38-eval-workspaces`。

```text
T4 IF          快，先确认契约没回归
T6 Tools       快
T1 HumanEval+  地板
T8 真工作      你最关心的画像
T5 GPQA/AIME   硬推理
T2 LCB 切片    竞赛
T3 Aider       最像日常编码
T7 长上下文    预填慢
T9 档位对照    最后，避免污染默认
```

Core 中途可以停：T4+T6+T1+T8 跑完就够出第一版能力报告。

## 7. 最终报告必须回答的问题

报告路径预定：`output/qwen38-27b-4090-20260818/reports/11-capability-portrait.md`

只允许用本机证据回答：

1. 这台 Q4 3.8 **会写短函数，还是会改仓库**？
2. 竞赛题和官方 90.3 差多远？差值来自量化、64K，还是切片偏差？
3. 指令遵循是否配得上 IFBench 79.5 的印象？
4. 硬推理是否被 Q4/q8 KV 打残？
5. 工具调用会不会编造不存在的函数？
6. 64K 内多跳检索能不能用？关思考会不会像 MRCRv2 那样崩？
7. 对 CodexGame / Java 后端，它可靠的边界在哪？
8. 现网默认 medium 是否仍正确？要不要改 low？
9. pass@2 值不值得在 OpenClaw 里做自动重试？

结论只许三选一，并引用套件数字：

- **主力够用**：短码+仓库编辑+真工作题都过线，硬推理可接受
- **限场景主力**：只适合评审/短修复/JSON，不适合竞赛或长上下文多跳
- **能力不足**：T1 或 T8 全面低于门槛，需要换量化或换模型

## 8. 来源

| 来源 | 用在 |
|---|---|
| https://huggingface.co/Qwen/Qwen3.8-27B | 官方分数，仅参考 |
| https://livecodebench.github.io/ | T2 |
| https://github.com/evalplus/evalplus | T1 |
| https://aider.chat/docs/leaderboards/ | T3 |
| https://github.com/google-research/google-research/tree/master/instruction_following_eval | T4 |
| https://huggingface.co/datasets/Idavidrein/gpqa | T5 |
| https://gorilla.cs.berkeley.edu/leaderboard.html | T6 形态 |
| https://x.com/DillonUzar/status/2089170939120378145 | T7 / T9 先验 |
| https://x.com/bnjmn_marie/status/2089384210591355340 | pass@2、LCB token |
| Dogukan BenchKit / Grok 转述 2089470770904793142 | T9 档位 |
| https://x.com/VladBrejcha/status/2088665246848409623 | T8 评审盲区 |
| https://x.com/YoutechA320U/status/2088534589937795259 | ELYZA，中文质量对照 |
| 本仓库 `output/hermes-bench`、`model-compare-*` | 可复用旧题，不重复造轮子 |

## 9. 假设与风险

- 假设现网 18343 在评测期间保持当前配方。若中途改 MTP/预算，整份作废。
- HumanEval 有污染风险，所以 T1 用 HumanEval+ 隐藏测试，T2 只用较新题目。
- GPQA 题目不得进 git 全文；报告只写对错统计。
- T3 工作树磁盘和测试依赖（go/node/jdk）若机器缺编译器，降级为 Python+JS only，并在报告里标明。
- 单卡排队时 OpenClaw 会变慢。评测窗口建议你知情。

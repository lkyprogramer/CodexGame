# NInfer baseline 精简：长任务评测的一手资料

调研日期：2026-10-21。范围：为 NInfer / Qwen3.8-27B 单 4090 后端改造提出评测取舍建议；本文未修改运行计划，未下载任务镜像、启动模型、测试或服务。以下“事实”来自已读取的一手资料；“建议”是针对本项目的推断，不代表来源要求，也不是实测结果。

## 结论

建议采用“少量真实长任务 + 分层回归”，而不是把更多 benchmark 与现有参数矩阵做笛卡尔积。按主代理补充的本地盘点，最少可落地方案应复用已有 3 个真实闭环任务与 QCB-4090 v1.0.0 题库，再从 SWE-bench Multilingual 选 2 个真实 Java repo 任务作为长程 holdout；不另造一组小 fixture。完整集合仅比较原 baseline 与最终候选，阶段内使用固定小子集。少量任务只能作为工程回归哨兵，不能证明总体编程能力没有下降。

来源子集使用自定义 agent、预算和题目选择时，只报告本项目内部成功率与逐题结果，不报 SWE-bench/Terminal-Bench 官方分数。“长程”指跨文件、多步骤、上下文与工具状态持续增长，不要求模型必须耗尽时长；超时是上限，提前交付应立即评分。

优先借用的机制是固定仓库/镜像、F2P/P2P、隐藏评分器、独立重放补丁、固定 agent/预算、逐任务配对和时间/质量同时报告。不要把“多跑 token 长度/采样/cache 组合”视为长时编程能力证据。

## 证据与适用边界

| 一手资料 | 已核实事实 | 本次取舍建议 |
|---|---|---|
| [SWE-bench Verified 官方说明](https://openai.com/index/introducing-swe-bench-verified/) | 500 个人工筛选任务；提供问题与解题前仓库，评分测试不展示给 agent；同时要求 F2P 与 P2P 通过；有按人工估计修复时长划分的难度注释。 | 借测试结构与难度分层。该集合来自 Python 仓库，不能替代 Java。人工任务时长不能直接当成本地模型 wall time。 |
| [SWE-bench Multilingual 官方页](https://swe-agent-bench.github.io/multilingual.html) | 300 个任务、42 个仓库、9 种语言；沿用 SWE-bench 数据格式/协议。Java 有 43 题，来自 Gson 9、Druid 5、Lombok 17、Lucene 9、RxJava 1、JavaParser 2。 | Java 首选池；按仓库与任务机制分层，避免抽 4 个 Gson 简单题就称为 Java repo 评测。 |
| [SWE-bench Pro 官方仓库](https://github.com/scaleapi/SWE-bench_Pro-os)与 [V2 协议](https://github.com/scaleapi/SWE-bench_Pro-os/blob/main/v2/README.md) | 当前 V2 是 642 个任务/11 个仓库，附 HARD-51；HF `default` 已改为 V2，731 是 `v1`。V2 提供公共镜像与 Harbor 任务。locked 协议规定 agent 离线、只放行模型端点、50 分钟/题，并将 `git diff` 在干净镜像重新评分。 | 最值得借的是补丁重放隔离；本地 endpoint 可接入。暂不直接选 HARD-51：它按较强模型失败筛选，小模型容易全失败，分辨不了小幅退化。本次未核实 V2 Java 题量，不声称其 Java 适用性。 |
| [Terminal-Bench 2.0 官方仓库](https://github.com/harbor-framework/terminal-bench-2) | 任务在容器中完成真实终端工作；官方给出本地 Docker oracle 执行方式，支持接入其他 agent。任务做过人工及模型辅助验证。 | 只选与目标相符的 0–2 题，补终端多步工具能力；不引入完整套件。TB2 任务不天然都是长 repo 编程题。 |
| [Harbor 任务格式](https://docs.harborframework.com/tasks/overview)、[Verifier](https://docs.harborframework.com/tasks/verifier)、[配置](https://docs.harborframework.com/tasks/configuration) | 任务由 instruction、环境、solution、tests 构成；tests 默认在 agent 执行结束后上传；可分别设置 agent 与 verifier timeout、CPU/内存及网络规则。 | 固定版本任务可复用现有 Pi agent，不必为了 benchmark 换 agent。只延迟上传 tests 仍弱于独立干净环境重放。 |
| [SWE-Lancer 官方发布](https://openai.com/index/swe-lancer/) | 超过 1,400 个真实自由职业工程/管理任务；工程题用经过三次核验的端到端测试评分；公开 Diamond split 与 Docker 镜像。2025-07 更新移除了执行时的联网要求。 | 借 E2E 验收与去联网波动。管理选方案不是本次代码修改目标；整套浏览器/全栈环境没有必要引入。任务的历史报酬不是本地推理成本。 |
| [SWE-rebench V2 作者数据卡](https://huggingface.co/datasets/nebius/SWE-rebench-V2/blob/main/README.md)、[作者代码](https://github.com/SWE-rebench/SWE-rebench-V2)、[作者发布](https://nebius.com/blog/posts/meet-swe-rebench-v2) | 32,079 个 GitHub issue/PR 任务，覆盖包括 Java 在内的 20 种语言；提供预构建 Docker 环境。代码提供现有镜像的 golden eval、补丁评分、日志解析器。 | Java 补题备选池；自动采集规模大，不等于每题适合长任务。先验证空补丁失败、gold 成功、描述足够、没有外部依赖；不整套运行。公开训练任务也不等于对当前模型无污染。 |
| [SWE-fficiency 官方代码](https://github.com/swefficiency/swefficiency) | 498 个性能优化任务，来自 9 个 Python 库；要求修改后仍通过相关正确性测试；提供专家补丁/workload/容器，建议固定 worker CPU/内存。 | 借“正确性先过关才报告加速”及固定资源。它测试 agent 优化代码，不是直接测试推理后端速度，也不是 Java 集合。 |
| [METR time horizon 定义](https://metr.org/time-horizons/)与 [TH1.1 方法更新](https://metr.org/blog/2026-01-29-time-horizon-1-1/) | horizon 按人类专家完成任务的时长定义，不是模型运行时长。TH1.1 强调任务分布、任务版本和 scaffold 影响；置信区间仍宽，31 个 8h+ 长题仅 5 个有实测人工 baseline，其余为估计。 | 借固定任务分布/配对比较与诚实标注时间。不要给本地 6–8 题拟合“能连续工作 N 小时”。 |

## 怎么选最少的题

以下是选集方案，尚未指定最终 instance_id，也未在 4090 上试跑。公开任务先做无需调用模型的环境/评分验收，再锁定 manifest；不要根据候选后端成绩选题。

最小版本：旧 3 题维持真实 Pi 闭环；从已有 QCB 的 Java/Python、RE/AT/LC 中按受影响行为挑少量题，不再叠加一整套 fixture；新增外部来源最多 2 个 Java repo holdout。以下 4+2+2 是有覆盖缺口时的备选上限，不能直接累加到当前题库。

1. Java 最小 2 题，扩展至 4 题仅在确有覆盖缺口时：优先覆盖 Gson/JavaParser 中的定位修复，以及 Lombok 的编译/生成行为或 Lucene/Druid 的跨模块语义。实际构建成本过大时换题；不要为覆盖大仓库让一次 Maven 构建占主要评测时间。
2. 长 repo 2 题：从 Pro V2 或现有真实 Pi44 选，要求必须读多个文件、修改后运行测试、有明确可观察验收，覆盖至少一次多轮工具恢复和长上下文增长。若现有 Pi44 已覆盖，就不用再加 Pro。
3. 可选终端 2 题：TB2 中筛与工具循环/构建/文件操作相关的题。比如 [fix-code-vulnerability](https://github.com/harbor-framework/terminal-bench-2/blob/main/fix-code-vulnerability/instruction.md) 要读 Bottle 仓库、修代码并生成结构化报告，可作为候选；[cancel-async-tasks](https://github.com/harbor-framework/terminal-bench-2/blob/main/cancel-async-tasks/instruction.md) 是单函数 Python 并发任务，更适合短回归，不能冒称长 repo 任务。具体题仍需检查 verifier、镜像资源和数据联网需求。

单 4090 是模型资源限制，不意味着任务镜像一定能运行：还要核实主机内存、CPU、磁盘、Linux/amd64 与 Docker。推断：只跑一个本地模型 endpoint、agent 串行、任务构建/测试用 CPU，可以避免 benchmark 任务与推理抢 GPU；本次未验证这一环境，也未证明 27B 的特定量化/上下文在显存中适配。所有题都避免额外模型 judge 与外部付费 provider，评分用固定测试。

## 隐藏测试与防改测试

建议采用 Pro V2 的结构：agent 只拿到问题和初始仓库，结束或超时时保存 patch；将允许范围内补丁应用到全新同版本环境，再注入未修改的评分 tests 执行。评分日志与最终代码保留。agent 自己在工作目录跑出的“全绿”只是调试信息。

评分器要验证 F2P/P2P，并固定测试、依赖和入口脚本；把对评分测试/脚本/已安装依赖的修改排除在最终评分环境之外。隐藏不是绝对防作弊保证；这是对本次后端回归足够实用的隔离。空补丁和 gold patch 必须分别证明题目确实失败/可解；环境失败要与模型失败分列，超时则按事先规则计失败并保留部分补丁。

## 分层回归而非每阶段全量重跑

以下数量是建议配额，不修改已有执行计划：

| 层级 | 内容 | 何时运行 |
|---|---|---|
| 合同/数值短回归 | 必要的 tokenizer/template、stream/tool JSON、长上下文/cache、错误路径与数值校验，复用已有 fixture | 每项触及相应路径的变更；无需全矩阵 |
| 代表性性能点 | 初始覆盖全部 14 个 P 的薄层，后续按变更筛选固定 cell，保留短/中/长 prefill、decode 与真实 cache 场景 | 每阶段只跑受影响点；发现异常才展开相邻参数；尾延迟资格仅在指定最终 gate 做 |
| agent 哨兵 | 固定 2 题，Java 与多步 repo 各一 | 会改变输出/采样/cache/工具行为的阶段 |
| 完整质量门 | 旧 3 题、少量既有 QCB、2 题 Java repo holdout，原 baseline 与最终候选逐题配对 | 初始参考和最终验收；中间阶段不全跑 |

现有 672 cells / 14,420 requests 来自多维交叉和重复，本身不能回答“真实编程是否变差”。主代理本地盘点还发现 O128 已运行项 146/146 均为 `finish=length`、4 个 workload 使用重复 record 填料、`quality_status` 始终 `NOT_JUDGED`；这些是主代理提供的本地观察，本文未独立复核。由此应把该层定位为性能/截断压力，质量结论交给已有 QCB 与真实闭环。全参数扫描保留为遇到性能断点的定位工具。本文不修改 Pi44×5、fixture20×3 等现行配置。

## 配对、重复与报告

同一任务固定 initial commit、镜像 digest、agent 版本、system prompt、工具权限、sampling、上下文上限、cache 策略、stop/turn/token/wall-time 预算。原 baseline 和候选使用同一 seed/任务配对；GPU 上 AB/BA 或分块交替，避免把温度、功耗、后台负载漂移误认为收益。同 seed 不保证不同后端数值路径产生相同轨迹。

先每题一对，保留逐题成功/失败/超时、工具错误、token、模型等待时间、构建测试时间和总 wall time。只对预先规定的分歧/临界题追加成对重复，或者最终整集做统一重复。若采用自适应追加，要同时报告首轮与追加结果，避免挑有利重试。不要把 pass@3“至少一次成功”与原 baseline 的单次成功率比较。

8 题中一题就是 12.5 个百分点；小样本全成功也不能证明总体零退化。报告每题的 paired delta、原/候选分歧数量和原始轨迹，不用小样本给出夸大精度的总体百分比。总 wall time/成功数可作为完成成本，但要同时保留失败和超时成本，不能只比较成功题的平均耗时。

## 推理性能测量应借用什么

- [llama.cpp llama-bench](https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md) 区分 pp、tg、pg，输出重复测量均值/标准差；明确不包括 tokenization 和 sampling。建议保留窄层基准，用于定位 prefill/decode 改进，不能替代端到端 agent 验收。官方默认 5 次重复不是每个参数都必须重复 20 次的依据。
- [vLLM serving benchmark 实现](https://docs.vllm.ai/en/latest/api/vllm/benchmarks/serve/) 区分 TTFT、TPOT、ITL、E2EL、请求/输出吞吐与达到延迟目标的 goodput。建议固定 prompt/output/request-rate/并发；cache 开/关以明确业务场景测量，不必和所有长任务交叉。
- [MLCommons LLM Inference v5 说明](https://mlcommons.org/2025/04/llm-inference-v5/) 区分 offline token throughput 与 server TTFT/TPOT。建议借指标边界，不复刻面向标准提交的完整 MLPerf 流程，也不声称结果符合 MLPerf。

## 时间预算：只给上限，不伪称实测

新增 2 个 Java holdout 若各给 50 分钟，单 GPU 串行对比两个后端的 agent 时间上限是 3 小时 20 分钟，已有闭环与 QCB 另计。若未来扩大到 8 题，一个后端上限 6 小时 40 分钟，原/候选一对上限 13 小时 20 分钟；6 题则一对上限 10 小时。以上仅算配置上限，不包括镜像准备、评分、失败环境修复与微基准，也不是预测实际完成时间。模型提前完成时不必硬耗到 timeout；50 分钟来自 Pro V2 协议，仅作可比参照，不要求 Java 子集照搬。

合理的下一步是先用 2 个固定试点任务测出 token/工具/构建的实际时间分解，再估完整集合；不能从远程付费模型 leaderboard、人工小时数或 task 数直接推算单 4090 天数。在缺少这些本地实测前，既不能承诺压到几小时，也没有证据坚持 baseline 必须 6–8 天。

## 本次验证状态

已阅读以上一手页面、README 与协议；GitHub API tree 查询遇到匿名 rate limit，改用官方网页与 raw 源文件核实。仅新增本文；未启动模型、运行 benchmark、下载 Docker 镜像或改动现有计划。最终任务 ID、镜像可用性、实际 CPU/RAM 占用、本地 endpoint 可达性与完成时长均未验证。

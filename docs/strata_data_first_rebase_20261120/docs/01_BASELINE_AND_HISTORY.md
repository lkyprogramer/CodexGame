# 01 · 新研究基线与历史证据

返回[总入口](../README.md) · [数据模型与测量](05_DATA_MODEL_AND_MEASUREMENT.md) · [阶段任务计划](19_PHASE_TASK_PLAN.md)。

**本轮用 Strata v0.2.16 作为独立研究基线。** 仓库记录只说明旧实验和某一时刻的状态；先在授权范围内重新绑定候选制品、服务身份和实际工作负载。不要把研究新基线解释为生产升级，不从任何一组 27B Dense 结果搬性能或参数。

## 1. 权威档案与最新现场结论

`lkyprogramer/CodexGame:4090-report` 的 GitHub [分支元数据][branch]、[固定 HEAD][head] 和[根 tree][tree]相互对应。HEAD 为 `c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b`（2026-11-19 16:51:06，北京时间），tree 为 `519ffa7b417049e9c4fadf670caad147d59b94fb`。递归全仓大请求失败后改读根树、`docs`/`scripts` 子树和指定实验目录的非截断递归树；结论不外推到未枚举范围。读过[根 AGENTS][agents]、[实验 AGENTS][labagents]、[frontier AGENTS][frontieragents]及两份后续包自己的约束；当前 Lab 为唯一实验根，生产/回滚树和既有配置只读，既往授权不续用。

| 固定变更 | 已核档案与意义 |
|---|---|
| [c5f05b46][head]，11-19 16:51:06 | [11-18 多会话报告][multi]和四份机器可读摘要入库：同机 Dense 27B 的 NInfer/HyperQwen 实验，**不是 Strata/Flash-Next 的新 baseline**。 |
| [fae59269][deltacommit]，11-19 16:50:58 | 归档 [11-15 source-delta 方案][deltareadme]；只做了来源、静态审阅、封包检查，R0–R4 和引擎/生成/GPU 均未执行。[验证][deltaval] |
| [d7fd182f][historycommit]，11-15 10:23:57 | 归档 [11-10 kernel evidence addendum][addreadme]、旧质量合成夹具、v2 包检查和 11-02 后续研究；不是完成 O0–O6/E0–E4。 |
| [fbc24c26][ptcommit]，11-04 | [Strata v0.2.10 PT0 vs A0/v0.2.3][pt]：三对、6 启动、12 请求。冷读首个非空输出中位改善 2.7%；同输入 Java LSP warm decode 137.7→117.7 tok/s（−14.5%），完整 warm 7.824→9.026 s（+15.4%）；两边任务 0/3。保留 v0.2.3，未移植 #1536；该次恢复旧服务。**两臂都是 MTP4**，不是 DFlash2 证据。 |

**最新有明确机器状态的版本化记录：** 11-18 10:47:48 验证旧 Strata 恢复，后续 12:48:48、14:34:44、16:53:49 时原单元 `openclaw-qwen38-next.service` 为 **inactive / disabled**；最后一轮试验容器移除、GPU 1 MiB / 无计算进程、实验和 Strata 端口不监听。该时间点覆盖 11-04/11-18 更早的 active 回执，但绝不是 11-20 的现场读回。旧树有历史部署，不等于当前加载、新版被部署、可直接复用端口或已有服务恢复授权。[报告][multi] · [最后复核 JSON][thinking]

**确证的历史配置（不写入当前默认）：** 29 为原生 Debian 12、RTX 4090 SM89 24,564 MiB / 450 W、62 GiB RAM、Xeon Silver 4216、PCIe Gen3×16。旧 Strata 是 A0/v0.2.3（HEAD 前缀 `5c8dd322`）+ EXACT6、别名 `openclaw/Qwen3.8-next`、Flash-Next **GSQ-RCO IQ3_XXS 两分片**（不是 IQ3_S，也不是 Dense 27B）、131,072 总窗、单流水 MTP spec4/min-p 0.5、INT8 KV/resident 20,480、6144 MiB/4 槽会话 cache、PT0/reply reuse、CPUSHARE_MAX4096/AUTO_MAX16384、974 MiB 预留；实际专家槽依版本/工作区变化，不能填默认值。旧 P6 observability 是另一个历史实验身份：v0.2.7 Strata `5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d` + 六文件 Python port，基线 binary SHA256 `58ffaf7f67535049baf996dd8793202b2ba4d2d7090569cfcc13019a28269f22`；P01B 重新构建的观察版 binary `cdfb67469b4cd22c1f1ee8ec28768e810433b91ea85cfdf43a8e8cef382e3341`。均不等于最新 Strata 研究基线。绝不把 `6144 MiB / 4 cache slots` 解释为四条并发 GPU 会话。[旧环境][environment] · [历史 P00][p00] · [P01B][p01b]

**新基线的判断口径：** 新版 Strata 是本次独立研究对象；重新绑定 tag 解引用、真正 engine source/build/SHA256、Control/service schema、可执行文件、有效 argv/env/dispatch、模型两分片或实际新制品、tokenizer/模板、MTP/draft、KV、cache、硬件和工作负载。历史上“在 v0.2.3/v0.2.7 按键存在/命中”的结论不能继承给新版；先验证观测路径是否有效再预算候选。历史 11-15 [来源锁][deltalock]中的 Strata 源 SHA `13eedf552417a6a791a7d13c6597e24300ee3a09`、release engine 源 `712fec6b4297c9cfd32ab43daaa2979a9aa01edf` 也只是当时参考，不充当 11-20 最新或已运行身份。

## 2. 最新同机数据：哪些可以用于设计观测

| 11-18 实测 | 可以继承的证据要求；不继承具体性能 |
|---|---|
| HyperQwen Dense DFlash2-7 的 2×2：共享 KV 5.2／6 GiB，子模型请求并发／短子单信号量。只有 **6 GiB 加短子推理错峰**在两条深轨迹均保住 120,960 token；两次主汇总 1.93/2.58 s，其他组合约 66 s。扩大池单独无效，错峰单独无效；并发情况下 vLLM 抢占增量为 0，仍丢空闲前缀。6 GiB 的最小可用显存 415 MiB（并发），475 MiB（错峰）。 | 空闲前缀/状态保留、活跃抢占、共享池压力和最低显存分开度量。真实子代理工具 I/O 可并行，模型资源冲突另量。不要把 6 GiB、tok/s 或得出的 DFlash2 应用策略搬到 Strata。 |
| B0+B1 NInfer `e753e228`／E8／MTP3：deep 双子四份报告中服务端排队 13.69–16.10 s、prefill 约 1.21–1.27 s；主汇总仍复用 ~120.6K。medium 纯主工具开启仅结构正确 5/16，固定关闭正确 16/16、完整答案 14/16；工具开启的 3.73 s 热轮中位含短失败，仅正确 5 个热轮为 8.88 s。 | 总耗时、包含失败的耗时、正确任务耗时、首思考、首可见正文与首工具事件分开。每次答复不能只判 SSE 正常。 |
| 关闭 thinking 时，NInfer 同会话键中途 `tool_choice=none→auto→none` 令派发 ~123.7K 重算，汇总可从 L2 找回 ~123.3K；工具语义改变渲染前缀。固定工具三槽另见 124,058 reuse / 304 read vs 双槽该轮全量 124,362 重读；槽数与总池同时变。 | “同一会话键”不是相同渲染序列。保存模板/tokenizer、工具有序列表、有效 tool_choice、历史 thinking 策略、LCP、实际 read/reuse/restore 和状态来源。不得因两件配置同时变化就单独归因槽位。 |
| 近 130K 双深是 Dense 测试：NInfer 两次真实 append 合计 8.26 s，KVarN 2 槽 25.32 s；冷预填充和精确重复有不同排名，短 C3/C4 的反转是 75 入/256 出专门形状。 | 新 Strata 的 A/A/诊断要区分 cold、exact repeat、真实 append、A→B→A、compaction 后首轮；是否测多请求由实际独立研究预算及 Strata 语义决定。不能把 Dense 双深或短并发成绩写成 Strata 承诺。 |

数据强度：以上为仓库版本报告和摘要，不是本轮重测。medium 记录 412 次正式流式模型请求、54 次真实本地源码搜索、独立代码回执 52/52；配置级指标有的仅两条轨迹，不能报泛化 p95 出现频率。NInfer 本地 `f4089901` **未参加**这组同机比较，“异步导出+有界交接+FIFO publish”的隔离 CPU/build 版本仍没有同合同硬件的正式收益回执。摘要：[ab][ab]、[fanout][fanout]、[thinking][thinking]、[observations][obs]。原件 `*-raw.tar.gz` 由[根忽略规则][ignore]明确留在测试工作区，不当作已获取；相同目录的复跑脚本未随本 commit 入库。

## 3. 三条实验轴分别编号

| 轴 | 基线 | 给它的问题 |
|---|---|---|
| R：新版研究基线 | 固定 v0.2.16 构建、实际同一模型/模板/有效配置；先做最少量只读盘点与资格后采集 | 时间靠哪一段？旧瓶颈是否仍存在？数据能否解释行为？ |
| V：版本迁移 | 如要比较，固定旧 A0 与新 R 的共同资产/工作量/工具契约，列出不可对齐差异 | 整套版本变更的任务质量、尾延迟、稳定性如何？不归功给单一 kernel。 |
| C：单机制候选 | 同一 R、相同资源与 workload，用候选关闭/开启；先证明关闭干净 | 已经测到的当前暴露成本是否有可复现净收益？ |

R 不依赖 V 才能成立；C 必须依赖 R 的新证据。三个命名空间分别落证，跨模型或量化比较另立轴。以 131,072 **总 token** 为窗口口径，模板、工具、历史、推理和输出都计入；保留实验安全余量，不把 128K 输入与还有可用输出混为一谈。

## 4. 新版启动前的证据缺口与判定

1. **现场身份仍 UNKNOWN。** 需要有授权的只读盘点：29 当前是否闲置、主机与 GPU/驱动/工具链/端口现状、最新拟测 engine 二进制 SHA、app/control/package/build/source 对应、实际模型与 tokenizer/template/draft/codec 的已有文件和校验。无现场，不推断热专家槽、MTP spec、cache budget、Engram tier 或新参数是否生效。最新上游可研究，但不得未经授权部署、停启或下载资产。
2. **现有指标先覆盖后扩。** 新版验证 SSE raw + timing 投影、服务端队列/prepare/实际 prefix 状态、cache restore/publish/evict、prefill/verify/commit/draft、正式提交率、首思考/首可见/首工具、真实任务和健康。每条缺字段填 unknown/原因而非零；实际执行的 dispatch/Graph 与 GPU timeline 分层，先诊断、后 observer-off；不增加同步/热路径 I/O。`warm-fixed2048` 与真实自然 EOS 继续分开。
3. **原件可得性。** [Lab 的 `.gitignore`][labignore] 排除 `workspace/`，[根规则][ignore] 排除 Dense `*-raw.tar.gz`。P01B、F03、P24、D1U、v0.2.10 PT0 的 report 内 raw 位置/hash 可作为索取清单，不等同已读或复算；发布版 Strata DF2 还缺用户侧完整结果/二进制/草稿/运行日志。无须为重建旧档单独重新跑 GPU。
4. **三条不可混用的轴。** 新版同权重/同模板的诊断基线；若资源允许才做独立的新版对旧版迁移比较；另有同 engine 且启用/关闭机制等效的候选对照。模型权重/量化/缓存语义改动是单独实验；即使标作同一个 Flash-Next 模型名，也不能证明同一制品。旧规范中的 18089 是实验端口，不代表当前空闲；不启动生产，不写 systemd、NGINX 或旧树，不擅改 128K 窗口或质量门，不启用 `STRATA_STAGE_PIN` 或 `STRATA_ROUTE_RESIDENT`。

## 5. 原始档案索取清单（若本机仍在，只读）

| 目的 | 原件及状态 |
|---|---|
| 旧 P6 可复刻标识 | `workspace/frontier/p00-20261030/{IDENTITY,IDENTITY_VALIDATION,SOURCE_ENV_SUPPLEMENT,PROTECTION_BEFORE,PHASE_GATE}.json`。旧路径/receipt 不是新版默认。 |
| 暖态事实与失败 | `workspace/frontier/p01b-20261031/` 的 raw manifest、请求、native trace、依赖、build 树；历史报告给导出 92 文件、SHA256 `e75a3fc776360829a35aa20cf046252c5392f75064811886780903a234bc738c`。 |
| HC 正式账本 | `workspace/combination/hc-perf-20261029/{ANALYSIS,PREREGISTRATION,COMPLETION,RESOURCES,RAW_MANIFEST,ARCHIVE_RECEIPT}.json`，429 项原件已由当时的 reviewer 复核；本轮只核 GitHub 报告。 |
| 旧 DF01 失败及发布版路径 | D1U 有独立 n2300 归档；发布版 Q4_0 路径功能摘要 **不**是同一组原件，需另取冻结配置、raw SSE/usage/log、draft/target hash。拿不到就保持 pending。 |
| 11-18 Dense | 四个 Git JSON 是摘要；三份本地 raw tar 的 SHA 位于报告。不为原件补跑，不以 Dense 容量给 Strata 共用池承诺。 |

接下来先读[防重复台账](02_NO_REPEAT_LEDGER.md)和[复用/迁移清单](03_EXISTING_ASSETS_AND_REBASE.md)。

[branch]: https://api.github.com/repos/lkyprogramer/CodexGame/branches/4090-report
[head]: https://github.com/lkyprogramer/CodexGame/commit/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b
[tree]: https://api.github.com/repos/lkyprogramer/CodexGame/git/trees/519ffa7b417049e9c4fadf670caad147d59b94fb
[deltacommit]: https://github.com/lkyprogramer/CodexGame/commit/fae592692f657700da088026d109db272152baf0
[historycommit]: https://github.com/lkyprogramer/CodexGame/commit/d7fd182ff8104176967ce5a694a967f81b0c10e8
[ptcommit]: https://github.com/lkyprogramer/CodexGame/commit/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc
[multi]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/qwen38-27b-4090-130k-multisession-20261118.md
[obs]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/output/qwen38-130k-multisession-20261118/observations.json
[ab]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/output/qwen38-130k-multisession-20261118/ab-summary.json
[fanout]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/output/qwen38-130k-multisession-20261118/fanout-summary.json
[thinking]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/output/qwen38-130k-multisession-20261118/thinking-summary.json
[ignore]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/.gitignore
[labignore]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/.gitignore
[agents]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/AGENTS.md
[labagents]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/AGENTS.md
[frontieragents]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/frontier/AGENTS.md
[pt]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/reports/V0210-PT0-VERSION-COMPARISON-20261104.md
[environment]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/docs/02_ENVIRONMENT.md
[deltareadme]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/ninfer_strata_source_delta_exploration_20261115/README.md
[deltaval]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/ninfer_strata_source_delta_exploration_20261115/evidence/VERIFICATION.md
[deltalock]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/ninfer_strata_source_delta_exploration_20261115/evidence/source_lock.json
[addreadme]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_foundation_kernel_evidence_addendum_20261110/README.md
[p00]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/reports/P00-EVIDENCE-20261030.md
[p01b]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/reports/P01B-PI-WARM-DIAGNOSTIC-20261031.md

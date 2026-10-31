> 历史入口，归档于 2026-10-30。原阶段状态和失败保留；后续执行以 [当前入口](../START_HERE_AI.md) 为准。

# Strata · RTX 4090 / 128K PR 实验包

**对象：已经部署的 Strata，不是 NInfer。** 单张桌面 RTX 4090 24GB、约 62GiB RAM（29 号机，Xeon Silver 4216）；总上下文硬上限 **131072 token**。本包提供 AI 开发执行计划、14 个 PR 的独立移植任务（初稿 10 项 + #2253 + 2026-10-26 从 v2 包收编的 #3871 / #4040 / #4039）、非 PR 方向与执行计划、冻结题集生成器、受控 Java 工具循环、单会话测试工具、隔离测试编排、配对统计与质量非劣门。**不包含模型或编译好的引擎。**

## 当前状态（2026-10-29）

**2026-10-29 最新：HC阶段测试完成，性能门未通过，当前候选收口。** P22完整默认memcheck、P23真实保留专家成本门PASS；P24完成20个fresh engine/24请求，全部请求验收通过。100K六对TTFT改善0.824%，95% CI[-0.035%,1.804%]，未达4%门；wall非劣通过、完整decode非劣失败。复用数值/生命周期证据，原10272槽/驻留/分派和原六FAIL保持；生产未改且停机、GPU1MiB、18089释放，自动续测仍PAUSED。不自动扩大其他候选。见 [P22](../reports/P22-HC-MEMCHECK-20261029.md)、[P23](../reports/P23-HC-RETAINED-EXPERT-COST-20261029.md)、[P24](../reports/P24-HC-PAIRED-PERFORMANCE-20261029.md)。

以下为各历史阶段当时的结论，保留原失败与未运行状态。

**2026-10-29 HC16K数值与生命周期PASS，memcheck加载OOM后停止。** 四份独立managed HC保持原Device缓存/10272槽和实际分派，4019条raw、完整logits与486,388,612bytes有效状态全部逐字节一致。8请求生命周期通过（4096→16384→4096、保存恢复、两类取消续接）；随后memcheck在cuLibraryLoadData/cuBLAS初始化OOM，auto-cache已从10272降至9984，未READY、GEN0。未改参数凑通过，成本/正式性能NOT_RUN，原六FAIL保留；生产未改且停机、GPU1MiB、18089释放、自动续测PAUSED。见 [P20/P21报告](../reports/P20-P21-HC-16K-LIFECYCLE-20261029.md)。

**2026-10-29 HC真实边界：4096数值门PASS，16K独立对照BLOCKED_VRAM，已停止。** 4096的3887条raw、全部logits与有效状态逐字节一致；自然C完成真实16384块、48层FFN，但匹配对照需990.001MiB、实余514.5MiB，主计算前拒绝。4次GEN1尝试、3次完成、零重试；生命周期/sanitizer/成本/正式性能未运行，原六FAIL保留。生产13保护hash不变、服务仍inactive/dead，GPU1MiB、18089释放，自动续测PAUSED。见 [P19报告](../reports/P19-HC-REAL-BOUNDARIES-20261029.md)。

**2026-10-29 C运行及同路径HC数值验证完成：PASS。** 计算/SAVE后先停止并join监控，再QUIT，两个新GEN1均正常完成。自然C与同驻留/实际分派的独立HC缓冲区对照，3325条raw、248320个logits和有效状态全部逐字节相同，容差0；自然A/C仍为NUMERICAL_DIFFERENCE，旧失败与原六FAIL保留。10项护栏＋6项对照验收回归在本地和29通过。边界/生命周期/性能未运行；生产未改且inactive/dead，GPU1MiB、18089释放，自动续测PAUSED。见 [P18报告](../reports/P18-HC-C-COMPLETION-20261029.md)。

**2026-10-28 HC-only scratch资格验证：BLOCKED_NUMERICAL_ORACLE。** 同chunk16384的启动借槽4388→3787，少601槽、实际借区约省990MiB；原P6同token A/A不逐bit。原布局原始字节定位显示layer3 FFN的HC输入/输出完全相同、主体后R不同，伴随动态CPU/GPU分派变化。B/C仅启动零请求，候选数值/生命周期/正式性能NOT_RUN；不能判无收益或采用。指标已预登记，原六FAIL保留、生产未改。见 [P13报告](../reports/P13-HC-SCRATCH-QUALIFICATION-20261028.md)。

**2026-10-28 IQ3_S nt1 AVX2 gather 探针完成：REGRESSION，扩展门 NOT_MET。** 同P6完整配置确认IQ3_S占nt1 GU worker时间36.246%；只改两处codebook查表，逐bit、实际命中和新增ISA检查通过。完整专家六对耗时增加33.038%，配对95% CI[31.401%,34.607%]；单核热GU增加77.960%。频率未下降、未见进程swap或测量窗major fault。拒绝当前独立AVX2候选，不扩格式、不进整机验证。原六FAIL保留，生产未改、继续停机。见 [P12探针报告](../reports/P12-GU-GATHER-PROBE-20261028.md)。

**2026-10-28 Ada MMVQ差量资格检查完成：NO_BENEFIT_SCREEN。** 同P6完整配置，4K/100K原请求各profile一次及无nsys控制一次，4请求均输出2048token。8个不同于旧IL89的表组合实际命中；新差量加全部quant/interleave超集在本次profiled完整请求的条件空间2.764%/2.003%，首末输出区间3.084%/3.240%。按限定筛查停止，IL89=0、SIDE=0全程保持。profiler扰动明显、控制轨迹不同，不能称严格未插桩上界或全表无收益；原六FAIL保留，生产未改/保持停机。见 [P11差量报告](../reports/P11-ADA-DELTA-QUALIFICATION-20261028.md)。

**2026-10-28 DEQUANT_SIDE关闭状态筛查完成：NO_BENEFIT_SCREEN。** 三种原请求的基线dense反量化确有覆盖，候选类型/grid与静态300矩阵/chunk清单闭合；本次profiled trace在“候选全部删除、其他工作耗时不变”的乐观模型下，TTFT空间仅1.22%/1.73%/1.36%，低于4%请求门参考，停止不开=1。另有同请求无nsys扰动对照，不当off/on收益；真实compaction fixture缺失，32K只作重读形态诊断。原六FAIL、P6正确性门及生产配置保持，未做开启parity/配对/部署。见 [P10筛查报告](../reports/P10-DEQUANT-SIDE-QUALIFICATION-20261028.md)。

**2026-10-28 已有较高精度IQ3_S复测完成，两个prime仍同错。** 找到与IQ3_XXS同一发布revision `ed59f920…` 的本地IQ3_S，4个分片重新全内容hash匹配LFS清单；结构/tokenizer/imatrix元数据一致。保持P8同token/同参考图/NGL18/F16 KV，16/16长输入argmax一致，仍为错位数字＋EOS；概率改变未反转选择。IQ3_S仍共享低比特PLE，且276分配变化含46处缩小，不能当作BF16基模对照。原六FAIL及DEQUANT_SIDE未运行状态保持，生产13hash不变；没有下载/部署。见 [P9较高精度对照](../reports/P9-HIGHER-PRECISION-LOGITS-20261028.md)。

**2026-10-28 同token/同GGUF独立logits对照完成。** llama.cpp独立qwen4exp图在两个完整prime上16/16个argmax与Strata一致，重现`1751936`/`6395887`及数字后EOS；短复制另8/8一致。参考FP16 KV中错误首位高于正确首位1.30/1.97 logit，EOS高于连字符6.15/3.62。更支持当前量化模型与原none长表提示的条件相关失败；仍未拆分基础模型/量化，也不证明全部内核正确。原六FAIL及DEQUANT_SIDE未运行状态不变；生产13hash不变、保持停机。见 [P8独立logits对照](../reports/P8-INDEPENDENT-LOGITS-20261028.md)。

**2026-10-28 六个长检索失败诊断完成，原判定仍FAIL。** gold均是输入中对应行的唯一完整值；两个prime取相邻行，四个追问取对数字前缀后输出EOS。raw证明不是服务截断；无MTP/lookup、实际8053相同槽数的对照仍六项同错。短表、明确完整字符串格式、low thinking控制可通过；明确格式两档冷读通过，原措辞warm仍错。27请求全部留存，未改变评分或原失败，未改引擎/生产，DEQUANT_SIDE仍未运行；权重/量化与共用数值内核尚无独立参考结果。见 [P7根因诊断](../reports/P7-LONG-RETRIEVAL-ROOTCAUSE-20261028.md)。

**2026-10-28 v0.2.7 隔离基线复测完成，正确性门 FAIL。** 保留完整配置及 #1536/PT；新树 Python402项与实际机制验证通过。P3六个68K/100K原长检索请求全部仍失败，两档真实恢复通过；布尔工具参数及seed43原失败末轮本次通过，但不构成间歇问题修复或新八轮任务完成证明。按前置门，`STRATA_DEQUANT_SIDE` 未开启、未测试，新八轮链未运行；无升级采用或性能结论。生产13保护hash不变、保持停机，GPU/18089已释放。见 [P6隔离基线报告](../reports/P6-V027-BASELINE-20261028.md)。

**2026-10-27 GU单格式探针完成：NO_BENEFIT，未过扩展门。** 按完整配置真实CPU miss成本唯一选择IQ3_S nt=1；整数madd+add改用无VBMI的EVEX256 VNNI，逐bit、ISA及实际命中通过。生产线程布局完整GU→SwiGLU→quant→down六对改善−0.152%，配对95% CI为[−0.570%, +0.245%]；热单核约+1.025%不触发扩展。root只读APERF/MPERF已补齐，没有明显频率下降；不扩格式，不进入整机候选或采用验证。生产未改、继续停机。见 [P5探针报告](../reports/P5-GU-VNNI-PROBE-20261027.md)。

**2026-10-27 运行边界补测完成，存在热边界失败。** 完整配置完成915.93秒混合负载及625.45秒连续100K冷读，峰值84°C，热态长恢复及取消续接通过；仅关闭KVRES的基线在682.70秒触发85°C停止线，其热态后续未运行。同阶段内存对照解释了日志1.55GiB之外的MTP分配：实际新增CUDA host allocation为1.675794GiB，13块映射与系统Shmem差额按页取整后完全对应。生产配置未改，服务继续停机。见 [P4运行边界报告](../reports/P4-RUNTIME-BOUNDARIES-20261027.md)；本轮不覆盖P3质量失败，不建立全天热稳态或新的ADOPT结论。

**2026-10-27 补充组合实验完成；正式采用门未通过，质量非劣未建立。** 在 29 实验环境比较完整生产配置与仅关闭 KVRES。性能表征完成 6 对、276 请求，96 个定长输出均达到 2048 token，但 8 个主指标 CI 均未达到预登记 4% 改善门；64K / 100K 样本分别复用 16K / 48K 前缀，不能称为完整冷读。tool 关闭 / 开启为 29/30 对 28/30，protocol 两臂各 30/30。原 31 题正式回放的 `FAILURE` 与独立两对 4/4 同错完整保留。

实际历史恢复两臂均有 69625 / 102385 token 的真实回执，但每臂六个长检索全部失败。Python 编码链两对中，关闭 KVRES 全链成功 2/2，开启为 1/2；seed 43 开启臂最终代码未定义 `dst_balance`，导致旧功能失败。样本小，不能因果归因 KVRES。全部实验进程已退出，GPU 1 MiB、无计算进程，生产 inactive/dead、仍 enabled，13 个保护文件 hash 不变。结果见 [组合验证报告](../reports/P3-COMBINATION-KVRES-20261027.md)。下文“过门 / ADOPT”仅为 10-26 历史筛查与部署决定，不能作为本轮正式通过结论。

**结论：Phase 0 与两个单会话 Phase 已完成。生产是 A0（v0.2.3）+ EXACT6 + host 调优，2026-10-26 09:24 又上线四个开关（[部署报告](../reports/DEPLOY-PROD-20261026.md)），09:44 起按用户同意再次停机测试：服务层 #1536（回复 token 复用）和 CFG-PT=0（不保留历史 thinking），引擎 env `STRATA_PREFILL_CPU_SHARE_MAX=4096`（3.2K 追问读入 −12%）和 `STRATA_PREFILL_AUTO_MAX=16384`（超过 8192 的读入 TTFT −27%）。真实 Pi 长会话的质量与速度在生产上复核。decode 侧的零代码与 pool 方向（spec 宽度、NP-3、NP-RES、#4040）都已测完，没有过门项。2026-10-26 按用户要求复查 v2 包，补出 4 个没测过的零代码 decode 项并停机测完：只有 CFG-KVRES（`--kv-resident 20480`）过门，decode +2.8%～+4.4%，每轮净省约 2～8 s。21:38 按用户要求写入生产配置并冒烟通过，含停放后恢复会话（[部署报告](../reports/DEPLOY-KVRES-20261026.md)），验证后重新停机；CFG-ADAPT、CFG-KVGROW、CFG-SPECCOST 未过门。到目前为止的累计收益和“为什么不多”见 [累计收益汇总](../reports/SUMMARY-GAINS-20261026.md)。**

- **用法决定优先级**：用户是一个会话长期追问、无切换、无并发。实测一轮追问的墙钟约 96～98% 是 decode，所以多会话 / park / 并发类优化降级。见 [单会话](../docs/11_SINGLE_SESSION.md)。
- **已定结论**：
  - MIG-PASS；EXACT6 进公共基线（窗口 −5.3%）；CFG-CSTATE 已上线（+2.2%）。
  - #2253：机制成立，本用法 0 次触发，不推荐；CFG-MMAP 不推荐。
  - #3453：Ada 表本身 0 收益。
  - #1536：追问重读 4/14 → 0/16，TTFT 4.87 → 2.52 s。
  - CFG-PT=0：同一会话能问的轮数约 2 倍（12 vs 5～7），质量链未测出差异。
- **v2 包（GPT Pro，2026-10-25）已并入的部分**：验证工具修复（严格 JSON 类型、流式首事件分类、绝对超时、计划驱动统计与缺项门、请求预算 / usage 审计、GPU 归属持续监控、收尾回执）、独立质量非劣门 `tools/quality_gate.py`、park/restore 离线计划校验、CPU pool 与 spec 两份执行计划、3 个新 PR、方向图谱对照。未并入的部分及理由见 [非 PR 方向](../docs/10_NON_PR_DIRECTIONS.md) 第 10 节。

| 对象 | 冻结值 |
|---|---|
| 开发基线 | A0 = v0.2.3 `5c8dd322528cc84f68f461ad54a506b9da8fa8d4` + 公共 env EXACT6（`sources/LOCK.json`）；v0.2.7仅建隔离候选，P3正确性门未过，未替换A0或生产，见P6报告 |
| 生产 | A0 + EXACT6，`/home/hhtele/strata-0.2.3`，18343 / NGINX 28343，模型名不变，另有 10-26 上线的五个开关（四个见 [DEPLOY-PROD](../reports/DEPLOY-PROD-20261026.md)，加 `--kv-resident 20480` 见 [DEPLOY-KVRES](../reports/DEPLOY-KVRES-20261026.md)）；**停机测试中**：09:44 起停机，21:38～21:41 启动做 KVRES 冒烟后又停；恢复需用户发话，服务仍 enabled，重启机器会自动拉起；回滚树 `/home/hhtele/strata-0.1.43.1` |
| 目标 GPU | NVIDIA `sm_89`，单卡 |
| 上下文 | 模板 + system + tools + 历史 + 输入 + 输出 ≤ 131072，预留 4096 |
| 噪声 | 引擎 ms/窗口 A/A 约 ±0.75%；decode 组级配对约 ±2%；采样单题 CI 常见 ±10%；greedy 跨进程不逐字节一致 |

## 执行次序（2026-10-26 重排）

| 次序 | 项 | 类型 | 状态 / 门槛 | 依据 |
|---:|---|---|---|---|
| 1 | 真实 Pi 复核：PT=0 + #1536 | 服务层 | **已上线（2026-10-26）**，与 CPUSHARE 4096、AUTOMAX 16384 一起；冒烟与回执见 [部署报告](../reports/DEPLOY-PROD-20261026.md)；真实 Pi 长会话质量在生产使用中复核 | 两项都已过实验室 A/B；质量只做过天花板题 |
| 2 | CFG-SPEC-S：`--spec 3/4/5`（Pi 采样 + thinking） | 零代码，decode | **已完成：保持 4**。spec3 慢 1～9%（拒绝），spec5 快 1.0～1.7%（低于 3% 门）；[报告](../reports/P2-CFG-SPEC-S-20261026.md) | 每 token 成本三档持平：窗口越宽，CPU 专家越多 |
| 3 | CFG-CPUSHARE-S：`STRATA_PREFILL_CPU_SHARE_MAX` 3072/8192/16384（补测 4096） | 零代码，追问 TTFT | **已完成：4096 为采用候选**。3.2K 读入快 12.2%，7～13K 持平，decode 不变；8192 / 16384 拒绝（7.3～7.9K 单 chunk 慢 15～20%）；[报告](../reports/P2-CFG-CPUSHARE-S-20261026.md) | 门槛以下的 chunk 走“只搬路由到的专家 + CPU 分担”，以上的流式搬全部专家；两者约在 4.4K 相交 |
| 4 | #3871 CPU 微基准修正 | 测量前置 | **已完成：ADOPT（仅实验工具）**。A0 上 3 次段错误，移植后出成本表；本机 10 种格式组合全部测完，IQ2_XXS + Q2_0 实际 31 GB/s（NP-0 误测为 13）；NP-3 上限约为窗口时间的 6～11%，NP-1 维持暂缓；[报告](../reports/P2-PR3871-20261026.md) | NP-1a 曾测错分支 |
| 5 | NP-3 CPU pool（[计划](../plans/NP3_CPU_POOL.md)） | 代码，decode | **已完成：pool 代码方向 NO_BENEFIT**（[perf](../reports/P2-NP3-PERF-20261026.md)、[trace](../reports/P2-NP3-TRACE-20261026.md)）。每个 CPU miss 约 76 µs，其中同步约 2.5 µs、尾部约 5 µs，其余在任务内；`--pool-tasks` 16～192 都在 ±1.5% 内。trace 工具保留 | 任务内偏慢来自 gate/up 受计算限制，以及 PCIe 与 CPU 争用 2 通道 DDR |
| 6 | NP-RES：CFG-PCIEFRAC、`STRATA_PCIE_BALANCE`，驻留 / 调度代码方向（v2 O07 / O08 / O09） | 先配置后代码，decode | **已完成：NO_BENEFIT**。固定 0.30 对 PcieAuto +0.3～4.2%（只有贪心 decode 组 CI 不跨 1）；balance 模型把实际 PCIe 份额从 8.2% 提到 22.3%，组总量 0～+2.1%；O07 / O08 分析判断 <1～2%，不立项；[报告](../reports/P2-NPRES-PCIEFRAC-20261026.md) | CPU 少算的时间被 GPU 多等 PCIe 抵掉，分担的最优点很平；每 MB CPU 成本在 10 种组合间只差 ±10% |
| 7 | #3307（或 #3281） | PR，长读 TTFT | **已完成：#3307 NOT_APPLICABLE（Gate A，未移植），派生 CFG-AUTOMAX 为采用候选**。ring 256 / 384 / 512 相差 <1%；chunk 卡在 `--prefill auto` 默认上限 8192 而非显存，`STRATA_PREFILL_AUTO_MAX=16384` 使超过 8192 的追问读入 TTFT 0.732 [0.708, 0.783]（每次省 1.0～2.2 s），≤8192 的读入与 decode 不变；32K～123K 冷读 −30%，检索 10/10；代价是 GPU 功耗约 +20%，连续冷读到 84～85 °C，长上下文 campaign 被 85 °C 保护中止（部分完成）；[报告](../reports/P2-PR3307-20261026.md) | 每个 chunk 要把全部非驻留专家搬一遍（约 2.5 s），chunk 越少越快 |
| 8 | #4040 | PR，decode（改文件类） | **已完成：NO_BENEFIT（Gate A，未移植）**。151 次引擎调用 lookup 份额 4.6%；≥20% 的 14 次都是编码链里思考后的回答段，只占 decode 时间 0.8%；[P2-PR4040](../reports/P2-PR4040-20261026.md) | 端到端上限约 0.4%（编码链 ≤1.8%） |
| 9 | CFG-ADAPT（v2 O09）：overlap 对 lag2nw（LAG=2 + NOWAIT）、对 async（`--adapt-async 1` + LAG=2） | 零代码，decode | **已完成：NO_BENEFIT，保持 overlap**。lag2nw 回答段 0.981 [0.968, 0.997]（略慢，窗口内 CPU 专家条目 +7.5%）；async 各组 1.000～1.015，CI 跨 1；[报告](../reports/P2-CFG-ADAPT-20261026.md) | overlap 下自适应层在关键路径上只剩约 0.24 ms / 窗口（1.4%），这是任何模式的上限 |
| 10 | CFG-KVRES（v2 O44 / O49）：`--kv-resident 20480` | 零代码，decode | **10-26 历史部署决定：ADOPT，已写入生产配置（21:38，冒烟通过，含 30K 停放后恢复；[部署报告](../reports/DEPLOY-KVRES-20261026.md)）**。旧基线筛查中检索 base / cfg 各 25/25、quality 各 40/40、protocol 各 25/25、tool 25/25 对 24/25，未建立正式质量非劣；decode 四组配对 +2.8%～+4.4%，为旧请求级统计（专家槽 9420 → 10290，CPU 专家条目 −17%）；7～12K 追问读入每次 +0.26～0.43 s，3.2K 追问不变；冷读 32K～123K 慢 8～13%；每轮净省约 2～8 s 为推算。完整组合的新验证见 [P3 报告](../reports/P3-COMBINATION-KVRES-20261027.md)；[历史报告](../reports/P2-CFG-KVRES-20261026.md) | K/V 1.55 GiB 移到 pinned RAM，腾出 1.41 GiB 显存给专家缓存 |
| 11 | CFG-KVGROW（v2 O44）：`STRATA_KV_GROW=1` | 零代码，decode | **已完成：未过门**。回答段 +3.2% 过，思考段 +1.3%（CI 跨 1）；32K +8.5%，≥65K 无收益；冷读不变；[报告](../reports/P2-CFG-KVGROW-20261026.md) | KV 按实际用到的 cell 占显存，上下文变长时把槽位还回去，单会话后半段没有收益 |
| 12 | CFG-SPECCOST（v2 O33）：`STRATA_SPEC_COST=1` | 零代码，decode | **已完成：NO_BENEFIT**。窗口变短变便宜，每窗口提交 token 同比下降，四组 0.973～1.003；[报告](../reports/P2-CFG-SPECCOST-20261026.md) | 与 CFG-SPEC-S 相同：T=3～5 每 token 成本持平 |
| 13 | 其余：CFG-PARKGAIN（前提 PT=0 已满足，但单会话用法下价值低）、#3584、#4039、NP-1、NP-4、NP-5、#3322（BLOCKED）、CFG-UNLOCK（需批准）；Q 轨道的 tail skip 加深（`STRATA_ROUTE_TAIL_SKIP=6`）需用户先接受质量换速度 | — | 低优先级、有前提或需批准 | 见 [综合排序](../docs/01_RANKING.md)、[非 PR 方向](../docs/10_NON_PR_DIRECTIONS.md) |

不再执行：#2253、CFG-MMAP、#3453 的表本身、#3517、#3711、#2822、#2964（理由见排序文档）。10-26 的历史实验在 A0 + EXACT6 上做，公共 env 对所有 arm 一致；其 base 的 K/V 全驻显存（9420 槽），与带 `--kv-resident 20480` 的生产不同。10-27 组合验证使用独立冻结的当前完整配置，两臂仅 KVRES 不同；其数字不能与历史 base 的收益直接合并。

## 使用入口

把整个目录交给负责实机开发的 AI，首先读 **[START_HERE_AI.md](../START_HERE_AI.md)**。它可以直接使用 TASK 文档工作；也可配置外部 AI 命令，让 `auto` 编排完整流程。

```bash
# 在实验包目录，用 Strata 所用的 Python 环境执行
export LAB_PYTHON=/home/hhtele/strata-0.1.43.1/.venv/bin/python

# 只需初始化一次。所有路径都来自现网实际部署，不下载或替换模型。
# 29 号机实际路径（2026-10-23 核对；29 上已 init 过，local.json 不要覆盖）。deployed-* 指向 0.1.43.1 的配置，
# 只作归一化运行配置的来源（MIG 的 P 臂）；生产已是 /home/hhtele/strata-0.2.3，两者参数一致
./run.sh init \
  --deployed-repo /home/hhtele/strata-0.1.43.1 \
  --deployed-config /home/hhtele/strata-0.1.43.1/strata-iq3_xxs.json \
  --gguf /data/strata-data/models/IQ3_XXS/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf \
  --template /data/strata-data/packs/iq3_xxs/tokenizer/chat_template.jinja \
  --python "$LAB_PYTHON"

./run.sh selftest
./run.sh doctor
./run.sh bootstrap
./run.sh assets               # 对实际GGUF/pack/profile做一次完整哈希
./run.sh qualify --pr 3871
./run.sh prepare --pr 3871
```

最后一条生成 `workspace/state/pr-3871/TASK.md`、冻结的 PR diff 和隔离 worktree。**不会自动把旧分支合并进最新 main。**

### 已配置 AI 开发器时的一键入口

在 `config/local.json` 中填入 `agent_command` 的 argv 数组，参数可以包含 `{task_file}`、`{worktree}`、`{package}`；该命令必须读取任务文件、完成开发并提交代码、输出 `READY.json`。没有配置时，工具会生成任务并停止，不伪装成已开发完成。

```bash
./run.sh auto --pr 3871 --suite smoke --execute
```

它依次准备源码、调用你选择的开发器、重新执行指定单测、构建 base/candidate、冻结题集、串行运行 base/off/on、生成 JSON/CSV/Markdown 报告。**GPU 阶段还要求 `maintenance_confirmed=true`，且没有其他计算进程。** 生产服务由你在维护窗口自行安排停启，工具不会替你杀进程。

### AI 在现有终端中直接完成开发后

```bash
./run.sh build                 # 冻结 main 基线
./run.sh build --pr 1536       # 当前 PR 单独候选
./run.sh noise --suite smoke --execute
./run.sh run --pr 1536 --suite full --groups quality,tool,protocol,decode,cold-prefill,long-retrieval --execute
./run.sh scenario --pr 1536 --name java-agent --execute
./run.sh cfg --name spec3 --arg=--spec=3 --corpus <frozen.json> --execute   # 配置对照（只接受 STRATA_* env 与 --arg）
./run.sh stats --results <run 目录>   # 缺项 / 重复 / 失败 / 未评分时退出码 2
./run.sh validate-plan --plan plans/park_restore.example.json   # 只做离线结构检查
```

### 单会话测试与质量门（2026-10-26 收编）

```bash
# 一个 Pi 形态的 Java 长会话；--tree 指向候选树，--env 只传 STRATA_*
$LAB_PYTHON tools/session/session_bench.py --name pt0 --budget 0 --stop-tokens 125000 \
    --tree workspace/trees/cfg-pt --env STRATA_PRESERVE_THINKING=0
# 8 轮编码链；模型生成的代码只在本地 Docker 镜像里评分，不给 --image 则 NOT_RUN
$LAB_PYTHON tools/session/chain_bench.py --name pt0-1 --image python:3.12-slim \
    --tree workspace/trees/cfg-pt --env STRATA_PRESERVE_THINKING=0
# 解释重读：需要该会话以 STRATA_DEBUG=1 运行
$LAB_PYTHON tools/session/reread_diag.py workspace/reports/session/<name>
# 配对任务级质量非劣（离线计算，不跑模型）；示例预期退出 1
python3 -B tools/quality_gate.py --input tools/examples/quality-smoke-30.json
```

说明见 [单会话](../docs/11_SINGLE_SESSION.md)、[质量门](../tools/QUALITY_GATE_README.md)。这些脚本直接使用 `OwnedServer`，尚未接入 schema2 计划与收尾回执，结论按配对筛查口径报告。

Java 评分需要预先存在的本地 Docker JDK 镜像（29 目前没有，需用户离线准备，否则 Java 组为 NOT_RUN）：在 `local.json` 设置 `java_enabled=true` 和 `java_image`。脚本解析本地不可变 image ID，不自动拉取镜像。没有隔离环境，Java 项标记未执行，不在宿主机运行模型生成的代码。

## 三态与生产版本的关系

- `P`：实际部署快照（单独迁移对照，不混入 PR 收益）。
- `A0/base`：冻结 main 原版。
- `A1/off`：同一 PR 移植版本，完整功能关闭。
- `B/on`：同一候选编译产物，完整功能开启。

先证明 A1 没引入回归，再看 B 相对 A1。每个 PR 独立从同一 A0 起步。组合只在单项通过后进行。普通请求的顺序和内容固定；缓存场景中的追加与编辑也固定，不被前一次模型回答改变。

## 包含与不包含

已包含：14 个专项任务文档；`plans/` 下 NP-3 与 spec / lookup 两份执行计划；82 个 full-suite 冻结请求的生成规则（其中 8 个 Java 单题）；21 个 smoke 请求；8 个有确定断言的 Java 任务；Java 工具循环与短请求抢占探针；单会话 / 编码链 / 重读诊断 / park 场景工具；MIG / CFG / DIAG 分析脚本；128K 安全门与 usage 审计；本地 HTTP/SSE 测试；计划驱动的配对统计；任务级质量非劣门；文件完整性清单；`reports/` 下的各 Phase 实测报告。

未包含：本机 CUDA 编译结果、RTX4090 实测收益、用户真实 Pi 仓库的任务完成率、主线与所有 PR 的最终冲突解决。它们是下游 AI 在隔离 worktree 中必须完成并记录的验收项。当前包的真实测试记录见 **[VALIDATION.md](../VALIDATION.md)**。

原生 GPU 编排目前只面向 Linux；WSL2 只有当 GPU PID/`/proc` 审计通过时才可运行。Windows PowerShell 入口可运行文档准备／CPU 测试，但没有声称原生 Windows GPU 生命周期编排已经实现。

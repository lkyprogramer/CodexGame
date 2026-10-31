> 历史入口，归档于 2026-10-30。原阶段状态和失败保留；后续执行以 [当前入口](../START_HERE_AI.md) 为准。

# 给实机执行 AI 的总任务

你在用户已部署的 Strata 旁边开发单卡性能实验。目标不是移植到另一推理引擎，也不是为了合并而合并。最终产出是**每项 PR 可追溯的采用／拒绝／不适用结论**、可回退补丁和原始证据。

## 不可越过的边界

1. 生产 repo、配置、模型、Pi 设置只读；不自动改驱动，不重装模型，不调用 `strata connect pi --write`，不自动运行任何更新器。
2. 只用实验包 `workspace/repo` 及其 worktree。禁止在生产目录 `reset/clean/checkout/cherry-pick`。禁止 `pkill strata`、`killall` 和全局 Docker 清理。
3. 单卡 GPU 测试串行；只停止本轮拥有的 process group。CPU 开发可分 worktree，但编译并行度按可用内存控制。
4. 硬上限 131072 token 是**模板+system+tools+历史+输入+输出**总和。最大输入目标120K，不是128K输入。每次先用冻结 Strata tokenizer 计数，计数器未经服务端 usage 校验不得长测。禁止0/-1输出上限。
5. 模型、量化、KV格式、KV resident、MTP参数、Expert Profile、CPU workers、采样和控制向量保持固定。确需改变是另一个配置实验，不得当成 PR 单项增益。
6. 不把“Open／merged=false”当作功能完全缺席。最新 main 已吸收部分 DFlash2 与协议修复，先检查具体代码与行为，再移植剩余差量。
7. 不删除失败记录，不只挑最快运行，不以流式数据包数量冒充 token。不因输出更短而宣称更快。
8. 模型生成的任何代码（Java、Python 评分题等）只在受限、无网络 Docker 容器内执行（本地不可变镜像 ID，`--pull=never`）；没有镜像就记 NOT_RUN，不在宿主机运行。所有工具调用经过本轮 allowlist 与 schema 校验；不得把测试工具映射为真实 shell。
9. **29 号机专属**：生产是 A0 + EXACT6 + 2026-10-26 上线的五个开关（`/home/hhtele/strata-0.2.3`，18343；四个见 [部署报告](../reports/DEPLOY-PROD-20261026.md)，`--kv-resident 20480` 见 [DEPLOY-KVRES](../reports/DEPLOY-KVRES-20261026.md)）；**2026-10-26 09:44 起按用户同意停机测试**（21:38～21:41 只为 KVRES 冒烟启动过一次），恢复需用户发话；以后需要 GPU 独占的实验仍先征得用户同意再停生产。不改 systemd unit（含 `strata-host-tuning.service`）、NGINX、`production-18343.sh`、驱动、CUDA 12.3；不装内核模块、不改 initramfs/GRUB/内核参数（CFG-UNLOCK 经用户批准的维护窗口除外）；不写 `/home/hhtele/strata-0.2.3` 与回滚树 `/home/hhtele/strata-0.1.43.1`（含 `data/` profile）；实验不占 18343；不运行 `./update.sh`；不删旧版本目录；不停用户未授权的共存容器；不碰 `/home/hhtele/strata-cvec-ablation-20261020*`。29 只能经 `jssh 29` 访问。
10. 任何 arm 禁止 `STRATA_STAGE_PIN`（损坏 IQ3 系权重）和 `STRATA_ROUTE_RESIDENT`（改变答案）。不把 NGINX Bearer、SSH 密码、sudo 口令、Pi `apiKey` 写进文件、日志摘要或 git。
11. 噪声与确定性：29 上重启 A/A 约 5%、抽样配对约 7%；greedy 输出跨重启不逐字节一致。收益低于噪声判 NO_BENEFIT；正确性用断言/评分，不用跨进程 bitwise 比较。

## 当前进度与后续次序（2026-10-29）

- **最新：HC阶段测试完成，性能门未通过，当前候选收口。** P22完整默认memcheck、P23真实保留专家成本门PASS；P24完成20个fresh engine/24请求，全部请求验收通过。100K六对TTFT改善0.824%，95% CI[-0.035%,1.804%]，未达4%门；wall非劣通过、完整decode非劣失败。复用数值/生命周期证据，原10272槽/驻留/分派和原六FAIL保持；生产未改且停机、GPU1MiB、18089释放，自动续测仍PAUSED。不自动扩大其他候选。见 [P22](../reports/P22-HC-MEMCHECK-20261029.md)、[P23](../reports/P23-HC-RETAINED-EXPERT-COST-20261029.md)、[P24](../reports/P24-HC-PAIRED-PERFORMANCE-20261029.md)。 下面记录为历史阶段当时状态。

- **2026-10-29 HC16K数值与生命周期PASS，memcheck加载OOM后停止。** 四份独立managed HC保持原Device缓存/10272槽和实际分派，4019条raw、完整logits与486,388,612bytes有效状态全部逐字节一致。8请求生命周期通过（4096→16384→4096、保存恢复、两类取消续接）；随后memcheck在cuLibraryLoadData/cuBLAS初始化OOM，auto-cache已从10272降至9984，未READY、GEN0。未改参数凑通过，成本/正式性能NOT_RUN，原六FAIL保留；生产未改且停机、GPU1MiB、18089释放、自动续测PAUSED。见 [P20/P21报告](../reports/P20-P21-HC-16K-LIFECYCLE-20261029.md)。

- **2026-10-29 HC真实边界：4096数值门PASS，16K独立对照BLOCKED_VRAM，已停止。** 4096的3887条raw、全部logits与有效状态逐字节一致；自然C完成真实16384块、48层FFN，但匹配对照需990.001MiB、实余514.5MiB，主计算前拒绝。4次GEN1尝试、3次完成、零重试；生命周期/sanitizer/成本/正式性能未运行，原六FAIL保留。生产13保护hash不变、服务仍inactive/dead，GPU1MiB、18089释放，自动续测PAUSED。见 [P19报告](../reports/P19-HC-REAL-BOUNDARIES-20261029.md)。

- **2026-10-29 C运行及同路径HC数值验证完成：PASS。** 计算/SAVE后先停止并join监控，再QUIT，两个新GEN1均正常完成。自然C与同驻留/实际分派的独立HC缓冲区对照，3325条raw、248320个logits和有效状态全部逐字节相同，容差0；自然A/C仍为NUMERICAL_DIFFERENCE，旧失败与原六FAIL保留。10项护栏＋6项对照验收回归在本地和29通过。边界/生命周期/性能未运行；生产未改且inactive/dead，GPU1MiB、18089释放，自动续测PAUSED。见 [P18报告](../reports/P18-HC-C-COMPLETION-20261029.md)。

- **2026-10-28 HC-only scratch资格验证：BLOCKED_NUMERICAL_ORACLE。** 同chunk16384的启动借槽4388→3787，少601槽、实际借区约省990MiB；原P6同token A/A不逐bit。原布局原始字节定位显示layer3 FFN的HC输入/输出完全相同、主体后R不同，伴随动态CPU/GPU分派变化。B/C仅启动零请求，候选数值/生命周期/正式性能NOT_RUN；不能判无收益或采用。指标已预登记，原六FAIL保留、生产未改。见 [P13报告](../reports/P13-HC-SCRATCH-QUALIFICATION-20261028.md)。

- **2026-10-28 IQ3_S nt1 AVX2 gather 探针完成：REGRESSION，扩展门 NOT_MET。** 同P6完整配置确认IQ3_S占nt1 GU worker时间36.246%；只改两处codebook查表，逐bit、实际命中和新增ISA检查通过。完整专家六对耗时增加33.038%，配对95% CI[31.401%,34.607%]；单核热GU增加77.960%。频率未下降、未见进程swap或测量窗major fault。拒绝当前独立AVX2候选，不扩格式、不进整机验证。原六FAIL保留，生产未改、继续停机。见 [P12探针报告](../reports/P12-GU-GATHER-PROBE-20261028.md)。

- **2026-10-28 Ada MMVQ差量资格检查完成：NO_BENEFIT_SCREEN。** 同P6完整配置，4K/100K原请求各profile一次及无nsys控制一次，4请求均输出2048token。8个不同于旧IL89的表组合实际命中；新差量加全部quant/interleave超集在本次profiled完整请求的条件空间2.764%/2.003%，首末输出区间3.084%/3.240%。按限定筛查停止，IL89=0、SIDE=0全程保持。profiler扰动明显、控制轨迹不同，不能称严格未插桩上界或全表无收益；原六FAIL保留，生产未改/保持停机。见 [P11差量报告](../reports/P11-ADA-DELTA-QUALIFICATION-20261028.md)。 不自动推进单shape、SELECT_LONG、GU或其他候选。

- **2026-10-28 DEQUANT_SIDE=0资格核查完成，优先读 [P10-DEQUANT-SIDE-QUALIFICATION](../reports/P10-DEQUANT-SIDE-QUALIFICATION-20261028.md)。** 同P6完整配置，三原请求profile各一次＋无nsys控制各一次。目标基线路径命中，type/grid完全匹配245H16+55IQ候选/chunk；本次trace条件删除模型TTFT空间1.22%/1.73%/1.36%，判NO_BENEFIT_SCREEN，未开=1、未做开启parity或配对性能。不能扩大为严格未插桩上界、所有shape无收益或已测side1无收益。32K只是compaction后重读形态替代，未找到真实compaction历史。原六FAIL及P6正确性FAIL保留，生产13hash不变、保持停机，GPU/18089释放；不自动推进Ada/IMMA或其他优化。

- **2026-10-28 本地IQ3_S同发布revision复测完成，优先读 [P9-HIGHER-PRECISION-LOGITS](../reports/P9-HIGHER-PRECISION-LOGITS-20261028.md)。** 已有两个分片与IQ3_XXS同一ed59f920发布快照，4份全内容hash匹配；同token/图/库/NGL18/F16 KV，两个prime16/16 argmax仍错位数字＋EOS。较高平均位宽没有解决这两项失败；两套共同低比特PLE、基础checkpoint commit未知，不能扩大为基模缺陷或量化无关。原六FAIL、P6正确性FAIL及DEQUANT_SIDE未运行状态保持，生产未改/保持停机。未找到本地全16-bit同谱系模型；理想载荷约329.6GiB，现有磁盘仅约163.5GiB可用，不能照搬NGL18，不自动下载。

- **2026-10-28 独立logits对照完成，优先读 [P8-INDEPENDENT-LOGITS](../reports/P8-INDEPENDENT-LOGITS-20261028.md)。** 固定原完整token与同一GGUF，llama.cpp独立qwen4exp图重现两个prime错位数字及EOS，16/16长输入argmax一致，短控制另8/8。参考FP16 KV，Strata保留int8 KV和P6完整配置；logits非逐bit等价，库为已有87b37ea-dirty并冻结实际hash。当前证据更支持量化模型/原提示条件，未拆分基础模型与量化。原六FAIL、P6正确性FAIL及DEQUANT_SIDE未运行状态保留；不改生产/部署。下一项最小模型对照需同revision同处理的更高精度权重，不能拿另一模型代替；本轮未运行。

- **2026-10-28 六个长检索失败诊断完成，优先读 [P7-LONG-RETRIEVAL-ROOTCAUSE](../reports/P7-LONG-RETRIEVAL-ROOTCAUSE-20261028.md)。** gold/tokenizer/SSE核对无误；目标路径实际输出七位数字＋EOS，两个prime邻行取错，四个追问缺后缀。去MTP及lookup后零草稿，六项仍同错；明确完整格式或low thinking冷读控制能通过，原措辞warm仍失败。27请求与严格原gold完整保留，不能用控制通过替代原六FAIL；尚未独立拆分权重、量化与共用数值核。不改生产/引擎，不进入DEQUANT_SIDE或采用验证。

- **2026-10-28 v0.2.7隔离复测已完成，优先读 [P6-V027-BASELINE](../reports/P6-V027-BASELINE-20261028.md)。** tag固定5e8a4cca，原生源码未改，保留完整配置及六文件#1536/PT移植。Python402项与实际PT/回复复用通过；P3六个长检索原请求全部仍失败，真实恢复69625/102385 token成立。工具与seed43原末轮本次通过，不能据此宣称间歇错误已修复或整链成功。正确性门FAIL，DEQUANT_SIDE=0全程保持，专项测试及新八轮链NOT_RUN。不要跳过前置门或重跑覆盖原失败。生产未改、保持停机，GPU与18089释放。

- **2026-10-27 GU单格式探针已完成，优先读 [P5-GU-VNNI-PROBE](../reports/P5-GU-VNNI-PROBE-20261027.md)。** 唯一IQ3_S nt1，无VBMI的EVEX256整数融合，逐bit/ISA/命中通过，旧门控未改；完整专家六对改善−0.152%，95% CI[−0.570%, +0.245%]，扩展门NOT_MET。root只读APERF/MPERF与实际进程内存已核对。到此停止，不扩格式，不启动整机候选；生产未改、保持停机。该结果不证明其他等价优化已穷尽，也不覆盖P3质量失败。

- **2026-10-27 运行边界补测已完成，优先读 [P4-RUNTIME-BOUNDARIES](../reports/P4-RUNTIME-BOUNDARIES-20261027.md)。** 完整配置完成15分钟混合负载及10分钟连续100K冷读，峰值84°C；关闭KVRES的基线在682.70秒触发85°C，其热态后续未运行。长恢复、取消续接和独立同阶段内存对照已执行；实际额外host allocation为1.675794GiB，包含主12层及MTP一层，系统Shmem映射归因见报告。旧主采样遗漏引擎PID，已明确排除并补测，不能用其生成RSS结论。生产配置不变、保持停机；P3既有质量结论不变。

- **2026-10-27 补充组合实验完成；正式采用门未通过，质量非劣未建立，优先读 [P3-COMBINATION-KVRES](../reports/P3-COMBINATION-KVRES-20261027.md)。** 当前完整组合与仅关闭 KVRES 的性能表征完成 6 对、276 请求，96 个定长输出有效，8 个主指标 CI 均未达 4% 门；64K / 100K 含前缀复用，不能称完整冷读。原正式回放 `FAILURE` 与独立 4/4 同错保留。tool 关闭 / 开启为 29/30 对 28/30，protocol 各 30/30；两臂均观测到 69625 / 102385 token 实际恢复，但各六个长检索均未通过精确答案检查。Python 全链成功率关闭 2/2、开启 1/2，开启 seed 43 因未定义 `dst_balance` 导致旧功能失败，样本不足以因果归因。生产配置未改，全部实验进程退出，GPU 1 MiB、无计算进程，生产 inactive/dead、仍 enabled，13 个保护 hash 不变。下列“全部完成 / ADOPT”仅指 10-26 历史筛查和部署决定，后续表征不能覆盖本轮正式回放失败。

- Phase 0 与 Gate P0 已完成；#2253 Phase、单会话 Phase（#1536、CFG-PT）、CFG-SPEC-S（保持 `--spec 4`）、CFG-CPUSHARE-S（4096 为采用候选）、#3871（仅实验工具）已完成；NP-3 已完成（pool 代码方向 NO_BENEFIT，保留 `STRATA_LAB_NP3_TRACE` 工具）；#4040 Gate A NO_BENEFIT（未移植）；NP-RES 已完成（CFG-PCIEFRAC、`STRATA_PCIE_BALANCE` 都 NO_BENEFIT，O07 / O08 不立项）；#3307 Gate A NOT_APPLICABLE（未移植），派生零代码的 CFG-AUTOMAX（`STRATA_PREFILL_AUTO_MAX=16384`）为采用候选。报告在 `reports/`，不要重做。
- 用户用法是单会话长期追问（[docs/11_SINGLE_SESSION.md](../docs/11_SINGLE_SESSION.md)），后续次序见 README“执行次序”：真实 Pi 复核（需用户决定）→ CFG-SPEC-S → CFG-CPUSHARE-S → #3871 → NP-3（[plans/NP3_CPU_POOL.md](../plans/NP3_CPU_POOL.md)，已完成）→ NP-RES（已完成）→ #3307（已完成）→ #4040（已完成）。#1536、PT=0、CPUSHARE 4096、AUTOMAX 16384 已于 10-26 上线。2026-10-26 复查 v2 包后补测 CFG-ADAPT（NO_BENEFIT）→ CFG-KVRES（ADOPT，10-26 21:38 写入生产配置并冒烟通过）→ CFG-KVGROW（未过门）→ CFG-SPECCOST（NO_BENEFIT），全部完成（README 第 9～12 行，脚本在 29 `workspace/o09/`）。此后剩低优先级项（README 第 13 行）。
- 下面 Phase 0～4 是每个 PR / NP 项都要走的通用门；Phase 0 的 P0-T* 是全局一次性工作，已完成。
- 验证工具已并入 v2 包的修复（2026-10-26）：`stats` 遇缺项 / 重复 / 失败 / 未评分退出 2；请求发送前做 128K 预算检查，返回后核对 usage，漂移 >32 停止该场景；GPU 归属持续监控；收尾写 `COMPLETION.json` 或 `FAILURE.json`。`cfg --env` 仍只接受 `STRATA_*`，allocator 类变量（`MALLOC_*`）没有受控接口，需要时用 `extra_frozen_env` 并在报告写明。

## 执行阶段

### Phase 0 · 基线与适用性
- P0-T1：读 `sources/LOCK.json` 与 `docs/02_ENVIRONMENT.md` 中 29 的当前事实；运行 doctor，核实真实 CPU、模型（IQ3_XXS）、启动参数与 env、KV 驻留方式、加载后 MemAvailable、驱动。与文档不一致时以实测为准并记录。
- P0-T2：冻结生产 Git SHA（10-23 为 `a0116b27`，工作区有本地改动）、未提交 diff 的私有备份、二进制哈希、模型/pack/template/profile 身份。备份不上传。P→A0（0.1.43.1→冻结 main）是大迁移，由 P0-T2b 单独评估，不计入任何 PR。
- P0-T2b：P→A0 迁移评估（MIG），定义、指标和分支见 `docs/04_TEST_PROTOCOL.md`“P→A0 迁移评估”。排在 P0-T5/T6 之前，因为它决定后续结论最终落在哪个版本上。A0 构建与 P0-T3/T4 的 CPU 侧工作可以并行，GPU 串行。结论只有 MIG-PASS / MIG-REGRESS / MIG-BLOCKED 三种，后续按对应分支执行；除 MIG-REGRESS 明确允许的两项外，不在 P 上重复测试。
- P0-T3：拉取冻结 main 与 PR head，检索本 PR 的关键符号，输出 `PORT_AUDIT.md`：已存在／缺失／部分替代、冲突文件、已废弃 API。
- P0-T4：运行 `qualify` 和机制探针。不适用写 `READY.json` 的 `NOT_APPLICABLE`，说明条件；不强开内存容纳不下的缓存。共存负载导致 MemAvailable 门槛不过时写 BLOCKED 并交用户决定，不降门槛。
- P0-T5：decode 诊断构建（DIAG）。在 `workspace/repo` 另建 worktree，把 #1864（decode 计时补全）和 #3631（`STRATA_WINDOW_TRACE`）移植到冻结 main 上，用相同 cmake 参数单独编译。用固定 decode 负载拆清每个窗口的 adapt wait / verify / commit / draft / join / other 和 expert 读取构成，并在同一维护窗口跑 `b6_mmvq_bench`、`mmvq_il_parity --bench`（模型实际形状，逐位一致）。DIAG 不是 A0，结果不进入任何 A/B 配对统计，只用于判断 #3453 与 B6 行复用有没有空间。
- P0-T6：A0 配置对照。CFG-IL0、CFG-EXACT 与 CFG-MMAP 的定义、身份校验和采用规则见 `docs/04_TEST_PROTOCOL.md`“配置与诊断对照”。先测 CFG-IL0（成本最低，且直接决定 #3453 的目标），再测 CFG-EXACT，两者都通过时测组合。二者必须在任何 PR A/B 之前定论：通过就作为所有 arm 的公共 `extra_frozen_env`，不通过就不用；不得只给某个 arm 加。
- P0-T7：读 `docs/10_NON_PR_DIRECTIONS.md`，完成其中 NP-0 测量；据此决定 CPU 专家路径与 GPU 融合方向是否立项。其中的 CFG-* 对照与 CFG-EXACT 同样在 PR A/B 之前定论；CFG-CSTATE、CFG-UNLOCK、hugetlbfs 预留等整机配置必须先得到用户批准。
- **Gate P0**：MIG 已有结论；评审适用性与边界，确认资源和对应工作负载。未通过不得开发大改。

### Phase 1 · 设计与失败测试
- P1-T1：按专项文档划定最小差量，隔离运行时开关。原 PR 无完整开关时加实验专用 `STRATA_LAB_*`；明确区别于上游参数。
- P1-T2：先写能在 A0 失败的机制/正确性测试，再实现。不以“输出看起来正常”替代状态不变量。
- P1-T3：规划生命周期：加载、prefill、decode、取消、预算截止、异常、卸载、恢复。标注资源所有者、图捕获地址与线程同步。
- **Gate P1**：记录失败测试，评审是否会改变数值、分布或采样语义。

### Phase 2 · 最小移植与 CPU 验证
- P2-T1：逐符号适配，不盲目套整个 PR diff。禁止把分支中的旧主线、大型 benchmark 数据或不相关后端一并覆盖。
- P2-T2：A1完整关闭时还原 A0 行为；输出启动回执 `LAB_PR_<id> enabled=0|1`。它必须反映实际路径，不能只是打印配置值。
- P2-T3：执行相关单测、协议回归、编译；所有基线已有失败单独保留。承认未测后端。
- **Gate P2**：独立 review：功能、内存、线程、错误恢复、协议和可观测性；有 blocker 就停止。

### Phase 3 · 构建与单卡实验
- P3-T1：提交 candidate，完成 `READY.json`，记录已运行的 unit_commands。不要伪造 GPU 结果。
- P3-T2：同一工具链编译 A0/A1+B，记录 CMakeCache、编译器、依赖 SHA、二进制 SHA。sm_89，只构建自己的 worktree。29 上为 CUDA 12.3 / gcc 12.2 / cmake 3.25.1，main 能否用它编译未验证；失败如实记录，不自行升级 toolkit。
- P3-T3：维护窗口中运行 A/A noise → smoke → 专项 → full/Java agent。配置被安全门拒绝时修复原因，而不是绕过安全门。
- P3-T4：每个 PR 至少5轮配对；AB/BA次序平衡。冷引擎与热前缀分开；不擅自全机drop_caches。
- **Gate P3**：失败、NaN、错误工具调用、超限、状态污染或内存持续增长直接阻断采用。

### Phase 4 · 留出集与选择
- P4-T1：按冻结的主要指标统计，不在看过结果后换指标。Java/tool正确性是硬门，不只看tok/s。
- P4-T2：在未用于调参的真实 Java/Pi 任务上复验；记录上下文压缩、测试通过、重试、总耗时。不能用本包小题集声称生产能力无损。
- P4-T3：出具 `DECISION.md`：ADOPT_CANDIDATE / NO_BENEFIT / NOT_APPLICABLE / BLOCKED / REGRESSION。
- **Gate P4**：只推荐候选，不自动发布；部署前仍由用户审批。

## READY 的最小要求

复制 `templates/READY.example.json` 到对应 state 目录。填写真实 base/pr/candidate SHA、reviewed=true、专项机制证据、off/on参数与启动回执、可重新执行的单测 argv。命令数组不经过shell。`common` 中任何前提配置变更要列入报告，并同时应用于A0/A1/B。

`READY` 表示实现、代码评审和可在编排前完成的单测已完成，可以进入 GPU 资格验证，不表示 GPU 验收已通过。在 READY 文件另写 `gpu_validation: "NOT_RUN"`；GPU 结果由编排器另外生成。尚未完成实现写 BLOCKED；硬件/场景不匹配写 NOT_APPLICABLE。未找到额外差量可写 ALREADY_UPSTREAM，但必须给源码位置和行为测试，不能只凭文件名判断。

## 交付目录

每项 `workspace/state/pr-N/` 至少包含 `PORT_AUDIT.md`、`IMPLEMENTATION_PLAN.md`、`REVIEW.md`、`READY.json`、`DECISION.md`。每次测试 `workspace/results/` 保留原始请求哈希、响应、usage/timings、日志、遥测、编译身份、统计报告。不得把含真实代码/路径/密钥的日志自动提交到公共仓库。

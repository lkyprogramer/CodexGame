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
8. 模型生成的 Java 只在受限、无网络 Docker 容器内执行。所有工具调用经过本轮 allowlist 与 schema 校验；不得把测试工具映射为真实 shell。
9. **29 号机专属**：生产 Strata 已停止、机器在跑其他实验，未经用户明确允许不启动 Strata、不占 GPU。不改 systemd unit、NGINX、`production-18343.sh`、驱动、CUDA 12.3；不装内核模块、不改 initramfs/GRUB/内核参数（CFG-UNLOCK 经用户批准的维护窗口除外）；不写 `/home/hhtele/strata-0.1.43.1`（含 `data/` profile）；不占 18343；不运行 `./update.sh`；不删旧版本目录；不停共存容器。生产停启每次单独找用户授权。
10. 任何 arm 禁止 `STRATA_STAGE_PIN`（损坏 IQ3 系权重）和 `STRATA_ROUTE_RESIDENT`（改变答案）。不把 NGINX Bearer、SSH 密码、sudo 口令、Pi `apiKey` 写进文件、日志摘要或 git。
11. 噪声与确定性：29 上重启 A/A 约 5%、抽样配对约 7%；greedy 输出跨重启不逐字节一致。收益低于噪声判 NO_BENEFIT；正确性用断言/评分，不用跨进程 bitwise 比较。

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

# 附件实验包审计：从已上线基线继续，而不是重做 P0

审计日期：2026-10-25。审计对象：`attachment/strata_4090_128k_lab`。本轮只读原附件；未连接 29 号机，未启动 Strata、访问 GPU、改变服务或系统设置。下文将**历史实机报告**、**本轮源码检查/CPU复现**、**待验证推断**分开。源码位置均相对于原附件根目录。

## 1. 最优先纠正的状态

附件含一套 10 月 23 日编写的实验框架和七份 10 月 25 日执行报告。入口文档和配置示例没有完全跟随报告更新。最新 `reports/DEPLOY-A0-EXACT6-20261025.md` 说明生产已经升级；不能继续把 `START_HERE_AI.md`、`docs/02_ENVIRONMENT.md`、`GATE-P0` 中较早的“生产停止”“perf 未安装”“需要批准 EXACT6 上线”当作当前事实。

**最后已知生产形态 = A0 v0.2.3 + EXACT6 + host performance/C6-off。** 它仍应在下一次目标机只读 inventory 中复核，而不是由本轮文档宣称当前实时状态。

| 项 | 附件最后已知事实 | 证据 |
|---|---|---|
| CPU | Xeon Silver 4216，16 核/32 线程，AVX-512 VNNI、有 AVX2、无 VBMI | baseline-qualify §1、NP0 §2 |
| RAM | 2×32GB DDR4；报告读带宽约 36GB/s；引擎匿名内存 43.0GiB，其中 THP 36.7GiB | NP0 §2/§6 |
| GPU | RTX 4090 sm_89，24GB；驱动 610.57.04 | baseline-qualify §1 |
| OS/toolchain | Debian 12，运行内核 6.1.0-17-amd64，glibc2.36，gcc12.2，CUDA12.3；成功构建用 venv 内 cmake4.4.3/Ninja，而非系统 cmake3.25.1 | baseline-qualify §1/§3 |
| 模型 | Qwen3.8-Flash-Next **GSQ-RCO IQ3_XXS**，两份 GGUF；不是 IQ3_S | docs/02_ENVIRONMENT.md 部署身份 |
| 当前二进制 | A0 `5c8dd322528cc84f68f461ad54a506b9da8fa8d4`；sha256 `819ff262a1742e8b57eedc6203b015f7c9831dd4a94ecacbb5a8b1c865fade3d` | baseline-qualify §3、DEPLOY |
| 当前部署 | `/home/hhtele/strata-0.2.3`；模型服务名 `openclaw/Qwen3.8-next`；18343、NGINX28343链路不变 | DEPLOY §1/§2 |
| 原生产回滚基线 | v0.1.43.1，HEAD `a0116b2782a5b82622358c04a06496485d12b2d6`；binary sha256 `d245b0f2a2ee1ef1ea697aa5b0fc536eafd2ff589f74e763603af9dfd2508247` | baseline-qualify §2 |
| 运行参数 | `--spec 4 --spec-min-p 0.5 --kv int8 --max-context 131072 --vram-reserve-mib 974 --expert-cache auto --prefill auto --conversation-cache-mib 6144 --conversation-cache-slots 4`；MTP `/data/strata-data/mtp/rt` | MIG §1、GATE §2 |
| 基础 env | `STRATA_ADAPT_OVERLAP=1`、`STRATA_PREFILL_CPU_SHARE_MAX=3072`、两项 timing | baseline-qualify、GATE |
| EXACT6 env | `STRATA_SIDE_MIXER=2`、`STRATA_ATTN_DAILY=1`、`STRATA_GR_UP75=1`、`STRATA_GU_SWIGLU=1`、`STRATA_QSA_ROWS=1`、`STRATA_B6_MMVQ_ROWS=1` | CFG §5/§6、DEPLOY |
| host 改动 | 32逻辑CPU governor=performance；C6 disable，POLL/C1/C1E不变；linux-perf6.1.190安装、paranoid=1 | DEPLOY §1 |
| 共存负载 | 部署报告关闭 OCR 容器，NInfer服务 inactive/disabled，Next active/enabled | DEPLOY §1 |
| 未知 | KV 是否全驻显存仍缺明确回执；SSD型号、实际剩余容量需新inventory；327GB与170GiB是不同时间的报告，不应拼成“当前值” | docs/02、baseline-qualify |

不能从“文件名 IQ3_XXS”直接假定所有张量都同一位宽。NP0 实际 CPU 专家路径记录：偶数层 gate/up IQ2_XS + down IQ4_NL，奇数层 IQ2_XXS + Q2_0；dense、head 另有不同量化。验证工具应冻结完整 GGUF、pack、template、MTP 和 profile 的身份。

## 2. 已完成与不应重复立项的方向

| 方向 | 历史结果 | 新包处理 |
|---|---|---|
| P→A0 MIG | MIG-PASS，390请求，5轮；报告各组配对中位约0.97～1.02 | 保留迁移证据，不重新作为首阶段 |
| A0构建 | CUDA12.3 + gcc12.2成功，约4分钟 | 不再把“CUDA12.3能否编译”列为未知 |
| EXACT6 | 引擎窗口17.30～17.42→16.43ms，约-5.3%；受控greedy decode约+4～5% | 作为所有后续arm共用基线 |
| CSTATE组合 | 短上下文、18对，tok/s配对中位+2.2%；收益与组级噪声接近 | 已保留；长prefill/长decode、能耗未充分测；不能归因单独C6或调频 |
| CFG-IL0 / IL89 | 无端到端收益；IL89窗口-0.56%低于A/A约0.75% | 不再以旧issue的18%回退作为本机可期收益 |
| #3453核心Ada表 | 实测配置表没有窗口级收益 | 降级，只有表以外可证明剩余差量才立项 |
| POOL8 | CPU专家+21%，窗口+5.8%，decode退化 | 不推荐简单减到8 worker |
| NP1a Q2_0 128位路径 | 微基准快、整机无益，因bench测了引擎不走的分支 | 保留失败教训；先对齐实际pool调用入口 |
| LOOKUP2 | 当前代码生成语料无收益 | 可在真实copy/edit工作量占比确定后另测，不泛化“lookup无效” |
| learned profile | 既有稳态题集无收益 | 冷启动前几请求未覆盖，不能泛化为冷态无效 |
| MTPQ4-head | 窗口约-1.5%，采样组不稳定 | 低优先级边缘候选，不纳入公共基线 |
| THP/大页 | 85%匿名内存已有THP | 不把“开启THP”当未经验证的大收益 |
| #2964 | adaptive overlap不兼容，NOT_APPLICABLE | 不为启用它关闭已有效的overlap |
| #2253、CFG-MMAP | 尚未完成park/restore复现和A/B | 下一实质任务 |
| NP-3 CPU pool | 关键路径/带宽数据支持候选，实际优化未完成 | 先perf分解，随后小粒度任务/同步实验 |

重要口径：EXACT6窗口改善、CSTATE短请求改善、旧生产版本变化的分母不同，**不能相加或连乘作为已证实端到端总提速**。CPU miss 与窗口耗时的相关回归、带宽折算和 nsys trace 支持“CPU路径值得优先研究”，不等于已证明任何未来补丁每省1µs都线性映射到用户延迟。

## 3. 原始证据可复算性

包中有完整人读报告，但没有 29 的 `workspace/results/*`、`assets.json`、`inventory.json`、实际 local.json、`window-trace*.bin`、nsys数据、`mig_analyze.py`、`cfg_analyze.py`、`mkdecode.py` 或新 `decode-1c99c03c6c9e` 语料。因此本轮无法重新算历史CI、校验请求数、确认窗口过滤与启动参数，结论只能称“附件实机报告记载”。

100项 `MANIFEST.sha256` 没有覆盖7份reports。当前解包曾过滤点文件，所以本轮观察到 `.gitignore` 缺失是解包策略，不归因原ZIP。新包应保留原ZIP哈希，并为原始报告、来源索引和新增资产重建独立manifest；不要改旧报告冒充旧时验证通过。

本轮本地测试：原包发现38项；初次受沙箱socket限制，35通过、2环境错误、1无JDK跳过。随后获工具自动审核放行临时localhost socket后重跑：**37通过、1因JDK缺失跳过**。没有目标GPU验证。原始日志与manifest检查位于 `audit-evidence/`。

## 4. 计时和性能统计缺口

### 4.1 流式时钟语义混合

`lab/http.py:21-24` 的 `first_s` 在 reasoning、visible content、tool_calls任意一类首次出现时触发；`measurements()` 把它命名 `ttft_s`。真实Pi常启用thinking，这个数不是“用户首次见到答案”的延迟，也不代表首个工具参数可执行的时间。

建议保留兼容字段，同时新增 `first_reasoning_s`、`first_visible_s`、`first_tool_s`、`first_tool_arguments_s`，明确后者只说明首段参数到达。完整工具可执行时间应等JSON完成/finish_reason，并通过schema后另记。记录SSE事件到达间隔只能叫event gap，**不能叫token ITL**。精确逐token间隔必须由引擎token时间戳提供；前端可能合并多个token。

`chat():56` 使用 `timeout=min(60, timeout)`，这是socket阻塞期限；即使配置request_timeout_s=1800，长prefill无数据超过60秒仍会失败。`parse_sse` 绝对截止仅在读到下一行时检查，无法单独中断阻塞读取。需要明确分离 idle timeout 与 absolute deadline，并在每次读取前设置剩余超时；添加慢首字节、不断heartbeat、半帧阻塞的行为测试。默认短读限制不应隐藏在代码中。

### 4.2 统计只支持旧三臂，历史脚本未交付

`lab/statistics.py:42` 固定 `base/off/on`；CFG的 `base/cfg` 与 MIG的 `p/base` 不受通用stats支持。历史报告所需专用脚本又不在包。升级应在campaign中显式保存arms/comparisons/expected cases/rounds/metric/cache state，保留旧接口，支持任意显式pair；未知pair或缺失case、重复记录、未完成round、失败、not_run必须阻止候选结论。

原 `summarize` 从实际观察到的round推导期望round（:31），未对照campaign计划；若两臂同时缺同一case，列表仍相等，可能误把部分完成当完整完成。`fixed_output_comparable` 缺字段默认True；对非fixed quality请求，输出长度差异并不阻止wall比较。不要把基线只写半个答案带来的wall下降当优化。

原框架对轮级总wall做配对，方向合理；但总和可混入不同冷暖/上下文机制，且不直接给PR主指标。新增统计必须按 `group × cache_state × scenario × context_bucket` 分层，另行按预先冻结的真实流量权重报告端到端指标。不要把最快层的结果外推成统一提升。

历史报告有5轮×多题的 n=25等组统计，专用脚本缺失，无法确认bootstrap是否按fresh-engine整轮聚类。应要求raw重算时按轮或独立进程块重采样，同一进程的多题和同一请求的窗口不当独立样本。5轮只能筛查；决定性留出应预先定样本量、最小收益和质量非劣边界。CSTATE的18对来自6轮×3题，应以6轮block考虑相关性。

### 4.3 缓存冷暖未充分分离

同一arm启动后按固定case顺序运行；长检索与cold-prefill共享大段ledger但system不同，实际是否复用应由read/reused tokens验证。`validate_counter` 的两次探针已经改变冷态。不能把“新进程”直接叫“SSD冷读”；不能把prefill缓存命中速度写成kernel吞吐。root-churn与cache-edit是冻结转录回放，尚未证明某个park/restore机制真正发生。

## 5. 质量与128K漏洞

1. **JSON类型误通过。** `scoring.py:15/27` 直接用Python相等比较，`False == 0`、`True == 1`。因此工具schema要求boolean，模型返回0时可能被误记通过；nested list/dict同样受影响。`json.loads`默认允许重复key、NaN/Infinity。修复需严格递归类型比较、拒绝重复key和非有限数，并校验工具声明schema；不能用新评分直接重写旧89/90结论，没有raw无法追溯。
2. **EXACT6质量证据不足以叫等价证明。** 历史正式质量90次来自7开关组合，去掉CPU开关的EXACT6没有单独同规模质量重跑。报告认为子集无需重跑是推断。后续采用门应对实际候选构建重新运行质量、工具、长上下文、Java和Pi留出。
3. **模型/质量覆盖有限。** 短质量8题、工具5题、协议5题；Java目标机NOT_RUN；长检索为合成ledger，不能代表Java仓库理解、工具权限、thinking预算与compaction行为。固有 `schema-boolean` 失败要区分模型失败与评分缺陷，不准删除样本。
4. **128K输入并未执行。** 正确约束是模板/system/tools/history/input/output总和≤131072，另有4096安全余量。实机最大输入约122850 + 约139输出，后来长decode约122749+512；不能写“128K输入且持续长输出已验证”。
5. **边界覆盖要补齐。** 离线整数预算测试不代表服务端按相同模板计数。应补接近边界的tool schema、thinking、多轮tool结果、BPE保留、取消后恢复、KV/递推/MTP state同时恢复。常规上限留余量，专门超限请求应被本地拒绝且不发送，不靠自动截断使测试通过。
6. `runner.py:270` 计数漂移>32仅把score设False，后续仍可继续请求；与协议“停止”表述不一致。`scenario` 中没有逐请求server usage复核，也不比较返回计数与预算。应共用一次请求审计入口，出现无法确认计数的长测停止。
7. 默认full语料关闭thinking、temperature0；真实Pi启用高/中thinking并常用temperature1/top_p.95/top_k20。现包新增采样副本不在生成器，必须把这些profile做成冻结语料生成资产，不能手动随请求覆盖。

## 6. 运行控制与证据一致性

| 位置 | 观察 | 建议 |
|---|---|---|
| runner._monitor | 每2秒采RAM/GPU，但只检查RAM与温度；外来GPU进程只在启动后审计一次 | 持续对GPU PID、可执行文件、进程组与启动时间匹配；发现外来占用只结束本轮拥有的进程，不杀外来进程；留telemetry |
| make_run_config | 两个禁止STRATA env只在cfg入口拦截，原配置/extra_frozen_env/READY仍可进入 | 最终配置统一验证；禁用值的语义需明确，不能只检查某一路入口 |
| scenarios.run_scenario | 缺arm之间wait_released；缺finally assets/config复核；中断缺统一FAILURE回执 | 与campaign共用收尾；异常保留首要原因及审计失败列表 |
| assets.verify | 完整SHA在snapshot时算；campaign前后仅size/mtime和文件集合复核 | 明确这是元数据快检；每轮完整hash代价78GB不必盲做，但最终发布需hash复核或不可变资产保证；不要文档称每次完整hash |
| workspace.build | 记录HEAD/hash/flags，未冻结dirty diff与全部编译器/依赖身份 | 编译回执增加源码dirty摘要、依赖SHA、CMakeCache、编译器版本、host profile；DIAG与候选分离 |
| env继承 | STRATA env清理，但MALLOC_/GLIBC_TUNABLES/OMP等仍可能从父进程继承 | 显式记录会影响实验的环境白名单；CFG-MMAP不得依靠临时shell遗留 |
| cfg env | 只接受STRATA_* | 当前CLI不能直接执行文档中的MALLOC_MMAP_THRESHOLD_对照；新增受控allocator字段后再称支持 |
| run/config | 全局最大context固定，但spec/CPU worker等不少参数可由READY修改 | PR只允许预先声明干预字段，所有其他差异拒绝；配置实验与PR收益分离 |

## 7. 在现包上最小增量升级

不重写引擎，不自动部署。新ZIP可保留现有CLI兼容层，新增验证资产；历史报告保持原文。

### 第一批：测量可靠性（本轮可在CPU完成）

- `lab/scoring.py`：严格JSON解析/递归typed比较，工具schema拒绝路径测试。
- `lab/http.py`：各类首事件时钟、idle/absolute超时、保留token usage为空，chunk/event明确分离。
- `lab/statistics.py`：显式任意pair、完整计划核对、按场景冷暖分层、缺项失败封闭。
- `lab/runner.py`/`lab/scenarios.py`：共享request budget/usage复核、生命周期finally、wait_released、持续GPU所有权审计。
- `lab/plans.py` + `validate-plan`：仅离线检查park/restore计划完整性，声明engine adapter未实现；不把JSON计划通过写成实机机制通过。
- `tests/test_validation_upgrade.py` 等：用反例先失败再修复；mock仅用于GPU/时钟/进程依赖，实际JSON与统计核心使用真实文件和对象。

### 第二批：目标机下一阶段（本轮仅设计）

1. `runtime_snapshot.json`：记录最后已知部署与本次observed timestamp，冻结A0+EXACT6+host tuning。先检查perf是否工作，不再重复安装。
2. #2253计划：至少A→B→C→A、多轮重复、取消中断、错误恢复、cache已空却内存门拒绝等；记录park/restore/evict次数、快照真实bytes、heap RSS、MemAvailable、swap、read tokens、TTFT与trim耗时。使用正常门槛或提高cache准入门槛来可控复现，不能把主机安全门降到危险区间。
3. 互斥对照：A0+EXACT6 vs CFG-MMAP，及#2253 off/on；后续才组合。CPU host tuning所有arm一致。每次记录实际生效配置回执。
4. NP-3：先perf对齐同一稳态decode负载，区分计算、dispatch/barrier/spin、内存访问；按真实pool的Q2_0路径写微基准。worker8已有负结论，不作为默认优化。
5. 真实Pi留出：保留现有compaction/codemode/thinking/profile，只在副本profile指向实验端口；记录任务完成而非仅token吞吐；未来执行需独立目标机窗口授权。

## 8. 可执行命令与范围

原包已存在且本轮可执行的CPU命令：

```bash
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python -B -m lab.cli --help
PYTHONDONTWRITEBYTECODE=1 python -B -m lab.cli stats --results <已完成结果目录>
```

最后一条在旧包仅适用base/off/on，不能冒称能重算历史MIG/CFG。本轮新增CLI的准确参数及测试结果以 `HARNESS_UPGRADE.md` 为准；部署、perf/ncu采样和真实GPU运行命令只作未来操作说明，未在本轮执行。

目标机已存在的复现入口（**历史命令，本轮未执行**）：

```bash
./run.sh mig --execute --corpus workspace/corpora/mig-523966959432.json
./run.sh cfg --name <name> --env STRATA_NAME=value --corpus <frozen.json> --execute
./run.sh cfg --name <name> --arg=--pool-workers=8 --corpus <frozen.json> --execute
./run.sh run --pr 2253 --suite full --groups quality,tool,protocol --execute
```

不要用第三条重复宣布POOL8候选，它只说明CLI语法。#2253真正的park/restore验收仍需显式会话adapter；通用full不是该机制的替代物。

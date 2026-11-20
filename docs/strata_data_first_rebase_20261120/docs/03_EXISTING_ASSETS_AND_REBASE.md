# 03 · 已有能力、证据合同与新版迁移

返回[总入口](../README.md) · [数据模型与测量](05_DATA_MODEL_AND_MEASUREMENT.md) · [阶段任务计划](19_PHASE_TASK_PLAN.md)。

**唯一实验根仍是 `docs/strata_4090_128k_lab`。** 按“上游已经实现／现有 Lab 已经实现／文档规划／现场未知”四层接线。研究资料中的旧控制器名字保留为未来实现点；复用现有 runner、parsers、stats 和校验，不另搭常驻监控服务，也不假定规划 CLI 可以运行。

## 1. 监控、指标和工具：能直接复用多少

以下路径都相对 `docs/strata_4090_128k_lab/`，除非另注明。先核新版本格式/身份适配，绝不把旧冻结工具直接指向新版或生产。

| 已有且核过源码 | 可复用接口 / 现实限制 |
|---|---|
| [`lab/cli.py`][labcli]；[`lab/runner.py`][labrunner] | `./run.sh --config <私有有效配置> doctor` 是读取身份的既有入口；`OwnedServer`、`make_run_config`、`process_identity`、`validate_gpu_ownership`、`audited_chat`、`managed_server` 与 `evidence_lifecycle` 是现有启动所有权、resource guard、清理与保护基座。不要再写第二套 runner，也不把 `doctor` 当新版启动激活；旧 `run/auto/noise --execute` 是有副作用的工作流。离线可从 Lab 根 `python3 -B -m lab.cli verify`；旧 `stats --results <旧格式>` 不能替代 frontier 正式六对门。[命令说明][labcmd] |
| [`lab/http.py`][labhttp] `parse_sse`, `chat`, `measurements` | 已分 aggregate TTFT、reasoning、visible、tool name/tool args，原 SSE 与 usage，`cache_n`/`prompt_n`、`prompt_ms`/`predicted_ms`、draft offered/accepted。`token_itl_ms` 实现明确为 `None`；SSE 块数量不是 token ITL。计数存在性、版本字段含义、阶段重叠、缺失值都要显式记录。 |
| [`tools/frontier/identity.py`][identity] `collect_identity`, `validate_identity` | `python3 -B -m tools.frontier.identity --config <P00-P6-私有配置>` 是真实 CLI；依赖旧 P6 的 BUILD_COMPLETE、port、旧保护文件、旧依赖与 asset 清单，逐文件读取大权重，并调用本机 systemctl/nvidia-smi。新基线复用 schema/拒绝漂移理念，**不能直接套旧 P6 验证器或当零成本**。prepared config 不等于 active PID。 |
| [`tools/frontier/pi_history.py`][pihistory] `project_session`；[`warm_plan.py`][warmplan] `validate_warm_plan`；[`contracts.py`][contracts] | 真实 parent 链、工具历史复用、脱敏投影、离线门与数据 schema；拒绝不支持的媒体/compaction，历史投影不冒称抓获 HTTP 字节、未运行的真实 Pi 工具验收。不改 gold/工具回执/追问凑预算。 |
| [`tools/frontier/warm_run.py`][warmrun] `run_diagnostic`；[`p01b_run.py`][p01brun] `Adapter`；[`p01b_analysis.py`][p01banalysis] `summarize_capture`；[`lab_p01b_trace.hpp`][p01bh] | 真实 P01B 复用 P01 runner：`--plan ... --identity ... --out ... --execute` 需要授权，绑定旧合同、旧资产和专用捕获版；绝不直接运行旧实验。可复用签核、固定数组/请求后导出、CLOCK_MONOTONIC、native emitted IDs、完整/失败/NOT_RUN 记账。验证 `WINDOWS / DEPENDENCIES / ANALYSIS / QUALIFICATION` 的身份门、配额/overflow；只部分 host 依赖，没有全栈 CUDA/CPU/DMA DAG，也无 GPU observer-on/off 配对。 |
| [`tools/frontier/critical_path.py`][crit] `summarize_windows`；[`tools/combination/boundary_memory.py`][memory] `process_memory`, `system_memory`, `MemorySampler` | 旧文本 trace 只给 observations，不会推导 DAG。`MemorySampler` 可收 `/proc` 中 RSS/PSS/Swap、fault 和系统计数，无法单凭采样建立物理页归属/停顿因果；详细 smaps 不在热路径采。 |
| [`frontier/tools/headroom.py`][headroom]、[`paired_stats.py`][pairstats]、[`validate.py`][frontiervalidate] | `python3 -B frontier/tools/headroom.py --input <人工审核的依赖区间.json>`，unknown/无依赖证据时不授资格；`python3 -B frontier/tools/paired_stats.py --input <预登记六对.json>` 要 12 fresh engines/实际同哈希同固定输出，`6^6` exact bootstrap，主时间比 CI 上界 ≤`1-max(0.04,2×AA)`，其他时间比上界 ≤1.02。合成 P24 舍入 fixture 不是 raw、不能重跑算作新 P24。正式计划按新合同决定是否适用，不为 baseline 诊断直接预付 12 次启动。[现有 CLI 与 schema][offline] |
| [`tools/quality_gate.py`][quality]：`evaluate` 和实际 CLI `--input [--output]` | 配对独立任务二元质量、默认 2pp Clopper–Pearson/Bonferroni。30 个无分歧 smoke 不是 2pp 非劣证据；0/0 差异约需 183 个独立任务且采样假设成立。绝对质量门和部署均始终不评。测试 fixture 不是真任务；生成代码仅沿用受限 Docker。[质量协议][qualityreadme] |

**已有 schema 与本次差量的准确边界。** `REQUESTS_SCHEMA` 有 campaign/engine/request/phase、旧 `prime|append_1|append_2` 和 0–2 顺位、时钟域/body/rendered IDs/history/template/tokenizer/sampling/recipe SHA、prompt/read/reuse/thinking/content/completion/SSE/TTFT/decode/wall/失败；`WINDOWS_SCHEMA` 有 window/start/end/coverage、draft/accepted/committed、expert format/`nt`、dispatch/resident mask/shape/stream/graph/event 等 **nullable** 结构；`DEPENDENCIES_SCHEMA` 有 nodes/edges/evidence reference/verified or UNKNOWN，所有要求 `missing_reasons`。这些是 Python JSON Schema 字典 **不是 collector**，旧 runner/分析原件只有相应可捕获的子集；尤其不代表已采集 GPU stream/graph 或独立 session/turn/parent/cache-tier/queue-id、tool-schema 前缀、显式首思考/首可见统计。11-15 的 ExperimentSpec/BudgetLedger/RunEvidence/RoundEvidence/Decision 是合同模板，计划对正式 run 增 `phase/pair_id/run_block_id/treatment/case_id/task_manifest_ref/run_order_index`；应继承身份/门控，以版本化附件或适配器补实际字段，不能拿模板作执行原件。[旧 schema][contracts] · [11-15 事件合同][deltaevents]

**Foundation O0–O6 与 addendum E0–E4：计划，不是已装监控。** 11-10 增补档直接说明原 11-06 ZIP（162,748 bytes、SHA256 `0a08667d8fc03d91e1b961a9e705f4649b357e65f25e285db847c390c2c99934`）是设计；已在该包交付期进行 50 项离线单测、三项 `force_check` 合成反例（缺 request、短覆盖、单 stock arm 都能 PASS），没有产品 TSV parser、实际 receipt/graph importer、CUDA/PTX/SASS/NCU/Nsight 采集或硬件结果。`tools/frontier/exploration_control.py` 是既有规划中唯一控制器，但查过固定 499 项 Lab 递归树未找到该源码；不可演示其 CLI 或假定本地未提交状态。按已有组件/证据链接续而不是另搭控制器。Strata `504b143342a9fe1aa8320a7b31e11f5c0ac265c3` 的 source-inspected 状态：`force_check.py`、`check_cuda_spills.py`、dispatch 统计、run manifest、微基准存在；manifest 不自动给全部内容 hash、PID/timestamp，Graph capture 不等于执行。`STRATA_VERIFY_PROFILE=0` 在该固定源码仍是存在值，可改 fork/fusion，必须先比 observer-off，不能用 PROFILE 打开组充当正式基线；CUDA HES 对 Ada 不适用，按同机实际驱动/CUPTI 权限验证受支持的替代，不能偷偷提权或强制落为零。[增补集成][addintegrate] · [验证][addval] · [源码 probe][addprobe]。新版本的观测代码由本轮独立源码审计重新绑定。

**可实跑但本轮未运行的增补工具（增补根）：** `tools/contract_examples.py` 是 FIXTURE_ONLY 的 JSON 守卫；`python3 -B -m unittest discover -s tests -v` 和 `python3 -B tools/validate_addendum.py` 校验离线附件，后一工具可 `--require-manifest`；只有先取得历史同 hash 原件才运行 `python3 -B tools/probe_upstream_force_check.py --source <固定旧源码>`。这是 AST 提 `ceil8`、`binom_tail_ge`、`check` 的白名单 probe，不能直接拿新版文件喂旧 hash 检查器或调用 `gen/score`。新版 `check` 当前源码仍以 request ID 交集和各臂行数统计；完整性守卫依旧必须先覆盖同集合、实际 emitted token 位置、至少两 stock 臂、日志身份/截断/告警等，[新版源码][newforce]；这不是对新版重新执行 11-10 三反例的 GPU 结论。

## 2. Upstream v0.2.16 路径迁移及现成 telemetry

2026-11-20 核查 GitHub REST releases + refs + annotated tag：发布 `v0.2.16`（北京时间 11-19 05:57:34），annotated object `acdcf162fd4af0e566b4d4bbc49f71c4c14e350a` → release commit `64524fb9fc82222ddce554c0643b64f056ec8366`；另见 `main` `58ee3227720629ff2e41d640165ebe89c880dfef`，不用 main 代替 release。发布说明给 Terminal/App 0.2.16、Control/Engines 0.1.62、feed 128；归档源码路径与公开包的 SHA 分开，所有主机已安装状态仍 UNKNOWN。[release][newrelease] · [annotated object][newtag] · [固定树][newtree]

| 旧引用 | 新版 release tag 查到的实际位置/修改点 |
|---|---|
| 根 `CMakeLists.txt`、P6 的旧 `ggml_dir` 依赖 | [`engine/CMakeLists.txt`][newcmake]：CMake source root `-S engine`。源码允许测试及 CPU fallback 引用 `engine/third_party/strata-ggml` 或 CMake `STRATA_GGML_DIR` 覆盖；测试 OFF、自有 CPU quant ON 的发布配置源码不链接 ggml。不要拿旧外部 `.ref/llama.cpp` 当新版必需，也不要拿开启 ggml oracle 的测试构建冒充 release 包。 |
| `src/program/generate.cpp`；`src/core/conversation_{state,snapshot}.cpp`；`src/kernels/cuda/iq_kernels.cu` | 保留相对子路径，加 `engine/` 前缀：[`generate.cpp`][newgenerate]、[`conversation_state.cpp`][newstate]、[`conversation_snapshot.cpp`][newsnapshot]、[`iq_kernels.cu`][newiq]；CUDA 的源不应误接 `engine/sycl/` 镜像。旧 P01B 字符串补丁锚点和硬路径 rebind，不应用原 patch。 |
| `include/strata/core/{conversation_cache,dispatch_stats,run_manifest}.hpp` | `engine/include/strata/core/…`；[`dispatch_stats.hpp`][newdispatch] 计数默认启、`STRATA_DISPATCH_STATS=0` 关闭；[`run_manifest.hpp`][newmanifest] 由 `STRATA_MANIFEST` 指文件启用。Graph capture 次数与 actual launch 单列；按工具实际行为判断开关，不能一律用字符串 `0` 关。 |
| `serve/{server,frontend}.py`；`strata_control/drafting.py` | 加 `terminal/` 前缀：[`serve/server.py`][newserver]、[`serve/frontend.py`][newfrontend]、[`strata_control/drafting.py`][newdraft]。旧 `OwnedServer` 的 import roots、进程 cmdline、配置发现与实际 API 适配新版，不能因仍叫 frontend 直接应用旧六文件 port。 |
| `tools/force_check.py`；`tools/check_cuda_spills.py`、微基准 | 前者移至 [`terminal/tools/force_check.py`][newforce]；后者仍为 `tools/check_cuda_spills.py`。微基准文件见 `engine/src/kernels/{mmvq_il_parity,native_expert_bench}.cpp`、`engine/tests/cuda/pa_bench.cpp`，先核适配和 oracle，再决定是否为本次真实热点运行，未在本审计启动。 |

无需另写监控服务器。v0.2.16 [`terminal/serve/server.py`][newserver] 的 `/metrics` 已提供 `live`（状态、queue、读/生速、slot/run/wait）、近期请求、会话 cache、硬件、总量和时间；默认近期 12 笔，JSON `?requests=all` 也只是缓存所保留的请求；同 endpoint 可按既有 Accept/query 协商 Prometheus text。受授权保护的 [`/v1/telemetry`][newtelemetry] 复用现有 metrics/status，补 `instance.id`、slot/group/replica→request ID、`queued_at/admitted_at`、oldest queue、拒绝/超时/断开取消和活动记录（最多 50 活跃/32 事件，显式遗漏计数）；`--batch-telemetry` opt-in 能获低频 `engine_bstat` 窗口行数，stage `engine_pstat_host_span` 是 host span，不是 GPU 完成依赖。`terminal/strata_cli/client.py` 已有 legacy/只 status 回退和清洗，`strata monitor --once --json` 语法已核，[监控 CLI][newmonitor]。使用已配置的只读授权，不打印凭据；`--api-monitor` 默认关闭，会记录最多 100 条请求原始 prompt/answer/reasoning，**不为研究默认开**，与无正文的 `/metrics`、`/v1/telemetry` 不是一回事。详情源在 [`begin_request`](https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/terminal/serve/server.py#L4682-L4711)。

实际接入仅做 **现成 API/日志 → 版本化证据适配**。主动投影只存脱敏/哈希身份；有限活动环、采样和请求淘汰意味着快请求可能缺行，不能单靠轮询重建 request/turn/session 父子 DAG。客户端仍需冻结 session/turn/工具序、原请求与事件；较新版的 active/slot ID 用来 join 并对账，不做硬件计时、硬件路径或 cache 因果代理。缺端点、权限或字段都记 UNKNOWN，不改产品配置“补齐”旧样本。

## 3. 开发接线：先验证现有，缺一层仅补一层

| 层 | 输入 → 输出 | 本方案责任 |
|---|---|---|
| 本机只读识别 | 拟测制品、source/build 清单、主机与绑定配置 → 版本化 identity receipt | 对旧 collector 抽取可复用的 hash/验证逻辑；新版本适配 root/加载清单，不读取无关凭据，不声称 prepared equals live。 |
| 客户端时间/质量 | 相同任务、实际请求和 SSE/usage → request/turn IDs、首思考/可见/工具、wall、错误与 oracle | 以 `lab/http.py` 和原 scorer 扩展，旧 `token_itl_ms=null` 不用 chunk 数补；结构化接外部用例前锁真实 tool schema 及输入。 |
| 运行资源/状态 | OwnedServer、现有 /metrics、/v1/telemetry、旧日志与 /proc → 容量/队列/cache 和进程对账 | 用短采样和 host timeline，区分 usage/reuse、分配和 CPU/GPU residence、已活跃和空闲前缀；保护采样借用方式不变。 |
| 完成路径/观察器 | 选中的少量 request scope → nullable events/DAG/evidence | 原 P01B 仅历史 host windows；只在身份绑定、无生产修改和适配验证后补新版缺口。用现实支持的 Nsight/CUPTI 功能，先证明 observer 可比较。 |
| 实验控制/报告 | 现有 parser/runner/stats/quality + 预登记 → Scope、Ledger、Receipts、Decision | 仍是规划中的 `tools/frontier/exploration_control.py`，**仅待实现薄编排**。未在当前工作树找到它就不得将任何子命令当成可执行接口；复查现场已有实现后只补差量。 |

### 不能由现成 telemetry 代替的证据

1. `queued_at/admitted_at` 是服务时钟，不能与 GPU clock 直接相减。客户端 monotonic、native host monotonic 和 GPU 再各自校准，有绑定误差才跨域求区间；采样测不到的尾部是 unknown。
2. `/metrics` 所报 cache/reuse 与 profiler bytes 不代表页面是在 GPU、CPU 或 SSD，也不证明其依赖压住 sink。读取现有计数与带地址/生命周期的必要层分开。
3. 与服务生成无关的短请求、失败/取消或已从活动历史淘汰的请求都必须在客户端 ledger 保留。只读 monitor 默认不记录正文，也不由该 API 推断完整 turn lineage。
4. 有限采样、默认启用的 dispatch stats、opt-in profile、NCU replay 与 observer-off 正式 wall 是不同实验模式。观察器更改 dispatch/Graph 或跨过扰动门就保留为诊断证据，不据其判定整机加速。
5. 在源码能找到调用、环境变量、微基准或 test fixture 只证明存在。已加载模组/实际分派/complete window/相同质量才分别允许逐层升格。

直接使用的命令仅限本页明确核过接口且满足现场前提的工具。运行任何 GPU/模型/服务/远写前仍需阶段权限。恢复历史原件优先于重跑；资料补测优先按[证据缺口](01_BASELINE_AND_HISTORY.md)和[台账](02_NO_REPEAT_LEDGER.md)明确提出。

[deltaevents]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/ninfer_strata_source_delta_exploration_20261115/docs/09_EVENT_AND_ARTIFACT_CONTRACT.md
[addintegrate]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_foundation_kernel_evidence_addendum_20261110/docs/03_BASE_INTEGRATION.md
[addval]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_foundation_kernel_evidence_addendum_20261110/VALIDATION.md
[addprobe]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_foundation_kernel_evidence_addendum_20261110/validation/upstream_probe.json
[labcli]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/lab/cli.py
[labrunner]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/lab/runner.py
[labhttp]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/lab/http.py
[labcmd]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/docs/09_COMMAND_REFERENCE.md
[identity]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/tools/frontier/identity.py
[pihistory]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/tools/frontier/pi_history.py
[warmplan]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/tools/frontier/warm_plan.py
[contracts]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/tools/frontier/contracts.py
[warmrun]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/tools/frontier/warm_run.py
[crit]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/tools/frontier/critical_path.py
[memory]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/tools/combination/boundary_memory.py
[headroom]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/frontier/tools/headroom.py
[pairstats]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/frontier/tools/paired_stats.py
[frontiervalidate]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/frontier/tools/validate.py
[offline]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/frontier/tools/README.md
[quality]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/tools/quality_gate.py
[qualityreadme]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/tools/QUALITY_GATE_README.md
[newrelease]: https://github.com/Niko1221/Strata/releases/tag/v0.2.16
[newtag]: https://api.github.com/repos/Niko1221/Strata/git/tags/acdcf162fd4af0e566b4d4bbc49f71c4c14e350a
[newtree]: https://github.com/Niko1221/Strata/tree/64524fb9fc82222ddce554c0643b64f056ec8366
[newcmake]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/CMakeLists.txt#L585-L599
[newgenerate]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/program/generate.cpp
[newstate]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/core/conversation_state.cpp
[newsnapshot]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/core/conversation_snapshot.cpp
[newiq]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/src/kernels/cuda/iq_kernels.cu
[newdispatch]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/include/strata/core/dispatch_stats.hpp
[newmanifest]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/engine/include/strata/core/run_manifest.hpp
[newserver]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/terminal/serve/server.py
[newfrontend]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/terminal/serve/frontend.py
[newdraft]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/terminal/strata_control/drafting.py
[newforce]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/terminal/tools/force_check.py#L265-L339
[newtelemetry]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/terminal/serve/server.py#L6672-L6800
[newmonitor]: https://github.com/Niko1221/Strata/blob/64524fb9fc82222ddce554c0643b64f056ec8366/terminal/strata_cli/monitor_commands.py#L49-L61
[p01brun]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/tools/frontier/p01b_run.py
[p01banalysis]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/tools/frontier/p01b_analysis.py
[p01bh]: https://github.com/lkyprogramer/CodexGame/blob/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b/docs/strata_4090_128k_lab/tools/frontier/lab_p01b_trace.hpp

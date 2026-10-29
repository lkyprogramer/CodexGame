# 交付验证记录

验证日期：2026-10-23（初稿），2026-10-26 追加（见下节）。本记录区分**本包已经执行的验证**和**必须在用户4090执行的验收**。29 号机上的实测结果在 `reports/`，不在本文件重复。

## 已实际执行并通过

| 项目 | 结果 | 证据 |
|---|---|---|
| Python 单元/集成测试 | **31 tests，0 failure，0 error** | `evidence/final_tests.txt` |
| 8套可信Java参考实现 | 全部 `javac --release 8` 编译成功，断言输出 `ALL_OK` | `evidence/java_reference_checks.json` |
| 真实本地HTTP/SSE | 启动loopback测试服务，验证片段重组/usage/timings/结束语义 | `tests/test_integration.py` |
| 上下文预算 | 131072总上限、输出余量、错误计数拒绝 | `tests/test_core.py` |
| 题集结构 | full=82、smoke=21；长输入/根检查点/编辑链结构 | `tests/test_corpus.py` |
| Git工作区隔离 | 临时真实Git仓库克隆/worktree，生产参照保持不变 | `tests/test_workspace.py` |
| 资产身份 | 模型文件变化被检测并拒绝继续 | `tests/test_workspace.py` |
| 统计拒绝路径 | 失败配对、请求hash不同、定长输出不足、未评分项不计有效收益 | `tests/test_additional.py`、`tests/test_integration.py` |
| 子进程超时 | 终止本命令拥有的进程组，保留已产生日志 | `tests/test_processes.py` |
| 脚本语法 | `compileall`、`bash -n run.sh`、CLI help/list通过 | `evidence/cli_help.txt` |
| 数据与PR锁 | 所有JSON解析、10个head为40位SHA、文档/PR一一对应 | `evidence/local_validation_summary.json` |

Java参考程序是本包作者编写的可信测试代码，只用于验证断言本身，不是模型产物。模型产生的Java在目标环境仍必须使用离线受限容器评分。

结构化题集测试使用假的token counter来验证生成器逻辑，**没有冒充实际Qwen tokenizer计数**。目标机运行`corpus`时会使用固定Strata代码和用户自己的GGUF/tokenizer；每个arm启动后还会核对服务端实际usage。

## 2026-10-26 追加验证（v2 验证工具并入、单会话工具收编）

| 项目 | 结果 | 说明 |
|---|---|---|
| v2 验证工具并入（`lab/*.py` 8 个文件、`tests/` 11 个文件、`tools/quality_gate.py`） | 29（Python 3.11）：**103 tests OK**；本机 macOS（Python 3.12）：103 tests，1 failure | 失败项 `test_copy_config_never_mutates_original`：macOS 临时目录 `/var` → `/private/var` 符号链接使路径前缀比较不成立；v2 原包在本机同样失败，29 Linux 通过。并入前 29 的旧代码备份为 `workspace/lab-code-backup-20261026.tgz` |
| 并入前提 | v2 包的 `lab/core.py`、`tests/test_mig.py` 与本包逐字节相同 | 说明 v2 基于本包当前代码修改，整文件替换不丢本包改动 |
| `quality_gate` 示例 | `quality-smoke-30.json` 退出 1（`NONINFERIORITY_NOT_ESTABLISHED`），与 README 预期一致 | 离线计算，不跑模型 |
| `chain_bench.py` Docker 评分（29，`python:3.12-slim`） | 参考实现 8/8（4.6 s）；只实现需求 1 的版本 1/8；容器内联网失败；不给镜像返回 NOT_RUN；结束后无残留容器 | 无网络、只读、非 root、512 MiB / 2 CPU / 64 PID、`--pull=never` |
| 10-25 编码链重评 | 6 条链 48 个评分点用容器重评，与当时宿主机评分逐一相同 | 当时在宿主机直接执行模型代码属于违规，已更正，见 [单会话](docs/11_SINGLE_SESSION.md) |
| 上游 v0.2.6（`4b9e05a2`）与 A0 对照 | `pool.cpp`、core、prefill、CUDA 无改动；AVX-512 单 token 行需要 4216 没有的 VBMI 类指令；async tier 在 `ADAPT_OVERLAP=1` 下不启用 | 本地 blobless clone 比对（29 访问 GitHub 不稳定）；决定保持 A0 基线，见 `sources/LOCK.json` |
| 新 PR 锁定 | #3871 / #4040 / #4039 的 head SHA 用 `gh` 核对为 open | 写入 `sources/LOCK.json` 与 `config/experiments.json` |
| `tools/session/*` 敏感信息扫描 | 没有 Bearer、密码、`apiKey` | 从 29 拷回后扫描 |
| v2 GPU 归属检查误报修正（`lab/runner.py` `owned_by`） | 先写的两条回归测试红→绿；29：**105 tests OK**；本机 105 tests，1 failure（同上，macOS 路径） | Strata `serve/lifeline.py` 用 `os.setpgid(0, 0)` 把引擎放进自己的进程组，旧检查只认 owned server 的进程组，误报 `foreign GPU process appeared`。现在接受 owned server 的后代进程（沿 ppid 上溯 ≤ 8 层）；exe、128K argv、启动时刻连续性检查不变 |
| CFG-SPEC-S 两个 campaign | 都写出 `COMPLETION.json`；`stats` 退出 0（spec3）/ 2（spec5：2 个采样回答自然结束、缺对） | 见 [P2-CFG-SPEC-S](reports/P2-CFG-SPEC-S-20261026.md) |
| CFG-CPUSHARE-S 三个 campaign + trace 单臂 | 都写出 `COMPLETION.json`、final audit PASS；`stats --metric ttft_s / prompt_ms` 都退出 0，`failures` / `unscored` / `invalid` 为 0；`read_mismatch` 0，引擎行全部对上 | 见 [P2-CFG-CPUSHARE-S](reports/P2-CFG-CPUSHARE-S-20261026.md)；新工具 `tools/analysis/ttft_trace.py`（trace 单臂 105 个请求全部对上） |
| #3871 候选 `kq_cpu_bench`（29） | A0 版本在本机组合上 3 次 exit 139；候选 exit 0，头行声明走 pool 路径；IQ2_XS + IQ4_NL 组合与 NP-0 一致（35.2 vs 35.3 GB/s）；补测其余 8 种组合，exit 0 | 见 [P2-PR3871](reports/P2-PR3871-20261026.md)；只构建 `kq_cpu_bench` 目标，cmake 参数与 base build-lab 相同 |
| NP-3 perf + 非 serve 分阶段汇总 | serve campaign `pr-0-20261026-032435` COMPLETE、final audit PASS；perf 按 pid 采样成功（无 sudo）；非 serve 模式 3K / 40K 两次退出 0，prompt token 数与 corpus 计数一致（`np3_tokens.py` 内置断言） | 见 [P2-NP3-PERF](reports/P2-NP3-PERF-20261026.md) |
| NP-3 trace 构建（`lab/np3` = A0 + `STRATA_LAB_NP3_TRACE`） | 构建 rc 0、pool.cpp 无新警告；`pool_tasks_test` trace 关 / 开各 360 次 bit 级比对通过（192 次 NUMA split test 模式）；`pool_test`、`pool_stress` 在 4216 上缺 VBMI 而 SKIPPED（不算通过）；非 serve 模式 13 次运行退出 0；trace 扰动 +2.6%（同一 token 轨迹） | 见 [P2-NP3-TRACE](reports/P2-NP3-TRACE-20261026.md)；工具 `tools/np3/trace_patch.py`、`trace_summary.py` |
| NP-RES：pcie030 / pciebal campaign | 两个 campaign 均 COMPLETE（pciebal final audit PASS），5 轮 AB / BA；pcie030 cfg 无 `PCIe share` 调整行；pciebal 无 serve 端回执行，以实际 PCIe 份额 8.2% → 22.3% 和源码条件作为生效证据 | 见 [P2-NPRES](reports/P2-NPRES-PCIEFRAC-20261026.md)；`spec_analyze.py` 配对；O07 / O08 / O09 无 GPU 测试 |
| #3307 Gate A：ring 深度与 auto chunk 上限（generate 模式） | A0 base 二进制，20 次运行全部 exit 0；`STRATA_PREFILL_RING` 以借用 slot 数 2269 / 2441 / 2621 为回执，`STRATA_PREFILL_AUTO_MAX` 以 `prompt chunk auto` 行为回执；同输入同 seed 的 8 个采样 token 在全部设置下相同（非逐位证明） | 见 [P2-PR3307](reports/P2-PR3307-20261026.md)；脚本 `workspace/pr3307/ring.sh`、`automax.sh` |
| CFG-AUTOMAX serve campaign | `pr-0-20261026-081733` COMPLETE、final audit PASS；cfg 启动行 `prompt chunk auto: 16384 tokens`；`read_mismatch` 0；两 arm expert cache 都是 9420 slot | `cpushare_analyze.py` 配对，逐步拆分按 `requests.jsonl` |
| CFG-AUTOMAX 长上下文 campaign | `pr-0-20261026-084843` **BLOCKED（THERMAL_GUARD，85 °C）**，`FAILURE.json` 记 `partial_results_preserved`；完成 1 对完整 AB 加 cfg 9 题；123K 上下文下 16384 chunk 无显存错误 | 未补跑：runner 无 arm 间冷却，不调高保护阈值；见 [P2-PR3307](reports/P2-PR3307-20261026.md) 第 5 节 |
| 生产更新（2026-10-26） | 合并分支 `lab/prod-20261026` 单测 396 项 OK（生产 venv，unittest）；打补丁前 7 个文件与 A0 一致、补丁后与分支一致；启动回执 `LAB_PR_1536 enabled=1`、`LAB_CFG_PT default=0`、`prompt chunk auto: 16384`；进程环境四个开关在位；PT=0 用 prompt token 数验证（157 / 284）；冒烟短问答与 27K 读入正常；NGINX 不带 Bearer 401 | 见 [DEPLOY-PROD](reports/DEPLOY-PROD-20261026.md)；#1536 在生产上只有回执，未做功能复用验证 |
| 生产再次停机（2026-10-26 09:44） | 用户同意；停前确认 GPU 利用率 0%、上线后只有冒烟请求；停后 `inactive` / 仍 `enabled`，GPU 显存 1 MiB、无计算进程，MemAvailable 57.9 GiB | 恢复需用户发话 |
| runner：cfg 模式放行 `--kv-resident` | `make_run_config` 的冻结参数表在 `ready` 带 `cfg_name`（配置实验）时去掉 `--kv-resident`，PR 对照仍拒绝；新增 `tests/test_mig.py::test_kv_resident_only_changes_in_a_config_campaign`。本机 `tests.test_mig` 8 项 OK；本机全量 106 项中 1 项失败（`test_additional.test_copy_config_never_mutates_original`，macOS 上 `/var` 解析成 `/private/var` 的路径前缀比较，与本次改动无关）；29 上 `tests.test_mig tests.test_additional` 12 项 OK；`MANIFEST.sha256` 重建，29 `./run.sh verify` 161 文件 VERIFIED | 依据 START_HERE 第 5 条：改 KV resident 是另一个配置实验 |
| CFG-ADAPT campaign | lag2nw `pr-0-20261026-094530`、async `pr-0-20261026-105632` 都 COMPLETE、final audit PASS、`engine_unmatched` 空；回执：lag2nw `adaptive overlap: off: not with STRATA_ADAPT_LAG / STRATA_ADAPT_NOWAIT`，async `adaptive tier asynchronous (--adapt-async 1)` 且每进程约 3,550 轮交换；两臂专家槽都是 9420 | [P2-CFG-ADAPT](reports/P2-CFG-ADAPT-20261026.md)；新增 `tools/analysis/adapt_cost.py`（窗口加权统计） |
| CFG-KVRES campaign | decode `pr-0-20261026-120749`、追问读入 `pr-0-20261026-154218`、质量 `pr-0-20261026-161253` 都 COMPLETE、final audit PASS；cfg 回执 `KV streaming: 20480 of 131072 cells per QSA layer in VRAM, the K/V in 1.55 GiB of pinned RAM`、`expert cache 10290 slots`；追问读入两 arm 均 `prompt chunk auto: 16384`，`read_mismatch` 0，脚本退出后 `config/local.json` 已恢复（核对 `extra_frozen_env` 只剩 EXACT6） | [P2-CFG-KVRES](reports/P2-CFG-KVRES-20261026.md) |
| CFG-KVGROW campaign | `pr-0-20261026-132026` COMPLETE、final audit PASS；cfg 回执 `elastic K/V: 16384 of 131072 cells in VRAM`、`expert cache 10296 slots`，运行中有 grow / trim 记录 | [P2-CFG-KVGROW](reports/P2-CFG-KVGROW-20261026.md) |
| CFG-SPECCOST campaign | `pr-0-20261026-143100` COMPLETE、final audit PASS；无专门回执，生效由各组平均 T 下降 0.04～0.38、draft 时间下降确认 | [P2-CFG-SPECCOST](reports/P2-CFG-SPECCOST-20261026.md) |
| 生产启用 KVRES（2026-10-26 21:38～21:42） | 用户要求；配置备份 `backup-20261026-kvres/`，diff 只多 `--kv-resident 20480` 两行，JSON 校验通过；回执 `KV streaming: 20480 of 131072 cells per QSA layer in VRAM`、`expert cache 10290 slots`、`prompt chunk auto: 16384`、`LAB_PR_1536 enabled=1`、`LAB_CFG_PT preserve_thinking default=0`；引擎命令行与两个进程的 env 在位；`/v1/models` loaded，NGINX 不带 Bearer 401；冒烟：短问答 119.9 tok/s，29,955 token 冷读 8.18 s 答对，停放后 `restored 30006 tokens (live)` 答对；一次采样追问错答（350 行答 4），固定文档复核 greedy / 采样 32/32 正确；验证后 `inactive` / 仍 `enabled`，GPU 1 MiB | [DEPLOY-KVRES](reports/DEPLOY-KVRES-20261026.md)；T3 错答的随机文档未保存，无法两臂重放 |
| #4040 Gate A（离线日志分析） | 18 段会话 / 编码链、151 次引擎调用全部解析；`suffix drafts` 行确认为每次调用一行（非累计），按调用配对 | 见 [P2-PR4040](reports/P2-PR4040-20261026.md)；工具 `tools/analysis/lookup_share.py`；未移植、未跑 GPU |

未验证：`tools/session/`、`tools/park/`、`tools/analysis/` 改为按包根解析路径后，没有在 29 上重新完整跑一次会话（只验证了 `chain_bench` 的评分路径）。

## 明确未执行（初稿时状态；29 上已完成的部分见 `reports/`）

- RTX4090上的CUDA编译、kernel parity、性能/温度/VRAM测量。
- 10个PR在固定main上的最终移植、冲突解决及完整代码评审。
- 目标模型128K真实Prefill、MTP、KV恢复、长时Pi工作流。
- Docker内模型生成Java评分的目标机集成（本地验证只编译可信参考代码）。
- 原生Windows GPU进程生命周期；WSL2目标环境的PID审计。
- DFlash2专用服务配置适配器，须由执行AI按PR10任务开发并验证。

所以本包不存在“4090已提速X%”的本机结论，也没有已替换生产配置。PR历史收益在专项文档中有来源与限定条件，不写入本机测量结果。

## 红绿测试历史

`evidence/`内保留早期失败与后续通过记录。早期`*_red.txt`及stage日志是开发历史，**不是当前失败状态**；当前最终结论以`final_tests.txt`和最终Java检查JSON为准。开发时发现Java断言字符串转义和超时日志保留问题，已修正后重跑整个测试集。

## 包完整性

`MANIFEST.sha256`覆盖交付的固定文件，不覆盖用户后续生成的local.json和workspace；它是完整性校验，不是作者数字签名。执行：

```bash
./run.sh verify
./run.sh selftest
```

ZIP另附同名`.sha256`便于核对下载字节。执行AI修改本包脚本前应另复制一份，保留原始包及哈希，不要抹去原始验证记录。


## 2026-10-27：当前完整配置与仅关闭KVRES的组合验证

完整结果见 [P3-COMBINATION-KVRES](reports/P3-COMBINATION-KVRES-20261027.md)。本轮正式采用门未通过，正式质量非劣未建立；以下将“执行完成/收尾审计”与“答案或任务通过”分开记录。

| 检查 | 实际结果 |
|---|---|
| 本机 `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_combination tests.test_combination_chain -q` | 23项通过；29相同两模块也23项通过，输出在原始目录 `unit-tests.log` |
| 本机 `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_combination_restore -q` | 8项通过 |
| 原31题正式回放，6对计划 | 第14请求长检索失败停止；exit2，保留FAILURE，其余未运行 |
| 原失败请求精确复现，2对 | 4/4同错；COMPLETE/final audit PASS，质量失败，exit2 |
| 固定性能表征，6对 | 276请求完整；96定长2048有效；3个工具类型失败；主指标八层95% CI均未达到4%门；COMPLETE/final audit PASS，exit2 |
| 实际历史恢复 | 16阶段完成；两臂均恢复69625/102385token；每臂6个长检索均未通过精确答案检查；COMPLETE/final audit PASS，exit1 |
| Python生成历史链，2对、每链8轮 | 31/32轮通过；完整链关闭2/2、开启1/2；失败链按2400秒记账；COMPLETE/final audit PASS，exit1 |
| 本机 `pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm test:integration`、`pnpm build` | 均exit0，日志在 `workspace/combination/kvres-20261027/local-verification/`；build有既有Phaser大chunk提示 |
| 生产保护与进程收尾 | 13个保护文件SHA256不变，生产inactive/dead仍enabled；GPU1MiB、无计算进程，无本次实验驱动/服务进程；23份运行配置临时key移除 |
| 原始数据本地复核 | 609个原始文件SHA256、342条请求body hash、3份corpus hash全部一致；见 `LOCAL_INTEGRITY_CHECK.json` |

新增工具仅位于 `tools/combination/` 和三份对应测试。原生引擎复用已确认与生产相同的binary，不伪称本轮重新编译。64K/100K性能题实际包含16K/48K前缀复用，不能算全量冷读；Python链实际最大输入4903token，不能算长上下文Java/Pi任务。

限定本轮文档的 `git diff --check` 通过。全实验包范围的 `git diff --check -- docs/strata_4090_128k_lab` 报既有 `lab/statistics.py:205` 文件末尾空行；该文件不是本轮修改，保持原样。没有重跑全量实验包selftest；本轮使用上述定向测试及实际GPU运行。


## 2026-10-27：运行边界补测

结果见 [P4-RUNTIME-BOUNDARIES](reports/P4-RUNTIME-BOUNDARIES-20261027.md)。本轮验证当前组合的温度、真实长恢复、取消续接及进程/系统内存构成，不重做P3采用统计。

| 检查 | 实际结果 |
|---|---|
| 本机 `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_boundaries -q` | 最终8项通过；收尾PID复用修正后再次8项通过，日志见原始目录 `package-final-tests.log` |
| 29 `/home/hhtele/strata-0.1.43.1/.venv/bin/python -B -m unittest tests.test_boundaries -q` | 最终8项通过，含loader线程/显式引擎PID；收尾版本8项也通过，见 `package-final-tests-29.log` |
| CUDA API追踪可信探针 | g++实际编译观测库和探针；8MiB allocation＋16MiB registration，4事件、峰值24MiB、释放后0；不代表重编CUDA引擎 |
| `run_boundaries.py ... --out run-v3 --heat-seconds 900 --execute` | exit1：base在682.70秒达到85°C，28/29记录通过；cfg完成915.93秒混合负载及热态步骤，43/43通过；保护与收尾有效 |
| `run_prefill_stress.py ... --arm cfg --execute` | exit0：625.45秒、23个冷读＋qualification共24/24通过，峰值84°C；base按热保护条件未运行 |
| `run_memory_pair.py ... --execute` | exit0：两臂各14/14通过；loaded阶段确认真实引擎smaps存在，14组body hash一致 |
| 本机 `pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm test:integration`、`pnpm build` | 本轮均exit0；日志及results.json在本轮原始目录 `local-verification/`，build仍有既有Phaser大chunk提示 |
| 本地原始证据复核 | 984文件SHA256、132条已记录请求body/budget、122条非取消响应usage（含1条热中止的零输出响应）、2份corpus和各阶段源码全部一致；另有初次取消的原始记录因harness错误未形成评分行，未补造 |
| 生产与资源收尾 | 13保护文件hash不变，inactive/dead/enabled；GPU1MiB、无计算或本次驱动进程；7份实验临时key移除 |

早期KeyError、提前中断的run-v2、旧采样漏引擎及单位测试修正均保留。旧主采样仅用于系统内存/CUDA/GPU遥测，不能用于引擎RSS/PSS。交付版主runner已采用补测验证的全部线程及显式PID枚举；GPU结果仍对应各自冻结源码，没有重跑或替换旧结果。

新增交付为6个工具源码、1个测试模块和P4报告。范围检查通过，包MANIFEST已更新；全包既有 `lab/statistics.py:205` EOF空行保持原样。未运行新的全量lab selftest。

## 2026-10-27 单格式GU探针（P5）

结果见 [P5-GU-VNNI-PROBE](reports/P5-GU-VNNI-PROBE-20261027.md)。完整配置CPU miss统计闭合，唯一选IQ3_S nt1；原实际oracle符号确认。只做整数融合，旧ISA门控及其他路径保持。

| 项目 | 实际结果 |
|---|---|
| 实机构建与pool_tasks_test | exit0，360次bitwise；缺VBMI的其他模式skip不计通过 |
| 错误stub红色证明 | 真实GU比较exit2，首字节不一致；红色源码/二进制保留 |
| 正式数值 | 100000整数向量、1310720 realGU dot、1024专家阶段、509个pool输出数组逐bit一致；4个回退场景通过 |
| ISA/命中 | 新EVEX256白名单及baseline隔离PASS；archive554函数/72宽/0违规；pool候选4191次，全部开启测量臂命中为正、关闭为0 |
| 完整链六对 | 改善−0.152%，配对95% CI[−0.570%, +0.245%]；NOT_MET/NO_BENEFIT，停止扩展及整机候选验证 |
| 频率与内存 | root只读MSR成功，每臂测量窗56区间/100%调度；owner频率约2.346GHz；实际PID采样，VmSwap0、测量内部major fault0，未采集IMC/LLC流量 |
| 工具测试 | 本机及29定向7项通过；统计门、ISA编码拒绝和profile闭合均覆盖 |
| 根仓库 | 本轮pnpm typecheck/lint/test/test:integration/build全部exit0；日志随raw归档 |
| 收尾 | raw在本地和29双份SHA256校验；13保护文件hash不变，服务inactive/dead/enabled，GPU1MiB、无计算进程，18089关闭 |

新交付为13个GU探针工具、1个测试模块和P5报告。保留初期assets/编译/ISA导出/依赖git查询失败；不把CPU结果当4090整机验证，不覆盖P3正式失败和质量非劣未建立。未运行新的全量lab selftest。既有 `lab/statistics.py:205` EOF空行保持原样。

## 2026-10-28 v0.2.7 隔离基线（P6）

结果见 [P6-V027-BASELINE](reports/P6-V027-BASELINE-20261028.md)。本轮只建立保守v0.2.7候选并复测P3原失败；前置正确性FAIL，未进入DEQUANT_SIDE实验。

| 检查 | 实际结果 |
|---|---|
| v0.2.7原生目标strata构建 | CUDA12.3/gcc12.2/sm89/CMake4.4.3成功；初次CMake3.25 CUDA20配置失败保留，未升级系统工具 |
| 新树Python `serve.test_prompt_encoder serve.test_frontend serve.test_server` | 29实测402项通过，原#1536/PT逻辑及测试保留；原生源码未改 |
| 实际PT与回复复用 | 5请求通过；PT默认/false/true usage78/78/211，前轮prompt+gen171、追问reuse170 |
| P3实际历史恢复与原答案 | 8阶段完成；两档真实恢复69625/102385 token通过；6个原长检索均错答，2个side正确 |
| 原布尔工具与seed43编码末轮 | 本轮各1请求通过；编码Docker八要求8/8，不代表新八轮任务或正式质量非劣 |
| `tests.test_v027_baseline` | 本机及29各5项通过；初次KVRES继承校验错误发生于模型加载前，已修正并补测试，失败日志保留 |
| 根仓库五项检查 | 本轮pnpm typecheck/lint/test/test:integration/build全部exit0，日志在本轮raw/local-verification |
| 原始证据本地复核 | 15份SSE重解析一致，10原body hash、9exact/tool重评分、15usage/预算一致；最大usage计数差8≤32，13生产保护hash及旧P3输入不变 |
| 资源与收尾 | 302遥测样本，无abort；峰值75°C/23724MiB、MemAvailable最低7715MiB；13保护hash不变，inactive/dead/enabled；GPU1MiB、18089释放，实验PID退出、1份key移除 |
| DEQUANT_SIDE / 新八轮链 / 正式性能与质量非劣 | NOT_RUN_CORRECTNESS_GATE；没有开启DEQUANT_SIDE，没有新采用结论 |

交付2个v027工具、1个测试模块、P6报告，更新入口与MANIFEST。182个raw文件双端逐一SHA256校验通过，实验包MANIFEST为203文件；私有3574文件GGML源码副本留29，本地只归档其hash清单。未运行全量native parity或lab selftest。既有 `lab/statistics.py:205` EOF空行保持原样。生产未改，未提交、推送或部署。

## 2026-10-28 长检索失败根因诊断（P7）

结果见 [P7-LONG-RETRIEVAL-ROOTCAUSE](reports/P7-LONG-RETRIEVAL-ROOTCAUSE-20261028.md)。原六项仍FAIL，诊断控制不替代原验收。

| 检查 | 实际结果 |
|---|---|
| 原请求/gold/SSE/渲染核对 | 六gold唯一绑定输入行，prompt逐字tokenizer往返正确，连字符12不在EOS248044/248046中 |
| raw trace，13请求 | 原六项同错，实际原生EOS；短literal/短表/完整格式/两档low thinking控制通过 |
| 去MTP/lookup，9请求 | 实际缓存与开启组同为8053槽，offered总和0；原六项逐字同错；literal通过 |
| 冷格式/暖原措辞，5请求 | 明确格式两档reused0、完整gold通过；原措辞reused65536/98304仍原错值 |
| 定向工具测试 | 本机/29各3项通过；最终29日志unit-tests-final-29.log |
| 本地证据复核 | 27份SSE、raw token数/usage/预算一致，18原body/完整gold、9修改控制的完整gold复评分一致；P6原182文件及旧P3输入不变 |
| 根仓库 | 本轮pnpm typecheck/lint/test/test:integration/build全部exit0，保留既有Phaser chunk提示 |
| 资源/收尾 | 三完成阶段361样本，无abort，峰值75°C/19976MiB，MemAvailable最低6192MiB；13保护hash不变，4份key移除，8个实验PID退出，GPU1MiB/43°C、18089可绑定，inactive/dead/enabled |
| 未运行 | 独立参考引擎/全精度logits对照、全量native parity/lab selftest、DEQUANT_SIDE、正式性能/任务质量非劣；P6服务402项按不变源hash复用 |

新增1个诊断工具、1个测试模块和P7报告。373个raw证据文件双端SHA256一致，包MANIFEST共206文件。首次容量误解及通用PR护栏拒绝都发生于请求前并保留；随后按源码修正诊断公共预算、使用单独no-MTP输入配置，未削弱共享护栏。没有修改引擎、生产、原评分或既有失败；未提交、推送或部署。

## 2026-10-28 同token/同GGUF独立logits（P8）

结果见 [P8-INDEPENDENT-LOGITS](reports/P8-INDEPENDENT-LOGITS-20261028.md)。原六项保持FAIL，未改变评分或P6前置门。

| 检查 | 实际结果 |
|---|---|
| 同输入/同源权重 | 原body hash及完整token int32 SHA/FNV一致；同一两GGUF分片，当前size/mtime匹配P6完整hash身份；144专家偏移/类型一致，pack conversions为空 |
| 独立实现 | llama.cpp 87b37ea的qwen4exp图、直接ID、FP16 KV、无MTP/MoE cache；已有库87b37ea-dirty，非本轮干净重建；实际加载5库hash及2个GGUF映射核实 |
| 短资格 | 63token输入，8/8 argmax一致；七位数字后连字符高于EOS参考9.9542/Strata9.8476 |
| 完整两个prime | 69616/102392输入，每边各8行完整248320-way FP32 logits；16/16 argmax一致，错位数字和EOS均独立复现 |
| 关键排序 | 参考错误首位高于正确首位1.3020/1.9740；数字后EOS高于连字符6.1524/3.6235；非逐bit logits等价 |
| 定向测试/构建 | 新C++参考客户端编译exit0；tests.test_reference_logits本机/29各5项通过；首次分析控制末位EOS假设被拒绝，修正为连字符并补回归，不重跑模型 |
| 根仓库 | 本轮pnpm typecheck/lint/test/test:integration/build全部exit0，日志保留；既有Phaser chunk提示 |
| 资源/保护 | 四阶段1161样本，无abort，峰值72°C/23640MiB，最低MemAvailable10443MiB；4PID退出，GPU1MiB/50°C、18089可绑定，inactive/dead/enabled，13保护hash不变 |
| 历史保护/归档 | P6原182文件、P7原373文件及P3输入不变；本轮raw双端SHA256校验，包MANIFEST为211文件 |
| 未运行/限制 | 无未量化/更高精度权重、KV与分块完全对齐或逐层parity；未重跑P6服务402项/全量lab selftest；DEQUANT_SIDE与正式性能/任务质量非劣仍未运行 |

新增3个工具、1个测试模块、1份报告及入口更新；不改Strata实现、生产或既有评分，不提交、推送或部署。

## 2026-10-28 已有IQ3_S同发布revision对照（P9）

结果见 [P9-HIGHER-PRECISION-LOGITS](reports/P9-HIGHER-PRECISION-LOGITS-20261028.md)。原六项FAIL及评分不变。

| 检查 | 实际结果 |
|---|---|
| 权重库存/身份 | 可读模型位置90个文件路径，仅4个Flash-Next/GSQ-RCO家族分片；缓存发布revision ed59f920同时列两量化LFS，4份148.507GiB全内容hash全部匹配 |
| 结构/精度范围 | 1224张量名/形状、tokenizer/qwen4exp/imatrix元数据相同；276量化分配变化，230增大/46减小；共同PLE仍IQ4_NL，非BF16基模对照 |
| 保持项 | 复用P8冻结客户端/库/图、NGL18、F16 KV、batch512、threads16、原完整token与原错位数字前缀；只换参考GGUF |
| 短资格 | 63token，8个argmax为6763216-；连字符高于EOS 11.1835 logit，进入long前通过 |
| 两个完整prime | 69616/102392输入，各8行完整248320-way FP32 logits；16/16 argmax与XXS一致，仍1751936/6395887＋EOS，无条件轨迹分叉 |
| 首位/末尾排序 | IQ3_S错误首位高于正确首位2.3680/0.7253；EOS高于连字符2.9290/2.6111，均未反转 |
| 工具验证/审查 | 复用P8 helper测试本机/29各5项通过；29最终保留stdout+stderr日志；P9脚本AST可解析；独立静态review无实质finding，reviewer未运行SSH/模型/测试 |
| 根仓库 | 本轮pnpm typecheck/lint/test/test:integration/build均exit0，保留原Phaser chunk提示 |
| 资源/收尾 | 1286样本，无abort，峰值64°C/23588MiB，最低MemAvailable54147MiB；2个C++ PID退出，GPU1MiB/47°C，18089可绑定，生产inactive/dead/enabled，13保护hash不变 |
| 原证据/归档 | P6原182、P7原373、P8原140个raw文件及P3冻结输入不变；本轮raw双端SHA256校验；包MANIFEST共212文件 |
| 缺口/未运行 | 未找到本地同谱系全16-bit权重、未独立核实基础checkpoint commit；未做逐层parity、P6服务402项/全量lab selftest、DEQUANT_SIDE或采用验证 |

只新增P9报告并更新入口/本记录，实验专用3个源码及raw在workspace内留存。没有下载权重、修改Strata实现或生产、提交、推送或部署。

## 2026-10-28 DEQUANT_SIDE关闭状态核查（P10）

结果见 [P10-DEQUANT-SIDE-QUALIFICATION](reports/P10-DEQUANT-SIDE-QUALIFICATION-20261028.md)。NO_BENEFIT_SCREEN仅指本次三个场景的候选成本筛查，原六项仍FAIL，未开启SIDE=1。

| 检查 | 实际结果 |
|---|---|
| 固定输入与状态 | 原32K准备/3K续接/100K冷读各profile一次＋无nsys一次；六body/gold/上限不变；实测32771冷读、32764复用＋3229新读、102392冷读，生成2/5/8一致 |
| 质量与真实性 | ACK、1730两组均PASS；100K两组均6395887、原gold仍FAIL；缺真实compaction fixture，32K明确为合成重读形态替代 |
| 原生/配置 | P6原生58ffaf7f及六文件port未改，完整配置/保守开关保持；实际SID=0；无新kernel、工具链升级或root计数器 |
| CUDA trace | 两SQLite均OBSERVED，NVTX request/first、真实engine PID、runtime correlation完整匹配候选；实际schema保留，未声称零drop或精确关键路径 |
| 路径覆盖 | 每dense-prefill chunk静态245H16＋55IQ候选，实际600/300/2100核；逐类型/grid闭合，H16无4096整片旁路，IQ保留超集限定 |
| 条件空间 | 候选并集106.193/53.310/371.434ms；在本次profiled TTFT中为1.222%/1.729%/1.359%，保持非目标工作不变的乐观模型仍不足4%门参考 |
| 扰动控制 | 无nsys TTFT8.3628/3.0209/26.8112s；profile10264槽、control10272槽。单次观测不因果量化profiler开销、不当开关收益 |
| 定向工具测试 | 本机/29各10项通过；独立静态review无影响筛查决定的实质finding，reviewer未运行模型/单测 |
| 根仓库 | 本轮pnpm typecheck/lint/test/test:integration/build全部exit0，保留Phaser chunk提示 |
| 资源/保护 | 209样本，无abort，峰值70°C/23672MiB、MemAvailable最低9479MiB；12个driver/server/engine PID退出，GPU1MiB/43°C、18089可绑定，13保护hash不变，4份key脱敏，生产inactive/dead/enabled |
| 历史/归档 | P6原182、P7原373、P8原140、P9原71个raw及P3输入不变；本轮raw双端SHA256验证，包MANIFEST217文件 |
| 未运行 | SIDE=1命中/parity/额外显存与槽位代价/配对性能，真实compaction链，P6服务402项/全量native parity/lab selftest/采用验证 |

新增2工具、2测试模块、1报告，更新入口/本记录；没有修改Strata或生产、提交、推送或部署。

## 2026-10-28 Ada MMVQ差量资格检查（P11）

结果见 [P11-ADA-DELTA-QUALIFICATION](reports/P11-ADA-DELTA-QUALIFICATION-20261028.md)。仅关闭态条件成本筛查NO_BENEFIT_SCREEN，未开启IL89；原六FAIL和P6正确性门保持。

| 检查 | 实际结果 |
|---|---|
| 冻结请求 | think-4096/think-102400原body不变；profile/control各一次，共4请求，均2048输出、冷读4095/102400 |
| 差量 | 344个实际shape×T单元中17个改变；9复用旧候选，8不同且全部退回plain；Q3_K无权重覆盖 |
| 运行覆盖 | 两trace OBSERVED；8新差量命中，base rows mismatch0、剩余unknown MMVQ0；逐kernel保留类型/T排除依据 |
| 条件成本 | 新差量+全部quant/interleave超集：完整请求2.764%/2.003%；首末输出3.084%/3.240%，非未插桩严格界 |
| 扰动控制 | profile/control生成轨迹不同；槽数10264/10272；未因果量化profiler开销，未据此声称候选收益 |
| 定向测试 | 本机及29最终各16项通过；独立只读评审和short SQLite重算无material finding，reviewer未执行模型/测试 |
| 根仓库 | pnpm typecheck/lint/test/test:integration/build全部exit0 |
| 资源及保护 | 257样本无abort，峰值71°C/23784MiB、MemAvailable最低7361MiB；12拥有PID退出，GPU1MiB/43°C、18089释放，13保护hash不变；4份key脱敏，生产inactive/dead/enabled |
| 历史证据 | P6至P10共922个raw hash不变；本轮raw归档双端校验；包MANIFEST224文件 |
| 未运行 | IL89=1、单shape候选/parity、固定token logits、配对性能及质量采用验证、其他优化 |

新增3工具、3测试模块、1报告；更新入口和本记录。未改Strata或生产，未提交、推送或部署。


## 2026-10-28 AVX2 gather 单格式探针（P12）

结果见 [P12-GU-GATHER-PROBE](reports/P12-GU-GATHER-PROBE-20261028.md)。REGRESSION，扩展门NOT_MET；拒绝当前候选，不扩格式或整机验证，原六FAIL保持。

| 检查 | 实际结果 |
|---|---|
| 当前覆盖 | 冻结4K/100K原请求均2048输出；IQ3_S占nt1 GU worker时间36.246%，实际oracle与链接符号匹配 |
| 输入身份 | P5的1008个fixture hash及冻结index一致；379.10MiB，115原批次、317 jobs、509 entries |
| 数值/命中 | red stub被捕获；100000 lookup、1310720 dot、1024阶段逐bit相同；115池批次/509输出相同，4191实际候选row调用；4回退通过 |
| ISA | 新TU仅AVX2/FMA/F16C、无EVEX/VNNI；caps实际限制成立，旧门不变；archive两项P6已有告警原样保留，无新增 |
| 完整链 | 六对30s预热/60s测量，耗时+33.038%，95% CI[31.401%,34.607%]；12臂输出hash一致，开/关实际命中正确 |
| 单核 | 三对仅诊断，耗时+77.960%，不参与扩展门 |
| 频率/内存 | 每臂56个有效MSR区间；开启A/M约+1.68%；55个窗内进程样本、minor6/major0、VmSwap0；无IMC/LLC流量因果结论 |
| 验证 | 本机17项定向测试，根仓库5项pnpm检查均exit0；独立评审从raw复算统计/频率/内存一致，未重跑模型 |
| 资源/保护 | 18 CPU臂1158样本；两次加载引擎覆盖尝试123样本、最高73°C；13保护hash及P6源码不变，1076旧raw hash不变；40拥有PID退出，GPU1MiB/43°C、18089释放，生产inactive/dead/enabled |
| 归档 | 372文件/30499137bytes双端SHA一致；保留两次前置失败及原始输出；实验包MANIFEST237文件 |
| 未运行 | 候选开启的整机请求、原六项质量复测、关闭GDS或更换编译目标等第二探针 |

新增9工具、3测试模块、1报告；更新入口和本记录。未提交、推送、改生产或部署。


## 2026-10-28 HC-only scratch资格验证（P13）

结论BLOCKED_NUMERICAL_ORACLE，非NO_BENEFIT。见 [P13报告](reports/P13-HC-SCRATCH-QUALIFICATION-20261028.md)。

| 检查 | 实际结果 |
|---|---|
| 预登记 | 主指标/顺序/门槛在首GPU资格前冻结；统计定义补充在首A/A之后、正式样本之前 |
| 隔离实现 | HC四buffer复用，A/B/C开关；CUDA12.3/sm89构建通过；未改kernel/GROUP/stream顺序 |
| 容量 | 16K启动借槽4388→3787，少601槽；实际cap减少1038003200bytes，shared region不变；B/C零请求 |
| 原版A/A | 4095与16384输入两对，各248320个logits均有bit差；输入16K实际prefill88+16295 |
| 首差异 | 原布局layer3/half1的R输入及mixed/inj/lo16原始bytes相同；FFN后3340590个float不同，CPU分派49vs53 |
| 工具/仓库 | 8项定向单测及P13 AST通过；根仓库5项pnpm检查全部exit0 |
| 未运行 | 候选数值/状态/生命周期/sanitizer、完整成本链、有效频率、正式配对性能与质量采用 |

原六FAIL保留。生产和旧P6-P12证据保护、双端归档及实验资源释放以本轮FINAL_PROTECTION/RAW_MANIFEST/ARCHIVE_RECEIPT为准。没有提交、推送或部署。

## 2026-10-29 数值回放oracle（P14/P15）

结论为冻结GEN1的固定分派A/A通过；用户要求完成oracle后停止，B/C及其他候选均未续测。见 [P14/P15报告](reports/P14-P15-NUMERICAL-REPLAY-ORACLE-20261029.md)。

| 检查 | 实际结果 |
|---|---|
| 局部FFN | 86字段、1,139,717,436 bytes逐字节相同；输入、分派、行映射三个负控制均按指定原因拒绝 |
| 完整请求A/A | 两个fresh engine；4090实际块、48层FFN；3329 raw字段、1,121,573,360 bytes全部相同 |
| logits与状态 | 248,320个有限FP32 logits零bit差；298,656,148 bytes有效终态相同，MTP实际有效范围[0,4090) |
| 失败保留 | aa-1旧runner目录冲突、aa-2监控器退出竞态保留；修复后aa-3通过；原六FAIL和P13旧raw不变 |
| 定向测试 | `python3 -B -m unittest discover -s docs/strata_4090_128k_lab/tests -p 'test_oracle*.py'` 44项PASS；`test_reference_guard.py` 4项PASS |
| 仓库要求 | `pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm test:integration`、`pnpm build`全部exit0；保留既有Phaser大chunk警告 |
| 归档 | 原始bytes、SAVE、二进制保留29；本地166个元数据/日志/源码文件逐项长度与SHA256匹配远端清单 |
| 资源/生产 | 原13个保护文件hash不变；187个P13 raw hash不变；8个本轮PID已退出；GPU 1MiB、无计算进程；18089空闲；生产inactive/dead |

共8次native请求，正式性能样本0，B/C请求0。自动续测PAUSED；没有提交、推送或部署。未运行真实4096/16K边界、生命周期/redzone/sanitizer、性能及GROUP_SCRATCH/IMMA。既有`lab/statistics.py:205` EOF空行保持原样。验证命令明细见`workspace/continuation-20261029/validation/RESULTS.json`。

## 2026-10-29 HC-only B/C最小验证（P16）

| 检查 | 实际结果 |
|---|---|
| `python -B tools/oracle_replay/full_request.py run --name replay-b` | FAIL；GEN1、SAVE及原生exit0完成，退出监控读取`/proc/2266238/exe`失败 |
| `python -B tools/oracle_replay/full_request.py analyze --name replay-b` | FAIL；`CAPTURE_NOT_VALID: replay-b`，AB门不放行 |
| 已产生文件离线对账 | `NUMERIC_BYTES_EQUAL_BUT_RUN_FAIL`；3329字段/1,121,573,360bytes相同，248320个有限logits零bit差，298,656,148bytes有效状态相同；没有改运行FAIL |
| 请求预算 | B=1、C=0、重试=0；C未启动，首失败停止 |
| 历史/生产保护 | 原oracle7459文件、P13原187raw、生产13保护文件hash不变；源码、引擎及工具未改 |
| 归档 | 新增3356文件/1,424,432,029bytes登记SHA256；本地26份导出文件双端匹配；大raw/SAVE保留29 |
| 收尾 | PID2266238退出、GPU1MiB且无计算进程、18089空闲；生产inactive/dead/enabled；自动续测PAUSED |

边界、生命周期、sanitizer、成本链及性能均未运行，正式性能样本0。复用上轮44+4定向测试及五项pnpm检查，本轮未重复运行。实验包MANIFEST纳入P16报告；本次文档与新增脚本空白检查、包完整性校验通过。未提交、推送或部署。详见 [P16报告](reports/P16-HC-SCRATCH-BC-MINIMAL-20261029.md)。

## 2026-10-29 退出护栏修复与限额重跑（P17）

| 检查 | 实际结果 |
|---|---|
| 修复前最小回归 | 6项中残留自有PID用例FAIL，其余5项PASS；红灯日志保留 |
| 修复后最小回归 | 本地和29同一组6项PASS；外来PID及运行中归属失败继续拒绝 |
| B运行与AB门 | CAPTURE_VALID/PASS；3329字段/1,121,573,360bytes、248320个有限logits、298,656,148bytes有效状态均与A相同 |
| C运行与AC门 | FAIL/FAIL；引擎完成GEN1、SAVE、exit0，退出监控仍报`/proc/2267846/exe`缺失；修复不完整 |
| C离线文件检查 | 不改验收FAIL；248319个logits值bit不同，max abs 0.734858512878418；有效状态首登记差异live.gdn；43层CPU分派变化，尚未归因 |
| 本轮预算 | B=1、C=1、共2个新GEN1；无额外重试或后续阶段 |
| 仓库要求 | pnpm typecheck/lint/test/test:integration/build均exit0，保留既有Phaser chunk警告 |
| 保护/归档 | 原oracle7459、P16原3356、P13原187文件hash不变；生产13保护hash不变；本轮6920文件/2,847,603,113bytes清单；56份本地导出文件双端匹配 |
| 最终资源 | 两个自有PID退出，GPU1MiB/45°C无计算进程；18089释放；生产inactive/dead/enabled，自动续测PAUSED |

新增回归通过没有覆盖本次C剩余退出窗口，不能宣称护栏彻底修复。边界、生命周期、sanitizer、成本链和性能未运行，正式性能样本0，原六FAIL保留。见 [P17报告](reports/P17-HC-GUARD-FIX-BC-20261029.md)。

## 2026-10-29 C退出修复与同路径数值验证（P18）

| 检查 | 实测结果 |
|---|---|
| 退出顺序回归 | 旧run_native在QUIT前未停止监控的实际用例FAIL；修复后10项护栏测试在本地/29均PASS |
| 对照验收回归 | 6项在本地/29均PASS，独立分配未执行或同路径分派不一致必须拒绝 |
| 隔离编译 | CUDA12.3/sm89，161个构建步骤完成、exit0；源码/补丁/新二进制SHA256归档 |
| C运行与独立HC对照 | 各1个GEN1，两次CAPTURE_VALID、exit0、monitor_stopped_before_quit=true；两个abort_reason均null |
| 严格同路径门 | CC_CONTROL_ANALYSIS=PASS；3325字段/1,121,572,804bytes原始记录、248320个有限logits、298,656,148bytes有效状态均零bit差 |
| 自然A/C | NATURAL_C_NUMERICAL_DIFFERENCE保留；42层CPU集合变化、所有logits值bit不同；不把该结果改写为PASS |
| 归档 | 6740原件/2,979,436,197bytes清单；87份本地小文件双端长度及SHA256匹配；大raw/SAVE/二进制留29 |
| 历史/生产保护 | 未覆盖旧运行，旧清单/原引擎代码身份一致；旧raw内容hash复用前轮证据。生产13保护hash不变，服务inactive/dead/enabled |
| 资源与仓库检查 | 两PID退出，GPU1MiB/44°C无计算进程、18089释放，自动续测PAUSED；pnpm typecheck/lint/test/test:integration/build均exit0 |

本轮没有重跑A/B，新增两个C相关GEN1，正式性能样本0。通过的是冻结4090实际块中HC地址复用的同执行路径数值验证，不覆盖全局自然确定性、真实4096/16K边界、生命周期、sanitizer、成本或任务质量采用。原六FAIL和旧监控失败保留。见 [P18报告](reports/P18-HC-C-COMPLETION-20261029.md)。

## 2026-10-29 HC真实4096/16384块（P19）

| 检查 | 实测结果 |
|---|---|
| 定向工具测试 | 本地/29各6项PASS；缺记录、错误实际几何和前序FAIL必须拒绝 |
| 构建 | 新隔离CUDA12.3/sm89引擎161步完成，exit0 |
| 真实4096配对 | 两请求均CAPTURE_VALID；3887条/1,123,191,816bytes raw、248320个有限logits、298,726,276bytes有效状态均零bit差 |
| 真实16384自然C | CAPTURE_VALID，实际单块、48 FFN、4019条raw、MTP[0,16384)、完整DONE/SAVE；不等于匹配数值门PASS |
| 16K匹配对照 | FAIL保留，需1,038,091,264bytes、仅余539,492,352bytes，主chunk前拒绝；0-byte预建logits，无SAVE；PAIR-16384 FAIL/数值NOT_PROVEN |
| 覆盖边界 | 两种真实块均48层streamed、0层fused；fused分支未取得GPU覆盖；无生命周期/sanitizer/成本/性能样本 |
| 归档及资源 | 11897原件/7,597,298,137bytes完整SHA清单；81导出文件＋2清单根文件双端核对；4 PID退出，GPU1MiB/43°C、18089释放 |
| 生产及历史 | 13保护hash不变、服务inactive/dead/enabled；旧清单/源码/引擎身份一致，旧raw内容hash复用；原六FAIL保留 |
| 仓库检查 | pnpm typecheck/lint/test/test:integration/build均exit0，保留Phaser chunk警告 |

本轮4次GEN1尝试、3次完成、零重试；首失败停止。资源阻塞不证明16K有数值差异，也不建立16K等价性或性能收益。首次归档脚本的空文件判断错误保留并修正，无GPU重跑。见 [P19报告](reports/P19-HC-REAL-BOUNDARIES-20261029.md)。

## 2026-10-29 16K独立HC与生命周期（P20/P21）

| 检查 | 实测结果 |
|---|---|
| P20匹配数值门 | PASS；一次GEN1，4019raw/4,136,034,468bytes、248320个有限logits、486,388,612bytes有效状态逐字节相同 |
| 原cache/实际分派 | 数值对照四Managed指针，原cache/region Device、10272槽；原host_res/路由/行映射/分组全量相同；原args/reserve974不改 |
| P21生命周期 | 8请求PASS；实际4096→16384→4096；4101-token SAVE/RESTORE有效状态298,726,276bytes相同；真实STOP取消及同进程续接成立 |
| Memcheck | 加载cuBLAS时cuLibraryLoadData CUDA_ERROR_OUT_OF_MEMORY；9984slots而非原10272，未READY/GEN0，FAIL保留；不是内存访问验收PASS |
| 退出及错误 | 正常两phase护栏无错；失败memcheck另有/proc子进程消失错误，日志保留；本轮全部PID最终退出 |
| 源码/工具验证 | 两次C++ overlay构建exit0；本地/29各5+9项定向测试PASS，独立审查后修复取消误PASS；原P19源码/引擎/链接输入不变 |
| 仓库检查 | pnpm typecheck/lint/test/test:integration/build均exit0，保留Phaser chunk警告 |
| 归档/保护 | 4132原件/5,236,606,478bytes完整SHA；106导出小文件及4清单根文件双端核对；13保护hash不变、inactive/dead/enabled；GPU1MiB/43°C、18089释放 |

本轮9个GEN请求：7个GEN1完成、2个预期取消；memcheck另一次启动失败，GEN0。未缩缓存或修改reserve重试，成本/正式性能/质量采用均NOT_RUN；正式性能样本0，原六FAIL及旧对照FAIL保留。恢复只覆盖4101-token状态，不能扩大为64K/100K恢复。见 [P20/P21报告](reports/P20-P21-HC-16K-LIFECYCLE-20261029.md)。


## 2026-10-29 P22至P24 HC分阶段验证

| 阶段/检查 | 实际结果 |
|---|---|
| P22原10272槽完整memcheck | PASS；首次LAZY verify watchdog失败保留，已有async helper纠正请求DONE、tool exit0/0 errors；数值与生命周期证据复用 |
| P23唯一100K A/C机制对 | 2引擎/2请求PASS；601个保留专家实际命中，专家prefill加回填减少8187264000bytes；诊断计时不进入正式统计 |
| P23本地及29定向CPU测试 | `python -B -m unittest discover -s tests -p 'test_hc_cost*.py' -v`：11项PASS |
| P24本地及29定向CPU测试 | `python -B -m unittest discover -s tests -p test_hc_perf.py -v`：5项PASS |
| P24正式阶段 | 20引擎/24请求全部验收PASS；6对100K、两对4K、两对prime→append，零替补/零重试 |
| P24统计门 | PERFORMANCE_GATE_NOT_MET；TTFT +0.824%，95% CI[-0.035%,1.804%]；wall C/A上界1.017491通过非劣，decode上界1.068783失败 |
| 独立验收 | 429份/49725277bytes原件逐文件SHA及长度一致；全统计重算一致，24条原始请求/响应/评分/SSE、20个native PID及资源记录通过 |
| 本轮此前仓库检查 | `pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm test:integration`、`pnpm build`均exit0，日志在`/private/tmp/strata-p22-repo-checks-20261029/RESULT.json`；后续仅Python/文档，未重复运行 |
| diff/语法 | 本次7份Python新源码AST解析通过、本次入口文件diff检查通过；全包diff仍有既有`lab/statistics.py:205`末尾空行，本次未改 |
| 收口 | 生产13项保护SHA不变，服务inactive/dead、GPU1MiB、18089释放；20个引擎运行均存在major fault和系统swap活动，不能宣称零swap或唯一归因HC |

报告：[P22](reports/P22-HC-MEMCHECK-20261029.md)、[P23](reports/P23-HC-RETAINED-EXPERT-COST-20261029.md)、[P24](reports/P24-HC-PAIRED-PERFORMANCE-20261029.md)。原六FAIL、单独任务质量门和未运行的其他候选状态不因本阶段完成而改判。

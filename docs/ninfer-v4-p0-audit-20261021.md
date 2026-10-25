# V4 P0：B29 / BO / P6 身份与证据审计

日期：2026-10-21，用户时间 Asia/Shanghai。状态：**AUDIT_COMPLETE_WITH_DISCLOSED_GAPS**。本次完成已授权的只读审计；**P0-GATE 未通过，P1 尚未开始**。根 V4 中的 PENDING 是冻结计划状态，本报告和执行账本记录本轮观察，不回写历史 Baseline 或原始资格结果。

当前 B29 的镜像、服务/CLI、模型、启动脚本、代理和 argv 与既有 Baseline 身份相符；BO 尚未取得可复现构建资格，未发现可认证的 P6 集成制品。P6 不能由当前 B29、固定 O/U 源码或镜像标签推导。

[修订版计划入口](ninfer-flare-v4-md-20261021/AI_EXECUTION_PROMPT.md) · [本轮证据入口](../output/ninfer-v4-p0-audit-20261021/README.md) · [机器执行账本](../output/ninfer-v4-p0-audit-20261021/execution-status.json)

## 1. 运行、源码、构建的身份

| 对象 | 本次观察 | 资格边界 |
|---|---|---|
| B29 运行镜像 | `sha256:e753e2283db78bbe2fe1fc92b9d45300a27fd5765b367c434c9023cbf2cb1cb3`，RepoDigests=[] | 本机 image ID 已确认；没有 registry digest 或本轮验证过的可移植镜像归档 |
| B29 服务二进制 | `447e37e36deed07e3359609ca41ad248ddf490c4b628c9fd487e0572be3f3c98` | 与原实测镜像内二进制相符；尚无完整源码到二进制的可复现构建链 |
| B29 CLI | `b7c7c5051fb9f1b7d99c565c481b5accfdba2e71f5b0f189785920cf92240468` | 仅身份核验，不因此取得新算法资格 |
| 生产模型 | 18,210,531,328 bytes；SHA `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e` | 本轮重新读取文件计算 SHA；只读挂载 |
| 生产参数 | C1；context / shared KV 262144；rk4v4-e8；MTP3；T=1/top_p=.95/top_k=20；presence=0；preserve-thinking；max_tokens=32768；代理 medium | argv 与历史相同，代理文件 SHA 相同；没有发新推理请求来验证行为 |
| 远端源码目录 | `/home/hhtele/ninfer-4090` 无 `.git`；PINNED_COMMIT 写 B=`44a2c6c…` | 标签不认证目录或镜像，选定源码范围与 O 存在差异 |
| O 源码 | `e0b05f7cb46adae2787be2ccbe605e1b0c9b3923` | 原本地工作区 clean，HEAD、index SHA、未跟踪状态保持不变 |
| BO | 尚无本轮可定位、来源闭合并通过资格的 O 对照构建 | 历史 `44a2c6c` / `prepare-detail` 镜像不能改名认作 BO |
| P6 | 没有合格集成 commit/build/runtime 证据 | 固定 U=`5b99996…` 是 donor 来源，不是已集成 P6 |

生产 image/参数/cache 三件套已记录在 [prod-profile](../output/ninfer-v4-p0-audit-20261021/prod-profile.json) 和 [rollback-manifest](../output/ninfer-v4-p0-audit-20261021/rollback-manifest.json)。实际发布和回滚均未执行。审计前后容器 ID、PID、StartedAt 相同；服务没有被本轮重启。`/metrics` 观察时 processing=0、deferred=0，只代表该时点。

## 2. P0-T01 完整源码审计

已按冻结 B/O/U 核对共同祖先与提交数：O 独有 **11**，U 独有 **34**。完整 diff 的路径数为 B→O **43**、B→U **324**、O→U **351**；43 项与原 API 保留账本的路径和增删计数逐项相同。另实际运行四个PinMismatch负例：无效SHA、错误共同祖先、O计数12、U计数35，均在产生输出目录前以exit2拒绝。

16 个双方共同修改路径已按 C01—C16 对齐。在本地临时 clone 执行真实 `ort --no-commit` 合并，得到 **9 个冲突文件、27 条未合并 index stage**，stage 1/2/3 blob 分别与固定 B/O/U 一致：

- `include/ninfer/types.h`
- `src/serve/http_server.cpp`
- `src/serve/request_log.cpp`、`request_log.h`
- `src/targets/qwen3_8/impl/frontend/frontend.cpp`
- 同目录 `processor.cpp`、`processor.h`、`tokenizer.cpp`、`tokenizer.h`

其余 7 个共同修改路径自动合并；这不授予语义、编译或保留测试资格。没有解决这些冲突，也没有把临时合并结果作为候选产品代码。

[完整审计及三组 patch](../output/ninfer-v4-p0-audit-20261021/source-audit-local-pins-v3/audit.json) · [43 项保留账本](../output/ninfer-v4-p0-audit-20261021/retention-ledger.csv) · [index 核验](../output/ninfer-v4-p0-audit-20261021/conflict-index-verification.json)

第一次探测揭示原仓库是 shallow / promisor checkout：U 的 commit 对象可见但对象闭包不完整，普通临时 clone 无法合并。原失败保留；在独立临时目录从固定上游 SHA 补齐对象后完成探测。没有对原工作区执行显式 fetch、添加 ref、改 index 或 reset。初次复用旧工具读取 promisor 对象时未禁用 Git lazy fetch，且没有对象库前态；因此仅证明 HEAD/index/工作树状态不变，不声称原 `.git/objects` 字节或访问缓存完全不变。固定对象已封存在 [pinned-source.bundle](../output/ninfer-v4-p0-audit-20261021/pinned-source.bundle)，`git bundle verify` 确认完整历史，避免依赖即将消失的 `/tmp`。

## 3. 远端目录与 O 的差异

当前选取 src/include/apps/tests/cmake/scripts/tools 的源码类型及顶层构建文件，共 856 份。对 O：**847 相同、9 不同、12 个 O 选定文件在远端缺失**；不声称这是整棵目录的完整构建输入认证。

9 处不同为四份前端 `processor.cpp/.h`、`tokenizer.cpp/.h`，`tests/CMakeLists.txt`，以及四份 linear_swiglu 测试。缺少的 12 份主要为 G1 driver、legacy oracle、边界 benchmark 及相关前端测试/reference。

这次范围包含更多测试文件；不能把相较旧 603 文件报告增加的差异解释为刚发生的源码变更。与旧哈希清单的连续性核验单列在 [historical-source-continuity](../output/ninfer-v4-p0-audit-20261021/historical-source-continuity.json)。[B/O/U 分范围比较](../output/ninfer-v4-p0-audit-20261021/source-tree-comparison.json)保留全部路径。

远端未找到 CMakeCache / compile_commands / 合格 BO 或 P6 的构建回执；image labels 没有认证 source commit。历史上线记录说明 schema20 overlay 曾在提交前进入镜像，且 BUILD_TESTING=OFF。当前身份核验与该记录一致，仍不能把 clean O 重建结果提前认作 B29 等价物。

## 4. P0-T02：环境、资源和回滚证据

GPU UUID `GPU-381cb85f-8ebf-b33e-5076-9305e6af4be5`，RTX 4090，驱动 610.57.04；总显存 24564 MiB，快照已用 22598 MiB。宿主 nvcc 为 12.3；生产 runtime 的 cudart 为 13.2.51-1、cuBLAS 为 13.3.0.5-1、cuDNN 为 9.20.0.48-1。runtime 内未定位 nvcc；缓存的 devel 镜像存在，但本轮没有启动或验证其构建能力。

启动日志实际包含：weights 16.67 GiB；KV resolved=262144、4096 pages；runtime 5.08 GiB；persistent arena 4.82 GiB；workspace 172.57 MiB；replay records 6.82 MiB；graph 8/86 MiB。text-KV、MTP-KV、GDN state 等是重叠账本分项，不重复相加。KV 是共享池，不能按每 lane 262144 计算容量。

[capacity-ledger](../output/ninfer-v4-p0-audit-20261021/capacity-ledger.json)保留原启动行。当前占用和启动 free-after-startup 不是 allocator 高水位；没有运行新容量、长请求、并发或回滚测试。97/Core 的 context_capacity 解释和 worst-case 容量资格仍待后续按已认证二进制开展。

## 5. P0-T03/T04：复用的材料与限制

六份本地资源全部重新计算 bytes/SHA，与历史 fingerprint 一致，聚合 SHA 为 `c8afe487da2dd305125cd7421a668bd55cadd632b13b0999956a7300d3917a51`。找到 88 行、88 个唯一 case_id 的原用例集，以及 thinking_toggle 模板；模板 SHA 与远端该 fixture 相同。材料可定位，不再笼统登记为“用例/模板找不到”。

历史 G1 real=53、synthetic=74，均含 fuzz=20000 的 summary 与 raw 输出可复用审阅。现有 diff 报告明确为 SUPPLIED_OUTPUTS_ONLY；尚不能证明它们由本次认证的 O oracle 二进制执行。缺少 oracle binary/build receipt、用例 SHA 与旧 run 的明确绑定，以及六资源与现网 `.ninfer` 内部资源的直接绑定。模板原始 bytes 与 O 的尾 newline 处理也须由实际 oracle 资格验证。

[resources-and-oracle-manifest](../output/ninfer-v4-p0-audit-20261021/resources-and-oracle-manifest.json)记录路径、SHA、历史范围与缺口。没有重跑原 G1、旧 Baseline、编程任务或 grader。

B29 的 278=250采集+28复用、8+2成绩及原始失败/中止成本继续作为历史证据；原报告/汇总/CSV 三项 SHA 核对未变。token IDs、真实 ITL、可靠 reasoning token 拆分、round wall、allocator 高水位和正式 p95 仍未取得。BO 未建立，因此缺少可用于新资格的 B29/BO 配对记录，不用旧 B29 样本代替新构建的资格。

## 6. P0 执行账本与剩余缺口

| 节点 | 本次审计结果 | 未完成的资格 |
|---|---|---|
| P0-T01 | 固定来源、完整 diff、43项账本、真实冲突/index、原工作区不变检查完成 | 实施冲突解决和统一 review 属于后续集成，不在本轮执行 |
| P0-T02 | 运行身份、参数、共享池、启动资源、可定位回滚三件套已核对 | B29 构建来源、可移植镜像归档、真实 worst-case 资源/回滚资格未齐 |
| P0-T03 | 六资源、88用例、toggle、历史 G1 raw 已定位并核验 | O oracle 二进制/构建链、实际资源绑定、新 artifact 前端资格未齐 |
| P0-T04 | 完整 B29 历史结果、不可观测指标及原缺口已承接 | BO配对、必要观测 producer、合格统计与质量证据未齐；没有新建或执行 benchmark driver |
| P0-GATE | **BLOCKED / NOT_PASSED** | T02—T04所需资格、同一构建上的 required 测试及统一独立 review 未完成 |

没有把当前只读审计标成 P0-GATE PASS，没有创建 qualified tag，没有绕过门禁进入 P1/H0/K0。

## 7. 下一步具体范围与预计耗时

建议下一个有界工作包为 **BO 可复现构建与 P0 前端证据补全**，完成后再判断 P0-GATE 是否具备条件：

1. 从本轮 bundle 的 O 建独立构建目录，冻结 source tree / Dockerfile / build context / toolchain / base image digest；解释四份生产前端源码、schema20 overlay 与 B29 的关系，不能直接用远端混合目录重建。保留 B29 二进制 oracle。
2. 只在隔离环境建立未优化的 BO、legacy oracle 和 G1 driver，产出二进制 SHA、构建命令/选项、注册测试和资源绑定回执；复用已找到的六资源、88用例、toggle及历史输出，不覆盖旧 run。测试属于新构建资格，另记新 run 身份。
3. 定向核验前端等价、模板 bytes、schema20 扩展及 E8/预算1或2边界所需的观察设计；将缺失的 token/round/allocator producer 单列，先确定最小实现范围。P6/rk4v4/schema24迁移仍在后续 P1—P6，Flare/Lookup 优化尚不进入。
4. BO 构建与前端资格就绪后，冻结小规模 B29/BO 配对方案、请求总预算和所需观测；单卡现网已占22598MiB，实机双版本对照需要独立 GPU 时段与相应操作授权。当前不切换服务或启动第二份模型。

规划估计：来源/构建链补全 **0.5–1工程日**，BO/CPU oracle 构建及定向前端资格 **0.5–1工程日**，合计 **1–2工程日**；工具链或资源绑定不能复用时约 **2–3工程日**。这些尚未实测，不包含 GPU 排期、生产窗口或 P1—P6 全量迁移。

后续有界 BO 实机诊断先规划 **2–4 GPU小时**，必须按新增 run 冻结 case 与请求上限；该额度不满足全部正式 p95/质量矩阵。若门禁要求正式统计，继续采用 V4 已登记的两种预算：限定1680+52方案24–36小时；24细cell分别每variant≥100则至少4800请求、约59.35小时纯请求耗时，外加工程题/审计。当前没有依据承诺整个 P0/P6 的固定完成时间。

## 8. 实际执行与可复核范围

本轮实际执行：`jssh 29` 的只读身份/文件SHA/包版本/日志资源行/metadata GET，固定 Git 对象获取（仅本地隔离目录）、完整源码审计与临时 ort merge、bundle校验、旧证据SHA和资源清点。主要命令、采集器源码、stdout/stderr、首次失败、receipt及完整哈希清单均在本轮证据目录。

未执行：NInfer C++/CUDA构建、推理/模型/grader请求、旧Baseline或工程题重跑、远端写文件、配置修改、服务重启、生产发布/回滚、原源码工作区变更、commit/push。整仓 CodexGame 测试不覆盖本次只读 NInfer 身份审计，因此未运行。

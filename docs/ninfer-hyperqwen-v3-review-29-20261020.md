# 29 上 Qwen3.8-27B 的 NInfer V3 方案审查与测试合同

审查日期：2026-10-20，Asia/Shanghai。对象：[GPT Pro V3 方案](ninfer-hyperqwen-v3-md-20261019/README.md)。仓库起点：`CodexGame@7e25989`，分支 `4090-report`。

后续执行更新：用户已授权按审查修订原方案并执行 B29 baseline。当前执行权威为[修订后的 baseline 合同](ninfer-hyperqwen-v3-md-20261019/plans/05-baseline-29-execution.md)，运行证据入口为[执行目录](../output/ninfer-baseline-29-20261020/README.md)。下文“原方案未改”“尚未执行”等是审查交付时的状态，不代表后续执行状态。源码核实后的容量合同为 `P>C` 拒绝，`O_eff=min(O,C−P+1)`，末 token 不再写入 KV；旧 `P+O+R` 表述仅可作明确声明的保守预算，不可替代实际拒绝/截断语义。

**结论：REQUIRES_ADAPTATION。保留方案主架构；完成真实部署复现、计量工具和采样范围适配后，再进入优化实施。当前不能据此承诺 29 主力请求提速。**

本次已通过 `jssh 29` 检查实际主机、恢复现有 27B 服务、采集部署指纹和短请求证据，审查历史结果与固定 donor 来源，并设计完整测试矩阵。没有合入上游、修改 NInfer/代理实现、构建候选镜像或运行未来优化矩阵。

## 1. 审查结论与范围

| 项目 | 判断 | 原因 |
|---|---|---|
| 单一 Target/accept/ReplaySSM 权威；Lookup 与神经 backend 分离 | 保留 | 避免第二套状态提交、停止与接受语义 |
| 先同宽 Lookup，再词表、W8、条件 W16 | 有条件保留 | 先证明完整 round 和业务 wall time 获益，不凭 acceptance 推断 |
| 27B 现网提速 | 尚未证明 | 当前默认 sampling；新路线首版主要限于 greedy |
| PROD/O/P6 基线设计 | 原方案已有，尚未完成现场资格 | 本次补齐具体主机事实，不能把 P6 的占位 SHA 当部署事实 |
| 历史速度数据 | 可定位瓶颈，不能直接作为新 A/B 的合格 baseline | 输出短、样本不足、缓存及采样不同，部分数字已作废 |
| 旧统计工具直接执行 V3 p95 门禁 | 不接受 | 已复现规则被静默忽略、恶化 100 倍仍 PASS |
| W16、DFlash2、全局 selective archive | 条件研究，默认 OFF | 资产、数值、完整长上下文资源和净收益未通过 |
| 29 运行状态 | 已恢复现有 27B | Strata 停止；没有改模型参数、服务自启动策略或部署新版本 |

本报告使用四种证据状态：**本次实测**、**历史记录**、**固定源码核验**、**待执行合同**。所有建议阈值是后续候选测量前要冻结的规则，不是已经取得的性能结果。

完整证据目录：[output/ninfer-hyperqwen-v3-review-20261020](../output/ninfer-hyperqwen-v3-review-20261020/)。原 V3 的 280 份 Markdown 保持原样，输入校验和见 [reviewed-inputs.sha256](../output/ninfer-hyperqwen-v3-review-20261020/reviewed-inputs.sha256)。

机器可读交付：[基线身份](../output/ninfer-hyperqwen-v3-review-20261020/baseline-manifest.json)、[672 单元清单](../output/ninfer-hyperqwen-v3-review-20261020/planned-core-matrix.csv)、[测试范围合同](../output/ninfer-hyperqwen-v3-review-20261020/test-plan-manifest.json)。主报告是整合后的审查权威；各专项报告保留其调查范围和当时状态，发生表述差异时以主报告和原始证据为准。

## 2. 29 的实际运行事实

### 2.1 服务切换与环境

连接使用本机 `jssh` 的实际定义：`ssh -J jump "$@"`，目标别名 `29`。主机显示 EDT；证据保留 UTC，本文用户时间统一 Asia/Shanghai。客户端采集脚本在 29 内运行，HTTP wall time 不包含 SSH 往返。

21:25 检查时，Strata 0.1.43.1 为 idle、queued=0，18343/18030 没有已建立推理连接。21:26:15 使用现有 `/home/hhtele/strata/switch-qwen.sh 27b`，21:28:06 确认两个模型接口就绪。脚本先停 Strata、等待 GPU/端口释放，再启动原 27B unit；没有修改脚本或服务文件。

| 项目 | 本次观察 |
|---|---|
| 主机 | `192.168.10.29` / `debian` / `hhtele` |
| GPU | 单 RTX 4090，24564 MiB；UUID `GPU-381cb85f-8ebf-b33e-5076-9305e6af4be5` |
| 驱动、功耗上限 | `610.57.04`，450 W；没有改功耗或锁频 |
| CPU / 内存 | Xeon Silver 4216，16 核 / 32 线程；67,064,762,368 bytes RAM，约 62.46 GiB |
| 内核 | Linux `6.1.0-17-amd64`，启动参数含 `iommu=pt` |
| 主机 CUDA compiler | `12.3.107`；不能拿它替代容器工具链 |
| 容器 CUDA runtime 包 | `cuda-cudart-13-2=13.2.51-1`，cuBLAS `13.3.0.5-1`，cuDNN `9.20.0.48-1` |
| Strata | `openclaw-qwen38-next.service`：inactive/dead、disabled |
| 27B | `openclaw-qwen38-ninfer.service`：active/running、enabled |
| 27B 空载显存快照 | 22594 MiB，剩余约 1970 MiB；这不是最坏负载 headroom 资格 |
| 模型接口 | native `127.0.0.1:18030`；兼容层 `18343`；模型均为 `openclaw/Qwen3.8-27B-WORK` |
| 对外路由 | 既有 NGINX 28343 未修改；本次未读取 Bearer 或调用公网鉴权入口 |

证据：[切换记录](../output/ninfer-hyperqwen-v3-review-20261020/switch-to-27b.txt)、[启动脚本与 unit](../output/ninfer-hyperqwen-v3-review-20261020/host-launch-before.txt)、[runtime-capture.json](../output/ninfer-hyperqwen-v3-review-20261020/runtime-capture.json)。

`/usr/local/cuda/version.json` 在 runtime 容器内不存在；本次改用 `dpkg-query` 核实包版本，原失败仍保留。没有把 `nvidia-smi` 显示的驱动能力当作编译 CUDA 版本。

### 2.2 B29：现有 27B 的不可混淆身份

| 对象 | 本次指纹 |
|---|---|
| Docker tag | `ninfer-4090:frontend-b0-b1-1dacb0f` |
| Docker image ID | `sha256:e753e2283db78bbe2fe1fc92b9d45300a27fd5765b367c434c9023cbf2cb1cb3` |
| `ninfer-serve` SHA256 | `447e37e36deed07e3359609ca41ad248ddf490c4b628c9fd487e0572be3f3c98` |
| `ninfer` CLI SHA256 | `b7c7c5051fb9f1b7d99c565c481b5accfdba2e71f5b0f189785920cf92240468` |
| 模型 | `/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer`，18,210,531,328 bytes |
| 模型 SHA256 | `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e` |
| 生产启动脚本 SHA256 | `46d4d709dceb75fd94c8749e4c4fa4ca7e051dfd3ed9d02989a22ca8ad607bf3` |
| 兼容代理 SHA256 | `4b0cefa5c1c785c43303e1d261969e889cd5989a95c135bb14998c96f5f6ea11` |
| request JSONL schema | **20**；实测有 `prepare_detail` 六段 |

这里记录的是本机 Docker **image ID**；`RepoDigests=[]`，没有伪称存在 registry digest。tag 可移动，后续执行以 ID/二进制 hash 校验；在清理镜像或迁移机器前必须导出并校验镜像归档。本次未导出数 GB 镜像或复制权重。

当前参数完整保存在 [baseline-manifest.json](../output/ninfer-hyperqwen-v3-review-20261020/baseline-manifest.json)。核心合同：

- `max-context=262144`、共享 `kv-capacity=262144`、`max-concurrency=1`、pending=8、pending timeout=600000ms。
- `prefill-chunk=1024`、`kv-dtype=rk4v4-e8`、MTP3、`lm-head-draft`。
- `rolling-tool`；continuation `l1-l2`；L1=6144 MiB、L2=8192 MiB。
- `preserve-thinking`；默认输出上限 32768；temperature=1.0、top_p=0.95、top_k=20、presence_penalty=0。
- 代理默认注入 medium；直接调用 native 而省略 reasoning 参数，不保证等价于经代理调用。

### 2.3 运行镜像、远端目录、本地源码是三个对象

本地嵌套仓库 `output/qwen38-27b-4090-ninfer/ninfer-4090` 为 clean `b0-scanner@e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`。29 的 `/home/hhtele/ninfer-4090` 没有 `.git`，`PINNED_COMMIT` 仍写 `44a2c6c3392c9d51e76a895ed97bf1867530d252`。

本次比较远端选定源码类型与顶层构建文件，共 603 个文件：

- 对 `44a2c6c`：592 相同、10 个文件不同，另有该提交没有的 Dockerfile。
- 对 `e0b05f7`：599 相同；`processor.cpp/.h`、`tokenizer.cpp/.h` 四个前端文件不同。
- 这是有明确文件范围的字节比较，不是完整构建树审计，也不能仅凭它证明镜像由这些目录构建。

因此，**不能直接在远端这个目录重建并称为“原样 B0+B1 baseline”**。历史上线记录也明确镜像是在若干提交落盘前构建，schema20 overlay 与后续 `f3b231d` 对应，而非从 clean `e0b05f7` 重建。生产镜像可作为二进制 oracle；源码重建身份尚需独立认证。

证据：[源码哈希](../output/ninfer-hyperqwen-v3-review-20261020/source-and-smoke-followup.json)、[比较结果](../output/ninfer-hyperqwen-v3-review-20261020/source-tree-comparison.json)、[历史构建说明](openclaw-qwen38-ninfer-b0-b1-20260930.md)第 3 节。本地旧 `scripts/production-18343.sh` 仍指向 `44a2c6c`，不得覆盖主机权威脚本。

### 2.4 本次 smoke 及其计量限制

| 用例 | 实际输入 / 输出 tokens | 缓存命中 | server TTFT | client 首有效 payload / 完成 | 结果 |
|---|---:|---:|---:|---:|---|
| native，greedy，thinking off | 17 / 2 | 0 | 0.0923s | 0.0930 / 0.1169s | `pong` |
| proxy，同文本 | 17 / 2 | 13 | 0.0393s | 0.0648 / 0.0653s | `pong`，L1 restore |
| proxy，medium，生产 sampling 参数 | 20 / 18 | 0 | 0.0904s | 0.2071 / 0.2083s | reasoning 后正文 `2` |
| proxy，tool_choice=auto | 285 / 26 | 0 | 0.3834s | 0.5723 / 0.5726s | 合法 `audit_echo({"value":"pong"})` |

四条成功请求均有匹配的 schema20 `request_start/request_done`。首次尝试命名 `tool_choice` 返回 400 `tool_choice_not_supported`；它是旧服务现有能力边界，随后按支持的 auto 方式成功。没有执行返回的工具。

这些只有短 smoke 样本，**不能用 2/18/26 tokens 的速率宣布提速，也不能把前两条冷/热差异当成代理开销 A/B**。它们实际证明了后续采集必须处理的四个问题：

1. 服务生成的响应 `X-Request-Id` 与提交的自定义 ID 不同。必须保存 client ID→响应 ID→`server_instance_id/request_id` 映射。本次首次按自定义 ID 检索为空，后按响应 ID 补齐了 8 个事件；不是没有日志。
2. `pong` 请求 accepted_drafts=3，实际 completion=2。接受量不能替代交付 token 分子。
3. medium 返回了 reasoning delta，但代理 `completion_tokens_details.reasoning_tokens=0`。本地代理第 77 行确为默认补 0；它不是真实 reasoning 计数。
4. 代理上的首有效内容可能晚于 server TTFT；工具参数可能整段到达。需要同时测 engine TTFT、用户首可见 payload、工具完整可执行时间，不能按 SSE frame 推算逐 token ITL。

证据：[smoke-summary.json](../output/ninfer-hyperqwen-v3-review-20261020/smoke-summary.json)、两份原始 capture。缺少的逐 token ID、真实 reasoning 分项、round span、GPU 时间序列没有补 0，仍未取得。

## 3. Findings 与必需修订

### R1 · P1：新路线资格与 29 主力采样语义不一致

位置：原方案 `design/00-architecture-and-contracts.md:22`、`plans/00-master-plan.md:15`、`plans/tasks/H1-T03.md:46–48`。原 `design/07` 已要求 greedy/sampling 分开，但没有把 29 的真实主指标落到具体轨道。

29 保持 temperature=1/top_p=.95/top_k=20 时，新 greedy-only 路径正确的行为应是继续走旧路径。改成 temperature=0 取得的 Lookup/W16 速度，不是同一业务语义下的提速。

**修订：** 冻结 `production_sampling_29` 和 `research_greedy` 两轨，分别记录实际路径与 fallback。前者是主力服务收益依据；后者只形成显式 greedy profile 资格。对 sampling 的提速优先验证公共 kernel、prefill、缓存、frontend；扩展 speculative sampling 必须另外定义 proposal q、logits processor、接受/拒绝残差与 RNG 消耗合同，不把 greedy 实现直接放开。

### R2 · P1：继承比较器会忽略 V3 p95 规则

位置：`previous-v2/scripts/merge_tools.py.md:135–153` 只枚举 p50/p90/p10；`design/07-metrics-and-acceptance.md:21–29` 要求 p95 与 bootstrap CI。

本次原样提取归档 Python，在内存执行 10 对样本：A latency=1，B latency=100，唯一规则为 `p95_relative=.05`。实际返回 `passed=true`、`metrics.latency={}`。[负例原始结果](../output/ninfer-hyperqwen-v3-review-20261020/p95-negative-control.json)。

**修订：** H0 checker 必须拒绝未知规则、空有效断言、缺 metric、样本不足、错误或重复配对；实现 p95、配对/聚类 CI，并加入此负例。不能只改规则 JSON。此 finding 针对现有归档 helper，**不声称尚未实现的 H0 checker 已存在同一缺陷**。

### R3 · P1 执行阻断：既有 PROD/O/P6 门禁尚未取得现场资格

原方案并非遗漏真实基线：继承的 `previous-v2/docs/05-validation.md:5–11` 已定义 PROD/O/C；P0-T04 要做 PROD/O；P6 要与 P0 对照，且已明确 E8 迁移不能要求 bit-identical。应保留这些设计。

本次发现的是**尚未满足的实证前置**：第 2.3 节的源码/镜像分离；当前 E8/schema20 与计划 P6 rk4v4/schema24 不同；P6 合格提交仍为 null。后续不能跳过 P0，从上游 U 或本地 O 填一个 SHA 就开始 H0。

**修订：** 把本报告的 B29 指纹绑定进 P0，建立 B29→O 重建差异、B29→P6 迁移验收，再对 P6→单因素优化。最终候选同时对 B29 回归。旧缓存与新 codec/snapshot namespace 隔离；旧日志缺的新字段保持 null/unsupported，不伪造 schema24。

### R4 · P1：现有采集口径不足以支撑“所有 metric 可追溯”

位置：旧 `output/qwen38-4090-compare/bench/http_bench.py:125–137` 在缺 usage 时按 `len(text)//4` 估 token，并可能用总 prompt/TTFT 估 prefill；`scripts/qwen4090_openclaw_long_context_concurrency.py:50–88,120–147` 非流式、输入规模近似；代理 reasoning 分项为补默认值。

这会把缓存命中算作重算吞吐、把 first byte 当首 token、把缺失值当 0，或使长上下文名义档位与实际 token 不符。第 2.4 节又实测到 ID 重写、SSE 合并和 accepted≠completion。

**修订：** H0 优先完成采集器与 normalizer；不复用这些历史脚本的统计结果作为新 gate 输入。每个 metric 必须绑定计数源、时间区间、单位、缺失原因、schema adapter 与 request ID；原始数据和派生公式都归档。

### R5 · P1 回归阻断：历史真实工具会话有未闭环的 reasoning 耗尽

仓库 [HANDOFF.md](../HANDOFF.md) 记录两条 medium 工具回合：prompt=20597/22345，completion=32768，finish=output_limit，tool_call_count=0；旧 1902 条高预算请求没有同类打满记录。因果未确定，不能直接归因 B0/B1，也不能因 tokenizer 差分通过就忽略。

**修订：** 冻结对应 Pi 分支与 wire 请求，覆盖 cold/append/restore 重放、前端 token/模板边界与停止行为。不得通过强行截断 reasoning、插入 `</think>`、缩小输出预算或丢弃异常来制造通过。短 arithmetic smoke 不能关闭此项。

### R6 · P2：统计权威需要统一，样本不足不能放行尾延迟

V3 `design/07:29` 给短中≥5、长场景探索≥3；继承 P0-T04/validation 给关键 case≥10、3 warmup。它们可以解释为探索与正式资格两层，但当前需要显式落盘。

**修订：** 探索可用 5 对，长场景可用 3 个 A/B/A block；正式关键 case≥10 个有效配对。每个对外声明的 p95 桶每 variant≥100 请求并有独立 run block；不足标 INCONCLUSIVE。旧 helper 自称 guardrail，不能替代统计非劣证明。

### R7 · P2：逻辑候选列与物理 verify 宽度尚有歧义

位置：`design/00:36–40,50,54`、`design/01:40–44`、`design/02:7,26`。`W=K+1` 与初始物理资格 `[1,4,5,6]`、K1/K2 短链及 valid-mask padding 同时存在，拟定类型没有唯一表示。

**修订：** H1-T01 显式定义 logical K、valid columns、physical W、physical batch/token rows；写出 K0/1/2/3/5 和 budget1/2 的映射。graph/workspace 按物理宽度计，accept/stop 按有效列计。这是文档合同歧义，不是已观察到运行越界。

### R8 · P2：技术资格与生产发布 gate 耦合

继承 P6-GATE 包含实际 canary/rollback，H0 依赖它；H5-GATE 同样含实际发布与回滚，H6 依赖它。没有发布窗口时，资产审计、reference 或离线研究也被管理依赖阻断。

**建议：** 分开 `technical_qualification` 与 `production_promotion`，后续技术研究依赖前者，正式发布依赖后者。若坚持原 DAG，明确这是停止条件，不能一边声明没有部署资格，一边把完整 gate 填 PASS。当前 full/e1_w6/e1_w8 DAG 均闭合无环，**这里不是悬空依赖或循环缺陷**。

## 4. 历史基线：能沿用什么，不能外推什么

### 4.1 原始 44a2c6c HTTP 阶梯

来源：`output/qwen38-4090-compare/results/fusion/ninfer-c262k-l16144/{meta,http_bench,cache_bench}.json`，精确出处与脚本行号见 [历史专项审查](../output/ninfer-hyperqwen-v3-review-20261020/review-history.md)。

| 历史 case | 实际输入 | 输出 | TTFT 秒 | 记录的 decode tok/s |
|---|---:|---:|---:|---:|
| short | 4141 | 256 | 1.223 | 111.78 |
| mid | 63848 | 256 | 21.902 | 110.77 |
| long | 119649 | 128 | 49.780 | 110.02 |
| deep | 184417 | 128 | 93.820 | 87.17 |
| cache-cold | 99701 | 36 | 40.058 | 129.41 |
| cache-exact | 99701 | 36 | 0.628 | 119.29 |
| cache-append | 104464 | 124 | 3.289 | 100.98 |

每档仅一次；temperature 实际为 .2，thinking off；cached=null 不能证明 cold；输出不足以支持稳态吞吐或分位数。cache-exact 的约 233 万“prefill tok/s”包含命中分子，不能解释为实际重算能力。

### 4.2 B0+B1 前端 ladder

来源：[verdict.json](../output/qwen38-27b-4090-ninfer/b0-evidence/ladder/results/verdict.json)，sample lane temperature=1.0；每档 index0 冷请求、index1–6 连续追加。

| 档位 / 冷实际输入 | 冷 TTFT 旧→新 | 追加 tokenize median 旧→新 | 追加 TTFT median 旧→新 |
|---|---:|---:|---:|
| 32K / 32933 | 11.140→10.392s | .914→.039s | 1.273→.412s |
| 128K / 131006 | 58.482→57.211s | 2.826→.172s | 3.292→.710s |
| 192K / 196806 | 106.150→105.145s | 4.052→.250s | 4.648→.839s |
| 240K / 245974 | 149.877→149.109s | 5.064→.305s | 5.714→.942s |

这支持“追加热分词曾显著减少，冷 prefill 仍是大头”。不能把同一会话的 6 个关联 turn 当成 6 次独立重复。该本地 verdict 不含完整 max_tokens/completion_tokens，不能证明长 decode 资格；240K greedy 路径还发生 full_reset→restore 差异，必须单列。

历史 G1 有差分证据；CPU ctest 为 31 pass / 71 skip / 0 fail。G0 不是 PASS，GPU 数值未跑，G6 真实流量观察未完成。这些状态继续保留。

### 4.3 必须排除的比较

- `extreme_v2/REPORT.md` 已作废的 219.8 tok/s、-18.5%、A/A .24% 来自 5-token 热缓存探针，不带入新 baseline。
- llama.cpp WORK、vLLM、Strata/next 使用不同权重/量化/框架/上下文/采样，属于系统方案比较，不能归因于某个 NInfer kernel。
- donor 381 tok/s 是 25K 逐字复述专项作者报告，不是自由 Java/中文/Agent 性能目标。
- 旧 Java 3 题×1 次只能作为回归种子，不能证明一般代码能力无退化。

## 5. 固定 donor 来源审查

固定 SHA 保持原方案，不追随浮动 HEAD：

| 来源 | 核验结论 | 对 29 的处理 |
|---|---|---|
| HyperQwen `30dba4f11b577e1f7699ec0b2947d6fe9d5ea997` | 长上下文表包含 3090、特定 KV/backend、PREFIX_CACHE=1、排除 prefill 等条件 | 只借算法；所有速度重新在 29 测量 |
| HyperQwen 40K vocab | 固定源码说明语料偏 Danish/English/Python，Han ID 覆盖极低 | 中文、Java、工具 JSON、byte-fragment 真实 ID 重新校准 |
| HyperQwen chain | 源码有 greedy、单请求/DP=1/no-media gate；不等于数学上所有 Lookup 都只能 greedy | 按每条路径资格判断，不将 donor 可关闭的 guard 当本地采样正确性证明 |
| NInfer U `5b99996bc7c1fe6ff27f271a205eb605302ec8bb` | 27B config 中 DFlash supported=false、max=0，MTP max=5 | DFlash2 不是加现成 flag；需要 H6 typed binding 与模型 companion |
| tqLLM `4d27324a124f92b7b7dcc554e6406ab6dc645b49` | 可见实现加载 selector、卷积、target taps、features、ring 与额外 scratch；retrieval 会改变 fast path | 模型文件约 .79GB 不能当总显存预算 |
| NInfer codec commit `772b88117867862d9669f4d970929242872bfabe` | 提交说明涉及 E8移除、midrise 语义与 snapshot/continuation ABI 版本变化 | 独立迁移与旧缓存隔离，禁止把参数改名当无语义升级 |

一级来源：[HyperQwen long-context](https://github.com/syv-ai/HyperQwen/blob/30dba4f11b577e1f7699ec0b2947d6fe9d5ea997/docs/long-context.md)、[vocab builder](https://github.com/syv-ai/HyperQwen/blob/30dba4f11b577e1f7699ec0b2947d6fe9d5ea997/prepare/build_draft_vocab.py)、[chain patch](https://github.com/syv-ai/HyperQwen/blob/30dba4f11b577e1f7699ec0b2947d6fe9d5ea997/patches/dflash2-ngram-chains.patch)、[NInfer 27B config](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8_27b/impl/config.h)、[tqLLM source](https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/src/qwen35.cpp)、[codec migration](https://github.com/tensorninja/ninfer-4090/commit/772b88117867862d9669f4d970929242872bfabe)。

证据限制：部分大文件下载截断、GitHub API 限流；lookup 核心 patch 未完整取得，optimizations、tqLLM cpp、codec patch 只引用实际取得部分。未宣称完整应用补丁、CUDA 编译或验证作者性能。逐项访问范围见 [donor 专项报告](../output/ninfer-hyperqwen-v3-review-20261020/review-donor.md)。相应实现阶段开始前应补齐关键完整源码。

## 6. Baseline 复现与比较链

### 6.1 四个有名字的对象

| ID | 含义 | 当前状态 |
|---|---|---|
| B29 | 本次恢复的真实镜像、模型、代理、argv、E8、schema20 | 身份与 smoke 已采集；性能资格未完成 |
| BO | clean `e0b05f7` 经冻结工具链重建 | 本次未构建；先证明与 B29 的产品差异 |
| B6 | 通过原 P0–P6 的真实集成提交、rk4v4/schema24 | 提交与资格尚未提供，不用 U 代替 |
| Cn | 某个单因素优化候选 | 未实施 |

比较链：`B29↔BO` 解释部署来源；`B29↔B6` 评价合并/codec 迁移；`B6↔C1↔C2…` 做消融；最终候选还需 `↔B29`。不能只报告相对变慢的中间版本获益。

### 6.2 冻结清单

每个 run 必须有机器可读 manifest，以下变化除预登记因素外均阻断比较：

- source 40位 SHA、dirty patch SHA、完整构建树/子模块锁、build flags、compiler/CMake/CUDA/cuDNN、image ID/可用 digest、binary SHA、实际加载库及构建日志。
- 模型/companion bytes、SHA 与资源清单；tokenizer/template/added tokens/config 六资源的独立 hash；adapter、KV codec revision、snapshot ABI。
- 完整实际 argv、代理版本与规范化规则、context/shared KV、active lanes/pending、prefill chunk、MTP、graph、缓存预算/namespace/TTL、输出停止策略。
- GPU UUID/PCIe、CPU/RAM/OS、driver、功耗/时钟策略、测量客户端位置和网络路径、外来 GPU 进程及 host swap/IO。
- dataset/generator/judge hash、case/会话分支、输入 token IDs/hash、采样 seed/参数、reasoning、tools schema、输出上限、校准/测试分区。

本次已冻结的字段在 baseline manifest；历史资源 aggregate hash 仅作历史来源，尚未从运行二进制重新提取。不能据此把 build provenance 写成 COMPLETE。

### 6.3 真正可复现的验收

1. 保存旧 image/binary/model 与配置的可恢复副本或已验证保留位置，建立独立 evidence/cache namespace。
2. 从 B29 原样启动，运行 A/A：同一冻结数据集、采样参数、缓存前置状态与硬件策略；确认漂移及重复性。
3. BO 重建后，完成 tokenizer/template/G1、稳定 golden、协议及 B29/BO 性能对照。解释所有差异，不能把重建后不同的输出改成新 golden。
4. E8→rk4v4 是数值与缓存 ABI 迁移：独立 oracle、业务质量、全长资源与速度均验收；不强求不同编码 bit-identical。
5. 同 codec、同 prefill state 下的新 greedy verify 路径，执行严格状态/输出合同；路径计数证明候选确实运行。
6. run manifest、raw、normalized、summary 与 gate hash 连通，换进程/换 commit 后不得借用旧 binary 的测试资格。

第 1–6 项是后续正式执行合同；本次仅完成其中的身份采集和有限 smoke，不把全长 baseline 标为 PASS。

## 7. 完整上下文与场景矩阵

### 7.1 输入长度与输出预算

主要配置始终保持 B29 的 `max_context=kv_capacity=262144`、prefill chunk=1024、active C1。不能为短档临时缩小池、为长档换 KV 精度，然后合成一张“同配置曲线”。

实际输入 P 指**最终模板、system、tools、历史和思考控制 token 处理后进入模型的总 token 数**。用同一模型资源的 tokenizer/prepare 路径计数并由 server 复核。启动 ctx、字符数、words 或重复次数均不算计数证明。

| 分组 | 精确目标 P | 必测输出预算 O | 目的 |
|---|---|---|---|
| 极短/短 | 256、1024、4096、8192 | 128、512、2048 | 启动固定成本、frontend、首内容与短 decode |
| 中等 | 16384、32768、65536 | 128、512、2048 | 主力代码/工具会话、prefill/decode 拐点 |
| 长 | 98304、131072、163840、196608 | 128、512、2048 | attention/带宽、缓存恢复、实际长 prompt |
| 超长 | 229376、245760、253952 | 128、512、2048 | 262K 池内最坏工作集、尾部质量与余量 |
| 长输出扩展 | 1024、32768、131072、229376 | 8192；业务回放按原预算，最高32768须容量可行 | 稳态 decode、自然终止、reasoning/tool循环 |
| 历史锚点 | 原始 request 对应 32933/131006/196806/245974，以及119649/184417 | 沿用原 payload 的预算；缺原始请求则不冒充复跑 | 对齐旧 ladder/HTTP，仅作迁移回归 |
| 上限边界 | `P = 262144 − O − R`，再测 +1；chunk/page/graph边界前后 | 1、2、K、K+1、128/2048 | 准入、停止、内部 speculative entitlement |

R 是从实际实现核实的内部 reserve，不能预填 0。253952 只剩 8192 空间，不意味着还能保证输出 8192 加内部预算，更不能沿用默认32768。若目标整数在实际模板/合法语料下未达到，校准器必须报错或登记预先冻结的实际 P；不得测后把近似值偷偷归入“精确目标”。

深度主矩阵的完整组合：14 个 P × 3 个 O × 4 个 workload × 2 个缓存状态 × 2 个采样轨道，共 **672 个资格单元**。workload 为复制/patch、自由 Java、中文分析、工具 JSON；缓存状态为 request-cold 与指定 warm prefix。每个单元是用例桶，包含冻结的多份输入，不是同一 prompt 重复即代表真实分布。

这份矩阵是待执行清单，不是 672 个已通过测试。初次筛选先 O=512、全 P 的最小场景；正式发布按声明范围补齐。不能为缩短运行把未测单元标 SKIPPED-success。

固定O矩阵刻意改变输出预算来观察成本曲线；`production_sampling_29`在这里表示采样语义保持现网配置，并非声称每格都是原生产完整请求。真实Pi回放另保留原请求预算。小预算medium可能用尽reasoning，需记录该结果；不得以压低预算使任务提前结束来证明任务提速。

### 7.2 语料与质量

语料按会话/项目划分 calibration、development、locked-test，不能把同会话相邻 turn 分进训练与测试。包含 Java/SQL/log/diff/tool JSON/中文/英文及 byte-fragment token；copy 专项单独标记，不用一段重复句凑满上下文。

长文本在 0%、25%、50%、75%、末尾放不同唯一事实，加入跨段类名/签名/约束与干扰值。检查精确检索、跨段依赖与实际代码编译；单 needle 命中不等于一般长上下文质量。

真实 Agent 至少 20 个隔离 Java 任务×3 固定 seed，覆盖事务、幂等、MyBatis 参数、异常链、分页、锁、缓存失效、序列化、API兼容、补测试。记录原始编译/测试命令、exit code、断言与任务完成标准。60 次是工程验证下限，不自动证明 3 个百分点统计非劣。

### 7.3 缓存与会话状态

| ID | 场景 | 必测深度 | 必须观察 |
|---|---|---|---|
| S0 | service cold→ready→首请求 | 短、32K、128K、最大可行 | 加载/图准备时间独立；OS page cache hot/unknown如实记录 |
| S1 | ready后 request cold | 全14档 | `reused=0`；warmup不得填充正式prefix |
| S2 | exact/warm prefix | 全14档 | 实际命中来源/数量；不是“第二次”就判热 |
| S3 | 连续 assistant→tool→user append，增量128/1024 | 8K、32K、128K、192K、接近248K | append/frontier/restore路径，新增prefill，B0/B1工作量 |
| S4 | 改最近user、改中间tool、改system/tools | 同S3 | LCP合法回退，不复用修改后的状态 |
| S5 | branch A→B→A | 32K、128K、最大可行 | 分支隔离、epoch、输出/隐藏状态正确 |
| S6 | 受控L1驱逐→L2恢复→miss | 32K、128K、最大可行 | evictions、restore/export、字节、IO、热冷区别 |
| S7 | 重启后的恢复 | 原配置支持的层级 | B29只有L1/L2；进程重启不应假称L2持久化恢复；L3仅在候选明确启用后另测 |
| S8 | target热/aux冷、tokenizer/adapter变更、late DMA | 候选相关shape | 错误身份拒绝、过期回调不影响新lane |

接近上限的追加必须从较短前置状态构造，以确保最后一轮仍满足 P+O+R。不得清空生产用户缓存或全机 drop_caches 来造实验；使用隔离服务实例/缓存 namespace 和该版本实际支持的控制方式。

### 7.4 客户端并发与引擎并发分开

B29 的 active concurrency 是 1。先测 C1 服务接收 2/4 个并行客户端的排队、公平性、超时和取消，不改配置冒充“当前 C4 baseline”。

候选如果声明 active C2/C3/C4，先建独立资源资格，以下只是待预检组合：

| 活跃 lanes | 输入组合 | O | 核验 |
|---:|---|---|---|
| 2 | 2×8K、2×32K、2×64K、2×112K、128K+64K | 512/2048 | 共享池、长短干扰、每lane TTFT及总吞吐 |
| 3 | 60K+40K+20K | 512/2048 | 继承混合Agent场景、状态导出与公平性 |
| 4 | 4×8K、4×32K、4×56K、128K+64K+32K+8K | 512/2048 | 各lane与合计 entitlement、图/GDN/scratch峰值 |
| 负例 | 超共享KV、pending8与第9个等待请求、取消释放 | 短 | 实际准入合同下受控拒绝/等待，不OOM、不永久丢lane |

每格核对 `Σ(Pi+Oi+Ri)` 及实际 allocator 约束，预算可行也不代表显存可行。无法支持时记 UNSUPPORTED/BLOCKED，并验证拒绝；不承诺四份262K。首版动态 COPY/W16 的 C1 限制保持。

### 7.5 协议与故障矩阵

对实际支持的 chat/responses/messages 分别测非流式、SSE、native、兼容代理；公网测量另列网络/鉴权路径，不混入 kernel 性能。当前本次仅测 chat，不能宣布三协议已验收。

必测：reasoning/content/tool 分离；空role/keepalive/prefill progress；中文与UTF8切分；参数delta拼接；多工具/中断JSON；stop/EOS/输出预算；previous_response_id；客户端断连；取消时export/evict/restore；lane复用；RoundFault后下一请求；超时、错误ID、旧snapshot拒绝。只有工具end完整并验证JSON后才能执行工具。

当前 named tool_choice 为400；这是 B29 契约负例，正向工具路径用支持的 auto。候选增加支持时单独记录能力变化，不能把原不支持案例纳入旧成功率分母。

## 8. Pi 真实会话测试

**建议以 Pi session 作为主要业务语料来源，同时保留定长合成矩阵。** 固定请求回放负责可比较的推理性能，真实 Pi 闭环负责任务完成率和用户等待时间。两者无法互相替代。

### 8.1 已核实的本机状态

按用户指定执行 `nvm use v22.19.0`；本机 nvm 初始化脚本为 `/usr/local/opt/nvm/nvm.sh`。当前 Pi 包 `@earendil-works/pi-coding-agent` 为 **1.3.0**，不是旧评测 parser 注释中的 0.84。

只读检查 `/Users/luo/.pi/agent` 的相关配置与 session；未读取 `auth.json`、未输出凭据、未调用模型或执行历史工具：

- 21 个主 session，6 个包含 27B assistant，共 2340 条标为 27B 的 assistant；next另有576条。
- 当前 defaultProvider/model 是 openclaw / `openclaw/Qwen3.8-27B-WORK`；API 为 openai-completions，指向既有公网入口。
- 当前客户端 `contextWindow=262000`、`maxTokens=98304`；历史异常回合输出预算是32768。直接resume会让当前默认值污染复现条件。
- 当前 compaction enabled，reserveTokens=16384、keepRecentTokens=20000；真实历史还使用 sol-pi 上下文扩展。
- Pi配置是当前事实，不能反推9月的 serializer、system、tools、采样或服务端镜像。

详见 [Pi 专项调查](../output/ninfer-hyperqwen-v3-review-20261020/review-pi.md)，其中保留配置/package/session的hash、完整本地路径和结构统计。私有session未复制进仓库。

### 8.2 首批必选语料

| 语料 | 来源与规模 | 用途 |
|---|---|---|
| Java LSP 长会话 | session `01a0b91b-d3f5-7399-b9ee-75ca51f2b4f2`，2192条27B assistant；11次compaction、25次context_edit、1278条sol-pi上下文状态custom事件 | 自然长上下文、真实工具比例、压缩/修改/分支 |
| candidate-kit 异常会话 | session `01a0f307-01d6-768d-92ec-f8512b8c047e`，108条assistant、115条toolResult | reasoning耗尽与工具回路回归 |
| 必选异常 entry | `f89c5dcc`、`97fc7be6` | input+cacheRead分别20597/22345，output32768，仅thinking，无text/toolCall |
| 其他自然会话 | 其余4个含27B标记的session | 补独立项目/会话，避免长会话过度加权 |

两个完整文件SHA分别为：

```text
long-session:
aee937bdc5d29b09ad4afc95ca39bfdcd3fe77df1465db1ee5bb00070de1c16b
truncation-session:
ee064ce94fbb8ba65286f03ac3eadb4f71a3f1f7603a7500757ce88be5c29ff8
```

不能只按 session 的最后 model_change 分类整个文件。长会话尾部后来改成next；10月其他会话即使模型字符串为27B，也可能请求到不校验model的Strata。必须联结服务端身份/日志；不能唯一确认的样本标 `ENGINE_IDENTITY_UNKNOWN`，可作为语料但不作为历史27B速度证明。

### 8.3 为什么直接 `pi --resume` 不可作为精确回放

session是有parentId的事件树，包含compaction、context_edit、custom/extension投影和system sections。当前Pi源码先按leaf恢复父路径、处理压缩保留范围，再应用context_edit；transformContext/sol-pi还可能修改最终上下文。简单筛选所有message会把其他分支、已压缩内容或被替换工具结果错误发送。

精确重建还需要当时Pi/AI serializer版本、system sections、tools schema、扩展版本与状态、reasoning映射、采样/预算和代理转换。session usage通常没有TTFT/ITL，也没有image ID。**usage.input通常是未缓存部分；这两条异常的总prompt必须取input+cacheRead，不能用991/1832冒充20K级上下文。**

给重建结果两个明确等级：

- `HISTORICAL_WIRE_VERIFIED`：重建请求与当时wire、token/hash或可唯一关联的server记录对上，历史配置来源完整。
- `FROZEN_SESSION_DERIVED`：历史信息不齐，用已冻结当前serializer重建的代表语料；后续A/B字节一致、可复现，但不声称精确重演历史HTTP请求。

缺旧依赖不阻止建立新可复现corpus，但不能把第二种改名成第一种。

### 8.4 A层：固定请求与固定轨迹回放

1. 冻结session文件SHA、leaf/entryId、parent路径、compaction/context_edit/extension状态；提取发生在指定assistant之前的上下文。
2. 在专属 `PI_CODING_AGENT_DIR`、独立session-dir和冻结Node/Pi依赖下离线生成payload；可用provider serializer、本地HTTP capture stub或 `before_provider_request` hook。只捕获无凭据body，并确保离线过程不发往真实provider。
3. 保存client wire和代理规范化后的engine payload hash，使用同一27B tokenizer校准实际P；A/B的单因素允许清单以外完全相同。
4. 从自然会话选择各长度、工具比例和状态路径；缺失长度才构造synthetic补充，并独立标记。定长合成、自然Pi语料分别报结果。
5. 暖轨迹的下一请求使用**冻结的历史assistant/toolResult**；候选生成结果仅作为测量，不接入下一条固定请求，不执行其工具。这是teacher-forced trace，不能据此宣布任务完成。
6. 包含cold、exact、append、近/远历史改写、compaction切换、A/B分支、驱逐恢复。两条真实异常及相邻前后序列必须入集，保持原32768预算和medium语义。

温度1的采样轨不要求与历史输出逐token相同；前端token/模板/边界先做确定性差分，模型层比较输出耗尽率、工具可用性、质量与延迟。相同seed不自动保证不同投机路径消耗相同RNG序列。

### 8.5 B层：隔离工作区的真实 Pi 闭环

每次从冻结repo commit/fixture创建干净临时工作区和新session；固定Node22.19.0、Pi包、system/tools/extensions、上下文文件、模型配置、reasoning/采样、最大工具轮次和超时。历史bash/edit/write不能在原cwd重放；工具仅作用于测试工作区，外部写入/付费provider不可混入。

沿用已有 [run_pi_java.sh](../output/qwen38-4090-compare/scripts/run_pi_java.sh) 的fixture复制、baseline Git、测试/verify hash保护、changes.patch与exitcode记录思路；执行前按实际CLI固定MCP、context files、prompt templates和扩展加载范围。需要真实sol-pi产品配置时单独命名该profile，不能一边关扩展一边宣称原工作流等价。

闭环中，基线和候选各自生成工具调用并执行，历史会自然分叉。记录总任务wall、模型等待、工具运行、编译/测试成功、轮次、无效调用、重试、循环与失败。候选自己的工具结果接回它的上下文；不能拿历史toolResult冒充真实执行。

旧 `bench/parse_pi_json.py:38–51` 只留最后一次usage。新统计必须按唯一assistant/request ID汇总整个任务，区分prompt/cacheRead/实算prefill/输出；处理重试、分支与compaction，避免重复累计。不要把 `last_usage` 写成全任务token成本。

### 8.6 启动下一步的最小证明

先离线重建两条异常entry和一段长会话，核对token计数、分支、预算与历史server统计，产出首批冻结wire corpus。再跑B29 A/A，随后扩到全长度矩阵和隔离闭环。本次只完成可行性、结构与身份调查，**没有执行请求重建、Pi回放或付费模型调用**。

## 9. Metrics 与追溯合同

### 9.1 每请求记录

| 类别 | 必填内容 / 来源 |
|---|---|
| 身份 | run/block/variant/order/case/session/branch/parent/lane/client ID、响应 ID、server_instance_id、manifest hash |
| 状态 | attempt、warmup、HTTP、协议终止、finish_reason、错误类别、deadline、是否重试/取消、实际候选route/fallback |
| token | actual prompt、requested output、实际交付completion、computed_prefill、reused、drafted/accepted/bonus；reasoning/content/tool真实分项及计数合同 |
| client时间 | send_start、headers、first_byte、first_progress、first_reasoning/content/tool、last payload、tool complete、done、request_complete，同一monotonic时钟 |
| server时间 | queue、prepare六段、restore、prefill、decode、publish；候选增加draft/alignment/verify/accept/round wall |
| speculative | N/K/logical valid columns/physical W/physical rows、每位置接受量、committed、graph key/hit、epochs、CPU Lookup与DMA span |
| 资源 | GPU/host时间序列、分配高水位、pool/graph/aux/pinned/RSS、温度/时钟/功耗/节流、IO、swap、其他GPU进程 |
| 质量 | 原始输出/工具参数、判定器版本、编译/测试exitcode、任务成功、检索断言、重试/循环/输出耗尽 |

原始日志不能包含凭据。私有 prompts/session 留在受控本地，报告用 hash、结构统计和脱敏摘要。缺失字段为 null+原因，并在 gate 中判定是否阻断；不补0，不通过重新 BPE 显示文本伪造原 token ID 数。

### 9.2 指标公式与边界

- **E2E latency**：client complete−send_start，包含队列、传输和流结束；不能拿 server decode 替代。
- **Engine TTFT**：server 原生定义，附版本和时间区间。**Client TTFT**：首非空模型 payload−send_start，reasoning/content/tool 最早者；progress/空role不算。另报首正文 TTFC、工具完整可执行时间。
- **E2E output throughput**：实际交付 completion / client E2E；不足长输出的短探针不作稳态结论。
- **Server decode throughput**：交付 completion / 明确的 server decode span，记录包含首token/末尾停止处理的具体定义。
- **Prefill throughput**：computed_prefill / prefill span；reused 不进分子。total_prompt/prefill 的热缓存数字另名，禁止叫实际预填充速度。
- **客户端 TPOT近似**：有可信交付数N且N>1时，`(last_payload−first_payload)/(N−1)`，明确合并flush与网络影响；如果全部tokens在一个chunk，不报告0 TPOT/无限吞吐。真实ITL分位需要逐token时间戳，否则只报chunk-gap。
- **Aggregate throughput**：同一测量窗口全部交付tokens / 窗口wall，不能把各请求TPS相加。
- **Speculation效率**：accepted/drafted、committed/round、round wall、有效W分布共同报告；acceptance上升不等于提速。
- **能耗**：对板卡功率时间序列积分得J/request或J/batch，再除交付tokens；并发时不把整卡能耗重复归给每lane。采样不足不伪称精确能耗。

跨机器的绝对时间不相减。server/client 通过ID关联各自duration；异步阶段重叠时不能把 span 简单相加。GPU采样以100–200ms为起点并测观测OFF/ON开销；短请求峰值可能只是下界，结合allocator高水位。

### 9.3 资源账本

GPU至少覆盖：Target weights、KV pool、FP32 GDN persistent state、MTP、proposal head净增量、chain frames、ReplaySSM、attention partials、alignment scratch、graph private pool、draft weights/ring、features、staging/index、export/transient、实测余量。

Host至少覆盖：RSS、archive、checkpoint ring、L2、pinned、双buffer、文件page cache与swap/IO。预算、实际allocated/reserved、NVML used与峰值分列；共享buffer按生命周期计，不重复加也不预扣未释放旧head。

原方案约17.05MiB/lane的 W6→W16 ReplaySSM 增量只是一项 raw payload；本次空载约1970MiB余量也不是可全部分配预算。满足同样262K上下文及安全headroom后才有资格；不能静默缩上下文、换codec或降低GDN精度求fits。

### 9.4 证据包目录

```text
run-id/
  manifest.json                 身份、允许变化因素、采集器/统计器版本
  expected-cases.jsonl           所有应执行单元及支持范围
  dataset-manifest.json          私有原件位置/hash、分支、模板、token IDs/hash
  requests/                     固定 wire payload；凭据分离
  client-events.jsonl            原始SSE及monotonic时间
  server-events.jsonl            schema adapter前原始日志
  gpu-host.jsonl                 时间序列及环境异常
  quality/                      工具/编译/测试stdout、exitcode、判定
  samples.jsonl                  归一化指标，每条回指raw
  statistics.json               配对、CI、分位数、样本数、剔除/失败
  coverage.json                 expected vs observed，缺项不能通过
  gate.json                     源码/功能/数值/资源/性能/发布分别判定
  SHA256SUMS
```

源码修改后的重测产生新run，不覆盖旧证据。环境异常、失败、超时、取消、重试均保留；一次成功重试不能替换原失败attempt。对照所需数据必须可从证据包和受控原件解析，不能只留截图、结论表或可变latest路径。

## 10. 统计、资格与采用门槛

### 10.1 运行与统计规则

1. 单GPU串行 A/B/A 或 ABBA，顺序和seed先登记；相同cache前置状态，切换后排空/export完成，再运行独立warmup。
2. 3次warmup不进正式样本；warmup使用独立前缀。每关键case正式≥10对，至少5个独立run block；长场景3个block只作探索。
3. 每个声明p95的预登记桶/variant≥100请求。桶内任务比例、输入/输出档、sampling/cache/endpoint预先冻结；不能测后混合长短或冷热点凑100。
4. bootstrap建议10000次、95%CI、固定seed；按会话/case聚类，并配对重采样run block。相关turn、同一请求tokens不是独立样本。
5. 同时报绝对差与相对比，mean/median/p90/p95、吞吐p10、样本数和CI。小分母使用预登记绝对预算。
6. 只按事先规定的外来GPU占用/可证实热节流等环境条件排除整个配对block；归档并整block重跑。候选自身OOM/超时/慢样本不能被当噪声剔除。
7. 性能成功样本统计与全部attempt可靠性并报；超时为censored/deadline，不记0、不静默删除。样本不足是INCONCLUSIVE；缺证据是BLOCKED；完整实验无收益才是NO_ADOPTION。

### 10.2 推荐冻结门槛

| Gate | 判定 |
|---|---|
| 身份/覆盖硬门 | binary/config/data/hash匹配；required cases齐全；实际深度正确；GPU必测无skip；候选真实route命中 |
| 数值/状态 | 按同codec/同prefill state的精确或独立数值合同；stop/bonus/rollback/cancel等正确 |
| 可靠性/质量 | 无新增必测失败、OOM、状态污染、schema回归；编译/任务观察成功率不下降，并报告CI |
| 旧业务guardrail | TTFT p50≤+5%、p90≤+10%；decode p50≥−3%、p10≥−5%；prepare同TTFT；小量绝对预算TTFT5ms、prepare0.5ms |
| V3长上下文 | 128K/192K/248K普通负载decode比率CI下界≥.97；warm TTFT p95比率CI上界≤1.05，样本不足不通过 |
| H5采纳 | copy/edit wall time改善≥15%；自由Java/中文/tools p50退化≤3%、p95≤5%；完整Agent wall time改善≥5% |
| H6/H7采纳 | 预登记目标桶committed throughput改善≥15%且E2E改善≥5%，同时过质量/资源/其他场景回归 |

改善阈值推荐用95%CI边界判断；跨阈值则继续测或INCONCLUSIVE，不凭一个最佳点。旧/V3门槛同时适用时取明确冻结的更严格规则。只有copy获益则只给copy profile资格；不能写成通用主力提速。greedy资格不扩到sampling，C1不扩到C4，短上下文不扩到262K。

概率质量的非劣margin、功效与样本数需要在候选结果出现前单独登记。20×3是现实功能验证起点，不能声称已经统计证明小幅无退化。

### 10.3 测试成本与执行层级

672单元是最终声明范围的覆盖表，不要求每个worker或每次局部改动重跑。顺序为：

- **T0可行性**：全长度、O512、少量固定用例，验证计数/内存/协议/日志；不评尾延迟。
- **T1筛选**：预登记代表case与受影响路径，短中5对、长3个block；淘汰无收益方案。
- **T2资格**：同一集成binary执行完整声明矩阵，关键case≥10对、p95桶≥100，补齐Agent/资源/状态与回归。
- **T3发布**：实际入口、排空、有限真实流量、回滚；生产与技术资格分别记录。

先用T0实测估算 `Σ(各格样本数×[prefill+decode+状态准备])+warmup+切换+复测余量`，再冻结GPU队列。历史240K冷TTFT约149s：仅100次同类冷请求就至少约4.1小时，尚不含生成、对照和重置。因此不能把本次审查短smoke描述为已经完成全长性能认证。预算不足就明确缩小发布范围，不降低统计门槛后继续称全范围通过。

## 11. 各优化阶段的具体检查

| 阶段 | 必须证明 | 未满足时 |
|---|---|---|
| P0–P6 | B29/BO来源、定制保留、E8迁移、schema/proxy、全长质量性能 | 保持PENDING/BLOCKED，不伪造P6 SHA |
| H0 | 采集器、ID/schema映射、实际tokens、baseline A/A、资源账本、checker负例、观测开销≤2% | 不进入性能采纳判断 |
| H1同宽Lookup | 同头延长；不一致头不接旧尾；K1/K2映射；hash collision；各拒绝位置、全接受bonus、budget/stop/cancel/epoch | 回到旧路径，不以高acceptance放行 |
| H2词表 | 40960/65536/98304/131072映射与真实中文/Java/tools链覆盖；byte-fragment；错误scale/ID/指纹拒绝；原子发布；旧head释放账本 | 保留合格大词表 |
| H3 W8 | B×W物理容量、scratch guard/NaN、同prefill数值、eager/graph、reject/alignment、长context | W8不合格则不资格化W16 |
| H4 W16/COPY | 真实物理宽度与每lane策略；高命中→拒绝退出；alignment不省；late DMA；完整round净收益 | NO_ADOPTION或选择已有e1_w6/e1_w8范围 |
| H5组合 | 同一commit完整保留路径、B0/B1、工具/三协议、Agent、资源；真实旧镜像+旧缓存回滚 | 只交付合格研究，不宣称生产 |
| H6 DFlash2 | immutable revision/license/tensor manifest、taps/norm/conv/selector/block/vocab绑定、逐层oracle、ring commit/reject | 缺资产BLOCKED；文件存在不等于兼容 |
| H7 selective | G可重建真实各层K/V的数学与reference；全历史页可检索；位置/re-RoPE；冷/热archive与PCIe完整成本 | 不把理论K/V压缩收益当实际提速 |
| H8最终 | 最近合格baseline及B29双对照；完整声明scope、真实回滚、推广边界 | 不将缩范围结果称完整融合 |

原方案的 full/e1_w6/e1_w8 是有效范围机制；取消宽块研究不应改写失败任务为PASS。多卡、GDN FP16、KV稀疏、直接移植vLLM页几何与英文40K表继续排除。

## 12. 本次验证、交付与后续执行入口

已执行：

- `jssh 29` 实机配置、GPU、服务、image/binary/model/proxy/launch指纹与源码字节对照。
- 现有 `switch-qwen.sh 27b`；Strata停机与27B双接口就绪。
- 四条成功流式smoke和named-tool-choice受控400，保留原始SSE、时钟、usage、server事件与指标快照。
- V3 default/e1_w6/e1_w8 DAG闭合/无环核查；完整图103节点（87任务/16gate），窄范围67和74节点。
- p95静默忽略负例复现。
- Node `v22.19.0` 下的Pi `1.3.0` version/help检查；使用临时独立agent目录，未改用户Pi配置或session。
- `pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm test:integration`、`pnpm build` 均 exit0。[命令结果](../output/ninfer-hyperqwen-v3-review-20261020/repo-checks.json)。这些是CodexGame检查，不是NInfer CUDA资格；Phaser大chunk警告仍为已知。

两路独立终审分别复核主报告事实/部署身份和矩阵/统计/Pi设计，均未发现阻断交付的问题。机器清单的状态、主报告链接及原V3输入未变另有 [交付校验](../output/ninfer-hyperqwen-v3-review-20261020/delivery-validation.json)。

未执行：BO/P6/任何候选构建，NInfer CUDA数值测试，全上下文正式baseline、长输出/并发/故障矩阵、Pi闭环重跑、词表校准、DFlash2资产转换、优化发布及新旧版本回滚演练。没有以本次停止Strata、启动既有27B替代这些验收。

下一步按顺序完成：**Pi语料冻结与采集器 → B29 A/A与源码重建认证 → P0–P6独立迁移验收 → sampling/greedy两轨单因素优化 → 完整声明矩阵 → 发布与回滚。** 原方案的拟建 `check_hybrid_evidence.py`、hybrid CLI/test targets 仍须先实现；不要直接运行文档占位命令并报已通过。

运行复查可以使用：

```bash
jssh 29 'systemctl show openclaw-qwen38-next.service openclaw-qwen38-ninfer.service -p Id -p ActiveState -p UnitFileState'
jssh 29 'curl -fsS http://127.0.0.1:18030/v1/models'
jssh 29 'curl -fsS http://127.0.0.1:18343/v1/models'
```

本次恢复前的服务路径仍保留：`/home/hhtele/strata/switch-qwen.sh next` 可切回 Strata；它会占用GPU并切换18343，后续以27B为主时不应自动调用。优化候选的回滚必须恢复 B29 的 image ID、参数、代理和独立旧缓存，不能只把hybrid flag关掉。

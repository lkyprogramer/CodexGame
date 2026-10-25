# Strata · RTX 4090 / 128K PR 实验包

**对象：已经部署的 Strata，不是 NInfer。** 单张桌面 RTX 4090 24GB、约 62GiB RAM（29 号机，Xeon Silver 4216）；总上下文硬上限 **131072 token**。本包提供 AI 开发执行计划、11 个 PR 的独立移植任务（初稿 10 项 + 2026-10-23 新增 #2253）、冻结题集生成器、受控 Java 工具循环、隔离测试编排和统计报告。**不包含已完成的 PR 移植，也不包含模型或编译好的引擎。**

## 先看结论

按 29 号机（192.168.10.29）2026-10-23 核对的生产事实重新排序后，优先筛选 **#2253 → #3453 → #1536 → #3307**。#2253 直接对应 29 现网会话缓存 park 失效（缓存清空后仍拒绝、堆约 6.9 GB）；29 的引擎时间 75～80% 在 decode，所以 decode 内核（#3453）紧随其后，先用诊断构建拆清 decode 窗口；#3711 与 #2253 方向相反，降到第 8；#2964 在生产形态（PCIe share 0.007 + adaptive overlap）下按规则直接 `NOT_APPLICABLE`；#3517 因 Pi 的 root 约 12.3K、低于 16384 周期检查点而降级。其余各项有明确前提，允许输出 `NOT_APPLICABLE`，不为了“完成所有 PR”强行开启缓存、换模型或改 KV 模式。

本次冻结的基线就是正式版 **v0.2.3**（2026-10-23 发布时核对，tag 指向同一提交）：

| 对象 | 冻结值 |
|---|---|
| 最近正式发布版 | `v0.2.3` / Engine `0.1.48`；`v0.2.3.1` 只修 Control（#3810），引擎包仍是 0.1.48 |
| 开发基线 | `5c8dd322528cc84f68f461ad54a506b9da8fa8d4` |
| 基线属性 | 即 v0.2.3 tag 的提交；之后 main 只多了 0.2.3.1 的 Control 热修，引擎代码无变化。生产 29 是 0.1.43.1，P→A0 仍是大迁移，先做迁移评估（MIG） |
| 目标 GPU | NVIDIA `sm_89`，单卡 |
| 最大实际输入 | 默认长测最多约 122880 token，仍须计入模板和工具定义 |
| 输出与安全余量 | 每请求显式正数输出上限；预留 4096 token 安全空间 |
| 生产环境 | 只读；不自动停止生产服务，不运行 `reset --hard`，不自动发布 |

来源、PR head SHA 和已知变更见 [sources/LOCK.json](sources/LOCK.json) 与 [来源索引](sources/INDEX.md)。

## 29 号机的实际前提

GPT 初稿依据的是 10-08 的旧记录（IQ3_S、conversation cache=0、可用 RAM 约 6.6GiB、PCIe 0.022），已与现网不符。当前生产（**已停止，29 正在跑其他实验，未经用户允许不得启动 Strata 或占用 GPU**）：

- Strata **0.1.43.1**（部署树 git HEAD `a0116b27`），模型 **IQ3_XXS GSQ-RCO**，expert cache 9434 slots / 15.29 GiB，`--kv int8`，KV 是否全驻显存**未验证**。
- 生产 env：`STRATA_ADAPT_OVERLAP=1`、`STRATA_PREFILL_CPU_SHARE_MAX=3072`；`--spec 4 --spec-min-p 0.5`、`--vram-reserve-mib 974`。
- conversation cache **6144 MiB × 4 slots**，确实发生 parking；10-15 起因 MemAvailable 约 1.5 GB 被拒，进程堆保留约 6.9 GB。
- 真实流量：decode 占引擎时间 75～80%；prefix reuse 89～94%；PCIe share 0.007；Pi root 约 12.3K；约 10% 续轮重读上一轮回复。
- 共存：端口 18343 被其他进程占用，18089 空闲；OCR 等 4 个容器常驻；无 JDK 镜像。
- 噪声：重启 A/A 约 5%，抽样配对约 7%；greedy 输出跨重启不逐字节一致。

完整数据、禁区和内存门槛见 [环境与限制](docs/02_ENVIRONMENT.md)。仍以 `doctor` 和本轮启动日志为准。

## 十一项顺序

| 排名 | PR | 先做什么 | 主要停止条件 |
|---:|---|---|---|
| 1 | #2253 内存门槛释放 glibc 堆 | 在 A0 复现驱逐后仍拒绝 park；同时测 CFG-MMAP | main 上复现不出，或 trim 代价大于省下的重读 |
| 2 | #3453 Ada MMVQ 参数表 | 先看 CFG-IL0（Issue #1842）与 decode 窗口诊断，再用本机微基准生成表并移植 | 只快微内核而端到端不变 |
| 3 | #1536 回复 Token IDs 复用 | 区分 BPE 不一致与 Pi 剥离 thinking 两种重读 | 重读全由客户端改写引起或破坏协议 |
| 4 | #3307 MTP 显存原位借用 | 主指标收窄为 ≥8K 未读 token 的 TTFT | DMA 代价大于 Prefill 节省 |
| 5 | #3584 前缀／递推状态恢复 | 小预算验证再扩到 120K | 内存不足、错误状态命中 |
| 6 | #3281 请求级显存事务 | 与 #3307 分开测试，同样看长读 TTFT | 无法跨过更优 planner 档位 |
| 7 | #3517 真正的 Root 固定 | 先确认 root（约 12.3K）是否越过 16384 检查点 | 根未越过检查点（当前预期如此） |
| 8 | #3711 Host KV 页复用 | 等 #2253/CFG-MMAP 让内存有界后再评估 | 无 parking、RSS 无界或不改善 capture |
| 9 | #2822 短请求抢占 | 真实主／辅助客户端重叠 | 单客户端、无暂停状态容量 |
| 10 | #3322 DFlash2 差量服务集成 | v0.2.3 的 DFlash2 在 `--serve` 下不生效；先做命令行 MTP vs DFlash2 上限测试 | 命令行采样组领先不足约 10%、只能快 decode |
| 11 | #2964 Expert Fetch 晋升 | 生产形态下 qualify 直接 NOT_APPLICABLE | PCIe share 0.007、overlap 开启 |

**测试顺序：** P→A0 迁移评估（MIG）→ DIAG 与配置对照 → 按排名逐个 PR → 组合 → 非 PR 代码改造。除 MIG 外，所有测试都在 A0（v0.2.3）上做，不先在 0.1.43.1 上全测一遍；只有 MIG 判定 A0 回归时，CFG-MMAP 与 CFG-IL0 才在 0.1.43.1 上作为生产候选另测。分支规则见 [测试协议](docs/04_TEST_PROTOCOL.md)。

`prs/` 下文件编号沿用初稿顺序（01=#3453 … 10=#3322，11=#2253），以上表和 `config/experiments.json` 的 `rank` 为准。P0 还有四个不属于任何 PR 的配置／诊断对照（CFG-IL0、CFG-EXACT、CFG-MMAP、decode 诊断构建），见 [START_HERE_AI.md](START_HERE_AI.md)。不依赖 PR 的底层方向（CPU 专家路径、C-state、大页、draft 开关、kernel 融合、4090 tensor 限速解锁 CFG-UNLOCK 等）见 [非 PR 方向](docs/10_NON_PR_DIRECTIONS.md)。

分数、依据、未选项目见 [综合排序](docs/01_RANKING.md)。

## 使用入口

把整个目录交给负责实机开发的 AI，首先读 **[START_HERE_AI.md](START_HERE_AI.md)**。它可以直接使用 TASK 文档工作；也可配置外部 AI 命令，让 `auto` 编排完整流程。

```bash
# 在实验包目录，用 Strata 所用的 Python 环境执行
export LAB_PYTHON=/home/hhtele/strata-0.1.43.1/.venv/bin/python

# 只需初始化一次。所有路径都来自现网实际部署，不下载或替换模型。
# 29 号机实际路径（2026-10-23 核对；init 前再 ls 确认）
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
./run.sh qualify --pr 3453
./run.sh prepare --pr 3453
```

最后一条生成 `workspace/state/pr-3453/TASK.md`、冻结的 PR diff 和隔离 worktree。**不会自动把旧分支合并进最新 main。**

### 已配置 AI 开发器时的一键入口

在 `config/local.json` 中填入 `agent_command` 的 argv 数组，参数可以包含 `{task_file}`、`{worktree}`、`{package}`；该命令必须读取任务文件、完成开发并提交代码、输出 `READY.json`。没有配置时，工具会生成任务并停止，不伪装成已开发完成。

```bash
./run.sh auto --pr 3453 --suite smoke --execute
```

它依次准备源码、调用你选择的开发器、重新执行指定单测、构建 base/candidate、冻结题集、串行运行 base/off/on、生成 JSON/CSV/Markdown 报告。**GPU 阶段还要求 `maintenance_confirmed=true`，且没有其他计算进程。** 生产服务由你在维护窗口自行安排停启，工具不会替你杀进程。

### AI 在现有终端中直接完成开发后

```bash
./run.sh build                 # 冻结 main 基线
./run.sh build --pr 3453       # 当前 PR 单独候选
./run.sh noise --suite smoke --execute
./run.sh run --pr 3453 --suite full --groups quality,tool,protocol,decode,cold-prefill,long-retrieval --execute
./run.sh scenario --pr 3453 --name java-agent --execute
```

Java 评分需要预先存在的本地 Docker JDK 镜像（29 目前没有，需用户离线准备，否则 Java 组为 NOT_RUN）：在 `local.json` 设置 `java_enabled=true` 和 `java_image`。脚本解析本地不可变 image ID，不自动拉取镜像。没有隔离环境，Java 项标记未执行，不在宿主机运行模型生成的代码。

## 三态与生产版本的关系

- `P`：实际部署快照（单独迁移对照，不混入 PR 收益）。
- `A0/base`：冻结 main 原版。
- `A1/off`：同一 PR 移植版本，完整功能关闭。
- `B/on`：同一候选编译产物，完整功能开启。

先证明 A1 没引入回归，再看 B 相对 A1。每个 PR 独立从同一 A0 起步。组合只在单项通过后进行。普通请求的顺序和内容固定；缓存场景中的追加与编辑也固定，不被前一次模型回答改变。

## 包含与不包含

已包含：11 个专项任务文档；82 个 full-suite 冻结请求的生成规则（其中 8 个 Java 单题）；21 个 smoke 请求；8 个有确定断言的 Java 任务；Java 工具循环与短请求抢占探针；128K 安全门；本地 HTTP/SSE 测试；配对统计；文件完整性清单。

未包含：本机 CUDA 编译结果、RTX4090 实测收益、用户真实 Pi 仓库的任务完成率、主线与所有 PR 的最终冲突解决。它们是下游 AI 在隔离 worktree 中必须完成并记录的验收项。当前包的真实测试记录见 **[VALIDATION.md](VALIDATION.md)**。

原生 GPU 编排目前只面向 Linux；WSL2 只有当 GPU PID/`/proc` 审计通过时才可运行。Windows PowerShell 入口可运行文档准备／CPU 测试，但没有声称原生 Windows GPU 生命周期编排已经实现。

# Kinetic：多源验证的成本模型有用，默认没跑树

来源：[main `f3723b1`](https://github.com/Veloresearch/kinetic/tree/f3723b1e046cc7e1d013de160402f58d819ab423)、[v0.1.0](https://github.com/Veloresearch/kinetic/releases/tag/v0.1.0)；[tag 对象](https://api.github.com/repos/Veloresearch/kinetic/git/tags/07bd36058861e904b20dcb85cd411226d7a6099a) 指 `c1a11c2fec64c5a4db89037265335938d4754acf`。#19 和 #23 是 main 的后续变更，不能算作 v0.1.0 已装包能力。
本机待绑定的新基线不能直接替换。历史目标是 Flash-Next GSQ-RCO IQ3_XXS 两分片，Xeon Silver 4216、Gen3 ×16，不是下文的 3060/P100、LFM/27B dense 或其他量化。

## RAD-1：从“有树代码”到“树值得跑”是两件事

1. [Server `drafter.rs`](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/crates/kinetic-server/src/drafter.rs#L43-L68) 组合 lookup、会话索引、可用时的模型预测块 MTP。工程意义在于同一轮可比较多个 source，而非每个模型都需要一件大 drafter。
2. [Ensemble](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/crates/kinetic-models/src/speculative/ensemble.rs#L6-L122) 合并共享 prefix、用各来源实际命中记分优先排序；同一个 token 前缀不重复预算。
3. [Decoder](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/crates/kinetic-models/src/speculative/mod.rs#L194-L312) 对分支评分、保存 state，沿 target policy 实际采出的路径前进，rollback 其他 score rows。收益比较是“期望可提交量 / 含 row cost 的时间”，不是 “proposals 数最多”。
4. 默认 `ROW_COST=f32::INFINITY` 明确关树，成本须针对模型和系统测；树无法评分时也退链。`score_tree` 在 [Target 默认](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/crates/kinetic-models/src/speculative/target.rs#L48-L88) 可拒绝；[CUDA adapter](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/crates/kinetic-models/src/cuda/target.rs) 未覆盖树评分。不要把有 CPU 测试支撑的代码，当成已打开的 4090 CUDA 快路径。
5. [Toy tests](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/crates/kinetic-models/src/speculative/tests.rs#L221-L293) 将 row cost 设为 0 才启用树，greedy/64 个 seeded cases 与 plain 等价，toy pass 数下降；[块单测](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/crates/kinetic-models/src/blocks/tree.rs#L120-L162) 检查树行与独立路径。两类测试都不是生产 Flash-Next 的吞吐测量；block drafters 仍列在 [roadmap](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/docs/roadmap.md)。

### 为什么只拿成本结构

- 树避免重复验证共同前缀，但额外分支行占用 attention、MLP/MoE、cache 构造和 rollback 资源。比单链多接受 token 仍可能增加 ms/committed token。
- 真实路径要维护 position、父行、attention mask，以及 recurrent/GDN 和 cache 的分支状态。Toy pass 数变少不会自动兑现这些工程成本。
- 当前上游 Strata 的线性窗口已有成本表。若实际 MTP/lookup 往往同意或只是前缀长短不同，树没有得到新增分支接受的机会。

## 性能：复写、普通生成和等待移走，要拆开看

| 报告 | 条件与口径 | 读数/反例 |
|---|---|---|
| LFM3 1.7B Q4_K_M | Ryzen 5 6600H、RTX 3060 Laptop 6GB，llama.cpp b12001；edit 为短文件改名复写、greedy、client 首至末输出，llama 有 `ngram-simple` | edit 229.7→1033.7 tok/s（4.5×）；不推测普通 generate 194.3→198.4（1.02×）；PP512 7642.7→6820.6（更慢） |
| Qwen3.5 4B Q4_K_M | 同机和格式，edit 对照启用 `draft-mtp` | edit 121.0→348.1；普通 76.4→89.9。8/32 层 GPU 的 5.1→13.3 是 dense layer offload，不是 MoE Flywheel |
| Zero Wait | 22631 tokens 粘贴再打字，RTX 3060 Laptop，TTFT 从回车计 | Kinetic 0.13s、未提前投递 13.07s、llama.cpp 10.95s。用户等得少，不等于模型吞吐 83× |

出处：[README benchmarks](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/README.md#L645-L670)、[zero-wait 定义](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/README.md#L251-L270)、[repro scripts](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/scripts/bench_vs_llamacpp.py)。[benchmark book](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/docs/src/benchmarks.md#L7-L84) 的若干结果仍为 TBD；不从表格推导 4090 Flash-Next。直接可确认的是脚本、测试与自报数字，不是目标硬件 trace。

## Flywheel：分派真实，但“命中率”不能直接拿来比

| 步骤 | 当前源码 | 需要修正的观测口径 |
|---|---|---|
| 每层按本轮每 expert 行数分配 | [place](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/crates/kinetic-models/src/cuda/experts/place.rs#L23-L118) 先保护 resident，cold 从行数高到低排序，以 host/copy 估时分去 Host、持久槽或短时 transit | 区分原有热命中、刚 admission、transit、host；装入新槽不算原已有 |
| 价格从微基准到 EMA | [offload cost](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/crates/kinetic-models/src/cuda/experts/offload.rs#L22-L66) 记录 host/load 估时、每 token 增量和实际 host slowdown EMA，host idle 时逐步松绑 | 估时和实际不能混：要分开 copy ready、前台 wait、CPU compute 与 RAM contention |
| 预取与统计 | [stats](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/crates/kinetic-models/src/cuda/experts/stats.rs#L3-L62) 跟踪 predicted、used、prefetched/loaded/host bytes；用到 pending slot 会同步 | `hits` 用最终 Place::Device，会含本层刚放进去的 experts；precision/recall 不等于 stall 减少；分开 late 与无用搬运 |

[示例](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/crates/kinetic-models/examples/flywheel.rs) 确实输出 offload plan、速率和流量；[device docs](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/docs/src/devices.md#L208-L231) 的 6GB 运行 12GB 类 MoE 主要是容量说明。已看到路由/数值 [CUDA tests](https://github.com/Veloresearch/kinetic/blob/f3723b1e046cc7e1d013de160402f58d819ab423/crates/kinetic-models/src/cuda/experts/tests.rs)，没有同用户 GPU/pack/上下文的 Flywheel 性能对照。

### 三个不可用的代理指标

| 代理值 | 为什么会误报 | 较好的判定 |
|---|---|---|
| “源 2 获得 90% 命中” | 未说明 source 是否与 source 1 同一序列，且未计 selection/verify 成本 | 实际用到且独立的提交增量和原本不需要验证的额外行 |
| “GPU hit 提升 15pp” | `Place::Device` 可以刚刚走了同步拷贝 | resident-before-demand 与 new-admit 分别记录；看需求就绪时间 |
| “复制吞吐接近 PCIe 峰值” | 与 CPU 共用内存控制器；不一定在依赖链上 | 实测独占和并行时 CPU/DMA BW、critical path wait，以及请求 p95 |

## 两个已实现但不进入主线的改动

- [#19 idle settle](https://github.com/Veloresearch/kinetic/pull/19)：其 CUDA decode 和 prompt 行归约不同，需要重放上一个回复才能兑现冷续聊一致。等待 250ms 后逐 64-token 块处理，被前台请求抢占；Qwen3.8-27B UD-Q6_K_XL 双 P100，300-token reply 后停 4 秒，后续首 token 1.68→0.42–0.47 秒，generation 81.6→82.2 秒重叠，PP 354→353。直接在回复后 settle 的原设计让 generation 慢 7–19%。Strata 若不存在同类重放，移植没有对象；只借“前台最坏被一块拖住”和 idle 条件的测量。
- [#23 分卡 MTP](https://github.com/Veloresearch/kinetic/pull/23)：模型层分到双 P100 时，不再完全禁用 prediction block，第一卡多约 0.7GB；同 27B Q6，story greedy 18.4→22.6，edit greedy 29.6→28.9（lookup 已有效）。单卡 Flash-Next 并不因此获得新 MTP 机制，不投入。

## 对 Strata 只加观测，不新增候选实现

[当前 DraftPolicy](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/src/spec/draft_policy.cpp#L577-L630) 已按成本、长度、上下文决定窗口，另有 MTP+lookup chaining；不重写或复制 Kinetic policy。各路线只要求以下反证：

- 既有 trace 同时有 MTP 和 lookup 提案时，离线记来源相同率、共享前缀、互斥分支有效行、相对现有链的 oracle 增量和实际 width/成本，避免同一支持量重复记为两个来源收益。
- 看 `window_cost`、row shape 与拒绝后 rollback/重算；如果 added branches 的理想增益都不能过门，不做 tree 实现，也不加生产 GPU 运行。
- 如需借 Flywheel 的口径，记 resident-before-demand、新 admission、cold host/copy、useful-ready/late/waste、CPU/DMA 互斥和 overlap、关键 wait；旧 CPU-gap 小的结论不得靠 donor 百分比推翻。
- idle 用前台 `arrival→start`、replay requested/completed/wasted、分块抢占上界归因，loader/rerun 占用不算 decode。

### 产出形态

- 多源只给一张「相对最佳现有链」的反事实表，分任务/上下文，不创建树候选。
- 放置只给 CPU/DMA/设备四类路径的可观测度与排队分解，current floor 不够就标 stay closed。
- 对比时同时保存 raw unit 与解释单位（ms/window、ms/committed token、MiB/committed token）；单条 peak tok/s 不能标为胜者。

仅当当前合同新增路径证据，且端到端收益机会至少 **4% 且超过 2× A/A 噪声**，再走独立提案。没有触发证据就结束，不重开 CPU/DMA、HC、预填调度或版本替换。采集/共用门槛见 [05_DATA_MODEL_AND_MEASUREMENT.md](05_DATA_MODEL_AND_MEASUREMENT.md)、[18_CANDIDATES_AND_STOP_RULES.md](18_CANDIDATES_AND_STOP_RULES.md)。

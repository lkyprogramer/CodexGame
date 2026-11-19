# 决策摘要：现在应优化什么，不应再追什么

## 1. 判断

这几套引擎的快，来自**权重格式、activation 数学、verify 几何、草稿成本、混合状态提交和特定负载**一起工作。它们不是同一个 GGUF、同一上下文和同一采样条件下给你现有实现打了个补丁。把最显眼的 tok/s 拆开，真正不改变你质量/容量合同、又没有重复旧实验的部分很少。

本轮两条值得形成执行准备规格：

- **D1：有来源位置记忆的复制/编辑草稿。**你的旧 H1 已经证明“请求内 lookup 命中”不等于加速；新增价值必须来自更准确的来源定位/编辑恢复，或确实少做被覆盖的神经草稿，而不是另一组 n-gram 参数。
- **H2：草稿头的粗筛＋精排。**它原本就在你的计划里。本轮找到可读的具体 donor，能把空泛“进一步裁 head”细化为可淘汰、可测的实现合同，但不能宣称发现新路线。

TensorFold 的分段投影值得查代码，却还缺 P3/当前部署的最终 dispatch；Strata 的 stop-bound 值得核版本，却是维护而不是新算法。

## 2. 对你的两条主线分别意味着什么

| 目标 | 最匹配的增量 | 最大障碍 | 本轮建议 |
|---|---|---|---|
| NInfer，Dense 27B，既有 MTP、裁剪草稿头、长上下文 | D1 / H2 条件接续；K-PAIR 源码核查 | 旧 H1/W6 失败；实际部署树未绑定；状态耦合与显存 | 不换 target；先 R0/R1，最多选一个机制实现 |
| Strata，Flash-Next MoE，保 MTP spec4 | 当前源码维护与归因证据完善 | CUDA 路径已有 suffix/DF2 skip/cost policy；旧 DF2 无净益；donor 多为 Dense | 不新增 DF2、宽窗或成本策略扫描；M0 单列维护 |
| 2–3 Agent 并发 | 旧 A2 的 cache-work、准入/公平性证据 | 并发是不同合同，不能从单流 copy 数字推出 | 本包不扩并发任务，沿旧基础包权限门 |

## 3. 一张表看“新”在哪里

| 机制 | 源码中确有 | 对你是否新 | 有无当前 4090 净益证据 |
|---|---|---|---|
| Anchor / cold-match / edit repair | OSAKANA copy planner | 相对旧 H1 有具体差量；全局 H7 早已计划 | 无 |
| Copy 命中跳过神经 proposal | OSAKANA ordered dispatcher；Strata 也已有 DF2 skip | NInfer 是否能省 mandatory MTP 待证明；Strata 非新 | 无 |
| Rank-512 sketch / shortlist / full-D rescore | YASAKANI，OSAKANA 也有对应资产 | 旧 H2 的实现细化；不是首次裁头 | 无 |
| 共输入多投影单 grid | TensorFold native CUDA | b0 有 small-T 异 dtype pair，但后续 P3 未绑定 | 无 |
| 终止输入行边界 | Strata HEAD CUDA 修复 | 上游已有、部署待核 | 无当前部署回归数据 |
| Trellis / A8 / KV5 / 64-row copy / PDL | donor 中有各自条件 | 换数学、格式、宽度或硬件合同；很多与旧路线重叠 | 不可用作者数字代替 |

## 4. 一个必须接受的收益上限约束

旧 H1 W4 的两个自然短窗已达到 3.880 / 3.944 正式 token 每轮。即便固定 W4 的命中全变完美，产出上升空间也仅约 **3.09% / 1.42%**；对应固定轮成本下每 token 耗时最多下降约 **3.00% / 1.40%**（未计 planner 新成本；精确值以原记录取整误差为准）。不能混用这两个分母。

所以 D1 若保持宽度，真正值得证伪的是**省下完整 round 的无效工作**，或者发现旧负载之外真实高价值 copy 任务；仅提高 acceptance 很可能不足。宽 W8/W16 已是旧规划，不能偷偷加进 D1 以制造大提升。

P14 的 proposal head＋AR 约 9.5% 是不同 P4/codec 合同的历史粗段。它既不是当前 head-only 占比，也不是 H2 可省 9.5% 的保证。Target 主体约 79% 说明内核探索仍有逻辑空间，但必须再分到真实热点；不能由这个粗比例指定一个新 kernel。

## 5. 最终采用标准

先通过身份/去重，再证明净成本机会；之后才是最小实现、状态/数值/服务资格、正式 observer-off 配对。任何一层失败都可以停止。没有可用候选时保留现有 NInfer/Strata、交付负结果，不为了消耗探索预算而移植整套引擎。

本摘要中的本地历史依据见 [历史台账](01_HISTORY_AND_NO_REPEAT.md)；新项目机制与固定来源见 [架构比较](03_DONOR_ARCHITECTURE.md) 和 [证据地图](02_EVIDENCE_AND_SOURCE_MAP.md)。

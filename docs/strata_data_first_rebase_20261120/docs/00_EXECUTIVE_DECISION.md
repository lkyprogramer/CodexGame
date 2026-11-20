# 00｜结论：先闭合证据链，再决定是否还值得改 kernel

## 1. 本轮明确决定

**以最新稳定 Strata 建立独立研究基线是合理的；现在没有足够证据直接批准某一条新的 4090 算法优化。** 最优先的工作是迁移现有观测能力、补足最少的事件关联与语义，再用真实数据筛掉低空间方向。

这不是重新推翻此前停止探索的决定。那个决定仍约束原冻结合同；本轮新增了原生 engine 重构与用户最新多会话归档，所以值得建立**新版本、可解释的测量基线**，而不是重复跑旧旋钮组合。

## 2. 三项事实改变了计划

| 新核实事实 | 对本轮的约束 |
|---|---|
| CodexGame 最新为 c5f05b46；11/18 130K 多会话测试是 Dense 27B NInfer/HyperQwen | 父前缀保留、工具/模板变化、排队必须可观测；不能把 Dense tok/s、6GiB KV 结论外推给 Strata |
| Strata App/Terminal 0.2.16，Engine/Control 0.1.62，source 迁入 engine/terminal | 旧 patch 路径、解析器和 env 含义都要重验；原生实现也可能已吸收 donor 优化 |
| O0–O6、E0–E4、R0–R4 大部分仍是计划；旧单测是 CPU/合成夹具 | 不能把“原包完整”理解成已装全链路观测；先复用真代码，再补最小缺口 |

固定证据见 [01](01_BASELINE_AND_HISTORY.md)、[03](03_EXISTING_ASSETS_AND_REBASE.md) 和 [source lock](../evidence/source_lock.json)。本轮不声称旧 private raw 均可获取，更没有重算用户未上传的硬件 trace。

## 3. 最新 metrics 够不够

**做健康与概况监控基本够；做 kernel/缓存/推测策略的因果比较还不够。**

- 已有：请求状态与摘要、queue/active slot、逻辑 prefix reuse、prefill/decode 总数、部分 native 周期与批次、内存/缓存概况。
- 主要缺口：用户任务→HTTP请求→native leg/slot/round 的持久关联；真实 token commit 与 SSE delivery 的不同时间；cache owner/tier/恢复/重算链；expert “ready命中”与“刚入驻还在搬运”；实际 dispatch/逻辑行与物理填充；CPU/GPU/DMA 重叠依赖。
- 容易误用：Prometheus ITL 由每请求均值重复累加，不是真实逐 token P95；`reused` 不证明物理驻留；服务阶段 `admitted` 在串行/parallel 分支含义不同；polling 的 receipt 时间不是事件发生时间。
- 需要改造：**需要，但先改 Lab 适配器和低频结构事件，不做全量 kernel tracing 常开。**

详见 [04](04_STRATA_METRICS_AUDIT.md)、[05](05_DATA_MODEL_AND_MEASUREMENT.md)、[06](06_MINIMAL_INSTRUMENTATION.md)。

## 4. 六个来源的真正价值

| 来源 | 借鉴重点 | 本轮准入 |
|---|---|---|
| QuixiInfer | fresh/busy/position 分层，提交与预取成本台账，反例保留 | 测量方法；不搬 sm120/DeepSeek 引擎或重试旧 HC |
| Kinetic | proposal source / ready-hit / pending-copy / CPU-DMA 成本分开 | 指标定义；树默认仍是 chain，不立多分支大工程 |
| Speedy | 同会话 8-gram 找回 trigram 4-way 桶丢失的旧匹配 | C01 离线反事实；近似 defer-CPU 明确排除 |
| FlashInfer | shape signature、调优 provenance、coverage/fallback、参考测试 | 数据契约；QSA接口须先过架构/布局/KV匹配，不换格式凑支持 |
| Blink 2604.07609 | host control、expert CPU、网络排队分开，completion ownership | 可观测设计；DPU/全GPU调度/常驻大内核不纳入 |
| PolyStrata | 实际 MoE 行分布/物理padding、功能必须绑定正确子引擎 | C02 census；NVIDIA归约重排路径不准直接移植 |

这批来源里最可能省下时间的是**更早识别没有空间或比较口径不成立的实验**。不承诺“换最新版就加速”，也不把任何作者 5090 / 双卡 / 小模型数字当作你的收益预期。

## 5. 建议的路线

~~~mermaid
flowchart TD
    A["P0 固定身份与旧结论"] --> B["P1 复用采集与离线校验"]
    B --> C["P2.0 复用或有限 L0"]
    C --> J{"缺决策必要字段"}
    J -->|是| K["P2 仅补对应挂点"]
    J -->|否| D["P3 新基线与缺口报告"]
    K --> D
    D --> E{"存在可闭合的净收益空间"}
    E -->|否| F["归档 NO_GAIN 或 INSUFFICIENT"]
    E -->|是| G["P4 单项反事实"]
    G --> H{"满足机制与质量门"}
    H -->|否| F
    H -->|是| I["P5 独立AA资格后单候选"]
~~~

现在应把主要精力投在 P0–P3。C01/C02 只是在数据到位后进入 P4 的两个问题，不是优先批准两组 GPU A/B。

L0足够就不改engine；没有当前原件或采集权限就停在缺口报告，不能反过来先造全量监控框架。所选L1挂点另行校准，同版本但不同source/build不能混成off/on。

## 6. 交付定义

本轮文档完成标准是：来源可复查、历史不改写、字段与代码挂点明确、Phase/Task/负测/预算一致、无假命令与“已部署”措辞。**生产收益、源码改造和 4090 性能验证不属于这次文档生成已经完成的事项。**


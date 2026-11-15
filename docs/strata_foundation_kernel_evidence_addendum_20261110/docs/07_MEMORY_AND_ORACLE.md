# 07 · 内存生命周期与独立小算子 oracle

新增能力状态：**PLANNED**。这里只规划离线证据合同与小夹具，不提供可调用产品。默认 GPU 预算为 **0**，没有模型启动、GPU 测试、容量扫描或代码改造；不改变现有 placement、cache 容量、MTP 配置，也不重开 F01、F03、adaptive tail。

## 不是从零设计缓存

Strata 已有分页缓存、混合 attention/GDN 状态和 MTP。固定源码 `504b143342a9fe1aa8320a7b31e11f5c0ac265c3` 的 [`state_pieces`][state]分别处理 QSA ring、GDN 递归矩阵、卷积历史、PLE 历史、MTP ring 与 KV 页；[`mtp_attach`][mtp]已有 draft 层缓存和 scratch。这里只补充审阅契约，不另造分配器或会话快照。

samir-vllm 的一层页大小为 `2 × 16 × 512 × 2` 字节，全部 16 层每 token KV 恰好也是 32 KiB；相同数值代表不同对象。[原结构][samir]只适用于固定 Llama/BF16，不能套到 Strata 混合层、量化 KV、QSA index 或 MTP。目标模型继续沿用原冻结的 Qwen3.8 FlashNext GSQ-RCO IQ3_XXS 混合张量合同，不能把部分张量的 IQ3_S/TG21 证据写成整模型精度。

## 生命周期不变量：仅补充记录

以下记录及检查均为 PLANNED，应绑定现有 manifest、状态导出与证据接口，不意味着现场已有新校验器。

1. **身份与有效范围。** 每对象记录 run/request/session、层或状态种类、逻辑位置、allocation generation、dtype、shape/stride、有效区间及来源。相同地址不等于相同对象；未知 MTP 范围不能按整块已定义内存比较。
2. **所有权与最后消费者。** KV、GDN、MTP 持久状态与临时 activation 分列。scratch 覆盖前必须能说明最后一次读取何时完成；CPU 返回、事件入队和 graph capture 均不能替代 device completion。
3. **提交边界。** 区分已预测、已计算、已接受和已提交 token。拒绝草稿、取消、恢复、slot 复用不能留下跨请求可见状态；GDN history、KV/index 与 MTP 有效域须按现有 commit/rollback 语义核对。
4. **别名与 graph 生命周期。** 同一 buffer 多用途必须列出互斥区间、stream/event 依赖和 capture/replay generation。指针仍存活不证明数据仍属于原 session；不能照搬顺序教学引擎的 alias。
5. **预算不等于测量。** 区分容量、有效 payload、已分配页、scratch 峰值、host/pinned staging 和保留额，引用原件而非相加重复统计。缺失峰值记 UNKNOWN；不得据此自动缩容或改 placement。

例如，一份旧快照能说明某个有效区间的内容，却不能证明随后异步消费者已经结束，也不能代表拒绝草稿之后的状态。审阅时应把原件的时间点、所属会话和可比较区间一起保留；没有完成证据就不宣称可释放。这里是对既有证明的字段检查单，不因字段未知自动开启泄漏排查、重做快照方案或追加运行预算。

## 独立 CPU reference 小夹具

夹具规范为 PLANNED；本轮不创建或运行实现。复用已有离线测试、严格输入与证据输出约定；不新增 runner、benchmark 或另一套质量 gate。

基础样例限定为少量 token/head 的可手工检查输入，覆盖 row-major 投影、RMSNorm、RoPE 和带显式 mask 的 attention。reference 采用独立标量公式及 FP64 中间值，单独定义 BF16 舍入与输出比较阶段；不得调用候选 kernel、直接复制其索引逻辑，或把候选输出来生成 golden。页映射用极小逻辑数组模拟，不加载模型、不接触 CUDA。

冻结输入、实现版本、输出形状、容差、比较量及负控制。至少包括页边界、不同长度、乱序物理页、无效映射、错误 head/position、NaN/Inf、近似相等 logits；必须验证故意错一处时会失败。报告最大绝对/相对误差和首个偏差位置；空样例、未执行与缺失 golden 不能生成 PASS。精确相等的 tie-break 与近似相等造成的 argmax 分叉分开判断。

独立性由算法和数据来源保证，不由“另一个进程”或“另一个评审者”的名字保证。预期结果不能随候选输出调整，容差不能在看到失败后放宽；若两边共用同一映射代码，应标注共同失效风险，而不是宣称双重验证。

## 资格上限与已有接口

小夹具只验证局部算子公式、布局与边界。它不证明真实量化张量路径、GDN 长历史、MTP 回滚、128K 会话恢复、服务质量或 4090 性能；通过后这些轴仍为 NOT_EVALUATED。

已有 [`compare_session.py`][session]受冻结 SAVE 版本与有效状态域约束，不是跨版本万能 oracle；缺范围或格式不符应 BLOCKED，不能自行重新采集。实际数值/状态证据继续依照 [06 数值护栏](06_NUMERICAL_GUARD.md)，按当前改动作用域复用既有工具。本页不得把局部 CPU PASS 升级为长上下文状态质量通过或新 GPU 任务许可。

[state]: https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/src/split/src/engine.cu#L877-L895
[mtp]: https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/src/split/src/engine.cu#L1249-L1269
[samir]: https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/src/main.cpp#L320-L418
[session]: https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/strata_4090_128k_lab/tools/oracle_replay/compare_session.py

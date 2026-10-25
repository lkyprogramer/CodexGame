# 用户提供的分析原文

> 输入材料，不是本次核验结论。渲染残留按原文保存，不作为代码执行。

# DFlash2 在 100K–256K 长上下文下，如何保持高速推理？

结论：不能只靠增加 DFlash2 的预测 Token 数量解决。真正有效的方向是「稀疏上下文草稿生成 + 完整上下文验证 + 动态推测策略」。

对于你的单张 RTX 4090、Qwen3.8-27B，以及已经支持 262K 上下文的 NInfer，我建议采用：

DFlash2 + Selective Draft KV + Adaptive Speculative Decoding + NInfer ReplaySSM。

这里有个关键区别：DFlash2 在 100K 以后变慢，并不意味着它的预测能力一定失效。实际上，长上下文下至少存在三类不同的瓶颈：

1. Draft 变慢：DFlash2 读取历史上下文的成本增加，或者有限的局部窗口无法获取真正相关的历史信息。
2. Target Verify 变慢：Qwen3.8-27B 每轮仍需要验证候选 Token，Full Attention 的 KV 访问成本随上下文增加。
3. 推测效率下降：长上下文下正确候选变少，或者为了得到更多正确 Token，需要验证太多无效分支。

这三种情况需要不同的解决方法。仅优化 DFlash2 的 CUDA Kernel，不能自动解决 Target Verify 的内存带宽瓶颈。

而且，查到的公开测试表明，100K 不是 DFlash2 的固定性能拐点，实现方式和 KV 配置的影响很大。

## 一、实际长上下文测试说明了什么？

有两组值得关注的社区实测：

| 测试环境                           | 上下文         | 无推测         | DFlash2     | 加速比             |
| ------------------------------ | ----------- | ----------- | ----------- | --------------- |
| RTX 3090，llama.cpp，Qwen3.8-27B | 128K / 160K | 33.16 tok/s | 59.88 tok/s | 约 1.81×，不同上下文长度 |
| AMD R9700，SGLang               | 129K        | 13.81 tok/s | 20.54 tok/s | 1.49×           |

第一组使用 Q4 Target + Q8 Drafter，作者发现 4–5 个草稿 Token 往往比 7 个更有效。第一组的两个性能数据也不是严格同一上下文长度，不能视为正式 A/B 结果。

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



第二组虽然 Decode 快了约 49%，但完整冷启动 Prefill 需要约 467 秒，因此 256 Token 输出的总请求时间仅缩短约 0.64%。

[image](https://www.google.com/s2/favicons?domain=https://lcz.me\&sz=32)

抡锤者



这说明：

- 长上下文下 DFlash2 仍然可能显著提高 Decode 性能。
- 但 Decode 加速与完整请求加速是两回事。
- 对于 Coding Agent，真正应该优化的是多轮会话的累计耗时，而不是单个基准测试中的峰值 tok/s。

后面重点讨论如何分别突破这些瓶颈，以及怎样利用你 NInfer 现有的 E8 KV Cache 和 ReplaySSM 实现。

## 二、我在 tqLLM 源码中发现的关键问题

这部分比一般的 DFlash2 原理分析更重要，因为它直接决定能否优化 100K–256K。

### 1. `--draft-retrieve` 并没有真正覆盖全部远端上下文

代码位置：

- [`src/qwen35.cpp`](https://github.com/turbo-tan/tqllm/blob/main/src/qwen35.cpp#L2958-L3019)[ L2958–3019](https://github.com/turbo-tan/tqllm/blob/main/src/qwen35.cpp#L2958-L3019)
- [`kernels/qwen35.cu`](https://github.com/turbo-tan/tqllm/blob/main/kernels/qwen35.cu#L976-L1085)[ L976–1085](https://github.com/turbo-tan/tqllm/blob/main/kernels/qwen35.cu#L976-L1085)

源码实现的基本方式是：从历史 Drafter KV 中选取相关片段，拼接到最近上下文之前，再执行草稿 Attention。

但它有一个硬上限：

```
constexpr int RCHUNK = 16;

const int n = std::min(nc, 4096);
const int first = nc - n;
```

换句话说：

每次检索最多覆盖 4096 × 16 = 65,536 个远端候选 Token。

举例来说，如果当前上下文有 256K Token，并且近期窗口约为 1.5K，那么这套实现只能在最近约 65K 的远端候选区域中寻找重要片段。

真正位于上下文开头的系统约束、函数定义、架构决策等，可能根本进不了它的检索范围。

对于长期 Coding Agent，这是明显的局限。

### 2. 开启远端检索会显著增加显存占用

tqLLM 的普通 DFlash2 使用 Sliding Window Ring Buffer；启用检索后，源码直接执行：

```
if (dfl.retr) {
    dfl.ring = 0;
}
```

随后通过完整上下文长度分配 Drafter KV，而不是只分配窗口长度。

根据项目说明，完整 Drafter KV 大约需要每 Token 20 KiB：

| 上下文  | 完整 Drafter KV 估算 |
| ---- | ---------------- |
| 32K  | 0.625 GiB        |
| 64K  | 1.25 GiB         |
| 128K | 2.5 GiB          |
| 256K | 5.0 GiB          |

这是估算的 Drafter KV 数据量，还不包括草稿权重、Target、Scratch Buffer 和 CUDA Graph。

你的 RTX 4090 只有 24 GB。NInfer 目前已经能把官方约 16.96 GiB 权重和完整 262K E8 KV 放入显存，README 给出的剩余空间约为 1.37 GiB。

因此，照搬 tqLLM 的完整 Drafter KV 检索方式，在保留 NInfer 当前 262K 配置的前提下，显存预算明显不成立。

### 3. 更隐蔽的是 CUDA Graph 快速路径会被关闭

tqLLM 在 `src/qwen35.cpp` 中有这样的条件：

```
const bool graph = dfl.ring > 0 && !subset;
```

开启 `--draft-retrieve` 时，`dfl.ring` 被设置为 0，因此常规单路 Draft CUDA Graph 捕获条件不再成立。

此外，`dflash_draft_batch()` 的快速路径也会拒绝 `dfl.ring <= 0` 的情况。

这意味着当前检索方案实际上存在三项成本：

- 每轮都要选择远端相关 KV 片段。
- 存储完整的历史 Drafter KV。
- 失去原有的一部分 CUDA Graph 与批量 Draft 优化。

尤其是它的选择过程会对每个草稿 Attention 层的候选 K 进行打分，并执行 Top-K 排序。长上下文下，这可能抵消检索提升接受率带来的收益。

这解释了为什么 tqLLM 官方只报告了 `--draft-retrieve 32` 在约 31K–51K Prompt 下的 8%–12% 解码增益，而不能据此推断它在 128K、256K 也一定有效。

所以，直接把 `--draft-retrieve` 从 32 调到 64 或 128，不是我建议的解决办法。

## 三、最值得采用的方案：Hierarchical Selective Drafting

我建议把 DFlash2 的远端检索改造成两级结构。

完整 128K / 256K 上下文

NInfer 保留完整 Target KV、GDN 和前缀状态

一级粗检索

全局 Page 摘要索引

1024 个页以内

二级精检索

Top-K 相关 KV Chunk

动态选择远端片段

DFlash2 有界草稿上下文

Recent

1–2K

Retrieved

256–1K

Anchors

动态预算

具体预算需按显存、接受率与周期延迟调优

DFlash2 Draft → NInfer Target Verify

Target 继续使用完整上下文验证，ReplaySSM 只提交接受的状态

### 第一层：Global Page Index

假设将 256K Token 按 256 Token 分页，只需要建立 1024 个逻辑页的摘要。

每页可以保留少量代表性 Key、Token 范围、重要性统计和必要的位置信息。

在 Prefill 阶段增量构建索引，后续请求只维护受影响的页面。

这样，草稿生成时不必每次读取最近 65K 的完整候选 K，而可以先在全局摘要上选择几十个最相关的页，再进一步细分。

这一步的优势是：检索范围覆盖整个 256K，但查询工作量不必随完整上下文线性增加。

### 第二层：Target-guided Retrieval

可以进一步借鉴 SpecExtend 的 Cross-model Retrieval 思路。

它不是单纯依靠 Drafter 自己判断什么历史内容相关，而是使用 Target Attention 的信息，帮助 Drafter 选择历史 KV。

例如一次 Coding Agent 请求正在修改某个 Java Service：

- 最近对话属于 Recency Window。
- 系统约束、当前任务定义属于 Anchors。
- 之前出现的 Service 接口、相关 Repository、DTO、测试断言属于 Retrieved Context。
- 其他不相关的日志和文件内容不必在每一轮草稿生成中反复参与 Attention。

注意：Qwen3.8 是 Hybrid 模型，不能直接把 Gated DeltaNet 的状态当作 Attention Score。可以从少量 Full Attention 层提取或汇总重要性，也可以采用更便宜的页级代理评分。

同时，不应每轮把完整 Attention Matrix 拷回 CPU，否则检索本身就可能成为新的瓶颈。

SpecExtend 已证明，利用 Target Attention 改善草稿上下文是一条可行的研究路线，但其公开实验模型和上下文规模与 Qwen3.8-27B 的 256K 场景不同，效果必须重新实测。

[image](https://www.google.com/s2/favicons?domain=https://aclanthology.org\&sz=32)

ACL Anthology

+1



### 第三层：保留 CUDA Graph 和有界 KV

这其实是我认为最关键的工程改造：

把原来的“完整 Drafter KV + 每轮扫描”改成：

固定大小的 Recent Ring + 选中页的 KV Staging + GPU 常驻摘要索引。

远端 KV 可以压缩存储，必要时从你已有的 L2 Host Cache 调入；GPU 上只常驻当前真正参与 Draft 的少量页面。

与此同时，让检索输出固定形状的 Staging Buffer，使后续 Attention Kernel 能继续被 CUDA Graph 捕获。

需要保证 Top-K、Gather、位置映射及缓冲区指针满足 Graph Replay 的约束，不能简单地认为换成 Paged KV 就会自动恢复性能。

这项方案的理论优势非常明确：Drafter 的历史状态预算由一个固定的检索窗口控制，不再要求随着会话从 32K 增长到 256K 而持续占用更多 GPU 显存。

它与 LongSpec 提出的恒定规模 Draft KV 思路一致。

[image](https://www.google.com/s2/favicons?domain=https://aclanthology.org\&sz=32)

ACL Anthology

+1



需要强调：Drafter 只看部分上下文不等于丢掉 Target 的上下文。只要最终仍执行正确的完整 Target Verification 和接受/拒绝算法，就可以保持相对于同一个 Target 基线的输出语义；对于随机采样，还需要严格处理真实的草稿提议概率。

## 四、再解决 Target Verify 随上下文增长而变慢的问题

仅优化 Draft 还不够，因为即使 DFlash2 每轮都能预测 5 个正确 Token，Target Verification 仍需要读取历史 KV。

按照你 NInfer 中 Qwen3.8-27B 的模型配置：

- Full Attention：16 层
- KV Heads：4
- Head Dimension：256

如果使用 BF16，每个历史 Token 所需的 Attention KV 数据量约为：

\\[ 16\times4\times256\times2(K,V)\times2\text{ bytes} =64\text{ KiB} \\]

于是：

| 上下文  | BF16 KV 理论数据量 | 4-bit KV 理论数据量 |
| ---- | ------------- | -------------- |
| 64K  | 4 GiB         | 1 GiB          |
| 128K | 8 GiB         | 2 GiB          |
| 256K | 16 GiB        | 4 GiB          |

这些是原始元素位宽换算，不包含 E8 编码元数据、页表及工作区。

RTX 4090 的显存理论带宽约为 1,008 GB/s。即使是 4-bit KV，256K 时每轮完整扫描历史 KV，仍然有数毫秒级的理想带宽下限，实际还需要解码、Attention 计算和同步。

[image](https://www.google.com/s2/favicons?domain=https://memorybandwidth.dev\&sz=32)

Memory Bandwidth Explorer



不过，你的 NInfer 已经有相当多的相关优化。

我检查了 [`gqa_attention_decode_i8.cuh`](https://github.com/lkyprogramer/ninfer-4090/blob/b0-scanner/src/ops/kernel/gqa_attention_decode_i8.cuh)，发现它已经实现：

- Split-KV Attention
- E8 Lattice 解码
- K/V 异步 Staging
- Producer/Consumer Warp 分工
- QK、Online Softmax 与 PV 的流水执行
- 多个验证 Token 共享 KV Tile 的专用路径

因此，不应该简单地再提出“给 NInfer 加 FlashAttention”这样的泛化建议。

更值得做的是分析 128K、256K 下 E8 Attention 的实际 Kernel Timeline，判断是否存在 KV 读取没有充分复用、寄存器压力或 Split 数量失衡的问题。

这里可以参考 2026 年 ICML 的 Dustin：它利用草稿信息和历史 Attention 重要性优化长上下文验证，减少不必要的 KV 访问。论文在其他模型和数据集上报告了显著的速度改善。

[image](https://www.google.com/s2/favicons?domain=https://proceedings.mlr.press\&sz=32)

proceedings.mlr.press



但 Dustin 的稀疏验证不能直接等同于严格完整验证。我建议你第一阶段不要裁剪 Target 的完整 KV，而是先把稀疏访问用于 Drafter。只有当 Profile 证明 Target Attention 是绝对主瓶颈时，再研究带有精确回退机制的 Target 优化。

## 五、第二个高性价比办法：动态选择 DFlash2 / MTP / Lookup

对于长上下文，我不建议固定使用 DFlash2 7-token Draft。

在 RTX 3090 的独立测试中，DFlash2 的 `n_max=4–5` 比 `n_max=7` 更合适；原因不是 7-token 接受数量一定更少，而是额外验证成本可能高于多提交 Token 的收益。

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



这与你的 NInfer 现有算子有个很好的契合点。

当前 [`gqa_attention_decode_i8.cuh`](https://github.com/lkyprogramer/ninfer-4090/blob/b0-scanner/src/ops/kernel/gqa_attention_decode_i8.cuh) 的专用 Token Tile 支持 1–6，而通常 K 个草稿 Token 需要 K+1 个 Target Verify 输入。

因此，先让 Qwen3.8-27B 的 DFlash2 使用 4 或 5 个草稿 Token，可以复用现有的 5/6 列验证 Kernel。

如果直接上 7 个草稿，反而可能需要扩展算子和 CUDA Graph Profile，增加研发成本。

### 建议的动态策略

| 场景               | 首选候选方案             | 原因                  |
| ---------------- | ------------------ | ------------------- |
| 短 Prompt，高预测接受率  | DFlash2，K=5 或 7    | 尽量摊薄 Target Forward |
| 64K–128K         | DFlash2，K=4 或 5    | 平衡预测收益和验证成本         |
| 128K–256K，远端引用很多 | Selective DFlash2  | 避免局部窗口缺失关键信息        |
| 128K–256K，短输出    | MTP 或无推测           | 避免复杂 Draft 初始化开销    |
| 代码重复、工具日志重复      | Prompt Lookup + 验证 | 历史内容可以直接提供草稿        |

这些是实验初值，不是固定的最优阈值。最终应由真实请求的延迟与接受率决定。

例如，运行时可以维护每种策略的移动平均性能：

```
struct SpecStats {
    double accepted_per_round;
    double draft_ms;
    double verify_ms;
    double commit_ms;
};

double effective_tps(const SpecStats& s) {
    const double round_ms =
        s.draft_ms + s.verify_ms + s.commit_ms;

    return round_ms > 0
        ? s.accepted_per_round * 1000.0 / round_ms
        : 0.0;
}
```

关键不是始终选择接受率最高的策略，而是选择单位时间实际提交最多 Token 的策略。

切换 MTP 和 DFlash2 时还需要特别注意状态管理：如果新 Drafter 的历史状态尚未初始化，不能无成本地在任意 Token 边界切换。第一版建议只在请求或回合边界切换，待两套状态能够同时维护后，再实现轮内动态切换。

## 六、结合 NInfer，我会怎么安排开发优先级？

P0 — 先补充分阶段性能观测

分离 Draft Attention、Retrieval、Target Attention、GDN、Commit 耗时，同时记录每轮接受 Token 数、CUDA Graph 命中情况和显存峰值。

目标是确定 100K 后究竟是谁成为瓶颈。没有这个数据，就容易优化错误的 Kernel。

P1 — 实现低成本的动态 Draft Width

先跑 K=3、4、5 对照测试。对 NInfer 来说，这能避免在第一阶段扩展超过 6 列的验证路径。

对比 MTP3 和 DFlash2，找到真正的长上下文收益区间。

P2 — 建立 Selective Draft KV

将全局 Page Index、远端 KV Chunk Retrieval、Recent Window 和固定 GPU Staging 结合起来。

优先验证 128K 和 256K 场景，并对比全局检索是否比 tqLLM 当前的最近 65K 检索更有利于 Agent 任务。

P3 — 恢复 CUDA Graph Fast Path

为选择、Gather 和 Draft 建立固定 Shape 的 Graph，并尝试多轮复用已经选择的远端 KV。

这一步要重点衡量 Retrieval Refresh 的频率与代价。

P4 — 视结果决定是否训练 Long-context Drafter

如果完成高效检索后仍然出现明显的第一候选准确率下降，才考虑利用长上下文数据训练专用 Drafter。

这是收益可能很高、但成本和不确定性也最高的一步。

### 验收门槛建议

不要预先承诺 128K 或 256K 能达到多少 tok/s。建议定义下面这些工程门槛：

| 指标          | 建议验收要求                           |
| ----------- | -------------------------------- |
| 128K Decode | 相比你当前 NInfer MTP3 提升至少 15%，才值得迁移 |
| 256K Decode | 优先保证无性能回退，再争取超过 15%              |
| TTFT        | 热缓存请求不能因 Draft 初始化明显退化           |
| GPU 显存      | 单卡 24 GB 内完成目标上下文，不依赖不可控的显存交换    |
| 正确性         | 同 Target、同采样设置下通过推测一致性测试         |
| Agent 质量    | 长时间任务成功率、Tool Call 正确性不得明显下降     |

这些是我建议的立项门槛，不是已经验证的优化收益。

## 七、最后的技术判断

你提出的问题，本质上并不是 DFlash2 的并行生成思想有缺陷，而是：

它把生成草稿的顺序成本降下来了，但在超长上下文里，仍然需要解决草稿模型的上下文表示成本、远端信息检索能力，以及完整 Target Verification 的成本。

我认为最值得借鉴的研究路线是：

| 研究                                                       | 可借鉴内容                                    | 对 NInfer 的适用价值 |
| -------------------------------------------------------- | ---------------------------------------- | -------------- |
| [LongSpec](https://github.com/sail-sg/LongSpec)          | 恒定规模 Draft KV、长短上下文位置适配                  | 非常高            |
| [SpecExtend](https://github.com/jycha98/SpecExtend)      | Target-guided KV Retrieval               | 非常高            |
| [Dustin](https://proceedings.mlr.press/v306/lee26d.html) | 长上下文稀疏验证                                 | 中高，需要正确性验证     |
| [tqLLM](https://github.com/turbo-tan/tqllm)              | DFlash2 CUDA Kernel、Token Tree、动态 MTP 切换 | 高              |

在你的设备条件下，我更倾向于以下路线：

保留 NInfer 的 262K E8 KV、ReplaySSM 和 L1/L2/L3 Continuation Cache；把 DFlash2 改造成固定显存预算、支持全局检索的 Drafter，并增加动态 MTP / DFlash2 调度。

这比单纯扩展 DFlash2 的 Context Window 更有技术价值。

如果这个方案成功，最终目标不是让 DFlash2 在 256K 上依然看到全部历史，而是让它只读取少量高价值历史状态，却能预测出与完整上下文 Target 尽可能一致的 Token。真正完整的历史始终交由 NInfer Target 负责验证。

# 用户提供的分析原文

> 输入材料，不是本次核验结论。渲染残留按原文保存，不作为代码执行。

# HyperQwen 深度分析：RTX 3090 的 381 tok/s 从哪里来？

对比 HyperQwen、tqLLM 与你的 NInfer-4090/b0-scanner｜截至 2026 年 10 月 19 日

## 一、先给结论

HyperQwen 的 381 tok/s 是真实项目公布的专项性能成绩，但不是 Qwen3.8-27B 的常规推理速度。

它真正的创新，是把 DFlash2 与 Prompt Lookup 组合起来，允许草稿模型只预测 7 个 Token，却让主模型一次验证最多 16 个位置。

当模型正在复述已有文档、复制代码、生成 Patch，或重复上下文中的内容时，额外的候选 Token 可以直接从 Prompt 中取得，不需要再运行一个草稿模型。

这才是 381 tok/s 的核心原因，而不是它实现了一个比 NInfer 快数倍的矩阵乘法内核。

普通单请求对话

# 127 tok/s

HyperQwen RTX 3090，默认单用户模式

文档复述场景

# 381 tok/s

16-token Verify，约 25K Prompt

作者也明确承认，在普通非复述任务中，长上下文 DFlash2 可能只有 MTP 约一半的速度，并且 TTFT 更高。

还有两个非常重要的事实：

- [HyperQwen](https://github.com/syv-ai/HyperQwen?utm_source=chatgpt.com) 和你贴出的旧仓库 `syv-ai/qwen38-27b-rtx3090` 实际上是同一个已重命名的项目。
- HyperQwen 不是完全从零编写的推理引擎。它是以 vLLM 为底座，加上一系列量化、Kernel、调度、Speculative Decoding 和 KV Cache 补丁。当前仓库已升级到 vLLM 0.31.0，因此比你引用的早期 Reddit 帖子又有一些新优化。

### 三个项目的根本区别

| 项目                                                                                                   | 核心技术路线                                      | 最值得关注的优势                    |
| ---------------------------------------------------------------------------------------------------- | ------------------------------------------- | --------------------------- |
| [HyperQwen](https://github.com/syv-ai/HyperQwen?utm_source=chatgpt.com)                              | vLLM + W4A8 + MTP/DFlash2 + Lookup + KV 优化  | Prompt 复述加速、多并发、成熟调度        |
| [tqLLM](https://github.com/turbo-tan/tqllm?utm_source=chatgpt.com)                                   | 原生 C++/CUDA + TQ3/TQ4 + DFlash2 Tree Verify | 专用低位权重算子、树形推测验证             |
| [你的 NInfer-4090](https://github.com/lkyprogramer/ninfer-4090/tree/b0-scanner?utm_source=chatgpt.com) | 原生 C++/CUDA + 专用算子 + ReplaySSM + E8 KV      | 262K 长上下文、完整状态恢复、Agent 缓存复用 |

对你来说，HyperQwen 最值得吸收的并不是它的整套 vLLM 架构，而是 Hybrid Lookup Drafting、可扩展 Verify Block，以及针对长上下文的 Attention Kernel 优化。

尤其是前两项，它们可能比继续单纯优化 DFlash2 的预测模型更有价值。

来源：[HyperQwen README](https://github.com/syv-ai/HyperQwen?utm_source=chatgpt.com)、[优化记录](https://github.com/syv-ai/HyperQwen/blob/main/docs/optimizations.md?utm_source=chatgpt.com)、[Reddit 原帖](https://www.reddit.com/r/LocalLLaMA/comments/1vtup5s/i_pushed_qwen3827b_to_381_tps_for_a_single/?utm_source=chatgpt.com)。

## 二、381 tok/s 的数学原理：每轮计算更慢，但生成效率更高

最能说明问题的是 HyperQwen 仓库里的同条件对照实验。

HyperQwen 不同任务的 Decode 性能

RTX 3090，25K 文档相关任务及短对话；数字来自项目自己的实验，单位 tok/s

DFlash2，无 Lookup

DFlash2 + Lookup，8列验证

DFlash2 + Lookup，16列验证

0150300450原文复述保留命令改写引用并解释自由摘要普通短对话

图表说明了它的加速具有极强的工作负载相关性。原文复述加速巨大，但自由摘要几乎没有收益。

### 精确拆解 381 tok/s

| 指标         | 无 Lookup | Lookup + 8 列验证 | Lookup + 16 列验证 |
| ---------- | -------- | -------------- | --------------- |
| 每轮有效 Token | 4.72     | 7.83           | 14.97           |
| Decode 吞吐  | 159      | 260            | 381 tok/s       |
| 每轮平均耗时（反推） | 29.7 ms  | 30.1 ms        | 39.3 ms         |

从 260 提升到 381 tok/s 时：

- 每轮提交的 Token 数增加了约 91%。
- 每轮计算时间增加了约 30%。
- 最终吞吐提升约 46.5%。

公式非常直接：

\\[ \mathrm{Throughput} = \frac{\mathrm{AcceptedTokensPerStep}} {\mathrm{StepLatency}} \\]

HyperQwen 并没有把原来的 30 ms 主模型前向推理缩短到 10 ms。实际上，16 列验证的计算更昂贵，但一次获得的有效 Token 也更多。

这也是为什么我认为它最值得借鉴的是 Verify Block 与 Draft Block 解耦。

### 具体如何实现？

HyperQwen 16-token 验证流程

当前已生成 Token + 历史 Prompt

寻找最长后缀在历史上下文中的最近匹配

DFlash2

# 7 Token

神经网络生成草稿

Prompt Lookup

# 8 Token

从历史文本复制候选

Target Verify：最多 16 个输入位置

包含上一轮 Anchor，由 Qwen3.8-27B 验证

接受匹配前缀，拒绝错误候选

平均提交约 14.97 Token / Step（专项测试）

示意中的 7+8 是最长验证块的一种划分，不代表每轮必然同时获得两个来源的全部候选；实际还要处理提议融合和可用长度。

更重要的是，HyperQwen 不会在每个请求中强制进行 16 列验证。

它监测 Lookup 是否持续有效，只有在检测到连续复制内容时才启用长验证块。源码还引入了 Sticky 策略，避免因为短暂的匹配中断频繁切回短验证路径。

甚至还有 `VLLM_DFLASH2_CHAIN=1`：在满足连续复制条件时直接沿历史 N-gram 生成候选，跳过部分 DFlash2 Forward。但这一模式需要严格控制拒绝后的重同步，以及随机采样时的正确提议分布。

核心源码：

- [dflash2-lookup-drafting.patch](https://github.com/syv-ai/HyperQwen/blob/main/patches/dflash2-lookup-drafting.patch?utm_source=chatgpt.com)
- [dflash2-ngram-chains.patch](https://github.com/syv-ai/HyperQwen/blob/main/patches/dflash2-ngram-chains.patch?utm_source=chatgpt.com)
- [Dynamic Verify 测试与参数](https://github.com/syv-ai/HyperQwen/blob/main/single-user/README.md?utm_source=chatgpt.com)

这项技术实际上可以先与 NInfer 的 MTP 结合，并不必须先移植 DFlash2。 这点对你的下一轮研发优先级影响很大。

## 三、除了 Lookup，HyperQwen 还做了哪些真正有价值的底层优化？

381 tok/s 的专项成绩由 Lookup 主导，但常规对话从早期的约 82 tok/s 发展到现在的水平，依靠的是一系列独立优化。

### 1. 显存：首先节省 2.6 GB 的非 Transformer 主体权重

HyperQwen 基于公开 W4A16 AutoRound 量化模型。

它发现原始量化模型虽然把大部分 Transformer 权重量化到了 INT4，但 `lm_head` 和 `embed_tokens` 两个大型矩阵仍然采用 BF16。

这部分对 24 GB GPU 很贵。

HyperQwen 把它们重新量化为分组 INT8，项目报告释放了约 2.6 GB 显存。

这些空间可以重新分配给：

- 更大的 KV Cache
- DFlash2 草稿模型
- CUDA Graph
- 更高并发下的状态与工作缓冲

这项优化的真正价值是扩大 GPU 上能够运行的完整推理配置，而不只是缩短一次矩阵乘法。

你的 NInfer 已经有专用的量化端点格式和 131K Draft Head，因此不能直接照搬“再节省 2.6 GB”的数字。需要检查 `.ninfer` Artifact 的实际 Tensor 格式。

### 2. MTP 草稿 Head：不是越大越好

这是该项目另一项很有价值的发现。

原始 MTP 每预测一个 Token，都可能需要对接近完整的 248K Token 词表进行投影。

HyperQwen 将草稿 Head 缩小到约 40K Token，并利用模型真实输出重新构建候选词表。

项目数据显示：

| Draft Vocabulary 来源 | 对真实生成 Token 的覆盖率 |
| ------------------- | ---------------- |
| 旧网页文本统计             | 约 92.1%          |
| 基于模型真实输出重新统计        | 约 97.5%          |

旧版在代码任务上的覆盖率甚至只有约 83%，新版本提高到了约 96%。

这里的关键不只是省计算。

如果正确的下一个 Token 根本不在 Draft Vocabulary 中，那么无论 MTP 模型多准确，都不可能预测正确，导致提前拒绝。

重新设计词表后，项目报告这一项单独改善了约 10% 的单流吞吐表现。

你的 NInfer 当前已经有：

```
// Qwen3.8-27B
constexpr std::size_t kDraftVocab = 131072;
```

并且使用 Q4 格式存储 Draft Head。

因此，建议探索的是针对你的 Java、中文指令、代码编辑和 Agent Tool Call 语料，重新测量 131K、96K、64K、40K 词表的覆盖率与延迟，而不是直接换成 HyperQwen 的英文语料词表。

### 3. W4A8 INT8 Tensor Core：主要改善 Prefill 和大批量 Decode

HyperQwen 通过 Marlin W4A8 路径，把部分线性层的激活从 FP16/BF16 降到 INT8，使矩阵运算能够使用更高吞吐的 INT8 Tensor Core。

但这里有一个重要区别：

单 Token Decode 往往受显存带宽限制；大量 Token 的 Prefill 和高并发 GEMM 更容易受计算吞吐限制。

因此同一套 W4A8 Kernel，在不同场景下的效果完全不同。

根据仓库测试，单用户 Prefill 在启用 `INT8_ACT=int8` 后：

| Prompt | W4A16 Prefill | INT8 激活 Prefill | 提升    |
| ------ | ------------- | --------------- | ----- |
| 1K     | 1,437         | 1,845           | 约 28% |
| 4K     | 1,494         | 1,937           | 约 30% |
| 16K    | 1,410         | 1,791           | 约 27% |
| 51K    | 1,200         | 1,423           | 约 19% |

不过，HyperQwen 也披露了代价：完整 INT8 激活方案的 Perplexity 和 GSM8K 结果略有变化，不能称作严格无损。

而你的 NInfer 已经实现针对 RTX 4090 的 INT8 Prefill Tensor Core 路径，并在 115K 达到 2,409.2 tok/s，所以HyperQwen 的这部分不是优先移植对象。

更值得参考的是其逐层选择 INT8 路径的策略，以及独立的精度验证方法。

### 4. Split-KV Verify Attention：它解决了隐藏的 GPU 利用率问题

这一点在长上下文特别有技术价值。

传统单 Token Attention 能比较容易地在 KV 维度上拆分工作，但多个推测 Token 同时验证时，部分通用 Attention 路径未能有效拆分长 KV。

HyperQwen 作者指出，旧版 FA2 多 Token Verify 在 RTX 3090 上仅让约 24 个 SM 执行主要工作，而 3090 有 82 个 SM。

它实现了专门的 Split-KV Verify Attention。

仓库给出的 Kernel 微基准：

| 场景                   | 原路径    | 优化后    |
| -------------------- | ------ | ------ |
| 1.5K Attention，单层    | 57 μs  | 23 μs  |
| 16K Attention，单层     | 1.3 ms | 120 μs |
| 128K，8 Query，INT8 KV | 7.4 ms | 1.3 ms |

128K 的数字比较的是项目特定的 Triton Unified Attention 与定制 Split-KV Kernel，并不是所有 FA2 实现的通用差距。

这表明一个重要事实：

长上下文推测解码的瓶颈，可能不是 DFlash2 本身，而是主模型的多 Query 验证路径没有充分利用 GPU 并行度。

不过你现有 NInfer 已经有 Split-KV、小 Token Tile、E8 解码和 Producer/Consumer Warp 分工。所以这项优化应通过 Nsight Compute 对照微基准，而不是直接移植另一套 Triton Attention。

## 四、100K–262K 长上下文：HyperQwen 真的解决了 DFlash2 的瓶颈吗？

只解决了一部分，而且它的源码和测试数据明确证明，长上下文仍是 DFlash2 的薄弱环节。

这与你前面提出的问题完全一致。

### 1. 修复了 DFlash2 的 KV 分配浪费

最初 HyperQwen 的 DFlash2 在 BF16 KV 下，显存池只能容纳约 69K Token。

把 KV 改为 INT8 后，作者本以为容量会接近翻倍，却发现显存占用异常。

原因是 vLLM 的 Hybrid KV 分组机制。

Qwen3.8 同时具有 Full Attention、GDN 和 Drafter 的 Sliding Window Attention。这些不同类型的缓存需要按照统一分组规则进行页大小对齐。

DFlash2 的五个 Sliding Window 层，每个 Page 只使用 16 个 Token，却被分配了远大于需求的空间，利用率只有约 1.88%。

作者通过 `hybrid-sw-block-promote.patch`，将这类块的大小从 16 调整到 864，解决了严重的内存碎片与页对齐浪费。

最终获得：

| KV 配置         | DFlash2 上下文容量 |
| ------------- | ------------- |
| BF16，默认 8 列验证 | 69,758        |
| INT8，默认 8 列验证 | 138,696       |
| BF16，16 列验证   | 57,669        |
| INT8，16 列验证   | 114,224       |

这项工作很有价值，但它解决的是 vLLM KV Cache Geometry 的特定问题。

你自己的 NInfer 已经采用专用 Paged KV 和 E8 编码，不能认为把 Page 大小改成 864 就能获得同样收益。

源码：[hybrid-sw-block-promote.patch](https://github.com/syv-ai/HyperQwen/blob/main/patches/hybrid-sw-block-promote.patch?utm_source=chatgpt.com)。

### 2. 到了 112K，DFlash2 的速度仍然明显下降

HyperQwen 在约 112,655 Token 的 Prompt 上，直接比较了 MTP 和 DFlash2。

112K 长上下文：DFlash2 与 MTP

RTX 3090，HyperQwen 项目自测，Decode tok/s。DFlash2 为 INT8/Triton 的长验证配置。

DFlash2 + Lookup

MTP

04590135180原文复述列出命令保留内容改写引用解释摘要问答

同一组测试中的关键指标：

| 指标            | DFlash2 + Lookup | MTP         |
| ------------- | ---------------- | ----------- |
| 六类任务综合 Decode | 47.0 tok/s       | 78.6 tok/s  |
| 原文复述 Decode   | 154.8 tok/s      | 101.4 tok/s |
| 首轮冷 TTFT      | 316.8 秒          | 151.9 秒     |
| 缓存命中后 TTFT    | 6.1 秒            | 2.4 秒       |

这组数据已经很有说服力：

DFlash2 + Lookup 仍然擅长复述，但在一般的长上下文编程、问答和推理任务中，MTP 反而是更合适的选择。

原因是 Lookup 不能保证每次都能找到高质量候选，而 Drafter 和 Target 的长上下文 Attention 开销却仍然存在。

来源：[HyperQwen Long Context](https://github.com/syv-ai/HyperQwen/blob/main/docs/long-context.md?utm_source=chatgpt.com)。

### 3. 2026 年 10 月 18 日的新进展：FP8 KV + FlashAttention-2

这是比 Reddit 原帖更新、也更值得你关注的一项优化。

项目最近将 FP8 KV 支持引入 RTX 3090 的 FlashAttention-2 路径，从而避免旧 INT8/Triton 后端在长上下文中的部分性能损失。

同一 RTX 3090 上的最新测试：

| Prompt 深度 | 旧 INT8/Triton | 新 FP8/FA2  | 提升    |
| --------- | ------------- | ---------- | ----- |
| 约 66K     | 48.2 tok/s    | 54.0 tok/s | 约 12% |
| 约 100K    | 37.9 tok/s    | 48.2 tok/s | 约 27% |

测试还验证了较低的冷 Prefill 延迟、128 组前缀缓存一致性检查，以及持续运行稳定性。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



针对 RTX 4090，仓库也有另一条优化路线：

Triton Split-KV Verify + FP8 KV + FULL CUDA Graph。

一份 4090 原生 Linux 测试报告给出了下列结果：

| Prompt 深度 | 旧 Unified Attention | 专用 Split-KV |
| --------- | ------------------- | ----------- |
| 约 24K     | 68.3 tok/s          | 100.6 tok/s |
| 约 50K     | 49.8 tok/s          | 96.0 tok/s  |
| 约 89K     | 34.6 tok/s          | 87.4 tok/s  |

这是 HyperQwen 内部新旧 Attention 路径的 A/B，不代表它比 NInfer 快同样倍数。

你的 NInfer 已经有定制的 Split-KV E8 Attention，所以要比的是实际 Kernel 的访存、Occupancy 和每轮耗时，而不是功能名称。

另外，新的 FA2 FP8 插件虽可显式用于 SM89，但项目尚未给出同条件下 RTX 4090 的完整验证报告。

### 4. 256K 的 KVarN 不是免费的

HyperQwen 使用 KVarN 的 4-bit Key / 2-bit Value KV Cache，使约 24 GB 显存能够支持更大的上下文。

但其公开结果非常值得警惕：

FP8 KV，112K MTP

# 68.1 tok/s

KVarN，112K MTP

# 32.0 tok/s

KVarN 在这组单用户测试中让 Decode 耗时增加约 2.13 倍。其中主要是底层 Attention 的每轮成本上升，同时 MTP 每轮有效 Token 数从 2.56 降到 2.38。

因此，不能简单地认为 KV 越低位，Decode 一定越快。

它与 E8 KV 的编码、解码、缩放、数据布局不同；即使同样减少内存占用，GPU 内核的实际效率也可能差异很大。

对你来说，NInfer 当前的 E8 4-bit + 262K 全上下文能力应继续保留，而不是迁移到 HyperQwen 的 KVarN。

## 五、与 tqLLM 和你的 NInfer 做性能、架构对照

### 底层实现差异

| 技术            | HyperQwen                 | tqLLM               | 你的 NInfer                |
| ------------- | ------------------------- | ------------------- | ------------------------ |
| Runtime       | vLLM V2 + 补丁              | 独立 C++/CUDA         | 独立 C++/CUDA              |
| 权重量化          | AutoRound W4A16、GPTQ Head | TQ3/TQ4/GGUF        | Groupwise `.ninfer`      |
| 草稿模型          | MTP、DFlash2               | MTP、DFlash2         | 当前 27B 为 MTP             |
| Prompt Lookup | GPU N-gram + 动态长块         | 已支持，但共享默认 Verify 预算 | 尚无同等完整路径                 |
| Verify        | Chain，最长 16 列的复述模式        | Tree + Chain        | MTP Chain + ReplaySSM    |
| 长上下文 KV       | FP8、INT8、KVarN            | TQ3/TCQ 等           | E8 4-bit                 |
| 前缀缓存          | Hybrid Prefix Cache       | 单槽缓存                | 完整 L1/L2/L3 Continuation |
| 典型侧重点         | 多模式工作负载与吞吐                | 模型专用 Decode 优化      | 长上下文与 Agent 连续执行         |

### 性能应该如何比较？

| 场景              | HyperQwen            | tqLLM                         | 你的 NInfer             |
| --------------- | -------------------- | ----------------------------- | --------------------- |
| 短上下文一般对话        | 3090 约 127–133 tok/s | 3090 摘要约 131–155 tok/s        | 4090 混合基准 106.5 tok/s |
| 特定推理任务          | 取决于接受率               | 3090 LocalMaxxing 约 273 tok/s | 尚无同一工作负载 A/B          |
| 代码生成            | 任务相关                 | 3090 官方 Code-v1 约 199.5 tok/s | 4090 代码基准 148.6 tok/s |
| Prompt 原文复述     | 3090 381 tok/s       | 有 Lookup，未见同条件成绩              | 未见同条件成绩               |
| 128K–256K Agent | 有长上下文模式，成本较高         | 已支持压缩 KV 长上下文                 | 完整 262K + 多级状态缓存      |

所有这些数字都来自各项目自己的基准测试，模型量化和测试任务不同。不能按表格直接排名。

这里还有一个区别不能忽略：

HyperQwen 的 381 tok/s 和 tqLLM 的 273 tok/s 都不是统一的真实 Coding Agent 基准成绩。前者主要是文档复制，后者主要是高接受率推理输出。

若改成真实的 Java 项目修改、执行测试、阅读日志、修复错误，这些极端速度未必能复现。

另一方面，HyperQwen 已测得约 1,035 tok/s 的 64 并发总吞吐。这是真正体现 vLLM 连续批处理优势的地方，但它是64 个请求的聚合吞吐，不是单请求性能。

对于多租户 API 服务，HyperQwen 很有竞争力；对于单个长时间运行的 Coding Agent，NInfer 的完整状态恢复具有更直接的价值。

## 六、你的 NInfer 最值得吸收什么？重新排序

基于这次调查，我会调整前面建议的开发优先级。

第一优先级应该改成 Prompt Lookup 与 MTP 混合推测，而不是先把 DFlash2 完整移植过来。

因为 HyperQwen 已经证明，长上下文下真正可以突破草稿模型限制的，是利用已有上下文本身提供候选 Token。

而你当前 NInfer 已经有 MTP3、ReplaySSM、Paged KV 和完整的缓存体系。

### 推荐架构：Hybrid Speculative Engine

\#chatgpt-mermaid-\_r_7tl\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(13, 13, 13);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_7tl\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_7tl\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_7tl\_ .error-icon{fill:rgb(243, 243, 243);}#chatgpt-mermaid-\_r_7tl\_ .error-text{fill:rgb(13, 13, 13);stroke:rgb(13, 13, 13);}#chatgpt-mermaid-\_r_7tl\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_7tl\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_7tl\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_7tl\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_7tl\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_7tl\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_7tl\_ .marker{fill:rgb(143, 143, 143);stroke:rgb(143, 143, 143);}#chatgpt-mermaid-\_r_7tl\_ .marker.cross{stroke:rgb(143, 143, 143);}#chatgpt-mermaid-\_r_7tl\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_7tl\_ p{margin:0;}#chatgpt-mermaid-\_r_7tl\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(13, 13, 13);}#chatgpt-mermaid-\_r_7tl\_ .cluster-label text{fill:rgb(13, 13, 13);}#chatgpt-mermaid-\_r_7tl\_ .cluster-label span{color:rgb(13, 13, 13);}#chatgpt-mermaid-\_r_7tl\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_7tl\_ .label text,#chatgpt-mermaid-\_r_7tl\_ span{fill:rgb(13, 13, 13);color:rgb(13, 13, 13);}#chatgpt-mermaid-\_r_7tl\_ .node rect,#chatgpt-mermaid-\_r_7tl\_ .node circle,#chatgpt-mermaid-\_r_7tl\_ .node ellipse,#chatgpt-mermaid-\_r_7tl\_ .node polygon,#chatgpt-mermaid-\_r_7tl\_ .node path{fill:rgb(222, 234, 251);stroke:rgb(83, 154, 248);stroke-width:1px;}#chatgpt-mermaid-\_r_7tl\_ .rough-node .label text,#chatgpt-mermaid-\_r_7tl\_ .node .label text,#chatgpt-mermaid-\_r_7tl\_ .image-shape .label,#chatgpt-mermaid-\_r_7tl\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_7tl\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_7tl\_ .rough-node .label,#chatgpt-mermaid-\_r_7tl\_ .node .label,#chatgpt-mermaid-\_r_7tl\_ .image-shape .label,#chatgpt-mermaid-\_r_7tl\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_7tl\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_7tl\_ .root .anchor path{fill:rgb(143, 143, 143)!important;stroke-width:0;stroke:rgb(143, 143, 143);}#chatgpt-mermaid-\_r_7tl\_ .arrowheadPath{fill:rgb(143, 143, 143);}#chatgpt-mermaid-\_r_7tl\_ .edgePath .path{stroke:rgb(143, 143, 143);stroke-width:1px;}#chatgpt-mermaid-\_r_7tl\_ .flowchart-link{stroke:rgb(143, 143, 143);fill:none;}#chatgpt-mermaid-\_r_7tl\_ .edgeLabel{background-color:rgb(252, 252, 252);text-align:center;}#chatgpt-mermaid-\_r_7tl\_ .edgeLabel p{background-color:rgb(252, 252, 252);}#chatgpt-mermaid-\_r_7tl\_ .edgeLabel rect{opacity:0.5;background-color:rgb(252, 252, 252);fill:rgb(252, 252, 252);}#chatgpt-mermaid-\_r_7tl\_ .labelBkg{background-color:rgba(252, 252, 252, 0.5);}#chatgpt-mermaid-\_r_7tl\_ .cluster rect{fill:rgb(243, 243, 243);stroke:rgba(0, 0, 0, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_7tl\_ .cluster text{fill:rgb(13, 13, 13);}#chatgpt-mermaid-\_r_7tl\_ .cluster span{color:rgb(13, 13, 13);}#chatgpt-mermaid-\_r_7tl\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(243, 243, 243);border:1px solid rgba(0, 0, 0, 0.1);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_7tl\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(13, 13, 13);}#chatgpt-mermaid-\_r_7tl\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_7tl\_ .icon-shape,#chatgpt-mermaid-\_r_7tl\_ .image-shape{background-color:rgb(252, 252, 252);text-align:center;}#chatgpt-mermaid-\_r_7tl\_ .icon-shape p,#chatgpt-mermaid-\_r_7tl\_ .image-shape p{background-color:rgb(252, 252, 252);padding:2px;}#chatgpt-mermaid-\_r_7tl\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_7tl\_ .image-shape .label rect{opacity:0.5;background-color:rgb(252, 252, 252);fill:rgb(252, 252, 252);}#chatgpt-mermaid-\_r_7tl\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_7tl\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_7tl\_ .node .neo-node{stroke:rgb(83, 154, 248);}#chatgpt-mermaid-\_r_7tl\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_7tl\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_7tl\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_7tl\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_7tl\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_7tl\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_7tl\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_7tl\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_7tl\_ [data-look="neo"].node .neo-line path{stroke:rgb(83, 154, 248);filter:none;}#chatgpt-mermaid-\_r_7tl\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_7tl\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_7tl\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_7tl\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_7tl\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_7tl\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_7tl\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_7tl\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(0, 79, 153);}#chatgpt-mermaid-\_r_7tl\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(0, 79, 153);}#chatgpt-mermaid-\_r_7tl\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_7tl\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_7tl\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(245, 250, 255);stroke:rgb(206, 219, 229);stroke-width:1px;}#chatgpt-mermaid-\_r_7tl\_ .node rect,#chatgpt-mermaid-\_r_7tl\_ .node circle,#chatgpt-mermaid-\_r_7tl\_ .node ellipse,#chatgpt-mermaid-\_r_7tl\_ .node polygon,#chatgpt-mermaid-\_r_7tl\_ .node path{fill:rgb(229, 243, 255);stroke:rgba(0, 0, 0, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_7tl\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_7tl\_ .node.mermaid-decision .label-container{fill:rgb(245, 250, 255);stroke:rgb(206, 219, 229);stroke-dasharray:2,2;}#chatgpt-mermaid-\_r_7tl\_ .edgePaths .flowchart-link{stroke:rgb(143, 143, 143);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_7tl\_ .marker{fill:rgb(143, 143, 143);stroke:rgb(143, 143, 143);}#chatgpt-mermaid-\_r_7tl\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}NInfer Agent RequestPrefix Reuse / ContinuationRestoreHybrid Draft SchedulerMTP ProposerN-gram Lookup ProposerDFlash2 ProposerDraft Fusion / CandidateSelectionTarget Verify - Full ContextAccept / RejectReplaySSM CommitKV + GDN + MTP StateCheckpointfuture

这里的主要设计原则是将 Proposer 与 Target Verification 解耦。

草稿来源可以不断扩展，但最终结果都经过 NInfer 原有的 Target Verify 和 ReplaySSM。

### 第一阶段：先加 Prompt Lookup，不扩展 Verify 宽度

先在当前 MTP3 的验证容量内实现 N-gram Lookup。

具体地说，先让历史 Token 序列作为一个新的候选来源参与 Draft Selection，验证 Lookup 的准确率和每轮净收益。

这部分不需要先引入 1.19 GB 的 DFlash2 模型，也不需要重写 GDN 多分支状态。

对于一个已经在真实负载运行的引擎，这是风险最低的一项高价值实验。

### 第二阶段：实现 Dynamic Verify Block

在 Lookup 验证有效以后，再逐步扩展 Verify。

建议先测试 6、8 列，最后才考虑 16 列。

这一步在 NInfer 中比 HyperQwen 更复杂，因为你现有的 E8 Attention 特化了较小 Token Tile，同时 ReplaySSM 必须能够保存和正确提交更长的候选前缀。

需要同时处理：

- GDN Raw Transition Record 的容量和 Replay 顺序。
- Attention KV 的推测写入和拒绝后回滚。
- MTP Hidden State、Position 和下一轮 Anchor 的一致性。
- CUDA Graph 对不同 Verify Width 的缓存和工作区管理。
- 多 Lane 并发下的不同候选长度。

应优先实现 Chain Verify，确认无误后，再研究 tqLLM 的 Token Tree。

### 第三阶段：启用 DFlash2，并保留 MTP 作为回退

你当前的 Qwen3.8-27B Target 配置中：

```
struct DFlashConfig {
    static constexpr bool supported = false;
};

inline constexpr std::uint32_t
    kMaximumDFlashDraftTokens = 0;
```

因此，DFlash2 虽然在 NInfer 的共享运行时中有架构基础，但 27B Target 还没有完成接入。

这里还有一个很现实的障碍：显存预算。

NInfer 当前 262K E8 运行配置仅有约 1.37 GiB 的余量，而 HyperQwen 的 W4A16 DFlash2 草稿模型本身就约 1.19 GB，尚未计算中间激活、Draft KV 和 CUDA Graph。

这意味着原封不动移植 W4A16 Drafter，很可能无法维持当前 262K 配置。

更好的策略是同时比较 tqLLM 的更低位 DFlash2 格式，或者通过减小主模型/草稿工作区获得空间，并分别测试 64K、128K、262K。

### 各优化的投资回报判断

| 优化方向                  | 与 NInfer 重叠情况   | 预期价值 | 建议        |
| --------------------- | --------------- | ---- | --------- |
| Prompt Lookup + MTP   | 当前缺少同等功能        | 高    | 优先        |
| Adaptive Verify Width | 当前较小窗口特化        | 高    | 优先        |
| DFlash2 27B Target    | 有共享框架，未启用       | 中高   | 第二批       |
| 动态 DFlash2/MTP 切换     | 需要状态管理          | 中高   | 第二批       |
| TQ3 低位 Drafter        | 需转换模型格式         | 中高   | 结合显存预算研究  |
| Split-KV Attention    | 已有专用实现          | 不确定  | 只做微基准 A/B |
| INT8 Prefill          | 已完成主要优化         | 低到中  | 暂不优先      |
| FP16 GDN State        | 现有 FP32 状态路径更稳妥 | 风险偏高 | 保持现状      |
| KVarN 替换 E8 KV        | 已有更适合的 E8 方案    | 不明确  | 不建议直接替换   |

这些是基于架构的优先级判断，不是已实现的性能收益。

## 七、如果在你的 4090 上验证，应该怎么做？

HyperQwen 已有 4090 的社区复现，包括 WSL2 和原生 Linux，并非只能在 3090 上运行。

其中一组 WSL2 RTX 4090 测试，DFlash2 的普通短任务获得了约 135–181 tok/s 的不同任务成绩，但这些不是统一长上下文工作负载，不能直接对比你 NInfer 的基准。

建议做两组不同的实验。

第一组不修改任何 NInfer 源码，把 HyperQwen 部署在独立端口，并使用固定的 Qwen3.8-27B 测试任务分别验证短上下文、100K、200K 和真实 Coding Agent 多轮会话。

第二组只实现 NInfer 的 Lookup + MTP 原型，使用相同任务测试新增功能的独立收益，避免把权重量化、Attention Backend、Prefix Cache 等不同因素混合到同一个性能结论中。

### 我建议采用的生产验收标准

| 指标               | 验收目标                      |
| ---------------- | ------------------------- |
| 代码复制、Patch 生成    | Lookup 相比 MTP3 有明确加速      |
| 普通 Java 代码生成     | 不得明显慢于原 MTP3              |
| 128K–262K Decode | 保持现有长上下文性能                |
| ReplaySSM 一致性    | 接受路径和回滚测试全部通过             |
| Agent 工具调用       | Schema、参数及执行成功率不退化        |
| TTFT             | Continuation Cache 热命中不回退 |
| 显存               | 262K 默认配置仍能在 24 GB 内运行    |

另外，需要特别测试请求历史被改写的情况。你的 Pi/Agent 系统可能重新组织系统提示词、摘要、工具结果和历史消息。Lookup 只能使用与当前请求一致的 Token 历史，不能从过期的缓存状态中复制候选。

否则，即便最终 Target 会拒绝错误候选，性能也会因为持续拒绝而恶化。

## 八、最终判断

这次调研让我更确定一个方向：

下一代单卡高速推理的竞争，不再只是比谁的 GEMM 或 Attention Kernel 快，而是比谁能让昂贵的 Target Forward 在每轮产出更多有效 Token。

HyperQwen 用文档历史作为几乎免费的候选生成器，在高度重复内容中做到了 381 tok/s；tqLLM 使用 DFlash2 Token Tree 增加被验证的候选路径；你的 NInfer 则已经在长上下文 KV 访问、状态回滚与缓存复用上进行了深度优化。

三者最有价值的能力可以组合，但不应该直接合并三套运行时。

对于你的单卡 RTX 4090，我会把目标明确为：

NInfer + MTP + Prompt Lookup + Adaptive Verify，之后再引入 DFlash2。

比起追求短上下文文档复述的 381 tok/s，更有价值的成功标准是：

- 长时间 Coding Agent 能否减少实际 Target Forward 次数；
- 100K–262K 下是否仍保持较高的有效 Token/Step；
- 改造后 Java 项目的真实任务完成时间是否下降；
- 不牺牲你已有的 262K 上下文能力和完整状态恢复。

这条路线可以吸收 HyperQwen 最有价值的技术成果，同时避免丢掉你已经建立的 NInfer 底层优势。

核心参考：[HyperQwen 优化明细](https://github.com/syv-ai/HyperQwen/blob/main/docs/optimizations.md?utm_source=chatgpt.com)、[长上下文测试](https://github.com/syv-ai/HyperQwen/blob/main/docs/long-context.md?utm_source=chatgpt.com)、[单用户性能矩阵](https://github.com/syv-ai/HyperQwen/blob/main/single-user/README.md?utm_source=chatgpt.com)、[RTX 4090 复现](https://github.com/syv-ai/HyperQwen/blob/main/docs/wsl2-4090.md?utm_source=chatgpt.com)、[NInfer b0-scanner](https://github.com/lkyprogramer/ninfer-4090/tree/b0-scanner?utm_source=chatgpt.com)。

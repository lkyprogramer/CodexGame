# NInfer 架构、性能机制与 RTX 4090 / Qwen3.8-27B 选型报告

**资料核查日期：2026-09-07**  
**目标机器：RTX 4090 24GB、64GB RAM、600GB SSD；最后确认的驱动为 545.23.08，nvidia-smi 显示 CUDA 12.3。**  
**目标工作负载：Pi / Java Coding Agent，单用户长期会话，实际约 200K 输入上下文，而不是仅在启动参数里填写 200K。**

> 本报告区分四类证据：**源码事实、作者/社区实测、本文推导、待实机验证**。没有在你的 4090 上运行 NInfer，没有把仓库自报的测试结果当成本次实测。审阅范围是架构、构建、模型制品、关键算子、状态回放、缓存和 HTTP 合同，不是逐行审计整个仓库。

## 一、结论：已经有 4090 版本，不应从零重写

**你不需要先把原版 NInfer 移植到 4090：社区已经有直接针对 Qwen3.8-27B / RTX 4090 的分支。** 最有研究与试验价值的是 `sergiuszm/ninfer-4090`，以及继续增加长期 Agent 缓存和 INT8 prefill 的 `tensorninja/ninfer-4090`。它们沿用 NInfer 的专用 C++/CUDA 执行路线，而不是 vLLM 配置文件的另一种包装。[S02][S03]

原版 `Neroued/ninfer` 的主要特色是：只服务明确注册的模型制品、GPU 和执行形状，通过离线权重布局、融合算子、CUDA Graphs、MTP 和 ReplaySSM，把通用框架需要承担的复杂性压缩到较小范围。**这是“模型、量化格式、GPU、运行时联合优化”，不是“C++ 天然比 Python 快几倍”。**[S01][S04][S05]

对你的实际情况，结论分三层：

| 问题 | 结论 | 证据边界 |
|---|---|---|
| 能否在 24GB 4090 跑 Qwen3.8-27B？ | 已有社区实现和实测 | 需要匹配的 `.ninfer` 制品，不能拿现有 GGUF 直接载入 |
| 能否接近或超过 200K 上下文？ | E8 K4/V4 KV 路线已有 262,144 容量及深度检索报告 | 检索题通过不等于所有长代码任务质量不变 |
| 是否比你的 WORK、patched vLLM 更适合长期 Pi？ | **值得成为优先 A/B 候选，尚不能宣布胜出** | 缺少同机、同任务、同 thinking、同输出口径的完整比较 |

**推荐行动顺序：固定一个 4090 分支和模型哈希 → 核验 Pi 协议与会话复用 → 运行真实 200K / Java 测试 → 再决定是否改内核。** 当前不值得先从零重造推理引擎，也不值得先移植 DFlash2 然后才验证缓存。

### 本次核查发现的三个实际问题

1. **模型制品合同已出现版本分叉。** 上游固定提交中的模型卡已经描述含 DFlash2 的 **19.03 GiB** 文件；4090 分支 Dockerfile 仍校验旧 **16.96 GiB** 文件的 SHA-256，却默认从 Hugging Face `resolve/main` 下载。[S09][S10]
2. **README 与 Docker 默认参数不同。** 文档示例强调单 lane，但审阅到的 Dockerfile 实际 `CMD` 是 `--max-concurrency 4`。不能直接把单并发的显存和性能数字套到默认容器。[S03][S10]
3. **HTTP 兼容不等于参数完全相同。** 该分支支持顶层 `enable_thinking`，但不能原样接受所有 SGLang 的 `chat_template_kwargs`；`strict:true`、强制指定工具等也有明确限制。[S13]

这些比“再增加一个性能开关”更值得先处理。

---

## 二、NInfer 是什么：一个专门为少数模型定做的发动机

### 2.1 用普通人的方式理解

可以把推理引擎看成厨房：

- **llama.cpp** 像设备兼容面很广的厨房，可以处理很多模型和硬件。
- **vLLM / SGLang** 更像调度能力强的大厨房，要处理不同顾客、批次、模型和部署环境。
- **NInfer** 像只做几道菜、知道每一步尺寸和顺序的专用生产线。

专用生产线可以提前确定工作台大小、食材摆放和操作顺序，减少搬运与临时协调。但换一道差异很大的菜，不能只换一个菜单名字。

这正对应 NInfer 的“exact target / closed registry”：模型架构、权重语义、算子几何和执行计划都有明确的注册范围。一个文件能被解析，不代表该模型能被执行。[S01][S04][S05]

### 2.2 它不是 llama.cpp fork，也不是 PyTorch 的薄封装

原版运行路径是自行实现的 C++/CUDA 引擎；4090 分支继续这一体系。模型执行并不依赖 PyTorch eager、TensorRT 或 ggml。但是构建、转换、测试和 Web 仪表盘可以有独立工具依赖，不能把“运行时不依赖 PyTorch”说成“整个项目不使用其他工具”。[S01][S03][S10]

### 2.3 `.ninfer` 不是另一种 GGUF 文件名

版本 2 的制品由二进制头、JSON 对象目录、4096 字节对齐后的 tensor/resource payload 构成。对象目录记录模型/权重身份、shape、数值格式、物理布局与偏移；**不携带一个可以随意解释的新模型计算图**。模型语义和执行流程仍在编译后的 target 中。[S05]

```text
源 Qwen checkpoint
       │ 转换、量化、重排、资源封装
       ▼
.ninfer 制品
       │ 检查 model_id / weights_id / tensor 合同
       ▼
已注册 target + 编译后的执行计划
       │
       ▼
匹配 GPU 的算子实现
```

因此，你现有 `Qwen3.8-27B-UD-Q4_K_XL.gguf` 不能直接给它加载。你需要匹配的 NInfer 制品；两者虽然来自同一个基础模型，量化与权重布局却不同。[S05][S09][S20]

---

## 三、底层架构：请求、调度、状态、算子各自负责什么

### 3.1 四层主路径

上游架构文档明确区分四个执行边界：[S04]

```text
Pi / OpenClaw / CLI
          │
          ▼
Gateway：HTTP、SSE、协议、工具与媒体输入
          │
          ▼
Frontend：Tokenizer、模板、位置、输出通道与边界语义
          │
          ▼
Engine：排队、请求生命周期、取消、资源与结果发布
          │
          ▼
Program：模型状态、KV、workspace、prefill/decode/speculative
          │
          ▼
Ops / CUDA kernels
```

这里最值得借鉴的不是类名，而是**状态的唯一所有权**：

| 组件 | 核心职责 | 不应该负责的事 |
|---|---|---|
| Gateway | 协议解析、SSE、请求转换 | 挑选 KV 页、决定缓存淘汰 |
| Frontend | 模板、token/position identity、工具与思考文本边界 | GPU 内存分配与 FIFO 调度 |
| Scheduler | 谁在什么时候运行 | 决定某个缓存文件的数值合法性 |
| ResourceManager | 哪些逻辑上下文值得保留、候选选择 | 维护另一份可能与真实分配器分叉的物理账本 |
| Program | 真实状态、物理资源、执行、提交与回滚 | 用户协议、缓存价值政策 |
| Op | 输入到输出/局部状态变换的闭合数学合同 | 会话生命周期、跨请求公平性 |

这对长期 Agent 很重要。错误地混合“输出已经发送”“KV 已经提交”“GDN 状态仍是投机状态”，可能导致下一轮看似正常却从错误的历史继续。NInfer 的设计在这些提交边界上投入了很多结构化工作。[S04][S06]

### 3.2 固定容量的小并发，而不是大规模云推理调度

上游 Generation Engine 的范围是一张 GPU、一个常驻模型、启动时确定的 1–8 个 active requests，以及有界队列。decode-ready 请求组成紧凑批次；它不把大规模抢占、跨卡放置、优先级 QoS 或分布式服务视为现有合同。[S04]

这与“一个人用一张 4090 跑 Pi”很匹配，但不意味着它更适合数十个相互竞争的 Agent。4090 分支的文档还明确指出：深冷 prefill 会阻塞其他请求的响应，不能把“支持多个 lane”理解成“prefill/decode 公平调度已经完善”。[S02][S03]

### 3.3 大块内存在启动阶段确定

权重、KV/State backing、workspace 和 CUDA Graph 资源通常在接收请求前建立，运行时主要改变 mapping、frontier、owner 和有效区域。这减少热路径上的动态分配和图重建，也使显存容量检查更可控。[S04]

但“可控”不等于“任何参数都不会 OOM”。显存预算还必须覆盖算子临时区、graph capture、媒体路径和不同投机长度；fork 的默认值、原版的 admission 合同也不能混用。

---

## 四、为什么会快：真正有价值的七项机制

### 4.1 针对固定 shape 选择不同 kernel

在 4090 分支 `q4_q5_attn_input_plan.cpp` 中，可以直接看到固定 geometry：

```text
input_rows = 5120
query_rows = 6144
kv_rows = 1024
```

A16 路线还根据 token 列数分段：1–16、17–20、21 及以上，分别选择不同 small-T / MMA schedule。大 prefill 和单 token decode，并不强迫使用同一个 kernel。[S07]

普通解释：一次切一根菜和一次切一千根菜，需要不同的工具。小批量最怕启动和搬运，大批量更关心计算吞吐。NInfer 把这些边界具体化到已知模型的算子计划，而不是寄希望于一个通用算子在所有形状都最佳。

### 4.2 融合与预先安排好的权重布局

源码包含 `linear_swiglu`、`linear_add`、`attn_input_proj`、`gdn_input_proj` 等闭合融合算子。它们可以把投影、分支拆分、门控或 residual 相关工作放到同一执行计划中，减少中间 tensor 的反复读写和多次启动。[S06][S08]

注意：**不是融合越多越好。** 大 kernel 可能增加寄存器压力、降低 occupancy，甚至比多个较小 kernel 慢。该项目把 Op 的数学边界与 kernel 实现分开，允许对不同 shape 选择不同内部组合；这是一个比“写一个 mega-kernel 就解决”更稳健的工程思想。[S06]

### 4.3 CUDA Graphs 降低重复启动成本

单 token decode 会重复调用大量相似的小算子。把稳定执行序列捕获为 CUDA Graph，再反复 replay，可以减少 CPU 发射与调度开销。NInfer 同时配合预分配 workspace、固定的小并发范围和 exact-batch 图，降低捕获形状的不确定性。[S04][S08]

这不意味着注意力的计算量不再随上下文增长。Graph 优化的是执行组织和启动，不会消除读取长 KV 的带宽成本。

### 4.4 MTP：让一次主模型验证提交多个 token

MTP 利用模型附带的预测模块生成草稿，再由 target 验证。粗略的吞吐关系是：

\[
\text{tokens/s}\approx\frac{E[A]+1}{T_{draft}+T_{verify}+T_{commit}}
\]

其中 A 为接受的草稿数；额外的一个 token 对应 correction/bonus。该式是理解性能的简化模型，不是对所有实现计时字段的精确对应。[S11]

为什么代码常常更快？结构化代码中的缩进、括号、标识符复用和固定写法更容易被草稿预测。社区表里代码与混合语料的接受率差异就很大。所以 **149 tok/s 代码成绩不是“这模型所有任务都 149 tok/s”**。[S02][S03]

为什么不把 draft 长度一直加大？更多草稿也增加验证、状态和缓存开销；接受率下降后，额外工作可能白做。你的 MTP2 与别人的 MTP3/MTP4 必须各自在真实任务上扫描，不能仅按 n_max 排名。

“投机解码理论上保持 target 分布”的前提，是验证/采样和状态提交正确。这里的 target 也是**已经量化的目标模型**，不是 BF16 原版。换 batch 形状、KV 精度或算术路径，还可能产生浮点差异；不能把理论保证扩展成跨实现逐字节相同。

### 4.5 ReplaySSM：不再给每个候选 token 保存一整份 GDN 状态

这是 NInfer 对 Qwen 混合架构最值得研究的一项。

Qwen3.8-27B 的 GDN 层持有循环状态。投机验证完若只接受前两个 token，下一轮必须回到这两个 token 对应的状态，而不能沿用后面被拒绝部分的状态。[S11][S12]

传统快照办法：

```text
S0 → S1 → S2 → S3 → S4
     保存每一份完整状态
最终接受到 S2，就取回 S2
```

ReplaySSM：

```text
保留 S0 + 每一步实际驱动状态变化的原始输入记录
验证结束，知道接受到哪里
只回放接受的部分，生成正确的新状态
```

对 27B geometry，一份 FP32 GDN 状态约为：

\[
48\times48\times128\times128\times4\ bytes=144\ MiB
\]

实际源码中的单步记录包括 BF16 K、BF16 V，以及 FP32 的 gate/beta。按声明的 head 数推导，48 层单步这些 raw records 约 **0.77 MiB**。因此仅比较“每个候选位置新增的数据”，144 MiB 与约 0.77 MiB 相差接近 188 倍。[S11][S12]

**这不是总显存减少 188 倍。** S0、提交后的状态、Attention KV、其他 workspace 和模型权重仍然存在；回放也需要额外计算。它减少的是投机状态轨迹的保存开销。

另外，回放必须复现实际有限精度的运算次序。实数公式等价，不等于 FP32/BF16 下得到同一个持久状态。上游文档明确强调 normalization、reduction、cast 和乘加结合顺序，否则微小误差会跨 Agent 轮次累积。[S11]

对你的意义：**保住 MTP 的显存空间，又不简单依赖把整个 GDN state 降到 FP16 来省内存。** 但数值正确性仍须通过长循环和失败回滚测试来证明。

### 4.6 真正针对 Ada 的算子调整

4090 分支不是只把编译参数从 120a 改成 89。其工作包括寄存器预算、producer/consumer 分工、V 的解量化、attention tile 组织和累加方式调整。作者报告某个 INT8 attention prefill shape 提升约 30%，但对应服务端 prefill 收益只有部分几个百分点。[S02][S14]

这符合 Amdahl 定律：如果某个算子只占总时间的一部分，它快 30%，整个请求不会跟着快 30%。也说明你应该先 profiling，再选改造点。

`tensorninja` 分支进一步给 prefill 引入 INT8 Tensor Core 路线。作者在 115,125-token 冷输入上的分步结果是：[S03]

| 改造阶段 | prefill tok/s | 相对原路线 |
|---|---:|---:|
| BF16 routes | 1,701.4 | 1.000× |
| INT8 fused SwiGLU | 1,976.4 | 1.162× |
| 再加 INT8 linear_add | 2,147.3 | 1.262× |
| 再加 Attention / GDN projections | 2,409.2 | 1.415× |

这是同一量化制品下的执行路线改变，但 INT8 **activation** 仍有数值近似，不能称为无损提速。源码将它显式归入 `AllowA8` 合同，并让同一个 prefill token 的量化方式不依赖调用宽度，避免冷/热 prefix 因 chunk 大小不同走不同数值路径。[S07]

还有一个关键边界：**“decode kernel 没改”不代表“最终答案不变”。** prefill 改变了初始 KV/GDN state，后续 decode 从不同状态出发，仍可能改变生成。因此性能扫描必须带质量控制。

### 4.7 PDL / Blackwell 优化不能原样算在 4090 上

原版 `src/core/pdl.cuh` 使用 Programmatic Dependent Launch：`cudaLaunchKernelEx`、`cudaTriggerProgrammaticLaunchCompletion` 与 `cudaGridDependencySynchronize`。[S15]

但 4090 分支给 sm_86 **和 sm_89** 定义了 `NINFER_SM86` 兼容宏。该宏下，PDL wrapper 回退为普通的同 stream kernel launch，设备端 trigger/wait 也被门控；构建还排除了 Blackwell 专属 W4A4 实现并使用 stub。[S16][S17]

所以：

> **4090 可以继承算法、量化布局、状态事务和部分 kernel 组织，但不能通过升级 CUDA 获得 Blackwell 的原生 FP4/TMA/PDL 快路径。**

这是“移植为 4090 版本”需要重新调度 kernel，而不仅改一个显卡名字的原因。

---

## 五、200K / 262K 是怎样装进去的：权重量化和 KV 量化是两回事

### 5.1 权重制品约 17 GiB，不等于只有 17 GiB 总显存占用

已测 4090 路线使用的旧制品是 `qwen3_8_27b.ninfer`，18,210,531,328 bytes，约 16.96 GiB。它包括 Q4/Q5/Q6 groupwise body、W8 embedding/head，以及模型资源。制品文件大小也不应直接当作启动后的 resident VRAM：部分可选能力不会上传，运行时另有 State/KV/workspace。[S20]

### 5.2 长上下文另有不断增长的 KV 成本

按 16 层 full attention、4 KV heads、head dimension 256 计算，FP16 K/V 的基础存储成本是 64 KiB/token。若把本报告的“200K”具体取作 204,800 tokens：

| 格式 | 仅完整 Attention K/V 的近似成本 |
|---|---:|
| FP16 | 12.50 GiB |
| 8-bit | 6.25 GiB，另加具体格式的 scale/元数据 |
| 理想裸 4-bit K/V | 3.125 GiB，未含 scale、索引、未压缩尾部等 |

这是从架构参数推导的下限/基础账，不是任何引擎的完整 allocator 结果。GDN、MTP、checkpoint、临时区必须另算。[S11][S14][S20]

### 5.3 4090 fork 的关键是 E8 K4/V4 KV

`rk4v4-e8` 不会把模型权重再量化一次。它压缩的是运行中存储的历史注意力 K/V；E8 相关编码主要用于键的低比特表示，模式名表示 K4/V4，而不是与任意普通 Q4 KV 完全相同的布局。[S14]

通俗理解：权重是模型长期学到的知识；KV 是它正在读这份代码库时写下的工作笔记。文件变大时，增长的是笔记。

作者在 24GB 4090 上报告：[S03][S14]

| Profile | 上下文容量 | 报告的 KV runtime | 启动余量 |
|---|---:|---:|---:|
| MTP3 + INT8 KV | 172,032 | 6.31 GiB | 约 136 MiB |
| MTP3 + E8 K4/V4 | 262,144 | 5.08 GiB | 约 1.37 GiB |
| MTP3 + E8 K2/V4 | 262,144 | 4.01 GiB | 约 2.43 GiB |

该表不是“你机器保证有这些余量”；图形桌面、驱动、编译器、运行时版本、并发和额外缓存都会改变结果。

**对你的选择：先 K4/V4，不先 K2/V4。** K4 已有容量满足约 200K 的公开证据，进一步把 K 降至 2bit 的收益主要是余量，而不是你必须达到的能力；没有必要先承担更激进的量化风险。

### 5.4 需要警惕三种“长上下文已支持”说法

1. 只把 `--max-context` 设成 262K，实际输入只有 2K。
2. 一个近 260K 的 needle 成功，就宣布 260K Java Agent 完全无损。
3. 浅上下文 149 tok/s，加上“262K 可启动”，拼成“262K 下 149 tok/s”。

三种都不构成你需要的证明。验收必须同时记录真实 prompt tokens、KV 类型、实际生成数、decode 时间和任务正确性。

---

## 六、公开性能应该怎样解读

### 6.1 把不同口径的数字分开

下表是作者/维护者报告，不是本次复测。旧 INT8 浅上下文数据、E8 深度扫描、新 INT8 prefill 不能拼成一次统一 benchmark。[S02][S03][S14]

| 场景 | 设置 / 口径 | 报告值 | 可以说明什么 |
|---|---|---:|---|
| 浅代码生成 | INT8 KV，MTP3 | 148.6 tok/s | 高接受率代码可很快，不代表全任务 |
| 混合 bench corpus | INT8 KV，MTP3 | 106.5 tok/s | 语料变化显著影响投机收益 |
| 不投机浅 decode | INT8 KV | 约 50.5 tok/s | 主模型普通解码基线 |
| 作者标记的 128K prose | E8 KV，MTP3 | 77.5 tok/s | 有长深度收益证据 |
| 作者标记的 256K prose | E8 KV，MTP3 | 65.4 tok/s | 不能用浅 149 代替该值 |
| 作者标记的 256K code | E8 KV，MTP3 | 91.2 tok/s | 内容可预测性仍影响深度性能 |
| 115,125-token 冷 prefill | E8 KV，新 INT8 projections | 2,409.2 tok/s | 新 prefill 路线的实际长输入记录 |

深度标签并不自动给出完整输入/输出边界与剩余窗口；复测时要从原始请求和日志确认。上述深度扫描来自特定语料，并非真实 Pi 任务的耗时保证。

### 6.2 不应该据此认定比你的 WORK 快两倍

fork 的一部分 llama.cpp 对照使用 Q8 KV，MTP 时窗口缩到约 131K；你的 WORK 已经用 Q4 KV + MTP2，并做过真实 Pi 测试。二者不是同一约束。[S03]

还存在以下变量：GGUF 与 `.ninfer` 的权重量化不同；MTP 深度不同；`llama-bench` 和 HTTP `/metrics` 的计量边界不同；thinking 与输出长度也可能不同。

因此合理结论是：**NInfer-4090 已经证明“有竞争力”，尚未证明“胜过你当前最优 WORK”。**

### 6.3 不能把更小 Python 开销当作主要解释

vLLM / SGLang 的重计算同样运行在 CUDA kernel 中。NInfer 的优势主要来自允许更激进的固定形状调度、融合、状态生命周期和布局选择。另一方面，成熟框架在 batching、算子库、模型覆盖和维护方面有优势；移除 Python 并不保证 GEMM 或 attention 就更快。[S04][S07][S21]

### 6.4 质量不应只看 retrieval 和接受率

NInfer 旧 groupwise 制品有公开能力评估：IFBench strict 77.67%、GPQA-D 87.37%，模型卡列出官方参考 79.5%、89.2%，但明确说明不是同协议对照。[S20]

这比只有 PPL/needle 更有价值，但仍不是：

- E8 K4/V4 + 新 INT8 prefill 的 200K Java 质量证明；
- 修改多个 Java 文件后测试正确率的完整证据；
- 长循环状态无漂移的证明。

同样，codec 的 98.678% cosine similarity 不是“模型保留了 98.678% 智力”；MTP 接受率近似不变也不是任务质量完全相同。

---

## 七、最贴近你需求的变化：完整 continuation cache

### 7.1 缓存的不只有 K/V

Qwen 的一次合法继续执行，可能需要：

```text
Attention KV
+ GDN recurrent / convolution state
+ continuation hidden state
+ MTP / draft state
+ token 与位置账本
+ 可恢复的对话边界
+ exact model / codec / runtime identity
```

只恢复 Attention KV 不恢复 GDN，下一轮会从不一致的历史继续。`tensorninja` 的 continuation cache 文档明确覆盖完整状态，而不是只做一个 HTTP response cache。[S18]

### 7.2 三层分别解决什么

| 层 | 在哪里 | 最有价值的场景 | 成本与边界 |
|---|---|---|---|
| L1 | 已有 GPU pool 里的 retained lane | 同一个 Pi 会话不断追加 | 不重新分配一份独立 KV 池；受容量和 eviction 限制 |
| L2 | pageable 主机内存中的完整 image | 多个会话交替、GPU lane 被换走 | 需要 CPU 处理和 PCIe restore |
| L3 | 本地 SSD 的 content-addressed chunks | 重启恢复、更多冷会话 | 文件 I/O、哈希校验、写放大与版本管理 |

这里的 L1/L2/L3 是软件缓存层级，**不是 GPU 硬件的 L1/L2 cache**。[S18]

L3 使用 SHA-256 分块、manifest、原子发布、权限隔离和 corruption-safe miss。它的 content-addressed 指持久化数据块去重，不等于能把任意位置重复的文件文本直接变成可互换 KV。[S18]

### 7.3 对同一长期 Agent，会话留在 GPU 最有价值

你的最佳热路径应是：

```text
已有 100K / 200K 历史仍在 GPU lane
          +
新的 user / tool_result tail
          ↓
只计算新尾巴
```

如果每轮都先落到 L2 再恢复，仍可能比冷重读好很多，但并不是最佳状态。

作者一轮真实 OpenCode 会话记录了 44 次 L2 restore：同步 import+preflight 平均约 2.91 秒；当会话长到 120K–130K 时，单次约 5.5–7.3 秒。该轮没有 L3 payload 读取，不能将其视为“SSD 恢复也同样快”的证明。[S19]

### 7.4 默认 768 MiB L1 值得你特别检查

文档把 `--continuation-cache-l1-mib 768` 定义为 retained-lane 字节预算/淘汰阈值，而不是另分配 768 MiB 显存。一个 200K 会话的完整状态显著大于这个数量级。[S18]

**本文推断：**如果这一阈值使长会话每轮都被降到 L2，那么“打开三级缓存”反而掩盖了“本可留卡，却频繁 restore”的问题。它不证明当前分支一定在你的请求路径上这样做，必须看 `l1_evictions`、`cache_source` 与 `l1_resident_bytes`。

你的单用户测试应比较默认值与足以保留一个完整长会话的 L1 阈值，例如从测得 image 字节数反推；可把 6 GiB 作为实验上限之一，但它只是**待验证的策略阈值**，不是承诺最优配置，也不增加物理 KV 容量。

### 7.5 两种 anchor 对客户端历史改写更友好

该分支不仅保留前缀末端，还增加 rolling-tool checkpoint 和 user-turn anchor。客户端若把 reminder 移到最新 user message，末端 LCP 可能失效，但仍可恢复到较早合法边界，重算变化之后的内容。[S03][S13]

这不是“忽略不一致内容继续用旧 KV”。正确做法始终是：**找到仍精确相同的前缀 → 恢复那个前缀的完整状态 → 重算变化后的尾巴。**

### 7.6 会话标识只是线索，不是正确性的替代品

`prompt_cache_key` 用来定位会话，仍要核验权重哈希、codec、speculative 配置、token/position/media identity 等。相同 key 搭配不相同历史，必须安全 miss，而不是强行复用。[S18]

对于 Pi，建议一个测试会话使用稳定 key；不要每个请求生成新 key，也不要让所有独立会话共享一个全局固定 key。客户端是否支持透传要验证，不能因为接口兼容就默认已经生效。

---

## 八、社区分支怎么选

### 8.1 主要路线图

```text
Neroued/ninfer
    │ 原始专用引擎，主要针对 RTX 5090
    ▼
Don-Chad/ninfer-3090
    │ SM86 兼容、Qwen3.8、ReplaySSM 等
    ├── sergiuszm/ninfer-4090
    │      Ada 调优、E8 移植、服务接口、深度测试
    │          └── tensorninja/ninfer-4090
    │                 更完整的会话分层缓存、anchors、INT8 prefill
    └── UDPSendToFailed/ninfer-4090
           E8/低比特 KV、原生 Windows 等工作
```

这是概念上的改造/继承关系；精确 Git parent 和 cherry-pick 关系要以目标提交为准。多个 fork 的 README 使用同一张表，不是多个独立实测。[S02][S03][S14]

### 8.2 我的选择建议

| 项目 | 主要价值 | 对你的定位 |
|---|---|---|
| Neroued/ninfer | 原始执行架构、Op 合同、ReplaySSM、最新 DFlash2 参考 | 上游算法和设计来源；不是原样部署 4090 |
| Don-Chad/ninfer-3090 | 从 Blackwell 到 Ampere 的兼容基础 | 移植经验来源，不优先当最终 Ada 分支 |
| sergiuszm/ninfer-4090 | 明确的 sm_89 调优和深度 benchmark | 相对较聚焦的 4090 基线候选 |
| tensorninja/ninfer-4090 | 长会话缓存、anchors、监控、新 prefill 优化 | **最贴近你的 Pi 场景，但新增功能也扩大回归面** |
| UDPSendToFailed/ninfer-4090 | E8 编码、低比特缓存、Windows 路径 | 按需借鉴；不能把 Windows 的性能优化直接视为 Linux 收益 |
| patched vLLM / kernel-sanders 路线 | W4A16、DFlash2/MTP、KVarN 与框架生态 | 与 NInfer 平行 A/B，不因新项目出现就废弃 |

建议先用固定的 `tensorninja` 提交做一个功能完整候选；若问题集中在新增缓存/INT8 prefill，再回退 `sergiuszm` 路线隔离变量，而不是把所有 fork 的补丁一次性叠加。

### 8.3 已有跨 fork 的反例，说明“优化补丁”并非天然可移植

维护者对 sibling fork 的 Q4/Q5 dequant 微优化做过回归测试：一些补丁编译通过、正确性 suite 也通过，却在其 Linux CUDA 构建的部分 GEMM 上显著变慢，最后撤掉。文档推测与工具链/SASS 差异有关，但该原因不是已经证实的结论。[S14]

你应借鉴的是它的流程：**同卡测量 → 分步 cherry-pick → 验证 → 撤掉负收益**，而不是 README 中哪个“优化”字样最多。

### 8.4 X 与社区证据的限制

本次使用 Exa 与网页检索交叉查了 GitHub、模型卡和社区反馈，也检索了 X 上的相关内容。没有找到足够可复核的独立 X 原帖日志来证明“200K Pi Java 会话的确定性能”。因此本文性能依据以作者仓库、固定源码和模型卡为主，不把转载、相同 fork 表格或搜索标题当成新增验证。

---

## 九、与已有推理方案的真正差异

| 维度 | WORK / llama.cpp | patched vLLM | NInfer-4090 | Lucebox / Escha 的相关路线 |
|---|---|---|---|---|
| 特化位置 | GGUF 和多硬件算子体系 | 框架之上的量化、kernel、runner 和 KV 改造 | 制品、target、kernel、状态事务一体化 | Lucebox 偏 speculative pipeline；Escha 偏专用低比特权重/kernel |
| 模型可替换性 | 较广 | 较广，但你的 patch 对版本敏感 | 注册制，明显更窄 | 依具体架构/格式 |
| 本次 4090 主要权重 | 现有 UD-Q4_K_XL | W4A16 AutoRound 等 | groupwise `.ninfer` | GGUF 或 Escha 格式 |
| 长上下文手段 | KV 量化、resident slot/checkpoints | KVarN/其他 KV + hybrid-state prefix | E8 KV + ReplaySSM + resident/continuation | 各版本不同，不能只看模型文件大小 |
| 开发维护风险 | 你已有可用实测基线 | Python/CUDA 依赖和 patch rebase | 模型/编译器强绑定、较小社区、fork 分叉 | 草稿/模型/运行时组合需固定 |
| 对你最有价值的比较 | 实际 Pi/Java 基准 | 更完整框架路线 | 单 GPU 长会话的专用路线 | 保留已测短循环结果作为参照 |

上述是设计取舍，不是绝对性能排名。[S04][S05][S18][S21][S22][S23]

尤其应修正此前“patched vLLM 是最终赢家”的表述：**那应该是一个待验证的优先工程候选，而不是既成事实。** 现在 NInfer-4090 已有与用户约束高度相关的证据，正确策略是增加候选并统一测试口径，不是不断按新项目的最大 tok/s 改换主力。

对于大并发和频繁换模型，成熟通用框架有明显的设计优势；对于固定 Qwen3.8-27B、单卡、小并发、长期本地 Agent，NInfer 的限制反而可能是优势。最终仍由实际任务耗时、正确率与会话复用决定。

---

## 十、当前不能忽略的工程风险

### 10.1 同名模型文件已存在两套合同

| 来源 | 大小 | SHA-256 | 能力说明 |
|---|---:|---|---|
| 本次检索到的 HF 模型卡、4090 fork 校验值 | 16.96 GiB | `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e` | 已测 MTP/vision 制品 |
| 上游固定提交的模型卡 | 19.03 GiB | `0634abb07024221de141456cf04a42ab74b18bc38e1b781c6eb2e062a467eec3` | 新增 DFlash2 companion，要求更新 runtime |

**这是来源的发布/索引同步差异；没有下载完整大文件核查此刻 HF main 实际返回哪组 bytes。** 但 Dockerfile 的“浮动 URL + 固定旧哈希”组合确实存在。HF main 一旦返回新文件，该构建就会安全地校验失败。[S09][S10][S20]

正确处理：固定 runtime commit、制品 revision/哈希、容器基底与编译器；校验不符就停止。**不能删除 hash check，更不能只把期望哈希改成新值而不审阅 loader 合同。** 新文件可能包含不同对象清单，文件额外体积也不能直接等同于 MTP 模式额外 resident VRAM。

### 10.2 新上游 DFlash2 不会自动进入旧 4090 fork

上游固定提交的模型卡与转换源码已经包含 Qwen3.8-27B DFlash2。但 4090 分支的 serving 文档仍描述该分支 DFlash 为 35B-A3B 路线，不能据此给 27B 直接加一个 `--spec dflash2` 就期待运行。[S09][S13]

若将来移植，需要一起处理新制品对象、5-layer drafter、特征 tap、窗口位置、proposal head、state transaction、graph shape 与缓存身份；原版 family 和 fork 的目录/合同也已分叉。对你第一轮部署，MTP3 更省事。

### 10.3 open issue 说明长期缓存仍值得做压力回归

上游 #177 有用户报告：private continuation 容量饱和后，第一个会话仍能复用，而后续独立会话持续 0% 命中；修复与回归测试发布在个人分支，评论未说明已合入原仓。[S24]

**不能直接说该问题必然存在于 tensorninja fork。** 两边缓存实现已不同。它的价值是提供了一个必须纳入验收的场景：A→B→C 多会话周转后，每个会话的第二轮都应重新建立复用，而不是只测试第一次会话。

### 10.4 “API 兼容”存在明确边界

审阅分支的 Chat Completions 合同：[S13]

- 接受 system/developer/user/assistant/tool，以及 tool history。
- thinking 可用顶层 `reasoning_effort` / `enable_thinking`；preserve_thinking 有自己的映射。
- `strict:true` 工具、`tool_choice:required`/指定工具、非空 logit bias 有明确不支持错误。
- 未知请求字段拒绝，不是忽略。

因此 Pi 接入应先验证实际请求，不可把上一套 SGLang/vLLM 的 extra body 全部转发。不能为了跑通而悄悄删除 strict/required 等语义约束；要么客户端显式选受支持模式，要么实现对应合同。

### 10.5 压缩 KV 不是压缩历史文本

E8/KVarN 改变 KV 的数值表示；Pi 的摘要、删除工具结果、重写历史改变输入本身。两种改变会叠加，第一轮引擎 A/B 应先关闭额外语义压缩，否则无法判断质量差异来自哪里。

### 10.6 单卡不能把所有后端一直并排驻留

64GB RAM 不等于给 24GB 显卡增加了 64GB 同速显存。NInfer 的模型执行目标是 GPU resident，主机内存主要帮助加载、checkpoint 与冷会话缓存；不能据此把 WORK、vLLM 和 NInfer 全部常驻同一块 4090。[S04][S18]

---

## 十一、针对你的配置：建议怎样开始

### 11.1 保留现有 WORK，不先重写内核

第一轮候选：

```text
Qwen3.8-27B 旧版、已校验的 groupwise NInfer 制品
          +
固定 sm_89 fork
          +
MTP3 / E8 K4V4
          +
单 lane、rolling-tool checkpoint、完整 prefix reuse
          +
按需 L2 / L3
```

不先打开 LoRA，不先启用 vision，不先把 keys 降成 2bit，也不先移植新 DFlash2。它们都不是你纯 Java Agent 首轮达标的必要条件。

### 11.2 上下文与资源建议

| 项目 | 第一轮建议 | 原因 |
|---|---|---|
| 输入验收点 | 实际 204,800 tokens | 明确“约 200K”的计数口径 |
| max-context / kv-capacity | 221,184 | 给输出和工具往返留出空间，不把输入顶满上限 |
| max-concurrency | 1 | 对齐你的长期单会话，避免默认 C4 改变显存和调度 |
| draft-tokens | 3；追加对照 2 | 以真实任务决定，不盲目加深 |
| prefill-chunk | 1024 | 先复现已测参数，再单独扫描 |
| KV | rk4v4-e8 | 先满足容量与质量均衡 |
| checkpoint ring | 如需历史改写，先 4–8 | 32 项约 4.6 GiB/slot，别盲目照搬 |
| L2 | 8–16 GiB 上限 | 给 Java、OS、加载、异步 publication 留内存 |
| L3 | 第一轮关闭；重启测试时 32–48 GiB | 先隔离 GPU/RAM 路径，再验证磁盘持久性 |
| L1 | 依据实际 retained bytes 调整 | 默认 768 MiB 不应被误认作可容纳整段 200K |

以上是**本文待测起点**，不是该硬件上的新实测结果。600GB 是 SSD 标称容量，不是可用容量；Docker 多阶段构建、嵌入模型、其他后端权重和缓存副本都要单独计账。[S10][S18]

### 11.3 CUDA 三种策略，不能混称“不升级”

| 路线                        | 是否保持 Driver 545 | 是否保持宿主 CUDA 12.3 工程 | 状态                                  |
| ------------------------- | --------------- | ------------------- | ----------------------------------- |
| 原驱动、原 Toolkit 全不动         | 是               | 是                   | 当前 4090 fork 原样不支持：CMake 明确要求 ≥12.8 |
| 保留旧工程，隔离新工具链/容器，升级驱动      | 否               | 可以∑                 | **优先的低侵入落地路线**                      |
| 移植回 CUDA 12.3 + Driver545 | 是               | 是                   | 可研究的工程分支，尚未验证，不能只改 CMake 版本门槛       |

fork 原生编译门槛为 CUDA 12.8+，Dockerfile 实际使用 CUDA 13.2.0。**容器隔离用户态库，不隔离宿主驱动。**[S10][S17]

NVIDIA 文档中 CUDA 13.x minor compatibility 的最低驱动分支为 R580，但这不是任意 CUDA 13.2/JIT 程序在任意 R580 上都保证可用；13.2 GA 的配套 Linux 驱动为 595.45.04。CUDA 12.8 GA 的配套驱动为 570.26。应按所选工具链的具体 release notes 和实机测试固定版本，而不是仅写“R580+ 一定能跑”。[S25]

对你来说，最合理的是保留 `/usr/local/cuda-12.3` 与 WORK 的旧二进制/依赖，新增一个隔离的新环境，升级驱动后先回归 WORK。不要修改全局 `LD_LIBRARY_PATH` 让两个环境互相覆盖。

### 11.4 要坚持 Driver545，回移植应检查什么

这是开发任务，不是已完成方案：

```text
检查所有 CUDA Runtime / Driver API 的最低版本
检查 CUDA 12.3 对 host compiler 的支持
只编译 sm_89；排除 Blackwell-only instructions / files
检查 PTX 与原生 SASS 的实际打包
核验图捕获、异步拷贝、allocator 与 codec 的编译路径
运行 kernel parity → 200K 请求 → cache resume → Pi loop
```

PDL 已有旧架构 fallback 是积极因素，但不足以证明整个项目兼容 12.3。任何缺失 API 都要给出等价后备实现与失败测试，不能简单删掉版本检查。

---

## 十二、最值得做的定制开发，不是重新实现全部算子

### P0：固定制品和构建合同

**目标：**消除“代码新、模型旧”或“模型新、fork旧”的隐性组合。

**源码/文件：**`Dockerfile`、根 `CMakeLists.txt`、`src/targets/*` 注册/binder、构建脚本。

**交付：**一个 source/model/toolchain lock；校验过的旧制品；显式单并发启动配置；`/v1/models`/日志记录完整 build identity。

**验收：**错误模型哈希、错误 weights_id、新 DFlash2 对象清单进入旧 loader 时，均清楚拒绝，不能半加载后再 CUDA assert。

### P0：Pi 协议适配和指标统一

**目标：**真实 tool loop，不只是 curl 聊天。

**源码：**`src/serve/openai_schema.cpp`、`translate.cpp`、`tool_call_parser.cpp`、`responses_schema.cpp`、`event_stream.cpp`、`request_log.cpp`。

**交付：**若必要，增加轻量兼容层，将 Pi 实际使用的 thinking 参数映射到现有受支持语义；保持 tool IDs、reasoning 与 messages 内容；统一导出 prompt/decode/cache 时间。

**验收：**读文件→tool_result→再次调用→最终答复完整通过；未知字段与真正不支持的约束不被静默吞掉；流内 error 即使 HTTP200 也统计为失败。

### P0：长期会话 L1 命中和 anchor 回归

**目标：**读过的大文件在后续十次追问中不被反复冷 prefill。

**源码：**`src/runtime/cache/continuation_cache.cpp`、`src/runtime/engine/`、`src/targets/qwen3_8/` 的 prefix/continuation 逻辑。

**交付：**request-level cache_source、effective frontier、reprocessed tokens、L1 eviction 原因；单用户长会话策略参数。

**验收：**200K append-only 命中；工具结果边界；中部编辑安全回退；A/B/A 会话切换；cancel 后无 stale state；同 key 不同历史不错误复用。

### P1：把 INT8 prefill 的数值影响单独量化

**目标：**把作者报告的 1.415× 收益与模型质量影响分开。

**源码：**`src/ops/attn_input_proj/q4_q5/q4_q5_attn_input_plan.cpp`、对应 GDN/linear_add/linear_swiglu routes、target phase policy。

**交付：**同 build 的 A16/A8 prefill 控制组。若添加参数，该参数必须是**新实现**并进入 runtime/cache compatibility identity，不能把本文建议的开关当成现有 CLI。

**验收：**同一 token 在完整 chunk、尾 chunk、warm suffix 下数值合同一致；Java 测试与深度检索不倒退；cold/warm 状态 parity 与整任务结果均检查。

### P1：可选的 CUDA 12.3 backport

**目标：**只有在你坚持保留 Driver545 时才投入。

**源码：**根 CMake、`src/core/pdl.cuh`、CUDA 资源/transfer/graph API、toolchain 配置。

**交付：**确实可编译/执行的 sm_89 12.3 构建及依赖版本；缺失 API 的受测 fallback；不用全局库路径劫持。

**验收：**sm89 kernel suite、同制品数值控制、200K prefill/decode、恢复/取消/长循环均通过。不能以“编过了”代替“能正常服务”。

### P2：高精度最近 KV 尾部

**动机：**长期代码工作可能更在意最近的变量名、错误日志与改动约束。可研究“旧 KV 用 E8，最近 512/1024/2048 tokens 用 FP16 或 INT8”。上游已有相近 feature request，但这不是当前分支的已验证能力。[S26]

**源码：**paged KV layout、`gqa_attention_decode_i8.cuh` / prefill 路线、尾部写入/封存与 checkpoint metadata。

**关键约束：**最近段滑动、block wrap、MTP rejection、cache restore 都必须保持 codec 和位置一致；不要先把整段 200K 解压成 FP16 再计算。

**验收：**同任务质量有可测收益，显存和延迟代价可接受，否则不默认打开。仅凭“更高精度直觉上更好”不够。

### P2：从上游移植 Qwen3.8 DFlash2

**动机：**MTP3 已跑稳，且 profiling/任务结构证明需要更长的高接受草稿后再做。

**参考：**上游 `tools/convert/qwen3_8_27b/dflash2_recipe.py`、`dflash2_inventory.py`、`docs/maintainer/qwen3.8-27b-dflash2.md`、family startup_features。[S09][S27]

**交付：**匹配的制品、drafter state、proposal/verification 合同、sm89 kernel routes、完整缓存身份与 memory budget。

**验收：**正确性先于接受率；在实际 200K、长输出、Pi Java 任务上胜过 MTP 才推广。不能把 5090 上游实现直接作为 4090 性能证据。

### P2：prefill/decode 公平性

单用户一个会话先不做。确有多子 Agent 同时请求后，才考虑在安全的 prefill chunk 边界让出执行权；不能在半提交的 GDN/投机状态中强行切换。该项涉及调度合同，不是调小 `prefill-chunk` 就自动获得公平性。

---

## 十三、一次约一小时的针对性验收建议

这里给的是**单个候选配置、模型已下载且编译/JIT 已完成后的预算**，不是下载、编译、多个后端全跑完都承诺一小时。它能做有效筛选，不能证明数小时无人值守已稳定。

| 阶段 | 预算 | 做什么 | 判定重点 |
|---|---:|---|---|
| 协议与 warm-up | 5 分钟 | 模型、thinking、SSE、工具调用、错误字段 | 真实 Pi 请求可工作，不静默降级 |
| 深上下文 | 12 分钟 | 64K 与实际 204,800-token 输入，分布式事实和代码细节；长输出测速 | tokens 精确计数、无截断、正确性与 ≥20 tok/s 用户目标 |
| 长会话复用 | 12 分钟 | 读 20K Java 材料后连续短追问；100K/200K append；一次中部改写 | new-tail 而非整段重读；改写后不能用旧答案 |
| Java Agent | 20 分钟 | 并发幂等、重试边界、重连/时间单位，三类小型 JDK-only 项目 | 真改 production code、编译与测试通过，测试文件未篡改 |
| 生命周期 | 8 分钟 | A/B/A 换会话、取消、错误请求后恢复；选一项 L2/L3 回访 | 无状态污染、资源泄漏、缓存饱和后永久 miss |
| 汇总 | 3 分钟 | 原始 JSONL、资源日志、统计、判定 | 未跑标 NOT_RUN，超时标 INCOMPLETE，不伪报 GO |

### 13.1 固定比较口径

- 首轮引擎对比统一 thinking off；产品体验测试另统一 medium，并记录 reasoning token。
- 记录 template/tokenizer/model SHA、实际请求 token 数、采样参数与输出上限。
- 相同语料、相同检索事实、相同 Java 测试；GPU 只跑一个后端。
- 流式事件可能一次包含多个 token，**不能数 SSE chunk 当 token 数**。
- warm/cold 分开，prefix restore、prefill、decode、tool execution 和 queue 时间分开。
- 能力不同的接口用经审核的 adapter；禁止把不存在的 `/tokenize` 当作所有后端都有。NInfer 有对应的 Responses input-token-count / Anthropic count-tokens 路径。[S13]

### 13.2 对长期 Java Agent 最有区分度的题型

**A. 读一次，再问十次。** 20K Java 代码与设计文档先进入 history，后续只问短问题，不重复 read。正确缓存应该复用旧文档，而不是每轮重新 prefill。

**B. 已读文件发生新版本。** 先给旧 `timeoutMs=200`，之后 tool result 返回修订文件，要求基于新版本修复。缓存应保留合法前缀，但最终结论必须使用新信息。

**C. 并发幂等。** 模型需要定位 check-then-act 或 future publication 的 race，修改实现，通过并发测试，不能只改返回值。

**D. 重试与状态机。** maxAttempts 包不包含第一次、terminal exception 是否可重试、时间单位转换与 registry 清理跨类关联。

**E. 恢复后继续。** 中途取消、切换另一个会话，再回来追问原上下文中的标识符与约束；检查 GDN/MTP/Attention 状态是否一起恢复。

### 13.3 建议的输出统计

```text
case_id, engine_commit, artifact_sha256, kv_codec, spec_method
actual_prompt_tokens, computed_prefill_tokens, restored_tokens
cache_source, restore_ms, prefill_ms, ttft_ms
reasoning_tokens, completion_tokens, decode_ms, wall_ms
tool_calls, compile_pass, tests_pass, protected_files_unchanged
gpu_peak_mib, host_peak_mib, cuda_error, timeout, finish_reason
```

**发布门槛建议：**实际 200K 能完整处理、目标 decode 至少 20 tok/s、深度事实/代码约束正确、3 类 Java 任务通过、append cache 真正有效、无 silent truncation、无 CUDA fault。若只是快而改坏代码，不升为主力。

一小时筛选通过后，再补独立长时间 soak。不要用一小时短题通过代替“连续数小时所有生命周期已覆盖”。

---

## 十四、可直接借鉴的启动合同示例

以下是**源码参数核对后的研究起点**，不是在你机器上执行过的安装脚本。前提是你已经用受支持工具链编译，并取得旧版、哈希匹配的制品。

### 14.1 固定源代码

```bash
git clone https://github.com/tensorninja/ninfer-4090.git
cd ninfer-4090
git checkout --detach 44a2c6c3392c9d51e76a895ed97bf1867530d252
```

不要直接混入另一个 fork 的所有提交。构建前阅读该固定提交的 `CMakeLists.txt`、`Dockerfile` 和模型合同。

### 14.2 校验已取得的旧制品

```bash
printf '%s  %s\n' \
  eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e \
  models/qwen3_8_27b.ninfer | sha256sum --check
```

未匹配就停止。HF 页面与 GitHub 源码模型卡已有不同版本，本文不提供未经核实的旧 HF revision，也不建议通过修改预期哈希绕过兼容检查。

### 14.3 单用户约 200K profile

```bash
mkdir -p logs "$HOME/.cache/ninfer/research"

nohup ./build-sm89/apps/ninfer-serve models/qwen3_8_27b.ninfer \
  --model-id qwen3.8-27b \
  --host 127.0.0.1 --port 18030 \
  --max-context 221184 --kv-capacity 221184 \
  --max-concurrency 1 --max-pending-requests 8 \
  --pending-timeout-ms 600000 \
  --prefill-chunk 1024 --kv-dtype rk4v4-e8 \
  --spec mtp --draft-tokens 3 --lm-head-draft \
  --prefix-checkpoint-policy rolling-tool \
  --continuation-cache l1-l2 \
  --continuation-cache-l1-mib 6144 \
  --continuation-cache-l2-mib 8192 \
  --preserve-thinking \
  --request-log-jsonl logs/requests.jsonl \
  > logs/server.log 2>&1 &
```

这里 L1=6144 MiB 是为了测试“单个深会话留卡”的**待验证策略阈值**，不是新分配 6 GiB KV，也不保证更快。应与默认 768 MiB 对照，检查实际 resident bytes、eviction 和恢复来源；显存总量仍由物理 pool 与模型/graph 决定。

若 `build-sm89` 不是实际构建目录，应使用本次构建生成的二进制；不要把别的 build 下旧可执行文件当作固定提交产物。

### 14.4 API smoke

```bash
curl --fail http://127.0.0.1:18030/v1/models

curl --fail http://127.0.0.1:18030/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model":"qwen3.8-27b",
    "messages":[{"role":"user","content":"Explain Java compare-and-set in two sentences."}],
    "reasoning_effort":"none",
    "prompt_cache_key":"ninfer-java-smoke",
    "max_tokens":128,
    "stream":true,
    "stream_options":{"include_usage":true}
  }'
```

这是该分支的顶层 thinking 语义，不应改成未经支持的 nested enable_thinking。真实 Pi 测试还需确认 tools、reasoning history 和 schema 附加字段。

---

## 十五、最终判断

**NInfer 的价值是把一个确定模型在一张确定显卡上的整条执行链做好，而不是证明“通用框架都太慢”。** ReplaySSM、exact-shape 算子、固定 workspace、MTP 状态事务和完整 continuation cache 都有实质技术内容。

对你最关键的新事实是：

> **4090 专用版本已经存在，而且其 E8 长上下文、rolling-tool checkpoint 和完整会话缓存，比单纯的短提示词 tok/s 更贴近你真正的需求。**

不过，源码核查同时发现模型制品发布差异、默认并发不一致、HTTP 参数限制、缓存容量与数值近似风险。它值得优先实测，但还不足以让你立即删除 WORK 或放弃 patched vLLM。

**我的推荐：把 `tensorninja/ninfer-4090` 固定提交作为“长期 Pi/Java 专用候选”，`sergiuszm` 作为较聚焦的回退参考；先做制品/协议/缓存资格验证，再做同机约 200K 的端到端 A/B。只有这轮通过，才值得继续做 CUDA12.3 backport、高精度 KV 尾部或上游 DFlash2 移植。**

---

# 附录 A：固定源码与证据索引

说明：以下索引既列支持性证据，也列限制性证据。仓库主分支与搜索索引可能不同步；对源码判断，优先使用明确提交。HF 模型卡内容在检索时仍描述旧制品，不能据此替代下载后实际 SHA 校验。

- **[S01] 原版项目定位与能力**：https://github.com/Neroued/ninfer ；固定审阅提交 `487f89773f07cb18a2fb841fe0971ec9634d409b`。
- **[S02] 聚焦的 4090 fork**：https://github.com/sergiuszm/ninfer-4090 ，分支 `rtx4090-port`。该 README 的多数历史性能亦被后续 fork 继承，不计作独立重复试验。
- **[S03] 本文主要候选 fork**：https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/README.md 。
- **[S04] 上游 Engine 架构合同**：https://github.com/Neroued/ninfer/blob/487f89773f07cb18a2fb841fe0971ec9634d409b/docs/maintainer/engine-architecture.md 。
- **[S05] `.ninfer` version-2 制品格式**：https://github.com/Neroued/ninfer/blob/487f89773f07cb18a2fb841fe0971ec9634d409b/docs/maintainer/artifact-container.md 。
- **[S06] Op / kernel / schedule 责任边界**：https://github.com/Neroued/ninfer/blob/487f89773f07cb18a2fb841fe0971ec9634d409b/docs/maintainer/op-development.md 。
- **[S07] 4090 Attention projection 实际 route**：https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/ops/attn_input_proj/q4_q5/q4_q5_attn_input_plan.cpp 。
- **[S08] 4090 编译对象、fusion、库边界**：https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/CMakeLists.txt 。
- **[S09] 上游新 DFlash2 制品合同**：https://github.com/Neroued/ninfer/blob/487f89773f07cb18a2fb841fe0971ec9634d409b/model-cards/Qwen3.8-27B-NInfer/README.md 。
- **[S10] 实际 Docker 基底、下载 URL、哈希、默认 C4**：https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/Dockerfile 。
- **[S11] ReplaySSM 有限精度与提交语义**：https://github.com/Neroued/ninfer/blob/487f89773f07cb18a2fb841fe0971ec9634d409b/docs/maintainer/replayssm-gdn.md 。
- **[S12] Replay record 真正 dtype/shape 校验代码**：https://github.com/Neroued/ninfer/blob/487f89773f07cb18a2fb841fe0971ec9634d409b/src/ops/linear_attention/gated_delta_net/replay.cpp 。
- **[S13] 4090 HTTP 与 slot/state 合同**：https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/docs/serving.md 。
- **[S14] E8、Ada 移植、数值与负收益补丁记录**：https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/docs/udp-fork-comparison.md 。
- **[S15] 原版 PDL 实现**：https://github.com/Neroued/ninfer/blob/487f89773f07cb18a2fb841fe0971ec9634d409b/src/core/pdl.cuh 。
- **[S16] sm89 的 PDL fallback**：https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/core/pdl.cuh 。
- **[S17] sm89 与 CUDA12.8 构建门槛**：https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/CMakeLists.txt 。
- **[S18] 完整 continuation cache：L1/L2/L3、权限与 identity**：https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/docs/continuation-cache.md 。
- **[S19] 同文档的实测 switching cost / 指标 / 未实现范围**：同 [S18]，章节 “Measured L2 switching cost”“Implementation status”。这是同一来源，不作独立验证计数。
- **[S20] HF 检索到的旧模型卡**：https://huggingface.co/neroued/Qwen3.8-27B-NInfer 。与 [S09] 描述的制品大小/哈希不同，需分别看待。
- **[S21] patched vLLM 4090/3090 路线**：https://github.com/kernel-sanders/qwen38-27b-rtx4090-vision ；来源链亦包括 https://github.com/syv-ai/qwen38-27b-rtx3090 。
- **[S22] Lucebox 项目**：https://github.com/Luce-Org/lucebox 。不同模型、GPU 和工作负载的 headline 不可互相移植。
- **[S23] Escha 权重与运行时合同**：https://huggingface.co/EschaLabs/Qwen3.8-27B-Escha-W2 。
- **[S24] 上游 private continuation 饱和报告与个人分支修复**：https://github.com/Neroued/ninfer/issues/177 ；评论中的修复 https://github.com/splickz/ninfer-yarn-nvfp4/commit/e49eda0bbae7bff58facd8ce41577aed627bac4f 。
- **[S25] NVIDIA CUDA13.2.2 release notes / toolkit-driver 表**：https://docs.nvidia.com/cuda/archive/13.2.2/cuda-toolkit-release-notes/index.html ；minor compatibility 说明 https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html 。
- **[S26] 高精度 KV 尾部 feature request**：https://github.com/Neroued/ninfer/issues/164 。仅作研究动机，不表示已经落地。
- **[S27] 新 Qwen3.8 DFlash2 实现入口**：https://github.com/Neroued/ninfer/blob/487f89773f07cb18a2fb841fe0971ec9634d409b/tools/convert/qwen3_8_27b/dflash2_recipe.py ；设计 https://github.com/Neroued/ninfer/blob/487f89773f07cb18a2fb841fe0971ec9634d409b/docs/maintainer/qwen3.8-27b-dflash2.md 。

# 附录 B：本次交付与未执行项目

| 项目 | 本次状态 |
|---|---|
| Exa / 网页 / GitHub 研究 | 已进行 |
| 关键源码与固定提交核对 | 已进行 |
| 社区现成 4090 引擎定位 | 已完成 |
| 框架比较、风险和开发顺序 | 已提供 |
| 用户专属资源与测试设计 | 已提供 |
| 下载完整模型并校验 | **未执行** |
| CUDA 编译 / kernel 测试 | **未执行** |
| 用户 4090 上性能与 Pi 运行 | **未执行** |
| 主力替换结论 | **待统一实机验收，不预先宣布赢家** |

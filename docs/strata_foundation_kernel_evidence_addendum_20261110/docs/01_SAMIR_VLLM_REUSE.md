# 01 · samir-vllm：复用机制，不借用性能结论

新增能力状态：**PLANNED**。本页是离线增量规范，不是引擎、kernel、测试或采集器已交付的声明。默认 GPU 预算为 **0**；不启动模型，不改 Strata 代码，不另建融合实现或 benchmark。

## 固定来源与适用边界

审计锁定 samir-vllm [`127c48089d5d872ca5c8b1f92fd624478975dde0`][commit]，提交时间为 2026-11-03 17:25:35 UTC。它自定位为教学引擎；源码固定 Llama 3.2 1B Instruct、16 层、hidden 2048、32/8 个 Q/KV heads、head dimension 64 和 2048 context。权重、activation、KV 为 BF16，GEMM 以 FP32 累加；不是 MoE、量化专家或 CPU offload 框架。[模型常量与投影][projection]没有证明目标 RTX 4090 已验证，构建文件也没有提供该卡的性能合同。

实际入口调用 `loadLlamaModel`：完整权重先读入 CPU vector，再整体复制到 GPU。另有 `loadModelMmap`，但当前入口不调用；即使调用，也仍全量复制到 GPU。不能把 mmap 的存在描述为专家按需加载或利用 64 GB RAM 扩展推理容量。[加载器][loader]与[实际入口][main]须分别核验。

源文件存在、函数被调用、某条分派实际命中是三种证据。历史教学阶段曾使用两个固定槽位，当前版本已改为按请求预算确定槽位，不能混用不同提交描述。相反，保留的密集缓存读取辅助函数并不属于当前解码路径；看到它还在仓库，不能据此声称解码仍把完整历史复制成连续缓存。

## 可复用的只是机制说明

| 源码机制 | 本增量如何复用 | 不应移植的假设 |
| --- | --- | --- |
| row-major 张量与 cuBLAS 参数对应 | 给既有算子记录 shape、stride、dtype、分派条件 | 不复制固定维度，不重写 Strata GEMM |
| `InferenceBuffers` 按生命周期复用 | 给既有 scratch 补充 owner、最后消费者和覆盖条件 | 顺序执行安全不等于异步/graph 下安全 |
| 页表直接访问与 FP32 online softmax | 作为注意力语义、有效长度和精度路径的解释参照 | 不是长上下文高性能 kernel 证据 |
| 物理页与 admission credits 分离 | 解释实际占用和未来预算是两个量 | 不修改 Strata placement、容量和准入策略 |

上述入口见[缓存与 scratch 结构][buffers]、[`pagedAttentionKernel`][paged]。该核每 query head 用 64 线程，按 token 串行遍历；`swiGluKernel` 只融合逐元素 SiLU 与乘法，Q/K/V 和 gate/up 投影仍分别调用。不能称其已实现 fused QKV、fused MoE 或完整融合 MLP。Strata 已有融合与性能工具，本页不把这些方向重新立项。

## 性能数字的证据等级

笔记中的“10 ms 得到 100 token/s、12 ms 双请求得到约 167 token/s”明确是教学假设，**不能放入性能对比表作为实测**。[原文声明][example]

检查当前文件树和主要源码，未发现可执行微核 benchmark、端到端性能原件、CUDA events/CPU timer 计时合同、CUDA Graph 对照或 profiler 报告。`warmUpGpu` 只是未被入口调用的空核；没有可核实 warmup/cache-flush 协议。唯一 checked-in 测试目标是 tokenizer test，不覆盖 GPU 数值或分页状态。[测试与构建][cmake]

正常调用路径的同步次数可以从代码计算，但无法据此推导耗时。代码中的页数、缓冲区字节数和线程数也都是结构事实，既不是峰值显存实测，也不是利用率。没有同一硬件、输入、精度和计时边界的原件，就不计算相对加速比，更不能把可运行与可采用合并为一个通过状态。

Prefill 仍分配 `32 × T² × 2` 字节 scores：T=2048 对应 256 MiB；若仅按公式外推到 32768，单项即 64 GiB。这是源码算术，不是支持能力或测量结果；paged decode 不会消除 prefill 的二次方临时占用。[分配公式][scores]

## 接入现有证据合同，而非新增平台

后续若获准补充离线记录，状态仍为 PLANNED：引用既有 benchmark 原件、manifest 和 dispatch 信息，核对实际 shape、数值路径、eager/graph、输入身份及计时边界；缺项保持未知，不补零，不从微核外推服务吞吐。Strata [现有 dispatch counters][dispatch]区分 capture 与 eager，仍不等于设备内部时间线。数值和状态资格沿用 [06 数值护栏](06_NUMERICAL_GUARD.md)，基础夹具边界见 [07 内存与 oracle](07_MEMORY_AND_ORACLE.md)。

证据补充应回答原件来自哪个提交、使用哪组张量、经过哪条入口、结论覆盖什么范围。这里只增加这些说明的规范，不创建第二套运行协议；发现缺项应明确降级或停止，不为了填齐表格而自动请求新样本。

源码可按其许可研究；notes/PDF 并非 MIT 内容。只保留固定链接和独立源码分析，不搬运教材或图示。[许可边界][license]

[commit]: https://github.com/samir-sarwar/samir-vllm/commit/127c48089d5d872ca5c8b1f92fd624478975dde0
[projection]: https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/src/main.cpp#L71-L132
[loader]: https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/src/main.cpp#L451-L737
[main]: https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/src/main.cpp#L1913-L1916
[buffers]: https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/src/main.cpp#L320-L441
[paged]: https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/src/kernels.cu#L407-L530
[example]: https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/proper_notes/markdown/youtubePT9_static_continuous_batching.md#L55-L59
[cmake]: https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/CMakeLists.txt
[scores]: https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/src/main.cpp#L1124-L1138
[dispatch]: https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/include/strata/core/dispatch_stats.hpp
[license]: https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/LICENSE-NOTES

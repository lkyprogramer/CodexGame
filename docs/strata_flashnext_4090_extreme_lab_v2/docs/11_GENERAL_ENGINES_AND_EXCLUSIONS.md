# 通用服务引擎补充对照与硬件排除表

检索日期2026-10-25。下面是官方文档层面的机制参照，**没有**宣称这些项目已兼容本机当前Flash-Next GSQ-RCO资产，也没有进行同机器跑分。这一层补充07文档中更深入的定制引擎源码研究。

| 引擎 | 官方文档列出的能力 | 对Strata本机可提取的方向 | 资格限制 |
|---|---|---|---|
| vLLM | PagedAttention、continuous batching、chunked prefill、prefix cache、CUDA/HIP Graph | O16分块与公平性、O25图调度、O50/51前缀与状态管理 | 不是“换框架就更快”；需独立确认目标架构/native混合量化支持和24GB容量 |
| TensorRT-LLM | inflight batching、paged KV、chunked context、MTP/EAGLE/NGram等推测 | O33–38成本/状态合同、O59调度与资源准入 | NVIDIA算子/硬件支持矩阵和格式适配决定可用性，不套B200/H100结果 |
| LMDeploy/TurboMind | persistent batch、blocked KV、dynamic split/fuse、权重与KV量化、前缀缓存 | O16/44/50/59内存与服务规划 | 官方吞吐倍率基于其基准，本包不引用为本机预期收益 |
| MLC LLM/TVM | 按平台编译模型库、定制量化与编译优化流程 | O32受控shape autotune、算子选择/融合和部署manifest | 新模型/混合IQ codec/CPU miss路径适配成本不能忽略 |

来源：[vLLM主页](https://docs.vllm.ai/)、[vLLM优化](https://docs.vllm.ai/en/stable/configuration/optimization/)、[vLLM Graph设计](https://docs.vllm.ai/en/stable/design/cuda_graphs/)、[TensorRT-LLM概览](https://nvidia.github.io/TensorRT-LLM/overview.html)、[IFB调度](https://nvidia.github.io/TensorRT-LLM/features/paged-attention-ifb-scheduler.html)、[LMDeploy](https://lmdeploy.readthedocs.io/)、[MLC编译](https://llm.mlc.ai/docs/compilation/compile_models.html)。文档可能更新，实施时固定需要移植的具体源码版本；本表不是一组已经审核可copy的patch。

## 对“所有理论方向”的边界

| 路线 | 本机判定 | 可保留的启发 |
|---|---|---|
| 多GPU tensor/expert/pipeline parallel、NVLink、prefill/decode异机分离 | 单4090不满足资源前提 | 单引擎公平性、局部流水和有界状态转移 |
| Hopper TMA/WGMMA/cluster/PDL、Blackwell tcgen05/NVFP4原生路径 | sm89不支持对应硬件能力 | Ada cp.async、warp/block分工和合理tiling；需要独立实现 |
| AMX或要求VBMI/VPOPCNTDQ的CPU TU | 4216不满足 | 独立no-VBMI VNNI、AVX2、任务/内存优化 |
| 补满6内存通道、更换CPU/GPU | 属硬件升级，不是当前软件任务 | 36GB/s作为资源约束；软件减少字节与争用，不创造通道 |
| SSD权重按需流式 | 当前模型CPU权重已经主要驻RAM，未证明需要 | 若将来RAM不足，另建mmap/pagecache/prefetch成本实验；不套新DeepSeek大RAMcopy-all |
| 换小模型、蒸馏、额外draft训练 | 改模型/增加训练投入 | P04/P10单列研究资格，不混同同权重无损加速 |
| prompt删减、输出变短、思考预算缩短 | 改请求/任务语义 | Q轨道报告独立速度—质量结果 |
| 任意fast-math、state降精度、跳专家/层 | 改数值/计算合同 | 独立N/Q测试，先量化误差与完整任务质量 |

[官方Ada调优](https://docs.nvidia.com/cuda/ada-tuning-guide/index.html)给出sm89的寄存器/warp/shared memory约束；[Intel4216规格](https://www.intel.com/content/www/us/en/products/sku/193394/intel-xeon-silver-4216-processor-22m-cache-2-10-ghz/specifications.html)确认16核/32线程、DDR4-2400、六通道能力和PCIe3.0。实际已装DIMM与PCIe链路仍以目标机inventory为准。

## 不使用“最佳引擎排行榜”替代实施设计

不同模型、quant、prompt、输出、spec、并发和质量门的tokens/s不可横比。对当前任务，最有价值的比较是机制能否进入真实调用链、是否适合4216+4090资源比例、迁移要改多少状态合同、以及真实任务wall能否改善。换语言、换编译器或换引擎名字本身不产生收益。

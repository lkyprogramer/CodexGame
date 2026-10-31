# 07 · 外部引擎的真实差量与移植边界

本节的“存在”指固定提交的定点源码检查；不表示CUDA12.3编译、RTX4090运行或用户题集质量通过。完整身份见[LOCK](../sources/LOCK.json)，逐来源见[来源索引](../sources/EVIDENCE_INDEX.md)。所有性能数字都要区分作者机器、模型、精度、上下文、采样和引擎版本。

## 1. 对照结论

| 引擎/机制 | 已核实的事实 | 相对本机基线的结论 | 后续入口 |
|---|---|---|---|
| Strata分组专家与融合GU | 共享权重解包、GU/SwiGLU/q8_1融合已经存在；EXACT6开启有关路径 | 重写整套融合不是新方向；只能找既有融合内部的新load/layout差量 | F02，需实际热点资格 |
| Strata QSA | selected宽度最多2051；现有CHUNK64 split/merge、GQA复用、host页缓存 | 不能套用dense128K attention结论；SELECT_LONG亦非4090即开开关 | F01/F04 |
| tqLLM compact gather | 选中行打标、压紧、cache填充、canonical位置remap已实现 | Strata A0和P6已有选择页去重/staging/CLOCK；新增源码不等于新机会 | 仅用于F01差量审计 |
| Maya GLM中间workspace行窗 | 存在窗口式MoE workspace、分段combine | Qwen P6相应中间缓冲仍按T×K；保留全Dm的窄派生有实现差量 | F05，偏prefill，未获资格 |
| Maya整数count/rank/scatter | GPU生成稳定整数分组，host规划专家边界 | P6已有mapped tables及部分fused::group；只剩非fused host分组差量 | F06，先证明暴露时间 |
| Maya MMQ pool | 2次幂sizeclass、slab借用MMQ scratch | P6有cache allocator，无相同sizeclass/slab机制 | F07，先证明预算/alloc成本 |
| Maya按rows与未完成复制债务分配CPU/GPU | 动态成本模型真实存在 | 改变数值分派；不能作为NP3/固定分担重跑的别名 | F08，E1延期 |
| Edge0 MLX prerouter/staged | trained predictor可替换真实gate；staged miss可落零overflow | 不是现用Qwen top10的无损预取插件 | 不移植其默认语义 |
| Edge0 Windows resolver | true gate保留；命中私有arena，否则等待/同步读/原mmap fallback | 精确需求回退合同值得借鉴，但实现属于Windows CPU文件IO | F12仅作合同参考 |
| HyperQwen/elpis | draft、低比特KV、kernel研究可参考 | 模型、采样或数值前提不同，不能把作者吞吐移到本机 | F09–F11延期 |
| kern | teacher-forced验证、ABI/layout合同有价值 | 不等于本机mixed CPU/GPU、Flash-Next性能资格 | 验证方法参考 |
| NVIDIA spark/原flare | 图与状态生命周期设计可参考 | 现成kernel面向SM120/121，不是SM89可直接使用路径 | 不移植未支持指令 |

上述对照的具体证据和推断如下。

## 2. tqLLM：源码有新增，但核心问题基线已解决过

固定提交为`b35b2ce9df8927c672f888651946849219a0effa`，旧v2 pin为`c2163c2da408603331a5814f62fd1f287f54370b`。新增host-KV工作可追到`54f71b6c…`。`QsaGather::run`在donor自己的KV表示下完成标记、scan、行汇聚、cache填充与位置remap；调用层有host-backed VMM条件、16384-row cache和epoch。它没有证明原有Strata整机欠缺同类逻辑。[实现](https://github.com/turbo-tan/tqllm/blob/b35b2ce9df8927c672f888651946849219a0effa/src/models/qwen/qwen4exp/qwen4exp_qsa.cu)、[调用层](https://github.com/turbo-tan/tqllm/blob/b35b2ce9df8927c672f888651946849219a0effa/src/models/qwen/qwen4exp/fn_layers.hpp)、[差量提交](https://github.com/turbo-tan/tqllm/commit/54f71b6cdc1351bfd7e13cb4d2345cd4ad5c5973)。

更关键的对照是Strata的`src/kernels/cuda/kv_stream.cu`：A0与P6的Git blob均为`209984b4ff1b54a824f26861a487ce4e943902f0`，长度12980 bytes。已有4cell page、跨query去重、当前epoch pin、CLOCK淘汰、16-byte搬运、host authoritative数据与resident一致性维护。P6运行记录也显示KVRES20480生效。因此，“先把散乱host KV聚到GPU再做attention”并不是待补的空白。[A0](https://github.com/Niko1221/Strata/blob/5c8dd322528cc84f68f461ad54a506b9da8fa8d4/src/kernels/cuda/kv_stream.cu)、[P6](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/kernels/cuda/kv_stream.cu)、[P6启动证据](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P6-V027-BASELINE-20261028.md)。

可剩下的问题只是更窄的差量：实际必要页是否反复搬运，命中维护是否正确，跨query重复load是否暴露。必须分别测resolve/copy/attention和其依赖，保留canonical selected顺序、causal mask及原规约。不能把resolve epoch误作“每轮旧数据均失效”的generation。

donor文档中128K的77.1 vs 47.2 tok/s来自RTX3090、IQ3_S、greedy以及Strata0.2.2对照；该表相对旧pin并未新增。作者109GB RAM上限或256K探索也不对应本机约62GiB可见RAM。它们不能成为这轮收益预测。[作者基准](https://github.com/turbo-tan/tqllm/blob/b35b2ce9df8927c672f888651946849219a0effa/docs/BENCHMARKS.md)、[变更记录](https://github.com/turbo-tan/tqllm/blob/b35b2ce9df8927c672f888651946849219a0effa/CHANGELOG.md)。

## 3. Maya：保留三个有实现差量的prefill分支

### 3.1 中间group scratch：移植生命周期思想，不照抄GLM数学

Maya `glm_prefill.cu`的`moe_window_rows/carve_moe/place/flush/run_set`把窗口作为MoE中间workspace管理单位。P6 `prefill.cpp`的`moe_bufs/moe_set_bytes`相应定义与A0相同，非fused GU/H/Xq/Hq仍以T×K规模分配。这是一个真实源码差量。[Maya](https://github.com/mw00/project-maya/blob/376b4b87402bc992af7b4a8dec089ef7cba7801c/src/core/glm_prefill.cu)、[P6](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/prefill/prefill.cpp)。

然而完整GLM方案会把窗口的部分输出累加；GLM的K≤8与本机Qwen的K10不等价。保守新设计保留全尺寸Dm、原始expert排序和k0…9 combine，仅复用完成最后消费者后的GU/H/Xq/Hq。每个原MMQ调用的shape、量化和规约顺序也保持；如果容量约束迫使拆MMQ group，就不能自称E0。[GLM combine](https://github.com/mw00/project-maya/blob/376b4b87402bc992af7b4a8dec089ef7cba7801c/src/kernels/cuda/glm_batch.cu)、[F05合同](../candidates/F05_MOE_GROUP_SCRATCH.md)。

收益上限首先受尺寸账限制：仅T16384×K10×N2560×FP32的Dm就是1.5625GiB；这不是可省量。有效scratch是GDN/QSA/MoE三路最大项，不能把每路相加。MoE不是最大项、AUTOMAX而非内存限制chunk、或释放空间不能减少真实借槽/回填/缺页时，方向即失去性能资格。

### 3.2 稳定整数分组：真实基线已经有mapped tables

Maya在GPU对每expert生成稳定`(token,k)`顺序的rank/count，host读取O(E) counts并规划分组，然后GPU scatter。迁移整数metadata在原则上可保数值；迁移GLM router则不可。[分组kernel](https://github.com/mw00/project-maya/blob/376b4b87402bc992af7b4a8dec089ef7cba7801c/src/kernels/cuda/glm_batch.cu)。

A0和P6已经默认尝试mapped pinned group tables，`STRATA_GROUP_COPY=1`可强制复制对照；mapped失败或force_pageable也可能回退copies，需核实际grp_mapped。部分路径已有`fused::group`。所以只准针对实际非fused host histogram/scatter研究，不能把普通D2H/H2D删除冒充差量。Maya的每expert扫描方法在512×16384×10下约8388万entry检查，仍有host counts/plan同步，CPUshare也仍需原row mapping。必须比较整条链的暴露成本。[P6调用链](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/prefill/prefill.cpp)、[F06合同](../candidates/F06_STABLE_INTEGER_GROUPING.md)。

### 3.3 MMQ allocator：已有缓存上的尺寸分级与生命周期补充

P6 `ggml_cuda_host.cu`与A0相同，已经能复用足够大的空闲buffer，不能说每次都cudaMalloc。Maya增加最小128KiB的2次幂sizeclass，以及允许MMQ fixup借用当前loan尾部的slab入口。[Maya pool](https://github.com/mw00/project-maya/blob/376b4b87402bc992af7b4a8dec089ef7cba7801c/src/prefill/ggml_cuda_host.cu)、[P6 pool](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/prefill/ggml_cuda_host.cu)。

先用真实申请序列评估sizeclass，单独算向上取整碎片。只有仍存在预算或hot allocation问题，才考虑slab。新增合同必须验证epoch+base+range和全部消费者fence；相同虚拟地址可能已属新一代loan。不能照搬donor按base变化失效的边界，也不能把30SM示例的16MiB上限用于4090的128SM。这里指出的是移植必须证明的合同，不是宣布donor已存在一个复现bug。[F07合同](../candidates/F07_MMQ_POOL_EPOCH.md)。

三个分支都主要影响prefill/长append。当前限定warm decode诊断没有提供它们的硬件资格；不能因源码差量存在就自动开启一次长冷读campaign。

## 4. Edge0：必须分开平台和路由语义

MLX路径`_patch_qwen_consume`在有prediction时使用预测expert IDs/scores，替换真实gate；实际路由专家未命中staged slots时可映射到zero overflow，并不总有精确miss fallback。模型配置、trained prerouter/LoRA、top-k和后端都不同。默认预测替代true router、以及zero/drop contribution属于Q，不能称为只提前搬权重；单独拆出的组织性复用须按实际数值变化另判。[prerouter](https://github.com/Edge0-AI/Edge0/blob/d4a2fa02fcf06c08961248a2da1d8fc861d842ef/python/src/edge0/prerouter/install.py)、[streaming](https://github.com/Edge0-AI/Edge0/blob/d4a2fa02fcf06c08961248a2da1d8fc861d842ef/python/src/edge0/streaming/layer.py)。

Windows `e0_mmid_base_res`不同：挂在CPU MUL_MAT_ID基础地址解析处，true gate保留，预测只给IO提示。ready可命中私有arena，inflight要等待，cold可同步ReadFile；预算、layout或读取失败时回到原mmap基址。这个“预测错误只损失预取收益，真实需求仍可完成”的设计合同有价值，但不能直接移植Win32 CPU文件IO到CUDA expert staging。Mac StepPrefetch的FIFO和ticket取消也不等于已有面向关键路径的deadline scheduler。[Windows resolver](https://github.com/Edge0-AI/Edge0/blob/d4a2fa02fcf06c08961248a2da1d8fc861d842ef/windows/serve/prefetch.cc)、[Mac队列](https://github.com/Edge0-AI/Edge0/blob/d4a2fa02fcf06c08961248a2da1d8fc861d842ef/macos/crates/engine-native/src/stepprefetch.cpp)。

本机已有graph、grouped专家、DMA握手和多种缓存。只有新的重复物化/描述符构建或无效同步确实暴露，才能在F12做保留true route的窄改造；否则不创建新缓存系统。

## 5. 最底层内核还剩什么条件空间

Strata `native_gu_swiglu_kernel`的融合已经覆盖GU→SwiGLU→q8_1；`EXPDEC`还会压掉GU_SWIGLU，二者不是可叠加开关。作者自己的Q2_0 down微基准改善也曾在完整引擎回退。这与NP-1a“更快的分支没有实际命中”的教训一致。[内核](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/src/kernels/cuda/iq_kernels.cu)、[作者EXPDEC记录](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/docs/EXPERTDEC.md)。

因此F02只保留既有融合内的加载对齐、同字节数跨row布局、已有activation读取复用等窄假说。维持整数code/scale、乘加和量化次序，确认register spill、occupancy、额外cache或复制不抵消收益。SM60 nibble是无损权重编码的证明参考，但其GU可能膨胀1.25–1.68倍，当前实现也受SM60门控制；在64GB机器复制一份膨胀模型并非免费。[nibble](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/include/strata/core/expert_nibble.hpp)。

llama.cpp的IQ4_NL 8-row interleave可参考表示方法，不能直接冒充IQ3_S singleton优化；tiled IQ3_S需要足够行批次，而真实nt分布要重查。P5没有给扩格式/nt/prepack任何新的资格；P12的gather回退仍是硬负证据。[repack](https://github.com/ggml-org/llama.cpp/blob/3c809f44383bcebc318b8cddd8c6d11aaa861e9b/ggml/src/ggml-cpu/repack.cpp)、[tiled](https://github.com/ggml-org/llama.cpp/blob/3c809f44383bcebc318b8cddd8c6d11aaa861e9b/ggml/src/ggml-cpu/tiled/tiled.cpp)。

QSA方向只准先检查跨query selected-load复用和严格等序选择；改成TC hi+lo、改exp或规约，即使selected IDs相同也已是E1。SELECT_LONG/DX的现成SM60门不能只删除宏就在sm89宣称可用。[QSA选择](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/src/kernels/cuda/qsa_select.cu)、[TC attention](https://github.com/Niko1221/Strata/blob/870aedd9e1ebe1c91f94da93b59af17729f6c5c0/src/kernels/cuda/qsa_prompt_attn.cu)。

## 6. 其他引擎与跨平台倍率的处置

HyperQwen的draft/词表和长上下文经验可借鉴，但对象含dense27B及特定草稿；elpis对目标数值、KV精度与greedy约束也有自己的边界。本包不宣称其draft资产已经兼容Flash-Next，不把target量化与draft近似混在一起。[HyperQwen drafter](https://github.com/syv-ai/HyperQwen/blob/ce9615c4f2309be727407918a6c979bd67968069/drafter/README.md)、[长上下文](https://github.com/syv-ai/HyperQwen/blob/ce9615c4f2309be727407918a6c979bd67968069/docs/long-context.md)、[elpis](https://github.com/gildrb/elpis/blob/13e8b593ea4c65f605b5fe7ac7d5ebb7a24f3c19/README.md)。

kern的teacher-forced/A/A比较适合补充数值审计，但KL/logits接近不等于任务质量非劣。NVIDIA spark（原flare）的现成kernel面向SM120/121；CUDA12.3/sm89不能因README吞吐高就获得硬件能力。[kern测试](https://github.com/pegainfer-project/kern/blob/5d0910c5e5beef5b1b204853ad65f3e1fe994777/docs/test.md)、[spark](https://github.com/NVIDIA/spark-local-inference/blob/a161b17f3ef3ac5c0cd3e219719f7d1d36a01175/README.md)。

KTransformers在旧包中仅属迁移分析，本次没有获得同模型、同配置、同质量/资源约束的新对照。迁移整引擎不应伪装成低风险下一项优化；若另立研究，需要独立证明模型、量化、MTP、Pi协议、128K和64GB RAM均适配。本包不以“未审查完”推断其已无潜力。

所有donor的共同落地条件都是：相对P6存在差量、当前实际命中、因果暴露时间足够、表示/状态/资源可证明、完整请求验收通过。没有这条证据链，就保留为源码参考，不消耗新的GPU实验轮次。

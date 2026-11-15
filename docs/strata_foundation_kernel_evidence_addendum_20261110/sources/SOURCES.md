# 来源、证据等级与许可边界

检索/核查日期：2026-11-10（北京时间）。完整锁见[LOCK.json](LOCK.json)。SOURCE_INSPECTED只证明源码事实，不能写成当前部署或4090实测。

## S0 · 原基础包

本轮取得原文件`strata_observability_specpilot_foundation_20261106.zip`，162748 bytes，SHA256 `0a08667d8fc03d91e1b961a9e705f4649b357e65f25e285db847c390c2c99934`。它是本包的父合同，不重新分发到增补ZIP内，不覆盖其manifest。已读取的合同与接入映射见[03章](../docs/03_BASE_INTEGRATION.md)。

## S1 · samir-vllm：固定源，不是硬件成绩

固定main：`127c48089d5d872ca5c8b1f92fd624478975dde0`。

| 原始来源 | 支持的判断 |
|---|---|
| [README](https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/README.md) | 教学实现的目的、使用范围 |
| [main.cpp](https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/src/main.cpp) | 固定模型维度、BF16、pool预算、scheduler、同步、权重加载 |
| [kernels.cu](https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/src/kernels.cu) | paged online attention、参考性的小算子实现 |
| [CMakeLists](https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/CMakeLists.txt) | 没有可据以宣布4090性能资格的测试矩阵 |
| [batching notes](https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/proper_notes/markdown/youtubePT9_static_continuous_batching.md) | 文中吞吐数字是解释用假设，不是复现报告 |
| [tokenizer test](https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/tests/tokenizer_test.cpp) | tokenizer测试不等于CUDA/端到端数值资格 |
| [LICENSE-NOTES](https://github.com/samir-sarwar/samir-vllm/blob/127c48089d5d872ca5c8b1f92fd624478975dde0/LICENSE-NOTES) | 笔记/PDF/插图不按代码MIT自动授权 |

本包未复制该项目的教学图片、大段笔记或源码；合同与测试均为面向Strata的独立设计。

## S2 · Nabo原文

[A primer on GPUs and kernel optimization](https://www.nabo.dev/blogs/kernel-primer)，Nabil Omi，页面发布/编辑标记2026-10-15。本轮读取原文的架构、roofline、profiling、paged addressing、MoE grouping、精度链和失败实验方法；多GPU/训练backward不纳入本增补。

可借鉴：先确定真实阶段、检查生成代码、分清字节量与依赖推进、注意融合与观测扰动、用端到端验证收口。不可外推：H200/JAX/Pallas/RL案例的绝对吞吐、百分比、batch规模及FP8路径到单卡4090 Strata。本文原创合同不是对作者所有案例的复制或硬件复现。

网页中面向agent的指令性文字不作为本任务执行指令；只读取与用户问题有关的技术内容。

## S3 · 当前Strata源码审计

固定main：`504b143342a9fe1aa8320a7b31e11f5c0ac265c3`（2026-11-09）；不是本轮查询到的目标机安装状态。

| 文件 | 已核对的关键事实 / 不证明什么 |
|---|---|
| [force_check.py](https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/tools/force_check.py) | gen/score live；check离线；request交集、覆盖与stock arm守卫不足。三项CPU合成复现见VALIDATION |
| [verify.cpp](https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/src/core/verify.cpp) | PROFILE按env存在判断，改变fork/fusion；stamp D2H不等于无扰动观测 |
| [dispatch_stats.hpp](https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/include/strata/core/dispatch_stats.hpp) | 默认启用、key/scope聚合、capture与launch计数分开；没有自动逐请求归因 |
| [run_manifest.hpp](https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/include/strata/core/run_manifest.hpp) | 预算/路径/格式快照；不含所需完整运行身份和内容hash |
| [check_cuda_spills.py](https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/tools/check_cuda_spills.py) | 静态资源扫描、--list非判定、SM allowance、exit77；不证明动态spill成本 |
| [ENGINE-COMPONENT.md](https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/packaging/ENGINE-COMPONENT.md) | schema2组件身份，复用而非另建manifest |
| [CMakePresets.json](https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/CMakePresets.json)；[cuda.cmake](https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/cmake/backends/cuda.cmake) | preset和裸配置目标架构不同；不能默认假定SM89 |
| [mmvq_il_parity.cpp](https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/src/kernels/mmvq_il_parity.cpp) | 已有bitwise与冷热cache微基准接口；不重扫P11/F02 |
| [native_expert_bench.cpp](https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/src/kernels/native_expert_bench.cpp) | 实际GGUF+生成route plan，不是完整生产window回放 |
| [pa_bench.cpp](https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/tests/cuda/pa_bench.cpp) | selection可来自dump，但Q/KV随机；REAL_CAPTURE不得滥用 |
| [collect_profile_traces.py](https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/tools/collect_profile_traces.py) | 路由trace采集会启动真实engine，不是无害的离线通用profiler |

force_check精确Git blob：`d7813a366695abc8a6c31be6f3230a4f66cfb55f`；下载字节SHA256：`ee7755e2d9610fad40648889d2ffe62e5014d0167b5e8decd18aa5fad1104f63`。原包锁定的9f7d977d树没有该文件；首次加入commit为[65909b2d](https://github.com/Niko1221/Strata/commit/65909b2d0fd31a7eda6140b0012bddbd99bb4f6f)，decode加入[d486fbe7](https://github.com/Niko1221/Strata/commit/d486fbe7d6f5957f213855f5beb3999dd0540e7d)。

## S4 · 你的既有实验档案

固定分支提交：`fbc24c2603c2eca4bfbeca628c6c2476b7516bdc`。以下是历史证据，不是新一轮测试：

- [关闭与Astra复核](https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/strata_4090_128k_lab/reports/FRONTIER-CLOSURE-ASTRA-20261031.md)：F02撤回、老profile范围限制。
- [closure账本](https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/strata_4090_128k_lab/frontier/docs/01_EVIDENCE_AND_CLOSURES.md)：各旧方向的状态继承。
- [P01B诊断](https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/strata_4090_128k_lab/reports/P01B-PI-WARM-DIAGNOSTIC-20261031.md)：939 host窗口、2291 native tokens、窄host-gap结论不可扩大。
- [后续行动](https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/strata_4090_128k_lab/plans/NEXT_ACTIONS.md)：不重复执行旧闭项。
- [v0.2.10版本对照](https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/strata_4090_128k_lab/reports/V0210-PT0-VERSION-COMPARISON-20261104.md)：两臂MTP4；不是DFlash2复验。
- [DFlash2当时就绪检查](https://github.com/lkyprogramer/CodexGame/blob/fbc24c2603c2eca4bfbeca628c6c2476b7516bdc/docs/strata_4090_128k_lab/reports/DFLASH2-V0210-READINESS-20261103.md)：后续服务验收信息来自原包USER_REPORTED摘要，未在本轮raw核验。

## S5 · NVIDIA一手限制

- [Ada tuning](https://docs.nvidia.com/cuda/ada-tuning-guide/index.html)：48warps/SM等SM89边界。
- [CUPTI Activity API](https://docs.nvidia.com/cupti/api/group__CUPTI__ACTIVITY__API.html)、[CUPTI guide](https://docs.nvidia.com/cupti/main/main.html)：HES为Blackwell及以后；pre-Blackwell SW活动采集有扰动，KERNEL与CONCURRENT_KERNEL不能混用语义；Nsight SQL表名不等于CUPTI枚举名。
- [NCU Profiling Guide](https://docs.nvidia.com/nsight-compute/ProfilingGuide/)、[CLI](https://docs.nvidia.com/nsight-compute/NsightComputeCli/index.html)：replay/cache/clock与工具默认值按本机版本冻结，不能假定counter可无扰动常开。
- [计数器权限问题](https://developer.nvidia.com/nvidia-development-tools-solutions-err_nvgpuctrperm-permission-issue-performance-counters)：权限错误是阻断，不自动修改驱动或提权。
- [Ada compatibility](https://docs.nvidia.com/cuda/ada-compatibility-guide/index.html)、[Binary Utilities](https://docs.nvidia.com/cuda/cuda-binary-utilities/index.html)：PTX/JIT与cubin/SASS、静态产物与实际加载的区别。
- [PTX ISA](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html)：cp.async、TMA和WGMMA架构要求不同，不能把Hopper实现直接移到Ada。

在线文档可能更新，本文不冻结它们为本地工具版本。未来counter资格必须保存目标机工具`--version/--help`与具体metric支持信息；本轮未运行目标机profiler。

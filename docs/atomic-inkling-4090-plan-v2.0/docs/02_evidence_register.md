# 02 · 一手证据登记与事实边界

核查截至2026-11-26（Asia/Shanghai）。本包同时参考官方文档、固定源码、模型配置与作者实验，未进行目标4090推理。事实、推断和本方案门槛分开使用。

## 1. 来源索引

| ID | 来源与固定入口 | 本包据此使用的事实 |
|---|---|---|
| S01 | [Atomic固定源码](https://github.com/AtomicBot-ai/atomic-engine/tree/fb69fff02101b048a0a165a3b502712dd2ca978f) | 底座、模型图、预算、Metal/CUDA能力边界 |
| S02 | [正式Mini config](https://huggingface.co/thinkingmachines/Inkling-2-Mini/blob/c9d028302cd0f035fdf8e7e91f089a4ce94d2195/config.json)；[模型卡](https://huggingface.co/thinkingmachines/Inkling-2-Mini) | 24物理层、固定R3、is_varloop=false；官方上下文与部署说明 |
| S03 | [varloop config](https://huggingface.co/thinkingmachines/TML-d24-varloop-research/blob/91a57fe2b779bbd12c0f74d1f518cbd5b84e8d0d/config.json)；[模型卡](https://huggingface.co/thinkingmachines/TML-d24-varloop-research) | 独立研究checkpoint、可变循环、不同后期训练 |
| S04 | [NVIDIA GPU能力表](https://www.nvidia.com/content/cuda/cuda-gpus.html)；[Ada指南](https://docs.nvidia.com/cuda/ada-tuning-guide/)；[PDL](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/programmatic-dependent-launch.html)；[异步复制/TMA](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/async-copies.html) | RTX4090=CC8.9；Ada特征；PDL/TMA的9.0门槛 |
| S05 | [squid5090固定源码](https://github.com/tensorfish/squid5090/tree/51b85dd17e719a45e93e77a9e49df94c50144b30) | Blackwell目标、图/arena/lookup与专家kernel可参考机制 |
| S06 | [2DSD固定源码](https://github.com/SqueezeAILab/2DSD/tree/431aade2f1e8ebc98a31158d53c39e554984a83a) | registry、tree scheduler、实际proposal与shared-KV约束 |
| S07 | [2DSD模型集合](https://huggingface.co/collections/minseo25/2dsd) | 已发布模型/草稿器入口；集合会变化，运行依赖具体revision |
| S08 | [Inkling 2DSD草稿器](https://huggingface.co/minseo25/2dsd-inkling-2-mini-varloop-dspark-drafter/tree/fe3e545788b84e879f3eb8b8f426aaceb5fb44c5) | 作者报告与5层草稿资产，per-loop目标 |
| S09 | [草稿器固定config](https://huggingface.co/minseo25/2dsd-inkling-2-mini-varloop-dspark-drafter/blob/fe3e545788b84e879f3eb8b8f426aaceb5fb44c5/config.json)；[指定训练target](https://huggingface.co/thinkingmachines/TML-d24-varloop-research/tree/657b53ba5da7baefe9ff15dca5cd25f5bd3dbaa2) | feature/head区别及不可替换的训练target pin |
| S10 | [LoopCD指定论文](https://arxiv.org/abs/2610.02185v1)；[HTML全文](https://arxiv.org/html/2610.02185v1) | Liu等，Decoding Looped Transformers Better for (Almost) Free；公式/成本/实验范围 |
| S11 | [Transformers PR51161](https://github.com/huggingface/transformers/pull/51161)；[固定head](https://github.com/huggingface/transformers/tree/228bb636a3809f1a46f6f9d4011dfbff89416e5c) | last_loop、conv独立、A100数据与static mask修复 |
| S12 | [llama.cpp PR32218](https://github.com/ggml-org/llama.cpp/pull/32218) | Atomic DSpark文件头所注明的上游来源；具体归属以文件头revision为准 |
| S13 | [TurboQuant来源](https://github.com/TheTom/llama-cpp-turboquant) | Atomic README明确致谢的KV/压缩来源；本包未锁定可直接移植版本 |
| S14 | [vLLM官方day-0文档](https://vllm-project.github.io/2026/11/20/inkling2-mini.html) | loop/controller语义、原生DSpark默认R限制、参考优化 |
| S15 | [Atomic README资产revision](https://huggingface.co/AtomicChat/Inkling-2-Mini-GGUF/tree/309509848b3151419aa26d069eb03db57fd29a00) | 已核实IQ2_M与Q8_0原生草稿文件入口 |
| S16 | [Atomic原始Metal跑分JSON](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/docs/atomic-engine-inkling-low-bit-metal.json) | 4000输入/64输出、旧folded draft和模型revision、接受率、逻辑读取 |
| S17 | [ARLoop论文](https://arxiv.org/abs/2611.05234v1)；[固定代码](https://github.com/OSU-NLP-Group/ARLoop/tree/16c8eaa6e841a6203a068c23394e0dbe69b08c55) | 独立循环架构的小模型验证载体，不是Inkling插件 |
| S18 | [Ghost固定main](https://github.com/affifuddin-hazam/ghost-infer/tree/b6cd02e099af2453f3674e047d5f89152f8a662d) | 最新公开官方分支、Inkling专用与通用路径、实现边界 |
| S19 | [Ghost v0.5.0](https://github.com/affifuddin-hazam/ghost-infer/releases/tag/v0.5.0) | 发布口径、作者8GB硬件数字；与main仅文档不同 |
| S20 | [Ghost Linux PR7](https://github.com/affifuddin-hazam/ghost-infer/pull/7) | fork linux head与已合并历史；不是另一个live官方分支 |
| S21 | [Ghost parking PR2](https://github.com/affifuddin-hazam/ghost-infer/pull/2) | closed/unmerged设计来源；main实际实现独立核查 |
| S22 | [NVIDIA CUDA Rust v1.2历史main](https://github.com/NVIDIA/cuda-rust/tree/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b) | 历史141文件审计pin；新工作以S45为准，不能转授旧证明/CI资格 |
| S23 | [Provably Safe and Fast GPU Kernels in Rust](https://nihalpasham.github.io/posts/provably-safe-gpu-kernels/?v=3) | 作者所述安全编译与B200微基准；不外推4090或Inkling |
| S24 | [CUDA oxide proof hardening PR1857](https://github.com/NVIDIA/cuda-rust/pull/1857) | 11类hardening已squash合入；head/main完整blob树相同 |
| S25 | [CUDA oxide latest release](https://github.com/NVIDIA/cuda-rust/tree/9d0c9bfbc954a9a29565ab81b78da70f054d8e04) | oxide发布身份；不能用较旧release代表当前proof main |
| S26 | [cutile-rs latest release](https://github.com/NVIDIA/cuda-rust/tree/e706cab335828f6be1a6d5990e7a9c2ce08e1cb0) | Tile发布身份与annotated tag解引用 |
| S27 | [Compute Sanitizer](https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/) | mem/race/init/sync工具范围、error-exitcode默认0 |
| S28 | [Nsight Compute Profiling Guide](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html) | replay、cache/clock与采样开销；诊断与正式计时分开 |
| S29 | [CUDA Minor Version Compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/latest/minor-version-compatibility.html) | CUDA13.x通用R580门槛、PTX与新功能兼容限制 |
| S30 | [PTX ISA](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html) | 具体指令形式、目标架构与同步语义 |
| S31 | [CUDA Driver Module Management](https://docs.nvidia.com/cuda/cuda-driver-api/cuda_driver_api/group__CUDA__MODULE.html) | PTX/cubin加载当前context、driver错误边界 |
| S32 | [CUDA Graphs](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/cuda-graphs.html) | capture/update/graph lifetime；项目lease额外合同 |
| S33 | [CUDA 13.2 GA Release Notes](https://docs.nvidia.com/cuda/archive/13.2.0/cuda-toolkit-release-notes/index.html) | 13.2GA对应Linux driver595.45.04+；非现场探针 |
| S34 | [CUDA Runtime Driver Interoperability](https://docs.nvidia.com/cuda/cuda-runtime-api/cuda_runtime_api/group__CUDART__DRIVER.html) | Runtime/Driver同context互操作与线程current context |
| S35 | [Nsight Systems User Guide](https://docs.nvidia.com/nsight-systems/UserGuide/index.html) | 完整请求trace、CUDA Graph观测粒度与开销 |
| S36 | [LoomKV](https://arxiv.org/abs/2611.32954v1) | Tier / Pool分离、压缩格式、容量与H800实验；4090效果未测 |
| S37 | [GAAC paper](https://arxiv.org/abs/2610.38210v2) | GAAC算法与作者实验；源码支持范围需另查S38 |
| S38 | [GAAC current main](https://github.com/Intelligent-Microsystems-Lab/GAAC/tree/a2cbcb5eb22b2bf08bb614a01189163b85c07cdd) | BF16、head/scale/escape/allocator实际约束与静态风险 |
| S39 | [SplitZip paper](https://arxiv.org/abs/2605.01708v4) | SplitZip算法与论文测量条件 |
| S40 | [SplitZip current main](https://github.com/Intelligent-Microsystems-Lab/SplitZip/tree/f6960f1487ab4a056f8565d749d355739dc8394a) | BF16与新增FP8路径；码本、尾部、同步和扩张边界 |
| S41 | [ZipFusion](https://arxiv.org/abs/2610.33719v1) | 融合解压Attention；官方公开实现未确认 |
| S42 | [ZipServ paper](https://arxiv.org/abs/2603.17435v1) | BF16权重压缩与融合GEMM；并非KV缓存系统 |
| S43 | [ZipServ current main](https://github.com/HPMLL/ZipServ_ASPLOS26/tree/15378387cb09634527ab0b20b7abfc9ffd5b62c5) | SM89编译目标与BF16实现边界；未本机执行 |
| S44 | [2DSD public Inkling experimental branch](https://github.com/SqueezeAILab/2DSD/tree/962874f303c3142406ab3eecfae2bb51567815c9) | 已公开Inkling实验runner；正式Mini无默认匹配2DSD drafter；撤销统一缺码阻塞 |
| S45 | [NVIDIA CUDA Rust current main at v2 audit](https://github.com/NVIDIA/cuda-rust/tree/f35d6ccc2e03a54e73e3796f415f11313e439d50) | #1866后当前main；相对S22的14文件增量审计 |
| S46 | [CUDA oxide writer coverage fix PR1866](https://github.com/NVIDIA/cuda-rust/pull/1866) | 写入witness、前置assert、仅1D writes_all_elems；不扩大证明范围 |
| S47 | [Magnitude current main](https://github.com/magnitudedev/magnitude/tree/3aba40fda19fdaacc345c91c5e711a3bca2f9ee3) | 统一ledger、传输退休、专家回放、cost epoch与Pi观测；当前无Inkling注册 |

`manifests/source-lock.json`记录核心pin；[source-audit.json](../manifests/source-audit.json)记录49项Atomic/squid静态核查路径与Git blob SHA。Git blob SHA不等于下载模型文件的SHA256，也不代表二进制或GPU资格。

## 2. Atomic关键代码的固定链接

- [预算CLI/model分派](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/common/atomic-budget.cpp)
- [loader与Inkling Metal gate](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-model.cpp)
- [loop映射与控制](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/models/inkling2-loop.cpp)
- [core banks](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-inkling-core-banks.h)
- [DSpark模型图](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/models/inkling2-dspark.cpp)
- [预算DSpark context入口](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-context-atomic.cpp)
- [expert store](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-expert-store.cpp)
- [host/device ledger](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-memory-budget.h)
- [SWA容量实现](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/src/llama-kv-cache-iswa.cpp)
- [折叠旧式草稿head工具](https://github.com/AtomicBot-ai/atomic-engine/blob/fb69fff02101b048a0a165a3b502712dd2ca978f/tools/expert-source/fold-inkling-dspark.py)

## 3. 已核实的数字，以及不能推出什么

| 作者证据 | 原条件/结果 | 本方案不据此断言 |
|---|---|---|
| Atomic最新README | 48GB M4 Max，IQ2_M+Q8 draft，14GiB+100MiB预算，约105.71tok/s | 4090、128K、Java Agent也有此速度 |
| Atomic原始JSON | 旧revision `4f0c56af...`、folded draft、4000/64；IQ2约33.71→105.49tok/s；draft55/55接受 | 这是独立驻留kernel的3倍收益；最新Q8与旧folded可混为同资产 |
| 2DSD Inkling模型卡 | H100 NVL，greedy、concurrency1；七任务均值AR92.5/MTP257.2/2DSD313.6tok/s | 额外获得3倍或7倍；相对MTP该组约22%，非4090结论 |
| PR51161 | A100 eager，2048+128；dynamic KV232.7→118.8MiB，速度3.92不变；static3.80→3.49 | 总显存减半、decode必定加速、所有采样分布等价 |
| LoopCD论文 | 四类循环模型，报告减半loop时forward FLOPs下降22.5%–48.2% | Inkling已验证、wall time加速2倍或guidance无质量代价 |

Atomic旧跑分对照未启用相同DSpark，短输出、重复fixture和极高接受率限制其代表性；buffered logical reads不能当物理SSD读取。2DSD卡对AR/MTP与自有runner的平均准确率也不同，不能把“本runner内精确”扩成跨引擎相同。全部作者数字只作背景，本包不会填进4090结果表。

## 4. 重要未知项

- 没有目标机当前driver/Toolkit/SSD/可用显存的现场记录。
- 没有Atomic固定commit在这台4090上用选定正式Mini资产的构建、正确性、容量或速度测量。
- 2DSD固定main未集成Inkling，但S44实验分支已有公开runner。正式Mini的匹配drafter、Atomic适配、SM89和完整质量/性能仍未资格；不能再以“仓库完全缺runner”阻塞R03。
- 用户指定LoopCD的官方可归属实现未核实。`byeonghoyu/LoopCD`属于另一篇 [EMNLP论文](https://aclanthology.org/2026.emnlp-main.1367/)，不能替代。
- 2DSD仓库PDF资源存在，本轮没有读取其二进制全文；算法边界以已核查的源码、模型卡与测试为依据。
- 现有NInfer/Strata私有/定制代码在本轮没有审计；仅继承用户给出的业务与历史失败约束。

## 5. 证据更新规则

执行者把新发现写入DECISION记录，保留旧结论的版本和适用条件。上游修复、PR合并或新权重发布只能开启新资格任务，不能追溯性地把旧实验标PASS。任何资料无法访问，记录确切URL与缺失内容；不猜测代码、参数或测量结果。

## 6. Ghost增量证据

v1.1时来源登记21项、机器源锁16项。Ghost固定源、latest tag、PR head与外部CPU CI的可支持范围详见[23](23_ghost_source_audit.md)及[机器审计](../manifests/ghost-source-audit.json)。现有Atomic engine-development重新核对仍为S01固定SHA。作者8GB数据、外部CI与本次静态审计不得填入目标4090的run测量字段。


## 7. v1.2来源与执行边界

v1.2当时来源登记35项、机器源锁30项；[CUDA Rust审计](../manifests/cuda-rust-source-audit.json)合并去重141份固定main源码，逐文件核对Git blob与SHA256。原Atomic/squid49项、Ghost34项继续保留。文件hash证明读取版本，不证明源代码无缺陷或目标性能。

历史S22 main本身为PR1857 squash提交；`fix/oxide-proofs-hardening`历史ahead2/behind1但5350个blob逐路径相同，不能据此称有未合入修复。Lean证明、GPU-less safe examples、历史Blackwell Tile GPU CI分别记录在[外部CI观察](../validation/cuda-rust-ci-observed.json)，没有SM89现场资格。更多当前版本、编译/证明范围和原文数字边界见[27](27_cuda_rust_source_audit.md)。

## 8. v2.0 新证据与纠正

当前登记47项来源、42项机器源锁。新增LoomKV及相关codec的论文/源码、2DSD实验分支、CUDA Rust后续修复与Magnitude。机器证据分别位于 [lossless-source-audit](../manifests/lossless-source-audit.json)、[upstream-refresh-audit](../manifests/upstream-refresh-audit.json)、[Magnitude pins](../manifests/magnitude-source-pins.json) 和 [Magnitude发现](../manifests/magnitude-source-audit.json)。

2DSD分支提交早于旧包核查，属于本次补查纠正，不描述成作者刚刚发布。37个新增文件已由完整patch重建并核对Git blob；这不等于整个仓库的构建。CUDA Rust新main的10项Actions success仅为摘要观察，旧141源码和旧日志仍绑定S22。Magnitude49分支及58个源码pin属于静态审计；当前main最近提交为release CI，不能包装成新kernel跑分。

LoomKV论文的约0.71是BF16记录比例；GPU有效容量、分配开销和完整Inkling状态另算。Tier不压缩活动GPU KV；Pool改Attention，输出仅可声明符合数值合同。GAAC/ZipFusion不自动覆盖Inkling的SWA、多token验证和逐loop状态。Magnitude SSD主要面向专家权重，不是L03完整会话SSD恢复的实现证明。

所有来源只能提出候选与资格边界。真实模型/硬件测试目录中的每一项保持NOT_RUN；本轮新完成的只有来源核查、设计与文档工具验证。

> TECHNICAL_REFERENCE_ONLY：以下固定源码/计算/旧论证保留，原先的“当前”时态或阶段要求不再调度任务。当前身份见[证据](../research/05-completed-baseline-and-current-state.md)，执行以[根注册表](../plans/02-task-registry.md)为准。原始字节另保存在本轮403份快照。

# V4 来源锁与证据等级

核对日期：2026-10-21。源码事实来自GitHub连接器固定对象读取；网页只用于官方公开范围与GPU文档的独立核对。不是整仓克隆、编译或运行结果。

## 固定身份

| 对象 | 固定commit | 当前证据状态 |
|---|---|---|
| Flare main | `47581ccac82660953a5b59cb04b2750d64edc97d` | 原V4编写时读取branch ref，commit时间2026-10-21 00:09:31 UTC；后续研究固定该对象 |
| Flare实际依赖FlashInfer fork | `622cec10eb75da189f4dadddabc2d142a33cd211` | F01明确固定；b12x源码在此对象内 |
| NInfer b0-scanner O | `e0b05f7cb46adae2787be2ccbe605e1b0c9b3923` | 原V4编写时重新读取branch ref，与V3相同 |
| NInfer upstream U | `5b99996bc7c1fe6ff27f271a205eb605302ec8bb` | 原V4编写时重新读取tensorninja ref，与V3相同 |
| NInfer共同祖先B | `44a2c6c3392c9d51e76a895ed97bf1867530d252` | 沿用已锁V3；实际整仓审计由P0完成 |
| 合格集成P6 / 生产构建认证 | P6未资格；原V4时生产身份未知 | 当前已知B29观察见本页顶部链接，源码/二进制构建链仍未认证；不把U或GitHub分支等同于生产 |

## 已阅读的关键源码

以下blob值是GitHub API返回值，用于定位，不声称原V4编写时已下载全部原始bytes并本地复算Git blob。未列文件的细节不能从目录名称推导。

| ID | 固定源码链接 | 支持的判断 / 阅读重点 | API blob SHA |
|---|---|---|---|
| F01 | [pyproject.toml](https://github.com/NVIDIA/flare-local-inference/blob/47581ccac82660953a5b59cb04b2750d64edc97d/pyproject.toml) | prepare 依赖固定到 FlashInfer fork SHA；不能改查另一仓库 latest 代替 | 未转录；以固定commit/path定位 |
| F02 | [ignition/components/gdn_recovery.py](https://github.com/NVIDIA/flare-local-inference/blob/47581ccac82660953a5b59cb04b2750d64edc97d/ignition/components/gdn_recovery.py) | _verify / _commit / GDNLayerRecords / PreparedGDNCommit；Qwen correction records，WINDOW=8 | `a78d922ae15ddd25e95e74e3c422549471952bf2` |
| F03 | [ignition/components/gated_delta.py](https://github.com/NVIDIA/flare-local-inference/blob/47581ccac82660953a5b59cb04b2750d64edc97d/ignition/components/gated_delta.py) | PreparedGDN：实际调用 recovered；GDN 16/48/128，conv10240；normal decode / prefill 的不同分派 | `729e7e73c40186da68a8594c1e1ae2fd31cebe4a` |
| F04 | [ignition/components/gated_norm.py](https://github.com/NVIDIA/flare-local-inference/blob/47581ccac82660953a5b59cb04b2750d64edc97d/ignition/components/gated_norm.py) | _gated_rms_norm / PreparedGatedRMSNorm；多head分组及显式BF16舍入 | `6b7302c26b4744511cab210c292d37146d3dac1d` |
| F05 | [ignition/components/linear.py](https://github.com/NVIDIA/flare-local-inference/blob/47581ccac82660953a5b59cb04b2750d64edc97d/ignition/components/linear.py) | QuantizedProjection / ParallelProjections；caller-owned输出、strides、fork/join及SM103分支 | `a73efb8b4f00fbbe1b74ebe48b220ab2cf5a789e` |
| F06 | [ignition/preparation/scratch.py](https://github.com/NVIDIA/flare-local-inference/blob/47581ccac82660953a5b59cb04b2750d64edc97d/ignition/preparation/scratch.py) | ScratchArena：候选上界→选中peak→刷新views→freeze；并行区间单独求和 | `d64debbd039b5e8977c10fffdb7e8ea3052a6400` |
| F07 | [docs/performance-work.md](https://github.com/NVIDIA/flare-local-inference/blob/47581ccac82660953a5b59cb04b2750d64edc97d/docs/performance-work.md) | 实际shape目录、完整replay、escaping output、poison、single-factor与graph-critical-path方法 | `e06c390a4ee0d05bf6dfffe1c353fd8f5ab11acb` |
| F08 | [helios/src/scheduler/policy.rs](https://github.com/NVIDIA/flare-local-inference/blob/47581ccac82660953a5b59cb04b2750d64edc97d/helios/src/scheduler/policy.rs) | PolicyConfig / RequestAccounting / Candidate / cost_key / published_output；阅读1–240行 | `a03bf4961c07624b8c2b9f1894a60e1cbb52c474` |
| F09 | [ignition/recipes/qwen38/decoder.py](https://github.com/NVIDIA/flare-local-inference/blob/47581ccac82660953a5b59cb04b2750d64edc97d/ignition/recipes/qwen38/decoder.py) | ModelWeights / DecoderScratch；48层Flash配方、hidden不同，不能当27B数据量 | 未转录；以固定commit/path定位 |
| B01 | [pyproject.toml](https://github.com/local-inference-lab/flashinfer/blob/622cec10eb75da189f4dadddabc2d142a33cd211/pyproject.toml) | b12x import由experimental/b12x/_compat映射；非通用flashinfer/b12x目录 | 未转录；以固定commit/path定位 |
| B02 | [flashinfer/experimental/b12x/sequence/gdn_decode/_recovery.py](https://github.com/local-inference-lab/flashinfer/blob/622cec10eb75da189f4dadddabc2d142a33cd211/flashinfer/experimental/b12x/sequence/gdn_decode/_recovery.py) | _Verify：KDA向量gate、等head；全窗口输入先入shared/register，仅借机制 | `054e029d23854ee4bcaad8fd3f3a922e3f4c8e24` |
| B03 | [flashinfer/experimental/b12x/sequence/gdn_decode/_tuning.py](https://github.com/local-inference-lab/flashinfer/blob/622cec10eb75da189f4dadddabc2d142a33cd211/flashinfer/experimental/b12x/sequence/gdn_decode/_tuning.py) | GdnQuery/GdnConfig：最多8 state columns，KDA恢复限定、alignment/strides属于query | `4e063a921af61b6604ce1f76bb4e0fb309f54da5` |
| N01 | [src/core/gdn_replay_records.h](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/core/gdn_replay_records.h) | raw conv/key/value/gate格式与layer×record_capacity外层 | `67504986ccd84f150860d604bf51de826c6fde01` |
| N02 | [src/ops/linear_attention/gated_delta_net/recurrent.cuh](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/ops/linear_attention/gated_delta_net/recurrent.cuh) | apply_gdn_transition / FoldAccess / recurrent_bf16_body；阅读1–260、540–790行 | `cdc176321ef4ea19c2ff1a969375a42b9714f9d0` |
| N03 | [include/ninfer/ops/gdn_replay.h](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/include/ninfer/ops/gdn_replay.h) | gdn_replay_fold；全层单Op、零commit严格no-read/no-write、conv tail_3 | `08d9b6b367277cb095bb69091aee6734ae74d026` |
| N04 | [include/ninfer/ops/gated_delta_net.h](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/include/ninfer/ops/gated_delta_net.h) | replay_record已有B1..8,T2..16；这不等于完整MTP W16产品已支持 | `2d1a25dc495560956eb6a3ae1488109c6c2ca329` |
| N05 | [include/ninfer/ops/gated_rmsnorm.h](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/include/ninfer/ops/gated_rmsnorm.h) | 已有RMSNorm+SiLU gate，输入BF16，FP64 represented-input oracle | `a20451333a3a003fa6a4edf8f7a2328cee02bd42` |
| N06 | [src/ops/launcher/rmsnorm.cu](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/ops/launcher/rmsnorm.cu) | D128 Plain128-thread；Gated落到512-thread/16-row路径；有限形状候选调优 | `e86a21f1c6bcab6b18f86eb2e58bc1a8a8514ae3` |
| N07 | [src/targets/qwen3_8_27b/impl/variant.cpp](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8_27b/impl/variant.cpp) | admits_a8仅Prefill；MTP Q/G独立投影；GDN norm/control已融合；graph边界目录 | `6038bd101f89646b803213669fb9fcb0aa692a42` |
| N08 | [src/targets/qwen3_8/impl/runtime/text_context_impl.h](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/runtime/text_context_impl.h) | DFlashFeatureSink逃逸输出、已有算子调用、连续layout检查；阅读1–230行 | `90fa18f5f8be4a18e2594f81685ce9a24070d9df` |
| N09 | [src/CMakeLists.txt](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/CMakeLists.txt) | 实际源文件入口、显式构建边界；阅读1–240行 | `ac99df5ac2084daa7e31d55f6e7643baa0bdfeba` |
| N10 | [src/ops/linear_attention/gated_delta_net/replay.cpp](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/ops/linear_attention/gated_delta_net/replay.cpp) | record参数/对齐/noalias与registered fold geometry验证；阅读1–155行 | `6ce2a4d5a737e69c1d68bcf86585abca19df9ff5` |

## 官方辅助资料

- [Flare README](https://github.com/NVIDIA/flare-local-inference/blob/47581ccac82660953a5b59cb04b2750d64edc97d/README.md)：公开定位SM120/SM121，构建期Python、服务期Rust。网页检索核对；固定源码文件的全量读取不作为原V4编写时事实。
- [NVIDIA Ada Tuning Guide](https://docs.nvidia.com/cuda/archive/12.6.0/ada-tuning-guide/index.html)：SM8.9资源、FP8能力、共享内存约束。不要把Ada FP8与Blackwell blockscaled/NVFP4原生算子混为一谈。
- [NVIDIA GPU Compute Capability](https://developer.nvidia.com/cuda-gpus)：4090为8.9；实施时同时用cudaDeviceProp记录实机属性。

## 证据分层

**SOURCE**：读取的函数和契约能支持；**AUTHOR_REPORTED**：作者文档/性能声明，未在本机重跑；**DERIVED**：本包根据明确维度计算；**PROPOSED**：拟建接口/优化；**UNVERIFIED**：需要构建、模型或GPU验证。

附件保留在[inputs](../inputs/flare-analysis.md)。附件关于速度、成熟度、部署与优先级的陈述不是独立GPU证据；按[核对表](02-input-audit.md)采用或修订。

原V4编写时容器无法通过DNS直接获取GitHub，故没有整仓clone、产品编译或SASS。连接器已读取上述关键代码与调用链，足以提出可检验设计；完整源文件依赖闭包、当前生产修改、CMake和硬件资格由K0/P0补核。不可把此限制描述成源码完全未看，也不可把静态阅读描述成已经性能复现。

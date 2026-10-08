# 来源与冻结日期

检索/设计截止：2026-09-08。来源中的性能和能力只代表其自身条件；本文包没有在RTX4090上复现。没有把社区宣传数字填进验收结果。

| ID | 来源 | 采用范围 |
|---|---|---|
| S00 | 用户附件 `d6f1461e-1648-4dbf-925a-7e087c9483ac.md`，以及本次明确给出的610.57.04/KMD/UMD13.3 | 机器、生产服务/路径、模型SHA、网络和恢复约束；最新消息覆盖旧驱动描述 |
| S01 | [Kern固定源码](https://github.com/pegainfer-project/kern/tree/5188aaf8dc992ebe635f111d17c269969706da27)，尤其docs/manifest.md、runtime.md、serve.md | schema-v4、states/pages/checkpoint与runtime边界 |
| S02 | [Qwen bring-up记录](https://github.com/pegainfer-project/kern/blob/5188aaf8dc992ebe635f111d17c269969706da27/docs/qwen38-bringup.md)、tools/gen_qwen35.py | 历史ABI、GDN数值与prefill末token问题；历史CLI不照抄 |
| S03 | [Kern Cargo.toml](https://github.com/pegainfer-project/kern/blob/5188aaf8dc992ebe635f111d17c269969706da27/Cargo.toml) | cudarc0.19.7/CUDA13.0 API；serve独立workspace |
| S04 | [4090 vLLM参考recipe](https://github.com/kernel-sanders/qwen38-27b-rtx4090-vision/tree/36317835f2224c620f4d604bd57bf0a70f14cade)，README.md、Dockerfile | 算子/依赖来源；默认profile不作为本PoC oracle |
| S05 | [dbirks W4A16模型卡](https://huggingface.co/dbirks/Qwen3.8-27B-W4A16-AutoRound)、[config.json](https://huggingface.co/dbirks/Qwen3.8-27B-W4A16-AutoRound/blob/main/config.json) | group128/symmetric、BF16act、FP32 GDN与几何；本机必须另锁文件hash |
| S06 | [NVIDIA CUDA兼容性](https://docs.nvidia.com/deploy/cuda-compatibility/forward-compatibility.html)、[CUDA13.0.1发布说明](https://docs.nvidia.com/cuda/archive/13.0.1/cuda-toolkit-release-notes/index.html) | 新驱动与旧用户态、compat限制；不依据UMD推导nvcc |
| S07 | [Kern ServeOpts](https://github.com/pegainfer-project/kern/blob/5188aaf8dc992ebe635f111d17c269969706da27/crates/kern-serve/src/lib.rs)、[scheduler.rs](https://github.com/pegainfer-project/kern/blob/5188aaf8dc992ebe635f111d17c269969706da27/crates/kern-serve/src/scheduler.rs) | 并发默认、容量、greedy限制、state/前缀策略 |
| S08 | [handwritten.py](https://github.com/pegainfer-project/kern/blob/5188aaf8dc992ebe635f111d17c269969706da27/tools/handwritten.py) | 实际artifact缓存键未绑定arch/toolchain，需要修复 |
| S09 | [NVIDIA Ada Tuning Guide](https://docs.nvidia.com/cuda/ada-tuning-guide/index.html)、[Programmatic Dependent Launch](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/programmatic-dependent-launch.html) | SM89共享内存/硬件能力和PDL边界 |

源模型卡通过Exa读取，关键仓库文件通过GitHub connector读取；NVIDIA文档通过web读取。生成环境的直接GitHub网络下载失败，未声称完成clone、Rust构建、CUDA编译或GPU验证。上面的完整SHA来自已读取的GitHub ref/文件；HF实际权重revision在目标机获取和冻结，不伪造。

下载到目标机的第三方源码/内核需保留原license与provenance。该ZIP不包含第三方cubin、模型权重或字体。CPU辅助工具是本交付生成的参考工程工具。

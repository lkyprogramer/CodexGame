# 外部资料与证据边界

检索/核对日期：2026-09-09。每个条目写明实际审阅范围。动态URL不是构建锁；作为donor前须生成本地commit+SHA锁。

## S01 — NInfer DFlash2 数学、selector q、40MiB ring、提交合同
- 来源：https://github.com/Neroued/ninfer/blob/b88c0f6fc7e999f13eb2fcf7fc9105ed79a91868/docs/maintainer/qwen3.8-27b-dflash2.md
- 审阅范围：读取算法前455行；基于上游源码，不是本机复现

## S02 — NInfer DFlash2 制品、66对象后缀、W8与BF16分配
- 来源：https://github.com/Neroued/ninfer/blob/b88c0f6fc7e999f13eb2fcf7fc9105ed79a91868/docs/maintainer/qwen3.8-27b-artifact.md
- 审阅范围：读取前210行；W8主体/BF16 conv-selector，不能简单称为全W4

## S03 — 44a small-T launcher
- 来源：https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/ops/launcher/gqa_attention_decode.cu
- 审阅范围：附件全文及GitHub核对；T=1..6

## S04 — 44a build instantiations
- 来源：https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/CMakeLists.txt
- 审阅范围：附件全文；foreach RANGE 1 6

## S05 — 44a E8 lattice/Root与读写路径
- 来源：https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/ops/kernel/gqa_attention_decode_i8.cuh
- 审阅范围：附件全文+GitHub258..280；半陪集近似不可静默修成另一格式

## S06 — 44a prefill性能计划
- 来源：https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/docs/maintainer/prefill-throughput-plan.md
- 审阅范围：附件全文关键节，尤其约716..725：E8 lattice是encode-side

## S07 — DFlash2公开AL/吞吐表
- 来源：https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2
- 审阅范围：Exa全文；H200/SGLang/xhigh/K7，不是4090 medium

## S08 — vLLM 4090 recipe
- 来源：https://github.com/kernel-sanders/qwen38-27b-rtx4090-vision/blob/36317835f2224c620f4d604bd57bf0a70f14cade/README.md
- 审阅范围：此前核对并结合附件；本轮仅作既有控制组来源，不能拿headline当本机成绩

## S09 — SuffixDecoding项目/混合调度与场景差异
- 来源：https://suffix-decoding.github.io/
- 审阅范围：Exa全文；SWE-Bench端到端采用4xH100/并发8

## S10 — SuffixDecoding实现来源
- 来源：https://github.com/snowflakedb/ArcticInference
- 审阅范围：项目页确认代码仓库；具体移植提交必须由T05固定，不声称已审阅全部实现

## S11 — SageAttention公开core head维度限制
- 来源：https://github.com/thu-ml/SageAttention/blob/main/sageattention/core.py
- 审阅范围：本轮读取260..390；所读函数>128拒绝，varlen causal条件不可照搬

## S12 — SageAttention 256维未开放说明
- 来源：https://github.com/thu-ml/SageAttention/issues/47
- 审阅范围：web读取维护者答复；与当前core相互核对

## S13 — SageAttention-ada用途与真实vs合成差异
- 来源：https://github.com/fblissjr/SageAttention-ada
- 审阅范围：Exa全文；主要ComfyUI/DiT，不是已验证Qwen d256 paged kernel

## S14 — Ada资源与FP8硬件说明
- 来源：https://docs.nvidia.com/cuda/ada-tuning-guide/index.html
- 审阅范围：NVIDIA官方：100KiB/SM，99KiB/block，>48KiB需opt-in

## S15 — NVIDIA profiling权限；R610能力模式
- 来源：https://developer.nvidia.com/nvidia-development-tools-solutions-ERR_NVGPUCTRPERM-permission-issue-performance-counters
- 审阅范围：web；sudo/CAP_SYS_ADMIN或条件CAP_PERFMON，不必全局开放计数器

## S16 — NVIDIA Nsight Compute profiling guide
- 来源：https://docs.nvidia.com/nsight-compute/ProfilingGuide/
- 审阅范围：web；profiling samples不得混入生产吞吐

## S17 — Reddit历史帖镜像线索
- 来源：https://reddit.sentinel-team.org/posts/1vtz2ub/snapshots/2026-08-21T19%3A43%3A59.644708Z
- 审阅范围：Exa摘要，二手镜像，排除出决定性性能依据

## S18 — Kern既有运行时设计
- 来源：https://github.com/pegainfer-project/kern/tree/5188aaf8dc992ebe635f111d17c269969706da27
- 审阅范围：以本轮附件源码巡检报告为主；不重复声称本轮编译过Kern

## 社区检索覆盖与局限
本轮用 Exa 对 NInfer/DFlash2、Suffix、Sage、X、Reddit 搜索并复查模型卡；精确 X 查询未返回原帖。Reddit 再检索获得历史镜像线索，但不是可复核的新 4090 DFlash2 长 Agent A/B，因此不进入胜负门槛。多个 fork 转载同一速度表按同一来源处理。
未找到能证明“本机 medium + 262K + 200 tok/s 长 Agent”已实现的新独立证据。缺证据不等于该性能不可能，但必须实测。
没有以论文图表作为数值依据；引用项目网页和直接源码。

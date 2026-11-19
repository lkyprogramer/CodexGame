# 证据分级、源码锁与阅读地图

## 证据级别

| 标签 | 能证明 | 不能证明 |
|---|---|---|
| `SOURCE_VERIFIED` | 固定提交中存在实现/分支/guard | 当前二进制执行该路径、4090 正收益 |
| `AUTHOR_REPORTED` | 作者给出该配置的结果 | 同模型同硬件公平对比、可复现性 |
| `VERSIONED_USER_REPORT` | 用户固定仓库中有历史试验和结论 | 当下部署身份、别上下文合同 |
| `USER_REPORTED_PENDING_BINDING` | 用户提供后续服务验收摘要 | 缺失的原始 trace、全部精确组合已通过 |
| `PROPOSED` | 本包给出的未来适配/测试设计 | 已实现、已授权、已获益 |
| `SOURCE_UNBOUND` | 缺关键身份或证据 | 不存在、从未测试、成本为零 |

完整锁见 [source_lock.json](../evidence/source_lock.json)。以下全部为此次已读取的固定源码；不以滚动 main 链接做证明。

## Donor

| 对象 | 固定源码 / symbol | 用途 |
|---|---|---|
| YASAKANI v0.1.3 | [README](https://github.com/yasakani-dev/yasakani/blob/274d70967f013dc197888dfec233681ddd386012/README.md)、[engine35.cpp](https://github.com/yasakani-dev/yasakani/blob/274d70967f013dc197888dfec233681ddd386012/src/engine35.cpp) `load_shead` / `bdr_block_impl` | 支持边界、资产和生命周期 |
| 草稿头 | [q35_bdraft.cu](https://github.com/yasakani-dev/yasakani/blob/274d70967f013dc197888dfec233681ddd386012/src/q35_bdraft.cu) `launch_bdr_shead` | sketch→shortlist→rescore |
| 3090 fork | [fixed tree](https://github.com/watayuki288/yasakani-Unlocked/tree/3131d9a285f476bbbdbd55730bb4b3a16706a285) | 兼容 guard，不当新的 LNORD 算法 |
| OSAKANA | [README](https://github.com/pentaCoxian/OSAKANA/blob/40c8a0554f1863e612eb5e045532ddf23b4ac8ae/README.md) | 26.8GiB、5090 单次 benchmark、QSA 限制 |
| Copy planner | [common/speculative.cpp](https://github.com/pentaCoxian/OSAKANA/blob/40c8a0554f1863e612eb5e045532ddf23b4ac8ae/common/speculative.cpp) `common_speculative_impl_copy` / `common_speculative_draft` | D1 差量与 ordered dispatch |
| QSA 实际 shared frontend | [qwen4exp.cpp](https://github.com/pentaCoxian/OSAKANA/blob/40c8a0554f1863e612eb5e045532ddf23b4ac8ae/src/models/qwen4exp.cpp) `qsa_block_fast` / `build_qsa_blk_update` | 树 path 压缩后重 pool、祖先 tail 的近似 |
| TensorFold v1.2.9 | [tagged commit](https://github.com/ashhart/TensorFold/commit/6b9de695104b6b8b30c20458da87ac06c9480289)、[recipe](https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/docs/recipes/qwen3.8-27b.md) | 版本、硬件/量化与性能反例 |
| 分段投影 | [cuda_projection_many.zig](https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/zig/src/families/qwen3_5/cuda_projection_many.zig) `projectMany`；[lane_gemv.cu](https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/zig/kernels/cuda/lane_gemv.cu) `tf_lane_gemv_seg` | 调度组织而非直接替换 codec |
| 成本身份 | [cuda_cost_adapter.zig](https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/zig/src/families/qwen3_5/cuda_cost_adapter.zig)、[lone_costs.zig](https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/zig/src/core/lanes/lone_costs.zig) | 旧 utility 计划的 identity / band / backoff 约束 |

## 接收端

| 对象 | 已读取固定路径 | 必查问题 |
|---|---|---|
| NInfer proposal | [mtp_impl.h](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/runtime/mtp_impl.h)、[text_context_impl.h](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/runtime/text_context_impl.h) | mandatory alignment、AR、next head 是否真可分离 |
| NInfer verifier / commit | [speculative_target_impl.h](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/runtime/speculative_target_impl.h)、[program_impl.h](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/runtime/program_impl.h) | full target、pending、partial terminal、Fold、KV trim |
| NInfer head 资产 | [bindings.cpp](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8_27b/impl/load/bindings.cpp)、[variant.h](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8_27b/impl/variant.h) | 131072 行 Q4G64_F16S 与 token remap，Target 248320不裁 |
| NInfer PDL guard | [CMakeLists](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/CMakeLists.txt)、[pdl.cuh](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/core/pdl.cuh) | sm89 定义 NINFER_SM86，PDL 退化普通 launch |
| Strata 当前 Head | [generate.cpp](https://github.com/Niko1221/Strata/blob/13eedf552417a6a791a7d13c6597e24300ee3a09/src/program/generate.cpp) | CUDA stop-bound 与 merged prompt / drafter end update |
| stop-bound | [helper](https://github.com/Niko1221/Strata/blob/13eedf552417a6a791a7d13c6597e24300ee3a09/include/strata/core/serve_stop_bound.hpp)、[tests](https://github.com/Niko1221/Strata/blob/13eedf552417a6a791a7d13c6597e24300ee3a09/tests/core/serve_stop_bound_test.cpp) | 不重复穷举 helper 单测；查 continuation 集成 |
| 已有策略 / 监控 | [draft_policy.hpp](https://github.com/Niko1221/Strata/blob/13eedf552417a6a791a7d13c6597e24300ee3a09/include/strata/spec/draft_policy.hpp)、[window_rule.hpp](https://github.com/Niko1221/Strata/blob/13eedf552417a6a791a7d13c6597e24300ee3a09/include/strata/spec/window_rule.hpp)、[stream_watch.hpp](https://github.com/Niko1221/Strata/blob/13eedf552417a6a791a7d13c6597e24300ee3a09/include/strata/core/stream_watch.hpp) | 已有 lookup skip/cost policy；watchdog 非精确完成归因 |

## 版本陷阱与检索边界

- YASAKANI v0.1.3 是轻量 tag，当前支持 sm89 编译；不能从支持列表推导官方 4090 实测。
- TensorFold v1.2.9 的 annotated tag 必须 peel 到 `6b9de...`；release 的 `target_commitish=2ba55...` 不是 tag 对象目标。其公开 benchmark 中被比较的 0.6.6 也不是本轮 native 1.2.9。
- Strata `v0.2.13` 的 app/control tag 指向 `d2f096...`，tag message 的 engine build 是 `712fec...`；`v0.2.13.1` 是 Linux Control 修复。它们均不能证明最新 HEAD `13eed...` CUDA 修复已在用户部署。
- 本轮重新读的是上述主线、用户历史和必要接收端；之前 HyperQwen、Basalt、tqLLM、RustingStrata、Hyperkernel、samir-vllm、Nabo 等仅按旧包结论去重，没有伪称将所有项目最新全量再审。
- 搜索仅用于发现官方材料；核心主张依靠固定代码/一手报告。本轮不以未找到第三方结果推断“没人跑过”，也没有独立复现作者的模型 benchmark。

# 08 源码映射与证据

基线commit：`44a2c6c3392c9d51e76a895ed97bf1867530d252`。目录/方法以当前读取的源码和此前同一commit的代码检查为依据；行号不作为唯一定位，因为新增文件会改变行号。执行时P0生成 `source-map-resolved.json`，把稳定symbol映射到实际文件和hash。

本次无法在工作容器直接clone外网仓库，已用GitHub连接器读取提交、构建配置、测试注册和关键Op合同；没有在此运行GPU、编译NInfer或训练。不存在“已经通过”的engine测试。

| 区域 | 已有文件/目录 | 改动目的 |
|---|---|---|
| 层与prefill执行 | `src/targets/qwen3_8/impl/runtime/text_context_impl.h`、`text_context.h` | range、tap、prefix/tail调度 |
| prefill入口 | `src/targets/qwen3_8/impl/runtime/text_prefill_impl.h` | 进入LSP状态事务 |
| Program/内存 | `src/targets/qwen3_8/impl/runtime/program.h`、`program_impl.h`、`layouts_impl.h`、`workspace_recipe.h` | startup预算、状态生命周期 |
| 状态导入导出 | `src/targets/qwen3_8/impl/runtime/continuation_image.h`、`session_snapshot_impl.h` | 来源标记与完整性 |
| KV/state | `src/targets/qwen3_8/impl/state/decoder_state.cpp` | 使用现有layer_view，不另造cache |
| GDN数学接口 | `include/ninfer/ops/gated_delta_net.h` | 不改变原契约；新增state-only独立接口 |
| GDN实现 | `src/ops/linear_attention/gated_delta_net/` | 复用state passing数学；P0定位具体kernel文件 |
| 卷积 | `include/ninfer/ops/causal_conv1d_silu.h` | 正确维持3列history |
| shared engine | `src/runtime/engine/concurrent_executor.h` | 只接stats/admission合同，不塞入Qwen数学 |
| 服务日志 | `src/serve/request_log.h`、`request_log.cpp` | 新指标与schema |
| 测试入口 | `tests/CMakeLists.txt` | 注册新CTest且禁止skip掩盖未测 |

## 待新增文件（均不是上游已有功能）

- `src/targets/qwen3_8/impl/runtime/late_state_policy.h`、`late_state_policy.cpp`、`late_state_prefill_impl.h`：策略和执行。
- `src/targets/qwen3_8_27b/impl/late_state_predictor.h`、`late_state_predictor.cpp`：27B绑定、固定head、forward。
- `include/ninfer/ops/gated_delta_net_state_only.h`、`src/ops/linear_attention/gated_delta_net/state_only.cu`：StateOnly合同与实现。
- `tools/ced_lab/`：preflight、phase runner、Teacher导出调度、benchmark、guard；只用于离线研究/测试。
- `tools/convert/qwen3_8_27b/convert_late_state_predictor.py`：Predictor容器转换。
- `tests/targets/qwen3_8_27b/test_ced_*.cpp`、`tests/test_gated_delta_net_state_only.cpp`、`tests/ced_lab/`：新测试。
- `ced-research/` 是LAB_ROOT兄弟工作目录，**不在NInfer源码根**：train、export、checkpoint评估与统计工具。

## 需要先解析而不能猜文件名的节点

```bash
git grep -n -- 'prefill-chunk' apps src
git grep -n -- 'continuation-cache-l1-mib' apps src
git grep -n 'gated_delta_net_workspace_capacity_bytes' src
git grep -n 'plan_linear_attention_state_pool' src
git grep -n 'prefix_checkpoint_policy' src include
```

P0解析并写出 `serve_options_parser`、`cli_options_parser`、`gdn_large_t_launcher`、`gdn_state_passing_kernel`、`prefix_checkpoint_planner` 五个键。多个候选必须由阅读调用关系选出实际owner，不以第一条grep结果替代。后续Task用 `@source_map.<key>` 指向这一已解析文件；解析失败即BLOCKED，不生成虚构路径。

## 外部与项目来源

### [S01] 固定提交与当前HEAD

[https://github.com/tensorninja/ninfer-4090/commit/44a2c6c3392c9d51e76a895ed97bf1867530d252](https://github.com/tensorninja/ninfer-4090/commit/44a2c6c3392c9d51e76a895ed97bf1867530d252)

已读取GitHub commit集合；默认分支当前HEAD。

### [S02] 构建要求

[https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/CMakeLists.txt](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/CMakeLists.txt)

CMake3.28/CUDA>=12.8/sm_89/BUILD_TESTING。

### [S03] 性能与INT8 prefill限制

[https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/docs/performance.md](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/docs/performance.md)

仓库报告，不是本次对用户主机测量。

### [S04] GDN/ReplaySSM接口

[https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/include/ninfer/ops/gated_delta_net.h](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/include/ninfer/ops/gated_delta_net.h)

FP64 oracle、张量shape、Replay T=2..16。

### [S05] 原生CED结构与训练

[https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash)

仅用于区分原生CED与既有Qwen近似改造，不引用其成绩作为本项目依据。

### [S06] Qwen3.8-27B模型状态

[https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/docs/maintainer/qwen3.8-27b-model.md](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/docs/maintainer/qwen3.8-27b-model.md)

64层、GDN/attention形状、final hidden、MTP。

### [S07] TextContext执行实现

[https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/impl/runtime/text_context_impl.h](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/impl/runtime/text_context_impl.h)

run_layers、gdn_mix、prefill_impl、mtp_prefill_chunk。

### [S08] 卷积历史合同

[https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/include/ninfer/ops/causal_conv1d_silu.h](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/include/ninfer/ops/causal_conv1d_silu.h)

BF16 [C,3] oldest→newest。

### [S09] 仓库工程与训练职责

[https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/AGENTS.md](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/AGENTS.md)

外部训练分工；新增近似路径需显式扩展合同。

### [S10] Continuation缓存合同

[https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/docs/continuation-cache.md](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/docs/continuation-cache.md)

state inventory、compatibility、L1/L2/L3与aliases。

### [S11] 测试注册与skip合同

[https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/tests/CMakeLists.txt](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/tests/CMakeLists.txt)

SKIP_RETURN_CODE77、实际已有测试名。

### [S12] 现有状态容器

[https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/impl/state/decoder_state.cpp](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/impl/state/decoder_state.cpp)

逐层paged KV与GDN pool。

### [S13] 已有GDN实现目录

[https://github.com/tensorninja/ninfer-4090/tree/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/ops/linear_attention/gated_delta_net](https://github.com/tensorninja/ninfer-4090/tree/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/ops/linear_attention/gated_delta_net)

正确目录；不是src/ops/gated_delta_net。

### [S14] 当前runtime prefill入口

[https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/impl/runtime/text_prefill_impl.h](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/impl/runtime/text_prefill_impl.h)

prefill_text_chunk/configure_text_card。

### [U01] 用户部署记录

`d6f1461e-1648-4dbf-925a-7e087c9483ac.md`，文档日期2026-09-08，来自用户Library。配置摘要只作P0起点，执行时重读主机实际信息。文档包不携带用户私密运维全文。

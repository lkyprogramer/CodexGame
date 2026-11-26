# 40 · 2026-11-26 上游复核与旧结论修订

**本章只更新来源事实和待验证设计，不继承任何 GPU/模型资格。** 分支列表、compare与关键源码已读取；未安装或执行这些项目。

## 1. 当前主线与参考分支

| 项目 | 此次核对的ref/SHA | 与v1.2的关系 |
|---|---|---|
| Atomic | engine-development `fb69fff02101b048a0a165a3b502712dd2ca978f` | 固定底座未变；公开64分支的本次枚举不意味着全部代码审计 |
| Ghost | main `b6cd02e099af2453f3674e047d5f89152f8a662d` | 官方仅main；上一轮main/tag代码边界仍适用 |
| Transformers PR51161 | open；head `228bb636a3809f1a46f6f9d4011dfbff89416e5c` | 状态及head未变；属于last-loop研究，不是已合并性能特性 |
| squid5090 | `51b85dd17e719a45e93e77a9e49df94c50144b30` | 未变，Blackwell特性仍需逐项拒绝/改写 |
| ARLoop | `16c8eaa6e841a6203a068c23394e0dbe69b08c55` | 未变，保持可选参考 |
| 2DSD | main `431aade2…`；feat/inkling-dspark `962874f303c3142406ab3eecfae2bb51567815c9` | 实验分支ahead3；旧版遗漏了这条公开分支，撤销仓库缺Inkling runner的笼统结论 |
| CUDA Rust | main `f35d6ccc2e03a54e73e3796f415f11313e439d50` | 相对旧main `5e5c77…` ahead1，新增#1866 |

原source-lock保留历史审计pin，新增来源记录新pin；不把旧141文件审计和旧CI日志改写成新提交结果。[2DSD比较](https://github.com/SqueezeAILab/2DSD/compare/431aade2f1e8ebc98a31158d53c39e554984a83a...962874f303c3142406ab3eecfae2bb51567815c9) · [CUDA Rust比较](https://github.com/NVIDIA/cuda-rust/compare/5e5c77b19a4b3204d6542bab2f0fde2a4eed824b...f35d6ccc2e03a54e73e3796f415f11313e439d50)

## 2. 2DSD分支的真正价值

分支在2026-11-24已有3次提交；不是本包声称今天才发布。新增Inkling代码覆盖参考forward、逐节点树runner、批量runner、静态CUDA Graph runner、attention/row ops、权重适配、DSpark及测试。通过GitHub完整新增文件patch恢复的37个文件均校验了Git blob SHA；这是源码身份验证，不是测试执行。

### 资产与服务边界

[configs/models.json](https://github.com/SqueezeAILab/2DSD/blob/962874f303c3142406ab3eecfae2bb51567815c9/configs/models.json) 区分：

- 正式Mini锁 `1fb4134b9a74f9681054f4ef82e4bf1f458a2337`，`drafters={}`、`w64=null`。
- varloop锁 `657b53ba5da7baefe9ff15dca5cd25f5bd3dbaa2`，有专用公开DSpark drafter。

正式Mini的该revision与本包正式参考 `c9d028…` 不同；不自动覆盖资产锁。研究资产与正式模型的traces、特征、head、结果必须分开。该fork没有标准Inkling engine model class，使用batch1定制worker直接持有Native/Fast模型；CLI/worker可实验不等于完整服务能力。

### 可以直接帮助Atomic设计的结构

[inkling2_reference.py](https://github.com/SqueezeAILab/2DSD/blob/962874f303c3142406ab3eecfae2bb51567815c9/vllm-fork/vllm/model_executor/models/inkling2_reference.py) 与 [tree runner](https://github.com/SqueezeAILab/2DSD/blob/962874f303c3142406ab3eecfae2bb51567815c9/vllm-fork/vllm/model_executor/models/inkling2_2d.py) 使状态更具体：k/v/attn/mlp四条conv输入历史、core每pass plane、早深度coda自己的plane、node的prelude/bank/rows/features/parent/depth。这些是L01/R02的状态清单参考，仍须与Atomic真实成员逐项映射。

### 不能直接继承的结论

1. `exact`路径使用FP64参考；`served`按特定BF16舍入点近似Hopper，不能复现全部GEMM/attention归约。因此两者均不自动成为Atomic量化路径的同算术oracle。
2. [GraphRunner](https://github.com/SqueezeAILab/2DSD/blob/962874f303c3142406ab3eecfae2bb51567815c9/vllm-fork/vllm/model_executor/models/inkling2_graph.py) 的full-plane PKf/PVf仍按所有planes×max_len分配。启用lagged读取共享不自动减少这份allocation；且shared目标可改变输出，需独立身份。
3. [Humming支持检查](https://github.com/SqueezeAILab/2DSD/blob/962874f303c3142406ab3eecfae2bb51567815c9/vllm-fork/vllm/model_executor/models/inkling2_humming.py) 不等于SM89支持证明。分支需要≥0.1.20，而旧lock较早；须隔离锁版本并测实际格式/launch/output，不自动升级生产环境。
4. [runner_check.py](https://github.com/SqueezeAILab/2DSD/blob/962874f303c3142406ab3eecfae2bb51567815c9/scripts/inkling2/runner_check.py) 的zip式first_divergence可漏掉严格前缀长度差，且诊断脚本不会因所有偏差自动非零退出。此为静态发现，未运行复现；不能直接当G2 gate。UX01要求完整长度、非空case、finish reason、状态和独立重算检查。

本次按exact head查询GitHub Actions得到0条run；这仅说明该查询未观察到Actions结果，不等于作者没做本地测试。我们的R03状态改为NOT_RUN：公开代码缺失这个理由已解除，资产、SM89、完整状态、采样与收益仍待资格。

## 3. CUDA Rust #1866 的影响

新main [f35d6ccc](https://github.com/NVIDIA/cuda-rust/commit/f35d6ccc2e03a54e73e3796f415f11313e439d50) 增加反向/交换索引的write coverage证明，并修正写入前assert可能trap与domain不匹配的漏洞。`writes_all_elems`目前要求1D launch contract，2D声明应失败关闭；也处理未内联ThreadIndex/Uniform get的dev/test导出。

K00后续优先冻结该新main及#1857基础，不用旧证明缓存冒充新候选证据。我们的K合同仍要求非空property、明确假设/TCB、MIR/代码/产物链绑定，以及实际SM89执行、数值与E2E测试。新修复扩大/加固一部分证明，不证明完整浮点算法或任意二维kernel。

本次exact head的10条Actions记录状态为success，但这是外部CI摘要；未据此认定其所有job执行了GPU或4090。旧CI细节保持历史日期。UX04在实施时重新运行相关正反例；没有Lean/GPU环境保持BLOCKED，不记录PASS。

## 4. 对计划的明确修改

- R03从“缺公开runner BLOCKED”改为“实验分支可审计 NOT_RUN”，正式Mini资产匹配仍是独立阻塞检查。
- R03 initial配置仍是varloop R3、per-loop、匹配5层drafter；native DSpark先于二维投机的主线顺序保留。
- 原有state/概率质量/资源/业务门不变，新增UX01–UX04回归。
- 源码例程、作者测量、外部CI、本机模型证据四者继续分列。
- 新增Magnitude的固定主线/分支与迁移判断见[41](41_magnitude_source_audit.md)、[42](42_magnitude_integration.md)，不以项目名称替换Atomic底座。

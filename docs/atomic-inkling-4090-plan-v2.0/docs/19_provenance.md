# 19 · 代码、模型与资料归属

## 1. 复用登记

每一份直接移植代码填写：上游repo、commit、路径、blob/hash、原LICENSE/NOTICE、拷贝范围、修改内容、兼容性测试与本地commit。只吸收设计而重新实现也写出参考来源，便于未来维护者理解为什么如此设计。

| 来源 | 核查到的声明 | 执行要求 |
|---|---|---|
| Atomic Engine固定源 | 根LICENSE为MIT；README致谢llama.cpp/ggml、TurboQuant | 保留原头与归属，逐文件检查第三方内容 |
| squid5090固定源 | Apache-2.0；NOTICE列出多个来源 | 保留Apache与NOTICE对应信息，不能整体改标MIT |
| 2DSD固定源 | Apache-2.0；fork中含上游代码 | 逐文件追踪vLLM与新实现归属，不能仅拷根license |
| 原生DSpark | Atomic文件头指向llama.cpp PR32218特定revision | 正确归属已有算法/实现，不宣称本项目原创 |
| 正式Mini / varloop | 官方模型卡标Apache-2.0 | 归档采用revision的模型条款与转换链 |
| 2DSD Inkling drafter | 模型卡/仓库含Apache-2.0声明 | 锁模型文件与目标依赖；不能把裸草稿器视作完整模型 |
| LoopCD 2610.02185 | 论文许可与代码许可是不同对象；未核实对应官方代码 | 按论文自行实现须记方法出处，不挪用同名另一论文仓库 |
| ARLoop | 代码MIT；HF权重标签Apache-2.0 | remote code、权重与依赖分别登记 |
| NInfer / Strata | 本包使用历史业务/工程经验，不复制其代码 | 如后续实际移植，先读取确切源与许可，不由记忆推定 |

以上不是完整第三方许可证审计结果。T00登记来源，T12检查实际引入的文件和分发资产；没有复制的项目不扩大成无必要的法律工作流。

## 2. 模型转换链

原checkpoint → converter commit/参数 → tensor quantization map → GGUF文件 → optional folded draft。这条链各步骤有hash、精度与metadata记录。模型repo名称与file名不足以证明转换来源一致。

对折叠output/Markov head保留目标head hash、原草稿器hash、折叠工具commit、dtype和误差验证。不能把用户私有adapter或带限制的数据随公共包重新分发。

## 3. 评测与业务数据

公开数据按各自条款获取；GPQA等有访问条件的数据不打包进本规范。真实Java仓库、Pi会话与工具结果保留在用户控制的执行环境，本包提供索引/schema，不含用户业务源码。调参集、holdout、失败回归集分别登记，不因失败就把holdout搬到开发集后继续沿用原检验。

## 4. 更新策略

本包源版本锁于2026-11-25。执行时可以只读查看上游变化，但不要无记录切换。若关键缺口被新commit修复，建立source-update任务，记录diff、受影响能力和重测范围；历史run继续指向原版本。

## 5. Ghost来源与移植归属

Ghost固定源为`b6cd02e099af2453f3674e047d5f89152f8a662d`，仓库提供MIT或Apache-2.0双许可；移植时记录所选许可、来源文件/commit/修改、保留对应声明。Cargo依赖、NVIDIA/NVRTC组件与模型资产分别核对，不能从仓库双许可推导所有二进制可随意打包。Linux PR7已合并；parking PR2 closed未合并，设计归属与main代码来源分别记录。具体证据见[23](23_ghost_source_audit.md)。

## v1.2：编译与证明产物来源

NVIDIA/cuda-rust固定源声明Apache-2.0；实际移植时保留对应LICENSE/NOTICE、文件头和修改记录，并逐项核对所用子模块、生成器、CUTLASS/LLVM/CUDA等依赖自己的版本与许可证。文章观点用来源链接归属，不将整篇文章复制进实现。审计文件列表与hash见cuda-rust-source-audit；本包不分发完整外部源码。

新产物链记录source/template/dependencies→实际验证MIR→emitted IR/PTX→cubin/SASS/资源报告，以及host ABI、launch前提、toolchain/driver与registry。hash绑定用于追踪身份，不作为编译语义证明。生成式AI参与的候选也要保留准确源、参数、生成版本/提示hash、人工或独立审查记录；不得只保存最终最快二进制。

既有Atomic/Ghost/squid来源不因使用新前端而消失。独立重写与直接移植分别记录，作者B200微基准、上游CPU/Blackwell CI和本机测试分别标类；不重新署名为自己的4090性能。

## v2新增来源与许可证

LoomKV/ZipFusion本次未确认官方实现与代码许可，不能将论文托管许可当软件授权。GAAC/SplitZip为MIT、ZipServ为Apache-2.0；固定源与嵌入依赖分别保存NOTICE。Magnitude根与其Pi组件metadata需分别核对，见41。2DSD新增公开分支与CUDA Rust新main保留独立pin/审计范围；原source hashes和CI历史不伪改成新版本测量。

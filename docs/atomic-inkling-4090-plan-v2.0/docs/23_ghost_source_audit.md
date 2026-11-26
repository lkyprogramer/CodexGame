# 23 · ghost-infer：最新分支、实现边界与证据审计

**版本：补充包1.1，2026-11-25，Asia/Shanghai。** 本文审计 `affifuddin-hazam/ghost-infer`，为Atomic/Inkling/4090方案增加来源与候选机制。没有运行目标4090或Ghost模型。

## 1. 结论与定位

Ghost值得加入本方案。它最直接的价值是已经写出了**消费级NVIDIA卡上的Inkling专用CPU参考与CUDA预览路径**，提供循环层优先驻留、专家布局重排、批量prefill和CPU/GPU交接的可审计实例。其创新主要属于针对小显存、单用户场景的工程组织；CUDA Graph、热专家缓存、Tensor Core attention、lookup和LoRA本身不是新算法。

Atomic继续作为底座。Ghost作为固定版本的比较对象、实现参考与实验假设来源；不把其整个Rust运行时加入服务依赖，也不以跨引擎短跑分替换原G0–G7门槛。[S18]

## 2. 最新分支与版本：已实际查询

本次独立查询GitHub官方 `branches?per_page=100` 和 `git/matching-refs/heads/`，两者均只返回一个官方分支。另查询tags refs、releases、最近commit及全部3个PR；不是仅凭搜索摘要判断最新版本。

| 对象 | 固定身份 | 核查结果 |
|---|---|---|
| 官方默认及唯一当前公开分支 | `main@b6cd02e099af2453f3674e047d5f89152f8a662d` | 最后提交2026-11-24 13:22:41北京时间；当前审计基线 |
| 最新发布标签 | `v0.5.0@9d15c249d4dbb7c3d376d878748ca71fd1546662` | release发表于2026-11-24 13:03:18北京时间 |
| main相对v0.5.0 | 同一批引擎源码 | 递归tree逐路径/blob SHA比较，仅README.md与docs/building.md不同 |
| 上一版 | `v0.4.0@04ebfeae989738961748dfdb4fe07836a4e995c6` | 用于识别新增Inkling、Linux与会话功能；不当当前实现 |
| Linux贡献分支 | `nullbyte61/ghost-infer:linux@583708c23e862e1ddb59a2a6bfe3f6fd5ced8e19` | PR #7已合并；merge `d470234d443ecab4b1739b7cfbb78058a46b3920` |
| 会话缓存贡献分支 | `2424830124/ghost-infer:park-contexts@7e8923e3c4c35a4fe6241cc7e414b105230bf691` | PR #2关闭且未按PR merge；main后续实现了相关功能并致谢，不能标成已合并PR |
| 旧中文界面分支 | `i18n-chinese`，PR #1 | 已合并；与本次底层优化无直接关系 |
| Atomic基线复核 | `engine-development@fb69fff02101b048a0a165a3b502712dd2ca978f` | 与原包一致，本补充不更换底座 |

“最新分支”因此包含当前main、v0.5.0对应代码、已合入的Linux/Inkling工作，以及PR贡献来源的区别。没有证据支持另一个仍活跃的官方develop/inkling分支，不自行猜分支名。仓库的fork分支不能算作官方当前heads。机器记录见 [ghost-source-audit.json](../manifests/ghost-source-audit.json)。[S18–S21]

### 关键开发提交

- `94854483a2c2a319642ecd8e2fd628cc743c8980`：新增Inkling CPU参考、CUDA专用路径、相关量化与专家计算。
- `74b9f348b5d3e8a839f0067158460185f8799e3b`：循环层优先、IQ3_S nibble布局、部分驻留交换、128-token prefill。
- `c9a6ebf34f97cf8cdbb8851ca1a49188c8ce00ca`：Inkling专家文件读取适配Unix位置读。
- `3024c380dcbe0aaa0cc8908365ba722b387f93eb`：低架构CUDA编译guard与编译架构覆盖开关。
- `ce8b809184c16e6cf04436241d7b57369f6837f8`：将Linux main合入Inkling工作；其后成为v0.5.0/main祖先。
- `9d15c249d4dbb7c3d376d878748ca71fd1546662`：Linux CI固定x86-64-v3，避免缓存中native编译产物在不同CPU上SIGILL。

## 3. 必须区分两个执行系统

| 能力 | 通用GpuModel/GpuSession路径 | 专用Inkling路径 |
|---|---|---|
| 入口 | serve、bench、通用generate | inkling-check / inkling-gen / inkling-gpu-check / inkling-gpu-gen |
| 输入 | 模板、tokenizer、聊天协议 | 命令行token ID列表；聊天适配未完成 |
| 服务器/桌面 | 已有，Linux服务器可从源码构建 | 发布说明明确仍为engine preview，server/chat待接入 |
| KV | 有int8、q4等通用codec与动态容量机制 | GPU每逻辑slot独立F16 K/V、F32 conv；CPU参考K/V与conv为F32；不能直接套通用--kv q4 |
| 投机 | 有lookup；独立draft模型路径限greedy；lookup有one-hot proposal采样实现 | 未见接入原生DSpark、2DSD或通用lookup运行循环 |
| 会话parking | 通用Engine/GpuSession含host snapshot路径 | 未接入通用Engine，不能宣称已有Inkling多会话恢复 |
| attention kernel | 通用TC/split-context方案 | 自有相对位置、sink、softcap等专用算子；需单独移植和验证 |
| 已报告硬件 | 主要RTX2060 SUPER/部分Linux移植信息 | RTX2060 SUPER 8GB、24GB RAM、UD-Q3_K_XL短输入 |

源码依据：`src/main.rs`命令分派、`src/model.rs`架构分派、`src/inkling.rs`、`src/inkling_gpu.rs`、`src/cuda.rs`、`src/server.rs`。README的通用功能列表不能跨越这条边界。[S18]

## 4. 作者数据能支持什么

| 数据 | 原条件 | 本包解释 |
|---|---|---|
| Inkling decode 21.0–21.2 tok/s | 2060S 8GB、Ryzen5 3600、24GB RAM、UD-Q3_K_XL、短prompt后128输出；ctx1024、reserve90MiB | 特定调优profile的作者结果 |
| Inkling decode 19.3–19.4 tok/s | 同机，默认ctx4096、默认设置 | 应与上一行分开，不能统一称默认21 |
| Inkling prefill 46–48 tok/s | 450-token prompt | 不证明64K/128K预填充速度 |
| llama.cpp约16.78/16.8 tok/s | 作者称同PC最佳设置 | 缺本机重跑及完整配对raw，约1.25倍只作背景 |
| IQ3_S解码5.0→1.57 ns/32值 | 提交说明中的CPU局部微基准 | 不代表端到端3.18倍，布局还会扩张 |
| Qwen MoE约80.5 vs39.5 tok/s | v0.4.0、2060S、七种prompt、两轮、i1-Q3_K_M | 属于另一个模型/路径/日期，不能作为Inkling增益 |
| lookup约3.2倍 | 高复制率编辑等适合lookup的任务 | 不代表一般Java任务，更不代表Inkling已具备该功能 |

作者也明确承认重复单句bench更容易集中命中少数专家，可能优于真实聊天；其部分通用表使用不同KV精度，长上下文项目采用best-of-N。原始bench输出被gitignore，固定源码并不提供一套完整公开的4090配对记录。所有外部数字只保存在来源区，不能写入本包目标机结果。[S18–S19]

## 5. 有真实测试，但资格范围有限

固定head关联的Linux CI run `45333157236`、job `138238857125`成功；日志显示 **84 passed、6 ignored**。workflow执行Rust release构建和CPU测试，没有GPU。测试包含lookup截断、量化局部比较和合成采样分布验证。这是有用的局部证据，不授予Inkling CUDA、长上下文或服务状态资格。[S18]

审计发现需要在T01/G00修补的测量边界：

1. `golden.ps1`虽打印reply是否一致，但其成功条件没有把这个结果纳入强制失败，也没有可靠的非零失败出口。
2. accuracy/decode/KL/dequant工具主要输出测量值，不能仅凭进程exit0判断数值通过。
3. `GHOST_INFER_VERIFY_CHECK`打印不一致信息但不强制失败；`VERIFY_N`回拨pos不足以恢复recurrent state。
4. draft bench分支没有更新相同的输出hash；空/初始hash不能当输出相同证据。
5. 当前 `bench-lookup.py`引用已移走的README小节，相关抽取会得到空文档；不能直接用它复现旧3.2倍表。
6. 部分脚本在usage缺失时以SSE chunk数代替token数；spec burst会使这种计数失真。

这些是代码与脚本的静态/文本核查结论，不是本次GPU故障复现。后续实验应使用原包T01的独立证据包装器，保留原始输出并显式失败，不能照搬这些脚本的PASS口径。

## 6. 安全借鉴的边界

Ghost采用MIT或Apache-2.0双许可。移植前按19登记逐文件归属，保留所选许可与作者信息；NVRTC二进制分发条款另算。只借鉴算法并在Atomic原有C++/ggml接口实现，不需要把Rust、桌面界面、夜间LoRA训练或NVRTC发行包加入主力服务。[S18]

夜间训练属于另一个产品问题：小LoRA、离线候选与有限验收并不证明通用持续学习、可靠纠错或可验证遗忘。它不进入本次4090推理加速任务。

## 7. 固定入口

- [当前审计树](https://github.com/affifuddin-hazam/ghost-infer/tree/b6cd02e099af2453f3674e047d5f89152f8a662d)
- [v0.5.0发布](https://github.com/affifuddin-hazam/ghost-infer/releases/tag/v0.5.0)
- [Inkling CPU参考](https://github.com/affifuddin-hazam/ghost-infer/blob/b6cd02e099af2453f3674e047d5f89152f8a662d/src/inkling.rs)
- [Inkling GPU](https://github.com/affifuddin-hazam/ghost-infer/blob/b6cd02e099af2453f3674e047d5f89152f8a662d/src/inkling_gpu.rs)
- [Linux PR7](https://github.com/affifuddin-hazam/ghost-infer/pull/7)
- [会话贡献PR2](https://github.com/affifuddin-hazam/ghost-infer/pull/2)
- [CI运行](https://github.com/affifuddin-hazam/ghost-infer/actions/runs/45333157236)

下一步阅读 [24迁移设计](24_ghost_transfer_design.md)、[25增量任务](25_ghost_tasks.md)、[26验收与复现](26_ghost_validation_runbook.md)。

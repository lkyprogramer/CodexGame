> V3 继承资料：P0—P6 的任务目标和上游合入顺序继续有效。命令依赖须先按根目录 `support/REHYDRATE.md` 恢复。

# 02｜差异分析与保留账本

## 1. 三种 diff，三种含义

`B..O` 用来识别你的独有定制；`B..U` 用来识别真正需要迁移的上游变化；`O..U` 只是两个当前树的净差异，不能独立决定保留/删除。整仓实验必须以 B 为共同祖先，记录 rename、binary、删除和自动合并结果。API 中被预算限制而显示 0 的增删行数不是“文件没有改动”。

本包完整列出了定制侧 43 个文件以及 34 个上游独有提交；定制 CSV 中的统计来自 GitHub compare。上游完整净文件总数与整仓冲突总数没有伪造：P0 运行 `source_audit.py` 后，会生成精确的三组 patch、numstat 清单、共享文件三版本内容和真正的 `git ls-files -u`。

## 2. 你的 11 个提交应该如何处理

| 定制提交 | 保留内容 | 合入后的处理 |
|---|---|---|
| `d5d2e17` | 原生产镜像、模型和资源审计 | 原封保存历史语境；另建 P0 当前审计，不覆盖旧证据 |
| `e924cc2` | request-local tokenizer 工作量计数 | 同一编码器可选计数，null 关闭；不进入 prompt/cache identity |
| `c782577` | 44a2c6c legacy oracle | 固定算法；只改旧 DTO 接口隔离层；保留 O 编译出的独立基线程序 |
| `6b4286d` | B0 首字节桶单调 scanner | 作为唯一生产 added-token 扫描后端；保留既有 tie-break 顺序 |
| `1d05441` | selected-token restart trace | 与分段信息共享一次扫描；不要在 ordinary EOF 伪造 restart |
| `a5128f0` | B1 局部重编码、memo、计数 | 功能并入上游 PrefixRelation；不把旧 strict-only 策略用于 Explicit |
| `1dacb0f` | legacy/B0/B1 bounded benchmark | 增加纯上游和合并后 lane；实测后判定是否存在性能倒退 |
| `f3b231d` | prepare_detail、请求/文本大小 | 保留字段和端点覆盖；统一命名扩展与字节单位说明 |
| `46320bd` | sm89 无模型烘焙镜像 | 保留；用独立测试构建和生产构建，不因上游 Dockerfile 改回 baked 模型 |
| `7c9d959` | CUDA 不可用时测试返回 77 | 保留正确 skip；真实 4090 必测项目 skip 必须使 gate 失败 |
| `e0b05f7` | G1 differential driver | 仍需单独执行；53 real / 74 synthetic 的旧套件不可偷偷降样本数 |

所有文件名、增删行数和处理动作在 `data/fork-files.csv`。参考实现的大量新增行并不等于生产热路径变大；保留它们有助于阻止“实现与测试同时变错”的合并。

## 3. 上游变化：按依赖而不是按宣传特性划分

### 3.1 U01—U10：生成服务正确性、缓存契约、分段前端

这一组引入 Responses 预填充进度、Hermes 工具方言、未闭合 think 的工具恢复、重复周期守卫、round fault 隔离、显式 alias 类型、prompt-cache 断点和 payload 去重，最后是 `SegmentedEncoding`。

重复守卫必须只观察 committed token，不把被拒绝的 MTP draft 计入历史。`4040222`、`995f4a2`、`15fd064` 需要一起看：出现 guard finish reason 后，输出许可与 executor 错误边界也必须接受它。单独移植守卫容易让“正常停止”变成引擎异常。

缓存 alias 的类型不能由名字前缀推断：adapter/session namespace 会使这个推断失效。系统/工具前缀、assistant opener、显式断点、路由 session 和 retained lane 是不同层级；显式模式关闭隐式边界，不表示关闭整个 continuation/session 系统。

这一组直接碰到你的 16 个共享修改文件，最适合作为一次完整、可测的 P1 基线，而不是先改 B1、下一阶段再全部重写。

### 3.2 U11：预填充准入与异步导出

新 executor 在更细粒度的预填充执行单元间考虑准入，能够推进多个 prefill 请求，并将 continuation 导出放到独立工作路径。热会话/冷会话混跑是它的主要价值场景。

代价是资源生命周期更复杂：host pinned staging、Program stream、lane 状态、发布别名与取消操作共同决定安全性。`publish_seconds` 的同步部分变少不等于实际导出成本消失；必须同时看 export 字节、耗时、队列和 fence 等待。[S13]

### 3.3 U12—U17：small-T 算子与流式工具调用

小 T 内核改变 Q5 residual、Q4 SwiGLU、Q4/Q5 attention/GDN 的计划选择和底层 MMA。源文件删除、新 kernel、新公共 row-split 组件、plan 类型和 CMake 必须一起迁移。旧 fused convolution snapshot 路线被删除后，不能只保留旧 plan 字段来“让它编译”。

这组收益更可能体现在 decode/MTP verify 的投影部分。100K+ 注意力读取、KV 带宽和多流调度仍可能支配总时延。MTP 接受率、吞吐、图捕获和数值误差都要测；不能只看单算子微基准。

工具调用从“生成结束后解析”转为增量状态机，新增 begin/arguments/end 回调；不完整调用、模型多余文本、schema-aware string 参数、Hermes 与历史恢复都有新契约。保留你的计时数据时不要把旧 `StreamSink` 或旧非流式解析函数覆盖回来。[S14]

### 3.4 U18—U27：决策执行、新 KV、LoRA/遥测与输出 UTF-8

决策是共享权重、共享 GPU、独立分支状态的 prefill-only 路径，不是用聊天生成 JSON 替代。它使用 A16，不能套用 Chat prefill 的 A8 catalog；没有常规 decode/LM-head sampling/MTP。每个 question 从同一 state 出发，不继承其他 question 的 GDN/conv 状态。

新 A4 segmented attention 只读 prefix cache，各分支 own token 直接使用 BF16 K/V 输入。长分支 scratch 只按最长分支需要分配，不是简单复制 N 份完整上下文。

决策 adapter 不只是普通 LoRA，还带 pointer head 和布局元数据；生成 API 必须拒绝决策 adapter。LoRA 数值与缓存 identity 隔离要一起测，不能因为同样的 tokens 就跨 adapter 命中。

midrise codec 变化、非饥饿遥测、日志 schema 21/22、35B 包构建修复、双系统 dashboard、混合负载 probe 都在同一组。UTF-8 修复只处理模型输出的 malformed 字节，输入 tokenizer 仍保持严格错误行为。

### 3.5 U28—U34：协议、Playground、图像决策

TypeSafe 路径改为 `/typesafe`，不会自动保留旧 `/systemone` 别名。OpenAI Decisions 使用独立的原生 schema/render/validation，不能通过有损 TypeSafe 转换来凑接口。`jev-latest` 是 TypeSafe 的别名，不是应添加到 OpenAI discovery 的通用模型名。

图像决策改变的不只是 HTTP 输入：还包括 image detail profile、预处理 digest、MRoPE、KV ordinal、缓存状态版本、媒体输入预算和取消后的资源回收。同一原图不同 resize/pad 方式必须产生不同 identity，即使 grid 相同。文本训练的 adapter 能运行视觉输入，不等于它经过视觉任务精度验证。[S16]

## 4. 上游默认值与现有生产要求的差异

| 项目 | 保留/迁移原则 |
|---|---|
| `--kv-dtype rk4v4-e8` | P1—P3 保持旧配置；P4 才显式验证 `rk4v4`；不做静默别名 |
| 262,144 原生上下文 | 作为核心生产资格，不通过短上下文冒充验收 |
| reasoning / preserve_thinking | 从实际 compat proxy 和服务配置采集；不根据模板默认 xhigh 推断 |
| MTP3 | 保留现有生产模式，另跑关闭 MTP 的数值参考；不把 DFlash 35B 功能当作 27B 新优化 |
| `Dockerfile.sm89-nobake` | 继续显式指定该文件，模型只读挂载 |
| Cache namespace | 每阶段隔离，新 codec 与旧 codec 必须不同目录/namespace |
| 决策 adapter | 代码可以合入，但生产目录默认只包含已资格化的现有生成适配器 |
| UI | 保持可选产物；不强迫无 dashboard 的生产镜像引入 Node、静态资源和额外入口 |
| GPU 架构 | sm_89；NVFP4 合约保持可编译，不在 4090 上虚构 Blackwell FP4 执行资格 |

## 5. 不要遗漏的非共享路径语义风险

`AGENTS.md` 虽不是你新增定制的冲突文件，却可能改变后续 Agent 的目标约束；必须明确本次生产保留与验收范围。`Dockerfile` 自动更新不意味着应该替换你的无权重 Dockerfile。`src/runtime/engine/concurrent_executor.h` 即使自动合并也要做生命周期 review。`chat_template.h` 不是 fork 独有改动文件，却会让你新增的 legacy oracle 和 G1 driver 产生编译和契约冲突。

最终每个上游提交的处理决定和目标 Phase 都记录在 `data/upstream-commits.csv`，没有把 UI/文档提交偷偷排除在“全量合入”的历史目标之外。

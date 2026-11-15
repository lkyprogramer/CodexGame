# 04 · kernel 证据附件：从源码到真实完成路径

状态：**PLANNED**。本章是原 `completion-path/v1` 的附件合同，不是新事件系统；包内合成示例也不构成产品实现。

## 1. 需要补的不是更多曲线，而是身份桥

原归因底座回答“哪个依赖阻碍某个完成 sink”。本附件回答“这个依赖执行了哪份代码、使用什么张量表示、观测是否改变执行方式、结论来自哪种证据”。两个问题必须同时成立。

固定连接方向：`RunEvidence → kernel-evidence/v1 → artifact/dispatch/graph/counter/oracle references`。仍只有 ExperimentSpec、RunEvidence、Decision、BudgetLedger 四类实验记录。附件可以多份，但同一共享 batch/kernel 只存一份；多个请求引用它，不能复制其耗时。

## 2. 字段与出处

| 字段组 | 必须表达的内容 | 拒绝的捷径 |
|---|---|---|
| schema / provenance | schema版本、采集器版本、原始文件hash、SOURCE_INSPECTED / SYNTHETIC / LIVE_MEASURED | 用静态审计伪装实测 |
| source_ref | 仓库、完整commit、dirty diff hash、相关文件 | 只有分支名/latest |
| build_ref | 编译器、CUDA/toolchain、flags、目标arch、组件manifest hash、产物hash | 只记录“Release”或编译成功 |
| loaded_module_ref | engine实例实际加载的module/cubin/PTX来源、内容身份与证明方法 | 把build目录的文件当已加载模块 |
| engine_scope | 复用boot/PID/start_ticks/engine_instance/segment | 只有PID，忽略复用/重启 |
| work_scope | request/attempt/slot generation、round/window、pool epoch/job | 只用请求顺序或日志行号 |
| cuda_scope | device UUID、context、stream、capture/graph exec generation、replay ordinal/node | capture次数直接当执行次数 |
| tensor_contract | shape、strides/layout、有效域、padding、dtype、量化块/scale/zero-point、权重与KV表示 | 将整个混合量化模型笼统叫IQ3_S |
| path_ref | dispatch分支、scope、调用/图节点证据、路径开关与实际值 | kernel名字一样就认定同路径 |
| measurement_ref | clock域、区间、backend、collector配置、丢失量、cache/clock/replay | unknown填0、不同域直接相减 |
| completion_ref | 原事件/DAG节点、选定sink、依赖证明、观察器资格 | 用kernel总和替代暴露时间 |
| limitations | 未绑定环节、隐式假设、缺失数据、可支持与不可支持的判断 | 模糊的“基本可信” |

ns时间和可能超过JavaScript精确范围的ID一律十进制字符串；不使用浮点时间保存原始精度。敏感提示词、模型token、地址、完整环境变量不进入公共模板；使用受控raw引用、hash和白名单字段。

## 3. 证据强度分开记录，不自动升格

至少保留以下独立维度：

- `artifact_binding`：SOURCE_ONLY / BINARY_ONLY / LOADED_MODULE_BOUND / UNKNOWN。
- `path_binding`：DISPATCH_AGGREGATE / GRAPH_NODE_BOUND / REQUEST_WINDOW_BOUND / UNKNOWN。
- `observation_role`：OBSERVER_OFF_RESULT / QUALIFIED_SEMANTIC_TRACE / DIAGNOSTIC_ONLY / SYNTHETIC。
- `graph_equivalence`：PROVEN_FOR_SCOPE / CHANGED / UNKNOWN，附证据而非仅由调用者传一个true。
- `data_origin`：REAL_CAPTURE / REAL_LAYOUT_SYNTHETIC_VALUES / ROUTE_ONLY / SYNTHETIC。

这些维度不替代原L0–L4。即使已绑定SASS，也不能自动得到L2上界、L3反事实或L4净提升。源码命中、二进制存在、GPU执行、请求归属、完成路径暴露是五个不同命题。

## 4. 三个必须堵住的现有缺口

### 4.1 Manifest和dispatch不能独立完成运行归因

当前上游 `run_manifest.hpp` 描述预算、路径、张量格式，按(area,name)更新；它不是不可变的逐请求历史。外层在既有生命周期边界保存受控快照及hash，与engine实例绑定，不要求上游在热路径逐token写文件。

`dispatch_stats.hpp` 区分图capture scope与graph launch，但按key聚合。存在多个graph generation或不同shape时，不能把某capture的节点数乘全部launch数。新附件需证明每次replay引用哪个graph generation；缺少映射就是UNKNOWN。

### 4.2 STRATA_VERIFY_PROFILE会改变图

审计SHA的 `src/core/verify.cpp` 根据环境变量是否存在启用profile；字符串“0”仍会启用。相关路径可以禁用df_branch、conv/AB融合、shared-expert stream fork、wait/rows/hits融合，并在收集阶段拷回stamp。

因此“开启profile后某kernel占比很大”首先是诊断路径事实。记录实际开关、分支集合、graph generation与观察器角色；图已改变则 `DIAGNOSTIC_ONLY`，不得进入生产路径暴露上界。仅比较平均开销或kernel数量相同，不能证明图等价。

角色与资格分字段：graph CHANGED可保留`observation_role=DIAGNOSTIC_ONLY`，但正常路径`observer_qualification=REJECTED`；graph UNKNOWN则资格为证据不足/未评估，禁止晋升。只有图等价且数据完整，才套原1%/3%开销CI规则。诊断用途不能覆盖硬拒绝。

原EXACT6、dispatch配置在baseline/off/on之间保持一致。observer-off指本次新增观察器关闭，不意味着擅自关闭既有功能；不得为采集新增Device/Stream/EventSynchronize。

### 4.3 异步结束不能由host时间猜测

host reservation结束、launch提交、query返回、CUDA事件、GPU活动结束各有自己的定义。host poll完成通常给完成时刻一个上界，不自动给出精确GPU结束。StageInFlightSampler等host占用不等于GPU利用率。

内部观察到的start不得冻结为外部release；不得补任意residual lag把DAG“拟合”到wall。资源排序是否在改时长后保持，必须由机制证明。固定调度下的条件反事实不是所有实现的可达上界；低值不能据此关掉一个更宽泛的新机制。

## 5. 内存与算力数字的统一口径

`logical_payload_bytes`、`packed_storage_bytes`、`dram_read/write_bytes`、`PCIe bytes`、`CPU memory bytes` 分列。重复读取和缓存命中不能由张量大小推断。FP32累加、FP16/BF16输入、INT解包、FP8存储分别记录；只在对应指令和维度被证明时使用匹配的计算峰值。

roofline是带假设的kernel理想下界，不是完成路径节省值。NCU的某个launch字节数不能除以另一轮Nsight Systems的聚合时间来声称精确带宽。无对应scope时只可作跨run关联诊断。

## 6. 最小接入接口

未来代码放在原包唯一离线包：`<LAB_ROOT>/lab/observability/kernel_evidence.py` 与 `lab/observability/artifact_bindings.py`；如果现场已有明确迁移，则E0记录canonical映射后扩展真实模块，不能新建并列的`<LAB_ROOT>/observability/`。

~~~text
validate_attachment(raw_refs, run_identity, event_index)
  → validation_errors + binding_levels + limitations
attach_to_run_evidence(validated_attachment)
  → existing RunEvidence attachment reference
~~~

只读已授权目录与已验证hash，不执行manifest中的命令，不import任意用户模块。验证器不得返回“优化PASS”；只有原控制器在原合同下作Decision。缺数据必须可保存为失败附件，不删除证据。

最小负例：旧PID新进程、同名不同二进制、PTX被JIT但仅有旧cubin、两个graph generation混乘、丢记录计数缺失、provider声明的无效时间戳sentinel、跨clock做差、共享batch重复计时、profile改图、内部start被当release。每项必须得到明确reason code，不能靠人工备注放行。CUPTI记录声明的无效零时间戳要拒绝；合法相对时钟原点0不等于缺测，零duration也需单独按schema判断。

代码出处：[Strata固定树](https://github.com/Niko1221/Strata/tree/504b143342a9fe1aa8320a7b31e11f5c0ac265c3)；具体文件在[来源目录](../sources/SOURCES.md)。

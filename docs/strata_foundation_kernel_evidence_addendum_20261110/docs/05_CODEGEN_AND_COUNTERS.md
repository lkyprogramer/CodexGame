# 05 · 编译产物身份与定向计数器

状态：**PLANNED / NOT implemented**。本章定义原底座的附件与未来薄适配器，不交付采集器。engine starts、generation requests、GPU budget 均为 **0**；不启动 NCU、不编译、不运行微基准。固定源码审计基线为 Strata `504b143342a9fe1aa8320a7b31e11f5c0ac265c3`，不是现场部署身份。

## 1. 先证明看到的是同一份代码

复用现有 run manifest、`ENGINE-COMPONENT.md` schema 2 的 build id、archs、逐文件 SHA256/size；不另建 manifest。增量附件引用它们，并记录以下身份链。字段缺失为 `null` 加原因，不能由文件名、时间戳或 preset 名补齐。

| 层级 | 附件最小字段 | 认定边界 |
|---|---|---|
| 源码 | `source_sha`、dirty 状态、patch hash | HEAD 相同不证明工作树相同 |
| 编译 | 配置 hash、完整 nvcc/ptxas 版本、实际 flags/targets | preset 与有效配置分开 |
| 产物 | component manifest 引用、文件 SHA256/size、cubin target、PTX/SASS hash | 仅为候选二进制 |
| 加载/JIT | module generation、加载字节 hash、AOT/JIT、PTX输入/JIT选项/驱动版本、输出身份 | 缺输出身份时不宣称最终 SASS 已绑定 |
| 执行路径 | 原 run/request/op id、dispatch 分支、shape/layout/dtype、eager/graph generation/replay id、kernel/module 引用 | host 分派不等于设备执行完成 |
| 诊断 | tool version、metric 原名/单位、scope、采集配置、原报告 hash | 不能替代 observer-off 结果 |

离线步骤：读取固定白名单原件 → 校验 hash/配置 → 解析已有反汇编与资源输出 → 关联既有加载/dispatch 记录。不得执行附件中携带的命令或 import 用户模块；没有加载证据就停在 `candidate_only`。未来加载身份采集仅在初始化/模块生命周期钩子设计，不增加热路径 I/O、锁、分配或观测同步。

源码核查发现 `cuda-compile` preset 含 `86-real,89-real,89-virtual`，而裸 CMake 的 CUDA backend 中 Qwen 默认值为 120；因此“项目支持 4090”不能证明某轮实际目标为 SM89。路径、原文与固定 SHA 统一见[来源目录](../sources/SOURCES.md)。

## 2. 复用 spill 检查，不复制裁判

已有 [`tools/check_cuda_spills.py`][spill] 离线调用 `cuobjdump --dump-resource-usage`，解析 REG/STACK/LOCAL/SHARED；无需 GPU。其 `--list` 只输出 CSV，不能当检查通过。allowance 按 kernel×SM 匹配，现有 86/120/121 项不可外推到 89；缺 SM 按无 allowance，保留原 vendored-symbol 过滤口径。原脚本退出码 `0=clean、1=violations、77=不可运行`；无工具、文件或 SASS 的 77 必须是 UNKNOWN，不能包装成 PASS。

增量只追加目标 SM、输入 hash、原始输出、退出码与加载身份引用。STACK/LOCAL 非零是静态资源现象，不等于动态 spill 流量。PTX 是虚拟 ISA，运行时可能 JIT 成 cubin；反汇编静态条数既不是动态次数，也不能证明当前请求命中。[官方编译兼容说明][compat]与[二进制工具说明][binary]分别约束这两层。

## 3. 未来 NCU adapter：先资格，再有界采集

预算为 0 时不得启动任何采集。未来单独获准后，先取本机 `ncu --version` 与 `ncu --help`，再按 help 使用 `--list-chips`、`--list-sections`、`--query-metrics` 发现支持项；`--chips` 与 metric suffix 取本地枚举，不写死 H200 名单。保存查询原文/hash，枚举成功不证明计数器权限。只选择问题需要的最小指标集，预算须覆盖 launch 数、pass 数、重跑次数、时长和报告体积；超限停止并保留失败。

每份附件保存实际 `replay_mode/cache_control/clock_control`、pass 数、预热、序列化、软件插桩、匹配策略和 native exit/stderr。kernel replay 会保存/恢复内存；application replay 重跑整个应用，必须证明确定性及无外部副作用。默认清缓存会改变缓存状态；`cache-control none` 仍非无扰动。时钟默认值随版本变化；无额外控频授权时须显式使用本机支持的 `--clock-control none`，缺该能力则 BLOCKED，不靠默认值。依据见 [NCU Profiling Guide][profile]、[CLI][cli]。

拟定适配器退出码（**不是 NCU 原生码**）：`0=完整诊断附件；2=身份/输入无效；3=工具/架构/指标不支持；4=权限阻断；5=丢失/无效/重放不匹配；6=其他工具失败；7=未实现或无预算`。原生退出码另存。3 记 UNKNOWN，4/7 记 BLOCKED，2/5/6 记 INVALID；任何非零状态均不得晋升，0 也不表示正确性或收益通过。

RTX4090/SM89 不支持 HES；[CUPTI API][cupti]明确 HES 仅 Blackwell 及以后。也不支持 Hopper TMA 的 `cp.async.bulk.tensor`（SM90+）或 WGMMA（SM90a）；普通 `cp.async`（SM80+）不可与之混称，见 [PTX ISA][ptx]。`ERR_NVGPUCTRPERM` 按[官方权限说明][permission]报告 BLOCKED，禁止自动 sudo/setcap、改驱动参数或容器权限。

## 4. 数据有效性与禁止推论

记录 `lost_records/invalid_timestamps/unmatched_launches`；未测为 null，不是 0。CUPTI dropped counter 读后清零，必须累加；其记录中声明为无效sentinel的零时间戳不能当零耗时。合法相对时钟原点0则不能误判缺失，须按backend/schema区分。若另获准使用传统 Activity，记录真实后端及 kind：CONCURRENT_KERNEL 保留并发但仍有插桩，KERNEL 会序列化本进程 kernel，见 [CUPTI Usage][usage]。

保留指标原始数值、单位、聚合后缀、作用域和采集机制，派生量另存公式与输入引用。算法有效载荷不等于 DRAM 实际流量；L1/L2/DRAM 不跨层相加。带宽只用同 scope 的 bytes/duration；分母缺失、单位不符或重放范围不同均拒算。软件插桩指标、采样估计与硬件计数分栏，采样值不能标成精确执行次数。

诊断 run 与 observer-off run 分开。counter duration、bytes、stall、静态 SASS 只支持机制分析；不得充当 observer-off wall、请求完成时间或因果关键路径边权。不得相加重叠 kernel 时间冒充总耗时；缺依赖与 sink 身份时不推导净收益，仍走原 O5/O6 裁判。

## 5. 必须拒绝的负例与最小测试

1. 同 SHA、不同 flags 或 dirty patch，被合并为同一 build。
2. preset 写 89，但候选 cubin 只有 120，被判实际命中。
3. 仅有 PTX 或静态 SASS，被标为已加载 JIT 输出。
4. spill `--list`、退出 77 或 SM86 allowance，被当作 SM89 clean。
5. metric 枚举成功、权限失败或字段缺失，被填 0 后算带宽。
6. 冷/热缓存、clock policy 或 replay 不同，仍合并 A/B。
7. 丢记录、无效sentinel时间戳、重复重跑或未匹配 launch 被悄悄丢弃。
8. 诊断时间替代 observer-off wall，或无预算自动开启 HES/NCU。

最小离线测试只读合成 fixtures：一组身份链完整阳例，上述八组逐项断言失败原因/退出码/null；附加 dropped 计数 `2,3` 累计为 `5`、native/adapter 退出码不混淆。拦截 subprocess/网络/引擎入口并断言调用数为 0。本章测试要求仍为 PLANNED；合成通过只证明合同解析，不能证明 GPU 资格、执行命中或性能收益。

[spill]: https://github.com/Niko1221/Strata/blob/504b143342a9fe1aa8320a7b31e11f5c0ac265c3/tools/check_cuda_spills.py
[compat]: https://docs.nvidia.com/cuda/ada-compatibility-guide/index.html
[binary]: https://docs.nvidia.com/cuda/cuda-binary-utilities/index.html
[profile]: https://docs.nvidia.com/nsight-compute/ProfilingGuide/
[cli]: https://docs.nvidia.com/nsight-compute/NsightComputeCli/index.html
[cupti]: https://docs.nvidia.com/cupti/api/group__CUPTI__ACTIVITY__API.html
[ptx]: https://docs.nvidia.com/cuda/parallel-thread-execution/index.html
[permission]: https://developer.nvidia.com/nvidia-development-tools-solutions-err_nvgpuctrperm-permission-issue-performance-counters
[usage]: https://docs.nvidia.com/cupti/main/main.html

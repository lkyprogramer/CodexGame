# 08 · 资源合同与硬件适配

## 不可改变的边界

| 条件 | 行为 |
|---|---|
| 输入+输出预算+4096 >131072 | 发请求前拒绝；不截输入 |
| GPU温度达到85°C | 停本轮自己的负载，归档；不抬温度线 |
| 实际MemAvailable<4096MiB，或cgroup约束更紧 | 停止；不以free缓存估算代替 |
| 外来GPU进程/占用18089/交接不明确 | 不启动，不杀对方 |
| 生产已恢复 | 不自动停；说明条件变化 |
| 源/模型/二进制/port/原件身份不明 | BLOCKED_EVIDENCE |
| 需新驱动/toolkit/内核模块才能运行 | 当前路线NOT_APPLICABLE或BLOCKED，不改系统 |

旧P4最高84°C和KVRES-off约683s触及85°C，只证明当时运行边界，未证明全天热稳定。P24峰值71°C也不豁免新的prefill热负载。来源：[P4](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P4-RUNTIME-BOUNDARIES-20261027.md)、[P24](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P24-HC-PAIRED-PERFORMANCE-20261029.md)。

## 每项新内存机制先交账

记录分配前/后physical bytes、allocator保留、必要额外副本、pinned量、slot数、模型工作集、graph-owned memory、加载峰值与steady-state。不能只报某个tensor减少多少。

预打包需算`extra_bytes = converted_bytes − replaceable_original_bytes`；若原blob仍被GPU上传/回退/校验使用，原blob不能扣掉。按需缓存计实际unique bytes、重复命中、淘汰和重算成本，不能将一个热点热L1微测视为全专家收益。

scratch复用需证明最后读→下一写的happens-before，覆盖所有stream/graph/取消/失败路径。相同地址不等于同一allocation epoch。若释放scratch改变expert loan/residency，自然dispatch可能改数值，必须从E0匹配对照扩展到完整路径审查。

## CPU资格

Silver4216的AVX512-VNNI与AVX-VNNI不同；没有VBMI/VPOPCNTDQ不能打开现有全宽TU门。不要删CPUID检查。单独TU仍需反汇编和OSXSAVE/XCR0检查；P5已做过的单格式VNNI不重开。

## GPU资格

编译目标显式sm89、沿现有CUDA12.3；不把sm103/sm120 cubin当兼容。Ada每SM寄存器/shared memory/occupancy限制按官方指南核实，核函数`ptxas`资源与运行命中都登记。occupancy高不等于更快，降低寄存器可能spill；cp.async也受实际地址/对齐/共享内存生命周期限制。

INT8 Tensor Core不等于现有IQ codebook可直接输入；如果把权重/激活转为另一个数值域，需要证明值、scale、舍入、溢出和规约，通常E1。已有融合GU/SwiGLU不能被新dequant路径无意拆开而只报告矩阵核速度。

## 明确排除

- Hopper WGMMA/TMA、cluster、SM90 PDL；Blackwell原生FP4；多卡NVLink/跨卡PD。
- 为单会话引入continuous batching并以总吞吐掩盖单请求时延。
- 全量BF16/FP16大模型留作本机必测基线；本机资源不够就注明。
- 自动超频、加功率、安装GPU解锁模块、调swappiness/THP/内核；旧THP已覆盖约85%，当前没有新的资格证据。
- “增加RAM/换CPU”作为软件计划通过条件。硬件上限可以如实报告，但不改变用户机器前提。

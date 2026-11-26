# 08 · SM89算子、CUDA Graph与squid借鉴

## 1. 硬件边界

RTX4090为CC8.9；NVIDIA Ada指南建议显式编译8.9，并列出寄存器、shared memory和FP8能力。PDL与TMA是CC9.0起的机制，thread-block cluster/DSMEM也不能当作4090能力。普通cp.async、ldmatrix、FP16/BF16 MMA与CUDA Graph值得按实际形状研究。[S04]

squid固定版本默认sm_120a。修改构建架构字符串并不能让其cluster、原生FP4或block-scaled低比特kernel自动获得SM89实现。只移植已经明确语义与硬件前提的部分。[S05]

## 2. 按收益证据排序

| 候选 | 触发证据 | 初始做法 | 停止条件 |
|---|---|---|---|
| 去除每token分配/host同步 | CPU timeline显示launch/同步形成关键空隙 | 复用scratch、固定地址、已有图机制 | 空隙占比不足以支持目标收益 |
| control/norm/residual/conv融合 | 小kernel累计占比可观且访存重复 | 单个精确语义融合，保留fallback | 误差、寄存器溢出或E2E无改善 |
| MoE small-B专用路径 | B2/4/8 verify效率低 | token按expert聚合、重用packed权重 | 重排代价/路由不稳定抵消收益 |
| grouped MoE prefill | 长prompt的router/gather/专家GEMM热点明确 | 复用通用矩阵乘，逐步优化tile | TTFT提高但scratch/128K峰值失控 |
| relative attention/FA | 随context增长mask/attention成为瓶颈 | 先正确分块与SWA，再选融合 | 改变global/SWA语义或不支持KV格式 |
| FP8/低比特新格式 | weight带宽确为瓶颈 | 格式/scale/误差单列实验 | 质量下降或转换/展开成本过高 |
| 大范围persistent/megakernel | 多项证据仍显示launch为主要成本 | 最后才做有界原型 | 两轮无E2E收益，不扩大重构 |

不能因为过去另一个Qwen引擎有launch瓶颈，就假定Inkling也有；旧CPU pool/no-benefit路线重开须有新profile。

## 3. 路径与文件

现有：`ggml/src/ggml-cuda/ggml-cuda.cu`、`CMakeLists.txt`、`ssm-conv.cu`、`topk-moe.cu`、`fattn.cu`、`mmq*.cu`，以及 `src/models/inkling2*.cpp`。

拟新增（只有T07选中对应热点才创建）：`inkling-control.cu/.cuh`、`inkling-relative-attn.cu/.cuh`、`inkling-conv.cu/.cuh`。优先沿用已有kernel接口与能力分派，不为了统一命名重构整个backend。

每个新kernel必须给出输入/输出shape、dtype、stride、alias约束、同步要求、supported B、shared-memory bytes、register/occupancy测量以及fallback路径。

## 4. Graph缓存键

至少包括模型epoch、kernel build ID、B、序列数、capacity/bucket、KV格式、loop策略、mask模式、地址generation与workspace布局。可变position/长度放device参数；图中所有数据依赖和memcpy的寿命必须明确。

权重reload、预算shrink、KV resize、quantization、tree宽度或模型loop数改变时，更新/失效图。图内地址若仍被引用，buffer不得evict。图缓存上限纳入账本，不能为每个长度无限创建图。

先捕获B1和少数固定B，测首次capture和steady-state分开。避免每请求rebuild却只报告热图速度。

## 5. 从squid吸收的具体机制

- 生命周期arena与先算容量再切片：迁入Atomic现有ledger而非独立漏记显存池。
- B1与B2/4/8固定图、device position：减少重复host工作；语义由目标模型状态保证。
- 按expert聚合token的prefill/verify：注意route顺序、top-k加权顺序和tie-break。
- prompt lookup：只作为已验证proposal。
- 每个逻辑visit的local/global状态分开：必须与Atomic实际slot映射一致。
- copy/compute流水：4090使用可用primitive重新选tile，不带入Blackwell资源参数。

不复制公开峰值作为计划数字，也不将squid的自定义Q4 KV与GGML Q4_0当同格式。

## 6. 算子测试门

覆盖B=1/2/4/8与prefill代表形状、实际每种quant tensor、非连续stride、极值/近零、top-k tie、稀疏expert分布、所有token同expert、长context尾块、边界对齐与非对齐。数值阈值先冻结，改变累加顺序即提升到数值/质量审查，不能凭greedy少数一致判定bitwise。

使用CUDA sanitizer或可用的等价工具检查memcheck/race；不可用时明确未覆盖。profiler单独采样，不混入正式计时。最终以同模型请求与Agent任务耗时决定是否启用。

## 7. Ghost的SM89可借鉴点

参见[24](24_ghost_transfer_design.md)与G02/G03。Ghost将NVFP4 code/scale拆开后软件解码并用dp4a；可研究其访问组织，不能声称4090执行Blackwell原生FP4 MMA。IQ3_S→Iq3SNib是精确存储重排，被转换张量110→134字节/256值；只在资产含对应格式且热点收益覆盖额外RAM/load成本时采用。通用路径的256维旋转Q4、TC/verify宽度上限有几何与格式限制，不自动适用于专用Inkling的128维head。先记录实际dispatch，再做原G2/G3/质量资格。

## v1.2：多前端候选与精确SM89资格

新增[27–30路线](27_cuda_rust_source_audit.md)与[机器支持矩阵](../manifests/sm89-backend-matrix.json)。cuda-oxide SIMT有SM89源码支持；cutile baseline支持SM89/Tile IR13.2，但FP8 registry要求SM90、FP4/scaled MMA要求SM100；同仓cute-rs-preview不支持SM89。后端、dtype和具体指令分别探针，不能由“支持Ada”推断整个算子目录适用。

按30的实际热点族研究norm/control/conv/repack、量化GEMV、小B verify GEMM、分组prefill、attention与已有graph参数化；全部遵守原E/N/Q、R3与T07门。48warps/SM、64K 32-bit寄存器、100KiB shared/SM和99KiB/block只是架构上限，实际分配/opt-in/resource report必须核对，不从满AD102参数推断实际4090。B200的224KiB shared、TMA/cluster/TMEM/tcgen05方案被硬件门排除。

先完成K02关键路径评估，再开启最多24个候选的有界离线搜索；详见29/31。更换语言或内存安全证明不是加速结论，原有无收益停止规则不放宽。

## v2.0 · 产物缓存不授予新资格

Magnitude的按芯片调优值得借鉴其证据合同：编译命中只表示有产物，不能证明当前driver、shape、dtype、layout、模型、KV码本和预算上的正确性或收益。K流程继续有界并与所有GPU生成串行；不因新来源扩大候选预算或启用生产JIT搜索。MGX11补充旧artifact/newprofile的拒绝用例；完整Seismic后端不进入当前主线。[41来源](41_magnitude_source_audit.md) · [42实施](42_magnitude_integration.md)。

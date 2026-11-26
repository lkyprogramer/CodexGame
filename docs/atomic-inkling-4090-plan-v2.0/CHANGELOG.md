# 版本变更

## v2.0 · 2026-11-26（Asia/Shanghai）

### 全面重排

- 保留原32专题和T/R/G/K任务ID，新增总计划00、缓存33–39、上游更新40、Magnitude41–42，共43专题、44任务、148计划测试。
- 改造顺序按正式R3基线→完整状态与资源账→局部性能→Tier→条件Pool/专家预取→组合验收。原验收阈值、质量门和生产授权边界不变。
- 新增L00–L07、LX01–LX32、UX01–UX04，以及M00–M03、MGX01–MGX16。全部是待实现/执行合同；没有GPU结果。
- 完整checkpoint、typed subrecord与runtime lease分离；明确zero-suffix next logits、请求私有状态、raw pending、graph metadata reader/update/replay、有限overflow和恢复事务。
- Magnitude机制融入预算、传输、投机、KernelLab和服务观测；不替换Atomic底座，不照搬不同KV表示或上游数值阈值。

### 来源纠正与更新

- LoomKV Tier/Pool、GAAC、SplitZip、ZipFusion、ZipServ按真实论文条件与源码支持范围分别审计。未确认的官方实现不写成已有可用代码。
- 旧版遗漏2DSD `feat/inkling-dspark@962874f…`；现已有公开Inkling实验runner，撤销全仓缺码阻塞，R03改NOT_RUN。正式Mini匹配drafter、Atomic adapter与SM89仍未资格。
- CUDA Rust当前main更新至`f35d6ccc…`；新增#1866写覆盖delta。原141文件/CI证据仍绑定历史`5e5c77…`，不追认新版本资格。
- Magnitude固定main`3aba40f…`，49分支、8组祖先比较、58份源码pin；识别其为推理引擎，当前无Inkling注册。最新main提交是release CI，运行时变化另列。
- 来源登记由35项增至47项；机器源锁由30项增至42项。新增静态发现标明未复现，不混入运行测试。

### 交付与执行范围

本轮只完成研究、设计、机器合同、文档与辅助工具验证。目标4090、Atomic/Inkling、CUDA/Lean/Seismic和业务测试未运行；没有修改服务。实际本地检查结果见[VALIDATION](VALIDATION.md)。下方保留旧版本历史，旧版“当前”和阻塞描述只对当时审计范围成立。

## v1.2 · 2026-11-25（Asia/Shanghai）

在v1.1上新增NVIDIA/cuda-rust与Provably Safe GPU Kernels审计，形成4090局部定制后端、有限自动优化、形式证明边界及实际验证计划。原Atomic固定base、正式Mini R3、全驻留优先、原G0–G7和所有停止/质量/资源/统计门保持。

### 新增与同步

- docs/27–32六篇：来源/证明、后端、自动优化、SM89算子、8任务、28测试。
- 五份新manifest：141文件源码审计、SM89矩阵、搜索policy、候选Schema、NOT_RUN示例；一份外部CI观察记录。
- README/AGENTS、02/05/08/14/15/16/18/19/20/21/22/26与机器图/源锁/目录同步；run仅增加K任务枚举，原gate与policy/helper字节保持。
- v1.2当时32篇专题、32任务、96计划测试、35来源ID、30源锁项。schema_version仍1.0，文档包版本1.2。

### 核实与纠偏

main `5e5c77b19a4b3204d6542bab2f0fde2a4eed824b`已squash合入PR1857，hardening head与main的5350blob树相同。cutile baseline可支持SM89，但Tile FP8/FP4与cute-rs-preview有独立更高架构门槛。Lean只覆盖指定MIR安全性质；B200示例仍有未覆盖输出IO和unsafe边界，并可在不支持GPU上skip后exit0。全部外部CI依真实job内容分类，未授4090资格。

### 本轮交付范围

没有连接目标4090、安装/编译Rust或Lean、构建Atomic、运行模型或测量收益。K00–K06 NOT_RUN，K07 DEFERRED，当时R03 BLOCKED/G04 DEFERRED；R03判断已由v2纠正；96项目标测试全部NOT_RUN。实际文档/Schema/helper验证见[VALIDATION](VALIDATION.md)。没有创造新的生产授权。

### 上一版身份

v1.1 ZIP SHA256：`6b05387c14e40f5825505ca5d241bc5b18bfaae8a71b8579f8c19a5eead69a5a`。v1.1合并MD SHA256：`756ccf03dce141e90767d7cec4566510687f0ef3c979495efffe8750af261503`。本版完整文件以PACKAGE_MANIFEST为准。

## v1.1 · 2026-11-25（Asia/Shanghai）

本版在原Atomic × Inkling × RTX4090集合上增加Ghost Infer源码审计与可执行计划。原Atomic固定底座、模型身份规则、全驻留优先策略、主线/研究分离和全部质量/性能/服务门槛保持。

### 新增

- docs/23：最新官方分支、v0.5.0与v0.4.0树比较、Linux/parking PR head、两类执行路径、作者性能与外部CPU CI的证据边界。
- docs/24：循环感知驻留、110→134字节精确IQ3_S重排、NVFP4布局、prefill分组、relay失败传播与生命周期、完整host快照、通用lookup/Q4/TC的限制。
- docs/25：G00–G05六个可选任务，含接口/文件/依赖/负例/验证与停止条件。G04初始DEFERRED。
- docs/26：GX01–GX20增量测试、trace与消融合同、真实Ghost CLI、由T01实现后可用的Atomic lab命令。
- manifests/ghost-source-audit.json、ghost-transfer-matrix.json与validation/ghost-ci-observed.json。

### 同步

README、AGENTS、02/05/08/09/15/19/20/22与机器任务图、源锁、run task_id、测试目录。共26篇专题、24任务、68项计划测试、21个登记来源ID、16个核心来源pin。schema_version保持1.0，文档包版本1.1。

### 固定来源与证据

- Ghost main：`b6cd02e099af2453f3674e047d5f89152f8a662d`。
- Ghost v0.5.0：`9d15c249d4dbb7c3d376d878748ca71fd1546662`；与main仅README.md/docs/building.md不同。
- 现存官方公开branch只发现main；fork PR heads单独记录，不冒充官方live分支。
- 观察到上游CPU CI 84 passed / 0 failed / 6 ignored；不是本地GPU/模型执行。
- 对relay和提前终止状态路径的风险判断来自静态审查，未在目标GPU复现。

### 仍未完成的工程

没有连接或修改4090服务，没有构建/移植Atomic或Ghost，没有下载/推理模型，没有4090吞吐、质量、长上下文或生产结果。68项计划测试仍NOT_RUN；当时R03以公开runner缺口标BLOCKED；此判断已由v2补查纠正。新增任务只有实现并通过对应gate后才获得能力资格。

### 基线可追溯性

v1.0原ZIP SHA256：`998f6c38ab4e07685e0fdf165d1b10a2089b09bec5424d7d0cb33822c42e1794`。完整变更以本包文件与校验清单为准，验证记录见[VALIDATION](VALIDATION.md)。

# BO 可复现构建与 P0 前端资格结果

Run日期：2026-10-21；跨日交付于2026-10-22（Asia/Shanghai）。状态：**BO_REPRODUCIBLE_BUILD_AND_CPU_FRONTEND_COMPLETE**。已完成本次无需切换GPU服务的BO构建和P0前端工作；**P0-GATE尚未通过，BO GPU运行资格未取得**。

[机器结果](../output/ninfer-v4-bo-build-20261021/final-summary.json) · [原始证据入口](../output/ninfer-v4-bo-build-20261021/README.md) · [上一轮身份审计](ninfer-v4-p0-audit-20261021.md)

## 实际产物与复现边界

全程通过`jssh 29`操作新隔离目录`/home/hhtele/ninfer-v4-bo-20261021`。固定O=`e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`，tree=`6022c83a205853c65510af0b46f0dc337733cbeb`；1149份源码文件的实际bytes与Git blob逐份一致，未修改O或生产源码。采用CUDA13.2工具链、SM89、Release、27B-only、BUILD_TESTING=ON、benchmarks=OFF，编译并行度4；源码只读挂载。

工具链image ID：`sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`。固定基础image digest、Dockerfile、全部已安装包版本、CMakeCache、compile_commands与实际命令均保留。两次构建使用不同的干净宿主目录，容器内同为`/src`、`/build`，固定SOURCE_DATE_EPOCH；oracle/G1的未剥离产物本就同字节；CLI/服务的原始差异仅为非运行`.strtab`中的28个NVCC临时文件名，代码、CUDA载荷和其余段均相同。原始A/B产物和失败结果保留，采用固定工具链标准`strip --strip-all`生成单独release目录。逐份验证所有SHF_ALLOC运行段的地址、大小和内容不变，四个release交付程序SHA逐字节相同：

| 程序 | SHA-256 | clean A/B |
|---|---|---|
| `apps/ninfer` | `83785d72ca85bef58c209d8a1e10bdc1b277d91e150c501c05ac375ed0a4c3cb` | 两次相同 |
| `apps/ninfer-serve` | `ff5e542fef099af557a21108cd0b1359d8f68a068dd57053ddfea225965b596b` | 两次相同 |
| `tests/ninfer_qwen3_8_legacy_frontend_oracle` | `9ae42ece3c34ff80f3def6c9fd331f635b006540611e9333df940e6fc43a86dd` | 两次相同 |
| `tests/ninfer_qwen3_8_g1_diff` | `1c6ec028768a2995c0e3a395ebd85ba686d139edf3a611ecb0ebcd6934393f0f` | 两次相同 |

本轮二进制可复现结论以**已冻结工具链image与已记录的标准release处理**为前提。未把未剥离CLI的原始哈希差异静默改写成PASS。APT安装配方用于解释该image，未把浮动APT仓库未来重新安装的结果声称为同字节工具链。工具链和候选image继续保留在29；另将两者导出为同一离线docker-save归档，配置SHA与原image ID及rootfs层列表已核验，[回执](../output/ninfer-v4-bo-build-20261021/image-export-receipt.json)记录路径、大小和全SHA。此镜像归档保存在29隔离持久目录，未复制到本机、未执行docker load，也不包含现网B29镜像。本机另有源码bundle、BO二进制归档及全部原始测试证据。二进制A/B可复现不代表已验证两次候选image构建的image ID相同，本轮只打包一次候选image。

候选image：`ninfer-v4-bo:o-e0b05f7-20261021`，ID=`sha256:da2f97311826959e7e9c244abf760c1251fbc8b9d12c9636a5657adde6a215a8`。这是无权重、用于后续资格的隔离制品；保留构建工具链，不冒称精简生产镜像。内部四程序SHA已核验；`ninfer --help`和`ninfer-serve --help`均在无GPU设备、无网络、无模型挂载环境实际exit0。初次纯runc检查因缺`libnvidia-ml.so.1`以127退出，失败保留；随后仅将当前主机NVML库只读挂入检查容器，实际验证`/dev/nvidia0`、`/dev/nvidiactl`、`/dev/nvidia-uvm`均不存在，再执行两种help并exit0。NVML路径/SHA已记录，驱动库未烘焙入候选image，也未修改host或现网。没有启动监听服务或加载27B。原源码的snprintf截断编译告警保留在日志中；本轮未改源码处理该告警，也不据编译exit0宣布相关运行时边界已验证。候选镜像的rootfs基础层与记录的工具链image一致。

[二进制归档](../output/ninfer-v4-bo-build-20261021/package-evidence/package-cpu-probe/bo-binaries.tar.gz)已复制到本机，大小322342626bytes，SHA=`86b14a9db7fc074d085e43fe2ed8fcd2db5db6e4161593393bd36319d799dbf2`；同一份也保留在29的`package-cpu-probe/`目录。

## P0前端证据

从现网只读`.ninfer`直接提取六份frontend资源，记录对象offset/bytes、目录及资源SHA，并重新计算整个模型SHA：`eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`。六份与历史资源逐字节一致。原六资源聚合SHA、88行G1用例与toggle原始字节不修改；没有从HF换资源。

O的reasoning_effort模板fixture为8953bytes，按原`read_pinned_template`仅去掉末尾一个LF后为8952bytes，SHA与生产chat_template完全一致。原toggle按原函数处理；这是测试fixture处理，未裁剪冻结测量语料或Pi预算。

6项现有native前端测试实际通过，0失败、0跳过：tokenizer_work、tokenization_equivalence、encoding_restart、boundary_encoding、legacy_oracle、frontend。equivalence原CTest注册没有资源参数；独立qualification清单保留原命令并显式追加实际生产资源路径，未修改源码注册、未把77当通过。engine-linked frontend测试也在不暴露GPU设备的容器内通过。

独立legacy_frontend_oracle已运行两次，复用原用例中的文本建立单独smoke输入，输出字节一致。G1是**新BO资格run**，原88个用例、seed20260925及每profile20K fuzz保持：

| profile | 适用原用例 | legacy/candidate配对输出 | 差异 |
|---|---:|---:|---:|
| real | 53 | 25,193 | 0 |
| synthetic | 74 | 23,613 | 0 |

35/14个profile外用例是既定路由计数，不是required测试skip。比较复用原严格比较器，逐case核对input/resource/kind/status、完整semantic及错误phase/class/message；未删字段或削弱断言。通用比较器保留SUPPLIED_OUTPUTS_ONLY标签，另由本轮source/build/binary/resource/case/command receipts补齐**新run**的产物来源链。未回填旧run缺失的二进制或日志。

原始G1输出、JUnit、完整命令、stderr/stdout、原子status/owner receipt、CMake清单、source bytes和编译器版本均已同步到本机持久目录。两次构建的未剥离产物继续保留在29的build-a/build-b；本机保存其SHA、ELF/字符串差异、原始失败与日志，另完整保存可复现的release二进制归档。没有重跑旧Baseline、历史编程任务或grader。

## 原失败与接续

R1在产物生成前采集CTest清单，随后因清单缺command字段停止；其source/toolchain/frontend build均已完成并保留。R2复用这些产物，刷新清单并通过5项CPU测试，随后补充smoke适配器因误用G1的kind名停止。R3仅修正测试编排和输入映射，继承已通过的测试证据，从smoke接续G1、BO与clean重建。两次编排失败和成本独立保留，未改引擎或golden，接续未重跑已通过的native或G1检查。随后原始哈希比较揭示的非运行符号表差异也独立保留；新release处理另有回执，运行段不变且release oracle输出与已执行raw oracle相同。

曾有一次SSH读取状态超时；没有重复启动owner。后续按原PID/receipt恢复读取，远端构建没有因此重启。 最终归档首次回传触及600秒传输截止，128MiB原始partial另存；用同一冻结export验证已收到前缀SHA后按字节范围续传，最终按完整SHA核对并解包。该步骤只重读归档文件，没有重新构建、运行测试或发送模型请求。

本次工具链准备7.89分钟，BO clean A为11.92分钟、clean B为11.93分钟。从远端首个构建owner启动至CPU包检查完成共约51.53分钟，另有本地准备、证据回传和核验耗时。G1耗时仅为资格过程记录，不作为新优化加速或端到端性能结果。

## 未改现网与剩余门禁

生产container ID/PID/StartedAt、镜像、argv、服务/CLI二进制、launch和proxy SHA均与审计前一致。未执行生产目录写入、服务切换/重启、驱动或模型变更。构建容器使用runc和无GPU设备配置，单容器4CPU/12GiB；实际推理请求、grader运行和现网参数变更均为0。Target T1/.95/k20、presence0、preserve-thinking和Pi medium/32768合同保持。

当前闭合的是BO可重复构建与CPU前端资源/oracle/G1来源证据；B29历史source→binary构建链仍不能倒推为已认证。BO尚未加载模型，GPU数值/状态/容量/协议/restore及完整任务质量未测；P6集成与优化没有实施。token IDs、真实ITL、可靠reasoning拆分、round wall、allocator高水位仍有缺口，p95=null，optimization_qualification=false。

P0-GATE仍需同一候选上的剩余实机/统计和统一独立review；没有创建qualified tag或解锁P1/H0/K0。

## 剩余实机范围、预算与耗时

[明确预算](../output/ninfer-v4-bo-build-20261021/remaining-gpu-plan.json)只针对新的BO诊断run：计划48次、预留16次、硬上限64次，准备/warmup/失败/允许的已知retry均计入；未知结果先核对原请求，不自动重发。

- 32次：两种新文本/tool-JSON格式×四档输入×cold/warm×B29/BO；冻结实际tokenization与独立可写cache。
- 8次：新的合成尾预算1/2、stop、cancel及随后请求状态诊断。此类协议fixture不缩减Pi的32768预算。
- 8次：新的continuation restore/错误恢复序列，逐请求记账。
- 16次预留：仅已登记的准备/漂移/失败处理，不展开旧Baseline矩阵或新完整Java/Pi任务。

单4090当前约22598MiB被生产占用，BO无法同时加载；剩余实机验证需独立GPU窗口和明确切换/恢复授权。按已保全的B29镜像、argv、proxy与原cache三件套执行后恢复，当前没有执行这些动作。规划GPU窗口**2–4小时**，含串行加载、drain、有限诊断和恢复；不含排期，不是新的实测吞吐预测。复用[原始耗时](../output/ninfer-v4-bo-build-20261021/gpu-time-evidence.json)估算：历史core/HTTP200的131K档单请求最长74.90秒，近context档最长172.17秒，含不同输出与cache合同。计划分别为准备/加载15–30分钟、32次前端/cache诊断30–60分钟、状态/恢复序列及预留20–40分钟、现网恢复/readback20–40分钟、回执核对15–30分钟，总计100–200分钟，保守取2–4小时。BO尚无GPU耗时，此处保留不确定性。

64次不构成正式p95、完整质量矩阵或优化资格。真实ITL等producer缺失需另明确最小测量实现与资格，不能拿SSE间隔填补，也不能因BO编译成功就宣布P0/P6通过。

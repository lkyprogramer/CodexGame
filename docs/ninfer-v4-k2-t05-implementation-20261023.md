# K2-T05 CPU实现、BO构建与冻结回执

已通过`jssh 29`在隔离分支完成普通prefill卷积直接写连续Q/K/V候选、最小驱动、BO构建和集成评审。本次16个CPU合同全部通过，工具及空账本已冻结。**未执行GPU、模型、HTTP或旧Baseline；真实逐bit、Graph和性能结果均为NOT_RUN。** 原服务继续停止。

## 身份与回执

| 项目 | 当前值 |
|---|---|
| 分支 | `codex/k2-prefill-split-20261023` |
| 远端根 | `/home/hhtele/ninfer-v4-k2-t05-20261023` |
| 复用基树 | `41a913488b0138fe868a8321d2f6a86ce83e313f` |
| 候选树 | `3ea537c00c759ef2a4577b525ae691f694ae102e` |
| 冻结SHA-256 | `7ca7ea1a0fd4199438abbfbdfe2188a56e5115570b18dcf6de75b2dcb5135bfc` |
| probe SHA-256 | `b1679dd61eee7eae0a3990129f32a0e8a0af8262fdb23e43d10dbef49aea7c19` |
| 冻结目录 | `/home/hhtele/ninfer-v4-k2-t05-20261023/prepared-window-r1` |

[冻结原件](../output/ninfer-v4-k2-t05-20261023/remote/prepared-window-r1/freeze-receipt.json)、[准备回执](../output/ninfer-v4-k2-t05-20261023/remote/evidence/preparation-receipt.json)、[原始空账本](../output/ninfer-v4-k2-t05-20261023/remote/prepared-window-r1/initial-ledger.json)、[补丁](../output/ninfer-v4-k2-t05-20261023/remote/evidence/K2-T05.patch)、[源码身份](../output/ninfer-v4-k2-t05-20261023/remote/evidence/source-identity.json)。没有创建提交或推送；tree是已暂存候选内容的身份，不是生产镜像。

## 实现范围

profile为`SM89_GDN_PREFILL_C10240_SPLIT_QKV_T65_T128_T512_T1024_V1`。仅支持BF16、连续二维张量、4B对齐、C10240，Q/K/V宽度2048/2048/6144，T65/128/512/1024。实际原服务配置的prefill chunk1024保持不变。

新增bench-only pairs kernel，沿用原四tap FP32累加、SiLU和BF16舍入，只改变最终store地址。候选仍先执行输出kernel，再执行**原BF16 conv state更新kernel**。raw kernel、raw launcher、默认wrapper及模型调用路径不变；不接入产品默认dispatch，不改arena布局、采样、context或Pi medium/32768。

唯一FP64 `causal_conv_oracle`及原A16阈值提取为共享测试头。原oracle、阈值、raw累加helper、输出kernel及state kernel的函数体均已核对不变。旧卷积测试只编译检查引用闭合，没有执行。源码保持证明见[source-preservation.json](../output/ninfer-v4-k2-t05-20261023/source-preservation.json)。

新驱动保留独立raw/split池；4个数值场景覆盖非零历史、finite压力输入、Q/K/V分界及末通道、state精确同址与分离。未来实机会比较完整BF16 Q/K/V、最终state逐bit相同，核验全部guard及不可变输入，并使用原FP64准则。Graph函数地址从实际launch TU导出，诊断先持久化实际函数/几何/参数/copy/dependency，再检查；不从probe重新实例化生产kernel获取地址。

关键实现：[candidate kernel](../output/ninfer-v4-k2-t05-20261023/source/src/ops/kernel/causal_conv1d.cuh)、[private launcher](../output/ninfer-v4-k2-t05-20261023/source/src/ops/launcher/causal_conv1d.cu)、[最小probe](../output/ninfer-v4-k2-t05-20261023/source/bench/ops/k2_prefill_split_probe.cu)、[共享FP64参考](../output/ninfer-v4-k2-t05-20261023/source/tests/ops/causal_conv_ref.h)、[冻结与控制工具](../output/ninfer-v4-k2-t05-20261023/source/tests/k2_t05/README.md)。

## 已运行的验证与修复

BO复用固定镜像`sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`、现有依赖及独立复制的构建目录；Release、CUDA13.2、SM89、27B-only，最多4 worker。容器显式`runc`、禁网络，`NVIDIA_VISIBLE_DEVICES=void`、无NVIDIA设备；未下载或加载模型。新工作树时间戳触发了较多已有目标重编译，不将其描述为全部缓存命中。

实际构建命令为：

```bash
cmake --build /build -j 4 --target ninfer_k2_prefill_contract_test ninfer_k2_prefill_split_probe ninfer_causal_conv1d_silu_test ninfer-serve
```

首轮648.71秒后在新probe失败：固定CUDA13.2的`cudaGraphNodeGetDependencies`为四参数接口。保留[原失败日志](../output/ninfer-v4-k2-t05-20261023/remote/evidence/build-r1.stdout)；核对[镜像原头文件](../output/ninfer-v4-k2-t05-20261023/CUDA13.2-dependency-header.stdout)后，只修正两处调用，增量构建19.28秒通过。非默认edge data仍会返回错误并停止，不静默忽略。

仅执行本次CPU合同：

```bash
/build/tests/ninfer_k2_prefill_contract_test
cd /src/tests/k2_t05
NINFER_K2_T05_PROBE=/build/bench/ninfer_k2_prefill_split_probe python3 -B -m unittest -v test_contracts
```

结果为8/8 C++ **Graph元数据合同**及8/8 Python **CPU编排合同**通过，无skip。Python使用实际BO probe的`--plan-only`，核验冻结、篡改拒绝、预算/profile、single-use、unknown不重试、授权先于外部动作、原容器保护及截止。这里没有CUDA数值验证或模拟GPU通过。原始结果见[C++ stdout](../output/ninfer-v4-k2-t05-20261023/remote/evidence/cpp-cpu-r1.stdout)、[Python stderr](../output/ninfer-v4-k2-t05-20261023/remote/evidence/tools-cpu-r1.stderr)。

独立只读集成评审的问题已修复：默认流reset完成后显式同步，再进入NonBlocking Graph流，避免初态竞态；同步位于计时外且不增加kernel/copy。候选非零退出现在先保留result，再使控制器明确失败。CPU metadata措辞及CUDA接口修复均已复核。见[评审记录](../output/ninfer-v4-k2-t05-20261023/independent-review.json)。评审者未代替主代理执行构建或测试。

初次隔离依赖复制因跟随包内悬空symlink失败，已保留[原错误](../output/ninfer-v4-k2-t05-20261023/setup-remote.stderr)，改用保留symlink的独立复制后继续；不重建或下载依赖。以上构建/环境失败均不计为模型质量或GPU数值失败。

## 已冻结的最小实机窗口

这是未来窗口上限，本次所有GPU账本计数均为0，无runtime或native owner。当前冻结不授予GPU执行。

| 项目 | 冻结上限 |
|---|---:|
| 数值场景 | 4：T65/128/512/1024 |
| direct Op / 直接算法kernel | 20 / 16 |
| Graph capture | 4：仅T512/1024×raw/split |
| correctness / warmup / timing replay | 8 / 16 / 160 |
| replay总计 | 184 |
| 算法kernel总执行 | 384＝16＋184×2 |
| 段内拷贝 | direct host调用12、capture host调用6、raw replay拷贝执行276 |
| 模型 / HTTP / 辅助compute kernel | 0 / 0 / 0 |
| 预计GPU耗时 / 硬截止 / 开始清理 | 2–5分钟 / 10分钟 / 第7分钟 |

raw Graph预期为2个kernel＋3个copy，split为2个kernel；276是拷贝操作执行量，实际节点必须实机见证，当前不能称已通过。

辅助传输按guard256B/端、最多64次准备与检查点的保守包络独立冻结，包含初始化、poison、reset、guard及结果导出；与段内三次拷贝分开，不能用于追加测量：

| 辅助方向 | API次数上限 | bytes上限 |
|---|---:|---:|
| H2D | 508 | 4,447,860,736 |
| D2D | 128 | 7,929,856 |
| D2H | 768 | 5,386,141,696 |

未来计时覆盖卷积输出＋原state更新＋raw三次提取，对比split两kernel整个段。5批AB/BA配对，每图每批8 replay；reset/检查/导出在event区间外，event时间、host投递与完成wall单列。host提交占event段过高时不能给纯kernel或稳定收益结论；驱动单列host条件。段级中位改善至少10%、至少4/5批更快且数值/Graph/guard全过，才有`SEGMENT_SIGNAL_NOT_K4`；无信号或失败停止，不自动加测。

预期消除T1024下每层40MiB、48层1.875GiB的**逻辑中间读写**，最终Q/K/V写仍存在。实际HBM、allocator节约、完整prefill及Chat收益都未测。只有段级信号成立后，才单独准备和授权完整prefill/Chat验证；候选资格与生产发布仍独立。

## 保留与交付边界

原服务镜像、argv及缓存身份未变，容器exited/PID0、GPU无计算进程。18处G1差异、C1附件缺口、旧Baseline、K1/K2/C0成绩与全部失败保留；三个已关闭任务的追加预算继续为0，不启动K1-T02。旧任务没有重跑，`p95=null`、`optimization_qualification=false`。

[实施记录](../output/ninfer-v4-k2-t05-20261023/implementation-core.json)与[最终交付摘要](../output/ninfer-v4-k2-t05-20261023/final-summary.json)区分已完成CPU验证和未执行GPU资格。V4执行入口已同步当前状态，原文归档保留；本轮只准备上述实机窗口。

最终[交付核查](../output/ninfer-v4-k2-t05-20261023/document-validation.json)通过：8份冻结文件、1263份持久源码、15份补丁文件、全零账本及417份Markdown的当前MANIFEST一致；20任务/4门禁/80断言、31个可选scope不变。核查只读取回执和哈希，没有重复旧套件或旧负例。原K1的4份关键结果与Baseline的3份交付哈希不变。

源码、原始构建/CPU日志、补丁和冻结目录已从远端备份到持久目录；归档SHA为`219e49d192086852102dc937b01e615fda4ed02abf4fa2c9d48acfae2e741f1c`。见[归档回执](../output/ninfer-v4-k2-t05-20261023/archive-receipt.json)。

# K2-T01 CPU实施与最小实机冻结

K2-T01已完成隔离补丁、BO增量构建、定向CPU验证和独立集成评审。状态为 **CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN**。本轮没有发起GPU算子、模型或HTTP请求；未取得数值、性能或K4资格。原GPU服务保持停止。

工程目录为29的`/home/hhtele/ninfer-v4-k2-20261023/source`，分支`codex/k2-gated-rmsnorm-20261023`。从C0工程树`4d31af405fca9c70bd39a71257f83f4eeebbd0bc`继承，补丁树为`13223b2b2989d0cf580715b197b276d74acffc86`；HEAD仍为O `e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`，未创建提交、推送或部署。工程继承不表示C0获准生产采用。

## 补丁与构建

只变更9个bench/test文件，见[补丁](../output/ninfer-v4-k2-implementation-20261023/K2-T01.patch)与[源码身份](../output/ninfer-v4-k2-implementation-20261023/source-identity.json)。其余1237个基点文件逐一匹配，包含全部583个`src/`文件；产品kernel、launcher、默认分派、SHA/ContentId、缓存格式及采样代码均未变。

- 新增独立`ninfer_k2_gated_rmsnorm_probe`，直接实例化现有`rmsnorm_warp_bf16x2_kernel<Gated,Block>`的128/256/512线程配置。限定BF16 aligned、D128/H48、T1/T4；保持warp内归约、gate表达式和BF16舍入。它不使用旧plain候选或payload control替代Gated算法。
- 将既有FP64 oracle与原误差阈值原式移到共享头，旧测试改为引用；probe的host oracle关闭fast-math和浮点收缩。旧suite仅重新编译，没有执行。
- 新增固定预算的native驱动与一次性控制器。默认只输出CPU计划；GPU入口需要另行授权、精确冻结SHA、空账本和未使用runtime。native独占写账，先持久化预留，再在实际入队前检查截止。未知预留不自动补跑。
- 未来控制器持有共享GPU锁，独立guardian先就绪，420秒关闭准入并仅清本窗口候选，600秒硬截止。原服务ID、镜像、启动参数SHA及缓存dev/inode在启动前和清理后核查，工具没有恢复原服务的动作。

复用BO镜像`sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`、既有C0构建产物与冻结OpenSSL依赖。Release、CUDA13.2、SM89、仅27B、最多4个worker。在`runc`、无网络、无NVIDIA设备的容器内执行：

```sh
cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DOPENSSL_INCLUDE_DIR=/deps/include \
  -DOPENSSL_CRYPTO_LIBRARY=/usr/lib/x86_64-linux-gnu/libcrypto.so.3 \
  -DNINFER_BUILD_QWEN3_8_27B=ON -DNINFER_BUILD_QWEN3_6_35B_A3B=OFF
cmake --build /build -j 4 --target ninfer_k2_gated_rmsnorm_probe ninfer_gated_rmsnorm_test
```

配置0.867秒，构建17.373秒，均返回0。此次是受影响目标的增量构建，没有重复BO清洁全构建或旧Baseline。[原始构建回执与日志](../output/ninfer-v4-k2-implementation-20261023/remote/evidence/build-r1.json)。

## 验证与评审结果

新增控制器CPU场景分两次完成：首轮19项通过，评审修复后只运行新增4项并全部通过，累计23项；未重复旧任务。范围包括冻结SHA与二进制篡改拒绝、非空账本/已有runtime拒绝、授权前无外部动作、精确候选所有权、原容器身份与缓存核查、截止、持久化和失败保留。[首轮结构化记录](../output/ninfer-v4-k2-implementation-20261023/remote/evidence/controller-cpu-r1.json)来自实际工具输出转录，未保存为原始stdout；对应19项源码快照保留。第二轮[原始日志](../output/ninfer-v4-k2-implementation-20261023/remote/evidence/controller-cpu-r2.stderr)完整保存。

在同一无GPU设备的BO容器中，probe的11项CPU CLI检查通过：默认/显式计划、错误参数、缺失runtime、未ARMED、预算错配、非空账本、过期截止、越界路径、已有结果、已认领窗口；所有拒绝发生在CUDA准入前。[检查结果](../output/ninfer-v4-k2-implementation-20261023/remote/evidence/native-cpu-r1.stdout)。冻结控制器另执行一次`--plan-only --freeze-sha`，确认不创建runtime、不改空账本。

两个独立代理分别评审数学/Graph和控制器/合同，均为静态只读评审，没有代跑测试。以下问题已修复并保留评审记录：

1. 两个fallback最初都非对齐，现明确为T1非对齐与T5对齐；T5走原512、T1非对齐走原generic256。候选只接收aligned T1/T4。
2. 账本持久化可能跨准入截止，现持久化后及每次norm/Graph replay前重新检查单调时钟。
3. 首次清理失败可能被后续成功覆盖，现独占持久保存`first-cleanup-failure.json`。
4. guardian退出时仍运行的候选可能被误记EXITED，现必须fresh readback确认`Running=false/PID0`，否则记未知失败并清理。

复审无剩余阻断。CPU mock证明合同分支，不能替代真实容器清理、SM89数值、Graph或性能结果。[评审记录](../output/ninfer-v4-k2-implementation-20261023/review.json)。

## 冻结回执与实机范围

准备根：`/home/hhtele/ninfer-v4-k2-20261023/prepared-window-r1`。

| 身份 | SHA-256 |
|---|---|
| freeze-receipt.json | `37a398b62655482f0f34ea42970d2eb4796f3f8d70c5cb7731b99af2c29cdd0e` |
| probe | `37ed2da07ebf489549c743fa92104a9aeea8c851e13715cae1615f8ac458bf5a` |
| CPU交付归档 | `3cf6fc7e58bb38f97b5bb2e4caecd37054747ffde142d0f1ecd55097b84d7210` |

[准备回执](../output/ninfer-v4-k2-implementation-20261023/preparation-receipt.json)绑定6个执行输入、源码/BO身份、原服务快照和初始账本。执行输入已只读化，当前账本全0、无reservations、无runtime/owner锁，`authorization=NOT_AUTHORIZED_PREPARATION_ONLY`。本机已复制归档并验证SHA，包含完整源树、补丁、工具、二进制与CPU证据；不含模型权重。

后续最小实机筛选只需本算子，不加载模型：

| 项目 | 冻结上限 |
|---|---:|
| 数值场景 | 8：T1/T4×普通、near-zero、饱和gate共6，加T1非对齐/T5对齐2个fallback |
| direct Op | 22：6×3配置＋2×原/回退 |
| capture | 6，每图一个真实Gated norm节点 |
| correctness replay | 12 |
| warmup replay | 60 |
| timing replay | 1920：6配置×5批×64 |
| 全部replay | 1992 |
| HTTP / 模型提交与准入 | 0 / 0 |
| 预计GPU实际耗时 | 2–5分钟 |
| 清理 / 硬截止 | 第7分钟 / 10分钟 |

数值保持原double oracle阈值，另比较旧新BF16字节、guard和输入保持；Graph核对函数指针、block/grid。五批交错对照原512，单节点Graph replay中位相对改善≥10%且≥4/5批更快，最多得到`OP_SIGNAL_NOT_K4`。event计时覆盖主机逐次投递的64次replay及截止检查，可能含GPU等待投递的间隔，**不是纯kernel latency**。没有稳定收益或数值失败即停止保留原路，不追加配置或重试追成绩。

本轮无需再补CPU驱动。GPU筛选仍未获执行授权。仅有胜者时，才单独准备匹配真实27B/现有权重与context的整轮驱动，预计另需1–2工程小时、5–10分钟GPU；内部Graph预算尚未冻结，不得直接运行旧bench或把整轮验证当本轮开发前置。norm份额、整轮/Chat收益均为null。

## 保全与当前边界

原服务仍exited/PID0，GPU计算进程为空；原容器ID、镜像、启动参数及cache dev/inode不变，C0原serve二进制SHA不变。[回读](../output/ninfer-v4-k2-implementation-20261023/runtime-after.json)。采样、context及Pi medium/32768保持原样。C0继续关闭，不追加补测。Baseline、18处G1差异、C1附件缺口及全部历史失败未修改。

V4入口、注册表、预算与当前状态已更新；修改前10份原文和SHA单独保留。`p95=null`、`optimization_qualification=false`，候选资格和生产发布门禁继续独立。

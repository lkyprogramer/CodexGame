# K2-T05 T1024 完整 Prefill／Chat：诊断构建缺陷，窗口停止

**本轮未完成验收。raw 首个 warmup 在导出时报告 `actual target logits capture missing`，候选和 Chat 尚未开始，完整 Prefill／TTFT 收益均无结果。** 已通过 `jssh 29` 保全现场，定位并修复诊断构建宏的目录作用域；raw、candidate 的 CPU 增量构建及实际对象引用检查通过。修复版本未执行 GPU，不把它写成实机通过。

## 执行身份与停止位置

本轮只启动一次原 `prepared-window-r2`，冻结 SHA `4aaa74fc762467e23859303405c7e4c00f9f0cffe64a11b9d74a01c9fd8ab39d`。候选源树 `abc974d38d861c4fa72692345aadfc8565624fa3`、raw 源树 `a5ba33de12d75ab1e16a153020e4068094ee1757` 均复用准备回执，未重跑旧 Baseline、旧算子筛选或 T512。

远端根为 `/home/hhtele/ninfer-v4-k2-t05-full-prefill-prep-20261023`。启动回执 `hardware-r1-dispatch.json` 在 2026-10-23 15:22:00 UTC 创建，supervisor PID 165401；controller、guardian 与精确 label 绑定。原服务停机、GPU 空闲、lease 可独占、冻结文件和初始账本均检查通过后才启动。

raw 容器 `85f49798f707f342193b1d4d5d6180d42af1a09e87c80bf9fb44f5337f9e482d` 退出码 1。原始错误见 `runtime/native-raw/failure.jsonl`，控制器随后报 `candidate nonzero exit or unknown process`。这里的 candidate 是控制器对实验容器的统称，**实际执行的是 raw，对照候选并未运行**。

失败点位于 `export_image()` 调用 `save_logits()`。按冻结源码控制流，该点在完整 Prefill、首个 target token 采样、MTP 准备、`resolve_prefill_lane(..., true)`、384 次 raw／0 次 split 路由断言之后。72 个实际状态段共 **306,659,921 字节**已写出并另做 SHA 清单。因此可判定首个 warmup 已执行到提交后的导出阶段；这不是新测得的独立数值或性能 PASS。

target logits 文件及原始 `state-and-logits.json` 均不存在。不能用已导出的 state 重建该次 target logits，不能把事后 SHA 清单冒充原始导出元数据。原始迭代日志只有一行 `RESERVED`，没有 `COMPLETED`；不回写旧账本，也不重发该次模型计算。

## 实际用量与缺口

| 项目 | 冻结上限 | 本轮结果 |
|---|---:|---|
| native Prefill | 12 | raw 首个 warmup 已执行，导出失败；其余未执行 |
| 有效测量配对 | 5 | **0** |
| 新 Chat | 4 | **0，未放行** |
| HTTP warmup | 2 | **0** |
| wire | 8 | **0** |
| 状态／target logits 逐 bit 比较 | 1 组 | **NOT_RUN** |
| 完整 Prefill／TTFT 收益 | — | **null，无可用对照** |

高层账本保留 `RUNNING`：raw 阶段预留 6 个 native 单位，完成数 0，reservation 仍为 `RESERVED`。这表示失败现场的预留未退还，不表示进程仍在运行；也不能把阶段预留 6 写成实际执行了 6 次。

CUDA 审计文件最后状态为 `MODEL_READY`，早于失败的 Prefill。该检查点记录 capture 9、replay 1、direct kernel 806、算法 kernel 1612、capture kernel 7254、capture copy 1224；H2D 1069 次／17,901,827,064 字节，D2D 4 次／40,960 字节，D2H 2 次／896 字节，memset 813 次／774,154,640 字节。**这些只是加载阶段的最后持久值，不是整个失败进程总数。** Prefill／状态导出的最终累计值未落盘，保留为缺口。冻结的所有资源上限未提高，CPU 修复阶段新增 GPU／模型／HTTP 均为 0。

原冻结控制器要求完成 raw/candidate 的状态与 logits 比较后才允许 Chat。证据门禁在此失败，本轮不跳过它继续发送请求，不重新启动 single-use 根目录。完整原方案还需要新的 raw 正确性 warmup 才能得到 logits，再完成两侧五次未污染计时；将其加入本轮会增加原 12 次总上限，不能静默追加。下一窗口及资源账本尚未冻结或启动。

## 根因与 CPU 修复

诊断宏原先在 `tests/k2_full/targets.cmake` 中通过 `set_source_files_properties()` 设置，却没有指定实际目标目录。`ninfer_engine` 创建于 `src` 目录，因此该 source property 没有作用到 `qwen3_8_27b/impl/variant.cpp`。raw、candidate 的真实 `compile_commands.json` 均缺少 `-DNINFER_K2_FULL_PREFILL_DRIVER=1`。

观测函数本身编入了 audit 对象，所以仅看到最终二进制含 `k2_full_observe_logits` 定义不足以证明模型调用了它。这是前次 CPU 准备遗漏的构建闭合检查，不是模型不产出 logits，也没有证据指向 T1024 数学错误。

最小修复只增加目录选择：

```cmake
set_source_files_properties(${PROJECT_SOURCE_DIR}/src/targets/qwen3_8_27b/impl/variant.cpp
  TARGET_DIRECTORY ninfer_engine
  PROPERTIES COMPILE_DEFINITIONS NINFER_K2_FULL_PREFILL_DRIVER=1)
```

使用独立只读 overlay `hardware-r1-cpu-repair/targets.cmake`，保留原 source、r1/r2 冻结包、初始账本、失败账本和四个原诊断二进制。复用 BO CUDA13.2／SM89／Release／27B、4 worker、runc 无 NVIDIA 设备、无网络及既有构建缓存，分别执行：

```sh
cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DOPENSSL_INCLUDE_DIR=/deps/include \
  -DOPENSSL_CRYPTO_LIBRARY=/usr/lib/x86_64-linux-gnu/libcrypto.so.3 \
  -DNINFER_BUILD_QWEN3_8_27B=ON -DNINFER_BUILD_QWEN3_6_35B_A3B=OFF \
  -DNINFER_K2_FULL_PREFILL_DRIVER=ON
cmake --build /build -j 4 --target ninfer_k2_full_native ninfer-serve
```

两侧均退出 0。修复后的两份真实 compile command 均包含诊断宏，两个模型 `variant.cpp.o` 均有 `U k2_full_observe_logits(...)`，证明实际调用方已编译进模型对象。主代理检查了修复作用域和四个链接产物；未使用独立代理评审，未重跑已通过 CPU 套件。原有 continuation image `snprintf` 编译告警原样保留。

新四个二进制位于远端 `hardware-r1-cpu-repair/bin/{raw,candidate}/{native,server}`，SHA 见 `repair-proof.json`；它们与原 r2 不同，**尚无新的 GPU 冻结回执、空账本或执行授权回执，不能直接替换原 r2 启动**。此 CPU 证明不等于运行时 logits 捕获、完整状态比较或 Chat 已通过。

## 清理、备份与后续边界

guardian 在窗口开始后 **61.943788373 秒**完成候选清理，早于第 17 分钟清理和 20 分钟硬限。controller/supervisor/guardian 均已退出；失败容器保留为 exited／PID 0。再次验证原镜像、启动参数、cache dev/inode 未变，`ninfer-4090-prod` 仍 STOPPED，GPU idle、lease free。未恢复原服务、未部署候选，采样/context/Pi medium／32768 均未改变。

原始失败归档 `hardware-r1-failure-evidence.tar.gz`，233,202,375 字节，SHA `f477f2a8bfa1616b8a09b5a5978e7215891c72b626b6ba1f867451ebfe092a7f`，含 72 个状态段、原 raw/状态/容器日志、账本、冻结文件、启动和退出回执。CPU 修复元数据包 `hardware-r1-cpu-repair-metadata.tar.gz` SHA `65cd54bed0e315a374f41462e8117e5387d6bf085d5f40531f201deb766c6519`。不含大状态段的完整失败元数据包 SHA `d05a6d190c6a18cf042e4bf4b45e85d9fc133a76536aa9df8f17df4471d091f4`，包含原始 failure/audit/journal/容器日志。

远端原文件和完整状态归档均持久保留、重新核验 SHA。CPU 修复及失败元数据在 [本地实机证据目录](../output/ninfer-v4-k2-t05-full-prefill-hardware-20261023/) 完整保存。大状态包本地复制停止于 81,730,560 字节，明确命名 `.partial`，**不是本地完整备份**；完整原始状态此时只在远端原目录和远端归档。未用元数据替代原始状态，具体状态见 `backup-status.json`。

剩余最小完整对照仍是 **12 次 native（每侧 1 correctness warmup＋5 measured）、4 Chat＋2 HTTP warmup、8 wire**，仅包含本次未通过或未开始的完整 Prefill／Chat，不重复任何旧 GPU 数值/Graph/T512/Baseline。此前 raw 失败计算及成本单列。新驱动需先版本化并冻结新的累计成本、截止和不可退款额度，不能相加旧空账本；预计准备 0.5–1 小时、实机 8–15 分钟，仍建议 20 分钟硬限／第 17 分钟清理。这是剩余工作的估计，未执行，也不是已通过。

18 处 G1 差异、C1 原附件缺口和全部旧失败保留。`p95=null`，`optimization_qualification=false`。算子段原 T1024 信号不外推为完整 Prefill 或 Chat 收益；候选资格与生产发布门禁继续独立。

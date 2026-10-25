# T4长上下文GQA：可构建候选在新增spill门禁结束

**已完成隔离实现、BO构建、必要CPU验证和集成评审；Bc64单一配置没有通过编译资源可行性门禁，状态为`CLOSED_FEASIBILITY_NEW_SPILL`。没有进入GPU首筛，不追加其它线程配置或tile。**

ptxas明确报告候选的寄存器spill高于同编译条件的原路线。按[既定方案及止损条件](ninfer-v4-post-w6-selection-20261024.md)和[kernel选型中的新spill停止规则](../output/ninfer-v4-post-w6-selection-20261024/kernel-source-audit.md)，在GPU前结束此具名候选。这是可行性不合格，**不是实测更慢，也不证明所有Attention分块方向无效**。

## 实现范围与身份

通过`ssh -J jump 29`创建隔离分支`codex/gqa-t4-bc64-20261024`，远端根`/home/hhtele/ninfer-v4-gqa-t4-bc64-20261024`。基点树`a728df11f92360108a3f12bb619137dafe4eed3d`，候选树`b361766a8072943b2cde700ae12263efd16423db`；未创建commit、push或部署。

仅变更6个源码文件：`bench/CMakeLists.txt`和5个`bench/ops/gqa_t4_*`文件。新增默认关闭的`NINFER_GQA_T4_PROBE`编译目标；原产品库、默认路由、采样、codec、缓存格式及Target状态链没有修改。[源码身份及逐文件SHA](../output/ninfer-v4-gqa-t4-bc64-20261024/remote/evidence/source-identity.json) · [可构建补丁](../output/ninfer-v4-gqa-t4-bc64-20261024/remote/evidence/GQA-T4.patch)。

实现了C1/T4/group6/rk4v4、8192/32768/131072 visible keys的原Bc32和单一Bc64入口，两路复用原kernel数学、split容量及reduce。保持`Masked=true`、显式非零页表行和`writes_cache=false`。它仍是预填cache的partial＋reduce实验，不是Target append集成或完整decode。

驱动复用已有控制器和原GQA数值checker；13个CPU codec/FP64 oracle函数按原函数字节提取并核对来源。CPU预编码与完整FP64参考生成入口已实现，但由于资源门禁失败，**未运行完整6场景参考生成，也未运行6个GPU数值场景**。没有用CPU辅助合同代替GPU数值/Graph资格。

## 编译资源结论

BO环境复用固定镜像`sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`，CUDA13.2、SM89、Release、4个CPU worker、runc、无网络且不暴露GPU。最终probe构建通过。[最终BO回执](../output/ninfer-v4-gqa-t4-bc64-20261024/remote/evidence/BO-build-r4.json)。

| ptxas编译指标 | 原Bc32 / 8warps / MinBlocks2 | Bc64 / 16warps / MinBlocks1 |
|---|---:|---:|
| 寄存器/线程 | 128 | 128 |
| stack frame | 8B | 64B |
| spill stores | 4B | 64B |
| spill loads | 4B | 72B |
| 静态shared/CTA | 43,648B | 13,440B |
| 动态shared/CTA | 0 | 65,536B |

这些spill数字是编译器报告，不是实测每请求内存流量。`cuobjdump`的`LOCAL:0`不能否定stack里的spill；因此追加了无GPU的ptxas详细报告，没有根据stack大小猜测结论。[原始ptxas日志](../output/ninfer-v4-gqa-t4-bc64-20261024/remote/evidence/BO-ptxas-r1.log) · [绑定最终源码树和二进制SHA的资源判定](../output/ninfer-v4-gqa-t4-bc64-20261024/remote/evidence/resource-assessment.json)。

源码可解释这个风险：Bc64使producer的score临时量从16增至32个FP32元素，而两路都限制在128个寄存器。它解释了更高寄存器压力的可能来源；没有SASS执行计数或GPU计时，不能据此计算净收益/损失百分比。实际总shared为78,976B，取代准备阶段未含编译布局的78,992B推导值。

## 验证与评审

实际执行的最小命令与结果：

```sh
# BO无GPU容器，source只读，复用现有build/deps
cmake -S /src -B /build -DCMAKE_CUDA_ARCHITECTURES=89 -DNINFER_GQA_T4_PROBE=ON ...
cmake --build /build --parallel 4 --target ninfer_gqa_t4_probe
/build/bench/ninfer_gqa_t4_probe --cpu-contract
/build/bench/ninfer_gqa_t4_probe --plan
cuobjdump --dump-resource-usage /build/bench/ninfer_gqa_t4_probe
# 精确候选编译命令仅追加--ptxas-options=-v，输出独立诊断对象，未替换原二进制
```

完整可复现argv保存在对应`BO-*.json`；上面的`...`只是缩写，不是声称执行过的完整命令。

- 最终BO构建：**PASS**。初次源码同步/目标准备失败、CUDA13.2 Graph API参数编译失败均保留；API已修复，未消耗GPU预算。
- CPU数值辅助合同：**PASS**，检查FP16、ties-even、zero scale、constant-V FP64、非法shape及原checker正负例；原数学未在后续守卫修正中改变，复用通过证据。
- 控制工具：初轮8项CPU回归通过；新增spill准入后3项新回归及3项受影响回归通过。没有重跑旧Baseline或原模型任务。
- 独立集成评审：失败前输出/参数证据缺口已修复；无剩余阻塞实现的问题。评审者只读，没有代跑构建或GPU。[评审记录](../output/ninfer-v4-gqa-t4-bc64-20261024/review.json)。
- **真实候选冻结拒绝：PASS**。用最终二进制、源码树及实际ptxas判定调用freezer，得到预期的新增spill拒绝，且未创建冻结目录、空账本或GPU窗口。[拒绝原文](../output/ninfer-v4-gqa-t4-bc64-20261024/remote/evidence/freeze-rejection.stderr) · [负例回执](../output/ninfer-v4-gqa-t4-bc64-20261024/remote/evidence/freeze-rejection.json)。
- 修复继承的旧Q4控制器权限问题：候选容器显式使用宿主UID/GID，避免root写0600账本后宿主无法读取。无GPU的runc容器已验证UID/GID、0600模式和宿主读回；GPU设备访问没有验证。[权限验证](../output/ninfer-v4-gqa-t4-bc64-20261024/remote/evidence/owner-uid-validation.json)。

同时修正了一处驱动判断：`cudaFuncAttributes.localSizeBytes==0`不能代表“没有新增spill”，而且原路线自身已有spill。现在保存该属性并单独检查可驻留性，真正的spill门禁移到CPU freezer，绑定源码树/二进制，逐项比较candidate与raw的spill stores/loads；伪造PASS状态也不能绕过。**没有为运行本候选放宽门禁，本候选仍被拒绝。**

## 预算与未验证部分

拟议主预算保持6场景、12 direct、6 capture、240 replay、504算法kernel，另12个capture节点；模型/HTTP为0。驱动已枚举辅助上限：

| 辅助资源 | 驱动计划上限 | 实际GPU消耗 |
|---|---:|---:|
| H2D | 12次 / 386,363,648B | 0 |
| D2H | 27次 / 387,100,928B | 0 |
| memset，含cold flush | 276次 / 67,646,914,560B | 0 |
| 显式cudaMalloc | 6次 / 累计1,191,227,648B | 0 |
| D2D、辅助compute、模型、wire | 0 | 0 |

最大显式缓冲558,132,992B，不包括CUDA模块/Graph内部资源，不能称allocator高水位。由于未通过可行性门禁，**以上只是停止候选的计划，不是可执行冻结额度**。actual direct/capture/replay/kernel/model/wire均为0，没有占用10分钟GPU窗口，也没有启动候选GPU容器。

GPU数值、Graph、自身逐bit、整Op计时、完整decode、TTFT及质量均**未运行/未证明**。收益保持null，`p95=null`、`optimization_qualification=false`。不进入append、native或Chat补测，不扩大到其它warps/tile来绕过单一候选范围。

## 收尾

2026-10-24T14:28:47Z核查：原服务仍为`STOPPED_IDENTITY_UNCHANGED`，镜像、argv和缓存目录设备/inode保持，GPU compute列表为空。没有需要清理的实验GPU进程；没有恢复原服务。[最终状态](../output/ninfer-v4-gqa-t4-bc64-20261024/remote/evidence/final-status.json)。

18处G1差异、C1与Baseline附件缺口、全部旧实验失败原样保留。原V4的其它候选继续保持各自状态；此结果不关闭H2、H6、H7、K3、W8/W16或utility，也没有自动开始它们。源码、工具、原始构建失败、资源判定和拒绝回执均已留存于本机持久工作区及29隔离目录。

可执行二进制保留在29的`build/bench/ninfer_gqa_t4_probe`，SHA绑定在资源评估中。包含大二进制的首次归档传输超时，部分归档保留且不计作成功备份；随后完整导出了紧凑文本证据和工具。没有丢失远端二进制，也不声称本机已有其完整副本。

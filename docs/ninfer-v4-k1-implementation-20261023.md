# K1-T01 correction Record/Fold：CPU候选与实机冻结

K1-T01已完成C1/W4、48层候选、最小驱动、BO构建、16个CPU合同场景与独立集成评审。状态为 **CPU_BUILD_REVIEWED_FROZEN_GPU_NOT_RUN**。本轮GPU算子、模型、HTTP请求均为0；FP32逐bit、Graph数值和性能尚未验证。原服务保持停止。

通过`jssh 29`在`/home/hhtele/ninfer-v4-k1-20261023/source`操作，分支`codex/k1-correction-records-20261023`。工程基点`4d31af405fca9c70bd39a71257f83f4eeebbd0bc`，候选树`1f26afd245e2f6fca5d7e2bee34ec07839ef62bf`，HEAD仍为O `e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`。未创建提交、推送或部署。

## 实现与边界

profile为`SM89_GDN_CORRECTION_C1_W4_L48_RECORD_FOLD_V1`，固定C1/W4/L48、Hk16/Hv48/D128。新增typed FP32 normalized-key、delta、alpha记录及候选Fold。Record从既有transition实际计算点捕获值，Fold按原state更新表达式重放，conv记录继续保留。候选只写correction池，raw对照只写raw池；两池独立，没有双写或workspace alias。

共变更15个文件，其余1235个基点文件逐一匹配。[补丁](../output/ninfer-v4-k1-implementation-20261023/remote/evidence/K1-T01.patch)与[源码身份](../output/ninfer-v4-k1-implementation-20261023/remote/evidence/source-identity.json)可复核。raw接口和默认分派保留。共享helper改为同源行表达式与默认空capture；另将头文件内FP32非模板kernel改成内部链接以修复重复符号。算术表达式未改，但不同编译路径的FMA/寄存器分配仍可能影响逐bit结果，CPU不能证明数值一致。Engine、Program、采样器、权重、codec、SHA/ContentId、缓存格式及既有FP64参考文件未改。

驱动覆盖8种有效/提交前缀组合，含commit0/1/2/3/4与有限极值输入；48层初state/conv/conv记录采用不同种子，所有层比较raw/correction FP32 state、conv及BF16 readout逐bit。**独立FP64仅layer0**，复用原`gdn_ref.h`与原阈值，其余47层以raw逐bit对照；plan和summary明示该边界。Record先检查无效输出置零、未写suffix canary、权威state及输入保持，再污染拒绝后缀，检查Fold只发布允许前缀。

Graph每图预期48个Record＋1个all-layer Fold，运行时核对函数地址、节点类型和grid/block；预算先持久预留，每次算法入队检查截止。各批以相同初state重置，D2D reset位于event之外，batch内采用相同rolling recurrence，AB/BA交替。CUDA event覆盖主机投递间隙，不能称为纯kernel latency，也不覆盖投影、conv生产者、Attention/MLP、proposal/sampling或host许可。该切片不授予完整Verify、Target输出、取消/epoch/permit或整轮资格。

raw payload为7,151,616字节，correction为10,260,480字节；双池合计17,412,096字节，新增完整correction池。数值来自布局推导，不是GPU allocator高水位；没有省掉正式state读写，也没有模型加载后的显存余量证据。NInfer原本已有统一Fold，不能将其算作新增收益。

## 已执行验证

复用原BO镜像`sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`、C0增量构建与冻结OpenSSL依赖。Release、CUDA13.2、SM89、仅27B、4 worker；使用`runc`、无网络、无NVIDIA设备，准备和CPU native计划也在该容器内执行。

```sh
cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DOPENSSL_INCLUDE_DIR=/deps/include \
  -DOPENSSL_CRYPTO_LIBRARY=/usr/lib/x86_64-linux-gnu/libcrypto.so.3 \
  -DNINFER_BUILD_QWEN3_8_27B=ON -DNINFER_BUILD_QWEN3_6_35B_A3B=OFF
cmake --build /build -j 4 --target ninfer_gdn_correction_contract_test \
  ninfer_k1_gdn_correction_probe ninfer-serve
/build/tests/ninfer_gdn_correction_contract_test
cd /src/tests/k1
NINFER_K1_PROBE=/build/bench/ninfer_k1_gdn_correction_probe \
  python3 -B -m unittest -v test_controller
```

- 新C++合同8场景PASS：固定布局、规格拒绝、容量、重叠、类型/形状、对齐、层边界及唯一writer覆盖。
- 新Python合同8场景PASS：实际native CPU计划及预算、全零账本/哈希、篡改拒绝、非空账本拒绝、授权先于外部动作、截止/guardian、精确归属清理与原服务保护、首失败/未知终态保留。
- 合计16场景，仅执行一次。旧raw Record/Fold测试仅在首轮编译/链接，没有执行；未重跑旧Baseline或已通过任务。冻结准备另校验CPU plan与空账本，不创建runtime。

[完整原始日志](../output/ninfer-v4-k1-implementation-20261023/remote/evidence/)包含各轮stdout/stderr和实际命令回执。r1 kernel/serve构建通过；r2 probe链接失败；r3修复后构建通过，耗时20.282秒。16项CPU分别耗时0.415/0.516秒，均返回0。

两个独立代理分别只读评审数学/布局及驱动/控制器，未代跑测试。评审发现的V输入8字节对齐不足已修复，既有alignment场景精确验证拒绝。实际链接暴露头文件非模板CUDA强符号重复，已改内部链接并复审、重编通过。48层数据同值可能掩盖stride错误，已改不同种子。无剩余CPU冻结阻断。[评审记录](../output/ninfer-v4-k1-implementation-20261023/review.json)。

## 冻结与下一次最小实机范围

准备根：`/home/hhtele/ninfer-v4-k1-20261023/prepared-window-r1`。native二进制、控制器、plan、源码身份、服务快照与初始账本共7个输入只读冻结。当前ledger及transfer_used全0、reservations空，无runtime和owner锁，授权状态仍为`NOT_AUTHORIZED_PREPARATION_ONLY`。

| 产物 | SHA-256 |
|---|---|
| freeze-receipt.json | `4ebed5b3177d1ef7eecb1deae36f6f42f18bbac8297afa8aed8c2d736b825105` |
| native probe | `5978092c268e1cf19481dfada20df66b0d45e143fffe8e0de83e41edf0dde726` |
| 本机精简交付归档 | `f46a55e82803f71d35d054398d2c5ebdb69f94ec75db74be827a96d178efc6d7` |

[准备回执](../output/ninfer-v4-k1-implementation-20261023/remote/evidence/preparation-receipt.json)、[冻结输入](../output/ninfer-v4-k1-implementation-20261023/remote/prepared-window-r1/freeze-receipt.json)、[归档](../output/ninfer-v4-k1-implementation-20261023/compact-delivery.tar.gz)已在本机持久目录保存并核验。本机精简归档包含变更源码、补丁、BO/CPU日志、工具和native二进制；完整源树复用已核对的本机初始快照及最终补丁。远端完整归档位于`/home/hhtele/ninfer-v4-k1-20261023/cpu-delivery.tar.gz`，SHA为`85f5f2e8af8e6cd8de48e350f95912c6fff1374bf21570ee7c8b592d14224981`，额外包含冻结依赖和serve/CPU测试二进制。不含模型权重或BO镜像本体。

| 项目 | 后续冻结上限 |
|---|---:|
| 数值场景 | 8，raw/correction对照 |
| direct Op | 784＝8×2×49 |
| Graph capture | 6，commit1/2/4×两路线，每图49算法节点 |
| Graph replay | 276＝12 correctness＋24 warmup＋240 timing |
| 算法kernel执行 | 14,308＝784＋49×276 |
| 模型提交 / HTTP | 0 / 0 |
| 预计实际窗口 | 3–8分钟 |
| 清理 / 硬截止 | 第12分钟 / 15分钟 |

传输独立计账，包括初始化、guard、reset及导出；保守上限为H2D 847次/3,174,503,944字节，D2D 128次/19,704,905,728字节，D2H 896次/30,979,424,768字节。允许最多64次prepare与64次完整checkpoint、每端256字节guard；没有memset或helper compute。传输不冒充性能样本。

首筛只判断完整Record＋Fold算子段：FP32/BF16逐bit及原FP64阈值必须通过，五批配对中位改善≥10%且至少4/5批更快，才记`SEGMENT_SIGNAL_NOT_K4`。10%是门槛，**不是预期已测收益**；没有信号或数值失败即保留raw，不追加配置追成绩。原通用32wire/84native资格模板不属于本窗口，不能相加。

后续只需核对本冻结回执与空账本后单独授权该GPU首筛；无需再补CPU套件或旧Baseline。若有胜者，再另行定义K1-T02真实runtime许可/epoch/取消与整轮预算，预计追加1–2工程日，当前未授权、未冻结，不自动接续。

## 保留事项

[最终回读](../output/ninfer-v4-k1-implementation-20261023/remote/evidence/runtime-after.json)确认原GPU服务exited/PID0、GPU计算进程为空，原容器ID/镜像/参数SHA、cache dev/inode及C0原serve SHA均未变。默认分派、采样、context、Pi medium/32768未改。Baseline、18处G1差异、C1附件缺口、K2 CPU19原stdout缺口及全部历史失败保持原样。C0和K2继续关闭，不追加补测。

V4当前入口、任务注册表和预算已同步，修改前14份正文/manifest逐字节备份。文档检查通过：416份Markdown、19项任务、4门禁、76条断言，原始资料、链接、manifest及负例校验通过。首次检查发现依赖行混入CPU状态标记，已拆行修复，未改依赖或放宽校验。交付另核验15个源码、7个冻结输入及空账本哈希，均通过。[文档结果](../output/ninfer-v4-k1-implementation-20261023/document-validation-r2.json)和[交付校验](../output/ninfer-v4-k1-implementation-20261023/delivery-verification.json)均已保存。`p95=null`，`optimization_qualification=false`；本次不授予候选采用或生产发布资格。

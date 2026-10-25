# Q4 FFN SwiGLU 紧凑 shared 布局与五级预取：候选准备交付

已完成可构建补丁、8个新CPU合同、BO构建、独立集成评审，以及固定预算驱动和空账本冻结。状态为 `CPU_BO_REVIEW_READY_GPU_UNRUN`。**本轮未执行GPU、模型或HTTP推理；没有实际提速结论。** 随机MTP保持关闭，不再追加补测。

## 实现范围与身份

通过 `jssh 29`（`ssh -J jump 29`）在隔离分支 `codex/q4-swiglu-compact-t4-20261024` 实施，远端根为 `/home/hhtele/ninfer-v4-q4-compact-t4-20261024`。复用既有源码、BO镜像和构建资源；没有提交、推送或部署。

- 基点源码树：`b9d4bfb714d537e1b9a51d94d3716c9441035107`。
- 候选源码树：`ebc4158e3146b87d65ca68427377476045af4646`。
- HEAD仍为 `e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`；候选树是未提交的隔离索引快照，不能混称为新提交。
- 16个变更文件，范围为共享layout、bench候选/驱动、原FP64参考抽取和定向CPU/控制工具。其余基点文件按Git blob逐项核验。

`small_t_rowsplit_mma.h/.cuh` 增加默认false的紧凑布局参数；只允许Q4、SwiGLU、Tile8、4或5级、MinBlocks3显式实例化。原MMA、scale-FMA、phase归约、SiLU、BF16舍入及等待/同步顺序保持。每stage去掉未被Q4消费的1024字节Q5 high区。

bench-only launcher另行限制实际T4、`34816×5120 → 17408×4`、连续BF16输入/输出、Q4 RowSplit/FP16 group64和split-K1。比较原四级、紧凑四级、紧凑五级。产品launcher、默认分派、Q5/Mixed、其他shape、Engine/MTP及采样均不接入新候选。**以后完整链接入仍须已有 `TextPhase::Verify` 与精确shape共同限界，不能用T4推断阶段。**

复用原 `q4_linear_swiglu_variants_bench` 的显式新入口，未新建控制器框架；原large-T默认流程保留，冻结控制器只调用 `--compact-t4`。从原Op测试抽取同一份独立FP64逻辑参考，原数学和A16容差未改；不复制kernel的中间舍入作为参考。

[完整补丁](../output/ninfer-v4-q4-compact-t4-20261024/remote/evidence/Q4-compact.patch) · [源码身份](../output/ninfer-v4-q4-compact-t4-20261024/remote/evidence/source-identity.json) · [独立评审](../output/ninfer-v4-q4-compact-t4-20261024/REVIEW.md)。

## 已执行验证

BO镜像为 `sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`。Release/SM89/27B，最多4个构建worker；Docker使用runc、无网络、`NVIDIA_VISIBLE_DEVICES=void`，并断言不存在 `/dev/nvidia0` 与 `/dev/nvidiactl`。随机MTP等诊断选项显式关闭。

执行并通过：

```sh
cmake --build /build --parallel 4 --target ninfer_ops
cmake --build /build --parallel 4 --target ninfer_q4_compact_contract_test
/build/tests/ninfer_q4_compact_contract_test
python3 -B -m unittest discover -s /src/tests/q4_compact -p test_controller.py -v
cmake --build /build --parallel 4 --target ninfer_q4_linear_swiglu_variants_bench ninfer_linear_swiglu_q4_a16_test ninfer-serve
```

4个C++场景覆盖原layout、紧凑plane对齐/边界、精确shape/profile及split-K资源；4个Python场景覆盖冻结身份、已消费/未知窗口禁止重试、资源合同、owner/deadline和仅候选清理。总计8/8，一次运行；没有重跑旧Baseline或已通过测试。原测试目标仅重新编译，以验证参考抽取的消费关系。

静态解析新二进制，无CUDA执行：

| profile | stages | shared/CTA | registers | stack / local |
|---|---:|---:|---:|---:|
| original4 | 4 | 29,696 B | 78 | 0 / 0 |
| compact4 | 4 | 25,600 B | 78 | 0 / 0 |
| compact5 | 5 | 32,000 B | 78 | 0 / 0 |

五级候选未增加编译寄存器或local spill。这不是占用率或吞吐提升证据。真实数值逐bit、Graph运行与收益尚未测试。

[CPU原始日志](../output/ninfer-v4-q4-compact-t4-20261024/remote/evidence/CPU-r1.log) · [BO构建回执](../output/ninfer-v4-q4-compact-t4-20261024/remote/evidence/BO-prober1.json) · [编译资源](../output/ninfer-v4-q4-compact-t4-20261024/remote/evidence/binary-resources.json)。

## 冻结的最小实机范围

冻结入口：`/home/hhtele/ninfer-v4-q4-compact-t4-20261024/prepared-window-r1`。账本 `PRISTINE`、所有used为0、无runtime。冻结SHA：

`55834651b95939debf2c1e29200460f489a9e96dc66d31a5339d9eadfbf4c717`

| 项目 | 固定执行或上限 |
|---|---:|
| 新输入场景 / 配置 | 4 / 3 |
| direct Op | 12 |
| capture / captured kernel nodes | 3 / 3 |
| replay | 126：每图4 correctness＋6 warmup＋32 timing |
| 算法kernel执行 | 138；每次544 CTA，共75,072 CTA |
| helper compute / 模型提交 / HTTP wire | 0 / 0 / 0 |
| H2D | 计划10次/98,386,944 B；上限40次/128 MiB |
| D2H | 计划13次/4,148,224 B；上限24次/4 MiB |
| D2D | 0 |
| cold-flush memset | 计划138次/37,044,092,928 B；上限144次/36 GiB |
| 显式device buffers | 363,596,800 B；上限384 MiB |

相较准备稿，驱动采用一块带guard的共享输入/三输出arena，减少传输次数，并增加计时后的完整arena检查及权重边界guard读回。旧准备稿的363,315,712 B是单输出布局估值；现按实际三输出布局纠正，预算上限不变。完整权重不额外D2H；权重只读参数和源代码静态检查，加末尾guard验证。CUDA context/Graph内部allocator高水位不可由显式buffer计账代替，保持null。

每次CUDA操作先持久预留资源，未知结果保持未完成，不自动重发。Graph检查一kernel节点、函数身份、全部输入/输出参数、grid/block/shared及资源；函数地址由同一launch TU取得，避免复现旧K1跨TU地址问题。输出全量对比原路径逐bit和既有FP64/A16标准，不能放宽断言。32组计时交错轮换三种配置；每次计时前冷flush，flush在CUDA事件区间外，但仍计入全窗口资源。

预计GPU窗口2–5分钟，硬上限10分钟、第7分钟开始清理。控制器复用原GPU锁和owner/guardian机制，只清理本候选；原服务保持停止。实机需要后续执行指令，本轮未使用该额度。

```sh
python3 /home/hhtele/ninfer-v4-q4-compact-t4-20261024/prepared-window-r1/tools/controller.py \
  --root /home/hhtele/ninfer-v4-q4-compact-t4-20261024/prepared-window-r1 \
  --run --authorize-new-gpu-run \
  --freeze-sha 55834651b95939debf2c1e29200460f489a9e96dc66d31a5339d9eadfbf4c717
```

[冻结回执](../output/ninfer-v4-q4-compact-t4-20261024/remote/prepared-window-r1/freeze-receipt.json) · [可执行预算](../output/ninfer-v4-q4-compact-t4-20261024/remote/prepared-window-r1/plan.json) · [空账本](../output/ninfer-v4-q4-compact-t4-20261024/remote/prepared-window-r1/budget-ledger.json)。

## 采用边界与后续

只有数值/guard/Graph全部通过，并且局部中位耗时下降至少10%、每Op至少节省12μs、32组中至少24组改善，才形成下一步完整decode验证信号。没有信号即收尾，不增加参数扫测或模型请求。上述是首筛阈值，不是生产资格或收益承诺。

若胜出，后续真实Verify接入与完整链驱动预计另需4–8工程小时，再独立冻结资源；前轮提出的4 native/≤16 decode、4 Chat＋2warmup/8wire仅为后续提案，本轮没有授权或执行。局部收益不能直接换算Chat收益。

2026-10-24 19:38（北京时间）收尾核对：原 `ninfer-4090-prod` 停止、PID0、镜像/启动参数/缓存目录身份不变，GPU无compute进程。未改默认分派、Target采样、Pi medium/32768或缓存格式；全部历史失败、18处G1差异、C1附件缺口保留。`actual_performance_gain=null`、`p95=null`、`optimization_qualification=false`。

[交付归档回执](../output/ninfer-v4-q4-compact-t4-20261024/delivery-r1.json) · [机器结果](../output/ninfer-v4-q4-compact-t4-20261024/remote/evidence/freeze-summary.json)。

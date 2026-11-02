# DF01 / D1L · 首个Q8偏离算子定位与CPU修复

日期：2026-11-02。连接：`ssh 29`。本轮授权：原首组夹具逐层前向采集，最多一个GPU程序、一组夹具、零次生成，60分钟内收口；不自动重跑、不进入D2，生产保持停机。用户随后明确要求Astra xhigh帮助排查和review，该复核纳入同一时间窗口。

**已完成：首个导致Q8码变化的CPU算子缺陷已定位、修复并通过CPU验证。完整D1仍未通过。** 问题在CPU参考的tap激活量化，不在本例已验证的原生GEMM计算。`127 / tensor`实际执行先倒数再乘127，发生两次FP32舍入；原生量化使用一次除法。位置22、特征1928因此从GPU的59偏为CPU的60。

Astra独立确认该反例及其FC输出因果效应，并接受最小修复。修正后首项概率误差由0.0529407859降为0.0049186349，token匹配由2/7变为5/7；最大概率误差仍为0.0718193054，完整夹具门继续失败。不能将首个缺陷修复写成整个前向问题解决。

## 1. 本轮执行与采集

| 项目 | 实际 |
|---|---|
| GPU程序 / GPU夹具 / 目标引擎生成 | 1 / 1 / 0 |
| GPU重跑、替补、D2 | 0 / 0 / 未开始 |
| 原夹具 | `drafter-n32-seed1.bin`，SHA与D0B冻结值一致 |
| GPU开始/结束，北京时间 | 15:02:55.535 / 15:02:56.143 |
| 逐层记录 | 323项，58129664bytes |
| 采集额外预算 | 固定128MiB诊断slab，实际记录约55.4MiB |
| CPU完整reference forward | 2次：原冻结路径记录1次，最小除法修复验证1次 |
| Astra | gpt-6-astra / xhigh，独立只读检查及8次局部CPU数值分析；GPU0 |

任务起点14:48:36，截止15:48:36。15:19:46现场与数值回执封存；报告包在该回执后完成，无继续负载。单GPU进程0.608秒监督墙钟含轮询等待，不是性能指标。

`run_once.py`的独占GPU标记保持，程序没有第二次启动。新binary SHA为`39891a816026ebe255a1d8e3b8885a1c8cbc4c4608f0b041cb86d43a3a446575`。原夹具SHA仍为`2f07802c933a9538dfd7ebf34e88a0b45a40766b29a3998227cd3f6990b6bec1`，Q8 pack SHA仍为`c7d83c0cdfeadc7c692a1587795adb0181cfd94dacd96ac1a91f71ea7ecc62ed`。

采集在独立core副本增加只读D2D快照，使用原producer stream，在缓冲复用之前保存；不删除原graph/fork/event依赖，不修改计算kernel。图外在原draft同步完成后统一读回。覆盖：

- context五段8/8/8/7/1的有效位置、FC实际tiled权重、每次GEMM实际Q/D和输出。
- context/block RoPE表、合法K/V ring行、block32个运行时metadata。
- 五层Q/K/V、RoPE结果、attention全部17个chunk的partial、输出量化输入。
- finish后的残差与norm、gate/up/down、最终行与selector尾部。

Astra建议的attention partial、RoPE及metadata均在唯一一次GPU启动前补齐。没有采未写的`hctx_`；context hidden_norm只有实际Q/D可见，不冒称获得了不存在的float输出。

新采集的final rows/token/probability原件及tail原件，与[D1R](DF01-D1R-SINGLE-FIXTURE-20261102.md)逐byte完全相同。对应SHA仍为`d52534d03147ad17f5c2385941afa2738539ffc4f8d0a819ad1a1a85c812da7f`、`3744531429d0c6fb7b8ccd2f0d677d78c44ca99c8d47e066d71f9abd4b729b1c`。本例没有观察到采集改变计算结果。

原资格exit1保留，仍为：

```text
selector probability 0: reason=absolute_difference actual=0.787050843 expected=0.734110057 abs_diff=0.0529407859 limit=0.0500000007
```

## 2. 首个偏离的因果证据

GPU context第3段为位置16..23。原输入位置22、特征1928落在32元素块60。原始输入和块最大值相同，scale也逐bit相同，差别仅在inverse计算：

| 数值 | 原CPU参考 | 真除修正 / GPU |
|---|---:|---:|
| 输入值 | 0.7580226063728333 | 相同 |
| amax | 1.617964267730713 | 相同 |
| inverse | 78.49370574951172 | 78.49369812011719 |
| 舍入前乘积 | 59.500003814697266 | 59.499996185302734 |
| Q8码 | 60 | 59 |

实际Torch dispatch负/正对照：

```text
127 / maximum          -> aten.reciprocal.default -> aten.mul.Tensor
torch.div(127.,maximum) -> aten.div.Tensor
```

该Q码多1的差量，乘实际scale与`fc.weight[:,1928]`，预测FC输出最大偏差0.0083631193；实际最大偏差0.0083665848。扣除预测差后，最大残差仅1.9983621e-05、RMS5.1934635e-06，与其他FC行的普通FP32累计差同量级。该证据将首个量化错误和后续非微小FC偏差闭合，不是把首个浮点低位差直接当作bug。

同GPU Q/D输入下，按原生“16元素整数点积→scale乘积→FMA→32 lane XOR归约”在CPU重放，**101/101个GEMM输出逐bit一致**。FC实际tiled权重与冻结pack逐byte一致。本例未发现原生GEMM或FC资产转换缺陷。

原冻结CPU完整前向仍精确复现旧gold行，证明不是夹具文件漂移。问题是CPU参考对原生量化算术的实现不一致。

### 更正早期NumPy代理判断

初次逐stage摘要用NumPy真除重算Q码，未复现Torch的反除行为，错误地把首次码差放在context hidden_norm之后的19码。Astra发现并纠正该遗漏。原`FROZEN_STAGE_COMPARISON.json`及NPY保留，`NUMPY_PROXY_CORRECTION.json`明确标记更正；`QUANTIZER_ROOT_CAUSE.json`用实际Torch计算证明更早的tap量化1码差。

该更正不影响101项原生GEMM逐bit比较，也不影响原冻结forward复现和GPU原件一致性结论。

## 3. 最小修复与CPU验证

修复位于新目录`cpu_reference.py`：planar inverse从Python scalar反除改为`torch.div(127.0, safe)`。保持zero处理、RN-even、`d=maximum/127`、head round-away与FP16 scale路径。原`maximum/127`本来就与GPU的12800个FC scale逐bit相同，不修改。

新Q8 hook明确调用修复后的activation，覆盖`mm/matmul`。本次完整CPU验证的唯一算术差量是inverse真除；保持原CPU卷积与GEMM路径，避免与先前卷积/GEMM/RoPE候选混合归因。没有改生产或原D0B/D1C/D1R文件，没有改冻结gold或容差。

`test_cpu_reference.py -v`实际5项通过：

1. 原冻结真实正值反例与镜像负值：旧60/-60，修正59/-59。
2. 全零块保持q0/scale0且finite。
3. 原RN-even边界和head路径保持。
4. 两种grad模式、两种matrix API均确实调用新量化。
5. 五段FC输入的409600个Q8码和12800个scale与GPU逐bit一致。

完整CPU修正结果与本轮GPU原件比较：

| 指标 | 原CPU参考 | 仅inverse修正 |
|---|---:|---:|
| 首项概率误差 | 0.0529407859 | 0.0049186349 |
| token匹配 | 2/7 | 5/7 |
| 全行对GPU RMS差 | 0.1463699399 | 0.1214103057 |
| 最大概率误差 | 不通过 | 0.0718193054，仍超过0.05 |

修正后token为`[116188,246916,30225,82220,57612,188546,183640]`，GPU为`[116188,246916,227130,179274,57612,188546,183640]`。剩余两项token差异和最大概率差继续阻塞完整夹具，未改成PASS。

### Astra独立复核

Astra审查采集前stream/graph/ring边界，未发现阻断。采集后独立核对RMS、RoPE、K/V、attention、反除dispatch和FC局部因果。复核接受首个CPU缺陷的定位和最小修复，确认完整D1仍不满足门。

Astra执行8次局部CPU数值分析，没有执行GPU、完整reference forward或修改文件。101项GEMM、两次完整CPU前向及5项测试由root执行。Astra读取测试结果，未冒称重跑。复核记录在`ASTRA_REVIEW.md`。

同输入分析还确认：分块attention的partial还原与其Q/D逐bit一致；一个后续量化阈值案例展示微小浮点差可放大。该案例不当作首因或本轮已修复项。实际native构建没有`--use_fast_math`，不使用该选项解释本轮差异。

## 4. 原件、生产与检查

15:19:46复核生产inactive/dead、MainPID0、NRestarts0，无GPU计算进程、无实验PID，18343/18089无监听。13项生产保护SHA及334项历史/源文件SHA匹配。本轮服务stop/start均0，继续保持停机，恢复等待用户明确要求。

原D0、D0B、D1、D1C、D1R报告和失败原件保持。新目录：`/home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1l-20261102/`，本地镜像为`workspace/dflash2/df01-d1l-20261102/`。原件Git忽略，不加入公开报告包。采集和CPU构建只使用该独立目录，原生产、CUDA、驱动、NGINX、Pi、PT0及缓存预算未改。

297个导出原件，共71368104bytes，归档56081422bytes；逐文件bytes/SHA验证一致。归档SHA256：

`3ddbe0459560387c57166956a761295904d1d1d63f07795d776c71a63e2ab233`

关键证据：`STAGES.json/bin`、`QUANTIZER_ROOT_CAUSE.json`、`GEMM_ANALYSIS.json`、`NUMPY_PROXY_CORRECTION.json`、`CPU_TEST.stderr`、`DIVISION_FIX_FORWARD.json`、`ASTRA_REVIEW.md`、`RESULT.json`和`FINAL_READBACK.json`。原错误摘要、执行版CPU脚本及元数据纠正前版本保留。

主要实际命令：

```bash
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1l-20261102/prepare.py'
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1l-20261102/run_once.py'
ssh 29 '/home/hhtele/strata-0.1.43.1/.venv/bin/python -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1l-20261102/analyze_gemm.py'
ssh 29 '/home/hhtele/strata-0.1.43.1/.venv/bin/python -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1l-20261102/test_cpu_reference.py -v'
ssh 29 '/home/hhtele/strata-0.1.43.1/.venv/bin/python -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1l-20261102/validate_fix_forward.py'
ssh 29 '/home/hhtele/strata-0.1.43.1/.venv/bin/python -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1l-20261102/confirm_root.py'
```

以上是已执行记录，不能用作自动续跑清单。GPU独占attempt标记保留。CPU脚本的继承注释/结果元数据经Astra指出后单独更正，执行版和原元数据归档；没有重算或改数值。包验证另记`PACKAGE_CHECKS.json`。apps/packages未改，未运行pnpm应用五项检查。没有commit或push。

## 5. 当前停止点

首个导致离散Q8码变化的CPU参考缺陷已定位修复，任务在本轮预算内收口。原唯一GPU程序仍为FAIL，修复后的参考与其保存原件的完整比较也仍FAIL。D1保持`BLOCKED_NUMERICAL_ORACLE`，不进入D2，不升级生产。

后续若继续，现有323项逐层原件足够优先进行纯CPU核对剩余差异，不必再为同一尾部或前向数据追加GPU采集。本轮不自动开始新阶段。原六FAIL、P05及关闭方向保持，生产继续停机。

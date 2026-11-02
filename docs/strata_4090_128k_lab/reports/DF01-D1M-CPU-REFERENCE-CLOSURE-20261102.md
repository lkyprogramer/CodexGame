# DF01 / D1M · 单夹具CPU参考修复与离线数值门收口

日期：2026-11-02。连接：`ssh 29`。用户授权：基于现有逐层原件排查剩余两项token和概率差异，派发Astra xhigh协助定位、修复及CPU验证；60分钟内收口，不追加GPU，不进入D2，生产保持停机。

**已完成：剩余两项token差异消除，原首组n32的离线比较满足原数值门。完整D1仍未完成。** 独立CPU参考采用来源一致的卷积和planar Q8 GEMM算术顺序后，七项token全部匹配，最大概率差为0.0451067686，低于原0.05门限。概率仍有非零差异，行数据不逐bit相同。

原C++比较器以保存的GPU观察值为actual、新CPU参考为expected，实际执行通过。错误token、概率超限及非有限行三个负例均按预期拒绝。没有修改原比较器、容差或冻结gold。原D1/D1R/D1L的FAIL保持历史结果，不能倒写成PASS。

## 1. 范围与执行量

| 项目 | 实际 |
|---|---|
| 输入 | D0B原`drafter-n32-seed1.bin`及固定Q8 pack |
| GPU观察值 | D1L保存的原首组，与D1R逐byte相同 |
| 逐层诊断依据 | D1L的323项记录；不重新采集 |
| 新GPU程序 / GPU夹具 / 目标生成 | 0 / 0 / 0 |
| root完整CPU参考前向 | 2次；两个预设算术组合 |
| 回执恢复 | 1次CPU head/selector重算；不重跑backbone |
| Astra | `gpt-6-astra` / `xhigh`，独立定位与review |
| Astra attention检查 | 1次CPU编译、1次五层局部检查；完整前向0次 |
| D2 / 服务start / 服务stop | 0 / 0 / 0 |

任务起点为北京时间15:29:58，截止16:29:58。数值及现场回执于15:46:03封存。其后只整理报告、同步原件和检查报告包，不增加模型前向或算子试验。

CPU前向使用CPU-only Torch，并设置`CUDA_VISIBLE_DEVICES=''`。本轮没有启动CUDA程序、CLI生成、HTTP推理或生产引擎。

## 2. 原因与修复边界

[D1L](DF01-D1L-LAYER-ROOT-CAUSE-20261102.md)已证实planar量化的反除双舍入缺陷。最小真除修复后，token由2/7改善为5/7，但最大概率差仍为0.0718193054。本轮沿用该真除修复，不重新寻找量化比例或调整门限。

剩余差异来自CPU参考与原生实现的算术路径不一致。原CPU路径先把Q8权重和激活还原为浮点，再调用Torch矩阵乘法。原生路径则先执行整数点积，再按固定次序应用scale和归约。这两条路径在实数公式上接近，但FP32舍入顺序不同。后续Q8阈值会放大低位差异。

本轮在独立目录`run_reference.py`组合两项有源码依据的路径：

1. 使用D1R已验证的卷积顺序：先加base与dynamic权重，再逐tap FMA。
2. drafter planar Q8 GEMM及selector hidden projection使用D1L的CPU整数参考：实际int8权重与FP16 scale、16元素整数点积、FP32 scale乘积、FMA、32-lane XOR归约。

D1L已有101/101个同输入GEMM输出逐bit相同的证据。本轮完整前向使用CPU自己生成的激活，不把保存的GPU Q/D、attention输出或最终行注入前向。GPU原件只用于比较。

head保持既有Q8_1量化加Torch矩阵乘法。不能将本轮变更描述为“所有矩阵路径逐bit原生化”。生产引擎、CUDA kernel和旧参考文件均未修改。新实现是独立CPU参考版本，不覆盖原冻结gold，也不自动替换其他三组参考。

## 3. 正负结果与原门验证

| 参考组合 | token一致 | 最大概率差 | 行RMS差 | 结论 |
|---|---:|---:|---:|---|
| D1L仅真除修复，历史结果 | 5/7 | 0.0718193054 | 0.1214103057 | FAIL |
| 真除＋原生顺序卷积 | 2/7 | 0.3481473923 | 0.1230598167 | FAIL，保留 |
| 真除＋原生顺序卷积＋planar整数GEMM | 7/7 | 0.0451067686 | 0.03107449785 | 单夹具离线原门PASS |

卷积单项组合没有满足门。结果不支持将卷积单项修复当作完整解决。组合修复通过后，停止继续试验attention接入或追逐逐bit一致。

最终七项token均为：

```text
[116188, 246916, 227130, 179274, 57612, 188546, 183640]
```

| 索引 | 保存的GPU概率 | 修正CPU概率 | 绝对差 |
|---|---:|---:|---:|
| 0 | 0.7870508432 | 0.7933388352 | 0.0062879920 |
| 1 | 0.9543380141 | 0.9535885453 | 0.0007494688 |
| 2 | 0.5275137424 | 0.5472844839 | 0.0197707415 |
| 3 | 0.4438980222 | 0.4388814867 | 0.0050165355 |
| 4 | 0.8930861354 | 0.8768584728 | 0.0162276626 |
| 5 | 0.7387927771 | 0.7145448327 | 0.0242479444 |
| 6 | 0.5695143342 | 0.6146211028 | 0.0451067686 |

原比较器的行指标：最小cosine为0.9999158319，原下限0.98；GPU/CPU norm ratio为0.9997055923–1.0003623303，原范围0.95–1.05；所有行有限。`compare_saved.cpp`直接include未改动的D0B `qualification_compare.hpp`，仅用CPU编译和执行，不链接CUDA。

实际输出：

```text
PASS
REJECT selector token 2
REJECT selector probability 4
REJECT nonfinite row
ORIGINAL_COMPARATOR_PASS 4 checks; single saved fixture only; no CUDA
```

### 保留的失败与非逐bit边界

第一个CPU组合完成前向并保存rows后，JSON写入因NumPy整数不可序列化而失败。原执行版`run_reference_BEFORE_JSONFIX.py`及`SERIALIZATION_ATTEMPT1.json`保留。修正仅在JSON边界转为Python `int`。该组合的回执从已保存rows重算head/selector恢复，没有重跑backbone或补样本。

通过组合仍有逐bit差异：首次Q码差出现在`block.L1/gemm/layers.1.self_attn.o_proj.weight`，一个码不同。此结果满足原最终数值门，不能外推所有中间值一致。

## 4. Astra xhigh独立复核

Astra按冻结CUDA对象PTX实现CPU attention局部重放：预缩放Q、四元素乘/FMA、32-key在线softmax、partial归约及逐key PV FMA。五层partial最大score逐bit一致，行RMS差比Torch局部基线降低约5–11倍。四层量化码完全相同；L2仍有一个量化码不同，坐标从旧Torch边界转移到新边界。

该局部结果保留为负结果，未接入完整前向。CPU `exp2f`与GPU `ex2.approx`不宣称逐bit相同。没有拟合或替换GPU超越函数结果。SwiGLU三种公式在五层的下游Q码与scale均一致，该检查不证明未量化浮点值一致。

Astra检查整数GEMM的输入独立性和算术顺序，未发现阻断问题。Astra独立读取最终rows并复算原行指标，接受“单保存夹具满足原离线数值门”的结论。完整前向和原C++比较器由root执行；Astra没有重复执行这些程序。复核全文在`astra-attention/REVIEW.md`。

## 5. 原件、生产与复现

新远端目录：`/home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1m-cpu-20261102/`。本地镜像：`workspace/dflash2/df01-d1m-cpu-20261102/`。

主要证据为`AUTHORIZATION.json`、`DEPENDENCIES.json`、两组结果JSON/rows/NPY、`ORIGINAL_GATE_CHECK.json`、`RESULT.json`、`FINAL_READBACK.json`及Astra局部实现和review。原件目录继续Git忽略，不加入公开报告包。导出包含CPU源码和结果，不包含模型权重、旧GPU逐层二进制或编译库；依赖来源及SHA另记在`DEPENDENCIES.json`。

277个导出文件，共22086287bytes；归档20066570bytes。本地逐文件bytes/SHA校验通过，见`EXPORT_CHECKS.json`。归档SHA256：

`228a58521740d6c548d7e065779b76e08c6b5edeb2a7d29a97e3e970a57844ac`

| 原件 | SHA256 |
|---|---|
| 未改动GPU观察值 | `d52534d03147ad17f5c2385941afa2738539ffc4f8d0a819ad1a1a85c812da7f` |
| 新CPU rows | `d9f7b82ac9f481acbb97ff0e7b0fac9fb5f4257b1356929109cf23f8bef1ab58` |
| 新CPU参考binary | `a430e21b562f4562fdd05771853dba03a9458fdeb0f2fc4da20c3381d72f3fe2` |

15:46:03现场复核为`inactive/dead`、`MainPID=0`、`NRestarts=0`，无GPU计算进程，18343/18089无监听。633项历史/源文件及13项生产保护SHA一致。本轮没有服务启停，继续保持停机。恢复等待用户明确要求。

主要实际命令：

```bash
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1m-cpu-20261102/prepare.py'
ssh 29 '/home/hhtele/strata-0.1.43.1/.venv/bin/python -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1m-cpu-20261102/run_reference.py --label division_conv'
ssh 29 '/home/hhtele/strata-0.1.43.1/.venv/bin/python -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1m-cpu-20261102/recover_conv_receipt.py'
ssh 29 '/home/hhtele/strata-0.1.43.1/.venv/bin/python -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1m-cpu-20261102/run_reference.py --label division_conv_gemm --native-gemm'
ssh 29 '/home/hhtele/strata-0.1.43.1/.venv/bin/python -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1m-cpu-20261102/check_saved.py'
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1m-cpu-20261102/finalize.py'
```

以上为已执行记录，不是自动续跑清单。C++编译与执行的精确argv记录在`ORIGINAL_GATE_CHECK.json`；Astra命令记录在`astra-attention/CPU_EXECUTION.json`。报告包检查另记`PACKAGE_CHECKS.json`。apps/packages未修改，未运行pnpm应用五项检查。没有commit或push。

## 6. 当前停止点

本轮CPU修复与原首组离线验证已完成。原首组在修正CPU参考下的数值阻断得到闭合；完整D1仍未完成。其他资格夹具、target-state及六次真实生成均未运行，性能、质量和服务生命周期均未验证。不能据此进入D2、升级生产或宣称DFlash2有收益。

后续若获新授权，下一项是先冻结新CPU参考版本与夹具身份，再制定剩余D1资格范围。不得覆盖旧gold、补改原FAIL或沿旧GPU额度继续执行。本轮在报告包检查后停止，不再追逐attention逐bit一致。原六FAIL、P05及关闭方向保持，生产继续停机。

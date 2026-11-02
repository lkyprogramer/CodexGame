# DF01 / D1R · 单夹具复现，差异定位到drafter前向

日期：2026-11-02。连接：`ssh 29`。用户授权：仅原失败首组，最多一个GPU程序、一组夹具、零次生成，60分钟内收口；不自动重跑、不进入D2，保留原失败，生产继续停机。

**最小复测与CPU修复已完成；原资格仍失败。** 实际执行1个GPU程序、1组原`drafter-n32-seed1`，目标引擎CLI/HTTP生成0、GPU重试0。采集到GPU实际概率、final rows以及定位用尾部中间量。

**首项概率差由selector之前的drafter行差传播而来。首个发生偏离的前向算子仍未确认。** 使用同一GPU行数据在CPU重算，7项token全部匹配，概率最大差`6.556510925292969e-07`；使用GPU实际head/selector projection核查，最大差仅`1.7881393432617188e-07`。这闭合了尾部定位，但不能据此宣布整个drafter正确。

修复了可确认的CPU参考算术顺序差异与本轮CPU分析适配器的漏量化问题。修复没有消除完整前向差异。原[D1](DF01-D1-QUALIFICATION-20261102.md)和[D1C](DF01-D1C-CPU-ORACLE-AUDIT-20261102.md)记录保持；D1继续`BLOCKED_NUMERICAL_ORACLE`，不进入D2。

## 1. 单次GPU执行

| 项目 | 上限 | 实际 |
|---|---:|---:|
| GPU程序 | 1 | 1 |
| GPU夹具 | 1 | 1，原首组失败 |
| 目标引擎CLI/HTTP生成 | 0 | 0 |
| GPU重跑/替补 | 0 | 0 |
| D2 | 未授权 | 未开始 |

任务起点为北京时间14:12:48，截止15:12:48。GPU程序于14:17:50.182启动，14:17:50.793结束。监督墙钟0.611秒包含0.5秒轮询等待，不是GPU执行耗时或性能指标。14:33:07最终现场复核完成，报告包在该回执后收口，没有继续负载。

原夹具是32行synthetic taps、seed1、256项合成head词表，不是真实Pi生成或128K性能样本。固定夹具SHA：

`2f07802c933a9538dfd7ebf34e88a0b45a40766b29a3998227cd3f6990b6bec1`

Q8 pack保持D0冻结SHA：

`c7d83c0cdfeadc7c692a1587795adb0181cfd94dacd96ac1a91f71ea7ecc62ed`

原D1C资格程序默认包含7组，不能直接整程序执行。本轮另建`drafter_single`，入口只接受pack与一个fixture，校验n=32/vp=256，只调用一次`run_case`，不包含独立selector三个case或后续长夹具循环。实际binary SHA：

`c50f9152e1c30e78bfa9532b9b2ba450f0bdf0f2d33d62ab2c0e5cc89e63d3bc`

复用原静态库和原计算路径，未改计算内核、图内计算、类字段、pack或比较门。只在实验目录的header副本增加inline尾部读回，在`draft()`完成后保存现有设备缓冲。额外读回只供诊断，不进入性能数据。

运行器持原GPU锁。独占创建`GPU_ATTEMPT.json`后才启动唯一子进程；已有标记时不得再次执行。超时、85°C、MemAvailable4096MiB及外来GPU进程停止门保持。清理只针对PID/starttime/exe匹配的本次进程，不调用生产start。

## 2. 实际失败与原始数据

原比较器的finite、[0,1]、绝对概率差≤0.05门保持。原始stderr：

```text
DF01 qualification FAIL: /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d0b-20261102/fixtures-q8act/drafter-n32-seed1.bin: selector probability 0: reason=absolute_difference actual=0.787050843 expected=0.734110057 abs_diff=0.0529407859 limit=0.0500000007
```

程序exit 1。没有重跑。`0`为提案索引，不是实际概率值。

| 提案索引 | GPU token | 冻结参考token | GPU概率 | 冻结参考概率 |
|---:|---:|---:|---:|---:|
| 0 | 116188 | 116188 | 0.787050843 | 0.734110057 |
| 1 | 246916 | 246916 | 0.954338014 | 0.965135455 |
| 2 | 227130 | 30225 | 0.527513742 | 0.656190217 |
| 3 | 179274 | 113131 | 0.443898022 | 0.375249475 |
| 4 | 57612 | 165645 | 0.893086135 | 0.615895152 |
| 5 | 188546 | 223618 | 0.738792777 | 0.592359424 |
| 6 | 183640 | 93902 | 0.569514334 | 0.845287025 |

首个硬门在第0项概率停止；后五项token差异来自对同一次readback数组的CPU诊断，未启动额外夹具或生成。整组只有2/7 token与冻结参考相同，不能只看首项概率接近门限。

实际保存：

- `drafter-n32-seed1.df01-observed.bin`：81992bytes，8×2560 final rows、7个token、7个实际概率。SHA256 `d52534d03147ad17f5c2385941afa2738539ffc4f8d0a819ad1a1a85c812da7f`。
- `drafter-n32-seed1.tail.bin`：55580bytes，实际head logits、top16值/候选、selector projection、head Q8_1与planar Q8激活/scale。SHA256 `3744531429d0c6fb7b8ccd2f0d677d78c44ca99c8d47e066d71f9abd4b729b1c`。

## 3. CPU定位

只读取上述GPU原件及原冻结pack/夹具。没有再次启动GPU。

| 定位检查 | 实际结果 |
|---|---|
| GPU final rows的finite、cosine/norm门 | 满足原门，最小cosine0.9985218319 |
| GPU行与冻结行的RMS差 | 0.1463699399；最大绝对差1.1837377548 |
| 由GPU行计算Q8_1/planar量化值 | 与实际readback的反量化数值完全相同 |
| 由GPU行计算head logits | 最大绝对差7.62939453125e-06 |
| 由GPU行计算selector projection | 最大绝对差3.5762786865234375e-06 |
| 用GPU logits重做top16 | 112个候选ID和对应分值逐项完全一致 |
| 用GPU head/projection重做selector | 7/7 token一致，概率最大差1.7881393432617188e-07 |
| 从GPU final rows重做完整尾部 | 7/7 token一致，概率最大差6.556510925292969e-07 |
| 原no_grad CPU完整前向 | 精确复现原冻结行与概率，差0 |

第0项在换用GPU实际行后，概率误差从0.0529407859降至5.364418029785156e-07。

因此，第0项0.0529407859的概率差可由前向行数据不同解释，不是同一输入行下出现的selector概率公式失配。首个门的行cosine检查较宽，不能保证后续离散top16/前驱链与概率都一致。后续提案还会受前一项token变化影响。

当前没有分层GPU前向输出，因此不能唯一指出第一个偏离的算子，不能将整个差异归因于某个CUDA内核错误，也不能将其全部归为无害舍入。该限制继续阻塞D1资格。

## 4. 可确认的CPU修复及验证

### 4.1 卷积算术顺序

原Torch reference把每个tap的base乘积和dynamic乘积分开相加。原生源码先把两项kernel相加，再使用`fmaf`累加。两式的实数代数相同，FP32执行顺序不同。

新`native_conv.cpp`与`reference_ops.py`按原生顺序计算。96个CPU标量位置与独立标量reference逐bit一致；旧展开顺序存在不同结果。没有修改GPU内核。

同一冻结n32输入的CPU比较保留：

| 参考版本 | 第0项概率 | 全行对GPU的RMS差 | 与GPU token一致数 |
|---|---:|---:|---:|
| 原冻结参考 | 0.734110057 | 0.146369940 | 2/7 |
| 仅改原生卷积顺序 | 0.769582212 | 0.148316007 | 2/7 |

**修正没有消除完整差异，RMS还略增。** 不用首项概率更接近GPU宣称整个参考修复成功。该实现作为源算术一致的CPU诊断修复保留，不替换冻结金标，不改原D1失败结论。

### 4.2 inference_mode下漏量化

本轮第一次CPU前向分析使用`torch.inference_mode()`，触发`CPU_FROZEN_FORWARD_DRIFT`。定位确认：该模式的`@`暴露为`aten.matmul`，旧`Q8Matmuls`仅拦截`aten.mm`，因此该分析尝试漏掉激活量化。

原D0B生成夹具使用`torch.no_grad()`，不受这次适配缺陷影响。第一次CPU失败的源码、行数据和`CPU_FORWARD_ATTEMPT1.json`保留，没有用它改原夹具或解释原GPU失败。

新CPU适配同时覆盖二维`aten.mm`和`aten.matmul`。八种组合覆盖no_grad/inference_mode、head/planar、mm/@，结果全部匹配显式量化reference。修复后的inference模式完整前向在保留原卷积时，精确复现冻结行与概率；卷积修正的结果也与no_grad执行一致。

### 4.3 实际CPU计数

`test_reference_ops.py -v`实际3项测试通过，包含上述8种量化组合、旧漏量化反例及96值卷积检查。完整CPU reference forward共5次：第一次分析适配失败1次、有效no_grad诊断2次、修正适配验证2次。全部复用同一原n32输入，没有补GPU样本。目标引擎CLI/HTTP生成仍为0。

最终封存工具曾误用缺少numpy的系统Python，exit1。改用已有CPU依赖venv解释器后完成；`SEAL_ATTEMPT1.json`保留。没有安装新依赖、修改原venv或把该工具失败计为GPU重试。

主要实际命令：

```bash
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1r-20261102/prepare.py'
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1r-20261102/run_once.py'
ssh 29 '/home/hhtele/strata-0.1.43.1/.venv/bin/python -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1r-20261102/analyze_tail.py'
ssh 29 '/home/hhtele/strata-0.1.43.1/.venv/bin/python -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1r-20261102/test_reference_ops.py -v'
ssh 29 '/home/hhtele/strata-0.1.43.1/.venv/bin/python -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1r-20261102/validate_reference.py'
```

`run_once.py`是已执行的记录，独占标记保持，不得将这组命令当作续跑指令。完整编译/链接argv见`BUILD.json`。新程序保留旧源码的misleading-indentation警告，编译exit0，未扩大无关改动。

## 5. 生产与原件

14:33:07只读复核：原v0.2.3为inactive/dead，MainPID0、NRestarts0；无GPU计算进程、无实验PID、18343/18089无监听。13项生产保护SHA及289项历史/源文件SHA全部一致。本轮生产stop/start均0，继续等待用户要求恢复。未改生产配置、模型、PT0、缓存预算、NGINX、驱动、CUDA或Pi。

仅有1个0.5秒间隔护栏样本，未观察到资源门触发；真实显存/温度峰值未完整采集，不能从该样本声明峰值。未启动目标引擎，专家缓存成本不适用。性能、采样/目标状态、质量与服务接入均未验证。

远端原件：`/home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1r-20261102/`。本地镜像：`workspace/dflash2/df01-d1r-20261102/`。44个导出原件，共691815bytes，逐文件bytes/SHA验证一致。归档546386bytes，SHA256：

`ea3fd34e237baa2f154f732d170d7fb0ae5a706f43ef30e0d60b1a976e769eab`

关键回执为`AUTHORIZATION.json`、`GPU_ATTEMPT.json`、`STATE.json`、`TAIL_ANALYSIS.json`、`TOPK_ANALYSIS.json`、`FORWARD_AUDIT.json`、`CORRECTED_REFERENCE_VALIDATION.json`、`CPU_CHECKS.json`、`RESULT.json`、`FINAL_READBACK.json`。源码与失败的CPU尝试同目录保留。build产物留在29独立目录，不纳入导出或生产。该原件目录Git忽略。

包验证另记`PACKAGE_CHECKS.json`。apps/packages未改，未运行pnpm五项应用检查。没有commit或push。

## 6. 当前停止点

本次唯一GPU额度用完，收口，不重跑。首项失败复现，差异定位到drafter前向行数据；selector尾部的同输入条件比对一致。首个前向分歧算子仍未确认，CPU卷积修正也未消除整段差异。不得把条件比对通过改写为D1通过。

当前D1继续`BLOCKED_NUMERICAL_ORACLE`，不进入D2，不切换生产。原D0/D0B/D1/D1C、六FAIL、P05及关闭方向保持。未来重开只能围绕尚未定位的drafter前向分歧制定新的明确范围，不能自动重复本次selector尾部诊断。生产保持停机，恢复等待用户要求。

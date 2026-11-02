# DF01 / D1T · n2300最后一次CPU审计与停止结论

日期：2026-11-02。连接：`jssh 29`。用户授权本轮最多30分钟纯CPU审计，最多派发一次Astra xhigh；若仍找不到最终原因则停止。起点21:13:48，截止21:43:48。原FAIL、原参考和硬门保持，不追加GPU，不进入D2，生产保持停机。

**最终根因未定位；按用户要求停止当前DFlash2候选的排查和后续测试。** 本轮只闭合差异传播机制，没有发现具备源码和同输入证据的单点修复。没有修改模型实现、CPU参考、gold、v2 token门或置信度分类。D1保持未通过。

## 1. 本轮实际完成

复用[D1S原件](DF01-D1S-V2-QUALIFICATION-20261102.md)，执行唯一一次数值尾部重放：冻结CPU行和已保存GPU行两个输入，合计14行selector。完整backbone前向0、GPU程序0、生成0、服务启停0。

| 检查 | 结果 | 证明范围 |
|---|---|---|
| 冻结CPU行经原CPU尾部重放 | token 7/7相同，概率逐bit相同 | 原参考尾部可精确复现，没有换参考 |
| 保存GPU行经同一CPU尾部重放 | token 7/7匹配原GPU输出 | 本夹具尾部同输入未复现token分歧 |
| 同GPU行CPU尾部与原GPU概率 | 最大绝对差`6.705522537e-7` | 原0.1118级第4项概率差可由进入尾部前的行差异解释 |
| Astra独立终审 | 最终根因未定位，支持`STOP_CANDIDATE` | 未发现可证实单点修复，没有另行数值前向 |

实际数值重放于21:18:49完成，耗时3.095秒。Torch为`2.5.1+cpu`，`torch.version.cuda=null`，`CUDA_VISIBLE_DEVICES=''`。没有使用GPU观测行生成新独立参考，观测行只用于定位。

## 2. 第4项怎样发生分歧

两个输入的第4项前驱均为`174243`。`212522`与`209087`都进入两侧top16；没有因前驱已分叉或候选缺失而产生差异。

以下分数均为本轮CPU尾部计算，**不是新增GPU中间采集**：

| 输入行来源 | token 212522总分 | token 209087总分 | 选择结果 |
|---|---:|---:|---|
| 冻结CPU参考行 | 21.259376526 | 20.953548431 | 212522领先0.305828094 |
| 保存GPU实际行 | 20.790576935 | 20.798450470 | 209087领先0.007873535 |

这一检查确认：前向行不同，经相同尾部处理后，两个候选的相对分数发生翻转。它不是精确同值规则触发，也不能直接称为无害舍入误差。

这仍不是最终原因。当前n2300原件没有逐层GPU同输入输出，不能定位首个产生差异的算子，也不能判断CPU参考或GPU实现哪一侧需要修正。行cosine/norm门通过，不保证候选分数排序相同。

## 3. 唯一一次Astra xhigh复核

实际派发`gpt-6-astra / xhigh`一次，任务名`astra_n2300_final_audit`。代理只读检查源码、SHA和本轮产物，未再派代理，未运行尾部或完整模型。

完整结论见[Astra终审原样副本](DF01-D1T-ASTRA-REVIEW-20261102.md)。原review SHA256：

`396c1082178407071a32542a936b08b34456a15db582dd93b2b92112a0c161cd`

复核覆盖head/selector不同量化格式、stable top16与tie规则、词表映射、前驱链、rows[1:]、s=n位置和ring窗口。n2300需要的位置253..2299仍在2064槽保留范围内，未发现具体绕环索引缺陷。5份GPU源码与29当前base身份核对一致。

RMS、RoPE、attention算术差量不能自动作为首因。原D1O统一候选在n32回归失败的记录保留，本轮没有重跑或采用该组合，也没有扫描新的计算顺序组合。

主代理与Astra结论一致：已知传播机制，最终根因未定位，没有可证实单点修复。因此不继续消耗剩余时间做试探修补。

## 4. 保留的失败与执行边界

首次启动误用系统`python3`，在import NumPy时报`ModuleNotFoundError`，尚未创建数值`ATTEMPT.json`。该启动失败的stdout/stderr/命令记录完整保留。

随后改用D1O命令回执记录的只读CPU解释器`/home/hhtele/strata-0.1.43.1/.venv/bin/python`，没有安装依赖或修改环境目录。源码与计算规则不改；实际数值程序只执行一次。

```bash
jssh 29 '/home/hhtele/strata-0.1.43.1/.venv/bin/python -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1t-cpu-20261102/check_tail.py'
```

实际子进程还设置`CUDA_VISIBLE_DEVICES=''`、`OMP_NUM_THREADS=2`、`OPENBLAS_NUM_THREADS=2`。正确启动exit0，原启动exit1不抹除。原始命令回执及派生规范回执同时保留，不覆盖原件。

本轮停止范围是当前DFlash2候选的排查与测试，不是更改既有生产版本。独立GPU selector、target采样、提交状态、EOS及六次生成仍未运行。当前不自动修复参考、不放宽token门、不追加GPU、不进入D2，不再安排该候选的下一轮实验。

该停止结论不等于DFlash2没有性能潜力，也不等于已经证明最终target输出错误；本机候选尚未通过资格，因此没有采用或升级依据。

## 5. 时间、原件与停机回执

21:27:06完成1143项历史/源文件与13项保护SHA核对，全部一致。生产`inactive/dead`、MainPID0、NRestarts0，无GPU计算进程，18343/18089无监听。核对只读取文件和系统状态，没有服务启停。

21:28:14封存最终`STOPPED_UNRESOLVED_ROOT_CAUSE`结果，距本轮起点866.123秒（14分26秒），早于30分钟截止。其后只有报告整理与包检查，不继续排查或数值实验。

远端新目录为`/home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1t-cpu-20261102/`；本地镜像为`workspace/dflash2/df01-d1t-cpu-20261102/`，继续Git忽略。

23项导出原件共267254bytes，归档73815bytes，本地逐项bytes/SHA一致；Astra公开终审与原review逐byte一致。归档SHA256：

`30d1f3243c925099c01b848fae36b9355519fecbdc585d7793cd6778ad5af8ea`

关键原件为`AUTHORIZATION.json`、`ATTEMPT.json`、`TAIL_RESULT.json`、`MECHANISM.json`、`DELEGATION.json`、`astra/REVIEW.md`、`FINAL_IDENTITY.json`、`RESULT.json`和原始/派生命令回执。启动失败保存在`BOOTSTRAP_CPU_TAIL.stdout/stderr`及`BOOTSTRAP_COMMANDS.json`，未覆盖或删除。

包检查另记`PACKAGE_CHECKS.json`。原报告与frontier内容保持，apps/packages未修改，pnpm应用五项检查未运行。没有commit、push、部署、生产恢复或自动后续任务。

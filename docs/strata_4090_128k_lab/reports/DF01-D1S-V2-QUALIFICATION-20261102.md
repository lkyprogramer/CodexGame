# DF01 / D1S · 冻结v2合同的D1 GPU执行回执

日期：2026-11-02。连接：`jssh 29`。本轮新增授权最多2个GPU资格程序、16组夹具、六次生成，GPU窗口≤60分钟；失败保留、不重跑、不补样本，不进入D2，生产保持停机。

**失败：D1在n2300的第4项token硬门停止。** 前三组完整drafter夹具通过v2硬门。置信度差按合同单独记录；原token硬门继续生效。原FAIL与原四组参考保持，D1未通过，性能和质量未验证。

实际执行1个GPU资格程序、4组夹具（3通过、1失败）、0次生成。独立selector三组、target-state九组及全部六次生成未运行。没有使用剩余额度，没有重跑、替补或GPU修复复测。

## 1. 绑定与预检

源冻结：[D1Q回执](DF01-D1Q-V2-ADAPTER-20261102.md)；合同：[默认exact-match v2](../plans/DF01_D1_EXACT_MATCH_V2.md)。读取D1Q的`FINAL_FREEZE.json`和`COMMANDS_V2.json`，不修改冻结文件、argv/env、原四组参考或原binary。

新目录为`/home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1s-v2-20261102/`。新增`AUTHORIZATION.json`承接本次GPU预算；原命令描述的`execute=false`保持历史身份。新监督器只绑定该D1目录，没有D2命令或服务启停操作。

CPU绑定检查2项正例通过，5项负例均拒绝：非有限概率、错误token、错误行门、伪装的legacy token失败、缺失置信度诊断。这里不做完整模型前向。

GPU前逐项核对1122项冻结身份。生产停机、无外来GPU计算进程、18343/18089无监听、GPU温度<85℃、MemAvailable>4096MiB、磁盘余量≥8GiB，均满足原护栏。真实输入token SHA及128K总预算核对通过；PROB/COUPLED/GATE_PICK/GUMBEL/COST模式继续排除。

监督器保留原程序非零退出即停止的规则，只接受指定完整drafter置信度绝对差的legacy失败。四份夹具记录均独立保存legacy、诊断和v2硬门；单夹具记录的`D1_v2_qualified`保持false。

## 2. GPU夹具结果

| context / seed | token一致 | 最大置信度绝对差 | 原v1数值判定 | v2 drafter硬门 |
|---|---:|---:|---|---|
| 32 / 1 | 7/7 | 0.045106769 | PASS | PASS |
| 2048 / 2 | 7/7 | 0.079903543 | FAIL | PASS，置信度诊断 |
| 2064 / 3 | 7/7 | 0.080638349 | FAIL | PASS，置信度诊断 |
| 2300 / 4 | 6/7 | 0.113537192 | FAIL | FAIL：`selector token 3` |

n2300的首个且唯一token差异为零基index3：GPU实际`209087`，冻结CPU参考`212522`。行有限值、cosine和norm门通过，随后token比较拒绝。置信度差仍保留为诊断，不能覆盖token硬失败。

原生程序输出：

```text
drafter n=32 PASS
drafter n=2048 PASS
drafter n=2064 PASS
DF01 qualification FAIL: /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1n-20261102/fixtures/drafter-n2300-seed4.bin: selector token 3
```

前三行来自stdout，失败行来自stderr。程序exit1，监督器记录`NATIVE_PROGRAM_FAILURE`并停止。独立selector的`1e-5`门未运行，target采样、提交状态和EOS GPU硬门未运行；不得将其写成通过。

本轮只观察到GPU草稿与冻结CPU参考的token不同。CPU参考或GPU实现中哪一侧导致差异，仍未确认。该失败阻断当前实现资格，不直接证明最终target输出错误，也不能给出真实吞吐或升级结论。

## 3. 时间与停止点

GPU窗口为19:58:17.988242至19:58:20.107318，约2.119秒。此后只有原件读取与身份校验，没有继续启动GPU进程。监督器20:02:31完成全部冻结身份复核并收口。

原四组参考不重算、不拼接、不替换。完整drafter置信度差以外的硬门不改。D1未通过，D2未开始；不安装服务，不切换生产版本，生产继续停机。

后续若继续定位，现有n2300实际行/token/概率原件可供CPU审计。本轮不追加该审计，不放宽token门，不补GPU样本。

实际命令：

```bash
jssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1s-v2-20261102/bind_cpu.py && python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1s-v2-20261102/supervisor.py --detach'
```

监督器源码副本见[run_d1_v2.py](../tools/dflash2_v2/run_d1_v2.py)，CPU绑定来源见[bind_d1_v2.py](../tools/dflash2_v2/bind_d1_v2.py)。原D1/D1N数值失败、D1Q的legacy记录及其他历史结果保留。

## 4. 原件与最终状态

四组完整实际行/token/概率及各自v2 JSON均保留。n2300最小行cosine为0.998586750，norm比范围0.998230531–1.001412192，仍满足原行门；6/7 token一致。读取原件并汇总这些数值不加载模型，不重新执行比较程序或GPU程序。

20:04:38最终回执：生产`inactive/dead`、MainPID0、NRestarts0，无GPU计算进程，18343/18089无监听。13保护SHA一致。监督器复用同一冻结清单完成前后两次1122项校验，1104项历史/源文件身份保持。没有服务启停或恢复生产。

GPU遥测只有1个采样点：41℃，MemAvailable约57925MiB。单点未覆盖完整GPU分配阶段，实际显存峰值为UNKNOWN；采到的1MiB不能作为drafter实际显存或峰值。没有真实生成、缓存槽数或吞吐证据。

本地镜像为`workspace/dflash2/df01-d1s-v2-20261102/`，继续Git忽略。23项原件共745927bytes，归档414895bytes；本地逐项bytes/SHA一致，监督器/绑定脚本公开副本与远端源码一致。归档SHA256：

`8cefda37bb0964f03f1e2c37e5d482693b71445f4edca20fdd924cb72e373d91`

关键回执为`AUTHORIZATION.json`、`BINDING_CPU_CHECKS.json`、`PREFLIGHT.json`、`GPU_ATTEMPT.json`、`STATE.json`、`drafter.stdout/stderr`、四份`*.v2-observed.bin`及其JSON、`RESULT.json`、`FINAL_READBACK.json`。冻结清单和命令仍指向D1Q，完整绑定SHA保存在新授权文件中。

包检查另记`PACKAGE_CHECKS.json`。原报告与frontier清单不改；apps/packages未修改，pnpm应用五项检查未运行。本轮没有commit、push、部署、D2或生产恢复。

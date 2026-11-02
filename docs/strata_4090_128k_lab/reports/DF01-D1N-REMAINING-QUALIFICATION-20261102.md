# DF01 / D1N · 四组参考冻结与剩余D1有界补验

日期：2026-11-02。连接：`ssh 29`。用户授权：CPU准备最多30分钟；通过后执行最多两个GPU程序、16组夹具、六次生成，GPU窗口不超过60分钟；失败保留、不重跑、不补样本，不进入D2，生产保持停机。

**部分完成：四组CPU参考冻结及CPU检查通过；GPU的n32回归通过，n2048概率门失败后停止。完整D1未完成。** 本轮实际1个GPU程序、2组夹具（1通过/1失败）、0次自由生成；剩余14组及六次生成未运行，没有重跑或补样本。

原首组n32的CPU修复经新GPU回归成立。但该修复尚不能支持全部D1夹具。n2048是未读取新GPU输出前冻结的边界夹具，其概率差超原门限。本轮不能据此断言DFlash2算法错误、性能无收益或生产可采用；更深的算术/参考原因未确认。

## 1. 参考冻结与CPU验证

任务起点为北京时间15:57:01，CPU截止16:27:01。四组统一使用D1M来源一致的真除、卷积和planar整数GEMM路径；head保持既有Q8_1加Torch矩阵乘法，不接入attention原型。

新`freeze_reference.py`只将D1M的n32入口参数化到原四组输入，删除与GPU逐层原件比较的诊断记录。四组完整CPU参考各执行一次，共4次。n32新参考与D1M逐byte相同；另三组在本轮新GPU执行前生成并冻结，没有注入GPU激活或输出，也没有观察结果后更换输入、seed或算法。

| context / seed | 新CPU参考SHA256 |
|---|---|
| 32 / 1 | `a430e21b562f4562fdd05771853dba03a9458fdeb0f2fc4da20c3381d72f3fe2` |
| 2048 / 2 | `80ad7419db4489780d7dfaf5e41214aa95127ba18ec1bc27ccbdf91da75c8b81` |
| 2064 / 3 | `76b9fd504355b7c6a6c0dd06e23f37bace0fd71f9a2a9b0b43d5d91443008cc7` |
| 2300 / 4 | `e17b4007ba1d280e57413812465f70ad3aced52e8d1d3108374d58642c2180ca` |

四份新夹具只在独立副本替换期望输出区。原header、tap、embedding、词表及head的输入前缀bytes/SHA均与D0B原件一致。原四份gold和历史失败不改。每组检查行有限、概率有限且在[0,1]、文件长度及写入往返；具体prefix SHA和新夹具SHA见`REFERENCES.json`。

CPU原比较器以保存的n32 GPU原件比较新参考，正例通过，错误token、概率超限及非有限行三个负例均拒绝。drafter资格程序只重新编译/链接诊断入口，不改CUDA计算，新的binary SHA为`960104e50d84081a4568234c43a2d21710323774a1ad397d4adb3cf4fb082b82`。target-state程序及六次CLI命令沿用原冻结版本。

CPU采样/状态原语源码未变，复用既有验证，不重跑其枚举测试。这里的CPU检查不替代GPU资格。

### 元数据封存中断记录

初版封存helper在编译和比较器通过后，重复整块读取同一目标模型文件。为在CPU截止前完成封存，主动中断该未完成的元数据阶段，exit143及原代码/输出保留。两份目标GGUF合计75839998528bytes；后续独立metadata入口对每个唯一文件流式校验一次。

该调整没有重跑参考前向、编译、比较器或GPU程序。没有数值/编译断言失败，也没有修改测试门限。实际记录见`HASH_SEAL_INTERRUPTION.json`、`HASH_SEAL_EXIT.json`、`METADATA_CONTINUATION_ATTEMPT.json`及两份封存脚本。

16:11:53.259完成冻结，CPU窗口892.259秒（14分52秒），低于30分钟。`FREEZE.json`包含965项身份：源码、依赖、四组新参考/夹具、比较器、程序、六条命令、目标资产及原保护/历史文件。合并清单保留全部原保护值与历史期望值，没有用新哈希覆盖不同的旧值。

## 2. GPU实际执行与首个失败

GPU前完整身份与资源核对通过后，16:16:32.506开始独立GPU窗口。上限为60分钟，运行截止为第50分钟，后10分钟保留清理与封存。监督器只启动一次，持有原GPU锁，不控制生产unit。

实际程序于16:16:32.529启动，16:16:34.609记录exit1；监督墙钟2.080秒包含轮询等待，不是性能测量。

实际stdout：

```text
drafter n=32 PASS
```

实际stderr的失败原文：

```text
DF01 observation: drafter-n2048-seed2.bin.df01-observed.bin (host rows, tokens, probabilities)
DF01 qualification FAIL: /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1n-20261102/fixtures/drafter-n2048-seed2.bin: selector probability 1: reason=absolute_difference actual=0.624771178 expected=0.704674721 abs_diff=0.079903543 limit=0.0500000007
```

“probability 1”是零起始索引，即第2项。原门为绝对差≤0.05，没有放宽为本次观察值。按原比较器执行顺序，失败前n2048的shape、八行有限值/cosine/norm以及前两项token已满足门；后续原断言因首个失败而停止。

失败观察文件直接保存程序已读回的host rows、七项token及概率，不增加GPU读回或第二次程序执行。后续仅离线统计保存原件，不生成新参考、不修复后重跑。

| 原冻结项目 | 本轮结果 |
|---|---|
| n32 / seed1 | PASS |
| n2048 / seed2 | FAIL，selector probability 1 |
| n2064、n2300 | NOT_RUN，共2组 |
| 三组独立selector | NOT_RUN，共3组 |
| target-state | NOT_RUN，共9组；程序未启动 |
| greedy短代码MTP/DF4 | NOT_RUN，2次生成 |
| 生产采样短代码MTP/DF4 | NOT_RUN，2次生成 |
| 生产采样长代码MTP/DF8 | NOT_RUN，2次生成 |

两项GPU程序上限实际使用1项，16夹具上限实际尝试2组，六次自由生成实际0次。剩余额度不用于诊断、替补或修复复测。D2及服务接入未开始。

## 3. 原件、资源与生产

保存原件的离线统计显示：n2048七项token全部一致，仅第2项概率超0.05；最大概率差0.079903542995，最小cosine为0.9994115861，norm比例0.9991267712–1.0042577591。这是对现有文件的CPU统计，没有追加前向或GPU，不将原程序未执行的后续断言倒写成GPU PASS。

n2048观察文件SHA256：`9dabed75cf7f998cd35a69930b350bade310ee4dadcde2f11b7326f5442d1075`。

GPU窗口16:16:32.506至16:20:44.562，共252.055秒，低于60分钟。窗口包含身份收口时间，不作性能指标。两秒周期只捕获1个资源样本：42°C、MemAvailable约57906.46MiB；未触发资源门。采样会遗漏短程序峰值，实际显存/内存峰值保持UNKNOWN，不能把样本中的1MiB说成运行峰值。目标引擎和专家池未启动，专家槽数不适用。

16:21:40最终复核生产`inactive/dead`、`MainPID=0`、`NRestarts=0`；无GPU计算进程，18343/18089无监听。13项生产保护SHA及910项历史/源文件一致，监督器启动前后965项冻结身份一致。本轮服务start/stop均0。生产目录、回滚树、NGINX、CUDA/驱动、Pi、PT0和缓存预算未改。

新远端目录：`/home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1n-20261102/`。本地镜像为`workspace/dflash2/df01-d1n-20261102/`，继续Git忽略。

关键原件为`AUTHORIZATION.json`、`REFERENCES.json`、`CPU_CHECKS.json`、`FREEZE.json`、`COMMANDS.json`、`STATE.json`、`drafter.stdout/stderr`、n2048观察binary、`RESULT.json`和`FINAL_READBACK.json`。所有实际argv、环境、身份与时间戳保留。新FREEZE文件SHA256：`9d7d51b9c01faa85b1a2df855ad4852a656df823ded652193f46299d87ca31b6`。

导出53项原件，共885417bytes，归档494581bytes；本地逐文件bytes/SHA校验一致。归档SHA256：`e6e79519ded670b13bf031a387db9127d94c14e76f237d335f8a2a6a52659a8a`。完整输入夹具、编译库/binary和CUDA缓存只留29；导出包含四份小型期望参考binary、源代码、日志及SHA清单，不复制大模型和旧原件。

主要实际命令：

```bash
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1n-20261102/prepare.py'
ssh 29 '/home/hhtele/strata-0.1.43.1/.venv/bin/python -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1n-20261102/freeze_reference.py'
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1n-20261102/build_cpu_checks.py'
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1n-20261102/complete_cpu_seal.py'
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1n-20261102/seal.py'
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1n-20261102/supervisor.py --detach'
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1n-20261102/finalize.py'
```

以上是已执行记录，不是续跑清单。第三条在元数据阶段主动中断exit143，第四条不重跑此前已完成的计算或测试。监督器内唯一GPU命令为冻结的drafter资格程序，exit1，不自动启动后续命令。包检查另记`PACKAGE_CHECKS.json`。apps/packages未改，未运行pnpm应用五项检查。没有commit或push。

## 4. 当前停止点

D1保持数值资格阻断，完整目标采样/状态、自由生成、性能及任务质量未验证。n32回归通过不能代替n2048边界资格，四组CPU参考冻结也不能写成四组GPU通过。

本轮到此收口。原D0/D0B/D1/D1C/D1R/D1L/D1M及六FAIL、P05与关闭方向保持。新失败单独登记，不改旧结果，不自动追加GPU、CPU参考前向或进入D2。生产继续停机，恢复等待用户明确要求。

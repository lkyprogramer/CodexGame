# DF01 / D1C · CPU概率审计与可确认问题修复

日期：2026-11-02。连接：`ssh 29`。范围：用户授权CPU概率定义/参考审计、修复可确认问题和CPU验证；原v0.2.3彻底停机，等待用户要求后再恢复。不追加GPU实验，不进入D2，保留原失败。

**部分完成：CPU审计和两项可确认问题修复完成；原`selector probability 0`的唯一根因仍未确认。** 原[D1失败回执](DF01-D1-QUALIFICATION-20261102.md)保持`BLOCKED_NUMERICAL_ORACLE`。本轮没有改容差、改原夹具或重标D1通过。

CPU参考与实际D1二进制中的selector使用相同的概率定义。四组冻结参考的28项概率在CPU精确重放。发现并修复参考实现的同值排序问题和资格程序的证据缺失问题。但这两项修复不改变原四组期望值，不能证明原GPU失败解除。

生产11:30:36停止。11:46:26最终复核为inactive/dead、MainPID 0，无GPU计算进程，18343/18089均无监听。原13项保护SHA一致。**本轮不恢复生产，后续仅按用户明确要求恢复。**

## 1. 概率定义

`selector probability 0`中的`0`表示第0项提案索引，不表示GPU实际概率等于0。原D1 stderr没有打印实际值。

对每一项提案，先从head logits选择16个候选，再计算：

```text
score[j] = unary[j] + sum(B[candidate[j]] * A[previous_token] * hp)
winner   = first_argmax(score)
p        = 1 / sum(exp(score[j] - score[winner]))
previous_token = candidate[winner]
```

这个`p`是selector在这16个分数上的置信度。它不是目标模型概率，也不是拒绝采样使用的完整proposal分布`q`。目标的temperature/top-p/top-k不进入这个selector置信度公式。

| 核查对象 | 结果 |
|---|---|
| 原CPU Torch reference | `softmax(score)[winner]`，同一定义 |
| D0B Q8参考的尾部 | 同一定义，先映射draft-vocabulary，再读两张codebook |
| 原生`select_kernel`源码 | 同一定义，严格大于才替换赢家，同值保留候选首项 |
| D1原binary的device PTX | 16个`exp(score-max)`相加后取倒数；与原静态库selector PTX逐字一致 |
| mapped输出与host读回 | 源码两端均在`+16`个32-bit元素，即64bytes；已有stream同步 |

PTX核查使用CPU工具`cuobjdump`，没有执行device代码。原D1 binary SHA仍为`dd81db40825ea253339df28e1b9eb5d7c2927d4148b698efca1638582d815200`。输出地址核查属于源码审计，不冒称重新验证GPU读回。

首次PTX提取用子串误选了无关的`mtp_select_kernel`，导致一次错误的差异断言。改用完整mangled entry后确认一致。错误提取和diff保留，不将其记为真实binary漂移。

## 2. 冻结输入CPU重放

从四个原`fixtures-q8act/*.bin`直接读取冻结final rows、Q8 head、词表映射及期望token/概率。不重新计算目标特征，不重新执行五层draft forward，不生成新样本。Q8 head和selector projection仍使用D0B冻结的对应激活量化格式。

| 冻结单元 | 期望token匹配 | 原概率最大差 | 同值修正后概率最大差 | top16边界同值行数 |
|---|---:|---:|---:|---:|
| n32 / seed1 | 7/7 | 0 | 0 | 0 |
| n2048 / seed2 | 7/7 | 0 | 0 | 0 |
| n2064 / seed3 | 7/7 | 0 | 0 | 0 |
| n2300 / seed4 | 7/7 | 0 | 0 | 0 |

独立标量公式与Torch softmax的最大绝对差为`8.636891046798212e-08`。这是两种CPU计算的比较，不是GPU实际误差，也不验证CUDA `__expf`的实际执行。

首组第0项CPU期望仍为`0.7341100573539734`。修复没有根据GPU失败值重拟期望。原D1实际概率、实际final rows、head logits和selector projection均没有原件，因此无法从CPU参考唯一反推原GPU差异产生的位置。

## 3. 可确认问题与修复

### 3.1 参考head同值排序

原参考使用`torch.topk(..., 16)`，没有规定同值顺序。原生head `better()`明确规定：同值时head行号较小者优先，再映射到实际token ID。

CPU反例为32个完全相等的head logits。原Torch实现首项选24；原生规则要求选0。原实现控制程序实际返回exit 1，输出`HEAD_TIE_CONTRACT_MISMATCH`。该反例保留。

新参考改为稳定降序排序后取前16项。selector最终分数同值仍保留候选首项。CPU检查覆盖head全同值、词表映射顺序、top16边界同值、前驱依赖、置信度公式和selector同分。

修复位于新目录中的`selector_reference.py`及`make_q8_fixtures.py`副本。旧D0B脚本和四组夹具未改。原四组修正后仍逐项完全一致，因此这项问题不是已经证明的原D1根因，也不能使原D1转为通过。

### 3.2 失败证据缺失

旧比较器将非有限值、越界和绝对差过大都压成`selector probability <index>`。它没有保存实际概率、差值或实际行数据。这是本次无法唯一定位的已确认限制。

新比较器输出`reason`、`actual`、`expected`、`abs_diff`和`limit`。例如CPU负对照实际输出：

```text
selector probability 0: reason=absolute_difference actual=0.899999976 expected=0.5 abs_diff=0.399999976 limit=0.0500000007
```

这些数值来自CPU控制，**不是原D1 GPU实际值**。同一程序对NaN、Inf和范围错误分别输出原因。原有限值、[0,1]、绝对差≤0.05门保持。

新资格程序在比较失败时，将已经读回host的8×2560 final rows、7个token和7个概率写入当前执行目录中的`*.df01-observed.bin`。D1OB v1固定格式为81992bytes，保留原始float bits，包括NaN。使用独占创建，已有文件不覆盖。写入失败仍保留原资格失败，不吞掉异常。

该修复没有新增CUDA调用、device读回、同步或kernel。仅在资格失败后写host原件，不修改性能binary。新资格binary编译/链接完成，**没有执行GPU路径**。SHA256：

`960104e50d84081a4568234c43a2d21710323774a1ad397d4adb3cf4fb082b82`

## 4. CPU验证

| 检查 | 实际结果 |
|---|---|
| 旧head同值反例 | 预期失败，exit 1，24≠0；原件保留 |
| 修正后的selector合同 | 6项通过 |
| 四组原参考重放 | 28项token/概率符合；概率差0 |
| 修正后四组原参考重放 | 28项token/概率符合；概率差0 |
| 新旧比较器差分 | 324组含NaN/Inf/边界的概率组合，判定完全一致 |
| 新错误原因 | 5类负对照通过 |
| host观察文件 | bits往返、81992bytes、禁止覆盖、错误shape拒绝通过 |
| 旧7项比较器控制绑定新header | 7项通过 |
| 新资格程序 | CPU编译/链接exit 0；GPU执行未开始 |
| Python语法 | 通过 |

执行器最初还按源文件的quoted include运行了未修改的旧7项控制。随后用显式绑定新header的独立副本完成上述7项验证，回执在`PATCHED_CONTROLS.json`。没有把前一项冒称新header验证。

新资格程序保留旧源码已有的`-Wmisleading-indentation`警告，编译exit 0。本轮没有将其作为错误，也没有扩大到无关格式重构。

主要命令：

```bash
ssh 29 '/home/hhtele/strata-0.1.43.1/.venv/bin/python -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1c-cpu-20261102/audit_selector.py'
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1c-cpu-20261102/validate_cpu.py'
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1c-cpu-20261102/finalize_cpu_audit.py'
```

编译/链接及CPU测试的完整argv与exit code见`CPU_VALIDATION.json`、`PATCHED_CONTROLS.json`。CPU Torch为`2.5.1+cpu`，`torch.version.cuda is None`。所有Python调用使用`-B`，未安装新依赖。

## 5. 生产、原件与交付边界

本轮生产只执行一次`systemctl stop openclaw-qwen38-next.service`，没有执行start。原unit、配置、引擎、模型、缓存预算、PT0、NGINX、驱动、CUDA和Pi设置不变。没有停止其他Docker容器。

| 当前检查 | 结果 |
|---|---|
| 生产 | inactive/dead、MainPID 0、NRestarts 0 |
| 18343/18089 | 无监听 |
| GPU计算进程 | 无 |
| 生产13项保护SHA | 匹配 |
| 冻结历史与所查源文件 | 226项SHA匹配 |
| 新GPU实验 / 目标引擎生成 | 0 / 0 |
| 新完整reference forward | 0；只做两轮各4组冻结尾部重放 |
| D2 / 服务接入 / 部署 | 未开始 |

原D0、D0B、D1原件和报告保持。新目录为`/home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1c-cpu-20261102/`，本地镜像为`workspace/dflash2/df01-d1c-cpu-20261102/`。修复源码、`FIXES.diff`、CPU负对照和验证回执均在该目录。新GPU binary保留在29的独立build目录，未放进原生产或原D1目录。

61个导出原件，共623542bytes，逐文件bytes/SHA验证一致。归档138697bytes，SHA256：

`11ef93c539d76717db910bbb4ced17461517e49f27213851ee465b9f688736de`

导出不包含编译binary、object和完整通用PTX dump；保留相关selector PTX与身份回执。新目录继续Git忽略，报告包不上传原始历史/资产。包检查另记`PACKAGE_CHECKS.json`。apps/packages未变，未运行pnpm五项应用检查。没有commit或push。

## 6. 当前停止点

CPU审计和可确认修复完成，原GPU失败的唯一根因仍未确认。已明确的阻塞是缺少原GPU实际概率及中间输出。相同概率定义、CPU参考可复现和同值修复不能代替该证据。

D1资格继续阻塞，性能与质量仍未验证。后续若另行授权D1资格复测，可以使用新诊断程序收集实际值；本轮不执行、不补样本，不进入D2。原v0.2.3保持停机，恢复等待用户明确要求。

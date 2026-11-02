# DF01 / D1P · 默认exact-match纯CPU验收合同复核

日期：2026-11-02。连接：`ssh 29`。授权：30分钟纯CPU复核、明确默认exact-match正确性依赖、判断草稿置信度差的诊断分类、保留目标采样/提交状态/EOS硬门并更新文档；原FAIL保留，不直接放行D1，不追加GPU，不进入D2，生产保持停机。

**已完成：草稿置信度绝对差可以在冻结默认exact-match路径中改为诊断项；目标采样、提交状态与EOS硬门保留。** 决定仅适用于后续新增批次，适用范围与执行前置见[合同v2](../plans/DF01_D1_EXACT_MATCH_V2.md)。原D1/D1N FAIL不重标，D1O统一参考回归失败也不改判。

本轮没有修改GPU程序、引擎或runner，没有重新选择CPU参考。v2适配未实现，GPU硬门未运行，完整D1仍未通过。不能直接忽略旧资格程序的exit1后继续。

## 1. 默认路径的实际依赖

在base CLI、实际计量版源码和target-state程序三份源码中，核对相同的窗口、接受、提交和EOS控制：

| 位置，base CLI行号 | 事实 |
|---|---|
| `src/program/generate.cpp:16542` | `spec-min-p`用实际草稿置信度选窗口宽度 |
| `:16608` | `ver.set_spec_q`仅在MTP概率模式满足条件时调用；冻结默认环境不启用该模式 |
| `:16647` | 接受判定只比较`window[a+1] == outv[a]`，不读取草稿置信度 |
| `:16669` | 提交`a+1`个有效输入行 |
| `:16681` | 可见输出受首个EOS和max-new约束 |
| `:16701` | 非终止步骤位置前进`a+1`，最后target输出作为下个anchor |
| `src/core/verify.cpp:3168` | 每次target采样以`pos0`设置counter |
| `src/kernels/cuda/sampler.cu:427` | 逐行使用`Philox(seed,counter+t)` |
| `src/core/verify.cpp:3382`及`:3441` | 提交数量有范围检查，PLE按输入前缀推进，存在异步提交等待边界 |

以上路径相对远端`/home/hhtele/strata-lab-4090/workspace/trees/base/`。计量版与状态程序对应行号、完整路径和SHA记录在`CPU_AUDIT.json`。

base CLI源码SHA与既有采样证明匹配，计量版源码SHA与`METER_BUILD.json`匹配，状态程序源码SHA与`QUALIFICATION_BUILD.json`匹配；三项核对均通过，见`SOURCE_BUILD_MATCH.json`。

### 正确性推导的前提

target在当前前缀和草稿前缀上逐位置产生输出。只有草稿等于该位置target输出时，才保留对应前缀；首次拒绝后，其余行丢弃。该控制流保持target输出的条件是：

- 同一有效前缀的target数值/采样处理器必须正确。
- 目标随机数按位置索引，窗口划分不能重置随机数或读取未消费的未来draw。
- 草稿与窗口宽度在对应target未来draw之前决定。
- 有效前缀提交和下一步位置推进必须正确。
- EOS和输出预算终止必须正确，终止CLI状态不得继续复用。

草稿置信度决定需要验证多少行，不替代target采样或最长匹配判定。它不需要在CPU与GPU之间相差小于0.05，才能满足上述控制流推导。但推导不能证明真实GPU的target计算和状态已经满足前提，因此相关GPU硬门不能降级。

## 2. CPU验证

新`audit_cpu.py`只使用Python标准库，不加载模型或CUDA程序。它核对冻结命令中没有PROB/COUPLED/GATE_PICK/GUMBEL/COST环境模式，也没有serve、固定续写、oracle或corrupt参数；DF命令保持`draft-conf=0`、`spec-min-p=0.5`。

独立有限Markov target使用27种草稿、8种置信度模式、cap4/8和243组逐位置draw，共**104976组**比较。窗口宽度随置信度和已输出前缀变化；每次推测输出均与逐token输出相同。

三个错误实现负例均检出：

| 负例 | 检出的区别 |
|---|---|
| 首拒后仍保留后续行 | 输出序列不同 |
| 每个窗口复用起始draw | 固定位置的输出不同 |
| target EOS后继续输出 | 出现EOS之后的token |

该有限模型验证控制逻辑和置信度调度独立性，不验证GPU数学指令、真实logits、KV/GDN/PLE/index或真实EOS轨迹。复用旧6561组CPU采样证明及CPU宿主EOS证据，没有重跑原程序。GPU采样/状态/EOS仍为NOT_RUN。

把n2048保存的两组概率代入原窗口规则，cap4两边均为4行，cap8两边均为6行。这是离线推演，不能当作真实CLI生成结果。

## 3. 诊断分类的精确边界

本轮只改变未来合同对“完整drafter GPU置信度对CPU参考的绝对差≤0.05”的分类。旧门及旧FAIL保持，原始概率、差值、输入身份和窗口仍须保存。

以下项目不降级：

- shape、有限行、原cosine/norm门和token相等检查。
- 草稿置信度有限且在[0,1]，token ID有效。
- 独立selector固定输入的token与`1e-5`概率检查。
- target采样、首/中/全拒绝及全接受控制。
- 有效输入前缀的KV/GDN/PLE/index、snapshot、异步提交和MTP fallback状态检查。
- EOS/max-new可见输出、正确提交及终止同步。
- 实际DFlash2命中、无回退、资源与身份门。

PROB/p-q分布校正、耦合草稿、其他采样模式不在本决定内。selector置信度不能直接当作target概率或q分布。运行参数和GPU计算均不因诊断分类改变。

## 4. EOS与现有状态夹具的边界

现有CLI在输出截断前提交接受输入前缀。EOS出现在前面时，可见输出数会少于已提交输入数；原D0B已经把这两项分别检查。其早期`FAIL_PREFIX_CONSERVATION`与后续边界修正记录继续保留，本轮没有重新定义或隐藏原失败。

保留的EOS硬门为：按首次target EOS截断，不输出其后token，不因草稿EOS提前终止；提交状态等于真正接受的输入前缀；结束等待commit完成并丢弃该CLI状态。这里不证明可见EOS位置的可复用终态。API/Pi恢复、取消与分支生命周期仍属于D5，serve guard保持。

另一个覆盖边界：现有target-state程序要求DFlash2启用和taps有效，但内部调用MTP draft来检查fallback状态。它不等同DFlash2完整多轮状态生命周期验收。CPU宿主EOS、GPU受控EOS状态与真实CLI终止记录必须分别报告。

## 5. 交付、停止点与原件

交付独立[合同v2](../plans/DF01_D1_EXACT_MATCH_V2.md)，并更新主计划、NEXT_ACTIONS、README、AI入口和VALIDATION。合同只用于下一次独立授权的D1，不继承旧剩余额度。

下一次GPU执行前仍缺：v2最小资格适配、分类负对照、新源码/binary/记录schema冻结，以及单独GPU授权。适配必须只允许指定置信度差作为诊断；错误token、NaN/越界概率、错误shape、target/state/EOS错误均须停止。当前旧程序遇到0.05差仍返回exit1，本轮未修改它。

任务起点17:11:03，截止17:41:03。CPU结论及现场回执17:23:28封存，耗时745.936秒（12分26秒）；其后只整理文档包。

17:23:28复核生产`inactive/dead`、`MainPID=0`、`NRestarts=0`，无GPU计算进程，18343/18089无监听。13保护SHA与1037历史/源文件身份一致；审计涉及的源码身份也再次核对一致。

新远端目录：`/home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1p-contract-20261102/`。本地镜像为`workspace/dflash2/df01-d1p-contract-20261102/`，继续Git忽略。

12项导出原件，共195596bytes，归档50897bytes；本地逐文件bytes/SHA一致。归档SHA256：

`537ef2c33994b1aafd3784b5b7b9e999102b69320902ecfd3a9bc73f5d7a4869`

关键原件：`AUTHORIZATION.json`、`CPU_AUDIT.json`、`SOURCE_BUILD_MATCH.json`、`CPU_AUDIT.stdout/stderr`、`RESULT.json`和`FINAL_READBACK.json`。主要实际命令：

```bash
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1p-contract-20261102/prepare.py'
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1p-contract-20261102/audit_cpu.py'
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1p-contract-20261102/finalize.py'
```

本轮CPU完整模型前向0、GPU程序0、生成0、服务启停0。原FAIL与CPU参考不改；D1不放行，D2未开始，生产保持停机。

报告包检查另记`PACKAGE_CHECKS.json`。apps/packages未修改，未运行pnpm应用五项检查；没有commit、push、部署或生产恢复。

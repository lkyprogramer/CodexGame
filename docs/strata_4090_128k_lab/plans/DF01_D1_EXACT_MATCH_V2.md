# DF01 · D1默认exact-match验收合同v2

版本日期：2026-11-02。决定依据：[D1P CPU合同复核](../reports/DF01-D1P-EXACT-MATCH-CONTRACT-20261102.md)。本合同仅适用于后续新增批次，不重标D1/D1N及其他已执行批次。

**决定：默认exact-match模式下，完整drafter的CPU/GPU selector置信度绝对差改为诊断项。目标采样、有效前缀提交和EOS继续作为硬门。** 该决定不是D1通过，不是GPU执行授权，不进入D2。

当前状态：[D1S](../reports/DF01-D1S-V2-QUALIFICATION-20261102.md)在n2300 token硬门失败后，[D1T唯一CPU终审](../reports/DF01-D1T-FINAL-CPU-STOP-20261102.md)确认差异传播自前向行，但最终根因未定位。按用户要求停止当前候选排查与后续测试。没有修改参考、gold或本合同硬门，D1未通过，D2未开始，生产保持停机；以下合同用于追溯，不构成新执行授权。

## 1. 有效范围

- 固定A0实验身份、同一Q8 pack、原D1N四组输入/参考及tokenizer/PT0；不重新选择CPU参考，也不采用D1O回归失败的组合。
- 单GPU、native、非serve且非batch的CLI；草稿确定性产生，target按原greedy或生产采样参数运行。
- `draft-conf=0`、`spec-min-p=0.5`和原cap4/8策略保持。诊断分类变化不改变运行时置信度、阈值或实际窗口。
- `STRATA_SPEC_PROB`、`STRATA_SPEC_COUPLED`、`STRATA_SPEC_GATE_PICK`、`STRATA_SPEC_GUMBEL`、`STRATA_SPEC_COST`必须不在本轮子进程环境中。采用完整环境白名单，不继承未知推测模式。
- 不启用`--spec-follow`、`--spec-oracle`、`--spec-corrupt`、suffix/lookup替代源、概率接受或分布校正。受控GPU状态/EOS夹具的人工拒绝或bias仅用于其隔离检查，不用于真实生成。
- 不增加penalty、logit bias或采样处理器。原EOS受控夹具的bias例外单独标记。

以上任一条件改变，本合同的置信度诊断分类不自动适用。尤其不能把该结论推广到p/q拒绝采样或把selector置信度当作q分布。

## 2. 正确性依赖

设当前窗口输入为`w[0]=x,w[1..T-1]=drafts`，位置为`p..p+T-1`。target输出为`y[0..T-1]`。

1. 每个`y[i]`必须来自同一有效前缀下的target计算及相同采样处理器。
2. target随机数必须按`Philox(seed,p+i)`取值，与窗口划分无关；greedy必须保持同值选择规则。
3. 草稿和窗口长度必须在对应target未来随机数取出前确定，不能读取未消费的target随机数。
4. 取最大`a`，使`w[i+1]==y[i]`对`i<a`成立；首次不匹配后的行必须丢弃。
5. 正常非终止步骤输出`y[0..a]`，提交输入`w[0..a]`；下一步anchor为`y[a]`，位置增量为`a+1`。
6. 实际KV/GDN/PLE/index状态必须与该有效输入前缀的逐token执行一致，并满足异步提交同步边界。

在这些条件下，草稿置信度只选择要验证的工作量，不能替代target接受判定。CPU置信度逼近GPU到0.05以内，不是上述控制流等价性的必要条件。

该推导依赖真实target数值、采样和状态的正确性。有限CPU模型不能证明GPU窗口计算已满足这些前提；以下硬门必须实际执行。

## 3. 仅本次调整的诊断项

| 项目 | v1历史分类 | v2后续分类 |
|---|---|---|
| 完整Q8 drafter GPU置信度对CPU参考的绝对差≤0.05 | 硬门；原失败保留 | 数值诊断；记录全部值、差值、原v1判定 |

诊断必须保存原输入身份、实际行/token/置信度、CPU参考及实际T。不能裁剪差值、覆盖gold、按context挑参考或把原FAIL改成PASS。

这一调整只适用于完整前向后的置信度跨后端比较。独立selector固定输入概率检查仍按原`1e-5`硬门执行。置信度非有限值、超出[0,1]或输出缺失仍为硬失败。

本轮不调整原drafter行有限值/cosine/norm门和token相等门。它们继续承担既有实现资格检查，不因置信度分类变化而自动放宽。

## 4. 保留的硬门

| 硬门 | 必须交付的证明 | 当前状态 |
|---|---|---|
| 模式与身份 | 实际argv/env、binary/输入/pack/参数身份匹配；没有越出第1节 | D1S冻结身份预检通过；真实CLI未运行 |
| drafter基本资格 | shape、有限行、原cosine/norm、有效token及原token相等检查；置信度有限且在[0,1] | D1S前三组通过；n2300 token硬门失败 |
| 独立selector | 三组unary/前驱/tie，token一致且概率差≤1e-5 | GPU未运行 |
| target采样 | target logits有限；实际GPU采样符合独立host参考；逐位置与逐token路径对应 | GPU未运行 |
| 接受与提交 | 首拒、中拒、全拒、全接受均按最长匹配前缀提交；无重复/丢token | GPU未运行 |
| 真实状态 | KV/GDN/PLE/index与有效输入前缀逐token状态一致；snapshot和提交同步成立；MTP fallback诊断按原合同 | GPU未运行 |
| EOS与预算 | 首个target EOS后无可见输出；max-new不超限；接受输入前缀状态与提交边界正确；结束等待commit完成 | GPU未运行 |
| 实际命中与资源 | DFlash2实际开启、轮数非零、无回退/自动缩cap救场；温度/内存/上下文及原资源门保持 | 六次真实生成未运行 |

任何硬门失败立即停止；不能只忽略整个资格程序的exit1后继续。D1通过也不授权D2、服务移植或生产采用。

## 5. EOS与状态的CLI边界

现有CLI先提交`a+1`个已接受输入行，再把可见输出截断到首次EOS或输出预算。因此终止时，内部已提交输入数可以大于可见输出数。原D0B已将两者分别检查；其早期`FAIL_PREFIX_CONSERVATION`历史记录继续保留。

本合同沿用该终止CLI边界，不放宽EOS输出或有效前缀状态硬门：

- 外显序列必须在首次target EOS处结束，不输出其后的token。
- 草稿EOS不能单独触发终止，必须以target输出为准。
- 实际设备状态必须对应真正提交的已接受输入前缀，不包含被拒绝输入。
- 终止后必须完成`wait_commit`并丢弃本次CLI状态；不得导出、恢复或继续服务请求。

这不证明“可见EOS位置的可复用会话状态”。未来API/Pi接入必须另行验证规范终态、回滚及恢复；DFlash2现有serve guard保持。

现有target-state程序内的MTP draft调用检查fallback状态，不等同DFlash2完整多轮生命周期验收。该程序、CPU宿主EOS检查及真实CLI终止记录必须分别报告。

## 6. 后续执行前置与记录格式

D1P合同复核未修改原GPU程序或runner。D1Q只在新目录构建独立适配副本；原比较器、原binary、runner和历史FAIL保持。旧drafter程序仍会因0.05差异返回exit1，不能直接忽略该退出码。

下一次GPU执行前，必须满足以下前置：

1. 分离完整drafter置信度诊断与所有硬断言，保留原v1判定及原始值。
2. 用置信度差异、错误token、NaN/越界概率、错误shape、target/state/EOS错误验证分类；只有指定置信度绝对差可以继续。
3. 冻结新源码、binary、记录schema、原四组输入/参考、argv/env及新预算。
4. 通过静态/CPU预检后，再按用户单独授权执行GPU硬门；不得沿用旧剩余额度。

D1Q已完成分类适配、CPU正负例、原四组参考身份核对及独立binary封存。源码见[适配目录](../tools/dflash2_v2/README.md)。最终身份为该run的`FINAL_FREEZE.json`，D1命令为`COMMANDS_V2.json`；全部`execute=false`，本轮GPU/生成预算均0。准备阶段的`FREEZE.json`和包含旧D2命令的`COMMANDS.json`仅用于追溯。后续监督器必须绑定最终清单、v2记录和新授权预算；本轮未安装GPU执行入口。

每个结果至少分列`legacy_v1_numeric_result`、`v2_confidence_diagnostic`、`v2_hard_gates`和`D1_v2_qualified`。硬门未运行时，`D1_v2_qualified=false`；置信度诊断不得单独使其为true。

本合同不继承GPU执行权限。生产保持停机，恢复等待用户明确要求。

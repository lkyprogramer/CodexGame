# Greedy proposal + Target production sampling统一合同

状态：PROPOSED_FOR_NEW_ROUTES。B29已有MTP3，源码已有deterministic proposal接受机制；换名称不是新优化。本轮不实施，不改现网参数。

Target固定temperature=1、top_p=.95、top_k=20，Pi medium/max_tokens=32768；固定tokenizer/template/权重/codec与该版本支持的processor顺序。greedy只指proposal选token，不指Target采样。Lookup、扩宽、DFlash2、检索可有不同来源，均使用同一Target权威。

## 概率与最终前缀

processor/temperature/top-k/top-p后的Target概率为p。deterministic proposal d的q=delta_d，接受p(d)；拒绝后从去掉d的Target残差重归一化采样；全接受bonus按合格规则。不临时近似或裁剪Target支持集。stochastic draft若没有真实条件q与独立接受/残差证明，不能套用q=delta公式，只能限定为确定性草稿。

每位置Target logits必须基于最终融合前缀；不能Lookup替换一列后用旧MTP前缀验证后续列。只有实际版本支持的penalty/mask/schema才纳入实现，并需按对应前缀/支持集验证，不从其它引擎猜功能。零/一概率、空残差、top-p边界及浮点规则由独立参考与负例固定。

## RNG、许可与state

固定RNG消费/残差/bonus、stop/EOS、尾轮remaining1/2、cancel/partial permit和下一轮衔接。anchor、accepted drafts、显示token、bonus与commit_columns分别定义；禁止散落accepted+1。correction只记录同一计算点，不拥有采样或许可权威。正式state/conv/slot/epoch只有已许可列可提交，取消/错误不能二次fold。

逐bit raw/state/conv/verify与分布级Target资格均需；单seed文本相同不是分布证明，分布正确也不是状态证明。只有真实production-sampling命中route才授予该路线资格；greedy-only或总fallback不能冒充。

## 最小验证与扩展

首个Lookup默认C1/W4、K≤3；它不是W8/DFlash2的必经前置。W8先验证整条MTP/Attention/GDN/Graph能力；W16复用W8技术证据。GDN支持T≤16本身不够。DFlash2需匹配27B资产，全局feature检索需匹配feature/位置/状态身份，utility只选择合格route。

索引、append、搬运、草稿、verify、mandatory alignment、commit、fallback和策略开销全部进入完整round/service成本。接受长度不是净吞吐，α模型只作条件算术。详见[H1-T07](../plans/tasks/H1-T07.md)、[预算](../plans/08-validation-budget-and-estimate.md)。原始采样推导见[历史合同](../baseline-v3/design/11-sampling-acceptance-and-proposal.md)，历史依赖不恢复为当前待办。

旧Baseline及97fc7be6/Gson/RE003原成绩与缺口不变，不重发、不重跑grader、不用缩减输出或context掩盖失败。

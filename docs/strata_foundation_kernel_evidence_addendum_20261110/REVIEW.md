# 增补包独立审阅与修订记录

范围：文档、缩小CPU教学helper与交付检查；非产品实现、非GPU资格。reviewer不审自己撰写的章节作为唯一证明。

## 第一轮发现并修正

| 问题 | 修订 |
|---|---|
| ENGINE-COMPONENT来源链接误在根目录 | 改为固定树的packaging/ENGINE-COMPONENT.md |
| START与E0的三个输出文件不一致 | 统一reports/kernel-evidence下三份canonical文档 |
| 新observability默认路径与原包不一致 | 统一<LAB_ROOT>/lab/observability；禁止并列第二树 |
| 位置完整但乱序会影响上游first-departure delta | 默认POSITION_ORDER_MISMATCH，禁止暗排；加入stock行重排负例 |
| 仅set/TSV/meta无法证明实际forced输出 | 加实际emitted-token receipt引用，缺证据FORCED_OUTPUT_UNPROVEN，不自动补跑 |
| 只检查finite会放过有限但非法的分数 | 明确logp域、top2排序/ID、同token同分数、margin与格式ε，加入负例和tie阳例 |
| diagnostic角色可能覆盖硬路径拒绝 | 角色和observer资格分字段；改图REJECTED，未知不晋升 |
| 笼统拒绝timestamp=0可能误伤相对原点 | 按backend/schema无效sentinel判断，合法相对原点保留 |

## 独立CPU测试发现的附加问题

| 额外负例 | 根因与修正 |
|---|---|
| logp=10**400令教学guard崩溃 | math.isfinite隐式转float溢出；显式安全拒绝不可表示score |
| emitted浮点token被当整数 | Python数值相等不等于严格类型；先验证list[int]与词表域 |
| 空或False预算被当0 | 空any为false、bool等于int0；验证完整键集合与type is int |
| JSON 1e999变成Inf | parse_constant不覆盖合法指数溢出；增加有限parse_float |

以上4类由tester独立构造，implementation owner以5项新回归先重现，再逐项修复；没有将其当作真实Strata缺陷。

## 独立复核状态

- 观察器/数值合同reviewer：已复读04/06/08/09与计划相关修订，并静态检查教学helper/tests；确认其三项问题已解决，未宣称自己重跑过单测。
- 源码/计划reviewer：已定向复读五项修订，全部RESOLVED；额外确认诊断角色/资格分离与E0→E4阶段顺序一致，无新增文档阻断。该reviewer未运行单测。
- 独立CPU tester：首次独立运行45项、文档validator及3项probe后追加恶意输入，发现并报告上述4类缺口。修订后独立重跑50项（exit0，无失败/跳过）、validator（exit0），并重验原恶意输入，全部RESOLVED。该轮manifest尚未冻结；最终hash/ZIP由交付方另验。不能代替真实parser或GPU测试。

主代理先后实际执行45项与最终50项单测，另见VALIDATION和原始输出；“有独立review”与“独立执行测试”分开登记，不冒充同一件事。

## 保持不变的局限

不能证明4090提速、当前生产已加载哪个binary、O0–O6已实施、counter权限已可用、完整模型/长上下文正确。不能因为审阅通过而重开F02、DFlash2或任何旧关闭方向。

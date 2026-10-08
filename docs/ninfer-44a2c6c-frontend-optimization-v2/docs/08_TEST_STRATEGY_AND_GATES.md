# 08 · 测试策略与 G0–G7 验收

## 8.1 分层，避免“辅助测试全绿=产品完成”

L0本包工具/有限词法模型：无需NInfer资源，确认资料和算法推理的一部分。L1固定版真实C++frontend oracle差分：真实词表/模板与有限合成词表，验证tokens及错误。L2原工程接线与CTest：count/text/vision/prepare_tokens/计数。L3节点29 CPU：同资源同输入可复现实测。L4 4090 HTTP：维护窗口对照与回滚。L5生产只读观察。

**L0通过不替代L1–L5。review-assets不是现网完整产品验证。**

## 8.2 独立oracle与case集合

reference应从44a2c6c真实旧实现构建，保留全processor函数，不使用评审简化B0支路作oracle；明确源文件blob/编译器/链接对象。可共享未改变unicode库，但新旧scanner/resolver必须隔离。

测试至少包含：

| 组 | 输入/动作 | 必须相等的内容 |
|---|---|---|
|added selection|earliest不同ID、同位真实prefix、反转ID、相邻/重叠、空词表、特殊token flags|tokens/选中序列/异常|
|普通文本|空串、ASCII、中文、组合音标、emoji、长路径、JSON、NUL、随机字节|tokens/UTF8错误|
|boundary|≤256bytes选定样本每个cut、cut0/full/outofrange、中间UTF8、added内部|optional值/完整异常|
|hint|同offset不同kind/allow_full、重复、非单调、user0|列表kind/顺序/重复/错误顺序|
|trace|空输入、parsefalse、只普通段、added末尾、copy/move/并发|原tokens与trace合同|
|prepared|同模板/两种模板资源、thinking开关、preserve、tool与多media展开|types/positions/identity/count|
|长形态|H约5/20、H约384仅stress、new user重置recent段|全部前端输出与局部工作量|

输入清单在[data/adversarial_cases.jsonl](../data/adversarial_cases.jsonl)，映射在[test-matrix](../data/test-matrix.json)。不可执行的生命周期B2案例放deferred，不计首期覆盖率。

## 8.3 随机差分与最小化

固定seed，至少20,000次变换：插入/删除/截断added标记，产生不完整标记，加入NFC combining与非法UTF8，插入重复和乱序边界，切换parse_added_tokens。每次比较独立reference与真实candidate；差异输出hash、种子、变换序列、异常phase/class/message和首个不同字段，最小化后的失败case加入固定回归。

对有限短样本的全部byte cuts逐一验证，不声称穷尽所有可能256bytes字符串。至少真实词表一轮、合成字节词表一轮；资源不在场记BLOCKED，不能只运行Python词法模型后宣布G1通过。

## 8.4 Gate 定义

| Gate | 通过条件 | 不充分证据 |
|---|---|---|
|G0 来源|全commit/blob核验；实际overlay diff/hash、完整imageID、六资源SHA256和编译环境冻结|短镜像ID/短SHA前缀/浮动tag|
|G1 精确等价|L1全部固定cases+有限全cut+≥20k变换0失配，prepared/error完整合同；reference隔离|主tokens相等而hint/错误未比|
|G2 工作量|主编码1次；B0外层扫描位置≤该调用输入B；无每命中全后缀find；局部字节和memo显式计数|只看运行时间或给estimated bytes当DRAM|
|G3 接线|原frontend测试、count/prepare_tokens、shared vision展开、copy/move/并发与schema回归通过|仅复刻bench没链接产品|
|G4 CPU性能|节点29匹配环境，约900KB/H5与H20形态：≥7次计时p90≤1s；与配对legacy主参考下降≥95%；短请求无显著回退|只满足相对80%或不同资源/输入|
|G5 HTTP维护|同资源/采样/容量的配对会话、多轮append、cache/computed/prompt/协议保持，无新增错误；测残余TTFT|只跑TG128/数学结果或超过262K输入|
|G6 发布/回滚|明确授权、固定新旧imageID、旧镜像可启动验证、配置保护、只读观察与退出条件|生产shadow、修改L2顺带提速|
|G7 独立审查|另一审查者核对代码/证明/所有门证据，无未关闭阻断项|作者自检当独立review|

G7用于T13；G6含T12动作必须在G7前置批准后执行，报告可分“G6 ready”和“G6 executed”。不因G6尚未执行否定部署前review，但不把ready写成发布成功。

## 8.5 性能细则

G4的1秒是节点29/实际资源/约900KB主形态的工程目标，不是任意硬件或任意字典普遍性能保证。合成语料H/bytes实际渲染后冻结；复现评审的超容量样本属于CPU-only。若宿主明显受到业务干扰，标`INCONCLUSIVE_ENVIRONMENT`重排试验，不放宽门假装通过。

短输入paired median允许上限`max(1.05×baseline, baseline+0.001s)`，同时要求p90无稳定退化；<8K不同结构分别报告，禁止用全局平均抵消某种极端变慢。≥7重复在new candidate侧；长legacy可至少3次交错配对并保留每次原始数据，报告两个样本量不同，不能虚构legacy p90稳定性。

G2不要求所有局部区间≤16bytes；对主生产形态记录分布，stress大普通段仍需正确。B1无安全added切点时性能可退回局部从0编码，这不允许删除验证。

## 8.6 HTTP 深度和输出预算

至少32K、128K、192K、240K四档，精确input token数以真实frontend校准，保留>=2048输出余量。一次完整冷请求后追加4–8个tool回合；模型实际输出导致分叉时，为cache对照应使用固定历史请求的离线冻结回放序列或逐条记录差异，不把不同生成历史当同input。

比较prompt/reused/computed tokens、模型/工具协议、first meaningful delta、server prepare/prefill/queue/restore、decode、内存/错误。随机sampling不要求文本逐字相同，但前端token序列必须相同；需要检验greedy输出时另列受控lane，不能代替medium生产lane。

## 8.7 失败处置

任何tokens/metadata/错误合同失配：停止性能比较与发布，缩小case，回到对应任务。新增GPUcache miss：先比较提交token是否一致，再看干扰/路由；禁止更改cache参数掩盖。HTTP超时且CPU优化已生效：归因其他阶段，不能声称B0/B1失败或自动扩B2。

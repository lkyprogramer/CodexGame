# NInfer 增量架构与状态合同

## 1. 基座与隔离

基座是`44a2c6c...`。新分支命名`lab/extreme-v2-*`，每次只进一类变化。donor `Neroued@b88c0f6...`只作算法/数据布局参考；禁止整棵merge带入Blackwell、格式和无关调度变化。先写`port-manifest.json`列文件/符号/依赖/许可证/排除项，再移植。

## 2. 执行层划分

```text
Frontend（模板/工具/stop/最终可见输出）
     ↓
Engine（lane、队列、cancel、资源提交）
     ↓
Proposal policy（只读已提交历史+历史统计，选来源/有效宽度）
     ├─ MTP existing
     ├─ Suffix/lookup deterministic chain
     └─ DFlash2 conditioned stochastic chain
     ↓
Target Verify（同主模型、同目标sampling pipeline）
     ↓
Rejection / correction / bonus
     ↓
Frontend preview → PartialCommit N
     ↓
Target KV + GDN + hidden + selected draft state原子提交
```

这里只定义接口职责，不声称44a已有所有接口。计划中的类型见`contracts/proposal_contract.h`，具体实现落在family runtime，不能让工具代理修改target状态。

## 3. Frontier不变量

- `F_target`：target已经消费的token数量；anchor是已被target采样授权但尚未forward消费的下一个token。
- `F_draft`：draft conditioning/materialized context覆盖的frontier，不等于候选token个数。
- `licensed`：target本轮授权数；`committed`：经Frontend stop/EOS/cancel后实际提交数，0≤committed≤licensed。
- 所有checkpoint同时拥有tokens/position、KV、GDN、hidden、draft conditioning和对应format/profile身份。不能只存KV。
- 输出先发布再回滚状态是禁止的；Frontend preview决定N以后，commit成功才能发出对应token。

## 4. 切换proposal来源的真正成本

Suffix**取代**某轮MTP草稿后（T06 v2），MTP的private KV、hidden/位置不可继续当作已覆盖accepted suffix。必须使用已提交target hidden重建/bridge，或者清理该draft缓存并走受控catch-up。DFlash2也必须捕获并materialize实际接受span。catch-up耗时属于下一轮真实成本，不能从suffix成绩里删掉。T06 v1（链延长，`06 §2`）不触发这一段：MTP仍产出并消费自己的3个草稿，suffix只在其后追加，被拒即作废，MTP状态与现网相同。

因此首版只允许固定驻留MTP+CPU suffix；另一进程profile固定驻留DFlash2+CPU suffix。**不默认同时驻留MTP和DFlash2三路动态切换**，避免24GB预算与状态复杂度爆炸。

## 5. Physical W 与 live Q

K=proposal数，W=K+1含anchor。一个图的物理W固定；临近输出预算/容量时，live proposal P≤K、live target Q=P+1。maskeddraft的物理W和target的liveQ不可共用一个长度变量。无效列不得污染GDN或KV。W4/6/8/16是不同经过验证的execution profile；首版不允许在一个CUDA Graph里任意重排shape。

## 6. Cache身份

新checkpoint加`state_schema_version`、target artifact hash、companion hash、codec/layout、proposal regime和ring coverage。能安全兼容的MTP旧checkpoints由明确迁移函数处理；否则失配miss并重算，禁止“为了命中率”偷用旧状态。

## 7. 不做的架构变化

不增加多GPU、不加入MoE、不改变主模型层数/有效attention窗口、不把草稿SWA=2048应用到target、不让CPU source estimator读取未来reference completion。控制端/服务端统计独立于推理状态；指标失败不能改变算法答案。

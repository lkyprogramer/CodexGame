# 极致优化的搜索空间与止损

## 1. 搜索目标：一个带约束的前沿

把候选按 `(quality,state correctness, capacity, task wall, coldTTFT, hotTTFT, decode, RAM/VRAM, maintenance)` 比较。不同cap/codec/主权重的点允许形成Pareto前沿，不做一个无权重定义的“9.4分”。生产默认优先不退化能力；copy-only profile可单独存在。

## 2. 有界搜索

Suffix最小匹配{8,16,32}、K{3,5}；先总共6个合法组合。DFlash先K3与K7/固定q精度，不同时扫15个K、三精度、四KV。wide kernel每次只改一个资源策略；每个候选先op，再round，再request，再task，失败留证并撤销。

实验不能只优化cached synthetic复制。调参12轨迹，heldout8轨迹；每次选择参数都记录train score，禁止查看heldout错误后反复手调仍把它叫heldout。需要更多调参时生成新验证集，并重新标记旧集已污染。

## 3. 停止与重新排序

带本机数字的停止点（推断值来自`22 §4`，可复算）：

- **T07 W8路径门**：`Δ_w8`（184K下T=8比T=4每轮多出的attention耗时）与固定成本≈2ms/轮相加，除以现网184K轮时≈29ms，得到DFlash2必须多提交的比例；若模型卡AL增益（+8.8–20.1%）的下界覆盖不了它，DFlash2链（T08–T10，6–10周）不启动，只保留可行性结论。
- **Suffix v1**：copy/rewrite桶收益95%下界<10%或`suffix_hit_rate`过低：保留off，不做v2 bridge，不扩大为suffix tree重写；其命中率同时决定W16是否值得。
- **DFlash2同K**：若只在K=3比较且净收益落在0–12%区间内、与噪声底重叠：不以同K结果推进，必须以K=7/W8比较。
- **DFlash AL高但step更慢**：先确认width route/conditioning/head/catchup/持久化恢复，而不是盲目更低bit draft。
- **W8/16无全round收益**：保留small-T，容量/稳定性比kernel单项更重要。
- **d256 prefill**：nsys测得attention占冷prefill的f<0.3时不投（Amdahl上限f=0.45、s=1.6才≈1.20×，即184K TTFT 94s→~78s）；精度门失败则回退target算术不变的调度优化。
- 只出现偶发近史branch cache miss：按真实流量频率×损失估计，再决定anchors；报告12不是默认加8checkpoint的理由。
- **任何线**：主桶配对<8或A/A噪声底>3%时不得下结论，先修测量链。

## 4. 研究预算是开发决策，不是承诺工期

A观测/控制实验可以在已有环境有界推进；Suffix/MTP状态接线、DFlash2迁移、d256 kernel均是独立工程工作，不是一小时测试。量级（推断，`22 §4.8`）：T00–T03 1–2周；Suffix v1 2–4周；DFlash2链6–10周（含会话持久化新功能）；W16 2–4周；d256 4–8周；串行约4–7个月一人。每阶段以产物/验收界定完成，不在未测GPU之前写固定“提升60%”承诺。预算耗尽时提交可复现失败/剩余工作，允许结束，不必须“换引擎来证明方向”。

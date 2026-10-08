# 精确投机采样与计数合同

## 1. 目标分布固定

本包所称“无损”是**相对于同一数值profile的target分布**保持语义，不是相对于原始BF16模型绝对无误差。当前target本身有权重量化、A8 prefill和rk4 codec。不能用“投机精确”证明target量化无损。

`p_i`必须由同一目标管线得到：有效vocab mask → grammar/请求约束 → 已提交历史和本轮此前accepted tokens的penalty → temperature → top-k/top-p/min-p → normalize。顺序与现网一致，不能按本文文字替换已有源码顺序。`q_i`是实际采样出当前draft token的条件分布；它可以与p support不同，但不能是事后重算的近似q。

## 2. 正确拒绝采样

对候选d：

```text
q(d) > 0
accept_prob = min(1, p(d)/q(d))
if accepted:
    emit d provisionally; continue to next candidate
else:
    r(v) = max(p(v)-q(v), 0)
    correction ~ normalize(r)
    finish this round
if all P candidates accepted:
    bonus ~ p_P
```

**44a已经实现了上面这段的one-hot情形**：`src/ops/kernel/speculative_round.cuh:60-68`注释明写T>0时"distribution-correct speculative rejection sampling … one-hot (greedy) draft: accept with p_i(d), resample from masked residual on first rejection, bonus from last column"。现网MTP（NativeMtp）和Suffix链延长（PointMass）都走这条已有路径；T04的工作是为它建立oracle回归并**只为Sparse16扩展**，不是重写验证器（`22 §2.2`）。

Suffix首版采用**确定性chain**：`q_i=δ_{d_i}`，不把后缀树频率当q。于是accept_prob=p(d)，拒绝时把d质量从目标中移除并归一化。tree频率仅供是否选这条chain的策略评分。未来若随机从多个suffix候选抽样，才需要精确定义并保留每步实际q。

上游DFlash2的q是top16 selector沿实际前驱的条件softmax，不能拿unary top16概率替代；全局token映射、valid-vocab、温度和FP32保存精度有合同。[S01]

## 3. 不能用“同seed输出一样”替代分布验证

speculation改变随机数消耗方式。要求：
1. 同一算法profile、同一seed、同样请求及调度扰动后结果可复现（若现网承诺）；
2. p/q数学oracle对枚举小词表精确；
3. 大量固定条件样本统计与target一致；
4. 不要求不同算法使用同seed逐token相同，除非专门实现位置/用途独立counter RNG耦合。

每个draw绑定`request_seed, logical_position, rng_purpose`；proposal、accept、correction、bonus用途分离，不用lane或compact batch row当随机key。拒绝重试、取消重发、宽度切换都必须测试。

## 4. Greedy合同与有限精度

greedy按目标tie-breaking规则验证每个candidate。不同矩阵宽度可能更换GEMM/reduction，产生near-tie翻转；这不应直接掩盖为“统计噪声”。比较**同profile target verify**与逐步target logits，定位首个差异；若改变target数值路径，就独立标记numeric variant并增加oracle/质量测试，不再称bit-equivalent补丁。

## 5. 停止、partial commit、缓存

每轮先算licensed token数组，再由Frontend preview返回N。EOS/stop/max_tokens可截到中间，cancel可N=0。commit只前进N，只有N对应的target KV/GDN/hidden可见。checkpoint前同步pending draft conditioning到同frontier；未接受draft和未来teacher答案不进入suffix index。

## 6. 必做反例

- p/q support不重合；p(d)=0；q(d)极小；p=q无拒绝分支；top-p后归一化；重复token合并；有效vocab末端和无效padding；proposal shortlist不含target top1。
- 在chain第0/1/末尾拒绝；全接受；输出剩0/1/K；EOS在accepted中间；stop跨token边界；网络取消后重试。
- 文本里形似tool JSON但未触发tool_call；真实tool_call的arguments跨SSE帧；thinking关闭/medium；penalty作用于本轮accepted前缀。
- baseline已有256K历史、只追加1token；prefix中间变1token；A/B/A session；换proposal backend后旧cache应明确miss或经过已验证迁移。

`tools/sampling.py`提供有限词表**解析式**oracle并经过CPU测试。它不是GPU算法实现，也不构成真实端到端验证。

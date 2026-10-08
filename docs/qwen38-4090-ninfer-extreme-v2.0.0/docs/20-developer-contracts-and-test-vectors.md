# 开发落地合同：源码改动、状态向量和验收数据

本章补足任务卡的公共接口。以下文件是**计划实现**，不得因为本文有类型/算法就报告引擎已完成。T01先注册验证器；每个未接入的case返回77。后续task只在真实测试通过后替换对应case。

## 1. 一次round的顺序不能改变

```cpp
// Architectural pseudocode: map these responsibilities to the fixed 44a owners.
auto origin = policy.choose(committed_history, completed_round_statistics);
auto proposal = proposer(origin).propose(anchor, state_frontier, requested_extent);
validate_request_identity_and_q(proposal);
auto target_rows = target.verify(anchor, proposal.tokens, proposal.live_extent);
auto licensed = reject_correct_or_bonus(target_rows, proposal.actual_q, request_sampler);
auto decision = frontend.preview(licensed);  // may stop inside a block
state_owner.commit(target_rows, decision.committed);
proposer(origin).retain_only_committed_features(decision.committed);
suffix_index.ingest_committed(decision.committed_tokens);
publish_to_client(decision.visible_output); // only after successful state commit
```

`state_owner.commit`必须绑定同一request、轮ID、前置frontier，拒绝重复commit。`licensed`可以包含EOS等控制token，`visible_output`未必同长度；指标分列，不能把显示字符数作为提交token数。checkpoint捕获前先完成draft conditioning catch-up。若catch-up失败，不能发布看似可恢复的checkpoint。

## 2. ProposalBatch所有权与生命周期

实现`contracts/proposal_contract.h`时补入：request唯一ID、target profile hash、round ID、RNG namespace、global token mapping和buffer generation。不能使用指向下一轮可覆写scratch的悬空q视图。

| q_kind | 内容 | 禁止做法 |
|---|---|---|
| PointMass | 每个位置的确定token；q(d)=1 | 把suffix频率冒充采样q |
| Sparse16 | 实际前驱row上的global IDs + FP32条件概率 | 使用unary分布、未选前驱或事后BF16重算 |
| NativeMtp | 明确委托既有MTP owner的分布/验证对象 | 先丢弃MTP q再假定其为onehot |

显式validate：IDs范围、无重复或正确合并重复项、q有限/非负/和为1、实际抽中的d在q正支持上、liveK≤物理K、targetfrontier相等。已知病态输入返回错误，不加epsilon后继续生成。

## 3. 可直接转成单测的拒绝采样向量

| p | q | 关键预期 |
|---|---|---|
| [.7,.2,.1] | [.2,.7,.1] | 接受质量[min]=[.2,.2,.1]；拒绝质量=.5；残差=[1,0,0]；最终边际=p |
| [.7,.2,.1] | [0,1,0] | suffix候选1接受概率=.2；拒绝残差=[.875,0,.125] |
| [1,0,0] | [0,1,0] | 必拒绝，纠偏0 |
| [.25,.75] | [.25,.75] | 全接受，残差零只表示不可达拒绝分支 |
| [0,.5,.5] | [.5,.5,0] | 支持不一致合法；零p候选必拒绝 |

CPU解析式oracle已在`tools/sampling.py`。GPU统计测试固定p/q而非反复运行27B：不少于100,000次draw，记录每bin计数、预期值、预登记置信区间和零支持违例。再做有条件的两步小词表树，第二步p/q依赖第一步token，枚举所有路径；这样可抓到“总是读上一行q”的错误。目标侧top_p、top_k、penalty、grammar分别提供测试向量，沿实际现网顺序处理。

统计测试不是完整分布正确性的形式证明。必须结合公式、RNG用途分离、条件索引和状态审查。不要事后调阈值直到通过。

## 4. 位置与状态测试矩阵

| 输入维度 | 必选点 |
|---|---|
| proposal长度 | 0、1、3、5、7、15；只启用当前任务已实现的上限 |
| 首次拒绝位置 | 0、1、最后一枚；另加全接受 |
| output预算 | 0、1、2、K、K+1 |
| paged KV边界 | page_size−1、page_size、page_size+1；从运行时读取page_size，不硬编码另引擎的64/784 |
| DFlash ring | 2047、2048、2049、4097；绝对位置不得按ring物理索引替代 |
| cancellation | proposal前、verify已排队、verify完成、Frontend preview后、部分文本已发布后 |
| 会话 | A→A追加、A→B→A、最新user改写、老分支回退 |
| 执行 | eager、已warm CUDA Graph；捕获期统计独立 |

一次取消不允许撤回已经成功提交/发布的旧轮；只撤销尚未提交的provisional尾巴。取消后的恢复起点取最近合法commit，不按HTTP已经收了多少字符猜测。

状态dump必须记录目标KV有效区、GDN、hidden、draftprivate、frontier、token历史和cache身份。比较有效区域，不比较未初始化padding/ring过期字节。padding guard另做越界写测试，不能用“padding不比”掩盖越界。

## 5. d256 attention的独立数学参考

固定一层真实捕获的Q与**按现网codec解码后的**K/V，CPU FP64或可信参考计算：

```text
q_head h -> kv_head floor(h / 6)    # 24 Q heads / 4 KV heads
score[i,j] = dot(Q[i,:], K[kv_head,j,:]) / sqrt(256)
allowed = j <= prefix_len + i      # 当前chunk的绝对causal对齐
O[i,:] = sum_j softmax(score[i,allowed])[j] * V[kv_head,j,:]
```

这里不代替target已有RoPE/gate；oracle输入必须位于同一个数学边界。两半128维的dot可以相加得到完整score，然后只做**一次**softmax；两套softmax再拼输出不等价。

测试非连续物理页、最后一页不满、prefix≠0、Q长度1/7/8/16/512/1024、所有6个共享Q头、全mask拒绝、极端logit、NaN输入策略。地址计算使用64位，增加跨2GiB虚拟跨度的受控测试，不能只在小连续tensor上通过。

## 6. W8/W16资源合同

不要只改`constexpr max_tokens`。T07/T12需要审阅以下链路并输出`width-audit.json`：

```text
CLI/config bounds
  -> model round geometry
  -> live extent / causal mask
  -> launch dispatch + compiled template instances
  -> split partial / reduction workspace
  -> ReplaySSM record capacity
  -> logits + head workspace
  -> CUDA Graph captured extents
  -> checkpoint/partial commit metadata
```

每个节点记录旧界限、新界限、源码位置、负测试ID和实际分配bytes。T7/T8专用kernel还未优化时，可以合法genericroute验证功能，但route必须公开；不能将genericroute的速度当作最终优化潜力，也不能“应该走TensorCore”而没有实际kernel名字/计数。

## 7. 验证器结果Schema（T01实现）

```json
{
  "schema": "ninfer-lab-validation-v1",
  "case": "t07",
  "status": "NOT_IMPLEMENTED",
  "source_commit": "runtime-lock里的实际candidate提交",
  "target_sha256": "运行模型的实际hash",
  "profile_sha256": "规范化运行参数hash",
  "executed": 0,
  "skipped": 0,
  "gpu_executed": false,
  "assertions": [],
  "evidence": []
}
```

上例只展示**未实现**的合法结果，进程必须退出77。PASS要求executed>0、所有必须assertions实际运行、evidence文件存在/hash匹配；必须GPU的case要求gpu_executed=true。验收AI核查rawlog和可重现命令，不信任一个手写PASS字符串。

## 8. 完成一个task的必要交接

交付最小diff、变更前后测试日志、首次失败原因、当前通过证据、命令退出码、环境锁和下一任务需要的签名。新测试应在去除关键实现时失败；不要求把真实生产反复改坏，使用独立worktree。T01的case registrar是测试入口，不是把所有断言藏入一个JSON生成器。

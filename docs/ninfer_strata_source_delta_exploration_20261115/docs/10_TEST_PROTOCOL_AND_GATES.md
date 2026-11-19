# 统一测试协议：从资格到真正净益

本文门槛是本增补提议，需R0冻结和用户硬件授权后才生效。Strata继承旧冻结合同；NInfer不能凭Strata已经认可的统计工具/门槛直接取得资格，必须审核其适用性。**本轮所有引擎/GPU/HTTP项均NOT_RUN。**

## G0：身份与去重

- 当前源码、dirty diff、binary/model/tokenizer/codec/config及实际调用路径齐全；baseline不是网页main。
- 旧关闭ID、具体变化和不再重复内容明确；H2不标新，K-PAIR不跳级，M0不重写。
- oracle/holdout/样本单位/统计方法/预算/适用任务在观察结果前冻结。
- 基础包collector尚未实现或未在此身份合格→BLOCKED，不假设已经拥有归因能力。

## G1：离线机会门

D1：至少三类各20个已有授权真实任务轨迹；只用task级划分，开发集与holdout不共享近重复文件。基准B1和B2使用同来源集合、同W；不能把source扩容与anchor混成一个因果。无真实轨迹可先跑纯CPU反例，但结论只能“planner合同可实现”，不能过机会门。

H2：当前真实draft hidden与head身份，head-only分项；sidecar峰值可行。建议首版top1 recall≥99.5%，分语言/代码/工具切片全部报告；此门不是Target质量结论。没有真实hidden则资格未建立。

成本门：有测量依据的保守估计净耗时下降需≥正式采用门+1个百分点余量；默认正式门4%，故筛查目标≥5%。未知catch-up/同步/分配不可填0。仅有乐观上界可排除无机会，不能用上界“通过”候选。阈值是本包的保守设计，不是经验测定的GPU规律。

## R2 / R3：分层资格，不共享一个PASS

Phase的G2只对应R2的CPU/build门；以下模型数值、混合状态与服务项属于R3的G3，不允许由CPU通过自动解锁。observer也在同一R3资格门中独立判定。

| 层 | 必须通过 | 不代表什么 |
|---|---|---|
| CPU planner/schema | exact token匹配、hash碰撞、编辑、失效、budget缺失、fail-closed | model正确或GPU加速 |
| 原算子数值 | H2选中行沿原Q4 oracle；D1不动Target数学；NaN/Inf/越界为硬失败 | 自然语言任务质量 |
| Greedy模型 | 相同输入/target规则，逐token及必要状态与已资格参考一致 | sampled自动无损 |
| 混合状态 | 拒绝各位置、cancel、EOS/remaining、KV/GDN/conv/hidden/MTP/position/ledger、保存恢复一致 | 端到端更快 |
| 服务 | 首请求、短追加、完整cache恢复、终止后下一turn、非copyfallback | 任务质量或采用 |

为了减少GPU窗口，CPU用所有W内位置组合；GPU仅跑冻结的最小代表集合与已知边界。已有同身份有效证据可以复用，不为本包重复同一套功能测试。

### 采样正确性硬约束

保持Target不变只是必要条件。若原系统为target sample-and-match，每个真实前缀应按原规则抽Target token，target RNG不能被proposal次数消费；如果走p/q acceptance，q必须是实际proposal（含copy/shortlist/重打分/截断）诱导的条件分布，拒绝residual也必须正确。不能把确定性copy当原neural q，不能沿用改造前的q。

未单独合格时本包候选仅对greedy开启，sampled请求走旧baseline。不得借此重新跑旧随机MTP/exact-q关闭路线。改变batch几何可能改Target浮点结果，扩大W必须另签合同，而非用“Target权重没变”免验证。

## G3：观测中性资格

复用原foundation规则及collector：相同身份与输入对比observer-off / on，observer只诊断，不作为正式获益样本。以on/off耗时比CI [L,U]：

- U≤1.01：qualified；1.01<U≤1.03：仅diagnostic；U>1.03且L≤1.03：inconclusive；L>1.03：reject。
- 身份、Graph、同步/内存语义变化为硬失败，优先于上述数字。
- 正式产品收益一律observer-off；hot-path低基数必要统计也要纳入模式身份。

trace合格不等于所有字段准确；missing、DROPPED、UNSUPPORTED会降低归因层级。CUPTI-HES不可用于4090，不为HES升级驱动。

## G4：预注册正式配对

仅一个候选，六个fresh-engine配对，顺序 `AC / CA / CA / AC / AC / CA`。每对跑同一份冻结任务清单与顺序，每引擎启动条件、cache策略一致；不得后台并跑。A是实际合格baseline，C只有一个改变。开始前冻结任务权重，copy-only提升只能称copy-only。

- 样本单位是完整run block / engine pair，不把token/round当独立样本放大N。
- 每pair的主指标为固定任务集合的加权总完成wall C/A；诊断另外报告decode ms/committed token、tokens/round、TTFT、输出长度、peak资源、CPU和每context/任务分层。
- 复用冻结的paired-log bootstrap，六pair的有放回重采样可精确枚举6^6=46656；95%CI定义/分位算法/权重必须由spec绑定同一实现。
- 对主耗时比上界要求 `U ≤ 1 − max(0.04, 2 × AA_noise)`。AA_noise由同合同既有有效A/A记录或另批资格给出；缺失不能填0。
- 非copy guard、TTFT和其他预注册守护指标的耗时比上界≤1.02；长context/Java后半等关键切片不得有已确定方向性回归。样本太少使CI过宽时记INCONCLUSIVE，不宣布尾延迟成功。
- 输出任务质量先通过；编译/单测/工具调用/结构化输出使用既有scorer，新的D1完整文件编辑以预先固定测试/编辑要求判断。仅字符相似度不合格。

六对不足以估计很稀有故障，不用性能通过替代后续生产灰度。预算不足以完成冻结清单时整实验INCOMPLETE，不挑已完成的漂亮子集。

## 固定轨迹与自然任务必须分开

固定token replay可隔离数值/路径成本，但不能证明真实任务耗时；自然生成要保留EOS、长度、质量与完整wall。候选让输出变短或变长均如实报告，不能固定输出裁剪制造“同样工作量”。失败、超时、取消都保留并按冻结规则计入，不仅对比两边共同成功请求。

## 最终状态

`KEEP_EXPERIMENTAL`仅表示此适用合同有证据，非上线许可；`REJECTED`保留负结果；`INCONCLUSIVE`不补第七对；`BLOCKED`等待明确缺失项；`NO_QUALIFIED_CANDIDATE`允许R1正常结束。生产部署另有独立批准与回滚窗口。

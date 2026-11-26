# 10 · R01：last-loop KV容量研究

## 1. 假设与当前证据

假设H-KV：在长上下文下减少重复loop KV的容量，可能让更高质量权重保持GPU驻留或减少KV换入，从而改善完整请求；短上下文未必加速。

Transformers PR51161在A100、eager、2048输入+128greedy输出报告：per-loop dynamic 232.7MiB/3.92tok/s，last-loop dynamic 118.8MiB/3.92tok/s；static由3.80降到3.49tok/s。它证明该设置中KV更省，并没有证明4090更快或任意历史分布等价。该PR在核查时仍未合并。[S11]

## 2. 定义新的目标契约

per-loop把每个pass的历史分别保存；last-loop让早pass读取共享历史，仅最后pass写入长期cache。当前token/当前块的KV仍来自正在执行的pass，conv state继续逐pass保存。改变历史KV可能改变条件分布，故必须新建target_fingerprint，与per-loop分开保存质量与性能结论。

测试分成两层：

1. **实现正确性**：CUDA last-loop实现与同一last-loop policy的reference一致。
2. **模型质量**：last-loop目标相对per-loop目标是否满足预先规定的非劣门。

第一层通过不能免掉第二层；第一次无past forward一致不能证明增量生成一致。

**批次语义是额外的目标风险。** 按“已缓存历史读final-loop、当前块读own-loop”的规则推断，两次B=1时第二个token可能读取前一个token的final-loop KV；一次B=2时则可能读取同块前一个token的own-loop KV。忠实复现PR也不自动保证两者等价，这不一定是CUDA实现bug。

因此R01起步只资格认证**冻结的prefill分区策略 + 单token decode**，关闭spec。固定prefill分区/块内读取规则写入target指纹。`B>1`的last-loop验证保持UNQUALIFIED，直到证明其条件分布等于该单步oracle；若为此改用lagged policy，则是新policy/新目标，不能继续称PR原始last_loop。

## 3. 不与2DSD lagged sharing混称

2DSD的shared_last有lag window `W_lag`：较旧历史读final-loop，近期及in-flight范围读own-loop；要求例如 `R × block_size <= W_lag`，且上游只给特定模型/精度/runner组合。PR的last-loop不能直接作为其替代。`W_swa`是attention滑窗长度，与`W_lag`是两个参数。[S06/S11]

Inkling HF 2DSD结果明确使用per-loop KV；没有本包核实到的Inkling shared-KV适配权重。组合留给R05，不能默认开启。

## 4. 拟新增接口与触点

现有触点：`src/models/inkling2-loop.cpp`、`src/llama-kv-cache-iswa.cpp`、对应hybrid memory类。先完整阅读其位置/滑窗协议。

拟新增：`src/llama-inkling-cache-policy.h/.cpp`，测试 `tests/test-inkling-cache-policy.cpp`。若沿用现有接口更小，允许保持路径不新增，但更新任务记录。

设计接口：

~~~cpp
enum class InklingCachePolicy { PerLoop, LastLoop };
struct CacheAddress { uint32_t physical, pass; uint64_t token, branch; };
struct CacheReadPlan { /* immutable history + pass-local current block */ };
CacheReadPlan plan_history_read(CacheAddress, InklingCachePolicy);
bool may_commit_history(CacheAddress, InklingCachePolicy);
~~~

`plan_history_read`应描述views/segments而非每步复制整个cache。default仍为PerLoop。读写策略还要定义prefill多token块、单tokendecode、B>1验证、SWA覆盖与rollback。

## 5. 试验步骤

- [ ] 冻结per-loop AR与资产/采样/输入，不开启DSpark；导出各pass参考KV和conv。
- [ ] 在独立reference checkout复现PR的dynamic/static行为；CPU或可用后端先做小shape，不把A100速度复测当必需前提。
- [ ] 实现read-only历史视图，最后pass才写长期cache；保持每pass conv与当前块状态。
- [ ] 测长度1、W_swa-1/W_swa/W_swa+1、1023/1024/1025、2048；W_swa来自实际SWA配置，不假定永远1024。启用lagged policy才另外测W_lag边界。
- [ ] 初始B=1、固定prefill策略；用B=2与两次B=1构造目标差异反例。B=2/4/8仅作为未资格研究，先定义并证明目标语义再测first/middle/last reject。
- [ ] 做4K/64K/P128K容量与完整请求A/B，记录减少的是哪些bytes、增加的是多少copy/kernel/同步。
- [ ] 执行质量门且先解决批次不变性后，才单独增加DSpark；重新测接受率、实际目标分布与事务正确性。

## 6. 不可缺的负例

早pass错误写共享cache；conv按physical合并；使用尚未完成final pass的in-flight KV；readonly view返回错误mask长度；static buffer将未使用capacity暴露给attention；reject只缩length没有还原ring；复用per-loop prefix cache；多tokenchunk顺序造成与逐tokenreference不一致。

## 7. 验收与停止

容量收益必须超过新增view/scratch/padding，并在NVML峰值中可见。若仅节省一小段KV且所有权重本来驻留、完整请求无收益，则标 `NO_BENEFIT_FOR_DEFAULT_PROFILE` 的原因，任务主状态用 `NO_BENEFIT`，保留容量实验结果。

出现质量非劣失败、不明确的块内读写语义或过多复制开销时停止。无法证明B>1验证与冻结单步oracle一致，则禁止该spec组合，而不是放宽数值容差。不能为了省显存把该模式伪装成per-loop，也不能把“KV减少49%”描述成总显存减少49%。

R01不阻塞正式Mini per-loop主线。若最终作为特定长上下文profile启用，单独命名、单独cache namespace、单独能力行。

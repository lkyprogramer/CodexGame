# 已有能力与真正增量：避免重新发明

本表是donor研究的适用性校正。外部引擎具有某技术，不代表Strata缺少它；每项先审计当前路径，再决定是否需要新代码。源码以41cf深审、4b9相关文件同blob为依据，详08、P03/P04/P07/P08。

| 名称 | Strata已经有 | 本包真正可研究的增量 | 关联 |
|---|---|---|---|
| CUDA Graph | 整verify窗口、MTP、部分commit和各T图 | graph预算、host前移、地址稳定、无CPU依赖的局部融合 | O25/26/31 |
| 专家多token与激活复用 | 同expert聚合、多token GU/down路径 | 真实格式未覆盖处、pool阶段调度、并行中间量化 | O01/02/05 |
| CPU/GPU overlap | 先发GPU/PCIe计划、CPU pool并行、门铃 | 降关键路径等待，不能简单删sfence/event | O01/08/09 |
| GPU expert VMM | open_segmented/shrink/grow/set_vmm | 跨KV/GDN/MTP/graph/scratch统一lease与资源账 | O44 |
| 专家预取 | RouterLookahead、ForesightSwap、FileExpertSource预取 | 本机预测准度、资源配额、冷专家workload价值 | O11 |
| 成本spec策略 | DraftPolicy context桶、EMA、stale probe、lookup/chain、概率校准 | 检验现STRATA_SPEC_COST；细分长ctx、CPU miss和graph机会成本 | O33 |
| int8 KV融合 | load8_q8直接载入字节与scale并寄存器解码 | 向量化、跨query/page复用、spill与merge税 | O27 |
| split selected-KV | CHUNK=64分块/merge；STRATA_QSA_SPLIT_ATTN int8 TensorCore路径 | 现路径资格/数值验证、segment与query tile、选中页交集复用 | O29 |
| 低比特KV | rotated Q4_0、k8v4及测试入口 | 本机128K质量资格、PR4068 exact-cell、其它未覆盖布局 | O46/47/48 |
| GDN prefill chunk | STRATA_GDN_CHUNKED CUDA FP32chunk32 | 本机有效条件/速度/长state验证；与Volta CHUNK区分 | O19 |
| 差分snapshot | 完整不变页复用、尾页重新复制、donor guard | 更细生命周期、共享/压缩/pinned shuttle、资源竞争治理 | O41/42/45 |

## 对几处donor表述的限定

D10/D11的donor机制是参考实现，不表示Strata需要首次加入split或去量化融合；D16是现有控制器的本机校准与扩展。D06是已有预取的增量。Q2/Q3先验收已有q4/hybrid，再研究新codec。下游AI遇到已有覆盖就标ALREADY_UPSTREAM或转向可证实剩余开销，不以重写代码量证明贡献。

## 数值必须按真实状态类型

Flash-Next verifier的GDN主state为FP32，record_window走gdn_step_norm_multi；不能照搬另一个模型的BF16-state合同。GPU resident与CPU专家的求和/量化路径也不完全相同，改变放置可能从E降N。QSA selected-cell语义不能换成dense attention后再称同一算法加速。

## 性能测量不能改变待测图

STRATA_VERIFY_PROFILE会改变部分分支/fusion行为，不能拿profile构建的时间直接代表生产。正式计时关闭侵入式profile，用wall与实际committed token；诊断trace单独留证。

### Kern pool的准确借鉴边界

Kern固定ff88b4f的`kern-pool`已把paged state与per-sequence state纳入同一physical-chunk预算，以Lease持有，并可将空闲page/slot的backing经VMM remap互转。draft/MTP只有在manifest声明为这些state时才参与；活跃lease不会被抢占。pool在host产出Copies/Remap，runtime执行CUDA动作。它**不是**覆盖expert weight/cache、CUDA graph、通用scratch的全局动态预算器。本计划借鉴显式状态所有权和映射合同，跨上述资源的统一lease是Strata上需另行设计的工作。

来源：[Kern pages.rs](https://github.com/pegainfer-project/kern/blob/ff88b4f24e3a455491af02bedb1639bde6a56b88/crates/kern-pool/src/pages.rs#L1-L70)、[chunks.rs](https://github.com/pegainfer-project/kern/blob/ff88b4f24e3a455491af02bedb1639bde6a56b88/crates/kern-pool/src/chunks.rs#L1-L23)。

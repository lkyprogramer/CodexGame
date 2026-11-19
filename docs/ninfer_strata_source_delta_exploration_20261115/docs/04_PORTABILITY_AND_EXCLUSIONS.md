# 04 — 4090可移植性、条件状态与明确排除

本包目标是为现有NInfer/Strata找到**机制差量**，不是更换生产引擎、量化格式或重新做一轮泛benchmark。
RTX4090 24GB与64GB host RAM是硬件约束；当前部署SHA、模型、codec、flags、sampling与服务路径仍须先绑定。
所有实验资格、顺序、预算、停止条件与通过标准以[统一协议](10_TEST_PROTOCOL_AND_GATES.md)为准，本文不另立GPU门。

## 1. 只使用四个状态槽位

| 槽位 | 本包状态 | 含义与下一步边界 |
|---|---|---|
| D1 | 条件机制差量 | anchor-aware copy/edit planner；先证明相对旧H1和当前路径的来源/恢复/成本差量，不能把泛lookup改名算新 |
| H2 | 旧计划细化 | draft-only shortlist/重打分；静态optimized head已存在，进一步裁剪/稀疏投影早有规划 |
| K-PAIR | 仅P3/当前binding源码门 | 老b0小T仍有异dtype投影pair，但P3后续源码尚未完全绑定；先查当前是否还缺该能力 |
| M0 | 维护，不是新性能 | Strata已有终止输入行修复的部署绑定与精确continuation回归；其他owner经验沿A2参考 |

D1实施卡见[06](06_D1_SOURCE_ANCHORED_COPY.md)，H2见[07](07_H2_DRAFT_HEAD_REFINEMENT.md)，K-PAIR/M0见[08](08_K_PAIR_AND_M0.md)。
总体集成边界见[05](05_ARCHITECTURE_AND_INTEGRATION.md)，历史关闭项见[01](01_HISTORY_AND_NO_REPEAT.md)。
上表不表示任何槽位已经取得GPU执行许可，不新增第三条性能候选。

## 2. D1：OSAKANA的差量在source-anchor，不在lookup名字

[common_speculative_impl_copy::draft_one / accept][o-copy]使用3-gram与长match双索引，优先匹配source anchor附近。
已接受copy移动锚点；冷启动需更长证据；来源为自身生成的短重复时不放大窗口。
单token edit可绕过已被新token打断的短key，短窗验证源对齐；多token edit可记住proven source并恢复。
低效窄copy与其它drafter的EMA竞争，连续失败会让路/熔断，不在每轮无限抢占proposal。

这不同于历史H1的请求内4-gram/8192环/K3整包替换。
但“扩索引范围”“Suffix+MTP”“全局lookup”都已有计划，D1只有上述特定差量需要被源码与实际任务轨迹支持。
不能以copy-heavy全文件rename命中率证明自然Java修bug或自由生成受益。

copy先命中时OSAKANA dispatcher可跳过该轮DF2 proposal，但仍须维护其历史/taps。
[Strata window_rule::skip_draft_for_lookup][s-window]已经有STRATA_DF2_LOOKUP_SKIP，长match可跳过DF2；CUDA默认值与Metal不同。
因此“跳过必然丢掉的DF2”对Strata不是本轮新机制。
NInfer当前mandatory MTP若仍全部执行，不能凭donor的skip行为扣掉本地并未省去的proposal成本。

D1可以保持target权重/codec；前提是最终仍完整target验算，commit/回滚保持现有合同。
在已资格的相同轨迹greedy合同内，anchor跟错源应只影响速度；若改变最终token，按accept/state或数值资格问题处理。sampled还须独立证明实际q/residual与Target RNG，不能以Target权重不变宣称无损。
不把OSAKANA的63-token wide、QSA或trellis捆绑进D1，避免把窄planner差量变成新引擎工程。

## 3. H2：已有proposal head上的细化，不做target剪枝

NInfer固定[b0 variant.h][n-variant-h]的draft_head_rows=131072；
[load bindings][n-bind]绑定Q4G64_F16S head及I32 token映射；
[proposal_argmax][n-text]已经linear→argmax→remap，不是尚未优化的完整词表head。

YASAKANI [shortlist实现][y-bdraft]给H2的参考是低秩粗扫、候选集、全维INT8重打分。
它的V约248K，与用户131072行静态head不同；不可直接套其读流量比。
新增sidecar、投影、候选召回损失与full-dim rescore开销都必须计入；target head不得同时剪枝。
保持target数学只意味着proposal可变但最终完整验证，不意味着draft acceptance不变。

0.17GB是作者bytes/pass估计，不是总VRAM。
同时保留完整INT8 head与sketch可能显著增加常驻显存；以真实loader/buffer账本为准。
既有P14的proposal head+AR约9.5%不是head单项，也不是当前b0-scanner rk4v4-e8 profile。
因此H2标签只能是旧计划细化，不能以漂亮压缩比宣布新的端到端收益。

## 4. K-PAIR：只做当前源码门，不从老b0直接推生产缺口

TensorFold [projectMany][t-many]与[tf_lane_gemv_seg][t-seg]把共输入的多个projection放同grid。
member保留独立split-K、workspace/ticket、归约顺序；少launch不等于改变每个矩阵数学。
它直接实现于MLX-affine4 tiles，不能把其kernel直接当Q4/Q5混合codec实现。

NInfer老b0的[attention small-T][n-attn]与[GDN independent][n-gdn]确有相邻Q4/Q5两dispatch。
但Q/K、gate/V已有打包，GDN大T已有grouped grid，gate/up已有融合，MTP decode也不等于prefill尾部那对linear。
[固定b0 variant][n-variant]是历史路径入口，不等于当前部署绑定；不能把所有projection都再提一次“QKV融合”。

P3后续small-T整合已经存在，尚未绑定其最终分派与实际部署。
所以K-PAIR只允许先确认P3/当前binding源码、各member现存几何与真正消费者。
若当前已经等价合组，直接关闭该槽位；不拿老b0的pair重新制造缺口。
若仍有pair，也不自动获得GPU资格，必须回到统一门判断它是否是当前关键路径的实质差量。

## 5. 4090能力边界：可运行不等于全功能等价

[YASAKANI gpu_caps][y-caps]检查实际build code capability；[pdl.cuh][y-pdl]在sm89把PDL指令门掉。
[bulk L2 prefetch][y-kernels]要求sm90以上，普通cp.async、INT8 MMA、CUDA stream/event/graph则仍可用。
**4090没有该PDL/griddepcontrol与bulk L2路径。**
NInfer [CMake guard][n-cmake]对arch86/89定义NINFER_SM86，[pdl helper][n-pdl]相应退化普通同stream launch。
函数名含pdl不代表4090实际执行PDL。

TensorFold [verifyRows][t-affine]的128-row共享weight panel依赖GB10 PDL/cluster，sm120的32-row也有筛选。
不能把“框架支持4090”“某kernel可编译”写成“所有5090/GB10新功能在4090同样成立”。
当前codec的权重布局、activation、row arithmetic与状态owner优先于GPU指令名字。

## 6. M0：维护项须保留，但不得包装成性能路线

YASAKANI v0.1.3在共享buf旋转/复用处加barrier，并改每engine encoder scratch所有权。
老Unlocked保留旧race；这支持检查同类scratch复用，不支持断言NInfer/Strata已存在相同bug。
这些owner/last-consumer/event fence经验沿旧A2参考，不扩大M0范围；M0只处理Strata已有终止输入行修复的部署与回归绑定。

Strata已有[serve_stop_bound][s-stop]，CUDA也按remaining预算及窗内首EOS限制最终提交。
用户v0.2.10 DF2已有服务验收摘要，不等于当前部署已绑定后续CUDA修复的每个组合场景。
维护验证不可倒推历史从未测，也不可把旧PASS扩成所有新增边界都PASS。
M0没有独立性能目标，不以维护修复创建新性能预算。

## 7. 排除表：保留旧结论，不换名字重开

| 项目 | 排除原因 | 本轮允许保留的用途 |
|---|---|---|
| 旧K1 GDN record/fold correction | 已测无净益；donor log/replay不是自动翻案 | 解释state语义、ownership；不新开性能线 |
| H3 W6/K5 | 短段赢但Java后半反向，已有关闭结论 | 约束宽度成本与跨内容稳定性 |
| W8/W16、Suffix+MTP、utility | 已有PLANNED_NOT_RUN路线，不是新发现 | TensorFold/YASAKANI作为旧计划源码参考 |
| 泛DFlash2适配/再验收 | NInfer已有计划；Strata0.2.10通过但收益不足保留MTP4 | 仅比较实际cost差量，不因名字重跑 |
| KV5 | 换KV codec/旋转/编码/读核，影响质量；相对现KV4无容量天然优势 | 记录容量与编码代价，不列直接候选 |
| Trellis+LNORD整模 | 换权重格式、转换、H512/A8与fixed-point数学 | 解释速度来源；不塞进保持现codec任务 |
| QSA+tree整栈 | 稀疏选择改变质量；祖先块强制可见改变sequential QSA语义 | 记录质量边界与indexer一致性 |
| 旧Unlocked部署/调优 | 官方v0.1.3已覆盖主要兼容目的，老fork无新调优且含旧race | 历史兼容证据，不建议生产倒退 |
| PDL/bulk L2 | sm89不具该路径 | 直接排除硬件不成立项 |
| “少host同步”“更大batch”泛优化 | 真实consumer未知；单流可能反归 | 仅以实际依赖与固定源码说明，不新增路线 |

TensorFold [v1.2.9单流draw修复][t-commit]就是最后一项的反例：全batch同步下载在单流无法摊销，反慢。
OSAKANA默认26.8GiB不fit 24GB；YASAKANI的262K预留也不等于262K真实prompt质量/服务验收。
这些限制不因64GB host RAM自动消失。

## 8. 外部参考的范围

本轮深入源码对象只有本章列出的四个donor及为判重读取的NInfer/Strata固定路径。
其他engine仅沿既有A1/A2参考入口，不声称本轮全网重审、更新结论或给出新的硬件资格。
有新名字、PR或作者tok/s，不构成解除旧关闭项的证据。
任何改变权重、KV、sampling、context、并发或精度合同的方案都需另行分类，不能与现baseline混算。
本包交付的是有边界的D1/H2与K-PAIR/M0状态，不保证存在高收益的新优化。

## 固定源码索引

[o-copy]: https://github.com/pentaCoxian/OSAKANA/blob/40c8a0554f1863e612eb5e045532ddf23b4ac8ae/common/speculative.cpp
[s-window]: https://github.com/Niko1221/Strata/blob/13eedf552417a6a791a7d13c6597e24300ee3a09/include/strata/spec/window_rule.hpp
[s-stop]: https://github.com/Niko1221/Strata/blob/13eedf552417a6a791a7d13c6597e24300ee3a09/include/strata/core/serve_stop_bound.hpp
[n-variant]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8_27b/impl/variant.cpp
[n-variant-h]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8_27b/impl/variant.h
[n-bind]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8_27b/impl/load/bindings.cpp
[n-text]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/runtime/text_context_impl.h
[y-bdraft]: https://github.com/yasakani-dev/yasakani/blob/274d70967f013dc197888dfec233681ddd386012/src/q35_bdraft.cu
[t-many]: https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/zig/src/families/qwen3_5/cuda_projection_many.zig
[t-seg]: https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/zig/kernels/cuda/lane_gemv.cu
[n-attn]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/ops/attn_input_proj/q4_q5/q4_q5_attn_input_small_t.cu
[n-gdn]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/ops/gdn_input_proj/q4_q5/q4_q5_gdn_input_independent.cu
[y-caps]: https://github.com/yasakani-dev/yasakani/blob/274d70967f013dc197888dfec233681ddd386012/src/gpu_caps.cu
[y-pdl]: https://github.com/yasakani-dev/yasakani/blob/274d70967f013dc197888dfec233681ddd386012/src/pdl.cuh
[y-kernels]: https://github.com/yasakani-dev/yasakani/blob/274d70967f013dc197888dfec233681ddd386012/src/q35_kernels.cu
[n-cmake]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/CMakeLists.txt
[n-pdl]: https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/core/pdl.cuh
[t-affine]: https://github.com/ashhart/TensorFold/blob/6b9de695104b6b8b30c20458da87ac06c9480289/zig/src/cuda/affine4_kernels.zig
[t-commit]: https://github.com/ashhart/TensorFold/commit/6b9de695104b6b8b30c20458da87ac06c9480289

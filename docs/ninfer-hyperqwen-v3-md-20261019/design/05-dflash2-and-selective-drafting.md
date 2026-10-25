# tqLLM 路线仍保留：DFlash2 与全局 selective drafting

本页取代旧P10/P11的执行入口；旧文档中的greedy-only限制已由现行design/11的确定proposal+Target sampling组合资格取代（资格前OFF，随机general-q草稿仍不支持）；具体资料保留于 [V2 DFlash2](../previous-v2/docs/tqllm/04-dflash2-design.md)、[V2 archive](../previous-v2/docs/tqllm/05-selective-draft-cache.md)。当旧文本说K≤5或只在请求级定width时，新的已合格verify能力表优先；不让旧设计重新覆盖C10—C20。

## H6：有界ring，先chain后其他

27B当前DFlashConfig unsupported，35B DFlash不可直接启用为27B。必须冻结checkpoint immutable revision、tensor inventory、许可、feature tap层、hidden/heads/dim、blocksize、conv、selector、词表及归一化语义。缺这些是资产BLOCKED，不填猜测常量。

离线将companion转为 `.ninfer` typed descriptor，H6先BF16参考和可落地低位草稿配置，Target不变。神经物理block长度取checkpoint训练结构；支持只消费前K个提案不代表只算K个mask。将 `physical_neural_rows` 与 `valid_neural_drafts` 分别观测。长期不引入tree验收的多分支GDN结构；统一chain入口允许DFlash2 N=5/7加Lookup tail直到已合格W8/W16。

现有shared DFlash runtime具有feature/ring/paged基础，但新27B dynamic convolution/selector与hidden taps必须完整实现并独立逐层验证。Graph预分配包含draft logits、projected特征、KV ring及checkpoint；不能用0.79GB/1.19GB文件大小替代总VRAM。

后端选择在请求边界冻结。MTP与DFlash2都驻留且状态ready时才可按校准选；不承诺任意轮切换。缺Draft history、长会话热Target命中时，可保持原MTP/ordinary而不是偷偷完整重跑Target以建草稿状态。

## H7：独立 ProjectedG Archive

Target KV不是Draft KV。从真实Target feature taps产生已提交ProjectedG，存入受限host archive，身份至少包含Target/adapter/tokenizer/feature-map/projection/位置策略/epoch。Target continuation可独立命中；archive缺失不作“完全命中”伪报。

首轮使用ProjectedG，而不是为全部历史保存所有层Draft KV。对全局逻辑页（起始256tokens/page）生成少量摘要；粗排全局页、精排候选chunk；按选中token重建各层Draft K/V并进入固定recent+retrieved staging。摘要和host archive仍是O(context)，仅GPU参与Draft的工作集有固定上限；不把全系统称为O(1)。

初始recent=2048，retrieved≤512tokens，页候选≤32；都是实验预算，不是品质保证。为第0页、1/4、1/2、3/4、末端分别种入测试依赖；继承tqLLM只搜索最近4096×16的旧行为必须被覆盖测试发现。完整Target KV不裁剪。

图外异步refresh、双staging及epoch fencing；以completed event切换。上一版已完成stage可短期复用，但超预算/过期/身份不符退回ring，不用未填完的数据。不每轮拷回完整attention matrix；首版页摘要为便宜代理，Target-guided评分后续只有在profile证明值得时引入。

H7可在H6 ring-only正确但未达采用性能线时研究：必须有可工作的ring基线，不能用缺资产/数值失败当作“有待优化”的理由跳过。任何未来收益必须包含archive构建、恢复、检索、投影、PCIe与Graph开销。

## selector分数不是q，Target不必改greedy

DFlash2/检索/Lookup融合若输出确定链，其真实q=delta；不能把selector lattice score、神经softmax或检索分数冒充full-q。目标是保留T1/.95/k20/presence0/preserve-thinking/medium的Target sampling，复用现有greedy-draft sampling接受/processor/RNG/commit链，按design/11通过该companion/W/cache组合资格后才启用。真正随机selector/drafter若无对应general-q合同则OFF/回原合格sampling；不为接入另写sampler。Target-greedy只是逐层/状态诊断，不能代替sampling分布资格或现网收益。H6/H7先跑相关小集，H5/H8才集中声明profile的正式性能与工程holdout。

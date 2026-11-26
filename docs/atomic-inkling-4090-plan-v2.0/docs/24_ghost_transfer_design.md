# 24 · Ghost机制如何进入Atomic / Inkling / 4090

**设计结论：** 继续全驻留优先，补齐循环感知的成本模型和可验证实现参考；只有容量/trace支持时才进入异构专家计算。本文中NEW均为拟新增接口，不是上游已有功能。来源与版本见[23](23_ghost_source_audit.md)。

## 1. 优先级与归属

| 候选 | 原包归属 | 增量任务 | 启动条件 | 性质 |
|---|---|---|---|---|
| 独立CPU参考、逐层/逐loop对照 | T01/T02/T03 | G00 | 相同资产可表示、几何已核实 | 优先，降低后续错误定位成本 |
| 循环层和热专家优先驻留 | T09 | G01 | 经过容量诊断确需部分驻留 | 条件容量优化 |
| 精确布局重排、选定格式kernel | T03/T07/T09 | G02 | 资产包含适用格式且解码是实际热点 | 条件计算/内存权衡 |
| prefill按专家聚合并复用权重 | T07/T08 | G03 | profiler显示专家重复读取或小kernel开销 | 条件性能优化 |
| 图内CPU/GPU交接 | T05/T09 | G04 | 已有安全分段实现且CPU handoff确是关键开销 | 默认DEFERRED，高风险实验 |
| inactive session host快照 | T10/T11 | G05 | 多会话反复切换，重prefill占明显E2E | 服务优化，不是真GPU并发 |
| lookup、TC attention、Q4 KV | T07/T08/T10 | 增加GX测试 | 对应路径在Inkling另行实现和资格 | 合并进原任务，不重复立整条路线 |

如果正式Mini选定精度、目标context与DSpark全部能全驻留，G01/G04可带完整profile证据跳过。Ghost在8GB机器上的CPU分工不能成为4090必须offload的理由。

## 2. 循环层优先驻留：有用，但要升级成成本模型

### 2.1 固定代码实际做了什么

`inkling_gpu.rs::place_experts`先处理循环区间，再处理单次层；每组先放完整层，再放部分专家。部分驻留至少需要 `max(n_expert/4, top_k)` 个slot。当前GPU专家格式仅接受 **down=NVFP4，gate_up=NVFP4或IQ3_XXS**。不支持的格式继续CPU计算，因此不能从“24GB足够”推断Ghost所有专家都会上GPU。[S18]

部分驻留用hot文件或初始排序选专家；`swap_experts`按照热度更换，条件为新热度大于旧热度的1.5倍再加2，之后热度乘0.85。每个部分驻留层最多4个交换，非全模型合计4个。实现按 `steps % 32` 触发，且nb=1才进入交换；批量prefill一次调用也增加step，故不能把注释的每32tokens直接当严格调度合同。

这条专用Inkling交换路径使用同步H2D和固定device slot地址，再更新expert→slot映射；不能混称通用Qwen路径的异步后台uploader。

### 2.2 Atomic中的实现决策

physical层共享权重；各loop的KV/conv仍独立。统计按 `(physical_layer, expert, logical_visit, phase)` 采集，最终在physical权重上决定驻留，避免把同一块权重重复收费或把loop1热度误当所有loop。

候选评分采用可测的收益/字节：

\[
S_e=\frac{E[T_{step}\mid e\text{不驻留}]-E[T_{step}\mid e\text{驻留}]-C_{迁移,e}/H}{B_{resident,e}}
\]

其中H是预登记的预计复用步数，B包括真实packed布局与元数据。循环访问次数影响期望收益，但不能简单乘3：CPU/GPU并行时关键路径接近各阶段的最大值，GPU命中增加却未缩短CPU尾部，E2E可能不变。

先比较完整层优先、按热度、成本模型三种**固定策略**，再加动态交换。交换只在安全token/批边界提交，发布新的slot generation；所有旧lease与相关CUDA event结束前不能覆盖。热度采集、排序、H2D、图更新、页面错误均计入总成本。

Ghost的阈值只作为明确标注的探索候选。不能把128MiB保留量、1/4专家门槛、每层4次或32步直接设为本机默认。原04的显存/host保留策略优先。

## 3. 精确重编码：用空间换解码成本

### 3.1 IQ3_S到Iq3SNib

`iquant.rs::iq3s_to_nib`把IQ3_S原来的grid/sign表示转成直接的4-bit符号和奇数level编码，保留block scale。每256值从 **110字节变成134字节，扩大21.818%**；含元数据的有效bits/value从3.4375变为4.1875。它是内存中的精确重排，不能称进一步压缩或把模型重新量化成通用Q4。[S18]

扩张比例仅适用于被转换的tensor，不是整个模型/进程的增幅。partial层可能同时持CPU专家副本和GPU slots，必须算双份。现有局部AVX2测试在无AVX2时可直接返回，记录实际断言覆盖，不能仅凭测试名称出现判断已验证。

该实现提供局部dequant与AVX2 dot相等测试。只有相同值和运算顺序经过验证的部分可按E类处理；随后更换activation量化、融合归约或head路径仍需要N类容差与质量检查。提交所称5.0→1.57ns/32值只说明特定局部微基准。

Atomic第一步只审计**当前选定资产是否有这类tensor**。AD-IQ2_M与UD-Q3_K_XL并非同一tensor格式组合，不能为了套优化偷偷换模型文件或精度。没有适用tensor就SKIPPED_WITH_EVIDENCE；有适用tensor但解码不在关键路径，结案NO_BENEFIT。

### 3.2 NVFP4存储与硬件FP4不同

Ghost的NVFP4 kernel通过软件拆码、查表/scale处理和 `dp4a` 计算，并不要求Blackwell原生FP4矩阵指令；这解释了它可运行在2060S这一事实。对4090的价值是**可研究的低比特存储执行布局**，不能推导4090获得原生NVFP4 Tensor Core吞吐。[S18]

在Atomic中沿现有ggml tensor/type与CUDA分派增加精确格式白名单，禁止用新编码冒充现有GGUF类型。runtime-layout指纹至少包含源tensor SHA、源格式、目标layout版本、row/stride、scale顺序、对齐、端序与kernel revision。布局相同值证明和完整计算路径数值证明分开。

## 4. Prefill按专家组织：适合复用，而非固定抄128

Ghost的Inkling批量路径默认使用128-token pass，对满块复用图；CPU对一段已解码权重行处理多个token，GPU对gate/up按专家分组。核心收益是让同一专家权重服务同一批多个token，减少重复读取与解码。[S18]

Atomic候选实现沿现有ggml图与 `llama-expert-executor.cpp`，先收集每个prefill块的路由，再建立expert→token索引，保持原token位置和每token的top-k聚合语义。不能跨有依赖的loop调换forward顺序；只能在同一合法访问阶段组织独立token/专家计算。

B从已支持的1/8/32/64/128及尾块中选择，实际probe必须遵守该profile的ubatch与budget上限。对循环依赖、relative bias、sink、SITU、conv和SWA边界分别比对。若归约顺序改变，按N类处理，不能凭greedy少量token相同宣称bitwise等价。

完成B1/Bn正确性后，才比较冷/热prefix、短/64K/承诺128K的TTFT、GPU峰值和总E2E；Graph capture、padding、排序与转码不能从总成本中消失。

## 5. 一张图里的CPU/GPU交接：研究候选，默认后置

Ghost的专用单token路径可把整个token装进CUDA Graph：GPU将输入/专家选择发布到mapped host memory，CPU算缺失专家，再写回ack；GPU的 `ink_await` 等待。图内仍有等待与串行依赖，不能称没有CPU同步。

静态审计发现：`ink_await`超时设置err后返回，后续graph节点可继续；host主要在等待下一flag的循环里查err，正常读logits前缺少同等强制检查。因此**迟到CPU结果，尤其最后一次handoff，存在未被最终提交拒绝的可达风险**。这是待注入复现的静态发现，不是已证实的4090事故。[S18]

Atomic默认先使用**有边界的分段图/host调度**，复用原预算lease及sticky error语义。只有trace证明CPU launch/sync足够重要，才进入G04的mapped实验。

实验接口必须有request/epoch/sequence编号，异步错误保持sticky；超时后不得commit logits/token/工具调用，必须drain并退役失效context，必要时重建worker。迟到ack不能复用到下一请求。等待期限使用明确时间预算，不把GPU cycle常量当跨频率固定毫秒。

还要验证graph销毁、mapped buffer、CPU专家owned数据的生命周期。Ghost为CLI预览采用的 `Box::leak` 或未完成的raw graph清理不能原样带进长驻服务；全局CPU pool的单调用者假设必须显式执行。

同样不能从metadata可读取loop.count推断varloop可用：专用GPU实现存在固定POOL_ROWS=12、head_dim=128、conv临时数组8等几何假设，部分容量检查发生在执行后。适配器必须在任何分配/launch前验证正式Mini/R3完整几何白名单；不匹配立即拒绝，不能靠修改循环数字探索R4/R5。

## 6. Host快照：面向会话切换，不增加活跃并发

通用Ghost路径把闲置会话状态放到host，恢复时减少重prefill。该思路与T10一致，但Ghost的通用Engine尚未接入专用Inkling，不能拿来即用。[S18,S21]

G05要保存完整Inkling状态：各loop global/SWA KV、conv、controller、位置、已commit token、采样/RNG、draft状态及目标指纹。必要的scratch可重算，但要证明恢复语义。会话缓存查找需要精确token前缀，不以文本长度或近似hash匹配。

按照实际字节预算和重建成本淘汰，禁止机械套用最多5个。64GB host同时容纳权重、转码膨胀、staging、页缓存、现有服务和会话快照；没有空间时逐个驱逐inactive状态。单GPU active generation仍为1，子agent在外部工具阶段释放GPU占用。

先做全局账本reservation/必要驱逐，再分段复制，全部成功后原子发布快照。Ghost通用路径的先复制、再按park预算淘汰会产生瞬时超额；opening缓存与live snapshot也必须进入同一账本。不能在copy后才检查内存限额。

恢复收益条件：D2H/H2D与序列化耗时加上资源代价，小于所节省的重prefill。报告首次请求、二次请求、切换与缓存失效四种情况；不能只展示最快的warm返回。

## 7. 通用路径只提供进一步假设

### Lookup与采样

Ghost lookup把复制的确定性token作为one-hot proposal。sampled模式按p(d)接受，拒绝后排除d并归一化抽样；这是一种合法的特例，但不能用来替代原生DSpark/2DSD的一般q分布与residual合同。独立draft-model路径仍限greedy。源码有合成分布测试，尚不足以证明GPU、recurrent和Inkling全链路。[S18]

通用spec/lookup在拒绝候选时恢复recurrent snapshot；但接受前缀遇到EOS或取消回调时，有分支只缩短pos，未同步回放recurrent state。该风险仅定位通用GpuSession，不应混称Inkling runner缺陷。普通max_new已参与限制k，不能单凭同一退出分支就认定它独立触发该缺口；输出上限仍作为回归边界覆盖。T05/T08新增GX17，要求终止后保存/恢复/续写仍和serial oracle一致。

### Attention与Q4 KV

通用TC、split-context和Q4 codec都需要明确dispatch条件。Inkling的head几何、相对位置、sink、softcap和SWA不能省略。Q4布局不是GGML Q4_0的同义词；替换codec属于独立N/Q实验，不能修改标识后复用旧KV。

具体可借鉴点是：split-KV按每token自身有效span选择分段，串行与verify保持相同浮点epilogue/归约顺序，避免同一个token因B变大就选择不同数值路径。通用64位置verify只在dense、非MLA、检查到的矩阵全为Q4_K/Q6_K且对应TC可用等条件下成立，其余上限为8；lookup的验证位置B=k+1，64位置不是64个草稿token。

当前generic Q4是256维行的旋转codec，含Hadamard变换与每32值FP16 scale；load/dispatch另有GQA、TC和架构条件。Inkling128维head不满足此路径。不能把codec同名、相同裸字节数或环境变量开启当兼容证明。T07/T08优先吸收数值一致性的组织方式，再评估更宽verify，禁止直接复制64这个上限。

### 数值参考

`GHOST_INFER_EXACT=1`不能被自动命名为完整FP32 oracle：代码中一些prompt matmul仍走activation量化，attention/默认KV选择也不由此变量全部关闭。G00必须记录实际路径与每项dtype；必要时固定stepwise、KV和TC配置，再与同资产可信参考核对。

## 8. 原方案哪些结论因此改变

增加：一个可审计的Inkling CUDA实现参考；更具体的循环驻留、精确布局、prefill复用和服务状态风险。

保持：Atomic底座、正式Mini/R3、per-loop KV、全驻留优先、先固定DSpark、64K/128K独立资格、真实Java/Pi质量和E2E、单GPU排队与旧服务回退。2DSD/LoopCD/last-loop仍走独立研究任务；Ghost没有消除它们的集成或正确性前提。

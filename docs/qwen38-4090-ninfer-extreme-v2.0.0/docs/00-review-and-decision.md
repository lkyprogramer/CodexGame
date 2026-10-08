# Claude 极致优化方案：独立复核与最终决策

## 结论先行

**接受“停止 Kern 64K 重写，以现有 NInfer 4090 为唯一生产基座”的方向；不接受把新路线的预测速度、已有 donor 或数学上限当作已证实的改造收益。** 本包替代旧 Kern PoC 性能开发计划，不推倒已经测过的 NInfer；Kern 留作非生产研究，不占本轮 GPU 维护窗口。

此前方案的主要失误不是“PoC 无法写”，而是没有把“学会运行另一个引擎”和“让这台已接近带宽受限的机器更有生产价值”分开。64K、no-spec、BF16 KV 的里程碑即便通过，仍不能回答能否超过当前 262K、MTP3、压缩 KV 的长 Agent。另有 Mac/Pi 拓扑、已改写权重、工具依赖和 Java 题目不一致问题。本包逐项修正，见 `../references/CLAIM_AUDIT.md`。

本轮实际做了：读取两份 Claude 文档、解包设计和评测归档、追到报告07/09/10/11/12及源码分支、核对相关 GitHub/模型卡、Exa 与 NVIDIA 文档。**原始生成时没有 SSH 到用户机器，没有加载模型，没有运行新 GPU kernel。** 2026-09-09 由 Claude 对 4090 做了只读 SSH 复核（源码 sha、artifact 目录、`nvidia-smi`、unit/端口、sudo 状态）并核对上游文档与 HF 合同，结果与由此产生的决策记录在 `22-machine-verified-facts-and-revisions.md`；本文 §2.11–2.15 是其对决策有影响的部分。仍然没有加载模型或运行新 GPU kernel。

## 1. 必须采纳的部分

- 已有 NInfer 同时有 SM89、INT8 prefill、KV codec、MTP、ReplaySSM、服务/缓存等资产；从这里增量改造比重新做 Kern provider 更贴近目标。[输入 Kern review §0/5；报告09]
- 继续记录独立的冷 prefill、热轮恢复、每轮投机成本和任务完成时间。只看 tok/s 会漏掉缓存重算、CPU/sudo/隧道、工具运行与失效重试。[报告10–12]
- 真实 T=1.0/top_p=.95/top_k=20、medium 才是产品路径。greedy 是诊断/逐位回归车道，不替代产品验收。
- DFlash2、Suffix/lookup、较宽验证和 d256 prefill 都值得研究；原生硬件相同与模型相同只是进入试验的条件，不是成功保证。

## 2. 必须纠正的部分

### 2.1 rk8 的收益和质量门没有想象中完整

报告12-D 的184k：`103.7` 对照 `98.5` tok/s，按同为medium的历史报告数值计算约 **+5.28%**（不是本轮ABBA配对证实）；92.2s 对94s冷 TTFT约减少1.91%。短/中长度可有更大收益，不能统一称为“+15–30%”。该报告的 Java 3/3 明写“上一轮 soak 同镜像”，没有证明那三题以 rk8 启动。应补一轮 **同配置、同 medium、同题、同采集器** 的 rk8 smoke。

**2026-09-09 更新**：受保护容量已由用户决定降为 200192（`22 §1.1`），因此 rk8@200192 不再自动是 `TRADEOFF_ONLY`。但 rk8 多出的 K 位宽（≈8 KiB/token → 200192 下 ≈1564 MiB）正好吃掉降容量释放的 ≈1597 MiB，与 DFlash2 W8 companion（净 +1734 MiB）**争同一块显存**；200192 下二者只能选一。T03 的 rk8 控制组因此是"对照 + 备选"，其结论是二选一决策，不是叠加。

### 2.2 现有 small-T 专用路径到6，不是8

附件源码 `src/CMakeLists.txt` 约279行 `foreach(token RANGE 1 6)`；`gqa_attention_decode.cu` 19/239/243行均限定T=1..6。因此“block8直接复用T≤8、零kernel改动”不成立。**这里并不等于全引擎绝对不能处理8行**：它可能走prefill/generic route，但需要路由记录与性能验证。W8和W16必须分别过shape、workspace、graph、reduction和mask验收。[S03/S04]

### 2.3 rk4v4-e8 的历史读路径不是 Root lattice decoder

当前源码中 `E8Root` 路径调用 `e8_root_decode_8d_int8`，属于rk2v4-e8；rk4 packed-K分支读取4bit code并unpack，lattice projection主要在写入侧。prefill计划也明确写了这个区别。优先优化 `e8_root_codec` 并不能默认改善生产rk4。更重要的是现有lattice路径明示半陪集舍入近似；把它“纠正成数学上更完整E8”会改变格式/数值，不能混入无损性能补丁。[S05/S06]

### 2.4 DFlash2 是完整协议和状态移植，不是启用布尔开关

上游已接入五层draft、dynamic convolution、top16条件selector、实际proposal q、target拒绝/残差采样、40MiB local KV ring、pending features、checkpoint和partial commit。上游存在是降低风险的参考，不代表旧44a可整棵merge或只开`enable_dflash`。[S01/S02]

### 2.5 Sage 有 Ada 内核，不等于有本目标可用的内核

本目标主Attention是24Q/4KV、d256、分页压缩历史、带prefix的causal chunk。所读Sage `core.py` 明确拒绝head_dim>128；维护者说明256需要不同block设置。Ada fork主要验DiT/ComfyUI，输入分布、mask、GQA、缓存格式均不同。必须按 **新的d256 paged causal kernel** 预算，而不是替换一个函数。不能将256拆成两个128各自softmax再拼接。[S11–S14]

### 2.6 AL不是速度，更不是全任务速度

公开DFlash2表是H200/xhigh/K7。相对同K的MTP，AL改善约8.8%–20.1%，并非所有题都只9–12%；采样下的吞吐还取决于draft耗时。Lucebox短输出、不同target量化的AL只能提示机会，不可直接迁移到NInfer。验收使用 `Σcommitted_tokens / Σround_wall_time` 和实际任务E2E，不设置单一“AL<3就否决”规则。[S07；输入报告]

### 2.7 Suffix可以先和MTP组合，不必等待DFlash2

SuffixDecoding原工作本来就提出model-free/model-based hybrid。对本机已有MTP基座，先做窄链、会话内索引、精确采样和MTP状态catch-up，是一个更小的可否决实验；不新增约2GiB draft权重。并非“零工程量”：skip MTP draft后，其private KV/hidden仍须正确前进，不能仅把候选token数组换掉。[S09/S10；44a mtp_impl.h]

### 2.8 宽验证“只读一次KV”与roofline不能当硬保证

共享tile能减少重复加载，但不同head、split、CTA仍可能读重复数据；增加宽度也增加query计算、GDN replay、head和scratch。按文件大小推DRAM流量、假设固定AL、把不同累加精度的峰值混算，都只构成近似模型。实际 DRAM字节/SM频率/occupancy/阶段占比才有资格约束上限。不开ncu时可以测整个round，不能声称已定位到某条指令的墙。

### 2.9 INT4 activation属于高风险新数值配置

Q4 nibble可表示s4，不代表无需重排、scale或算术；group rescale还在。Hadamard折叠`W·Hᵀ`改变矩阵，已有量化codes通常不能原样使用，须从合适源重新生成并引入新的量化误差。Q5层不能无损塞进s4。P5只能独立artifact/profile与更强质量门，不能借用“权重侧零误差”豁免。[S06]

### 2.10 ncu权限不需要先全局放开

NVIDIA允许管理员授权的单次sudo/能力方式；R610还提供更细的权限模式。不要自动卸载驱动、写modprobe全局开放配置或授予任意shell管理员权限。统计/算法实验不依赖ncu；kernel归因阶段取得受限授权即可。[S15/S16] 实操：hhtele 在 docker 组，devel 镜像内已有 `ncu`，用 `docker run --cap-add=SYS_ADMIN` 即可，不需要任何主机权限变更（`22 §4.7`）。

### 2.11 DFlash2 W8 在 262144 下显存不成立，这笔账不需要 GPU（2026-09-09）

现网空闲 1509 MiB；按上游 66 对象 inventory 逐项累加，companion 常驻 2124 MiB，不加载 MTP 只省 430 MiB，加 40 MiB ring 后净增 1734 MiB，再加 50–150 MiB 工作区。零余量都差 ≈0.3 GiB，按 ≥512 MiB 门差 ≈0.8 GiB。原包把这笔账放在 T08"实现后再算"，等于让最大的一条研发线在自己的门前注定 `BLOCKED`。它已在 `22 §3` 算清，并直接导致了 200192 决策：降容量释放 ≈1597 MiB，DFlash2 W8 后余量 ≈1.2 GiB。draft 主体 W4 的 fallback 因此降为条件实验。

### 2.12 44a 对 DFlash 后端没有会话持久化，T10 是新功能不是移植（2026-09-09）

`session_snapshot_impl.h:342/534` 对 `speculative_backend==DFlash` 显式抛错，`docs/serving.md:130` 写明不支持。现网 85% prompt token 靠前缀复用，热命中 TTFT 1.1 s 对全重算 21 s。DFlash2 profile 若没有等价恢复，任务墙钟必输（`task_wall_ratio>1.02 → NO_MEASURABLE_PRODUCT_GAIN`）。T10 因此加入硬断言：解除 throw、image 含 ring+pending、A→B→A 后 `reused_prompt_tokens` 与 MTP 等价。

### 2.13 两项"待建"能力其实已在 44a（2026-09-09）

`speculative_round.cuh:60-68` 已是 T>0 的 distribution-correct rejection sampling（one-hot accept `p(d)`、首拒 masked residual、末列 bonus）；`/metrics` 与请求结果已有 `draft_accepted_tokens_total`、`speculative_accepted_tokens`、`reused_prompt_tokens`、`cached_tokens`。T04 缩为"扩展现有 sampler 增加 Sparse16 q"，T02 缩为"增加每轮字段"。

### 2.14 Suffix+MTP 有一个零 bridge 成本的第一版（2026-09-09）

MTP 常驻照跑，suffix 只在 `[committed…, d1, d2, d3]` 之后做**链延长**到 K≤5（W≤6，恰在 small-T 1..6 与 `--draft-tokens ≤5` 内），延长部分 q 为 one-hot。零 MTP 状态修改、零 bridge、零新 kernel、零新权重。它回答的正是 T05/T06 的问题（本机流量有没有可利用的长重复）。原 alternating-source + bridge 设计降为 v2。

### 2.15 DFlash2 的收益只能来自宽度，T07 是关键路径（2026-09-09，推断）

同 K 换 drafter 的固定成本 ≈+2 ms/轮（draft 权重 2.07 GiB 读），现网 184K 轮 ≈29 ms，打平需 committed/轮 +7–9%；模型卡同 K 的 AL 增益 +8.8–20.1% → 净 0–12%，接近噪声。实质收益只能来自 K=7（W8）。因此 T07（W8 合法路径及其 184K 轮成本）必须先于 T09/T10 拿到数据；4-bit KV 下 W4→W8 的 verify 读字节几乎不变，W8 在长上下文更划算。公式与代入值见 `22 §4.1`。

## 3. 最终路线

第一优先：事实与采集器冻结 → rk8@200192 控制组（对照 + 备选，与 DFlash2 二选一） → **Suffix 链延长 + MTP（v1）**。第二优先：**T07 W8 路径收益门** → DFlash2 companion binder + 算子 + 正确采样/状态事务 + **会话持久化**。第三优先：根据实测热点扩 W16（依赖 T07+T06，不依赖 DFlash2 完成）和 d256 prefill。A4 独立后置；树验证、低 bit 主模型、drafter 训练、显存超频不在默认预算。

这不是承诺哪一路一定赢。它让每个失败实验也能回答一个具体问题，并在失败时停住，不把全部未验证优化串成一项无法定位的巨大改造。

## 4. 不作的强断言

不再宣称“已达9.4/10最优”、不宣称“唯一翻倍杠杆”、不承诺200/250/500 tok/s、不把1.4×1.15×1.2当最终收益。当前只能确认：继续利用现有工程资产具有更好的风险/收益比；最终前沿由同机、同口径、多负载实测决定。

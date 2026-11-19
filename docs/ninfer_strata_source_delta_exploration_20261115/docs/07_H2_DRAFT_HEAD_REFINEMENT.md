# H2：低秩候选筛选，保留原草稿头重打分

状态：`PLANNED_NOT_RUN_SOURCE_REFINED`。用户旧 H2 已计划 further head pruning/sparse projection；本轮贡献是具体机制和淘汰规格，不是新路线或已测收益。

## 1. Donor 的真实实现

YASAKANI `launch_bdr_shead`：hidden 经 rank-512 投影，近似给全 vocab 打分，用 histogram 选 shortlist（默认512，可配），再对候选做 full-D INT8 head 重算和 top-k。OSAKANA 也有 sketch / shortlist 资产及 hidden 分布拟合工具。

“exact rescore”只相对其存储的 INT8 head 和入围候选，不是原 BF16 全词表精确 top-k。作者约 0.17GB 描述的是每次读流量估计，**不是整个 head 的显存**；full head、sketch、投影和 workspace 都还要算。

## 2. 对你的适配，不照抄格式

固定 NInfer b0 已有 `draft_head_rows=131072`、Q4G64_F16S 草稿头和 I32 token remap。Target 248320 行不变。拟做：

1. 以当前现有 proposal 的 hidden/head 身份建立 sidecar，不借 donor 不同词表/权重。
2. sketch 仅生成 shortlist；精排优先用**现有 Q4 head 指定行**，不额外复制完整 INT8 head。
3. 保留 full existing head 作为资格 oracle / fallback。任何资产缺失、identity mismatch 或未合格采样模式，走旧路。
4. 不因 H2 改 AR 步数、Target verifier、W、KV、采样/grammar；不把 D1 同时打开。

这条 Q4 selected-row rescore 是本包提出的适配，**不是 donor 已实现功能**。它可能需要新的行索引 kernel，必须维持原 scale/group/归约顺序，不能以“只是 head”免数值审阅。

## 3. 内存账先算清

示例仅用于预审：若 V'=131072、D=5120、group64 Q4每组32字节code+2字节scale，无其他padding，则现存主 head 约340MiB；这是现有资产，不是新增。一个 V'×512 INT8 sketch约64MiB，D×512 FP32投影约10MiB；还需 scales、shortlist、workspace、padding与常驻元数据。若额外复制完整 V'×D INT8 head，单这一项约640MiB，不是免费。

实际 shape、dtype、padding、资产文件、设备 arena、Graph workspace都以 R0 实际版本为准。VRAM同时记录reserved/live/peak与prefill、decode、restore各阶段；维持原context上限和OOM余量。不能为了 fit 缩短用户的长上下文，再说“H2省显存”。

## 4. 拟新增接口（未实现）

接入点：`.../runtime/text_context_impl.h::proposal_argmax`；资产绑定点：`src/targets/qwen3_8_27b/impl/load/bindings.cpp`。如实际生产树不同，R0 给出新固定路径，不直接往九月 b0 打补丁。

| 产物 | 必须字段/语义 |
|---|---|
| `draft_head_sidecar.json` | model/head/token_remap/tokenizer hashes、V'、D、rank、sketch dtype/scale、训练/构建方法与数据hash、format_version、expected bytes |
| `shortlist(hidden)` | 每 token 有界候选行、去重/越界/tie规则、实际count；不提供 Target logits |
| `rescore_original_rows` | 原 Q4 对指定行的分数；与 full head同输入这些行逐bit或沿旧已冻结容差相符 |
| `fallback(reason)` | 原全131072草稿头；不带错误 sidecar 继续推理 |

如果现场尚无合法 hidden 数据，先做静态尺寸/所有权审查，不生成随机 hidden 来证明召回。新采集 hidden 属于单独授权数据/硬件窗口，脱敏并控制保留范围；不上传到外部训练服务。

### 首个离线资产构建规格（拟议，不是已实现）

为避免“低秩”停留在概念，首版只选择**现有Q4草稿头的weight-only rank-512近似**，不与hidden训练/多rank搜索混跑：

1. 用现有codec的权威decoder解释草稿头W（V'×D），保留原行/token映射；不得读不同checkpoint或donor.shead。
   hidden必须是`proposal_argmax`最终linear实际消费的向量，包含原norm/rotation等坐标变换；不能用Target层tap或另一坐标系的草稿hidden替代。W与hidden必须在同一实际数学空间。
2. 用固定seed、固定算法/迭代数的有界randomized SVD构建正交P（D×512），C=W×P（V'×512）。算法实现、BLAS版本和seed写入资产manifest；这仅决定proposal粗筛，不改变原W。
3. C逐行对称INT8量化：scale=maxabs/127、RNE、饱和[-127,127]；全零行scale=1、codes=0。P首版保FP32。记录scale dtype、padding、构建误差和资产hash。
4. 每次近似评分为`C_hat × (P^T × hidden)`；固定top512，分数相同时原行ID升序。NaN/Inf、不完整候选或identity不符直接baselinefallback。
5. selected-row rescore仍使用原Q4 head与原算术；不从C近似恢复“完整head”，也不把候选集内最高分当全局精确最高分。

这是一套**可被淘汰的适配提议**，不是作者原样实现或已证最优。资产构建需单独的CPU/内存权限和timebox；原头解码、SVD临时矩阵也计host peak。超预算停止，不能中途降context/偷偷切GPU。先用小矩阵rank恰等于真实rank的CPU fixture核shape、P方向、row量化/重建与token映射；真实hidden召回仍按R1 holdout单独判断。若weight-only方案不合格，hidden-aware拟合属于以后新冻结适配，不在当前窗口继续扫。

## 5. 前置资格与单候选原则

先绑定当前 `head_only_ns` 和 `ar_body_ns`，只读历史 P14 9.5% 不足以过门。需要原 observer 已在此身份合格的记录，或经批准的新的有界归因窗口。

固定首个候选 rank=512 / shortlist=512，依据 donor 作为初值而非最优宣称。若尺寸/预算不合适，R1 可在**没有运行结果前**修订一次规格并重新冻结；开始资格后不得扫 rank/k 到过门。rank不同的效用空间是新合同，不续用旧预算。

资格分开：

- 选中行分数的数学一致性：必须沿原 oracle；precision mismatch 为硬失败。
- 相对原草稿头 top1 recall：预注册建议 ≥99.5%，各真实语言/工具/代码切片均报告；这只是接受率风险筛查，不是最终质量保证。
- 完整 target 的 greedy 输出与状态资格；sampled 必须单独证明实际 q / target RNG。
- accepted 正式 token / round 与 full-round成本一起看。head 微基准快而 acceptance 下降吞掉节省就关闭。

若现有 head-only 可省空间扣除 sketch/rescore/额外访存后，不能覆盖正式净收益门与1个百分点的筛查余量，不进入实现。该余量是本包提出的保守资格规则，不是作者证实的4090规律。

## 6. 测试反例

token remap有空洞/非连续；中日韩与低频代码符号；ties；NaN/Inf；零/大幅度 hidden；候选重复/越界；满/空 shortlist；sidecarhash错；首请求/复用Graph；prefill→decode/restore峰值；fallback与取消；连续fallback不得污染next draft状态。

保持 Target 全头并不能自动保证 sampled 分布：如果旧 accept使用q，新shortlist诱导的q必须实际可计算，拒绝residual也必须一致。未证明时 sampled请求直接原路；不得把以前随机MTP/完整q失败路线重新打开。

## 7. 退出条件

current head-only不够热、sidecar无法满足容量、实际recall不达预注册门、归约/词表映射不一致、AR/acceptance吞掉节省、服务/任务质量失败，均关闭 `H2_THIS_ADAPTATION`。继续保留“旧H2是计划、此次适配不成立”的记录，不删除旧计划也不伪称已经穷尽所有稀疏head算法。

# 逐项审计表

“支持”不表示本包在4090上复现；见E0–E5证据定义。外部S编号见SOURCES.md；输入报告保存在input-review。

| ID | Claude/此前方案说法 | 核查结论 | 依据 | 本包处理 |
|---|---|---|---|---|
| C01 | Kern PoC不是现网性能优化首选 | 支持方向 | Kern review §0/5；已报no-spec与MTP差别 | 停止Kern主线，NInfer增量 |
| C02 | Kern完全无可复用GPU内核 | 措辞过强；无现成可跑的SM89量化package≠源码primitive全不可移植 | Kern review §4；generic CUDA来源 | 不用此绝对说法论证，不改变停止重写决策 |
| C03 | Pi在4090、600GB总SSD、GitHub不可连 | 已被较新巡检推翻 | Kern review §2 | Mac Pi、915GiB/557free、在线先试 |
| C04 | W4目录仍是原始HF权重 | 错误 | Kern review W2实查 | 按shard/config hash，不按metadata revision认定 |
| C05 | 610/13.3意味着有nvcc13.3 | 错误 | host实查12.3+Docker13.2 | 不再升级，工具链独立锁 |
| C06 | rk8零工程+15–30%且Java3/3 | 部分支持；184K同medium+5.28%；Java沿用上一轮 | 报告12-D原文 | 新鲜rk8资格；tradeoff-only |
| C07 | checkpoint8或autoanchors应立即加 | 不支持作为默认 | 报告12干净newest-user已100%；branch串行混杂 | 条件任务T17，不重复错误探针 |
| C08 | small-T已有T1..8，W8零kernel | 被固定源码反驳 | S03/S04：编译及dispatcher到6 | T07显式建设W8或证明genericroute |
| C09 | rk4读KV的大成本是root/lattice decoder | 混淆写/读与rk2/rk4 | S05/S06；源码PackedK vs E8Root | 不把root优化推为生产收益 |
| C10 | 当前rk4是精确E8 lattice | 不成立 | S05半陪集舍入注释 | 性能任务保留既有数学，格式变更另案 |
| C11 | 上游DFlash2缺少/27B只开配置 | 上游已有；旧fork移植不止配置 | S01/S02 | binder+5层draft+q+状态+W8完整任务 |
| C12 | 19.03–16.96GiB是新增显存 | 只能作为文件差 | S02按backend选择materialize，S01 ring40MiB | artifact/device/stage peak三张账 |
| C13 | DFlash2全部可先压W4 | 部分可研究但没证明 | S02主体W8，conv/norm/selectorBF16 | W8oracle，draft-onlyW4单独变体 |
| C14 | DFlash2比同K MTP的AL只+9–12% | 部分数字不准确 | S07 MBPP3.99→4.79约20.1% | 逐任务表，不统一百分比 |
| C15 | AL高/块宽大就一定更快 | 不成立 | AL/耗时公式；不同H200/4090路径 | rate=committed/完整roundcost |
| C16 | 混合suffix必须等DFlash2 | 非必要依赖 | S09已有model-free+model-basedhybrid | 先suffix+现有MTP，catch-up成本不能漏 |
| C17 | 根据后缀频率验token即可保持采样 | 缺实际q定义 | S01拒绝采样数学 | 首版deterministic q=delta，精确残差 |
| C18 | W16验证可以几乎免费只读一次KV | 研究目标，不是可保证事实 | 多CTA/split重复load，寄存器/算术增加 | 实测tile复用和全round收益 |
| C19 | Sage已有sm89因此可直接替换 | 错误适配推断 | S11/S12 >128；本目标d256 | 新paged causal d256研发，不改两半softmax |
| C20 | d256可拆2个128分别attention | 数学错误 | softmax(sum logits)不等于独立softmax拼接 | 显式负对照 |
| C21 | A4直接吃Q4+旋转且权重零误差 | 条件冲突 | S06 rotation需重新量化；Q5不匹配 | 新artifact/新质量门，默认禁用 |
| C22 | ncu前必须全局开放计数器 | 不必要且扩大权限 | NVIDIA S15 R610权限模式 | 单次最小授权，不动modprobe |
| C23 | AL<3立即判DFlash失败 | 不完整门 | speed由AL与roundtime共同决定 | 不用单一AL阈值 |
| C24 | 1.4×1.15×1.2≈1.9最终收益 | 尚无共同条件实证 | 路线图自己标推断 | Amdahl+实测叠加，不承诺150–250t/s |
| C25 | Java3/3和needle足以证明更低精度无损 | 不足 | 样本规模与任务覆盖 | 原3题兼容、30语义、heldout/更大集分级 |
| C26 | 本机训练drafter物理上做不了 | 推荐训练配置不是不可能定理 | online recipe配置 vs离线/冻结/PEFT | 后置独立可行性研究 |
| C27 | Python runtime就是vLLM慢的根因 | 不能从语言标签推出 | 实际kernel、shape、缓存、队列数据 | donor/control角色，不做泛化速度排名 |
| C28 | 4090已接近最佳且只有这些优化有价值 | 无法证明全局最优 | 有限benchmark与未测工作负载 | 使用受约束Pareto/分阶段实证 |

## 2026-09-09 复核裁定（Claude 对照实机与源码）

对上表针对 Claude 方案的纠正逐条复核，结果如下；证据在 `../docs/22 §2`。

| ID | 裁定 | 说明 |
|---|---|---|
| C08 | **成立** | `src/CMakeLists.txt:278`、`gqa_attention_decode.cu:19/239/243`；W8 需 T07 |
| C09 / C10 | **成立** | rk4 读路径是 PackedK unpack；lattice 是 encode-side；半陪集近似注释在 `gqa_attention_decode_i8.cuh:269` |
| C12 | 成立但无实际差别 | 权重 1:1 常驻，按 inventory 累加的常驻差就是 2.074 GiB |
| C14 | **成立** | 范围 +8.8–20.1% |
| C19 | **成立** | Sage 仅 head_dim 64/128 |
| C05 | 成立（针对 kern PoC） | 宿主 nvcc 12.3.107，容器 13.2 |
| C03 | 针对 kern PoC | Pi 在 Mac 正确；但示例路径 `~/.pi/bin/pi` 错误，实为 `~/.nvm/versions/node/v22.19.0/bin/pi`（已改 `configs/local.example.json`） |
| C20 | 归因不成立 | 两份 Claude 文档均无"d256 拆两个 128 各自 softmax"说法；作为负对照护栏保留 |
| C28 | 归因不成立 | 唯一的 "9.4" 是 kern review 的小节号；非评分 |
| C23 | 表述偏强 | roadmap 原文是"AL<3.0 → 先做 P2/P3"，是重排序不是否决 |
| C24 | 成立 | roadmap 已标推断；本包改为给**有界估算与停止点**（`../docs/21 §4`），不是完全不给数字 |
| C06 | 部分支持 → 更新 | 200192 决策后 rk8@200192 通过容量门，但与 DFlash2 W8 争同一块显存，二选一 |
| C11 / C13 | 支持 → 补充 | 44a 对 DFlash 后端**无 session persistence**（`session_snapshot_impl.h:342/534`），T10 是新功能；draft W4 variant 降为条件实验 |
| C16 / C17 | 支持 → 具体化 | 首版改为 MTP 链延长（零 bridge，W≤6），one-hot q 走 44a 已有 exact rejection sampling |
| 其余 | 护栏 | 不影响决策 |

## 未验证而保留的假设

DFlash2在NInfer same-target medium上的AL与吞吐；suffix+MTP bridge实际成本；W8/W16在rk4/184K上的全round改善；W8companion在262K预算内**已算出不成立**、在200192下预计余量≈1.2GiB（22 §3，待T08 loader plan实测）；新的d256FP8路径质量；长期soak。没有任何一项被本包标为已完成。

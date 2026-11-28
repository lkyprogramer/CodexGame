# 版本变更

## v3.0.27 · 2026-11-28

T45 PASS：decode 按“只有一行的 verify”执行（fork `d1f4012`，默认），投机解码与无草稿逐 token 相同（DSpark 各 k 与 DFlash2 的 token SHA 一致，V8 分歧 0），完整 G2 通过；plain decode 1K +4.9%、32K +8.4%、128K +18.7%（73.9 → 87.7 tok/s），T14 无草稿 149.6 tok/s。K12 按原设计 NO_BENEFIT（Q8_0 共 6 GB，重排代价大；8 字节加载反而慢 36%，K 切 8 份只快 1.6%），其价值由 T45 的统一 kernel 实现。新增 `astral t45-diff`、`tools/t45/`。

## v3.0.26 · 2026-11-28

T43 PASS。Phase 2：fork `d586fec` 的 `serve --draft-alt` 按上下文长度换草稿器，DFlash2 + DSpark（≥ 4096 token）在 T21 上达到 257.6 tok/s（DSpark 单用 222.5，×1.16），每个桶都取到两者中较好的。Phase 3：开 DFlash2 的最大容量为 122880（DSpark 为 114688；推断的 132096 不成立），120K prompt 上 94–95 tok/s（plain 76.1）；长上下文单 prompt 的结果方向不一致（32K DSpark 好、64K DFlash2 好）。新增 `tools/t43/t43_p3.sh`。

## v3.0.25 · 2026-11-28

T43 Phase 1 PASS：DFlash2 草稿器在 Astral 实现（fork `509062f`），接受长度与 llama.cpp 参考一致；T21 协议下相对 DSpark 全体 ×1.13（burst）/ ×1.22（固定 k7），短 prompt ×1.20–1.22，长文档 ×0.89–0.91（进入 Phase 2 的按桶选草稿器）；完整 G2 不变。T46 PASS：评估闭环工具 `tools/t46/`，top-k 加尾桶 KL 在 k = 2048 时与全词表 KL 差 0.43%（k = 128 为 4.8%，未达标），默认改为 2048。`t21_cost.sh` 增加 `DRAFT` / `ALT`。

## v3.0.24 · 2026-11-28

T42 PASS：fork `df7f95b` 的热点重测（decode 1K / 32K / 128K、DSpark 一轮、prefill 2K / 32K）。排序：T43 → K12 → T44 → K15 → K13（先把 prefill 的 `gemv_f32` 改 GEMM）→ K14 → T47。

## v3.0.23 · 2026-11-28

T43 Phase 0-A 过门：llama.cpp b12823 上 A1 + DFlash2 的接受长度相对 DSpark 为 sn ×1.70、sc ×1.45，长文档 ×0.82–0.85；llama.cpp 实测 121.3 → 150.3 tok/s；按 Astral 的 T21 成本表预测混合负载 +19%–26%。新增 `tools/t43/`（目标 shim、接受率测试与汇总）。下一步 Phase 1：Astral 实现。

## v3.0.22 · 2026-11-28

T41 PASS：T25 判定工具改为 fail-closed（负控制按 `negs_expect.json` 登记的期望并入判定，缺件 / NaN / 重复位置判 INCOMPLETE），`t25_e.sh` 传播返回码，`t27_share.sh` 只解析 prefill 字段；新增 `tests/test_t25_judge.py`。T25 E 重判仍 PASS，T27 重算结论不变。用户确认采用 num-4L。

## v3.0.21 · 2026-11-28

并入方案 13（S41）、MTB 方案（S42），以及 TensorFold、DFlash2、Mirage / TileLang / Basalt、LoopTitan / QDA / Self-Rewriting 的源码与论文调研（S43–S46；报告在 `research/20261128/`）。用户把目标定为在 4090 上做最极致的定制，不考虑兼容，所以有损与改模型的候选正式进入计划，按 [05](docs/05_validation.md) §6.8 分开命名、分开验收。新增任务 T37–T47（DFlash2 草稿器 T43、全局 KV FP8 / INT8 T44、decode ≡ verify T45、评估闭环 T46、有损专家剪枝 T47、判定工具 fail-closed T41、热点重测 T42，以及改模型的 T37–T40），调优候选 K12–K17，研究项 R15；K7 改判为不做；T33 更正 slot 数并暂缓。核实了方案对已有工作的 8 条更正（[07](docs/07_tasks.md) 的 v3.0.21 记录），其中 T25 E 的判定不是 fail-closed、T27 的计时解析拼接两条属实，由 T41 修复后重判；已有结论不变。清单改由 `tools/make_manifest.sh` 只对 git 可见的文件生成（原清单收了 3 个被忽略的日志）。本版只改文档与工具，4090 上没有运行任何新实验。

## v3.0.20 · 2026-11-28

fork `e83ef7d`、`df7f95b`。T27、T26 NO_BENEFIT：coda prefill 裁剪只快 2.2–4.0%，草稿 base head 只占 4.8%。T25 长上下文：D 组诊断显示 llama.cpp 自身换批长就会在高 margin 位置翻转，于是在 E 运行之前冻结长文规则 num-4L（[05](docs/05_validation.md) §6.6，**待用户确认**）。E 集 PASS，但已撤回的 dp4a 负控制判不出来。F16 草稿 KV 与 f32 逐 token 相同，改为默认，DSpark 最大 114688；完整 G2 不变。T28 shadow NO_BENEFIT：远历史质量分散，oracle 保留 1/2 时最大漏失仍有 0.22–0.37，可证明安全的跳读为零。T32（L0）：A4 LS 一致率 0.90 / 0.94（100K 为 0.975），A4 + DSpark 200.2 tok/s；门 LS 继续、AD-G0 都不通过，T34 NO_BENEFIT，AD 降为机制研究；更深方向等 AD01。

## v3.0.19 · 2026-11-27

T21 PASS（fork `7108b78`，`tools/t21/`）。成本表与接受分布表明 burst 策略已接近各负载桶最优的固定 k，保留默认；BF16 草稿无收益；草稿 sliding-window K/V 改为 ring 后逐位相同，DSpark 最大容量 73728 → 106496（可选 FP16 为 114688）。并入方案 12（S40，GPT 的自适应循环方案），核实后在原文 §16 补充现场更正、无损的循环深度自推测路线与各模型的探索编排；新增 T32–T36、[06](docs/06_loop_research.md) R14。

## v3.0.18 · 2026-11-27

T16 第 2 轮 PASS（fork `aa837c7`）。sm_89 上 DSpark 的 2–8 行 Q8_0 乘法改走 dp4a，DSpark 从 173.9 提到 206.3 tok/s，相对无草稿 1.44×，G2 全部通过（含 T20 B 组）。**更正 v3.0.16**：第 1 轮的 G2 漏跑了 T20，decode dp4a 让 B 组 decode 的 num-3 FAIL（kl.max 比值 3.55），已撤回；无草稿回到 142.0 tok/s。`tools/t16/t16_g2.sh` 补入 T20，新增 `t16_k2b.sh`。

## v3.0.17 · 2026-11-27

并入方案 11（S37，原文保留在仓库 `docs/11_inkling4090_new_optimization_plan_20261127.md`），先按 fork `3f5a49d` 核实。

- **新增任务**：T26 草稿 head 完整分数筛选、T27 末层 coda 的 prefill 裁剪、T28 全局远块稀疏（先 shadow），状态均为 NOT_RUN；T29 编辑复用、T30 GPU 连续生成暂缓（T30 由 T16 的主机侧计时否决：0.3%，否决线为 2%）；T31 GSQ-RCO 资产评估（可选，暂缓）。
- **核实时的新测量**：现有开关 `ASTRAL_SMALL_DP4A=1` 把小批 Q8_0 改走 dp4a，DSpark 快 1.20×，尚未做 G2。另有一轮 DSpark 的 kernel 分解：小批 tensor-core GEMV 约占 40%，head 每轮调用两次，各约 1.26 ms。脚本在 `tools/t16/t16_spec_ab.sh`、`t16_specprof.sh`。
- **路线调整**：T16 第 2 轮 → T21 → T27 → T26 → T25 长上下文 → T28。
- **资产评估**：GSQ-RCO 两个仓库（S38、S39）的 IQ / K 系列类型 Astral 不支持，精度也低于 A1，所以不替换 A1；它们的 dspark GGUF 与 A3 的 `mtp.safetensors` 是同一份权重，草稿用 BF16 还是 Q8_0 作为一臂并入 T21（[01](docs/01_model.md) §4.1）。
- 改动的文档：00、01、04、05、07、09，以及 README。

## v3.0.16 · 2026-11-27

T16 第 1 轮 PASS（fork `3f5a49d`，`tools/t16/`）。热点表显示：decode 的注意力输入投影融合 GEMV（`multi_mma`）占 GPU 时间的 26%，带宽只有约一半。唯一的候选是 K2，即 sm_89 的 decode 改走 dp4a。结果：无草稿服务基准 143.1 → 156.6 tok/s（llama.cpp 的 2.10×）。G2 全部复判通过（V3–V6、V8，C 组 num-3）。DSpark 相对无草稿的加速降到 1.09×，交给 T21。

## v3.0.15 · 2026-11-27

用户确认了执行顺序和两项决策：长上下文按 [05](docs/05_validation.md) §6.6 的方案判定（D 组作固定回归，规则先冻结，再用独立的 E 集验证）；G4 改为“4090 显存能放下的最大上下文”，不强制 128K（[00](docs/00_plan.md) §2）。

- T22 PASS（fork `744e32a`，`tools/t22/`）：`quantize` 写 FP16 平面；GEMM 自测先在旧代码上复现失败，修复后 93/93；模型路径逐位不变。
- T17 PASS（fork `9593eb4`，`tools/t17/`）：8K 内与旧构建逐位一致；16K / 32K 按 V4 通过；128K 能跑，pass key 9/9 命中；不开草稿最大 132096，开 DSpark 最大 73728；短上下文 decode 慢 0.6–0.7%。v3.0.14 新加的几项边界用例转入 T25。
- 工具：新增 `t17c_fit.sh`（最大上下文探测）、`t17_needle.sh`（从 t17b 拆出；补上 `serve` 必需的 `--checkpoint`，推理强度设为 none）；4090 没有 `bc`，计时改用 awk。

## v3.0.14 · 2026-11-27

并入方案 10（[09](docs/09_sources.md) S32）。方案里关于 fork 代码的结论逐条对照源码核实。

- [07](docs/07_tasks.md)：新增 T22（数值测试的输入合同）、T23（显式执行映射）、T24（每遍消息预计算）、T25（T20 增补）和 R11–R13；T16 增加候选命中记录，T17 补边界用例和坐标划分，T21 写入成本模型与草稿 KV 压缩；执行顺序定为 T22 → T17 → T16（T24 是其候选）→ T21。
- 更正两处已有记录。一是 T19 加的 GEMM split-K 自测，输入平面为零（[05](docs/05_validation.md) §6.5；修复本身另有证据）。二是 T20 的 D 组，argmax 硬门同样不通过（[05](docs/05_validation.md) §6.6）。长上下文判定的建议改成：D 组留作固定回归，判定规则先冻结，再用独立的 E 集验证。
- [05](docs/05_validation.md)：新增 §6.7，包括测试输入的有效性要求、负控制、候选命中、请求复用和三种输出模式；变化类别细分；§7 的运行记录增加二进制 hash、工作区差异 hash、plan 指纹和 cache 布局。
- [04](docs/04_astral_fork.md)：§2 新增三项代码事实（slot / visit / tap 映射，FP16 激活平面，草稿 KV）；新增 WP-G；调优候选扩到 K8–K11；§3.2 记录 T17 选用“额外容量”环，方案的“ring + delta”作为后续候选；§5 补边界用例。
- [06](docs/06_loop_research.md)：新增 visit / slot 表、树推测的前置条件、R11–R13，以及 §6 迁移边界。[01](docs/01_model.md) §3 新增 T17 实际 KV 与 DSpark 草稿 KV 两行，并说明 128K 时开草稿放不下。[09](docs/09_sources.md) 新增 S32–S36。
- 方案文件留在仓库原位置，没有移进本包，所以专题数仍是 10。`tools/check_package.py` 的研究编号范围改为 R1–R13。

## v3.0.13 · 2026-11-26

T18 完成：fork `02259e1` 的 `ASTRAL_PASSES` 与 varloop（A4）原生加载。A1 默认三遍逐位不变；A4 的 1–5 遍运行记录与 6 / 10 遍外推，A1 截断对照。记录见 [07](docs/07_tasks.md)。

## v3.0.12 · 2026-11-26

T15 完成：fork `2c2f424` 的 `astral trace` 只读探针（schema 见 fork `docs/trace.md`）；探针关、探针开、eager 三者逐位一致，decode 速度不变，主机重算与 GPU 输出对账误差 ≤ 1.1e-6。记录见 [07](docs/07_tasks.md)；[06](docs/06_loop_research.md) §3 注明实现范围。

## v3.0.11 · 2026-11-26

T20 完成（[07](docs/07_tasks.md)）：fork `18bf3e3` 新增 decode 路径与 DSpark verify 行的 logits 导出；保留集 B 上 prefill、decode、verify 2 / 4 / 8 行按 num-3 全部通过；自由生成首个分歧都在近平局处；c4096 密集 KLD 按 V4 公式通过。长文档 64 个边界位置按 num-3 FAIL，原因是双峰分岔位置（llama 自身也有），[05](docs/05_validation.md) §5 覆盖表、§6.6；长上下文判定口径的建议待用户决定。

## v3.0.10 · 2026-11-26

T19 完成并改判 PASS：修复后 Astral prefill / step 两次运行 208 个文件逐位相同；V7 按 num-3 在保留集 C（80 个位置）上通过，Astral prefill 对 step 的差异是 llama.cpp 自身 ub512 对逐 token 差异的 0.36–0.87 倍；`verify-model` 与 128 token 贪心输出不变。G2 解除“有条件”。结果在 `tools/t19/results_c/`。

## v3.0.9 · 2026-11-26

查清并修复 Astral prefill 的运行间不确定性（两条 split-K 路径的 float `atomicAdd`；fork `35de94a` 改为分片写工作区、按固定顺序归约，16 token prefill +2.5%，更长无差别），[05](docs/05_validation.md) §6.5。用户采用 V7 的 num-3（同位置配对比值，概率加权的窗口差），fork `f8c976e` 实现 `judge-paired`；新增保留集 C（`tools/t19/prompts_set_c.json`），在其结果出来之前冻结。

## v3.0.8 · 2026-11-26

执行 T19。fork 新增 `astral dump-final-logits`、`bench/llamacpp_compare/final_logits.cpp`、`logit_compare.py`（含离线测试，`a8ca269`）；本包新增 `tools/t19/`（manifest、导出、判定脚本、冻结的规则与小体量结果）。按先冻结规则（`92f4c40`）再看候选的顺序，V7 num-2 在 A、B 两组都判 FAIL；分析表明失败来自规则的两个缺陷（窗口 max 被极小概率 token 主导；绝对限值不能跨位置分布迁移），同位置上 Astral 的 prefill / step 差异与 llama.cpp 自身的 ub512 / 逐 token 差异同量级。num-3 提案写在 [05](docs/05_validation.md) §6.4，待用户决定。另发现 Astral prefill 路径两次运行之间不逐位一致（§6.5），[06](docs/06_loop_research.md) 的逐位一致要求限定在 step 路径。

## v3.0.7 · 2026-11-26

逐条核实用户提交的研究评审（仓库 `docs/Inkling-4090-Lab-v3-Research-Review-2026-11-26.md`，[09](docs/09_sources.md) S31）后修订文档。Astral 源码相关结论对照 fork 源码核实，外部来源 13 条按固定 commit 抓原文核对（9 条属实，4 条部分属实，按原文修正了表述）。

- **验证（[05](docs/05_validation.md) §5–§7）**：V7 在 v3.0.4 复判时两侧不是同一统计量（原始 logit 对 u16 log-prob、窗口与 KL 定义不同、16 个末位对 2040 个位置），T12 的 V7 降为“有条件通过，待 T19 复核”；写明各项 PASS 的实际覆盖范围；起草统一数值口径 num-2、三类噪声对照、阈值校准规则和 `run.json` 记录格式。已批准的阈值不变。评审 §3.5 的前提（缺少生成提示）来自 T13 初稿的误记，已不成立，不需要因模板问题重跑。
- **任务（[07](docs/07_tasks.md)）**：T04 关闭为 PASS；新增 T19（口径复判）、T20（覆盖补测）、T21（DSpark 成本模型）；T15–T18 按评审 RV-03 / 05 / 06 / 07 重写交付物；研究依赖拆开（R4 不再等 T17）。
- **代码地图（[04](docs/04_astral_fork.md)）**：默认解码注意力是已有的 split-K online softmax，`logit[MAX_CTX]` 只在 simple 路径；8192 上限分散在四处；WP-D 改为四段并补上 SWA 环形缓冲的同批覆盖问题与边界用例；新增调优候选 K1–K7；fork 已公开。
- **研究（[06](docs/06_loop_research.md)）**：重写 R1–R7（坐标与状态约定、tanh 门、三种读出、R4 三臂按原文核实），新增 R8（量化误差经循环传播）、R9（历史深度与当前深度）、R10（局部稳定性，可选），KV 压缩降为局部实验。
- **其他**：[00](docs/00_plan.md) 的 330 tok/s 带宽上限与 launch-bound 改为待测假设（原算式不自洽）；[01](docs/01_model.md) 补 varloop 的 1:2:6:2:1 训练方式、随遍数变化的状态预算；[03](docs/03_engine_landscape.md) 补齐外部数字的条件、重新定位 v2 删除的参考项目；[09](docs/09_sources.md) 固定 S21，新增 S25–S31；[08](docs/08_runbooks.md) 标明命令模板与已执行脚本的区别；[VALIDATION](VALIDATION.md) 标为历史记录；`tools/check_package.py` 支持 R1–R10 和合并的研究行。

## v3.0.6 · 2026-11-26

Astral fork 拆成独立公开仓库 [lkyprogramer/inkling-4090-engine](https://github.com/lkyprogramer/inkling-4090-engine)：删除 `patches/astral/`，通用分析脚本迁到 fork 的 `bench/llamacpp_compare/`（新旧名对照见 [08](docs/08_runbooks.md) §9）。按评审（`docs/Inkling-4090-Lab-v3-Research-Review-2026-11-26.md` §4.1）核实源码后，更正 [04](docs/04_astral_fork.md)：Inkling 的预填走 `mma3`，不是 `mma5`。

## v3.0.5 · 2026-11-26

T14 性能基线完成，G3 通过：Astral 无草稿 143.1 tok/s，是同一 GGUF 下 llama.cpp 的 1.92 倍。脚本在 `tools/t14/`。另外更正 T13 记录：prompt 格式本来就对（Inkling 模板没有生成提示，模型自己输出 `<|message_model|>`），初稿把接受率低归因于缺少生成提示，是误判。

## v3.0.4 · 2026-11-26

经用户同意修订 V7 阈值（[05](docs/05_validation.md) §3）：由“全词表最大绝对差 ≤ 1.0 logit”改为相对 llama.cpp 自身噪声底的判定（概率窗口内最大差 ≤ N0_near_p99，KL ≤ N0_p99）。依据是 T12 的实测：llama.cpp 自身批量对逐 token 时，19.4% 的位置超过 1.0。按新阈值，T12 复判为 PASS。

## v3.0.3 · 2026-11-26

T11–T13 执行完毕。T11 定位并修复了 Astral 的跨 stream 同步缺陷（T07 的 MXFP4 失败由此引起），T07 改判 PASS；T12 的 V4–V6 通过，V7 按冻结阈值判 FAIL，并附上 llama.cpp 自身噪声的对照数据，阈值待用户决定；T13 的 V8 通过。W2 的脚本放在 `tools/w2/`。

## v3.0.2 · 2026-11-26

W1（T07–T10）执行完毕，结果记在 [07](docs/07_tasks.md)：T08、T09、T10 PASS；T07 的 selftest 有 4 项 MXFP4 失败（Qwen 路径，Inkling 不用），定位工作并入 T11。W1 实际使用的脚本放在 `tools/w1/`。

## v3.0.1 · 2026-11-26

P0 执行后的修正：conda-forge 改走清华镜像；包列表补上 `cuda-driver-dev`、`cuda-nvml-dev`（llama.cpp 需要）；Astral fatbin 的路径改为 `target/release/build/astral-kernels-src/*/out/`；[07](docs/07_tasks.md) 记录 T00–T06 的结果。Strata 已按用户指示停止，恢复前 GPU 任务直接执行，不再经过 `lab_window.sh`。

## v3.0 · 2026-11-26（Asia/Shanghai）

全面重写，取代 `docs/atomic-inkling-4090-plan-v2.0`（v2.0/v2.1）。

- **方向变化**：目标从“以 Atomic 为底座的服务候选”改为“自有 Rust 单模型引擎 + 循环研究”。依据是社区调研（[03](docs/03_engine_landscape.md)）：Inkling-2-Mini 的瓶颈是大量小算子而非带宽，专用单模型引擎在 4090 上比通用框架快 2–4 倍；而 Atomic 落后上游且其显存预算/专家流式能力在 24 GB + PCIe3 上用不上。
- **用户决策**：Rust（Astral fork）；用户目录安装 CUDA 12.8；先用量化 GGUF；不动驱动。
- **删除**：Atomic 移植、Ghost、Magnitude、CUDA Rust 形式证明、LoomKV Tier/Pool、2DSD/LoopCD 的服务化路线、148 项计划测试和 44 任务 DAG。其中仍有价值的研究点并入 [06](docs/06_loop_research.md)。
- **保留**：现场事实与停服流程、证据纪律、配对统计工具、上游 llama.cpp 作为参考的结论（v2.1 §43）。
- **新增发现**：Astral 当前上下文硬上限 8192（`MAX_CTX`，注意力 logits 放在共享内存），且 48 个 slot 全部按满容量分配 KV；长上下文是移植的独立工作包（[04](docs/04_astral_fork.md) §5）。

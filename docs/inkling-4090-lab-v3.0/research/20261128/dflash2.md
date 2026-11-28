# DFlash2 草稿器在 4090 / Astral 上替换或叠加原生 DSpark 的研究

日期：2026-11-28 ｜ 范围：只读研究（未编译、未在 GPU 上运行任何程序） ｜ 对象：A1（unsloth UD-Q4_K_XL）+ Astral fork（`df7f95b`）+ A5（incoai/Inkling-2-Mini-DFlash2 @4f9088e）

标注约定：**【源码】** 引用文件:行号；**【自报】** 对方 README / 博客 / PR 的数字；**【实验包】** v3.0 已有实测；**【推断】** 我的估算或判断，未经实测。

---

## 0. 结论

1. **可以替换，且是目前看到的 4090 上 decode 提速最大的单项无损候选。** DFlash2 与 DSpark 用完全相同的 4 个 tap（visit 5 / 23 / 41 / 48，48 = final norm），verify 侧（anchor + ≤7 草稿 = ≤8 行、per-k graph、dp4a `multi_t`、conv rollback、accept）一行都不用改；只换 `store_ctx`（context ingest）和 `draft()` 两段。【源码 + 推断】
2. **收益估算（推断）：T21 混合负载 +25%～+60%，中心约 +40%（206 → 约 290 tok/s）。** 依据：T21 的 4090 轮次成本 C(k) ≈ 8.3 + 0.96k ms【实验包】，套上 GB10/vLLM 贪心下实测的逐位置接受曲线【自报】：prose 类 DSpark 最优约 182 tok/s（k=2）→ DFlash2 约 290 tok/s（k=7，+60%）；code 类约 +24%。DFlash2 的深位置条件接受率约 0.9（曲线很平），正好对冲了 4090 上“每多 verify 一行 ≈ 0.96 ms”的 MoE 成本。
3. **草稿显存与上下文无关**：5 层全是 2048 滑窗，每流一个约 42 MB 的 ring；DSpark 有一个全局层，草稿 KV 随上下文增长（4 KiB/位置，128K 时 0.5 GiB）。推断开草稿的最大上下文可从 114,688 回到引擎上限 132,096。
4. **“叠加 DSpark”不值得**：逐位置接受率 DFlash2 在每个位置都高于 DSpark【自报】，两个都跑等于草稿成本翻倍；唯一可能的叠加是**按请求切换**（长文档 copy 类若 DSpark 的全局层更好）。
5. **树 / 多路径 verify：在 per-k graph 下工程上可行，但在 4090 上预期是负收益**（一行 0.96 ms，最好的兄弟节点也只多 ~0.08 token），除非实测兄弟行的边际成本 ≤ 约 0.3 ms。所有已知的 Inkling DFlash2 实现都是单链。
6. **A1 GGUF 搭配风险：低～中**。DFlash2 针对官方 `thinkingmachines/Inkling-2-Mini`（ModelOpt NVFP4/MXFP8）训练和评测；A1 的专家同为 NVFP4，注意力 / head / embedding 是 Q8_0。llama.cpp 已在 Q4_K_M 目标上测出 DFlash2 接受率不降【自报】。用 Phase 0 直接在 A1 上测，不靠推理。
7. **先离线测接受率再写 CUDA**：llama.cpp **≥ b12785** 已原生支持 Inkling DFlash2（PR #33073，2026-11-26 合入；实验包现用 b12751 不含）。这是零 Astral 代码的最快路径。

---

## 1. 材料与本地副本

| 材料 | 本地路径 | 体积 / 版本 |
|---|---|---|
| TensorFold RTX 5090 recipe（patch 0018/0019/0020/0026） | `/root/github/inkling-research/repos/Inkling-2-Mini-RTX-5090-TensorFold/patches/` | 已有 |
| tonyd2wild DGX Spark recipe（vLLM DFlash2 补丁、TensorFold 0018 原版、CPU 参考 `inkling2_dflash2_ref.py`、GB10 结果） | `/root/github/inkling-research/repos/Inkling-2-Mini-NVFP4-DGX-Spark/` | `--depth 1`，3.2 MB |
| z-lab/dflash（DFlash/DFlash2 参考实现、rejection sampling） | `/root/github/inkling-research/repos/dflash/` | `--depth 1`，268 KB |
| HF A5 小文件（README、config.json、`sglang_inkling_dflash2.py`、图） | `/root/github/inkling-research/hf/Inkling-2-Mini-DFlash2/` | rev `4f9088ea…`，约 300 KB；权重未下载 |
| A5 safetensors 张量目录 | 4090 上 `/home/hhtele/inkling-lab-v3/models/dflash2/model.safetensors` 只读文件头 | 494,983,424 参数，全 BF16 |
| DFlash 论文 arXiv 2602.06036 | `/root/github/inkling-research/papers/dflash_2602.06036.pdf` | 0.5 MB（本机无 poppler，内容经 arXiv HTML 读取） |
| TensorFold 上游 `draft_tree.zig`（Landing 校准、best-first 树）、`lone_costs.zig` | gh api 读取 ashhart/TensorFold HEAD（2026-11-28），临时副本在 scratchpad | 上游 HEAD，与 recipe 固定的 `dc2ca8a` 可能不同 |
| DFlash2 博客 inco.ai/blog/dflash2 | WebFetch | 训练数据未公开 |

---

## 2. DFlash2 的精确结构与数学

记 H = 2304，块 B = 8（第 0 行 = pending token，第 1–7 行 = mask），32 个 Q 头 / 8 个 KV 头 × 128，FFN 6912，滑窗 W = 2048，mask token = 200056，softcap = 30，selector rank 256，top-k = 16。【源码】`0018:27-36`（dflash.cu 常量）、`0018:467-496`（mini_dflash.zig 常量）；config 校验 `0018:1396-1428`；HF `config.json`。

### 2.1 taps（哪些 visit）
- `target_layer_ids = [5, 23, 41, 48]`，与 DSpark 的 `mtp_config.target_layer_ids` 完全相同（4090 上 A3 config 读出）。【源码】`0018:467`；HF config.json。
- 语义是 Inkling 的 **visit 编号**而不是物理层：48 = 访问数 = final norm 之后的状态。SGLang 补丁直接把 DFlash 的捕获函数别名到 DSpark 的（`sglang_inkling_dflash2.py:39-41`）；vLLM 的通用 DFlash 路径原来会 +1（取到 6/24/42/49），必须改成原样使用（DGX README:378）；llama.cpp 为此新增 GGUF 键 `target_visits`（PR #33073）。
- Astral 的 DSpark 已经采集这 4 个特征：“the residual stream entering layer visits 5, 23 and 41, and the final-norm output”【源码】`crates/model/src/dspark.rs:7`，存在 `Spec.feats`（f32 `[4][tmax][2304]`）。因为 Astral 的 DSpark 已对齐 vLLM（T13 V8），而 SGLang / vLLM 的 DFlash2 用的就是 DSpark 的捕获点，所以 **Astral 现有 taps 可直接喂给 DFlash2**。区别只是 DSpark 每层用 softmax(fuse_weight) 做 4 路加权（`mix4`），DFlash2 是拼接后过 `fc`。
- 拓扑解读【推断】：visit 5 = prelude 末层（物理层 5，全局层）的输入，23 = core 第 2 遍中段，41 = core 第 3 遍最后一个 visit（物理层 17，全局层）的输入，48 = coda 之后的 final norm。

### 2.2 context ingest（committed token → ring）
对每个已提交位置 p，特征 f_p = concat(tap5, tap23, tap41, tap48) ∈ R^{9216}：
- c_p = RMSNorm_hidden( W_fc · f_p )，W_fc ∈ R^{2304×9216}
- 每层 ℓ：K_ℓ(p) = RoPE_p( RMSNorm_k( W_k^ℓ c_p ) )，V_ℓ(p) = W_v^ℓ c_p，写到 ring 槽 p mod 2048。
- 注意 context 的 K/V **复用每层自己的 k_proj / v_proj**，不经过该层的 input_layernorm；这就是 DFlash 论文的 “KV injection”（目标特征注入每个草稿层的 K/V，而不是只进输入层）。
- 【源码】`0018:1131-1146`（`ingest`：fc → hidden_norm → 每层 `kv` GEMM → `tf_ink2d_ctx_kv`）、kernel `0018:140-153`；CPU 参考 `inkling2_dflash2_ref.py:163-164, 181-182`；论文 §3 / 附录 A.3（arXiv HTML）。
- ring 只收**已提交**的行：absorb 时只 ingest 最后 2048 行（`0018:1160-1162`），被拒绝的行不会进 ring，因此**没有草稿侧回滚**；回退的位置下次被原地覆盖（`0018:1164`）。0019 进一步让 prompt ingest 只做 `[plen−2048, plen)`（`0019:117-138`）。
- RoPE：Qwen3 per-head RMSNorm + neox rotate-half，θ = 10000（`0018:48-65`）。Astral 的 `astral_dsp_head_prep` 是同一约定（`dspark.cu:112` 起，neox，θ 参数化）。

### 2.3 block pass（一次前向出 7 个位置）
输入 x_t = RMSNorm_embed( E[id_t] )，id = [pending, 200056 ×7]，位置 A..A+7（A = pending 的位置）。**必须经过目标的 `embed_norm`**（vLLM 补丁 (b)，DGX README:379；llama.cpp PR #33049 也是这一项修复让接受率从约 0 回到正常）。【源码】`0018:1182`、`0018:1308-1311`。

每层（`0018:1184-1226`，CPU 参考 `ref.py:167-203`）：
1. h = RMSNorm_in(x)；dyn_a = W_aproj · h ∈ R^{576} = [输入侧/输出侧][tap0/tap1][144 组]。
2. **两 tap 动态因果卷积（块内、无状态）**：Conv(z)_t[c] = (b_0[c] + d_t[0][g(c)])·z_t[c] + 1[t>0]·(b_1[c] + d_t[1][g(c)])·z_{t−1}[c]，g(c) = ⌊c/16⌋（16 通道共享一个动态系数）。输入侧卷积作用于 h，输出侧作用于 o_proj 的输出，然后加回残差。【源码】`0018:91-105`；z-lab `dflash/model.py` `_grouped_dynamic_convolve`。第 0 行只用 tap0；第 1 行读第 0 行（即“最后一个已验证 token”）。
3. q/k/v = W_qkv·Conv_in(h)，q_norm / k_norm + RoPE。
4. **注意力：块内非因果**，第 t 行看 ring 中 p > A + t − 2048 的 context 位置 + 全部 8 个块 key（每行自己的窗口下界）。【源码】`0018:155-217`（`lo = p − (WIN−1)`，`0018:166-167`）；`ref.py:187-189`。
5. o_proj → Conv_out → 残差；MLP 同样包在 `mlp_conv` 的输入 / 输出两侧卷积里，SwiGLU。
最后 RMSNorm(norm)。

### 2.4 head、top-16 与 candidate selector
- 第 1–7 行过**目标的 LM head**（DFlash2 没有自己的 head），在真实词表 200,058（不是 padded 的 201,024）内取 top-16（值 + id，平局取小 id）。【源码】`0018:1230-1247`、`0018:235-317`；0026 改成两遍 radix（`0026:28-152`，48/48 token SHA 一致）。
- selector 打分（`0018:343-408`；`ref.py:131-145`）：
  g_t = W_h · ĥ_t ∈ R^{256}（ĥ_t 为最终 norm 后隐状态），
  S_t(c | prev) = 30 · tanh( ( u_t(c) + ⟨ P[prev] ⊙ g_t , S[c] ⟩ ) / 30 )，
  P、S 是 [vocab × 256] 的 predecessor / successor codebook，u_t(c) 是原始 head logit。
  `selector_softcap_mode = "after_correction"`：**softcap 加在 unary + edge 之后**；顺序错了会改变 argmax（vLLM 补丁 (a)、llama.cpp `selector_softcap_after_correction`）。
- **路径而非树**：从 pending token 出发贪心走一条路径，prev ← 本步选中的 token（`0018:366-386`）。每步额外输出 chance_t = softmax_{16}(S_t)[选中项]（温度 1），供 round planner 用（`0018:398-403`）。
- 博客：Recall@16 在位置 0 为 99.5%，路径选择把 Qwen3-4B 的接受长度从 4.27 提到 4.61，oracle 上限 6.79【自报】——说明 top-16 晶格里还有很大的“选路”空间（树 / 更好 selector 的理论上限）。

### 2.5 采样时如何保持分布
三种做法，都是无损的：
1. **rejection sampling（z-lab 参考 / vLLM “candidate-walk with rejection”）**：沿路径在 16 个候选上按 q_t = softmax(S_t/T) 采样并记录 q；verify 用标准 speculative sampling：以 min(1, p/q) 接受，拒绝时从 (p − q)+ 归一化重采样（q 在 top-16 外为 0）。【源码】`repos/dflash/dflash/model.py` `_rejection_sample` 与 `CandidateSelector.select`。
2. **keyed race / Gumbel 耦合（TensorFold MiaAI 版）**：目标采样器本身是 argmax_id( logit/T − log(−log u(seed,pos,id)) ) 的 keyed race；草稿在自己的 16 个候选上用**同一组 keyed 噪声**算 race 赢家（`0018:319-341, 388`）。输出完全由目标的 keyed 采样决定，草稿只影响能否“猜中” → 无损；接受率略低于最优耦合但无需保存 q。tonyd2wild 的 0018 原版对采样请求只给贪心草稿（DGX README:531）。
3. 贪心：接受最长相等前缀 + 目标的 bonus token。
**Astral 目前只有贪心**（`crates/api/src/lib.rs:10`：temperature / top_p / seed 被忽略），所以采样问题只在将来加采样时才相关。

### 2.6 参数与显存（来自 safetensors 文件头）

| 组件 | 形状 | 参数 | BF16 | Astral 落地后（推断） |
|---|---|---:|---:|---:|
| 5 层（q,k,v,o,gate,up,down,a_proj,m_proj，每层 74.05M） | — | 370.2M | 740 MB | Q8_0 393 MB |
| `fc` | 2304×9216 | 21.2M | 42.5 MB | Q8_0 22.6 MB |
| selector `hidden_projection` | 256×2304 | 0.59M | 1.2 MB | Q8_0 0.6 MB |
| predecessor / successor codebook | 2 × 201024×256 | 102.9M | 206 MB | 截到 200,058 行 BF16/FP16 205 MB |
| norms、conv base_kernel | — | ~0.1M | — | — |
| **合计** | | **494,983,424** | **990 MB** | **≈ 0.62 GB** |
| ring（每流） | 5 层 × K,V × 2048(+16) × 1024 | — | 40 MiB | FP16 约 42 MB（FP8 可减半） |
| 可选：draft-only NVFP4 head 副本 | 201024×2304 | — | — | +260 MB |

TensorFold 在 5090 上记 1.67 GiB（`README.md:94`），因为保留了 BF16 原件再加 FP8 副本和 NVFP4 head；Astral 只存 Q8_0 就够（llama.cpp PR #27342 实测 DFlash2 草稿 Q8_0 的接受长度 5.08 ≥ BF16 4.92【自报】）。

---

## 3. 每轮成本构成

一轮 = **verify(k+1 行) + accept + conv commit + ingest(k+1 行) + 下一块的 block pass**（Astral 已把这些放在一个 per-k graph 里：`crates/model/src/inkling.rs:964-993`）。

| 部分 | DFlash2（每轮字节，4090 推断） | DSpark（Astral 现状） |
|---|---|---|
| 草稿层权重 | 5 层 Q8_0 393 MB，8 行 dp4a `multi_t` | 3 层 ≈ 278 MB |
| head | 7 行一次读 Q8_0 head 492 MB（或 NVFP4 副本 260 MB） | 同样 492 MB |
| 逐 token 递推 | selector：7 步 × 16 个 codebook 行 gather，约 60 KB | **Markov head 7 步，每步读整张 fold（201024×256 Q8_0 ≈ 55 MB）≈ 383 MB** |
| 草稿注意力 | ring 2048 × 5 层 ≈ 42 MB（8 行共享，L2 可容纳） | 2 个 1024 局部层 + 1 个全局层（随上下文增长） |
| top-16 | 7×201024 logits，radix 两遍 | 逐步 argmax（在 fold_argmax 内） |
| ingest | fc 22.6 MB + 5×[k;v] 25 MB ≈ 48 MB | 3 层 `wkv_ctx` ≈ 15 MB |
| **合计** | **≈ 0.98 GB**（NVFP4 head 时 ≈ 0.75 GB） | **≈ 1.17 GB** |
| verify | k+1 ≤ 8 行，**不变** | 同左 |

- 草稿 pass 时间【推断】：1.0–1.4 ms（Astral 的 DSpark 草稿一步实测 1.23 ms ≈ 940 GB/s【实验包 T16 第 2 轮】；DFlash2 字节更少，但 kernel 数更多，约 5 层 × 14 + head/top-16/selector ≈ 90 个 launch，graph 内）。
- GB10 对照【源码/自报】：hold 4.3 ms（FP8 层 + FP8 head 4.4 ms，NVFP4 head 3.6 ms），与流数、深度基本无关（`0018:520, 536-543`）；按带宽 273 → ~1008 GB/s 换算约 1.0–1.2 ms，与上面一致。
- verify 每多一行约 **0.96 ms**（短上下文）/ 1.4 ms（16K）【实验包 T21】，来自 MoE expert 并集增长；GB10 上对方测的是“每多 verify 一个 token ≈ 5 ms”（DGX README:489）。这正是 TensorFold 要做 chance 引导 round planner 的原因。

---

## 4. 对方自报数据（都不是 4090，也都不是 A1）

| 来源 | 设置 | DSpark | DFlash2 | 比值 |
|---|---|---|---|---|
| inco HF 卡（README.md:62-104） | H200 SGLang + FA4，T=1.0，默认思考，7 草稿 | 接受长度 2.95–3.66；c1 297.6–393.8 tok/s | 3.90–4.97；387.3–525.8 tok/s | AL ×1.32–1.43；c1 吞吐 +27%～+40% |
| tonyd2wild vLLM（DGX README:9-17, 401-417） | GB10，T=0，思考关，k=7 | 6 prompt bench 2.40 tok/step，40.2 tok/s；8 类均值 61.4 tok/s | 3.26，55.2 tok/s；88.2 tok/s | 1.37–1.44× |
| 同上，逐位置累计接受率（README:416-417） | prose | 0.57/0.29/0.14/0.08/0.05/0.04/0.02 | 0.79/0.61/0.49/0.42/0.38/0.35/0.33 | — |
| 同上 | coding（首/末位置） | 0.81 → 0.28 | 0.90 → 0.47 | — |
| TensorFold + 0018（DGX README:510-515） | GB10，T=0，chance 引导 | 8 类均值 68.2 tok/s | 105.5 tok/s | 1.55× |
| TensorFold RTX PRO 6000（README.md:34-40） | T=0.7、思考开、top_k 20 | prose 150.7（**更早的 300 W 基线**），code 231.1 | prose 230.1 | 不可直接比（版本、功率、采样不同） |
| RTX 3090（vLLM，DGX README:425-426） | 1 用户 | — | k=7 179.8 > k=5 156.5 > k=3 150.4 tok/s | 定宽时 k=7 最好 |
| llama.cpp PR #33049（未合入，硬件未写） | Inkling DFlash2 | — | 修复后 code 158.0 / prose 85.7 tok/s（修复前约 51） | — |
| 博客（DFlash2 vs DSpark，同训练设置） | Qwen3.8-27B，块 8 | AL 3.62 | 4.80 | ×1.33 |

一致性检查【推断】：Astral T21 的 sn（自然语言）DSpark 逐位置条件接受率 0.50–0.59、近似几何分布【实验包】，与 GB10 vLLM prose 的 DSpark 曲线（0.57, 0.29, 0.14…，即条件率 ≈0.5）几乎一致，所以用 GB10 曲线估 Astral 是合理的近似。

---

## 5. 4090 上的收益估算（推断）

模型：一轮时间 C(k) = D + 7.07 + 0.96k（ms），7.07 = T21 拟合截距 8.3 − DSpark 草稿 1.23；E[N(k)] = 1 + Σ_{j≤k} P(A ≥ j)；吞吐 = E/C。DSpark D = 1.23，DFlash2 D = 1.3（敏感性 1.0–1.6）。code 曲线由首末位置几何插值。

| 负载曲线 | DSpark 最优 | DFlash2 最优 | 增益 |
|---|---|---|---|
| prose（GB10 vLLM） | k=2，E=1.86，**182 tok/s** | k=7，E=4.37，**290 tok/s** | **+59%** |
| coding（GB10 vLLM，插值） | k=6，E=4.27，302 | k=7，E=5.66，375 | +24% |
| 16K 成本（9.7 + 1.4k）下的 prose | 149 | 223 | +50% |
| 每行成本 0.5 / 1.5 ms 敏感性（prose） | 204 / 165 | 368 / 233 | +80% / +41% |

- Astral sn 的 DSpark 估计 180 tok/s、sc 236 tok/s，与 T21 实测混合 206–222 tok/s 吻合，说明成本模型可用。
- T21 混合（sn 21 条、sc 11 条）几何加权：≈ 1.60^0.66 × 1.24^0.34 ≈ **1.47×**；考虑 A1 与官方目标的差异、思考段内容、Astral 的 code prompt 接受率比 vLLM coding 低，给区间 **+25%～+60%**。
- 叠加 chance 引导的逐轮 k：DFlash2 的最优 k 多数是 7，planner 只在“首个草稿 chance 低”的轮次缩短 k；预计再 +2%～+6%。
- 风险项：长文档 copy 类（T21 的 ln/lc 在 DSpark 下条件接受率 0.68–0.96）可能依赖 DSpark 全局层的远程检索；DFlash2 只有 2048 窗口（远程信息只能通过 taps 进入）。这一项没有任何对方数据，必须测。

---

## 6. 在 Astral 里落地需要的改动

### 6.1 不需要改的
- verify 前向、taps 采集（`SpecIo { feats, taps: [5,23,41] }` + final norm）、`accept`、`conv_commit`、per-k round graph、`Policy`、`ASTRAL_SPEC_LOG`。k ≤ 7 ⇒ verify ≤ 8 行，正好落在现有 dp4a `multi_t`（T = 2–8，`ops.rs:580`）和 `QITEM_ROWS = 8`（`ops.rs:453`）以内。
- `Spec::new` 的约束 `k < block && block ≤ QITEM_ROWS`（`dspark.rs:607`）对 DFlash2（block 8）同样成立。

### 6.2 需要新增 / 替换的（建议新文件 `crates/model/src/dflash2.rs`、`crates/kernels-src/cu/dflash2.cu`，按 config 中 `dflash_config` / `mtp_config` 在 `enable_spec`（`inkling.rs:855`）分派）

| 项 | 做法 | 复用 |
|---|---|---|
| 权重 | 层、fc、hproj 加载时转 Q8_0（同 DSpark 的 `q8()`）；codebook 截到 200,058 行，BF16/FP16 常驻 | `DraftWeights::load` 的模式 |
| ingest（替换 `store_ctx`，`dspark.rs:687`） | 新 kernel：4 个 tap 平面 gather → [rows][9216] Q8 激活（替代 `mix4`）；fc → RMS(hidden_norm) → 每层 [k;v] GEMV → `head_prep`（k_norm+RoPE）写 ring | `mm_small`、`add_rms_q8`、`head_prep`、`KvBuf` ring |
| ring 尺寸 | **≥ 2048 + 8**（建议 max(2064, tmax)）。Astral 在 round graph 里对固定的 nv = k+1 行做 ingest、并把块 K/V 也写进 cache；若 ring 恰好 2048 槽，第 j 行 (A+j) mod 2048 会覆盖窗口里最老的 context。TensorFold 只 ingest 被接受的行，所以能用 2048 | 现有 `kv_rows`（`dspark.rs:224`）已按 `max(window + block, tmax)` 设计 |
| embedding | pending + 7 个 mask 过 `tok_embd` + `tok_norm`；7 个 mask 行是常数，加载时预算 | DSpark 对 anchor 已这么做 |
| 两 tap 动态卷积 | 新 kernel（逐元素，可与 `add_rms_q8` / `quant` 融合）；`a_proj`/`m_proj`（576×2304）走 `multi_t` T=8 | — |
| 注意力 | `astral_dsp_attn` 已是“块内无因果 + ring + FP16”（`dspark.cu:152-162`），但窗口是**整块共用**的 lo = L − window；DFlash2 需要**逐行** lo_t = A + t − 2047。加一个参数即可；可顺带用 0020 的 shared-tile 写法 | `DSP_MAXG = 4` 正好等于 32/8 |
| head | 7 行目标 Q8_0 head（`mm_small(&tw.output)`，同 `dspark.rs:756`）；可选 `ASTRAL_DRAFT_HEAD_FP4` 已有的 NVFP4 副本 | 已有 |
| top-16 | 新 kernel：7 行 × 200,058，移植 0026 的 radix 版（限制在 `cfg.vocab`，不是 padded） | — |
| selector | hproj GEMV（f32 输出）+ 单 block 的 7 步贪心 walk，写 `token[1..=7]` 和 7 个 chance | 移植 `tf_ink2d_select`（去掉 keyed 分支） |
| round planner | 主机在每轮同步后与 `out` 一起读回 7 个 chance（`inkling.rs:1014` 那次 D2H 顺带），用 Landing 式校准表（按 own log-prob 半 nat 分箱，chance = (landed + 2·e^{own}) / (offered + 2)，ashhart/TensorFold `draft_tree.zig:91-109`）得到 P(A ≥ j)，再按 T21 成本表选下一轮 k | `Policy::choose`（`dspark.rs:498`）的 E/C 框架 |
| prefill | 只需最后 2048 个 prompt 位置进 ring：整块早于 plen − 2048 的 chunk 可跳过 ingest（省得很少，TTFT 不变） | `inkling.rs:836` 的 per-chunk `store_ctx` graph |
| graph | 块 pass 形状固定（8 行、ring 位置由设备端 pos 计算），可直接进 `first` 和每个 `rounds[k]` | 现有捕获流程 |

工作量【推断】：Rust 约 600–900 行、CUDA 约 300 行，加一个 Python 参考对拍；2–4 人日 + 验证。

### 6.3 verify 窗口超过 8 行（只有树 / 块 16 草稿才需要）
- 链式 DFlash2 不需要。若将来做树或重训块 16 的草稿：`Spec::new` 的 `QITEM_ROWS` 上限、`multi_t` 只有 T = 2–8 的实例、`argmax_rows` 的 `8 × ARGMAX_PARTS` 缓冲、`next_all`、conv `hist` 行数都要放大。
- 分派建议【推断】：T = 9–16 时 dp4a 寄存器分块的累加器压力大，int8 `mma.sync m16n8k32` 一个 M=16 tile 正好装下 16 行，TC 路径应优于 dp4a（与 T ≤ 8 时相反，T16/T26 测得 TC `multi_mma` 在 ≤8 行时只有约 390 GB/s）。MoE 专家部分的每行成本（expert 并集）不受此影响。

### 6.4 树 / 多路径 verify 在 per-k graph 下的可行性
- **工程上可行**：graph 按“树模板”而不是 k 捕获（少量固定拓扑，parent/depth 数组常驻设备）。
- **需要的改动**（与 06 中 R7 列的前提一致）：目标 48 个 visit 的注意力（含 40 个 SWA ring visit 和 8 个全局 visit）支持祖先可见掩码；Inkling 的 4 处短卷积（l_cache = 4）按 parent 链取输入，`conv_commit` 按被接受路径提交；同深度兄弟共享位置 → 树行 K/V 先写 scratch，接受后把路径压实到 48 个 visit 的 cache；DFlash2 ring 只 ingest 路径上的行；先证明单链树退化为现有 chain verify（逐位一致）。
- **4090 上的收益估算是负的**【推断】：prose 链 k=7 是 4.37 token / 15.1 ms。加一个第 1 层兄弟行：+0.96 ms，期望多 0.21 × P(兄弟正确 | 首选错) ≈ 0.21 × 0.4 ≈ 0.08 token → 277 tok/s < 290。整条第二路径（再 7 行）约 +0.34 token / +6.7 ms → 216 tok/s。要打平，兄弟行的边际成本须 ≤ 约 0.3 ms。兄弟行与首选行上下文相同，路由可能高度重叠，边际成本可能低于 0.96 ms——这是唯一值得先测的量（T21 的 `expert_union_size`）。
- 所有已知 Inkling DFlash2 实现都是单链：TensorFold 的 Inkling drafter 对树输入直接报 `TreesNotBuilt`（`0018:1154, 1302`），虽然 TensorFold 框架对其他模型有 best-first 树（`draft_tree.zig`，branch 4、默认 15 节点）。

---

## 7. 与 A1 GGUF 搭配的风险

- **DFlash2 针对谁训练**：HF 卡 `base_model: thinkingmachines/Inkling-2-Mini`（finetune 标签），评测用官方 SGLang 镜像（README.md:39-51）。官方 checkpoint 就是 ModelOpt NVFP4（4090 上 A3 config：`quant_method: modelopt, quant_algo: NVFP4`），所以推断训练特征来自这个 NVFP4/MXFP8 目标；博客没有公开训练数据、温度、目标精度【自报缺失】。
- **A1 与官方的差别**（01_model.md §4）：专家 NVFP4 ×40（同格式，是否逐位相同未核实），MXFP8 专家 → Q8_0，BF16 注意力 / embedding / LM head → Q8_0。
- **影响路径**：taps（4 个隐藏状态）有小扰动；candidate logits 用 A1 的 Q8_0 head；mask/pending embedding 来自 Q8_0 `token_embd`。
- **证据**：T19 中 Astral 与 llama.cpp 的逐 token KL 约 1e-3、top-1 约 99.9%【实验包】；DSpark（同样针对官方目标训练）在 A1 上工作正常，T21 中 llama.cpp 的 DSpark 草稿 Q8_0/BF16 接受率 0.264/0.265【实验包】；llama.cpp 在 Q4_K_M 目标上 DFlash2 的接受长度 4.92–5.08【自报】。
- **判断**：低～中风险，主要不确定性在思考段内容和长上下文，而不在量化。用 Phase 0 在 A1 上直接测量，不靠推断。
- **A4 varloop**：DFlash2 按固定 3 遍的 48 个 visit 训练；A4 在 R ≠ 3 时 visit 编号整体平移（R = 2 时没有 visit 48），R = 3 时权重也不同 → 预计接受率下降，需要重训 / 微调才能用于 T33/T35 的变遍场景。

---

## 8. 与实验包的关系（建议，不改文档）

| 实验包条目 | 关系 |
|---|---|
| A5、R7 | R7 的前置“先优化原生 DSpark（T21）”已满足（T21 PASS）。建议把 R7 拆成可执行任务：Phase 0（离线接受率）→ Phase 1–2（Astral 实现）→ Phase 3（长上下文） |
| T21 | 成本表、burst/model 策略、`ASTRAL_SPEC_LOG` 直接复用；chance 引导 planner 是 T21 model 策略的逐轮版本，也可回移植给 DSpark（在 `fold_argmax` 里顺带算 logsumexp 即可得到 chance） |
| T17 / T21 草稿 KV ring | DFlash2 没有随上下文增长的草稿 KV；开草稿的最大上下文推断可从 114,688 回到 132,096（需实测 graph 实例化显存） |
| T26 | head 份额问题在 DFlash2 下变为：head ≈ 草稿字节的一半；`ASTRAL_DRAFT_HEAD_FP4` 值得在 DFlash2 下重测（仍是 draft-only、无损） |
| T27 | 0019 的“最后一个 visit 只算尾部行”在 DFlash2 下与开草稿兼容；但 T27 已判 NO_BENEFIT，不建议重开 |
| K2 | DFlash2 的 8 行 GEMV 全部落在 K2 的 dp4a `multi_t` 上 |
| T25 | verify 3/5/7 行的状态用例原样复用（verify 路径不变） |
| T34 / R14 | 与草稿器正交；不受影响 |
| llama.cpp 版本 | Phase 0 需要 ≥ b12785（实验包现为 b12751） |

---

## 9. 分阶段验证计划

**Phase 0：离线接受率（不写 Astral CUDA；4090 上运行，本机 1 GB 内存不跑）**
- 0-A（最快，llama.cpp）：构建 llama.cpp ≥ b12785；在 `$LAB/venv-convert`（CPU torch）用 `convert_hf_to_gguf.py` 把 A5 转成 BF16 和 Q8_0 GGUF（需写入 `target_visits` 与 `selector_softcap_after_correction`，PR #33073）；A1 + DFlash2，温度 0，固定 7 个草稿，跑 T14 的 32 个 prompt × 512 token 和 T21 的 sc/sn/ln/lc；同一 harness 跑 A6（DSpark）作对照。交付：两种草稿器的逐位置 P(A ≥ j)、接受长度、输出与无草稿逐字节一致（健全性）。
- 0-B（与 Astral 数值一致的 teacher-forced）：在 fork 加一个诊断命令 `dump-taps`（prefill 后把 `feats` 按 bf16 `[T][4][2304]` 写盘，加上贪心 token）；用改写的 `inkling2_dflash2_ref.py` 对每个 anchor A 计算：ring = feats[A−2047..A−1]，pending = token[A]，草稿与 token[A+1..A+7] 比较。贪心下已提交序列与草稿无关，所以 teacher-forced 的逐 anchor 接受长度与真实投机解码完全相同；再按接受长度串联 anchor 模拟轮次，套 T21 成本表和不同策略（固定 k、burst、chance 引导）给出预测 tok/s，同时离线拟合 chance 校准表。成本：每个 anchor 约 7 GMAC（head 为主），5K 个 anchor 在 4090 主机 CPU torch 上约 10 分钟量级；16K 长文本的 dump 约 0.3 GB / 条。
- **门 G0**：A1 上 DFlash2 / DSpark 的接受长度比 sn ≥ 1.25、sc ≥ 1.10，且按 T21 成本表预测混合负载 ≥ +15%。不过即记 NO_BENEFIT，停止。长文档（ln/lc）单独看：若 DFlash2 更差，记下切换阈值。

**Phase 1：Astral eager 实现与对拍**
- 按 §6.2 实现，开关 `--draft` 指向含 `dflash_config` 的目录时启用；DSpark 路径不动。
- 对拍：与 CPU 参考在 ≥ 64 个 dump 的 hold 上比较，贪心草稿完全一致的比例 ≥ 95%，top-16 交集 ≥ 15/16（TensorFold 的标准是 8/8 一致）；spec-generate 的 V8 式检查（分歧只出现在近平局处）。

**Phase 2：graph 与性能**
- per-k graph（k = 2–7）；`ASTRAL_SPEC_PROFILE` 测草稿一步（目标 ≤ 1.3 ms）；重测 T21 成本表。
- T14 + T21 协议（32 prompt × 5 次；sc/sn/ln/lc），与 DSpark burst 配对比较。逐项 A/B：Q8_0 head vs NVFP4 head 副本；radix top-16；shared-tile 注意力；chance planner vs burst。
- 回归：G2（V3–V8，T20 的 verify k = 1/3/7，verify 路径没改，主要是回归检查）；G3。
- **门 G1**：T21 混合负载几何均值相对 DSpark ≥ +10%，且没有任何负载桶差 3% 以上（否则按桶选草稿器）。

**Phase 3：长上下文与显存**
- 开 DFlash2 时的最大上下文（逐级到 132,096，单列 graph 实例化显存）；64K / 128K decode；ln/lc 接受率。
- 若长文档 DSpark 明显更好：评估两个草稿器同时常驻、按请求 / 按上下文长度切换的显存。

**Phase 4：探索项（按 Phase 2 结果决定）**
- 采样：keyed race 采样器 + keyed 草稿，或 top-16 上的 rejection sampling；用小词表穷举检查输出分布（R7 的要求）。无损。
- A1 自蒸馏：用 A1 自己的思考段轨迹微调 DFlash2（或只训 selector）；只改草稿，输出无损。4090 上 0.5B + Adam 约 7 GB，特征从 dump 流式读入。
- A4：为 varloop 重训 / 微调（taps 映射要重新定义）。
- 树：只在实测兄弟行边际成本 ≤ 0.3 ms 时启动，按 §6.4 的前提。
- 有损（单列命名）：放宽接受（例如目标 top-2 且 logit 差 < δ 时接受），必须过任务质量评测，不称无损。

---

## 10. 其他可借鉴项（0019 / 0020 / 0026 与 TensorFold 框架）

| 项 | 来源 | 对 Astral 的价值 |
|---|---|---|
| chance 校准 + round planner（按 E/ms 选 k，并做宽度探测、按上下文分 6 档保存成本表） | `0018:1089-1115`；`lone_costs.zig`、`draft_tree.zig:91-109` | 中；同时适用于 DSpark |
| radix top-16（单次加载，精确，平局同序） | `0026:28-152`；对方 +0.2%～+1.3% | 低，但写 DFlash2 时直接用这个版本 |
| shared-tile ring 注意力（8 个 warp 共享 16 行 K/V tile） | `0020:44-126` | 低（4090 L2 72 MB 已能容纳单层窗口） |
| 多流批量 ingest、FP8 fc/kv | `0020:238-303` | 单流时无关；Q8_0 已等价于 FP8 字节 |
| prompt ingest 只取最后 2048 行；最后一个 visit 只算尾行 | `0019:82-138, 251-306` | 很低（T27 已 NO_BENEFIT） |
| draft-only NVFP4 head 副本（主机端按 ModelOpt 量化） | `0018:797-887` | 低～中，DFlash2 下 head 占草稿字节一半，值得重测 |

---

## 11. 未验证的假设与风险

1. GB10 / H200 的接受曲线能迁移到 A1 + Astral 贪心 + 思考段内容（Phase 0 验证）。
2. DFlash2 草稿一步在 4090 上 ≤ 1.4 ms（Phase 2 测）。
3. 长上下文 copy 类负载：2048 窗口 vs DSpark 全局层（无任何对方数据）。
4. 开 DFlash2 的最大上下文能到 132,096（显存余量约 1.25 GiB 是 T17 的无草稿数据，graph 实例化另计）。
5. 训练数据 / 目标精度未公开；A1 的 Q8_0 head 与 embedding 对 top-16 的影响预计很小（TensorFold GPU 对 CPU 参考 top-16 交集 15–16/16）。
6. 树 / 多路径的负收益结论基于 0.96 ms/行的链式 verify 成本；兄弟行成本未测。

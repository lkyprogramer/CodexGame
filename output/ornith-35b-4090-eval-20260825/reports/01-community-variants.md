# Ornith-1.5-35B-A3B 社区调优 / 量化变体汇总

日期：2026-08-25  
范围：Hugging Face + X + LocalLLaMA / 官方卡。只列 **1.5-35B-A3B** 这条线；1.0-35B 的大量 abliterated 不展开，文末点一下。  
本机已部署：`AtomicChat` `AD-Q4_K-IQ4_XS`，SHA `6def24b4…`。

## 结论

**没有找到像 Qwen3.8 S-list 那种「换模板/换 CPT 专门打 coding agent」的成熟 1.5-35B 微调。**  
社区一周内长出来的是四类：

1. **量化配方**（AtomicChat / 官方 / bartowski / Unsloth 风 / APEX）— 权重语义几乎不变  
2. **MTP 头修补**（官方自带 MTP 是随机初始化；shisa 蒸馏、EryriLabs 嫁接、mudler 打进 `blk.40`）— 主要换速度  
3. **Abliterated / 去拒绝**（huihui、alztrk/PocketAiHub）— 审不审，不解决 QCB 工具格式  
4. **一次 TIES merge**（EryriLabs × BigBang）— 通用性 merge，Python 小测与原版打平

对 4090 coding agent：**继续用现有 AtomicChat AD-Q4_K-IQ4_XS。**  
若只想再刷 tok/s：优先试 **shisa 蒸馏 MTP 头 + 现权重**，或 **mudler APEX-MTP Compact（17.4GB，自带 `draft-mtp`）**。  
不要拿官方 GGUF 里那份原生 MTP 当投机草稿（accept ~0.13，等于随机）。

Abliterated 不当下一档 WORK：X 上已有「alztrk 版仍很容易拒绝」；huihui 只切了 11–29 层。

---

## 1. 官方（不是社区调优）

| 仓库 | 格式 | 备注 |
|---|---|---|
| `ornith-ai/Ornith-1.5-35B-A3B` | BF16 | 基座 |
| `ornith-ai/Ornith-1.5-35B-A3B-GGUF` | GGUF | 官方 Q4_K_M 约 **21.7GB**（三家同名文件尺寸不同） |
| `…-FP8` / `…-NVFP4` | 服务端量化 | 4090 llama.cpp 用不上 NVFP4 |
| `…-MLX` | Apple | 无关 |

官方卡：思考默认开；MTP **单独文件**。EryriLabs 实测：原装 `mtp.*` 是 `initializer_range=0.02` 的随机头，投机 accept ~13%。

---

## 2. 量化（权重不变，只改精度）

| 发布者 | 仓库 | 4090 相关档 | 社区声音 |
|---|---|---|---|
| **AtomicChat** | `AtomicChat/Ornith-1.5-35B-A3B-GGUF` | **AD-Q4_K-IQ4_XS 20.1GB**（官方写 24GB 留上下文）；AD-Q5_K-Q4_K 22.1GB 短会话 | 本机已跑：200K q4，decode ~155 tok/s。@danirebollo 3090 同量化 + 196K q4 KV |
| **ornith-ai** | 官方 GGUF | Q4_K_M 21.7GB | @analogalok 4090：Q4_K_M + q8 KV **250K**，宣称 156 tok/s |
| **bartowski** | `bartowski/Ornith-1.5-35B-A3B-GGUF` | imatrix，Q4_K_M 约 21.9GB | AtomicChat 点名：三家 Q4_K_M **不是同一文件** |
| **peculiar-ragdoll** | `Unsloth-Ornith-1.5-35B-A3B` | UD-Q4_K_XL 等 Unsloth 动态阶梯 | 社区 UD 配方，无独立 4090 大样本 |
| **mudler / LocalAI** | `Ornith-1.5-35B-A3B-APEX-GGUF` | Compact / Balanced / Quality；专家更狠压 | 专家占 89.6% 权重、每 token 只亮 8/256，APEX 专门吃这个 |
| **quimmedes** | XYZ 阶梯 | Q4 ~17.1GB | 小众 |

zephel01（note.com，60 题自建套）：**24GB 实用最优写官方 Q4_K_M**（88.3% / 22.5GB / ~251 tok/s 其环境）；Q5 只高 1.7pt。和 AtomicChat「24GB 留窗用 AD-Q4」不冲突：一个偏质量表、一个偏窗口。

---

## 3. MTP：这才是「调优」里对速度最实的一块

官方 1.5 的 MTP 头 **没训好**。社区三条修法：

| 方案 | 仓库 | 做法 | 数字 |
|---|---|---|---|
| **shisa 蒸馏头** | `shisa-ai/Ornith-1.5-35B-A3B-MTP-ONLY`（仅头）+ 合并仓 `…-MTP` | 从 Qwen3.6-35B MTP 初始化，对 Ornith hidden 做 12K KL | 代码 accept **69%** / 原装 37%；X @tsuckamo：AtomicChat 主权重 + 这份 Q6_K MTP，262K q8 KV |
| **EryriLabs 嫁接** | `EryriLabs/Ornith-1.5-35B-A3B-BigBang-MTP` + `…-GGUF` | TIES merge Ornith×BigBang-v1，MTP 用 Qwen3.6 真头 | 3090：MTP **169 tok/s（+29%）** vs 无草稿 131；accept 0.55–0.75。15 题 Python 与原版都 15/15 |
| **mudler APEX-MTP** | `mudler/Ornith-1.5-35B-A3B-APEX-MTP-GGUF` | 把 MTP 打进 `blk.40`，`--spec-type draft-mtp` 不用另下草稿 | Compact **17.44GB**（4090 很宽裕）；Balanced 26GB 偏紧 |

X @qyrpie 在 3080 10GB 上开 `--spec-type draft-mtp` 报 204/205 drafts accepted——**高度可疑，更像把未训练头/错误统计当成功**；不要当 4090 依据。

对本机：现权重 20.1GB + 空载余量 3.1GB，**外挂一份 ~1GB 的 shisa Q4/Q6 MTP** 物理上塞得下，比换整包 merge 风险小。

---

## 4. Abliterated / 去拒绝（1.5-35B）

| 发布者 | 仓库 | 备注 | 社区 |
|---|---|---|---|
| **huihui-ai** | `Huihui-Ornith-1.5-35B-A3B-abliterated` | 只切 **11–29 层** | 作者 X 宣布；不是全层 |
| **alztrk → PocketAiHub** | `alztrk/…-Abliterated` / `PocketAiHub/Ornith-1.5-35B-A3B-Abliterated-GGUF` | Dynamic Q4_K_M ~19.7GB；Ollama：`codecraftersllc/ornith-1.5-35b-a3b-abliterated` | @trevorwood222 发帖，**@ornith_ 回了🧡**。@neutron42jp：**「alztrk 版仍很容易拒绝」** |
| **AtomicChat 警告** | 指南 Troubleshooting | 发布次日就出现 uncensored/abliterated 假仓，先认发布者再下 | — |

对 OpenClaw：**不解决** QCB 上的 illegal tool / `invalid_output`。1.0 时代 AEON/Heretic 那套评测更完整，**不要把 1.0 数字套到 1.5**。

---

## 5. 真正改权重的 merge（仅一条像样的）

**EryriLabs BigBang-MTP**：Ornith-1.5（agentic RL）× `endless-frontier/BigBang-v1`（通用），TIES density 0.25，**router 原样保留**（MoE merge 的常见翻车点）。  
小测：15 题 Python 与原版打平，PPL 略好（3.34 vs 3.41）。这是「通用一点 + 能用的 MTP」，**不是** coding-agent 专用 CPT。

没看到 Sharp / grug / Salience / Cold Fusion 那种 1.5-35B 对标 S-list 的系列。

---

## 6. X 上和 4090 相关的实装（变体，不是官方便当）

| 账号 | 说了什么 |
|---|---|
| @analogalok | 官方/Q4_K_M，4090，q8 KV 250K，~156 tok/s，**没提 MTP** |
| @danirebollo | **AtomicChat AD-Q4_K-IQ4_XS** + mmproj + 196K q4 KV（3090） |
| @tsuckamo | AtomicChat 主量化 + **shisa MTP Q6_K** + BF16 mmproj + 262K q8 |
| @trevorwood222 / @ornith_ | PocketAiHub abliterated GGUF；官方只回了个🧡，不等于背书质量 |
| @neutron42jp | alztrk abliterated **拒绝仍多** |
| @support_huihui | 发布 1.5-35B abliterated（部分层） |
| @qyrpie | 3080 上 native MTP 高 accept — 与 EryriLabs「原装头随机」冲突，存疑 |

---

## 7. 对本机 4090 的建议（不自动部署）

| 优先级 | 动作 | 图什么 |
|---|---|---|
| 0 | **保持** 现网 WORK + 盘上 AtomicChat AD-Q4_K-IQ4_XS | 已测 200K、155 tok/s、smoke 5/12 |
| 1 | 外挂 `shisa-ai` MTP 头，`--spec-type draft-mtp`，加 `--reasoning-budget 4096` | 速度；思考量对齐 WORK |
| 2 | 换 `mudler` APEX-MTP Compact | 一条 GGUF 自带 MTP，17.4GB |
| 3 | EryriLabs BigBang-MTP GGUF | 仅当要「Ornith+通用 merge」实验 |
| — | huihui / alztrk abliterated | 不为 coding agent 换 |
| — | 官方原生 MTP 文件 | 头没训，不要开 |

`reasoning_effort=medium` 对这份 Ornith jinja **无效**；钳思考用 `--reasoning-budget`。

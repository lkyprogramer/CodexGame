# Qwen3.8-27B 社区实践与 4090 场报告

日期：2026-08-18  
范围：X / Reddit r/LocalLLaMA / Hugging Face / GitHub / Unsloth / 官方卡，叠加本机单卡 RTX 4090 24GB 实测。  
现网对照：`openclaw/Qwen3.8-27B-WORK`，Unsloth `UD-Q4_K_XL`，llama.cpp `4df29be` + 正文预留补丁，`-c 112000`，q8 KV，MTP n=2，`reasoning_effort=medium`。

事实 / 推断 / 未验证会分开写。社区数字来自公开帖，硬件、llama.cpp 版本、采样、思考档位几乎都不一致，**不能直接横向比 tok/s**。

---

## 1. 一句话结论

**Qwen3.8-27B 是 2026-08 消费级卡上最值得当本地主力的 27B dense 模型。** 官方和社区都把它放在「能打闭源 flash / 部分 Opus 4.6 代理分」的位置；单卡 4090 用 UD-Q4 + MTP n=2 可以稳定跑在 **55–80 tok/s**、**64K–112K 工作窗口**。真正会把体验打崩的，不是量化，而是默认 `xhigh` 思考税、Jinja 模板陷阱、MTP 深度、以及思考吃光 `max_tokens` 导致空正文。

对 4090 单人 OpenClaw：现网配方（Q4_XL / q8 KV / 112K / n=2 / medium / 思考预算钳制）和社区 24GB 主航道一致，也避开了社区踩过的主要坑。不要再追 128K、n=4、Ollama 默认模板、或顶层 `reasoning_effort`。

---

## 2. 模型是什么，社区怎么评

### 2.1 官方画像

来源：[Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)

- 27B **dense** 视觉语言模型（不是 35B-A3B 那种 MoE）。
- 原生 262,144，可扩到 1M。
- 内置 MTP（多步预测头，不是外挂 draft 模型）。
- 思考默认开；`reasoning_effort`：`xhigh`（默认）/ `medium` / `low`。没有 `high`。
- `preserve_thinking` 官方默认开。
- 官方采样：思考 `1.0 / 0.95 / 20`；非思考 `0.7 / 0.80 / 20` + `presence_penalty=1.5`。
- 自报高光（闭源对照 Opus 4.6 Max）：SWE-bench Pro **61.7** vs 53.4；OSWorld-Verified **84.3** vs 72.7；LiveCodeBench v6 **90.3**；IFBench **79.5**。

这些官方分是完整权重 + 官方 harness + 大窗口，**不是** 4090 上 Q4 GGUF 的分数。

### 2.2 社区总体评价（2026-08-14 发布后约 4 天）

| 声音 | 代表 | 态度 |
|---|---|---|
| 「本地 27B 天花板，3090/4090 价值暴涨」 | AJ (@ItsmeAjayKV)、Yume_X、Alok | 强正面。AJ 已把它接进真实项目；Artificial Analysis Agentic Index 报 52，对齐 Gemini 3.6 Flash / GPT-5.6 Luna |
| 「极好，但默认 xhigh 是搞笑的」 | Simon Willison、HF #113、Reddit megathread | 质量认可，默认档不可用。画个圆也要想几分钟；pelican SVG 用了 22k 思考 token / 21 分钟 |
| 「Q4 + 工具就能当编码代理」 | chiribe（5060 Ti 16GB / 1M+ token）、Simon + Pi | 支持，但必须带仓库上下文和 agent harness |
| 「比 3.6 慢 / 想太多 / 要 babysit」 | megathread 4090+MBP 用户、部分 AMD 用户 | 多数是配置错，不是模型废。常见根因：Ollama 模板、mmproj 被 CPU offload、MTP 没开或 n 太大、xhigh |
| 「MTP 在思考文本上命中率低于 3.6」 | Reddit megathread、本机 S2 | 部分成立。3.8 思考更长、更散，draft 更难猜；代码复述时可到 100–180 tok/s |

Unsloth GGUF 发布后约 1 天就冲到 HF 趋势 #2、2.7M downloads——消费级落地几乎全部走这条。

### 2.3 和 3.6-27B 比，社区共识

- 能力：编码、代理、视觉、长程任务明显强于 3.6。
- 速度：同量化、同 MTP，3.8 不该比 3.6 慢一倍。HF #32 里 7–10 tok/s vs 3.6 的 25 tok/s，后面被证伪为 **mmproj 拖到 CPU / MTP workspace / 旧二进制**，不是 dense vs MoE（两边 27B 都是 dense）。
- 思考税：3.8 默认 `xhigh`，同样题往往 3–7× 思考 token。Reddit 4090 用户：xhigh Q6 一次生成 8.4 万 token / 3.5 小时；medium 同题 1 万 token / 2 分钟，观感仍优于 3.6。
- 硬件定位没变：24GB 卡的本命 27B。

---

## 3. 4090 / 24GB 的显存物理

24GB 上这模型的账只有四块：**权重 + 主 KV + MTP draft KV + CUDA workspace**。权重几乎锁死，能调的是后三项。

### 3.1 权重档（Unsloth / 社区常用）

| 量化 | 盘上大约 | 24GB 态度 |
|---|---|---|
| IQ4_XS | ~14.6 GB | 给 16GB/8GB 混部用；4090 不必降到这档 |
| Q4_K_M | ~16.7 GB | 社区 24GB 参考配方 |
| **UD-Q4_K_XL** | **~17.9 GB** | **本机现网。质量/速度甜点** |
| Q5_K_M / UD-Q5 | ~20+ GB | 4090 能塞，但窗口和 MTP 会挤 |
| Q6_K | ~22–24 GB | 单卡几乎只剩短上下文；有人忘改 temp 后 xhigh 跑了 3.5 小时 |
| Q8 / BF16 | 31 / 56 GB | 单 4090 不做 |

Unsloth 官方硬件表：4-bit 17–19GB 总内存即可起步；6-bit 要 24GB——那是「能加载」，不是「能开 100K + MTP」。

### 3.2 同一张 4090 上的窗口地图

社区（Alok @analogalok、Yume_X）和本机对齐后的可用区间：

| 配方 | 大约窗口 | 大约占用 | 用途 |
|---|---|---|---|
| Q4 + q8 KV + MTP n=2，无视觉 | 64K | ~20.6 GB | 保守工作档（本机 08-18 早班） |
| **Q4 + q8 KV + MTP n=2，无视觉** | **112K** | **~22.7 GB，余 ~1.5 GB** | **本机现网。单人甜点** |
| Q4 + q8 KV + MTP | ~128–140K | ~23.5 GB，余 <0.7 GB | 社区上限附近，预填高峰危险 |
| Q4 + q4 KV，无 MTP 视觉 | 240–262K | ~22.2 GB | 社区「塞满窗口」极限，长上下文质量有争议 |
| Q4 + q8 KV + mmproj-F16 + MTP | ~60K | 接近满 | Alok：多模态 73 tok/s 异常点 |
| Q4 + q4 KV + mmproj | ~240K 多模态 | 满 | 宣传向；本机未验证 |

Yume_X 原话：24GB 上不加 q4 KV，窗口过 ~90K 会创建失败；加上 q4 KV，262K 能进 22.2GB。

本机选择 **q8 KV + 112K**，不用社区的 262K q4 KV。理由见 §6.3。

### 3.3 必须记住的乘法

llama.cpp 默认 `-np` 曾经是 4。**KV 按 slot 数倍增。** 3060 上跑 35B 的人靠 `-np 1` 才塞进 150K；4090 上 `-np 2` 会直接把 112K 打成 OOM。单人 OpenClaw 必须 `-np 1`。

MTP 自己还有一份 draft KV。社区 issue：3090 上开 MTP 后显示窗口从 137K 掉到 14K——不是模型变小，是 **draft cache 默认 f16 把显存吃光**。必须同时设：

```text
--cache-type-k q8_0 --cache-type-v q8_0
--spec-draft-type-k q8_0 --spec-draft-type-v q8_0
```

要再抠窗口，draft 可以降到 q4；主 KV 在 4090 上不建议为了 128K 再降。

KV 是启动时预分配的。长会话 **不会** 因为聊得久而涨 VRAM。会 OOM 的是：再起一个模型、`-np>1`、临时拉到 128K+、或一次 `prompt + max_tokens` 超过 `n_ctx`（通常是请求失败，不是 GPU 被撑爆）。

---

## 4. 速度：社区数字 vs 本机 4090

### 4.1 社区公开点（摘）

| 来源 | 硬件 | 量化 / 要点 | 数字 |
|---|---|---|---|
| HF #32 匿名 | 4090 FE 24GB | UD-Q4_XL，196K，q4 KV，MTP n=2 | 生成 70–80 tok/s，长生成 71，预填 1900–2100 |
| Alok | 4090 24GB | Q4 + q8 KV + mmproj + MTP n=4，60K | 宣传 73.4 tok/s 多模态 |
| AJ | 3090 24GB | Q4_K_M + 社区 24GB 配方 | 「最大速度 + 可用窗口」；Q5 网页 demo 打 Gemini 3.7 Flash |
| AssassinBug | 未标明（像 24GB） | Q4，无 MTP 60–70；MTP 命中时 | 100+，代码复述可 180+ |
| udevadm | 未标明 | IQ4_XS，200K，q4 KV，MTP n=3 | 过 128K 仍约 40 tok/s |
| chiribe | 5060 Ti 16GB | UD-Q3_XL，73K，q4 KV，MTP n=2 | 能跑完 1M token 代理编码；速度不是卖点 |
| analogalok | 4060 8GB + 16GB DDR4 | IQ4_XS，ngl 25，64K，MTP n=2 | 预填 150，解码 **5** tok/s（能跑，不能当主力） |
| RX9070XT×2 ROCm | 双卡 | Q4KM + mmproj | 解码 60–70；Windows Vulkan 旧环境仅 31 |
| 2×R9700 | Q8K_XL | 10K 处 30 tok/s，156K 处 15 | 长上下文解码必然掉 |
| 2×5060 Ti | Q5KM + MTP | >60 tok/s | |
| RTX Pro 4000 Blackwell | Q4_K_M，131K，MTP n=3 | 57 tok/s，accept 0.83 | |
| Tamayan / 社区 5090 | Q6，128K | 约 52 tok/s | |
| Simon / DGX Spark LM Studio | Q4_K_M，无 MTP | 15–30 tok/s；开 MTP 后约 +72% | |
| GB10 Spark | FP8+MTP vs NVFP4+MTP | 12.0 vs 10.3 tok/s | 更小权重量化 ≠ 更快，内核效率优先 |
| ggerganov 参考 | 32GB / 5090 | Q4_K_M + Q4_0 draft，196K，q8 KV | 官方口味启动行 |

### 4.2 本机 4090（已跑，不是转述）

条件：UD-Q4_K_XL，q8 KV + q8 draft KV，32K，**关思考测速**，官方 instruct 采样。

| lane | ~1024 tok 生成 | accept 中位 | 峰值 VRAM |
|---|---:|---:|---:|
| 无 MTP | 39.0 tok/s | — | 18214 MiB |
| **MTP n=2，无 p-min** | **59.2 tok/s（1.51×）** | 0.57 | 19124 |
| n=2，p-min=0.75 | 47.3（1.22×） | 0.79 | 19124 |
| n=3，无 p-min | 60.2（1.53×） | 0.46 | 19276 |
| n=4，无 p-min | 56.3 | 0.42 | 19430 |

112K 空载 **22664 MiB / free 1553 MiB**；灌 62K prompt 后 22694 MiB，几乎不涨。

和社区 4090「70–80 tok/s」的差，主要来自：他们用 **q4 KV + 思考关或代码复述 + 更激进 ubatch**；我们用 **q8 KV + 非 greedy**。08-17 那轮 q4 KV + temp=0 + n=4 测到 75.8，已经作废，不能当工作速度。

Full 能力（medium，约 36 分钟，见 `11-capability-portrait.md`）：

- HumanEval+/MBPP+ 抽样 pass@1 84%，pass@2 90%
- 自制竞赛切片 39/40
- 多文件编辑 42/48（Python 32/32，JS 10/16）
- 工具 31/31，指令 63/68，硬推理 46/50
- 56K 多针 8/8
- 弱项：闭卷项目知识（tickMs 答 50）、思考打开时的格式洁癖

---

## 5. 社区已经收敛的「能用配方」

### 5.1 24GB 主航道（Yume_X 汇总 AJ / sudoingX / keys）

```bash
llama-server -m Qwen3.8-27B-Q4_K_M.gguf \
  -ngl 999 -fa on --jinja \
  -np 1 -t 12 \
  --spec-default --spec-type draft-mtp \
  --spec-draft-n-max 2 \
  --spec-draft-type-k q8_0 --spec-draft-type-v q8_0 \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --temperature 1.0 --top_p 0.95 --top_k 20 \
  --min_p 0.0 --presence_penalty 0.0
```

社区补充，本机全部验证过：

1. **n=2 是甜点。** keys 深度梯：n=1 1.75× / n=2 2.37× / n=3 2.85× / **n=4 打爆单层 MTP 头**。本机 n=3 几乎没额外收益，n=4 更慢。
2. **思考必须 medium**（或 low）。默认 xhigh 烧 token。
3. **过 100K 有人换 f16 KV**（mmike87：「量化 KV 过 100K 模型变蠢，f16 昼夜之别」）。本机用 q8 + 112K 折中，62K 交叉事实仍对；满 100K+ MRCRv2 未测。
4. **`--jinja` 必开**，否则 `reasoning_effort` / 工具模板不生效。
5. 顶层 JSON 的 `reasoning_effort` **会被静默丢掉**。必须：

```json
"chat_template_kwargs": {"reasoning_effort": "medium"}
```

Petko 5090 Q6：638 思考 token → 23；首动作 10.9s → 0.7s。

### 5.2 本机现网（相对社区的增量）

在 5.1 上多做了四件事，都是社区后来也在补的：

| 增量 | 为什么 |
|---|---|
| UD-Q4_K_XL 而不是普通 Q4_K_M | Unsloth 动态量化，HF 讨论里独立 KLD 往往优于同档 Bartowski |
| `-c 112000` 而不是 64K / 262K | 单人要长会话；q8 KV 下 128K 只剩 0.65GB |
| `--reasoning-budget 4096` + 短 cutoff | 防 xhigh/medium 把 `max_tokens` 吃光 |
| llama.cpp 补丁：预算钳到 `n_predict-reserve`，剩余不够就强制结束思考 | 社区还在靠「调用方把 max_tokens 拉到 20k+」；我们在服务端兜底 |

现网完整命令见 `launch/production-18343.sh`。

### 5.3 其他卡档（只作对照，不是现网建议）

| 显存 | 社区做法 | 预期 |
|---|---|---|
| 32GB 5090 | Q5/Q6 + q8 KV + 128–196K + MTP n=2 | 50–70 tok/s，质量余量大 |
| 16GB（5060 Ti / 4070 Ti Super） | UD-Q3_XL 或 IQ4_XS，q4 KV，32–73K，MTP n=2 | chiribe 用 73K 跑完真实代理项目；Q3 有人不信任 |
| 12GB 3060 | Q3/Q4_K_S + q4 KV + 混部，~10 tok/s / 96K | 能聊天和短改，不当主力 |
| 8GB 4060 | IQ4_XS，ngl≈25，64K，解码 ~5 tok/s | 「能跑」宣传，不适合 OpenClaw |
| 双 4090 / 多 16GB | SGLang/vLLM FP8 或 llama.cpp tensor-split | 吞吐和视觉 bug（mmproj 多卡预填永久掉 40%，llama.cpp#26873） |
| Apple 24GB 统一内存 | 4-bit，8–32K，5–10 tok/s；MLX MTP 研究向 | 能用，慢 |
| AMD 16–20GB | Vulkan/ROCm 差一个数量级；双 9070XT ROCm 才到 60–70 | 优先 ROCm + 新 llama.cpp |

16GB 以下想「又 Q4 又 100K 又 MTP」做不到。先砍量化或窗口，不要砍 `-np 1`。

---

## 6. 调优手段（按收益排序）

### 6.1 思考档：收益最大、成本几乎为零

官方默认 `xhigh` 是给云端和「要极致质量」的。消费级上：

| 档 | 社区观察 | 本机 T9（20 题） | 建议 |
|---|---|---|---|
| none / 关思考 | 短题最快；长上下文/复杂编辑会掉（社区 MRCRv2：关思考 128K 8 针约 43%） | 20/20 | 短 JSON、工具名、分类 |
| low | Reddit 5080：思考 4.4k，观感接近 medium | 20/20 | 大量短轮次时的默认候选 |
| **medium** | 质量≈low，token 远小于 xhigh；HF 用户挂 vLLM 代理后质量反而升 | 15/20（扣分多是格式/闭卷） | **工作默认** |
| xhigh | Simon：画圆也要「几何研究」；Reddit：7× 时间；视觉 SVG 分略高 | 18/20，不更强 | 难推理/视觉精修，按请求开 |

只能用这三个名字。llama.cpp 还认 `high` / `max` / `minimal`，**本模型模板会直接 4xx/5xx**。本机用 banana 哨兵验证过：非法值不会静默回落。

Ollama 换掉原模板后，`reasoning_effort` **完全无效**——这是 HF #113 的原话。要用档位就走 llama-server `--jinja`。

`preserve_thinking` 官方默认开，多轮会把旧思考塞回上下文，**单人 112K 会被历史思考吃掉**。现网显式 `false`。需要审计思考轨迹时再按请求打开。

### 6.2 MTP

- 确认 GGUF 带 MTP 头（`nextn_predict_layers > 0`）。缺头的文件开 `--spec-type draft-mtp` 会断言失败或静默退化。Unsloth 主文件现在带；早期/第三方「MTP-ONLY」分片踩过坑。
- **n-max=2。** 社区和本机一致。n=4 是单层头的硬顶，Yume_X / keys 明确说会 break。Alok 图里写 n=4 跑出 73 tok/s，那是短上下文宣传点，不要当默认。
- `p-min`：0 更快、accept 低（本机 0.57）；0.75 更稳、只剩 1.22×。工作先 0，线上出现 draft 胡话再加。
- 任务差极大：代码复述 accept 高、速度翻倍；开放思考 accept 低。有人在 MLX 上测到 MTP 净负收益——只对「只生成代码、不思考」正。所以测速必须关思考，测工作必须开思考，两套数不要混。
- 贴着 VRAM 墙时，HF #32 的 4090 经验：只把 **MTP 的 n_ubatch 降到 32**，不要动主模型 `-b`。否则 196K + MTP 会在初始化阶段被 CUDA compute buffer 卡死。本机 112K + `-ub 512` 目前没撞上。
- 三卡 4080 有人写 `n-max 5`——和架构警告冲突，不要抄。

### 6.3 KV：速度 / 窗口 / 质量三角

| KV | 窗口（Q4，24GB，MTP） | 质量风险 | 何时用 |
|---|---|---|---|
| f16 | ~64–80K | 最低 | 社区「100K+ 变蠢」的修复；4090 上要用就得砍窗口 |
| **q8_0** | **~112–140K** | 本机 62K 交叉事实仍对 | **工作默认** |
| q4_0 | ~240–262K | mmike87 称长上下文推理明显差 | 只为「塞进官方 256K」或短生成检索 |
| q4_1 / q5_1 | 16GB 档常用 | chiribe 说代理编码还行；其他人骂过 KV 量化 | 16GB 才考虑 |

本机不用 f16、不用 262K q4，是因为：OpenClaw 要的是 **中长上下文仍然清醒**，不是跑满卡纸窗口。112K 刚好擦着社区说的 100K 质量悬崖。若以后满窗口检索明显变傻，第一反应是退到 96K，不是先改量化。

长上下文解码必然掉。2×R9700：10K→30 tok/s，156K→15。这不是 bug。有人做 LIFO 把最老 512MB KV 换出，窗口能撑满，解码仍掉。

### 6.4 采样

跟官方走，不要发明：

- 思考：`temp=1.0 top_p=0.95 top_k=20 min_p=0 presence=0`
- 非思考：`0.7 / 0.8 / 20 / presence=1.5`
- 社区 24GB 帖有人写 `top_k=30`，官方是 20。本机按 20。
- chiribe 代理编码用了 `0.4 / 0.90 / 15`——那是他的 Q3 + 16GB 经验，和官方冲突。本机短码 + 仓库编辑在官方思考采样下已经过门槛，不跟低 temp。
- **不要 temp=0。** 08-17 评测这么干过，数字好看、工作形态假。

### 6.5 批、并行、fit

- `-np 1` 非商量。
- `-b 1024 -ub 512`：本机 112K 预填和 MTP workspace 的折中。再大容易在贴墙时炸 compute buffer。
- 无头机可 `--fit-target 64~128` 抠最后几百 MB；带桌面/本机 112K 已手算过，不必再交给 fit。
- `--cache-prompt --cache-ram 2048 --cache-reuse 256`：OpenClaw 多轮系统提示重复度高，值得开。
- 4080 Super 一类「K/V 分量化」需要编译 `FA_ALL_QUANTS`，否则 q8K+q4V 会回退或失败。

### 6.6 视觉

- mmproj-F16 大约 0.87–0.9GB。Alok：几乎不挤 KV。
- **文件在模型同目录时 llama.cpp 会自动挂上。** HF #32：有人因此把层 offload 到 CPU，速度从应有的 50+ 掉到 7。对策：`--no-mmproj` 或 `--no-mmproj-offload`。现网文本主力应显式关掉自动挂载（当前 launch 脚本没写 `--no-mmproj`，同目录若出现 mmproj 会中招）。
- 多卡 + mmproj：一条图片请求可把随后所有文本预填永久打掉约 40%，重启才恢复。workaround：加一条匹配不到任何 tensor 的 `-ot` 来关 pipeline parallel（llama.cpp#26873）。

### 6.7 引擎选择

| 引擎 | 24GB 单人 | 坑 |
|---|---|---|
| **llama.cpp llama-server** | **首选。** MTP、GGUF、Jinja、reasoning 最完整 | 要新二进制；模板断言；思考预算 |
| Unsloth Desktop | 懒人路径，MLX 也能跑 | 可调性不如手写 server |
| LM Studio | 上手快 | 默认 8K 上下文会被 xhigh 立刻吃光（Simon） |
| Ollama | `ollama run qwen3.8:27b` 能拉 18GB Q4 | **换模板，档位失效**；MTP 路径有人测到净负 |
| vLLM / SGLang | 5090/多卡/NVFP4 才值得 | 24GB Q4 权重大约就 18GB，再加 KV 很紧；3.6 有 MTP+Responses API 工具调用回归 |

消费级 4090 单人：不要为「 theoretically 更快」去 vLLM。

---

## 7. 踩坑清单（按严重度）

### P0 — 会让你以为模型坏了

1. **默认 xhigh。** 改一个变量也要「全面调查」。Simon：画个圆想成几何论文；HF #113：每次小改都分析十种可能。修复：`chat_template_kwargs.reasoning_effort=medium`，服务端再加 `--reasoning-budget`。
2. **顶层 `reasoning_effort` 被丢弃。** 模板继续 xhigh。必须放进 `chat_template_kwargs`。Hermes / 部分 UI 要 llama.cpp ≥ b10434 才能从界面改。
3. **思考吃光 `max_tokens`，返回空 `content`。** 本机 S4 在 2048 上稳定复现。社区对策是把客户端预算拉到 20k+；我们额外打了 reserve/force 补丁。OpenClaw 调用方仍应 `max_tokens>=8192` 并解析 `reasoning_content`。
4. **Jinja：`System message must be at the beginning`。** 官方模板对后置 system / Claude Code 的 developer 消息 `raise_exception`。llama.cpp#27107、#20733，HF Unsloth #7。Claude Code、SillyTavern、部分 agent 会 400/500。修复：用 Unsloth 已修正的 UD 模板，或本地注释掉断言（渲染结果对合法输入是 byte-identical）。非法 `reasoning_effort` 同样会在模板里 raise。
5. **Ollama 模板换皮。** 档位、preserve_thinking、部分工具指令失效。不要用 Ollama 当 OpenClaw 后端。

### P1 — 速度或显存突然腰斩

6. **没开 MTP，或 GGUF 没头。** 停在 ~39 tok/s 会以为 27B 就这样。
7. **n-max=4/5/6。** 单层头，n>3 无收益或崩溃。Ollama 小包有的写 `draft_num_predict 4`，那是另一套包装。
8. **`-np` 默认 >1。** KV×N，OOM 或窗口从 100K 变成 14K。
9. **MTP draft KV 仍是 f16。** 同上，窗口蒸发。
10. **同目录 mmproj 被自动加载并 offload 到 CPU。** 7–10 tok/s「谜之慢」的第一嫌疑。
11. **贴 196K/24GB 墙时 MTP compute buffer 初始化失败。** 只降 MTP ubatch。
12. **旧 llama.cpp。** 3.8 要新的 Gated DeltaNet + MTP + chat_template_kwargs。HF #32 的 CMP 50HX 7 tok/s 有一部分是旧构建 / 缺 CUDA graph 补丁。

### P2 — 质量阴沟

13. **100K+ 仍用 q4 KV。** 社区（mmike87）认为推理会「变蠢」。需要长窗口清醒就 q8 或 f16，并接受更短 `n_ctx`。
14. **关思考跑长上下文检索。** 社区 MRCRv2 掉很多；本机 64K 内没崩，128K 未测。
15. **闭卷问项目约定。** 本机 T8：tickMs=50，还说客户端可以拥有模拟权威。3.8 强的是读了文件之后，不是记仓库。
16. **xhigh 不等于更强。** 本机 T9、Dogukan、HF 代理用户都支持。xhigh 主要换更长、更漂亮的视觉/散文，不换编码正确率。
17. **temp=0 / 评测配置当生产。** 08-17 的失败复盘。
18. **安全评分器误杀。** 模型引用 `rm -rf` 来拒绝时，字面匹配会判失败。3.6 同一规则也中招。

### P3 — 生态碎片

19. 第三方 Ridge 3.69bpw、TQ3_4S、IQ2 等：能把 16GB/超长窗口打下来，**没有公开 BFCL/工具分**，不要换现网。
20. 双卡视觉预填静默退化（#26873）。
21. vLLM 3.6 上 MTP + Responses API 工具调用回归（#46249）——3.8 若上 vLLM 先当高风险。
22. 上下文变长，预填和解码都会掉。没有免费的 256K。

---

## 8. 经验与教训（社区 + 本机合成）

### 已经反复被打脸的假设

| 当时以为 | 实际 |
|---|---|
| 3.8 比 3.6 慢一倍，所以模型有问题 | 多半是 mmproj / 没 MTP / xhigh / 旧二进制 |
| MTP 越深越快 | 单层头，n=2 到顶 |
| 默认思考档是官方最优工作点 | 默认是云端展示档；消费级要 medium/low |
| 顶层 OpenAI 字段和模板字段是一回事 | llama.cpp 只吃 `chat_template_kwargs` |
| 64K 对单人够用 | 系统提示 + 几个文件 + medium 思考很快顶满 |
| 照搬 3.6 的 128K | 3.6 那套是 **q4 KV** 的账；3.8 现网 q8，128K 余量不够 |
| 空 content 是采样坏了 | 是思考预算 ≥ `n_predict` |
| 官方 90.3 / 61.7 可以写进 4090 报告 | 不同栈。本机可写的是 pass@1/编辑/工具/64K 针 |

### 真正赚到的调优顺序（4090）

1. 新 llama.cpp，CUDA arch 89，`-np 1`，`--jinja`。
2. Unsloth UD-Q4_K_XL，确认 MTP 头在。
3. MTP n=2 + q8 主 KV + q8 draft KV。
4. 服务端 `reasoning_effort=medium`，客户端走 `chat_template_kwargs`。
5. `--reasoning-budget` + 正文预留（或强制客户端大 `max_tokens`）。
6. 窗口：先 64K 稳，再按余量加到 96–112K；不要一上来 256K。
7. 文本主力关掉自动 mmproj。
8. 测两套数：关思考看吞吐，开 medium 看工作。
9. 编码失败做 pass@2（本机 +6 题 / 81）。
10. 项目问题必须先 `read_file`。

### 不要做的「优化」

- 为了跑满 256K 把主 KV 打到 q4，然后抱怨模型变傻。
- 为了再快 2 tok/s 上 n=4。
- 用 Ollama 图省事，再花两天查为什么档位不动。
- 双开 3.6 和 3.8。单 4090 一次只能活一个满配 27B。
- 把 xhigh 当「认真模式」长期挂着。它是「烧钱模式」。
- 用评测的 greedy / 关思考分数决定生产配方。

---

## 9. 对「4090 当 OpenClaw 主力」的评价

**适合长期单人主力。** 条件就是现网这套，不要再加第二模型、不要加 slot。

| 维度 | 判断 |
|---|---|
| 编码 / 改仓库 | 可用。Python 稳，JS 格式更脆。pass@2 值得做 |
| 工具调用 | 本机 31/31。不要用会后置 system 的 Claude Code 原模板 |
| 长会话 | 112K q8 预分配，VRAM 不随 uptime 涨。风险是请求溢出窗口，不是慢慢漏内存 |
| 思考体验 | medium + 4k 预算可日常用；短路由关思考 |
| 视觉 | 模型能做，现网没挂 mmproj。要挂就接受窗口回落到 ~60K 或再降 KV |
| 项目记忆 | 无。必须 RAG / 读文件 |
| vs 云端 flash | 质量社区认为能打；体感慢一截（云端 70–180 tok/s 且不思考 2 万 token）。本地的价值是隐私、无限量和工具闭环 |
| vs 继续 3.6 | 3.8 能力明显强；3.6 思考更短、MTP 在某些任务上更好骗。已经决定切 3.8 就不要双开 |

OOM 的真实来源，按概率：再起一个进程 > `-np>1` > 手改 128K > 单次 prompt+predict 超过 112K。不是「开着开着显存涨」。

---

## 10. 关键入口（再查时从这里进）

### 官方 / 权重

- https://huggingface.co/Qwen/Qwen3.8-27B
- https://huggingface.co/unsloth/Qwen3.8-27B-GGUF （现网来源，UD-Q4_K_XL SHA256 `bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372`）
- https://unsloth.ai/docs/models/qwen3.8

### 社区配置真源（X）

- Yume_X 24GB 配方总帖：https://x.com/yume_arasaki/status/2088689423554920813
- AJ 3090 启动行：https://x.com/ItsmeAjayKV/status/2088407570562134021
- Alok 4090 VRAM 地图：https://x.com/analogalok/status/2089403194157965345
- Yume_X 分档（24/16/12/8GB）：https://x.com/yume_arasaki/status/2089501888148603330
- Petko 档位必须走 kwargs：https://x.com/petko_petkovvvv/status/2089040090781663727
- ggerganov 32GB 参考行：https://x.com/ggerganov/status/2088312671196082312

### Reddit / HF / GitHub

- r/LocalLLaMA megathread：https://www.reddit.com/r/LocalLLaMA/comments/1voojjz/
- chiribe 16GB / 73K / 1M token：https://www.reddit.com/r/LocalLLaMA/comments/1vqrt86/
- Simon Willison 默认 xhigh：https://simonwillison.net/2026/Aug/16/qwen-38-27b/
- HF Unsloth #32 谜之 7 tok/s（含 4090 70–80 反证）：https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/discussions/32
- HF Qwen #113 停不下来的思考：https://huggingface.co/Qwen/Qwen3.8-27B/discussions/113
- HF Unsloth #7 Jinja system 断言：https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/discussions/7
- llama.cpp#27107 Claude Code × 模板断言
- llama.cpp#23751 MTP 吃掉窗口（3.6，机制同样适用于 3.8）
- llama.cpp#26873 多卡 mmproj 预填退化
- llama.cpp#22673 MTP 支持（历史；现已在主线）

### 本机已落盘

- 运维：`OPENCLAW_QWEN38_4090_RUNBOOK.md`
- 现网启动：`output/qwen38-27b-4090-20260818/launch/production-18343.sh`
- 能力：`reports/11-capability-portrait.md`
- 窗口：`reports/12-ctx-112k.md`
- MTP：`reports/s2-mtp-matrix.md`
- 空正文补丁：`patches/llama-cpp-reserve-content-tokens.diff`

---

## 11. 未验证 / 不要写进决策的部分

- 官方 SWE-Pro 61.7、LCB 90.3、OSWorld 84.3：本机未复现。
- mmike87「100K+ q8/q4 KV 昼夜之别」：本机只验证到 62K q8 仍清醒。
- 社区 MRCRv2 128K 关思考崩盘：本机 64K 内未崩，128K 未测。
- Alok 240K 多模态 / 73 tok/s @ n=4：未在本机复现，且 n=4 与架构警告冲突。
- Ridge / TQ3_4S / 3.69bpw：没有工具调用公开分。
- 双 4090 SGLang、5090 NVFP4：与现网单卡无关。
- 长时间（天级）leak：KV 预分配从机制上不应涨；未做 24h 泄漏专项。
- Reddit 全文和部分 HF 页在本环境有 SSRF/抓取限制，megathread 后半和部分讨论楼可能还有细节没吸到。

---

## 12. 若还要再拧一圈（按优先级，不是现在必须做）

1. 现网 launch 加上 `--no-mmproj`，防止以后有人把 projector 丢进模型目录。
2. OpenClaw 路由：短 JSON `enable_thinking=false`；改仓库保持 medium。
3. 若 100K 附近体感变傻：先 `-c 96000`，不要先改 q4 KV。
4. 若只做纯代码复述、想再抠速度：可以试会话级关思考，不要改 n-max。
5. 真要视觉：单独开一条 60K + mmproj 服务，不要和 112K 文本主力挤一张卡。

# NInfer 44a2c6c 前端 tokenization 优化方案 v1 Review

**评审对象：** `docs/ninfer-44a2c6c-frontend-optimization-v1/`（GPT Pro，2026-09-24）
**评审日期：** 2026-09-25
**基线：** `tensorninja/ninfer-4090@44a2c6c3392c9d51e76a895ed97bf1867530d252`；现网 `ninfer-4090:prepare-detail`（image `9c2dec8b9ff0`）
**复现材料：** `docs/ninfer-44a2c6c-frontend-optimization-v1-review-assets/`（基准程序、会话生成器、日志分析脚本、29 上的原始结果）

---

## 0. 结论

1. **方案对根因的判断是对的，已在 29 上复现。** `encode_rendered_chat` 先整段编码，再对每个边界从字节 0 重新编码前缀；hint 数等于“最后一条真实 user 之后的 assistant 轮数 + 2”。在一个与最慢请求同形态的会话上（903 KB、22 个 hint），legacy 耗时 101.6 s；现网同形态那条请求实测 80.6 s。
2. **方案漏掉了同量级的第二个根因，而且方案自己的约束会把它锁死。** `Tokenizer::encode` 每选中一个 added token，都要对全部 33 个 added token 执行一次 `text.find(content, pos)`，文本里不存在的 token 每次都扫到末尾。单次编码因此是 O(命中数 × 33 × N)。在上述会话里，单次主编码耗时 4.45 s，其中约 90% 花在这段扫描上（一次编码累计扫描 42 GB）。方案把它归为 P3 常数优化，并要求 B1“沿旧 encode 控制流记录 trace”。**照方案原样实现 B1，最慢那条请求仍需约 4.3 s；在同形态会话上，换成语义完全等价的单遍扫描后实测为 0.44 s。**
3. **建议第一期改为 B0 + B1，B2 推迟。** B0 指单遍 added-token 扫描（保持“最左起点、同位最小 ID”的选择规则），B1 就是方案里的“单次主编码 + 局部边界验证”。29 实测：legacy 101.6 s，B0 10.0 s，B1 4.3–4.5 s，B0+B1 0.43 s，结果全部与 legacy 逐项相等。按两天 1690 条请求估算，tokenize 合计会从 84.2 分钟降到 0.6–1.5 分钟；在此基础上 B2 最多再省约 0.7 分钟，却要引入跨请求共享的可变状态。
4. **验证与发布流程可以大幅精简。** 前端是（请求，资源）的纯函数，等价性可以离线做穷尽式差分。生产 shadow（最慢请求会因此再多花约 80 s）、4 种运行模式、1000 条真实请求 golden（日志里没有请求正文，无法执行）都可以去掉。
5. **方案范围之外、但对“一个大任务要一个多小时”同样关键的问题：** 长请求里有 64 次 full_reset（命中 0），prefill 合计 57.8 分钟，和 append 路径上的 tokenize（64.7 分钟）是同一个量级。成因有两类：主 Agent 与另一个 2 工具小客户端交替占用唯一的 lane（46 次），以及空闲超过 600 s 后 L1 条目被淘汰、而 L2 发布全部因容量被拒（15 次）。建议单独立项，不要并入本方案。

---

## 1. 评审范围与证据

| 证据 | 来源 | 说明 |
|---|---|---|
| 方案包 | 14 份文档、14 个任务卡、tools、data | 全部通读 |
| 源码 | 本地 fetch `44a2c6c` | `source-lock.json` 中 15 个 blob SHA 全部匹配 |
| 现网构成 | 29 只读核查 | 容器启动参数、prepare-detail 源码 diff、artifact 内嵌资源哈希、`/metrics` |
| 请求日志 | 29 `/home/hhtele/ninfer-4090/logs/ninfer-request.jsonl*` | schema 20 共 1690 条 `request_done`（2026-09-22 03:22 至 09-24 23:00 EDT），只含元数据；统计全部基于这 1690 条。9/24 23:28–23:49 的几条仅作为“实况”引用（来自 00:00 轮转后的日志） |
| 基准 | 29，生产构建镜像 | 在 `nvidia/cuda:13.2.0-cudnn-devel-ubuntu24.04`（GCC 13.3、glibc 2.39、`-O3`，与生产 Dockerfile 相同）里编译 44a2c6c 的 `tokenizer.cpp`/`chat_template.cpp`；单核（cpuset 15）、`nice 19`；输入为方案包的合成会话和按生产形态生成的会话；每个候选都与 legacy 逐项比对 |

**没有做的事：** 没有改动生产；没有跑 GPU/HTTP 端到端；没有回放真实请求正文（日志不含正文）。

**对生产的影响说明：** 基准在 29 上累计运行约 20 分钟（单核）。期间有 1 条真实请求（23:46，211,761 token），tokenize 54.66 s，比该会话“每轮 +2 s”的趋势线高约 1 s（约 2%），可能是共享 L3 带来的轻微干扰，也可能只是噪声。基准目录和容器都已清理。

**现网关键事实：**

| 项 | 值 |
|---|---|
| CPU | Xeon Silver 4216，16C/32T，2.1 GHz 基频 / 3.2 GHz 睿频，L3 22 MiB，governor `schedutil`；同机还有 paddle-cpu、onnxocr 等 CPU 负载容器 |
| 内存 | 62 GB，可用约 45 GB |
| 启动参数（与本评审相关） | `--prefix-checkpoint-policy rolling-tool`、`--preserve-thinking`、`--continuation-cache l1-l2`、`--continuation-cache-l1-mib 6144`、`--continuation-cache-l2-mib 8192`、`--max-concurrency 1`；容器无 CPU 配额 |
| 前端资源 | 6 份资源与 HF `Qwen/Qwen3.8-27B@1d4bf0f` 逐字节一致，模板是 ReasoningEffort 语义（见 F6） |
| added token | 33 个（ID 248044–248076），最长 M = 21 字节（`<tts_text_bos_single>`），flags 全为 false |

---

## 2. 方案中经核实正确的部分

| 方案论断 | 核实依据 | 结论 |
|---|---|---|
| `encode_rendered_chat` 对每个边界从 0 重编码前缀 | `processor.cpp:537-589`；29 实测请求编码字节放大 9×–152× | 正确 |
| hint 随工具历史增长 | `chat_template.cpp:61-71, 345-351, 408-416, 437-447` | 正确；需补充驱动量的准确定义（见 F3） |
| added token：最左起点、同位取较小 ID，不是最长匹配；flags 只允许 false | `tokenizer.cpp:176-186, 292-293, 645-671` | 正确。真实词表里就有这种情况：`<tts_text_bos>`（248073）是 `<tts_text_bos_single>`（248075）的前缀，按最长匹配实现会改变结果 |
| 44a2c6c 没有 `encode_with_boundaries` 等接口 | `tokenizer.h` 只有 `encode`/`decode` | 正确 |
| `append_frontier` 在 tokenize 之后才产生，前端不能拿它当开关 | 调用链与 overlay 计时位置 | 正确 |
| 当前请求的 exact prefix 不代表对未来追加稳定 | 推理成立 | 正确 |
| B1 局部分解 `E(R[:b]) = T[:t_r] ∥ E(R[r:b])` | 附录 B 证明；29 上 7 个会话、20 个 legacy 对照轮次的所有边界逐项相等 | 正确。局部输入通常只有 `assistant\n`：生产形态会话 25 个查询合计只编码 212 字节 |
| B2 guard `r + (M-1) ≤ LCP` | 附录 B 证明；29 上 21 个追加轮次的拼接结果与完整编码相等 | 正确。M = 21，21 个切点全部落在旧文本末尾前 31 字节 |
| 现网 overlay 需要单独审计 | 已完成（F7） | 纯观测补丁，前端输出语义未变 |
| render 是毫秒级，保留全量 render | 最慢请求 render 13 ms | 正确 |

方案在语义约束上很严谨，尤其是 added-token 优先级、边界错误契约、hint 顺序/重复/kind 不得改变这几点，都应原样保留。

---

## 3. 主要问题与修订建议（按严重度）

### F1【P0】added-token 扫描是二次项，被错放成了 P3

**代码事实。** 下面是 44a2c6c 的主循环（`src/targets/qwen3_8/impl/frontend/tokenizer.cpp:645-671`，节选）：

```cpp
    while (pos < text.size()) {
        std::size_t match_pos         = std::string_view::npos;
        const AddedToken* match_token = nullptr;
        for (const AddedToken& token : added_tokens_) {
            if (token.content.empty()) { continue; }
            const std::size_t found = text.find(token.content, pos);
            if (found == std::string_view::npos) { continue; }
            if (match_token == nullptr || found < match_pos) {
                match_pos   = found;
                match_token = &token;
            }
        }
        // ... append_bpe_ids(ordinary segment), push added id, pos = match_pos + size
    }
```

每选中一个 added token，就对 33 个 token 各做一次从 `pos` 到文本末尾的 `find`。Agent 会话里通常只会出现约 8 个（`<|im_start|>`、`<|im_end|>`、`<think>`、`</think>`、`<tool_call>`、`</tool_call>`、`<tool_response>`、`</tool_response>`），另外约 25 个每次都扫到末尾。所以单次编码的扫描量约为 命中数 × 25 × N/2，随会话长度平方增长。

**实测（29，生产构建环境，单次主编码）：**

| 会话 | 渲染字节 | added 命中 | 单次编码 `find` 扫描量 | 旧扫描器 | 单遍扫描 | 扫描占比 |
|---|---|---|---|---|---|---|
| medium（合成） | 170 KB | 500 | 1.1 GB | 0.083 s | 0.038 s | 54% |
| deep-fragmented（合成） | 542 KB | 1,750 | 11.9 GB | 0.666 s | 0.127 s | 81% |
| 190k（合成） | 709 KB | 3,000 | 26.7 GB | 1.652 s | 0.151 s | 91% |
| 生产形态 | 903 KB | 3,823 | 42.2 GB | 4.450 s | 0.448 s | 90% |

生产日志也能对上：9/22 03:55→03:57 同一会话每多一轮（多一个接近全长的前缀重编码），tokenize 增加 3.8–4.3 s（885 KB 左右），与生产形态会话单次编码 4.45 s 一致。

**对方案的影响。** 方案 `03 §3.2` 写的是“第一次实现不要重写 BPE，不改变 added-token 选择。沿旧 encode 控制流记录 trace 即可”，`12 §12.3` 又把“ID-priority 保持的多模式搜索器”放在 P3。照此实现，B1 只是把 H+4 次编码（主编码、H 个 checkpoint hint、3 个专用边界）降到 1 次，而这 1 次在生产尺寸下仍要 4.3–4.5 s（与 H 无关），最慢请求的 TTFT 仍在 5 s 左右。方案在 `08 G4` 里只设了“相对 legacy 下降 ≥80%”的相对门，这个结果（下降约 95%）会通过门槛，却解决不了体感问题。

**建议。**

- 把“单遍 added-token 扫描”从 P3 提到第一期，与 trace 一起在 T03 实现。它**不改变选择规则**，只改变搜索算法：旧实现与新实现都是在所有“起点 ≥ pos 的完整匹配”里取 (起点, ID) 字典序最小者（证明见附录 B.1）。这与方案“不改变 added-token 选择”的约束并不冲突。
- 实现可以很小。trace 需要的 restart 点就在这里顺手记录：

```cpp
// Selection rule unchanged: smallest start >= pos, then smallest id.
// by_first_byte_ buckets keep added_tokens_ in id order.
std::size_t match_pos = std::string_view::npos;
const AddedToken* match = nullptr;
for (std::size_t i = pos; i < text.size() && match == nullptr; ++i) {
    for (const AddedToken* token : by_first_byte_[static_cast<unsigned char>(text[i])]) {
        if (text.compare(i, token->content.size(), token->content) == 0) {
            match_pos = i;
            match = token;
            break;
        }
    }
}
```

- 这一改动放在 `Tokenizer::encode` 内部，`count_tokens`、vision 路径、`/tokenize` 类接口会同时受益（见 F5）。
- 差分测试要专门覆盖：`<tts_text_bos>` 与 `<tts_text_bos_single>` 这类前缀冲突对、不完整标记（`<|im_sta`）、相邻/重叠标记、`parse_added_tokens=false`。
- **可以单独先发（B0）。** 只改 `Tokenizer::encode` 一个函数、保留旧边界算法，生产形态会话从 101.6 s 降到 10.0 s，等价性论证最简单。

### F2【P1】做完 B0+B1 后，B2 的收益很小，建议推迟

用 29 实测的吞吐对 1690 条 schema 20 请求逐条估算（B1 按“一次旧扫描器编码”、B0+B1 按“纯 BPE”、B2 按“只编码后缀”，吞吐取真实语料的 1.57–3.60 MB/s）：

| 方案 | tokenize 合计（实测为 84.2 分钟） |
|---|---|
| B1（沿用旧扫描器） | 6.4–7.3 分钟 |
| **B0 + B1** | **0.6–1.5 分钟** |
| B2（在 B0+B1 之上） | 0.6–0.8 分钟 |

B2 最多再省约 0.7 分钟（两天），而它需要：Frontend 内共享的可变缓存、锁与 pin、字节预算、LCP + guard 证书、资源 identity 隔离、失配熔断，以及方案 T06–T08 和 T09–T12 的大部分验证工作。这些复杂度与收益不成比例。

**建议：** 保留 B2 的设计文档，但默认不实现。触发条件建议写成：B0+B1 上线后，120K+ 热续写请求的 tokenize p90 仍大于 1 s。这与方案 `12 §12.2` 的决策规则是一致的，只是把数据提前给出了。

### F3【P1】hint 数的真实驱动量，以及合成数据的偏差

**驱动量是“最后一条真实 user 之后的 assistant 轮数”，不是总消息数。** 规则见 `chat_template.cpp:408-416`：只有 `i > last_query_index` 的 assistant 才会加 StableTurn/Rolling hint，`last_real_user_query` 会跳过纯 `<tool_response>` 的 user 消息。证据：

- 用户窗口之后的 73 条长请求，字节和消息都更多，tokenize 反而更短（120–185K 档 p50：15.3 s / 459 条 / 598 KB，窗口内是 27.3 s / 358 条 / 493 KB）。
- 同一会话里 tokenize 按轮次线性增长：9/22 03:40→03:57 从 17.4 s 涨到 80.6 s（约 +3.7 s/轮）；9/24 21:57→23:49 从 31.5 s 涨到 61.7 s（约 +2.1 s/轮）。
- 用户发新消息后会骤降：9/23 22:34→22:38，同一会话渲染字节几乎不变（569→572 KB），消息只多 2 条，tokenize 从 19.9 s 降到 5.0 s；9/23 00:08→21:45 从 52.0 s 降到 4.3 s（527→531 KB）。
- 同样约 903 KB 的生产形态会话，H≈7 时 legacy 38.5 s，H≈22 时 101.6 s（下文 H 均指 checkpoint hint 数）。

**生产会话的编码字节放大约为 H+1.5，不是方案写的 1+H/2。** 生产里 hint 集中在最近几轮，每个前缀长度都接近 B（生产形态实测：7 个 hint 为 9.0×，22 个为 23.5×）；1+H/2 只适用于“开头一条 user、之后全是工具轮”的合成会话。

**方案包的合成数据偏离生产。** `tools/generate_sessions.py` 只在开头放一条 user，max-shape（769 条）因此有约 384 个 hint，而生产最慢那条按增量反推只有约 20 个。合成会话的 legacy 耗时会被严重高估（190k 合成会话在 29 上 legacy 为 178 s）。另外合成内容的字节/token 比为 2.4–2.7，生产为 3.6。这些数据不影响“单次主编码”的测量，但不能用来预测 legacy 或用作性能门的输入。

**建议：** 生成器增加 `turns_since_last_user` 参数，主基准用 H≈5/20 两档；T01 的日志字段加上 hint 数（`checkpoint_hints`）和 `boundary_queries`，让 H 在线上可见。

### F4【P1】验证与发布流程过重，其中一部分无法执行

| 方案要求 | 问题 | 建议 |
|---|---|---|
| `08 §8.4`：≥1000 条真实资源前端请求 golden，其中 ≥50 条 120K+ | 现网日志只有元数据，没有请求正文，做不到（方案自己也承认） | 以生产形态合成会话为主；如需真实输入，经用户明确授权后，在代理层采集少量会话到受控目录 |
| 生产 shadow（同步双算，有界采样） | 被采样的请求要额外跑一遍 legacy，最慢的请求会多出约 80 s；采样只能减少受影响请求的数量 | 不上生产 shadow。前端是纯函数，任何捕获到的输入都可以离线完整比对 |
| 4 种模式 + 4 个 CLI 参数，T12 canary 链路 | 对 B0+B1 这种可证明等价的改动过度设计 | 最多保留一个 legacy / single-pass 两档开关；回滚靠切回 `ninfer-4090:prepare-detail` 镜像 |
| T11 维护窗口端到端 | 必要 | 保留一次；测试时需隔离 2 工具小客户端，否则 GPU 复用路径会被交替请求打乱（见 §4） |

**建议的最小充分验证：**

1. 合成字节词表与真实词表上，≤256 字节样本的全部字节切点；
2. 2 万次随机变换（插入完整或残缺的 added token、NFC 组合符、非法 UTF-8、重复/无序边界）；
3. 生产形态长会话的全部边界逐项相等（token、三个 optional 边界、hint 顺序/kind/重复、错误类型与名称）；
4. 现有 CTest（`ninfer_qwen3_8_frontend_test` 等）；
5. 在 29 上跑 CPU-only 基准，不需要停机（本评审就是这样做的）；
6. 一次维护窗口做 HTTP 端到端：同一会话多轮 append，GPU reused/computed token 与基线一致，无新增 `request_error`。

### F5【P2】vision 与 count_tokens 路径应一并受益

`encode_rendered_chat` 同时被 text 路径（`frontend.cpp:900`）和 vision 路径（`processor.cpp:655`）调用；`count_tokens` 用的是 `tokenizer->encode(rendered.text)`（`frontend.cpp:931`）。方案 T05 让“media 暂时走 legacy”，反而要多维护一条分支。

**建议：** B0 放在 `Tokenizer::encode` 内部，B1 直接替换 `encode_rendered_chat` 的实现，三条路径共用同一份证明和同一组差分测试。旧实现移到测试代码里作为 oracle，不在产品代码里长期保留双实现。此外，vision 会把每张图展开成大量 `<|image_pad|>`，每个都是一次 added-token 命中，旧扫描器在带图的长上下文里会更慢（推断，未实测）。

### F6【P2】资源身份：转换器的官方清单与现网 artifact 不一致

现网 artifact（`/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer`）内嵌的前端资源：

| 资源 | SHA256（前 16 位） | 与 HF `Qwen/Qwen3.8-27B@1d4bf0f` | 与 44a2c6c `official_resources.py` |
|---|---|---|---|
| tokenizer.json（12,809,320 B） | `0997f410c57a1f4e` | 一致 | 不一致（清单为 `5f9e4d49…`） |
| tokenizer_config.json | `b11349aafa7cdc6a` | 一致 | 不一致（清单为 `5186f0de…`） |
| chat_template.jinja | `c3cf9e34abf4f9e3`（ReasoningEffort） | 一致 | 不一致（清单为 `e84f32a2…`，ThinkingToggle） |
| generation_config.json | `e70c136c1b78ddc1` | 一致 | 一致 |
| preprocessor / video_preprocessor | `27225450…` / `7768af27…` | — | 一致 |

**影响与建议：** 方案 T02 要求“从旧 artifact 六对象读取资源”，方向正确。需要补一条明确警告：不要用 `tools/convert/qwen3_8/common/official_resources.py` 校验现网资源，那会拒绝生产用的资源。oracle 可以直接从 artifact 读取（只需读目录和 6 个资源对象，约 13 MB），也可以用 HF `1d4bf0f`，二者逐字节一致。另外，生产走的是 ReasoningEffort 模板，`preserve_thinking` 默认为 true，再加上服务端 `--preserve-thinking`，历史里保留了全部 reasoning，渲染字节因此偏大。差分测试应以这一组合为主。

### F7【P2】prepare-detail overlay 审计结果（方案当时拿不到）

对 `/home/hhtele/ninfer-4090` 做逐文件哈希比对：与 44a2c6c 相比只有 11 个文件不同，共 +125/−11 行。文件 mtime 为 9/21 23:37，镜像 `9c2dec8b9ff0` 在 23:45 构建，二者对得上。`tokenizer.cpp`、`processor.cpp`、`chat_template.cpp` 与 44a2c6c 完全相同，所以 A20 与 A0 的前端输出在源码层面等价。需要注意的语义：

- `prepare_detail.tokenize` 包住的是整个 `encode_rendered_chat`，包含全部边界重编码，不是“一次整段 BPE”。用户按“约 3000 token/s 的整段 BPE”理解并不准确：29 上旧扫描器单次编码约 6 万 token/s，纯 BPE 约 60 万 token/s，3042 token/s 是多次前缀重编码叠加二次扫描之后的有效吞吐。
- `timings_seconds.prepare` 的截止点从 submit 之前挪到了 `engine_submit` 之后，与 schema 19 对比时要注意（该段实测接近 0）。
- `rendered_chars`、`content_chars` 实际是 UTF-8 字节数（`std::string::size()`）。
- 建议 B0/B1 分支 rebase 这份 overlay，保留 schema 20 字段，再加上 hint 数、`boundary_queries`、主编码字节数。

### F8【P3】数据与文档的小修正

- 分档里“差 1 条、归属未知”的那条在 8–32K 档：单消息、约 100 KB 的冷请求（tokenize 0.09 s，prefill 5.6 s）。
- 首条 schema 20 记录是 9/22 03:22 EDT（即 07:22 UTC），不是 07:40 EDT。
- “约 81 万字符”实为渲染后 889,726 字节。
- “冷启动 100 条”无法用“命中 <10%”复现（按该条件有 226 条，且大多是短请求），需要注明额外的筛选条件。
- `source-lock.json` 有 7 处行号范围超出文件实际长度（如 `chat_template.cpp` 只有 467 行，引用到 497）；blob SHA 全部正确。
- 方案 ADR“增大 GPU L1：不做，因为已 99.9% 命中”只对 append 路径成立，见 §4。

以上都不影响主要结论。

---

## 4. 方案范围之外：长会话的 full_reset

**数据。** 长请求（≥32K）共 272 条，按复用路径：

| 路径 | 条数 | prefill 合计 | tokenize 合计 |
|---|---|---|---|
| append_frontier | 200 | 1.1 分钟 | 64.7 分钟 |
| full_reset（命中 0，`not_attempted`） | 64 | 57.8 分钟 | 15.6 分钟 |
| restore_turn_checkpoint | 8 | 0.2 分钟 | 2.3 分钟 |

**成因拆分：**

| 成因 | 条数 | prefill 合计 | 依据 |
|---|---|---|---|
| 客户端交替（与上一请求的间隔 ≤600 s，多数时间上重叠） | 46 | 32.8 分钟 | <8K 的 1417 条里有 1402 条带 2 个工具，长请求 272 条里 271 条带 12 个工具。9/22 04:38 起，小客户端约每秒一个请求，与主 Agent 交替；主 Agent 在 95K→121K 之间连续约 40 轮 full_reset |
| 空闲超过 600 s | 15 | 21.3 分钟 | L1 idle TTL 默认 600 s（`include/ninfer/types.h:98`），生产未覆盖；遥测显示请求结束约 10 分钟后 `l1_entries` 1→0。随后向 L2 发布全部失败：`/metrics` 中 `publication_failed_capacity_total=14`、`publication_successes_total=0`，对应 `RejectedTooLarge`（`continuation_cache.cpp:756-775`），即 21 万 token 会话的 L2 镜像超过了 8 GiB 的 L2 预算 |
| 服务重启后的首个请求 | 2 | 2.0 分钟 | — |
| 客户端压缩历史（新前缀） | 1 | 1.6 分钟 | — |

**实况：** 9/24 22:32、23:00、23:28、23:46 连续 4 轮都是 full_reset，每轮 prefill 约 112 s、tokenize 47–55 s，TTFT 约 160–167 s。紧接着 23:47 起的几轮重新命中 L1，但 TTFT 仍有 57–62 s，几乎全部是 tokenize。两个问题在同一个会话里叠加。

**建议（需先验证，单独立项）：**

- 空闲类：生产把 L2 设为 8192 MiB，而上游镜像默认是 16 GiB 主存 L2 加 48 GiB 磁盘 L3。可以先测出 21 万–25 万 token 会话的实际镜像字节数，再决定把 `--continuation-cache-l2-mib` 提到能容纳一条长会话（主机可用内存约 45 GB），或启用 L3，或提高 `--continuation-cache-l1-idle-seconds`（L1 是保留显存，要评估它与峰值显存的关系）。这些都需要重启服务。
- 交替类：先确认 2 工具小客户端的来源（标题生成、摘要，还是子代理），再在“路由到其他端点”“让 L1 同时容纳两路状态”“主会话 session alias”之间选择。
- 方案 ADR“增大 GPU L1：不做，已 99.9% 命中”依据的是 append 路径的中位数。算上 full_reset 这条尾巴，这个依据不完整。

---

## 5. 实测数据汇总（29，生产构建环境）

**完整请求（legacy 为 44a2c6c 的 `encode_rendered_chat` 逐行复刻）：**

| 会话 | 消息 | 渲染 | token | hint | 编码字节放大 | legacy | B0 | B1 | B0+B1 | B2 |
|---|---|---|---|---|---|---|---|---|---|---|
| medium（合成） | 100 | 170 KB | 64,051 | 51 | 27.2× | 1.91 s | — | 0.084 s | 0.038 s | 0.001 s |
| deep-sparse（合成） | 164 | 513 KB | 198,244 | 83 | 43.1× | 9.35 s | — | 0.263 s | 0.112 s | 0.001 s |
| deep-fragmented（合成） | 350 | 542 KB | 203,075 | 176 | 89.7× | 44.79 s | — | 0.673 s | 0.126 s | 0.001 s |
| 190k（合成） | 600 | 709 KB | 296,832 | 301 | 152.3× | 177.82 s | — | 1.702 s | 0.156 s | 0.002 s |
| 生产形态 H≈7 | 769 | 903 KB | 272,819 | 7 | 9.0× | 38.47 s | — | 4.353 s | 0.433 s | 0.001 s |
| 生产形态 H≈22 | 768 | 903 KB | 273,012 | 22 | 23.5× | 101.56 s | 10.01 s | 4.25–4.48 s | 0.426–0.443 s | 0.001 s |

说明：

- 所有候选与 legacy 逐项相等（token、三个边界、hint 顺序与 kind）。没跑 legacy 的轮次，以已被 legacy 验证过的 B1 结果作参照。B2 数据来自第 1–3 轮（需要上一轮作为缓存）。
- B0 在单独一轮运行中测得，同一轮 B1 为 4.25 s、B0+B1 为 0.426 s；表中区间反映两次运行之间的差异。
- 生产形态会话中，legacy 全部编码累计输入 21.2 MB、`find` 累计扫描约 0.96 TB；B1 局部边界只编码了 212 字节。

**纯 BPE 吞吐（29，512 KiB 原始文本，几乎不含 added token）：**

| 内容 | 耗时 | 吞吐 |
|---|---|---|
| 中文文档 | 0.333 s | 1.57 MB/s |
| 英文文档 | 0.213 s | 2.46 MB/s |
| C++ 源码 | 0.182 s | 2.88 MB/s |
| JSON 日志 | 0.146 s | 3.60 MB/s |

B0+B1 之后剩下的就是这部分纯 BPE 成本，最慢那条请求（889,726 字节）约 0.25–0.57 s。如果以后还要再压，才轮到方案 P3 里的 heap BPE、减少临时字符串等常数优化。

---

## 6. 修订后的执行路径

| 原任务 | 建议 |
|---|---|
| T00 | 大部分已由本评审完成（overlay diff、镜像 ID、资源哈希、启动参数），在工作分支里固化即可 |
| T01 | 保留；日志加 hint 数与 `boundary_queries` |
| T02 | 保留；资源从 artifact（或 HF `1d4bf0f`）读取，不按 `official_resources.py` 校验 |
| T03 | **扩大**：单遍 added-token 扫描（B0）+ restart trace |
| T04 / T05 | 保留；直接替换 `encode_rendered_chat` 的实现（text 与 vision 共用），旧实现移入测试作 oracle |
| T06–T08 | 推迟为 B2，按 F2 的触发条件决定是否实施 |
| T09 | 精简为 F4 的差分验证清单 |
| T10 | 在 29 上跑 CPU-only 基准，不需要停机；可直接复用本评审的基准程序 |
| T11 | 一次维护窗口做端到端，隔离 2 工具小客户端 |
| T12 | 去掉 shadow 与 canary 链路；回滚为切回 `ninfer-4090:prepare-detail`（`9c2dec8b9ff0`） |
| T13 | 保留独立 review |

**门槛调整：**

- G1（精确等价）保持不变，任何失配都是 FAIL。
- G2（工作量）改为三项结构性指标：主编码 1 次；`find` 扫描量为 O(N)；局部边界字节约为“查询数 × 十几字节”。
- G4（性能）在相对门之外增加绝对门：29 上约 900 KB 的生产形态会话，tokenize ≤ 1 s（实测 0.43 s）。
- G5（无回归）：短请求也会变快（medium 0.083 s → 0.038 s），<8K 不应回退。

**工作量估计：** B0 约 0.5–1 天（含测试），B1 约 1–2 天，验证约 1–2 天，另需一次 30–60 分钟的维护窗口。原方案完整范围（含 B2、shadow、canary、4 种模式）估计要 2–4 周。

---

## 7. 预期收益（有界估算）

| 范围 | 现状 | B0+B1 之后 |
|---|---|---|
| 最慢那条请求（245,194 token） | tokenize 80.6 s，TTFT 81.0 s | tokenize 约 0.25–0.57 s，TTFT 约 1 s |
| 两天全部 1690 条 | tokenize 84.2 分钟（占服务端忙碌时间 38.9%） | 0.6–1.5 分钟 |
| 长会话段（265 条，墙钟 437 分钟） | tokenize 81 分钟，占服务端忙碌时间 50.7%、墙钟 18.6% | 墙钟约减少 18%，服务端等待约减半 |

再加上 §4 的 full_reset 修复，长会话段最多还能省下约 54 分钟 prefill（交替类与空闲类之和，上限，需验证），也就是墙钟再少约 12%。剩下的是 decode（约 21 分钟）和服务端空闲时间（工具执行、用户思考、客户端处理，约 277 分钟），这部分服务端改不了。对最严重的 9/22 03:39 那一段（226K–245K），tokenize 占墙钟 62.6%，修复后体感改善最明显。

---

## 8. 风险与未验证项

- 基准输入是合成的生产形态会话，不是真实请求正文。真实内容的纯 BPE 成本按语料类型在 1.6–3.6 MB/s 之间，所以 B0+B1 的绝对耗时有约 ±50% 的不确定性，但量级（亚秒）不变。
- 基准程序逐行复刻了 legacy 的 `encode_rendered_chat` 和 `Tokenizer::encode`，并与生产用同一编译器和运行库，但它不是生产二进制本身；绝对值可能有少量内联和布局差异。
- 没有做 GPU/HTTP 端到端验证。
- L2 镜像大小是从 `RejectedTooLarge` 推断出来的（大于 8 GiB），没有直接测量。
- vision 路径的放大程度是推断，没有实测。

---

## 附录 A：复现方法

基准程序（`bench_ftc.cpp`）直接 `#include` 44a2c6c 的 `tokenizer.cpp`，以便调用其内部函数；legacy 路径逐行复刻 `encode_rendered_chat`，候选包括 B0、B1、B0+B1 和 B2 模拟，每个候选都与参照逐项比较，失败时退出码非零。

```bash
# 在 44a2c6c 源码根目录（或只含 src/include/third_party 子集的目录）
gcc -O3 -DUTF8PROC_STATIC -c third_party/utf8proc/utf8proc.c -o utf8proc.o
g++ -std=c++20 -O3 -DNDEBUG -DUTF8PROC_STATIC -Iinclude -Isrc -Ithird_party -Ithird_party/utf8proc \
  bench_ftc.cpp src/targets/qwen3_8/impl/frontend/chat_template.cpp \
  src/targets/qwen3_8/impl/frontend/digest.cpp src/text/unicode.cpp utf8proc.o -o bench_ftc

# res/ 放 tokenizer.json、tokenizer_config.json、generation_config.json、chat_template.jinja
# （从 artifact 读取，或取 HF Qwen/Qwen3.8-27B@1d4bf0f，二者逐字节一致）
./bench_ftc res sessions/prodshape.jsonl --legacy-turns=4   # 每轮一行 JSON
FTC_B0=1 ./bench_ftc res sessions/prodshape.jsonl --legacy-turns=0
./bench_ftc res --raw raw/zh_docs.txt                         # 纯 BPE 吞吐

python3 gen_prodshape.py 769 20 0.78 > sessions/prodshape.jsonl  # 生产形态会话
python3 analyze_logs.py /path/to/logs                            # 复现本文全部日志统计
```

29 上的做法：把上述文件放到 `/tmp` 下，用 `docker run --rm --network none --cpuset-cpus 15 -v DIR:/w -w /w nvidia/cuda:13.2.0-cudnn-devel-ubuntu24.04 ...` 编译和运行，不需要 GPU，也不影响生产服务。原始结果见 `results-29/`。

---

## 附录 B：正确性论证草图

**B.1 单遍扫描与旧扫描等价。** 旧实现在游标 `pos` 处，对每个 added token t 求最早的完整匹配起点 f_t ≥ pos，取 f_t 最小者；并列时保留遍历顺序（ID 升序）中的第一个。这等价于在集合 {(s, id) : 文本在 s 处完整匹配 id，s ≥ pos} 中取字典序最小元素。单遍扫描从 pos 起逐位检查首字节桶内按 ID 升序排列的 token，遇到第一个匹配就停：找到的 s 是最小起点，且是该起点上 ID 最小的 token，所以是同一个元素。普通片段与游标推进完全相同，输出因此相同。

**B.2 B1 局部分解。** 设 T = E(R)，r 是 E(R) 扫描中某个被选中 added token 的结束位置（或 0），且 r ≤ b。考虑前缀 P = R[:b] 的扫描：P 中的任何完整匹配都是 R 中的匹配（P 是 R 的前缀）；而 R 的扫描在游标 < r 时选中的匹配都结束于 ≤ r ≤ b，所以也存在于 P 中。候选集合只会变小，而原来的最小元素仍在其中，因此 P 的扫描在到达 r 之前做出完全相同的选择；r 之前的普通片段也相同，于是前 t_r 个 token 相同。r 之后，P 的扫描等价于独立编码 R[r:b]，因为每个普通片段各自做 NFC、预切分和 BPE，互不影响。所以 E(R[:b]) = T[:t_r] ∥ E(R[r:b])，边界合法性只需比较 T[t_r : t_r+|L|] 与 L，再套用原来的非空、allow_full、uint32 规则。

**B.3 B2 guard 充分。** 设旧文本 R0、新文本 R1、最长公共前缀长度 L，r 是 R0 扫描中某个 added token 的结束位置，且 r + (M−1) ≤ L，其中 M 为 added token 的最大字节长度。任何起点 q < r 的匹配，终点不超过 q + M ≤ r − 1 + M ≤ L，完全落在公共前缀内，因此在 R0 和 R1 中同时存在或同时不存在。两次扫描在 r 之前的候选集合相同，选择相同，于是 E(R1) = T0[:t_r] ∥ E(R1[r:])。普通文本的 EOF 不是 added token 的结束位置，不能作为 r。真实词表 M = 21；在 Agent 续写场景下，旧文本以 `<|im_start|>assistant\n<think>\n` 结尾，满足 guard 的最大 r 位于其前一个 `<|im_end|>` 之后，也就是旧文本末尾前 31 字节，与实测一致。

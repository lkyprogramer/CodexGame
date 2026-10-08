# 00 · 范围、基线与证据分级

## 0.1 用户目标与工作负载

目标是在既有 4090、Qwen3.8-27B、262,144 原生窗口、MTP3、`rk4v4-e8`、rolling-tool、L1/L2 continuation 上，消除长 Agent 热续写前的几十秒 CPU tokenize 等待。用户已完成 NInfer/vLLM 对照；本次不重复引擎选型。诊断显示主模型 hot prefill 只有约零点几秒，decode 仍约100–115 token/s，而整个 `encode_rendered_chat` 成为 prepare 的主要部分。

固定源提交见 [source-lock](../source-lock.json)。这是设计绑定的历史版本，不随 GitHub 当前 HEAD 漂移。实际生产是固定基线叠加本地 prepare-detail；其原始 diff 不在本包中，执行者必须获取，不得用新 master 代替。

## 0.2 证据不是同一层

| 标签 | 含义 | 本次可用内容 | 不允许外推 |
|---|---|---|---|
| `PINNED_SOURCE_READ` | 固定 commit 的代码事实 | scanner、边界验证、旧头文件、hint 规则已复核 | 不等于执行了产品二进制 |
| `REVIEW_RETAINED_RAW` | 用户附件中的保留 CPU JSONL | 28条session、4条raw语料记录 | 不等于真实请求正文或HTTP |
| `REVIEW_REPORTED` | 评审在节点29报告的现场事实 |1690日志、overlay审计、资源匹配、full_reset分类 | 未附logs/diff，无法本地独立重算 |
| `LOCAL_HELPER_VERIFIED` | 本包作者实际运行的辅助测试 |文档工具、有限词法模型、数据可复现 | 不证明NFC/BPE/真实词表C++产品等价 |
| `DESIGN_REQUIREMENT` | AI 必须实现/验证的合同 |B0+B1设计、G0–G7 | 不能标成现有能力 |
| `DEFERRED` | 不进入首期 |B2、full_reset配置修复、DFlash2等 | 不得偷偷扩展产品范围 |

评审的 101.56 → 0.443 秒是保留数据；约 10.01 秒 B0 只有报告正文。估算全段 tokenize 从84.2分钟降至0.6–1.5分钟是以语料吞吐代入生产元数据的模型，不是已完成发布后指标。

## 0.3 双根因及主要变量

令 B 为渲染 UTF-8 字节数，A 为主编码中选中的 added token 数，V 为词表中 added token 数，Q 为实际边界查询数，b_j 为各查询字节切点。

旧成本至少包含：主编码加 `Σ E(R[:b_j])`；每次 E 内又以每个选中 added token 为轮次，对全部 V 个 token 从当前位置执行 find。若多数 token 不出现，每个 find 会搜索到尾部；在标记密度近似固定时可形成随 B 二次增长的工作。

Q 与总消息数不是同一变量。实际 H=`checkpoint_hints.size()`；主要受最后真实 user 之后的 assistant/tool 形态驱动，同时受 system、generation opener、checkpoint policy 影响。边界常集中在接近全文末尾的位置，因此不能用固定 `1+H/2` 预测生产放大；使用真实 `B+Σb_j`。

## 0.4 首期交付与不做项

交付：B0 immutable ID-order first-byte scanner；B1 request-local trace 和局部边界验证；必要计数器；独立旧 oracle；有限全部字节切点与至少20,000随机变换；生产形态合成语料；CPU绝对/相对门；一次隔离HTTP和回滚；独立review。

不交付：跨请求 token cache、incremental render、tokenizer资源重写、BPE算法重写、模型升级、MTP深度调整、CUDA新kernel、KV格式调整、L1/L2容量或TTL变更、其它客户端迁移。full_reset 的定位资料单列 [17](17_FULL_RESET_SEPARATE_PROJECT.md)，不是 tokenizer 发布条件里的自动配置动作。

## 0.5 结果边界

本包内 gate 初始均 `NOT_RUN`。节点29的CPU负载和镜像环境可能变化；基准要记录真实环境。输入超过原生窗口仍可做CPU函数测试，但HTTP必须满足准确token数与输出预算。不能用“名叫190k”“字符/3”替代 tokenizer 校准。没有真实请求正文，合成输入就必须标为合成。

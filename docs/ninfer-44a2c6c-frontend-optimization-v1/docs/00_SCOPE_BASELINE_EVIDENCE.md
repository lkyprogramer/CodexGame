# 00｜范围、基线与证据

## 0.1 固定产品条件

用户部署：单 RTX4090 24GB、约64GB主存；`qwen3.8-27b/groupwise-int`，旧 16.96GiB `.ninfer` 制品；262144 context/KV capacity；`rk4v4-e8`；MTP3 + optimized draft head；max-concurrency=1；rolling-tool/L1-L2 continuation；默认 thinking on/medium、temperature=1、top_p=.95、top_k=20、presence_penalty=0。

源码锁定 `44a2c6c3392c9d51e76a895ed97bf1867530d252`。该提交将 request log schema 18 升到19；schema20/prepare-detail 是本地诊断 overlay，不是该 commit 的原生能力。提交元数据与代码固定来源见 [13](13_SOURCE_REFERENCES.md)。

已给出的部署文档记录模型 SHA256 为 `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`、18210531328 bytes。实施时必须本机复核，不能仅凭旧文档宣称现网仍一致。维持原有代理入口/model ID，不绕过兼容层改变 medium 语义。

## 0.2 用户报告，非本次复跑

诊断镜像从“2026-09-22 07:40 EDT”到“主机9/23 21:50”；报告 schema20 request_done=1617，9/22=1600、9/23=17。后一个主机时间未明确时区，本包保留原记法，不擅自合并为确定的 UTC 采集时长。

最慢记录：245194 prompt tokens、769 messages、约81万字符，append_frontier，cache显示100%；template_render .013s、tokenize80.6s、prefill.39s、TTFT81.0s；decode约100t/s。换算 245194/80.6≈3042 是**整个计时区域的有效吞吐**，并非已经证明底层 BPE 单次只跑3042t/s。

分档原始数字在 `data/diagnostic_summary.json`。列出的各档 n 加和为1616，而总数1617；8–32K 未列。差1条的归属未知，不补造。p50×n 不能当真实总CPU用时；几个 p50 也不能相加推演 TTFT。<8K的1417条占约87.6%，不能据此认定全部来自真实长 Agent，样本来源须分层。

120–185K内两组消息数：200–349条组 n23/tokenize20.6s/字符426K；≥350条组 n31/37.1s/468K。该相关性与重复 hint 编码机制相符，但未控制文本分布和具体 hints，不能据此量化每条消息的因果成本。

## 0.3 证据分层

- **OBS**：用户提供的诊断汇总。tokenize 是已测大头；还没有取得原始逐请求行或请求正文。
- **SRC**：指定 commit 源码。重复前缀编码、hint 产生、旧 BPE 和 added-token 选择规则已经核对。
- **INFER**：重复边界工作可解释消息碎片化放大；需新增工作计数与同输入实验确认占比。
- **PLAN**：单次扫描/增量缓存的性能目标，不是实测结果。

不要把 SRC 的潜在复杂度直接宣称为 OBS 每一秒的来源；tokenize 区域还包含主编码、added-token查找、NFC、BPE及多个前缀调用。T01须分开计数。

## 0.4 不变项与非目标

不改 GPTQ/EXL3/Bonsai 等模型路线；不改 `.ninfer` loader/权重；不改 E8 KV、MTP K、GDN/ReplaySSM、attention、CUDA graphs、prefill chunk、sampling、工具序列化。保留全文 render 与元数据重建，它们目前毫秒级。多模态走原路径，不能因为仅优化text而破坏原有Vision。

不以“只支持 append_frontier”删除其他路径。第一期跨请求加速只接纳前端证明的稳定追加候选；rewrite/compaction 等回退到正确的单请求编码。后端仍自己判定 append/restore/reset。

## 0.5 完成定义

完成不是“代码可编译”或“缓存命中高”。必须同时满足独立 oracle、边界/错误语义、工作放大量、CPU预算、真实HTTP热续写、GPU无回归及回滚门。没有本机/真实资源的门保持 NOT_RUN。

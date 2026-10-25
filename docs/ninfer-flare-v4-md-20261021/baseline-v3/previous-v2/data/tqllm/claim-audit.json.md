# V2 支撑材料：`data/tqllm/claim-audit.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: data/tqllm/claim-audit.json -->
<!-- payload-sha256: fd74d224ecffb7dfa206f0ee2734e0501f6643f42c7796d6c8ef899164adcb33 -->
<!-- payload-bytes: 4465 -->

<!-- payload-begin -->
````json
[
  {
    "id": "A01",
    "claim": "附件56—82：检索候选最多65536远端tokens",
    "verdict": "VERIFIED",
    "sources": "T06",
    "resolution": "保留判断；这是候选覆盖上限，不是drafter总窗口，也不是所有上下文硬上限。",
    "owner_task": "P11-T02"
  },
  {
    "id": "A02",
    "claim": "附件84—109：完整DraftKV256K约5GiB",
    "verdict": "CONDITIONAL_GEOMETRY",
    "sources": "T03/T04/T08",
    "resolution": "20KiB/token算例成立，但实际layer/head/stride以模型manifest与显存测量为准，文件大小不等于设备大小。",
    "owner_task": "P7-T04"
  },
  {
    "id": "A03",
    "claim": "附件111—129：检索关闭部分CUDA Graph/batchfast path",
    "verdict": "VERIFIED",
    "sources": "T03/T05",
    "resolution": "限定常规draft快速路径，不声称所有Target graph同时关闭。",
    "owner_task": "P11-T04"
  },
  {
    "id": "A04",
    "claim": "附件175—185：全局页索引保持查询常数",
    "verdict": "CORRECTION",
    "sources": "T06/R01",
    "resolution": "GPU工作集可有界；主机archive仍O(N)，扫描页摘要O(N/page)，不能宣称整个算法O(1)。",
    "owner_task": "P11-T02"
  },
  {
    "id": "A05",
    "claim": "附件222：直接从NInfer L2调入远端DraftKV",
    "verdict": "CORRECTION",
    "sources": "T04/N04",
    "resolution": "L2 Target状态没有所需Draft投影；建立独立有界DraftArchive，复用传输设施而非强转payload。",
    "owner_task": "P11-T01"
  },
  {
    "id": "A06",
    "claim": "附件240：随机采样只需真实draftq",
    "verdict": "QUALIFY",
    "sources": "T07/N05",
    "resolution": "ratio方法需要条件q和residual；lattice分数不是q。先greedy，采样走原合格后端；target-sample-match是独立后续方案。",
    "owner_task": "P8-T01"
  },
  {
    "id": "A07",
    "claim": "附件313—317：K4/5适配5/6列验证",
    "verdict": "PARTLY_VERIFIED",
    "sources": "N01/N07",
    "resolution": "Attention列数相容；还须核对整个schedule、GDN、projection、graph及sampling契约。",
    "owner_task": "P8-T02"
  },
  {
    "id": "A08",
    "claim": "附件363—367：现有27B直接对比MTP和DFlash2",
    "verdict": "CORRECTION",
    "sources": "N01/N03",
    "resolution": "27B没有DFlash2产品路径；P10是前置，不能把它放进尚未实现的P8基准。",
    "owner_task": "P10-T01"
  },
  {
    "id": "A09",
    "claim": "附件动态MTP/DFlash切换",
    "verdict": "NEW_DESIGN_NOT_DONOR_FEATURE",
    "sources": "T08/N06",
    "resolution": "tqLLM mtp-from是prompt阈值；NInfer新增能力掩码/校准策略，先请求边界选择。",
    "owner_task": "P8-T01"
  },
  {
    "id": "A10",
    "claim": "附件340—346：accepted_per_round用于有效吞吐",
    "verdict": "CORRECTION",
    "sources": "N05",
    "resolution": "用实际committed，包括修正/bonus，分母用关键路径wall time；重叠阶段不求和。",
    "owner_task": "P7-T03"
  },
  {
    "id": "A11",
    "claim": "附件419：保留262KE8KV",
    "verdict": "SUPERSEDED_BASELINE",
    "sources": "原包P4",
    "resolution": "基于上游整合后的rk4v4；不可把旧E8别名/缓存读回。",
    "owner_task": "P7-T01"
  },
  {
    "id": "A12",
    "claim": "附件社区长上下文倍数",
    "verdict": "UNVERIFIED_AS_CONTROLLED_AB",
    "sources": "用户附件",
    "resolution": "附件有异上下文3090比较和第三方运行；未取得其完整配置/原日志，不用于本机收益承诺。",
    "owner_task": "P7-T02"
  },
  {
    "id": "A13",
    "claim": "DFlash2 draft-max降低必然减少draft计算",
    "verdict": "NEW_CAUTION",
    "sources": "T05/T08",
    "resolution": "物理block B取训练配置，want可能只截断返回候选；分别记录physicaldraftrows与verifywidth。",
    "owner_task": "P10-T06"
  },
  {
    "id": "A14",
    "claim": "Largecontext参数即长上下文测试通过",
    "verdict": "CORRECTION",
    "sources": "T09/T10",
    "resolution": "现有exactfixture截12000字符，retrievalfixture pos6000；新增真实128K/248K输入。",
    "owner_task": "P12-T02"
  },
  {
    "id": "A15",
    "claim": "NInfer源码kNativeContext=1M意味着4090可服务1M",
    "verdict": "UNSUPPORTED_INFERENCE",
    "sources": "N01",
    "resolution": "源码上限不等于已测容量；本轮仍冻结262144pool与输出余量。",
    "owner_task": "P7-T04"
  }
]
````
<!-- payload-end -->

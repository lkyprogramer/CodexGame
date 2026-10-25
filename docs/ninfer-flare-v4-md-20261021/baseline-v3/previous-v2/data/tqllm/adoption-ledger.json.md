# V2 支撑材料：`data/tqllm/adoption-ledger.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: data/tqllm/adoption-ledger.json -->
<!-- payload-sha256: c0c5a2fc69550b7d2a66915ad853ec423f76861c8e74dd5fe094aaeb626bb98e -->
<!-- payload-bytes: 3773 -->

<!-- payload-begin -->
````json
[
  {
    "id": "F01",
    "feature": "MTP宽度及后端选择",
    "decision": "原生实现",
    "sources": "T08",
    "ninfer_context": "已有MTPmax5；无请求级auto",
    "phase": "P8",
    "risk": "低—中",
    "guard": "不改变Target；常驻能力集合，请求边界选择"
  },
  {
    "id": "F02",
    "feature": "Prompt Lookup链式提案",
    "decision": "原生实现",
    "sources": "T08",
    "ninfer_context": "共享TargetVerifyFrameView",
    "phase": "P8",
    "risk": "中",
    "guard": "只提案不直接提交；最长匹配及坏命中回退"
  },
  {
    "id": "F03",
    "feature": "同一attention算术与exactness tests",
    "decision": "吸收验证方法",
    "sources": "T02/T09",
    "ninfer_context": "已有强数值/ReplaySSM约束",
    "phase": "P9",
    "risk": "中",
    "guard": "跨width/codec/graph定位首个分叉，不用宽松最终文字判据代替"
  },
  {
    "id": "F04",
    "feature": "DFlash2 grouped conv和lattice",
    "decision": "语义移植/审查后局部代码改写",
    "sources": "T03/T07",
    "ninfer_context": "35B DFlash机制可参考，27B需要新绑定",
    "phase": "P10",
    "risk": "高",
    "guard": "新增companion artifact；单链greedy先行"
  },
  {
    "id": "F05",
    "feature": "64K draft词表与低比特草稿权重",
    "decision": "消融实验",
    "sources": "T01/T03",
    "ninfer_context": "已有131072优化proposalhead",
    "phase": "P10",
    "risk": "中—高",
    "guard": "仅draft近似，Target完整词表；量化来自原始checkpoint单次转换"
  },
  {
    "id": "F06",
    "feature": "全局SelectiveDraftKV",
    "decision": "新设计",
    "sources": "T04/T06/R02",
    "ninfer_context": "TargetL2不能提供Draftfeatures",
    "phase": "P11",
    "risk": "高",
    "guard": "独立archive/位置策略/有界工作集；缺状态不隐藏全量重算"
  },
  {
    "id": "F07",
    "feature": "fixedring与device-resident graph",
    "decision": "原生适配",
    "sources": "T04/T05",
    "ninfer_context": "NInfer图与workspace既有规则",
    "phase": "P10/P11",
    "risk": "高",
    "guard": "CPU刷新在图外；固定指针与slot/epoch fencing"
  },
  {
    "id": "F08",
    "feature": "Token tree",
    "decision": "延后",
    "sources": "T02/T07",
    "ninfer_context": "GDN每分支状态及完整accept契约需改",
    "phase": "后续",
    "risk": "高",
    "guard": "链式有效且树增益超过额外复杂度后独立立项"
  },
  {
    "id": "F09",
    "feature": "TQ3/TQ4 Target与TCQ KV",
    "decision": "不纳入主线",
    "sources": "T01/T08",
    "ninfer_context": "破坏同Target/codec基线",
    "phase": "后续",
    "risk": "高",
    "guard": "独立转换/质量项目，不为给drafter腾空间静默替换"
  },
  {
    "id": "F10",
    "feature": "Target hostKV/自动缩ctx/自动降KV精度",
    "decision": "不采用",
    "sources": "T08",
    "ninfer_context": "本轮目标是既定24GB长上下文性能",
    "phase": "本轮拒绝",
    "risk": "高",
    "guard": "容量不足必须NO_GO，不能悄悄降级为另一产品"
  },
  {
    "id": "F11",
    "feature": "FP8/INT8 prefill",
    "decision": "不重复开发",
    "sources": "T08/N07",
    "ninfer_context": "上游已有A8 prefill；decision要求A16",
    "phase": "按profile另案",
    "risk": "中",
    "guard": "只测实际新瓶颈；不泛化声称FP8更快"
  },
  {
    "id": "F12",
    "feature": "稀疏Target Verify",
    "decision": "不纳入精确主线",
    "sources": "R03",
    "ninfer_context": "需要维持完整Target验证",
    "phase": "后续",
    "risk": "高",
    "guard": "必须证明排除项不影响accept或精确回退，否则是近似模式"
  }
]
````
<!-- payload-end -->

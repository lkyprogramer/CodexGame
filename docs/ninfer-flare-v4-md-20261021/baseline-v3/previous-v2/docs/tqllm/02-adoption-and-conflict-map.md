> V2 参考快照：P7—P12 不再是执行权威；按根目录 `plans/00-master-plan.md` 和 `plans/01-v2-migration-map.md` 执行。本文保留历史设计与来源，不表示实现完成。

# 借鉴清单与融合冲突

| 编号 | 能力 | 处理 | 来源 | NInfer现状 | 阶段 | 风险 | 约束 |
|---|---|---|---|---|---|---|---|
| F01 | MTP宽度及后端选择 | 原生实现 | T08 | 已有MTPmax5；无请求级auto | P8 | 低—中 | 不改变Target；常驻能力集合，请求边界选择 |
| F02 | Prompt Lookup链式提案 | 原生实现 | T08 | 共享TargetVerifyFrameView | P8 | 中 | 只提案不直接提交；最长匹配及坏命中回退 |
| F03 | 同一attention算术与exactness tests | 吸收验证方法 | T02/T09 | 已有强数值/ReplaySSM约束 | P9 | 中 | 跨width/codec/graph定位首个分叉，不用宽松最终文字判据代替 |
| F04 | DFlash2 grouped conv和lattice | 语义移植/审查后局部代码改写 | T03/T07 | 35B DFlash机制可参考，27B需要新绑定 | P10 | 高 | 新增companion artifact；单链greedy先行 |
| F05 | 64K draft词表与低比特草稿权重 | 消融实验 | T01/T03 | 已有131072优化proposalhead | P10 | 中—高 | 仅draft近似，Target完整词表；量化来自原始checkpoint单次转换 |
| F06 | 全局SelectiveDraftKV | 新设计 | T04/T06/R02 | TargetL2不能提供Draftfeatures | P11 | 高 | 独立archive/位置策略/有界工作集；缺状态不隐藏全量重算 |
| F07 | fixedring与device-resident graph | 原生适配 | T04/T05 | NInfer图与workspace既有规则 | P10/P11 | 高 | CPU刷新在图外；固定指针与slot/epoch fencing |
| F08 | Token tree | 延后 | T02/T07 | GDN每分支状态及完整accept契约需改 | 后续 | 高 | 链式有效且树增益超过额外复杂度后独立立项 |
| F09 | TQ3/TQ4 Target与TCQ KV | 不纳入主线 | T01/T08 | 破坏同Target/codec基线 | 后续 | 高 | 独立转换/质量项目，不为给drafter腾空间静默替换 |
| F10 | Target hostKV/自动缩ctx/自动降KV精度 | 不采用 | T08 | 本轮目标是既定24GB长上下文性能 | 本轮拒绝 | 高 | 容量不足必须NO_GO，不能悄悄降级为另一产品 |
| F11 | FP8/INT8 prefill | 不重复开发 | T08/N07 | 上游已有A8 prefill；decision要求A16 | 按profile另案 | 中 | 只测实际新瓶颈；不泛化声称FP8更快 |
| F12 | 稀疏Target Verify | 不纳入精确主线 | R03 | 需要维持完整Target验证 | 后续 | 高 | 必须证明排除项不影响accept或精确回退，否则是近似模式 |


## 不是Git分支合并

tqLLM与NInfer是不同引擎。不得执行`merge --allow-unrelated-histories`或把tqLLM整体vendoring成第二个服务进程。保留参考T checkout只读；复制代码先登记来源、函数、许可证及改写，纯思想实现同样标注设计来源。[T02/T11/N09]

## 冲突落点与唯一所有者

| NInfer边界 | 主要风险 | 决定 |
|---|---|---|
| `include/ninfer/types.h` / `runtime.h` / `decoder_state.h` | startup backend与新request policy冲突 | P8-T01冻结能力/plan；Integrator唯一落盘；P10新增DFlash2不得把DFlash原枚举改义 |
| `schedule.h` / target_verify_accept / `program_impl.h` | 新backend各自accept导致状态分叉 | 单一TargetVerifyFrameView，所有提案走共同许可/ReplaySSM提交 |
| `workspace_recipe.h` / layouts / graph profiles | ring、workspace、graphs显存未入账，指针热换 | startup明确容量；graph key含物理shape和资源代号，不按prompt内容无限膨胀 |
| `continuation_image.h` / cache identity | Draft缺失被误认为Target状态失效，或跨适配器复用 | Target缓存仍独立有效；Draft sidecar匹配失败只禁用该draft路由，不能强转旧缓存 |
| B0 / tokenizer /模板 / 日志扩展 | 引入GGUF tokenizer或改模板使模型对比失真 | 原路径不替换；保留prepare_detail，新增`extensions.spec_perf_v1` |
| GDN记录/输出parser | 丢弃草稿/取消后推进隐藏状态或输出token | pending→licensed→commit唯一顺序；只有已提交token可进入parser和工具流 |
| CMake / AGENTS /CLI | 并行worker覆盖、过早公开开关 | Integrator串行；新选项明确experimental，未资格资产不可成为默认 |

上述是语义接入冲突，不是已经运行出的文本merge冲突列表。P7重查实际P6集成树的符号/布局，再将新路径锁表提交。

# 12 需求追踪与交付边界

| 用户目标 / 必要正确性 | 对应Task与统一Gate |
|---|---|
| 继续现有ninfer-4090而非换引擎 | P0-T01、P1-T01、P4-T02、P8-T01 |
| 完整Phase与Task计划 | phases/P0.md至P8.md；manifests/plan.json |
| 每Phase改完后统一验证 | 每阶段Pn-G；05、11及PHASE-GATE prompt |
| 先48/16，再有条件40/24和32/32 | P4、P6、P7A/P7B |
| Teacher state injection | P1-T02/T03/T05，P1-G；MTP扩展P5-T01 |
| StateOnly GDN | P2-T01/T02/T05，P2-G |
| 完整conv history与K/V写入 | P2-T03、P4-T02/T03 |
| 24GB能训练和运行 | P0-T05、P2-T04、P3-T01/T02/T03 |
| MTP可正确续接 | P5-T01/T02/T05，P5-G |
| 不污染native continuation | P5-T03/T04，P5-G |
| 精确尾部与首token | P4-T03/T04；03状态合同 |
| 大输入/小append/改根prompt | P0-T04、P5-T04、P6-T01/T03 |
| Java与Pi真实任务 | P6-T02/T03，P6-G |
| 质量不是只看PPL/NIAH | P4-T04、P6-T04/T05，06统计合同 |
| 不改/不误停生产 | P0-T01/T02、P8-T02 |
| Gate未过不能盲目前进 | 05、09、10、START提示词、run_phase合同 |
| 可下载文档集合 | 当前ZIP；00入口、prompts、configs、templates、工具校验 |

## 当前文档包已经做与没有做的事

已经做：读取公开源码及用户部署记录，冻结设计基线，定义完整状态/数据/资源/验收合同，生成同源Phase/Task/DAG文档，提供计划导航与预算工具，并对文档包做结构与工具测试。

没有做：连接用户GPU、停止现网、修改NInfer源码、构建CUDA二进制、运行真实推理、生成Teacher训练集、训练Predictor、验证提速或Agent质量。文档中所有Phase初始状态为NOT_RUN。

任务执行后新产生的实验结果必须进入独立runs目录，不能覆盖本包的“计划校验”报告并改称GPU验证。

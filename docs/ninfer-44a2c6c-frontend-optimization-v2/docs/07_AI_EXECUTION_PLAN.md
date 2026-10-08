# 07 · AI 分阶段执行计划

**Goal：** 用B0+B1修复固定NInfer的两层重复编码，保持前端输出/错误合同，交付可审计的生产验证。  
**Architecture：** 只读Tokenizer索引 + 请求内主编码trace + 请求内局部边界验证，无跨请求可变缓存。  
**Tech stack：** 原C++20/CUDA工程、现有unicode与JSON依赖；Python3仅作离线数据/报告工具。  
**Spec：** [02](02_DESIGN_AND_ADRS.md)、[03](03_BOUNDARY_CORRECTNESS_SPEC.md)、[04](04_B0_SCANNER_AND_B1_ALGORITHM.md)。

## 7.1 全局约束

保持44a2c6c基线和诊断overlay可追溯；资源来自实际artifact；不改权重/窗口/采样/KV/模板；不删hint；零semantic/error差异；产品只保留一条优化路径；不生产shadow；所有缺失资源与未授权维护如实BLOCKED。

## 7.2 Review Focus

真正有共同起点的前缀token冲突；Tokenizer copy后原对象销毁；UTF-8切在多字节中间/NFC跨切点；同一offset不同allow_full与name；乱序或重复hint；主编码与边界同时非法时先报哪一个。六类分别由T03/T04/T05/T06/T09承担，不可只测标准chat。

## 7.3 顺序与交付

| 任务 | 可独立审查的交付 | 前置 |
|---|---|---|
|[T00](../tasks/T00.md)|基线/overlay/资源/权限证据|无|
|[T01](../tasks/T01.md)|真实H/Q与扫描工作计数定义|T00|
|[T02](../tasks/T02.md)|完整独立legacy oracle与归一化格式|T00|
|[T03](../tasks/T03.md)|B0搜索等价与结构性工作量下降|T01,T02|
|[T04](../tasks/T04.md)|可选trace与生命周期合同|T03|
|[T05](../tasks/T05.md)|B1局部边界验证接入shared encoder|T04|
|[T06](../tasks/T06.md)|有限全cut/20k随机/错误差分报告|T05,T02|
|[T07](../tasks/T07.md)|H5/H20生产形态、CPU/HTTP校准分离|T02|
|[T08](../tasks/T08.md)|CPU绝对/相对/结构门|T06,T07|
|[T09](../tasks/T09.md)|原CTest与count/vision/prepare_tokens回归|T06|
|[T10](../tasks/T10.md)|候选不可变镜像与保护证明|T08,T09|
|[T11](../tasks/T11.md)|授权维护窗口HTTP对照|T10|
|[T13](../tasks/T13.md)|独立review与发布裁决|T11|
|[T12](../tasks/T12.md)|授权发布、观察与回滚演练|T13|

T07数据准备可与T03–T06并行，但不能运行多个重CPU基准污染性能。T13虽然编号在后，必须在T12生产部署之前完成。

## 7.4 每张卡必须执行的循环

- [ ] 读取本卡spec/输入合同，核对依赖证据，不靠聊天回忆。
- [ ] 先写特定失败断言；性能重构先红结构门，旧语义测试可维持绿色。
- [ ] 执行并保留正确原因的失败日志。
- [ ] 最小修改、再跑相同测试；禁止混入其它优化。
- [ ] 执行本卡边界/错误回归，保存commit及资源hash。
- [ ] reviewer检查diff、测试独立性、统计和停止条件，再交下一任务。

本包不强制特定外部agent框架。使用子agent时任务边界可分离；同一源码文件改动必须串行整合，不能并发修改tokenizer/processor后跳过整体复验。

## 7.5 旧任务映射

v1 T00–T02保留基线/统计/oracle；T03扩大为B0；T04/T05保留trace/B1但职责明确；旧T06–T08跨请求cache移至deferred，本版同编号用于差分/数据/性能。旧shadow/canary步骤全部删除。T11保留维护验证，T12简化为镜像发布/回滚，T13审查提前到发布前。

## 7.6 停止而不是扩写方案

若B0+B1已满足CPU≤1s及HTTP gate，结束首期，不为“更极致”立即实现B2。若CPU门不达标，先拆B0 scan/main BPE/localbytes/allocator；若HTTP依旧慢而tokenize已低，按residual查真正瓶颈，不继续优化tokenizer。若发现full_reset，转独立项目，不调整本期验收输入掩盖问题。

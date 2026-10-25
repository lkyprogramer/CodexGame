# V2 支撑材料：`plans/tasks.csv`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: plans/tasks.csv -->
<!-- payload-sha256: 1979051807105ee50032d875d59174b3eec40efcf9fb4bebcc698c6960e3438e -->
<!-- payload-bytes: 9515 -->

<!-- payload-begin -->
````csv
﻿id,phase,kind,title,owner,depends_on,status
P0-T01,P0,task,冻结完整源码与实际合并冲突,Integrator,[],PENDING
P0-T02,P0,task,核对生产三件套、代理配置与显存账本,Deployment,[],PENDING
P0-T03,P0,task,冻结真实资源、旧 oracle 和 G1 素材,Frontend QA,"[""P0-T01""]",PENDING
P0-T04,P0,task,建立 PROD/O 配对基线与冻结质量门槛,Performance QA,"[""P0-T02"", ""P0-T03""]",PENDING
P1-T01,P1,task,串行合入上游里程碑（U01—U10）,Integrator,"[""P0-GATE""]",PENDING
P1-T02,P1,task,统一 B0 扫描、分段前缀与 B1 memo,Frontend implementation,"[""P1-T01""]",PENDING
P1-T03,P1,task,隔离 legacy DTO 并建立独立差分 oracle,Frontend QA,"[""P1-T01""]",PENDING
P1-T04,P1,task,恢复 prepare_detail 与三协议请求体观测,Serving observability,"[""P1-T01""]",PENDING
P1-T05,P1,task,验证 typed alias 与新缓存边界语义,Cache implementation,"[""P1-T01""]",PENDING
P1-T06,P1,task,验证 repetition guard、轮级故障与进度事件,Runtime QA,"[""P1-T01""]",PENDING
P2-T01,P2,task,串行合入上游里程碑（U11）,Integrator,"[""P1-GATE""]",PENDING
P2-T02,P2,task,补齐异步 export 的 fence 与生命周期回归,Runtime implementation,"[""P2-T01""]",PENDING
P2-T03,P2,task,对齐异步阶段耗时和导出指标,Observability QA,"[""P2-T01""]",PENDING
P2-T04,P2,task,实机混合热冷流量与导出压力验收,GPU QA,"[""P2-T02"", ""P2-T03""]",PENDING
P3-T01,P3,task,串行合入上游里程碑（U12—U17）,Integrator,"[""P2-GATE""]",PENDING
P3-T02,P3,task,整体验证 small-T MMA 与算子路由,CUDA implementation,"[""P3-T01""]",PENDING
P3-T03,P3,task,贯通三协议增量工具调用与历史存储,Serving implementation,"[""P3-T01""]",PENDING
P3-T04,P3,task,固定测试注册与 skip77 策略,Build QA,"[""P3-T01""]",PENDING
P3-T05,P3,task,验证 small-T 与工具流的端到端收益,Performance QA,"[""P3-T02"", ""P3-T03"", ""P3-T04""]",PENDING
P4-T01,P4,task,串行合入上游里程碑（U18—U27）,Integrator,"[""P3-GATE""]",PENDING
P4-T02,P4,task,迁移 KV codec、序列化版本与缓存隔离,CUDA / cache implementation,"[""P4-T01""]",PENDING
P4-T03,P4,task,整合决策 runtime、LoRA 和分支隔离,Decision implementation,"[""P4-T01""]",PENDING
P4-T04,P4,task,迁移 schema22、无饥饿遥测和双系统观测,Telemetry implementation,"[""P4-T01""]",PENDING
P4-T05,P4,task,隔离输出 UTF-8 修复与输入严格校验,Frontend output QA,"[""P4-T01""]",PENDING
P4-T06,P4,task,4090 上验证新 KV 质量、容量与性能,GPU qualification,"[""P4-T02"", ""P4-T03"", ""P4-T04"", ""P4-T05""]",PENDING
P5-T01,P5,task,串行合入上游里程碑（U28—U34）,Integrator,"[""P4-GATE""]",PENDING
P5-T02,P5,task,验证双决策协议、模型发现与错误契约,Protocol implementation,"[""P5-T01""]",PENDING
P5-T03,P5,task,合入图像预处理身份、MRoPE 与媒体容量,Vision implementation,"[""P5-T01""]",PENDING
P5-T04,P5,task,验收 playground 与历史日志显示,Web QA,"[""P5-T01""]",PENDING
P5-T05,P5,task,统一验收最终 API 与多模态状态,Integration QA,"[""P5-T02"", ""P5-T03"", ""P5-T04""]",PENDING
P6-T01,P6,task,完成全量 ancestry 与定制保留审查,Integrator / independent reviewer,"[""P5-GATE""]",PENDING
P6-T02,P6,task,最终 128K—248K Java Agent 配对验收,Performance / quality QA,"[""P6-T01""]",PENDING
P6-T03,P6,task,构建不可变镜像并演练启动与排空,Deployment,"[""P6-T01""]",PENDING
P6-T04,P6,task,在批准窗口执行生产试运行,Deployment / user approval,"[""P6-T02"", ""P6-T03""]",PENDING
P6-T05,P6,task,实际回滚演练与最终交付,Deployment / final reviewer,"[""P6-T04""]",PENDING
P0-GATE,P0,gate,统一代码 review 与集成测试门禁,Independent reviewer + Integrator,"[""P0-T01"", ""P0-T02"", ""P0-T03"", ""P0-T04""]",PENDING
P1-GATE,P1,gate,统一代码 review 与集成测试门禁,Independent reviewer + Integrator,"[""P1-T01"", ""P1-T02"", ""P1-T03"", ""P1-T04"", ""P1-T05"", ""P1-T06""]",PENDING
P2-GATE,P2,gate,统一代码 review 与集成测试门禁,Independent reviewer + Integrator,"[""P2-T01"", ""P2-T02"", ""P2-T03"", ""P2-T04""]",PENDING
P3-GATE,P3,gate,统一代码 review 与集成测试门禁,Independent reviewer + Integrator,"[""P3-T01"", ""P3-T02"", ""P3-T03"", ""P3-T04"", ""P3-T05""]",PENDING
P4-GATE,P4,gate,统一代码 review 与集成测试门禁,Independent reviewer + Integrator,"[""P4-T01"", ""P4-T02"", ""P4-T03"", ""P4-T04"", ""P4-T05"", ""P4-T06""]",PENDING
P5-GATE,P5,gate,统一代码 review 与集成测试门禁,Independent reviewer + Integrator,"[""P5-T01"", ""P5-T02"", ""P5-T03"", ""P5-T04"", ""P5-T05""]",PENDING
P6-GATE,P6,gate,统一代码 review 与集成测试门禁,Independent reviewer + Integrator,"[""P6-T01"", ""P6-T02"", ""P6-T03"", ""P6-T04"", ""P6-T05""]",PENDING
P7-T01,P7,task,冻结P6基线、tqLLM来源与drafter资产契约,Integrator + Artifact owner,"[""P6-GATE""]",PENDING
P7-T02,P7,task,冻结实际长上下文与Java业务A/B语料,Evaluation owner,"[""P6-GATE""]",PENDING
P7-T03,P7,task,增加采样式GPU阶段观测和稳定日志扩展,Telemetry owner,"[""P7-T01""]",PENDING
P7-T04,P7,task,建立实测资源账本和阶段采用门槛,Performance + Runtime owner,"[""P7-T01"", ""P7-T02"", ""P7-T03""]",PENDING
P8-T01,P8,task,冻结策略、能力集合与新backend枚举,Integrator,"[""P7-GATE""]",PENDING
P8-T02,P8,task,MTP3/4/5完整shape与状态资格,Runtime worker,"[""P8-T01""]",PENDING
P8-T03,P8,task,实现有界Prompt Lookup提案索引,CPU worker,"[""P8-T01""]",PENDING
P8-T04,P8,task,外部提案共同验收与同构batch集成,Integrator,"[""P8-T02"", ""P8-T03""]",PENDING
P8-T05,P8,task,低成本策略整体验证和E1候选,Evaluation owner,"[""P8-T04""]",PENDING
P9-T01,P9,task,固定完整验证数值oracle与优化点,Numerics worker,"[""P8-GATE""]",PENDING
P9-T02,P9,task,优化选定full-KV kernel或保持现状,CUDA worker,"[""P9-T01""]",PENDING
P9-T03,P9,task,冻结verify图包络和资源生命周期,Runtime worker,"[""P9-T02""]",PENDING
P9-T04,P9,task,完整验证优化的长上下文资格,Evaluation owner,"[""P9-T03""]",PENDING
P10-T01,P10,task,实现离线companion转换、typed绑定与只读模型view,Artifact owner + Integrator,"[""P9-GATE""]",PENDING
P10-T02,P10,task,建立独立DFlash2逐层reference和固定golden,Numerical reference worker,"[""P10-T01""]",PENDING
P10-T03,P10,task,实现DFlash2 dynamic-conv、selector和chain算子,CUDA worker,"[""P10-T01""]",PENDING
P10-T04,P10,task,feature捕获、ring、workspace与事务状态,Runtime worker,"[""P10-T01""]",PENDING
P10-T05,P10,task,DFlash2单链进入共同验证、采样路由与故障边界,Integrator,"[""P10-T02"", ""P10-T03"", ""P10-T04""]",PENDING
P10-T06,P10,task,固定ring图、草稿词表与head内存消融,Performance worker,"[""P10-T05""]",PENDING
P10-T07,P10,task,固定ring DFlash2全量资格与24GB止损,Evaluation + Runtime owner,"[""P10-T06""]",PENDING
P11-T01,P11,task,独立ProjectedG host archive和版本化identity,Archive worker,"[""P10-GATE""]",PENDING
P11-T02,P11,task,全局页代表索引与两级CPU oracle,Index worker,"[""P10-GATE""]",PENDING
P11-T03,P11,task,GPU coarse/refine选择、按headstage与Draft位置映射,CUDA worker,"[""P11-T01"", ""P11-T02""]",PENDING
P11-T04,P11,task,图外异步刷新、双stage和迟到任务隔离,Runtime worker,"[""P11-T03""]",PENDING
P11-T05,P11,task,连接continuation、重写、slot与adapter生命周期,Integrator,"[""P11-T01"", ""P11-T04""]",PENDING
P11-T06,P11,task,检索成本进入后端策略与观测,Telemetry + Policy worker,"[""P11-T05""]",PENDING
P11-T07,P11,task,全局检索128K/248K远端依赖与端到端资格,Evaluation owner,"[""P11-T06""]",PENDING
P12-T01,P12,task,最终来源、架构与原定制保留审查,Independent reviewer + Integrator,"[""P11-GATE""]",PENDING
P12-T02,P12,task,最终组合版本完整数值、业务与性能验收,Evaluation owner,"[""P12-T01""]",PENDING
P12-T03,P12,task,生成只读artifact与部署ready profile,Deployment owner,"[""P12-T01""]",PENDING
P12-T04,P12,task,获授权后的单卡试运行及实际回滚演练,Deployment + Evaluation owner,"[""P12-T02"", ""P12-T03""]",PENDING
P12-T05,P12,task,封版、机器门禁与开发/生产资格分离,Integrator,"[""P12-T04""]",PENDING
P7-GATE,P7,gate,统一代码review、完整集成测试与资源/性能门禁,Independent reviewer + Integrator,"[""P7-T01"", ""P7-T02"", ""P7-T03"", ""P7-T04""]",PENDING
P8-GATE,P8,gate,统一代码review、完整集成测试与资源/性能门禁,Independent reviewer + Integrator,"[""P8-T01"", ""P8-T02"", ""P8-T03"", ""P8-T04"", ""P8-T05""]",PENDING
P9-GATE,P9,gate,统一代码review、完整集成测试与资源/性能门禁,Independent reviewer + Integrator,"[""P9-T01"", ""P9-T02"", ""P9-T03"", ""P9-T04""]",PENDING
P10-GATE,P10,gate,统一代码review、完整集成测试与资源/性能门禁,Independent reviewer + Integrator,"[""P10-T01"", ""P10-T02"", ""P10-T03"", ""P10-T04"", ""P10-T05"", ""P10-T06"", ""P10-T07""]",PENDING
P11-GATE,P11,gate,统一代码review、完整集成测试与资源/性能门禁,Independent reviewer + Integrator,"[""P11-T01"", ""P11-T02"", ""P11-T03"", ""P11-T04"", ""P11-T05"", ""P11-T06"", ""P11-T07""]",PENDING
P12-GATE,P12,gate,统一代码review、完整集成测试与资源/性能门禁,Independent reviewer + Integrator,"[""P12-T01"", ""P12-T02"", ""P12-T03"", ""P12-T04"", ""P12-T05""]",PENDING
````
<!-- payload-end -->

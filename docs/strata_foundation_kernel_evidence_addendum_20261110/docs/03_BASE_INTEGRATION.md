# 03 · 与 2026-11-06 基础包的接入与去重

## 1. 已实际核对原包

原文件名：strata_observability_specpilot_foundation_20261106.zip  
大小：162748 bytes  
SHA256：0a08667d8fc03d91e1b961a9e705f4649b357e65f25e285db847c390c2c99934

本次读取了原README、AGENTS、身份/历史、事件、完成归因、观察器资格、SpecPilot控制器、测试协议、已有工具绑定、总计划与来源锁。原包是设计/实施计划，不是已装好的监控插件；不能因本次找到文件就宣称O0–O6已完成。

## 2. 非破坏式放置

推荐先与原包并列解压，保留原ZIP和旧MANIFEST不动。需要纳入一个文档树时，把本目录整体放到原包的 addenda/ 下；本包内部链接不依赖外部路径。原文档只需以后在新的文档修订版增加“增补阅读入口”，不要直接覆盖旧证据文件或伪造其旧hash。

如以后生成合并版，另取新版本名和hash，保留本表的parent hash与独立增补manifest；合并版不得继续冒用原ZIP名字/校验和。本次交付的是增补ZIP，不是声称已修改原ZIP。

## 3. 精确接入位置

| 原包位置 | 原有职责 | 新增阅读/接口 | 如何去重 |
|---|---|---|---|
| docs/01_SCOPE_AND_BASELINE.md；O0 | 来源、部署身份、冻结合同 | 本包04章 artifact链与最新源码锁 | 不重建身份系统；source与deployed分开 |
| docs/02_UPSTREAM_MONITORING.md；O0 | 监控现状 | 本章4节更新清单 | 只补核查到的增量 |
| docs/05_EVENT_CONTRACT.md；O1/O3 | request/round/graph/clock关联 | kernel-evidence/v1 引用已有scope | 不新增第二套事件总线/ID |
| docs/06_COMPLETION_ATTRIBUTION.md；O1 | L0–L4、DAG与反事实 | kernel_floor/counter作为附件 | 不改DAG算法或把并集当暴露成本 |
| docs/09_CUDA_BACKENDS_AND_HES.md；O3 | CUDA采集/架构边界 | 05章codegen/counter/replay规则 | HES unsupported保持 |
| docs/10_OBSERVER_QUALIFICATION.md；O4 | observer资格 | 验证profile改图、默认flag与计数器扰动 | 1%/3%观测门保持；NCU默认诊断 |
| docs/11_SPECPILOT_CONTROLLER.md；O5 | 唯一控制器、token forcing理念 | 06章接现有force_check并守卫输入 | 不重做checker/控制器 |
| docs/12_TEST_PROTOCOL.md；O6 | 分层测试与正式统计 | 08章新增负例 | 旧六对/4%/不补样不变 |
| docs/16_EXISTING_TOOL_BINDINGS.md | lab已有工具 | 05章spill/microbench，07章oracle | 不复制runner/scorer/allocator |

本包 E0–E4 是原阶段的增量子任务链，不取代 O0–O6。只有文档存在时，不假定原模块已实现；若现场已经实现，审真实diff后仅做缺口。

## 4. 2026-11-10 上游源码变化/发现

审计基线：[Strata 504b1433](https://github.com/Niko1221/Strata/tree/504b143342a9fe1aa8320a7b31e11f5c0ac265c3)。

| 能力 | 代码事实 | 增补要求 |
|---|---|---|
| tools/force_check.py | 旧9f7d977d树无此文件；2026-11-06 09:35:53Z加入，随后加入decode强制路径 | 更新旧“未有checker”表述；存在不等于资格 |
| tools/check_cuda_spills.py | 已有静态REG/STACK/LOCAL/SHARED检查 | 复用；增加SM89与加载产物绑定，不复制脚本 |
| dispatch_stats.hpp | 按path/type/shape聚合，区分capture scope和graph launch计数；默认启用 | 不能把capture次数当每次执行计数；保留既有开关 |
| run_manifest.hpp | STRATA_MANIFEST指定路径才开启；有预算/路径/张量格式；不带时间戳/PID/内容hash | 外层补不可变运行身份，不修改其既有语义 |
| Verifier profiler | PROFILE按环境变量存在判断；可禁用fork/fusion | DIAGNOSTIC_ONLY，图变化时不能代表生产路径 |
| 微基准 | mmvq_il_parity、native_expert_bench、pa_bench等已有 | 只做选择与封装；随机张量/路由回放不等于真实张量回放 |

来源细节在[来源目录](../sources/SOURCES.md)。这里“已有”是SOURCE_INSPECTED，不是本轮目标机LIVE_MEASURED。

## 5. 历史决定继承表

| 范围 | 保留状态 | 本增补不能做什么 |
|---|---|---|
| F02 GU/TG21 | DEFERRED_NEW_EVIDENCE | 以PTX/SASS审计名义重新搜索旧kernel |
| F01 selected-KV、F03 scratch | 原关闭保持 | 借分页/生命周期教材重做cache或pool |
| P01/P01B | 窄host-gap问题已按原范围关闭 | 重跑原采集、把内部UNKNOWN泛化为新预算 |
| P24 HC、NP3、SPEC/SPECCOST | 原失败/关闭保持 | 新donor改名续测 |
| DFlash2 v0.2.10 | 用户后续报告：服务PASS，采用条件未满足；KEEP_MTP_SPEC4 | 写成尚未测试、自动再次比较 |
| P05、六项长检索 | 旧BLOCKED/FAIL保持 | 数值或监控PASS覆盖任务质量失败 |

旧GU家族6.8911%/6.5884%，最大TG21为2.2188%/2.1287%，均为旧profile条件成本，不是当前真实warm暴露时间。原包已正确记录，增补不改。

DFlash2后续结果来自原包标明的USER_REPORTED摘要，未在本轮取得raw；固定lab分支中的V0210-PT0版本对比两臂都是MTP4，不能误引用为DFlash2复验。

## 6. 不会直接带来的东西

不保证增加tok/s；不自动升级生产Strata；不自动获准任何GPU实验。只有原始路径证据、数值/状态门与独立任务结果均成立时，才允许另立新优化合同。没有合格候选，保持基线就是有效输出。

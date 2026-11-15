# 增补包执行约束

本包只增补 2026-11-06 基础包；用户直接指示、目标仓库更严格约束与冻结合同优先。

- 本次交付仅文档、离线示例/自检；PLANNED 不得改写成 IMPLEMENTED。
- 不启动 Strata、samir-vllm 或微基准，不访问 GPU，不 SSH，不下载模型，不改生产。
- 原基础包 O0–O6 保留；本增补 E0–E4 是子任务链，不是另一个框架。
- 唯一实验根是 CodexGame 的 docs/strata_4090_128k_lab；Strata 是另一工作树，禁止混淆两个相对根。
- controller 仍是原计划 tools/frontier/exploration_control.py；已有实现先审差量。新增只能是版本化附件与薄适配。
- 不复制 samir-vllm allocator/scheduler/kernel，不迁移 JAX/Pallas，不扩大到多 GPU 或训练。
- 不重启 F01/F02/F03、P01/P01B、P24、DFlash2、NP3、SPEC/SPECCOST；不把换 SHA、tile、名字视为 premise_delta。
- 不修改原 4%净空间、六对统计、oracle、golden、holdout、自然EOS/失败保留合同。
- 不加入观测用 Device/Stream/EventSynchronize，不移动正确性原有同步/原子操作，不热路径 I/O/锁/分配。
- STRATA_VERIFY_PROFILE 的“0”仍是存在值，当前代码会开启；按实际版本记录，不统一猜测布尔环境变量。
- 原有 EXACT6/dispatch 设置保持一致；observer-off 不等于擅自关闭原有统计。
- HES 对 Ada 4090 不支持；权限或工具缺失必须 UNKNOWN/BLOCKED，不自动 sudo/setcap/改驱动。
- 检查源码、编译成功、反汇编和合成测试都不能证明实际命中、实测提升或模型正确。
- force_check 的 gen/score 是 live 命令；check/selftest 才是离线。不能直接把上游 Engine launcher 作为本机 OwnedServer 的替代。
- 离线附件读取固定输入白名单；不任意 import 用户模块、不执行 manifest 中的命令、不隐式联网。
- Phase 串行；互不改同一文件的 Task 可并行。Task 最小测试；Phase 独立 review 与独立 test。
- raw/manifest/报告输出不得覆盖原件；失败保留，未知不补零，不能用交集悄悄丢请求。
- 本包 tools 是示例合同/交付检查，不是完整产品实现或可用于生产晋升的裁判。

# 来源、许可与使用边界

本包由用户提供的评测/设计资料及文档中列出的公开源码核对形成。`input-review`是用户输入的副本；按`references/input-provenance.json`记录hash与脱敏状态。禁止将其中私有机器、路径、业务轨迹未经批准提交到公共仓库。

`fixtures/java-agent-*`沿用用户此前的23文件基准；参考修复仅在本次临时目录中用于验证题目，未交付。`tools`是本次辅助代码；`contracts/proposal_contract.h`是开发接口说明，不是已链接的引擎实现。

本包没有重新分发完整NInfer、Sage、vLLM、ArcticInference源码或模型权重。T00/T05/T08在移入任何donor代码前核对其固定提交的LICENSE/NOTICE与文件头，保留版权、作者、修改说明和适用许可证；不能依据仓库描述“看起来是Apache”跳过这一步。

所有模型性能预测均需要真实机器验证。权限/维护工具不是抵御恶意Agent的安全沙箱；执行者负责在授权维护窗口、可信进程环境下运行，并核对生产恢复状态。

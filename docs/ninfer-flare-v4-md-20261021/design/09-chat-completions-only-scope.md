# 当前产品范围：纯文本Chat Completions性能

用户只要求OpenAI Chat Completions。当前以纯文本与工具调用/流式增量的真实性能为目标；Responses、Messages、Decisions/TypeSafe、图像/视频、Playground和其它目标模型都不作为性能研发或候选验收前置。

已有共享实现不在本轮删除，完整上游候选也可以携带未启用代码，但不因此恢复这些功能的必测矩阵。只有选中改动实际触及的共享编译依赖、数值、采样、缓存身份/格式、故障/取消和GPU生命周期需要定向验证。不能借scope收缩删除真实Chat合同或放宽断言。

DFlash2、检索、W8/W16和utility是可能提升推理性能的实验，不属于无关业务功能；全部保留可选择的candidate入口。完整上游也按性能/耦合证据选择，不能统一视为零价值或统一强制完成。

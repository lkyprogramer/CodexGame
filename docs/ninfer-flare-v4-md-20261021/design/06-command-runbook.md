# 命令与执行边界

本轮只运行文档检查，命令见[只读检查器](../evidence/validate-documentation.py.md)。不执行历史材料中的构建、模型、grader、GPU矩阵或服务切换命令。

后续开工使用用户指定的`ssh 29`直连，在干净P4研究树的隔离分支工作。先读取当前回执/进程/请求终态，不能从旧/tmp或owner PID猜状态；不因连接失败重复启动。P5冲突导入只读保留，当前不恢复。

未来每个已授权实验都先冻结可审核账本：source tree/HEAD、dirty diff、BO image/build flags、模型/codec/tokenizer/template/采样、script/manifest哈希、输入与route/shape、总wire/提交/native/Graph/时间/内存预算。请求允许后，原始request/raw/SSE与request/job/round关联必须落盘；unknown outcome先readback，不自动重发。

结束只清理本次候选和临时资源，原GPU服务保持停止。生产启动/发布/回退另行授权，不沿用历史窗口的恢复要求。预算耗尽/硬边界失败停止，保留全部失败与成本。

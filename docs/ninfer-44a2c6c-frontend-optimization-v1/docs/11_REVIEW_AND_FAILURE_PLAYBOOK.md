# 11｜Review与故障处理

## 11.1 独立Reviewer必须核对

阅读diff前先看03的oracle与04的guard证明。检查代码有没有把单请求exact-prefix冒充未来append稳定；有没有把原始byte offset误用为NFC后offset；added-token同位置tie是否仍为ID顺序；hint非递减及allow_full是否保留；错误包装/发生顺序是否被排序优化改变。

进一步检查Frontend共享const Impl后的cache所有权、锁范围、被pin条目计费、超预算fallback、跨资源隔离。任何按session ID直接复用而不比较bytes的实现拒绝合入。模型输出直接append进cache、固定尾部token窗口证明、media走文本捷径，同样拒绝。

## 11.2 常见假成功

| 表现 | 可能错误 | 必须取证 |
|---|---|---|
| 主encode变少但TTFT仍几十秒 | 边界prefix仍全量编码或scanner反复扫 | BPEbytes、boundary calls、CPU profile |
| tokens相同但append命中下降 | PromptIdentity/hints不同 | 完整metadata diff、原顺序/重复 |
| 第一次快，第二次错误 | EOF或partial added误复用 | 最短append反例与guard切点 |
| Unicode单测正常但中文日志失败 | NFC/码点切割或byte/char混淆 | 原始bytes hex本地受控记录 |
| count_tokens快，prepare慢 | 只优化计数API没优化hint路径 | 确认Frontend::prepare调用 |
| shadow显示很慢 | 同步多做legacy oracle | 不能用shadow wall评估candidate净性能 |
| 全部stop_token | 只看到完成子集 | request_error/rejected/工具verify总分母 |
| decode提高但任务慢 | TTFT/重试/首包缓冲 | 客户端首次非空delta与任务墙钟 |
| schema解析字段缺了却0耗时 | adapter默认0 | missing字段必须null/报错 |

## 11.3 失配缩小流程

冻结输入hash和资源identity；复制到受控本地fixture。先只比较Tokenizer::encode，再比较边界resolver，再比较Frontend metadata，最后查GPU路径。缩小消息数/边界数而保留首个差异；每次只改变一个因素。

若tokens错：关闭CPU cache仍错则定位single-pass；single-pass关闭才正确则trace/scanner/局部resolver问题。若tokens对而metadata错：检查query去重后原顺序重建。若仅多线程错：检查snapshot共享和lifetime，不修改BPE以掩盖竞争。

## 11.4 Golden管理

oracle生成后不可由candidate覆盖；脚本默认不同输出目录，存在文件则拒绝除非明确新campaign。golden更新必须有“基线/资源合同改变”的批准，而本任务不允许改变这些合同。浮动main的结果只能做参考，不是golden。

## 11.5 完成声明允许的粒度

允许：“辅助脚本12个测试通过，NInfer/CUDA测试未执行。”
允许：“真实资源CPU等价通过，4090端到端Gate待维护窗口。”
不允许：“所有验证通过”，实际只运行了Python/静态检查。
不允许：“预计80秒变0.5秒”，不附同输入实测且不标为目标。

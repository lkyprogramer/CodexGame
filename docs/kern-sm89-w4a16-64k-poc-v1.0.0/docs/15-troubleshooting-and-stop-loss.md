# 故障隔离与止损

| 现象 | 先看什么 | 禁止的“修复” |
|---|---|---|
| no kernel image / invalid image | cubin真实arch、源/toolchain key | 改文件名、移除hash校验 |
| invalid value / too many resources | 参数ABI、shared-memory总量、grid | 盲降校验门 |
| 文本连贯但后续错误 | teacher-forced第一个差异、GDN/conv位置 | 仅调temperature掩盖 |
| 64K OOM | manifest最大shape、graph/pad/state slot、重复权重 | silent truncation或CPU offload冒充 |
| exact repeat快但append慢 | template重渲染、最后token是否消费、end checkpoint | 按session id强制错复用 |
| graph快但结果漂移 |指针生命周期、host-write事件、shape bucket|跳过graph正确性测|
| Pi无工具调用 | tool schema/template/parse/usage/CLI | 把自然语言描述当工具执行 |
| HTTP墙钟慢 | tokenization、prefill/decode、restore拆账 | 用kernel单测数字替代E2E |
| GitHub不可达 | 源码bundle、vendor、离线镜像 | 全局改DNS/代理或安装无关CUDA |

## 止损条件

未知codec/ABI不能安全解释；需要超过可用显存的常驻BF16整模型；必须依赖SM90+专用指令；P0持续出现state corruption；无法保护/恢复生产；64K靠截断才通过——立即停止本路线交付，输出最小复现。可以保留已完成的单层实验，但不能给POC_GO。

单一优化不超过3次有证据的调参循环。用户生产已经有可用NInfer，不应为了追一个不确定的小提升长期破坏工作环境。

## 恢复动作

先停止你自己登记的candidate前台进程/实验容器，确认GPU没有该进程。若 `.state/gpu-lease.json` 写了restore_required，且guard/child已终止，再启动白名单unit、检查18343模型id与18030。不要启动多个冲突服务，不用`pkill -9 python`等全局命令。

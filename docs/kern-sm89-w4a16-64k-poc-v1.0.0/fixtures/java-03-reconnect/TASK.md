只修改 src/main 下的生产代码，不修改测试、TASK.md、AGENTS.md 或 verify.sh。先运行 ./verify.sh 复现，再读代码、修复，最后再次运行。禁止删除测试、绕过断言、联网下载依赖、改用其他语言或请求 sudo。最终简要列出根因、修改文件及测试结果。

客户反馈：刚连接的会话被提前踢下线，旧连接的异步清理有时会删除新连接。结合 DESIGN.md 和 reconnect.log 修复 HeartbeatPolicy 与 SessionRegistry。秒→毫秒转换必须可检测溢出；恰好到期应过期；时钟倒退不应过期；只能删除预期的同一 Session 实例。保持 API 不变。

只修改 src/main 下的生产代码，不修改测试、TASK.md、AGENTS.md 或 verify.sh。先运行 ./verify.sh 复现，再读代码、修复，最后再次运行。禁止删除测试、绕过断言、联网下载依赖、改用其他语言或请求 sudo。最终简要列出根因、修改文件及测试结果。

修复 IdempotencyStore：相同有效 key 的成功结果只计算并保存一次；并发调用也共享该结果。失败不得缓存，后续允许重试；不同 key 不能被全局锁串行化。key 为 null/空白应拒绝。使用 Java 8 标准库。

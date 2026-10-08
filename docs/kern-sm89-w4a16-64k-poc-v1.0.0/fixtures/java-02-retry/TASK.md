只修改 src/main 下的生产代码，不修改测试、TASK.md、AGENTS.md 或 verify.sh。先运行 ./verify.sh 复现，再读代码、修复，最后再次运行。禁止删除测试、绕过断言、联网下载依赖、改用其他语言或请求 sudo。最终简要列出根因、修改文件及测试结果。

修复重试合同：maxAttempts 表示包括首调在内的总尝试次数且必须 >=1。只重试 IOException；其他 Exception 原样传播。InterruptedException 必须立即传播并恢复中断标志。不得吞掉最后一个异常、不得增加 sleep 或引入依赖。

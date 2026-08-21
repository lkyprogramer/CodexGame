# Python Webhook 验签与重放审查

审查 webhook 接收器的认证、原始消息语义、时间窗口、去重并发与错误响应。只报告可从代码证明的问题。

输出必须是单个 JSON 对象，不要使用 Markdown 代码围栏：

{"issues":[{"file":"相对路径","line":1,"severity":"critical|high|medium|low","category":"类别","explanation":"问题、可利用条件与影响","fix":"具体修复方案"}],"summary":"总体结论"}

只报告有代码证据的问题。相同根因不要重复计数。

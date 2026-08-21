# Java 文件上传服务安全审查

审查上传落盘代码，识别路径、文件类型、资源消耗、竞态和覆盖风险。需要区分“字符串检查”与真正的文件系统边界保证。

输出必须是单个 JSON 对象，不要使用 Markdown 代码围栏：

{"issues":[{"file":"相对路径","line":1,"severity":"critical|high|medium|low","category":"类别","explanation":"问题、可利用条件与影响","fix":"具体修复方案"}],"summary":"总体结论"}

只报告有代码证据的问题。相同根因不要重复计数。

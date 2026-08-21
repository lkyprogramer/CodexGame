# Python 并发任务队列审查

审查任务队列的并发正确性、死锁、唤醒、生命周期和 API 级数据共享问题。给出具体交错场景与修复方向。

输出必须是单个 JSON 对象，不要使用 Markdown 代码围栏：

{"issues":[{"file":"相对路径","line":1,"severity":"critical|high|medium|low","category":"类别","explanation":"问题、可利用条件与影响","fix":"具体修复方案"}],"summary":"总体结论"}

只报告有代码证据的问题。相同根因不要重复计数。

# 换会话后接续执行

先读取00、AGENTS、manifests/plan.json和最新phase-report/gate，不从“已经开发完了”的自然语言推断完成。核对实际source、binary、base、Predictor和config的SHA。

列出最高已通过的必需Phase、当前失败/阻塞项与仍允许执行的Task；然后只执行下一项具备依赖的工作。P7可选，没做不等于整个CED16未完成；P7失败也不能伪造为通过。

若主机有maintenance.json未结束，先按07确认生产状态，不能直接启动新实验。GPU单实例，生产暂停必须有显式授权。读不到原始证据时将原声明降为待验证，不继续堆砌功能。

# CPU / HTTP 基准报告模板

## 数据来源

本次输入来自review retained / v2 synthetic / authorized production capture之一。标明真实body是否可用。报告所有hash、compiler、affinity、governor、并行负载；GPU跑分只在HTTP部分。

## CPU

legacy/b0/b1/b0-b1构建lane各自函数来源；每case记录B/P/H/Q/A、maincalls、scanpositions/candidatechecks、localbytes/max、重复列表、median/p90；每行是否独立oracle=true。没有保留B0raw时留空，不能把review文字10.01抄成新测量。

## HTTP

准确P+reserve校准、maxcontext、sampler、model/artifact、cachepath、firstmeaningfuldelta。说明baseline/candidate分开占卡、其它客户端隔离。生成差异若使后续prompt不一致，退出paired结论，不用不同会话比较。

## Gate

按08给G2/G4/G5状态。记录失败/缺测，不只展示通过组。短请求按结构分层报告，不用长请求大幅提升掩盖短输入退化。CPU≤1s是指定环境目标，不是所有输入保证。

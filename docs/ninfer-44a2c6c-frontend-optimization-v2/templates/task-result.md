# 任务报告模板

复制到自己的execution evidence目录，不覆盖原始模板。

## 身份

记录task_id、状态NOT_RUN/IN_PROGRESS/PASS/FAIL/BLOCKED、执行者、UTC时间、pin、candidatecommit、overlaySHA、resourceaggregateSHA、构建镜像及compiler身份。未知值写null并说明阻塞门，不填看似有效的示例hash。

## 需求与实际修改

列出本卡输入/输出合同、修改文件和diffhash；说明没有修改的GPU/权重/模板/采样/参数。标明与计划偏差及原因，不能省略暂时关闭的测试。

## Red → Green

| 命令 | 环境/输入hash | 退出码 | 原始输出文件与SHA | 结论 |
|---|---|---:|---|---|

表初始为空；执行后逐行填入真实信息。失败测试要证明失败原因是预期结构/语义，而不是找不到资源或编译器。纯正确性回归旧版已绿时另保留结构门red。

## 边界/错误/性能

列出具体case/resourceprofile覆盖、oracle来源、测试数量/seed/失配数。CPU与HTTP分开，source/function拷贝原型与真实product分开。记录first mismatched field以及最小化case路径，不在公开报告贴真实prompt。

## 剩余与下一步

明确本卡门PASS/FAIL/BLOCKED和原始依据、剩余NOT_RUN、下一任务ID。任务代码完成不等于部署；没有授权的生产动作保留READY_NOT_DEPLOYED。

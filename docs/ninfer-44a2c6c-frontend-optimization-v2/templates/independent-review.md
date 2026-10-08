# 独立审查报告模板

**初始结论：NOT_RUN。** 合法最终状态：APPROVE_FOR_AUTHORIZED_RELEASE / REQUEST_CHANGES / BLOCKED_EVIDENCE。

记录reviewer、被审candidate/overlay/resources/image完整身份，审阅文件与实际复跑命令，不把自己未跑的owner测试写成亲自验证。

## 必答项

earliest-position/smallest-ID是否与旧版等价？真prefix冲突与specialflags覆盖？桶是否copy/move安全？B1cut为何安全且没把ordinaryEOF当restart？所有name/allow_full/empty/full/uint32/hint顺序是否保留？reference是否独立？CPUshape是否准确P/H/bytes？超窗input是否CPU-only？HTTP是否隔离干扰并保留production采样？旧镜像是否真的能回滚？B2/full_reset有无混入？

## Findings

每条写id、P0/P1/P2、证据文件:行或原始row、复现命令、影响、最小修正、复验门。没有问题时明确覆盖与盲区，不能写“全都没问题”替代范围。

## 发布裁决

G0–G5与G7证据齐全才可准入；G6分别记录ready与execution。GPU/HTTP未跑则不能批准直接生产。若授权未取得，保持READY，不做隐式部署。

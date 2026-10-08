# 10 · 构建、维护窗口、部署与回滚

## 10.1 安全边界

本包工具不会停止服务、登录主机、改systemd、下载权重或覆盖镜像。以下命令是执行计划，只有具备权限与用户明确维护授权才执行生产相关步骤。始终保留原source worktree、未提交diagnostic diff、旧镜像完整ID及启动配置。

```bash
PIN=44a2c6c3392c9d51e76a895ed97bf1867530d252
: "${REPO:?Set the audited source checkout}"
: "${EVIDENCE:?Set a new evidence directory}"
mkdir -p "$EVIDENCE"
git -C "$REPO" show -s --format='%H%n%s' "$PIN"
git -C "$REPO" status --short
# Only if this checkout is proven to correspond to prepare-detail:
git -C "$REPO" diff --binary "$PIN" > "$EVIDENCE/prepare-detail.patch"
```

diff只覆盖tracked内容；另记untracked清单并确认是否参与镜像构建，避免漏诊断脚本。不能自动reset/clean/stash原工作区。新worktree从pin建立，再审阅后应用overlay；overlay已包含其它语义修复时记录并先单独baseline验证，不假装纯计时。

## 10.2 原工程编译环境

固定源码声明C++20、CMake>=3.28、CUDA>=12.8，目标`sm_89`。评审使用CUDA13.2构建镜像/GCC13.3/glibc2.39，这些是参考现场信息，不是本地已安装保证。优先用已确认的生产构建镜像digest，不升级驱动、不拿旧宿主CUDA12.3硬编。

```bash
cmake -S "$REPO" -B "$BUILD" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DBUILD_TESTING=ON -DNINFER_BUILD_APPS=ON \
  -DNINFER_BUILD_QWEN3_8_27B=ON -DNINFER_BUILD_QWEN3_6_35B_A3B=OFF
cmake --build "$BUILD" --parallel 4 --target ninfer_qwen3_8_frontend_test
ctest --test-dir "$BUILD" -N
ctest --test-dir "$BUILD" --output-on-failure -R '^ninfer_qwen3_8_frontend_test$'
```

`BUILD`必须是新目录。新增v2target注册后再编译它们。工程即使跑CPUfrontend测试，configure/link仍可能依赖CUDA、FFmpeg、curl等；缺依赖标BLOCKED，不用Python辅助模型替代。

## 10.3 CPU-only 评审原型

[build_review_bench.sh](../tools/build_review_bench.sh)只提供评审附带harness的编译路径，以便调查比较，不构成产品测试。它要求固定源码与本地编译器，不触碰GPU。不传`--gpus all`。真实raw资源从artifact提取，本包不打包17GB模型。

评审基准输入和资源不完整；执行者必须注明自己生成的新fixture。build命令可在既有镜像中执行，镜像tag需本地锁成digest；不自动pull浮动tag。

## 10.4 候选镜像与不变量

建议新标签`ninfer-4090:frontend-b0-b1-<candidate-short-sha>`，仅便于人类识别；部署记录完整image sha256。不要覆盖`prepare-detail`标签。启动参数/model ID/接口/端口/采样/max-context/MTP/kv/weights路径保持现网已有值。

核对构建Dockerfile不会偷偷bake/下载新版artifact。挂载旧模型只读并记录resource/制品身份。server_start需与预期参数对齐；不能启动后发现格式不支持就换制品完成测试。

## 10.5 一次维护窗口的内容

授权、记录现网状态和metrics → 隔离外部请求来源 → 停止原服务占卡 → 旧镜像做基线requests → 释放GPU → 新镜像执行同输入对照 → rollback旧镜像smoke → 按最终授权决定是否再部署candidate → 恢复流量。

不得同时加载两个约20GB服务。不要抢用生产端口，测试endpoint只loopback并遵守现有鉴权。2工具客户端来源未知时先只读调查，不能自行杀掉或改它路由。

## 10.6 发布前条件与退出条件

G0–G5及独立G7 review ready；旧镜像可启动与配置可恢复；无未解释semantic/error差异；CPU绝对门满足；真实resource已冻结。发布后只观测新路径，不加legacy shadow。

出现token/hint/metadata错误、cache/computed异常、新request_error、RSS持续增长、短请求稳定回退：停止candidate流量并按预先授权rollback流程恢复旧镜像。无权限则立即报告需人工操作，不声称已回滚。rollback应测试models/健康、小型medium工具回合，不能只看进程alive。

## 10.7 记录

记录新旧镜像完整ID、source/overlay/resourcehash、时间UTC及本地offset、旧/新启动参数diff、smoke输入hash、原始响应元数据、GPU峰值/CPU负载、释放与端口检查。敏感token不进入文档。重启可能导致一次冷prefill，不把它当优化回退，也不隐去启动成本。

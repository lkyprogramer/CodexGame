# 10｜构建、部署与回滚

## 10.1 两个不同基线

纯源码baseline必须是完整44a2c6c；现网prepare-detail是该基线之上的未知本地diff。先读取现网image ID、启动脚本、systemd unit、proxy版本、source diff，保存只读证据。不能把现网镜像覆盖成新tag后再声称可回滚。

```bash
PIN=44a2c6c3392c9d51e76a895ed97bf1867530d252
git cat-file -e "$PIN^{commit}"
git show -s --format='%H%n%s' "$PIN"
git status --short
git diff --binary "$PIN" > ../ninfer-prepare-detail-overlay.patch
# 此diff仅在该worktree确实对应诊断镜像时才是部署证据；否则记为未知。
git worktree add --detach ../ninfer-ftc-baseline "$PIN"
git worktree add -b perf/frontend-tokenization-v1 ../ninfer-ftc-work "$PIN"
```

禁止`reset --hard`覆盖原工作区。若本机无GitHub网络，从已验证源副本/镜像构建上下文取证，不强行替换成远端main。

## 10.2 构建约束

源码声明CMake≥3.28、C++20、CUDA≥12.8且`CMAKE_CUDA_ARCHITECTURES=89`。[S12] 用户现网构建容器为CUDA13.2系；不把宿主nvcc12.3当有效编译器，也不为本任务升级宿主驱动。复用经确认的构建镜像，固定digest。

```bash
cmake -S . -B build-ftc -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DBUILD_TESTING=ON \
  -DNINFER_BUILD_APPS=ON \
  -DNINFER_BUILD_QWEN3_8_27B=ON \
  -DNINFER_BUILD_QWEN3_6_35B_A3B=OFF
cmake --build build-ftc --parallel 4 --target ninfer_qwen3_8_frontend_test
ctest --test-dir build-ftc -N
ctest --test-dir build-ftc --output-on-failure -R '^ninfer_qwen3_8_frontend_test$'
```

这套工程即使只跑CPU frontend test，configure/link仍依赖CUDA及FFmpeg/curl等。**“测试不执行GPU计算”不等于“在纯Python环境可以编译原仓”。** 缺依赖记录NOT_RUN，不用替代实现冒充。

新增targets在T03–T09注册后再构建。最后运行相关CTest集合和生产enabled target的完整suite；77单独记录。

## 10.3 制品保护

旧17GiB MTP `.ninfer`不替换为HF main的DFlash2制品。所有实验权重只读mount，checksum对应旧baseline。不要直接运行可能自动下载/烤入浮动制品的默认Dockerfile流程；采用用户已有已审计的no-bake构建方式，并核对启动所加载的路径。

版本建议：`ninfer-4090:ftc-single-pass-<commit>`与`ninfer-4090:ftc-incremental-<commit>`；真正deploy记录image sha256，不依赖tag。不能给新代码复用`prepare-detail`旧tag覆盖原镜像。

## 10.4 单卡互斥及服务保护

生产NInfer、WORK/TEXT、评测容器互斥。维护前记录当前service active/enabled、container列表、监听端口、model ID、窗口和metrics；维护后恢复同一service，而不是旧llama.cpp。

本包不自动执行停服务。执行者必须有明确维护授权。使用用户现有start/restore脚本，不重新发明端口布局。实验端口避免18030/18343/28343冲突，绑定loopback；禁止暴露引擎绕过兼容层。

## 10.5 部署阶梯

1. Baseline+计数：验证诊断无明显扰动，保存原slow case。
2. single-pass离线：全oracle与构造反例、A/B Gate。
3. single-pass维护窗口：相同text/tool/medium warm episode，确认GPU路径没变。
4. incremental离线：证书、cache生命周期与oracle全部过。
5. 有界shadow：只CPU双算、只提交legacy，采样不让正常短请求被长oracle阻塞。
6. canary：优先专用测试会话或明确授权窗口；mismatch自动熔断，不自动改全局生产参数。
7. release：记录mode、镜像digest、门结果；保留旧镜像/脚本直到回滚演练完成。

## 10.6 回滚触发及顺序

token/metadata mismatch、新增非法输入接受、GPUcache异常、RSS持续增长、短请求延迟越门或新增request_error：立即停止新mode。先回legacy逻辑的已验证镜像/参数；进程级参数变更需要重启，不假装现有运行时热切换。

重启会丢CPU token cache，这是预期；不得为了保留它伪造GPU state兼容。模型/接口/采样配置恢复后跑`/v1/models`、一个medium smoke、一次小型tool回合，再恢复真实流量。GPU KV/L1是否跨重启存在由原机制决定，不作额外保证。

回滚报告包含原/新镜像ID、时间、服务状态、smoke结果及残留容器/端口检查，不包含Bearer token或密码。

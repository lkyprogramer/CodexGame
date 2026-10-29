# 固定配对性能运行

`run_campaign.py` 是29宿主机入口。默认只读取清单并输出计划，不调用Docker、不写文件。正式执行前必须完成Mini安装，所有其他本任务job终态、无编译；两个候选容器必须已创建，`/work`挂载同一任务根、CPU集合`0-7`。不要外包`run_job.py`：本脚本自己持久化状态，外层RUNNING记录会被当作其他活跃工作阻止。

```bash
python3 /data/ocr/dual-ocr-20261028/deploy/run_campaign.py --plan-only
nohup python3 /data/ocr/dual-ocr-20261028/deploy/run_campaign.py --execute --name perf40-r1 > /data/ocr/dual-ocr-20261028/logs/campaign-perf40-r1.log 2>&1 &
```

`--pairs`支持1、3、6，默认6。六对固定顺序为Mini/Ovis、Ovis/Mini、Ovis/Mini、Mini/Ovis、Mini/Ovis、Ovis/Mini；三对固定为Mini/Ovis、Ovis/Mini、Mini/Ovis，先后数量相差1；单对为Mini/Ovis，只能用于扫描，不作主速度统计。计划记录统计范围，不因结果增减轮数。每一轮先停止本任务的既有GPU容器，再启动当轮容器，因此相邻同模型也会获得新进程。只操作硬编码的两个OCR候选；build容器和既有CPU OCR服务仅只读检查。

默认兼容原40页D0诊断。正式G4分成两份独立六对campaign，明确给scope及清单：

```bash
python3 /data/ocr/dual-ocr-20261028/deploy/run_campaign.py --plan-only --name g4-d0-whole49-r1 --workload complete49 --timing-scope D0 --manifest /data/ocr/dual-ocr-20261028/corpus-extra/perf-prepared/d0-complete3-49-manifest.json --warmup-manifest /data/ocr/dual-ocr-20261028/corpus/development-manifest.json
python3 /data/ocr/dual-ocr-20261028/deploy/run_campaign.py --plan-only --name g4-p0-forty-r1 --workload selected40 --timing-scope P0 --manifest /data/ocr/dual-ocr-20261028/corpus-extra/perf-prepared/p0-formal40-manifest.json --warmup-manifest /data/ocr/dual-ocr-20261028/corpus-extra/perf-prepared/p0-dev4-manifest.json
```

将对应命令的`--plan-only`换成`--execute`执行；两个campaign串行，使用各自名称和日志，不能并行启动。D0完整集严格要求原3份PDF的15/26/8页，原始页序和所有49页齐全。P0严格要求正式40页及开发4页均为共同预渲染图像，拒绝PDF输入。D0与P0各有12个新模型进程、独立开发预热、采样文件与墙钟，不能把两种scope合并吞吐或称同一服务内连续job。

原选择清单保留原hash，formal和warmup均另写冻结执行清单：稳定文档分组，把任务根下宿主绝对路径或已经位于`/work`的容器绝对路径统一映射到`/work`；相对路径先按原清单位置解析。页身份、像素及固定40或49个分母不变。每轮由现有执行器完成4个开发输入的同worker预热，之后page admission=1、region limit=4。每轮开始重验原formal/warmup及两份派生执行清单hash。API就绪、预热与正式计时分别保留；磁盘缓存和持久JIT缓存未控制，不称冷磁盘或完全冷缓存。

G3同裁剪性能使用`--workload mixed100 --timing-scope R0`：100个唯一RGB正确crop，固定text70/name20/formula6/seal2/table2；4个开发crop为text3/name1，像素唯一且与正式集不交叠。R0允许同源family的不同crop，计划明确标为性能输入，不声称holdout质量或独立作者。每个输入必须有公开task，现有执行器按case.task调用对应区域任务。

```bash
python3 /data/ocr/dual-ocr-20261028/deploy/run_campaign.py --plan-only --name g3-r0-region1-r1 --workload mixed100 --timing-scope R0 --pairs 3 --page-admission 4 --region-limit 1 --manifest /data/ocr/dual-ocr-20261028/corpus-extra/perf-prepared/r0-mixed100-manifest.json --warmup-manifest /data/ocr/dual-ocr-20261028/corpus-extra/perf-prepared/r0-warmup4-manifest.json
```

`--page-admission`与`--region-limit`均支持1、2、4，默认仍为1/4；每档使用独立名称/配对campaign。G3固定page=4，逐档region=1/2/4，各3对。G4容量扫描使用完整49页D0，逐档page=1/2/4，各6对；P0 selected40以page=1为主。完整D0三文档各有8页以上，可在文档完成边界内接纳多页；40页P0来自39文档，配置page=4通常仍只有1个实际活跃页，不能称容量4通过。配置上限与实测活跃度分开，实际区间由每份产物的`events.jsonl`中page_admitted/page_terminal及时间戳核实；共享区域并发由现有执行器的全局slots限制。

证据在`evidence/campaign-NAME/`：冻结计划与源hash、派生清单、每轮新PID/StartedAt、真实argv/预算、1Hz GPU/cgroup采样、前后各10秒空闲窗口、既有CPU OCR负载快照、日志及持久化终态。模型产物在`results/NAME-pNN-POS-MODEL/`。`PASS`仅表示固定执行与产物门通过；质量仍由独立评分确定，脚本不产出good-page/s或质量排名。

失败只留终态继续后续预定轮，不复用其结果。若发现外部活跃工作、队列无法确认空闲、服务启动失败或资源条件变化，该轮FAIL；不强行停止非本轮启动的进程。进程被外部杀死时保留RUNNING状态，需先核实现场，不可直接重用同名目录。资源采样和分布统计的有效性由后续报表按完整窗口检查。

## 统一串行入口

`run_sequence.py`在两模型标准验证完成后，串行执行7组66轮配对及两模型各一小时E0。默认`--plan-only`只检查静态矩阵；正式执行前会调用现有`build_plan`检查真实输入。E0使用由原3份PDF共同预渲染的49张P0图，最多4个活跃页；不将重复压力输入计为新增独立质量样本。

```bash
python3 /data/ocr/dual-ocr-20261028/deploy/run_sequence.py --plan-only
nohup python3 /data/ocr/dual-ocr-20261028/deploy/run_sequence.py --execute --name g3g4-e0-r1 > /data/ocr/dual-ocr-20261028/logs/sequence-g3g4-e0-r1.log 2>&1 &
```

入口不外包`run_job.py`。组内模型失败保留后继续固定轮次；共享guard、冻结源码/清单漂移、未知终态或清理异常会停止后续步骤。状态在`evidence/sequence-NAME/state.json`，各组与E0证据保留独立目录。脚本不产生质量排名；默认计划通过也不代表真实GPU测试通过。

统计方法在读取正式轮次结果前固定：按相同pair配对比较完整固定工作量墙钟及资源，不按成功页筛选。速度比使用同pair固定分母的墙钟比，95%区间用配对块bootstrap（10000次，seed=20261029）；3对扫描的区间仅描述该小样本，6对也不代表新文档泛化。未完成或缺失pair不补造比率。聚合延迟必须报告重复观测数与唯一页/源家族数；不足200观测不报p95、不足1000不报p99。AI合格吞吐另需对应输出的验收与身份绑定，不能从parse PASS推导。

已有idle检查还保存`api-before-warmup.prom`与`api-after-idle.prom`完整服务指标，不额外发模型请求。其TTFT/TPOT/prefill/decode sum/count差值覆盖同worker开发预热、恢复与正式API请求；Mini区域请求与Ovis整页请求的单位不同，不能把这个均值标为正式整页首token延迟。客户端非流式，正式整页TTFT仍为UNAVAILABLE。薄汇总入口为`summarize_campaigns.py`，E0只统计真正admitted集合，未提交候选不进入失败和能耗分母。配对bootstrap的组估计是sum(Mini墙钟)/sum(Ovis墙钟)，每次重采配对块后重算该比值；单pair比值另列。

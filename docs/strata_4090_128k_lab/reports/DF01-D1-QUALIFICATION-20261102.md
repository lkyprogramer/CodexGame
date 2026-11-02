# DF01 / D1 · 首组概率检查失败，恢复 v0.2.3 生产

日期：2026-11-02。连接：`ssh 29`。范围：用户明确授权D1、临时停生产，最多两项GPU验证程序、16组夹具、六次生成、总时限60分钟；失败保留、不补样本、不进入D2。

**已完成：按首个硬门停止并恢复原生产。D1资格失败，状态为`BLOCKED_NUMERICAL_ORACLE`。** 实际启动一项GPU验证程序。首组`drafter-n32-seed1`在`selector probability 0`检查失败，exit 1。剩余15组夹具与六次生成均`NOT_RUN`。本轮没有性能或质量比较结果，不能据此判断DFlash2收益为正或为负。

原[D0](DF01-D0-PREPARATION-20261102.md)与[D0B](DF01-D0B-CPU-READY-20261102.md)报告不改写。六项旧FAIL、P05及已关闭方向保持。生产继续使用v0.2.3，未升级或部署新算法。

## 1. 执行与计数

| 项目 | 授权上限 | 实际 | 未执行 |
|---|---:|---:|---:|
| 原生GPU验证程序 | 2 | 1，失败 | target-state程序1项 |
| GPU夹具 | 16 | 首组失败，0组通过 | 后续15组 |
| CLI自由生成 | 6 | 0 | 6 |
| D2 | 未授权 | 0 | 全部 |
| 重试/替补 | 0 | 0 | 无 |

D0B的原始预登记仍保持准备态。新目录`workspace/dflash2/df01-d1-20261102/`单独记录本轮授权。只读取`qualification_programs`与`D1_generation_commands`，没有遍历21条lookup catalog或执行D2数组。

| 事件 | 北京时间 |
|---|---|
| 独立监督器开始 | 11:15:20.835 |
| 确认生产停止 | 11:15:23.429 |
| 首项验证进程结束被监督器确认 | 11:15:25.509 |
| 原生产恢复验收完成 | 11:16:02.183 |
| 最终独立只读复核 | 11:17:13.856 |

监督窗口41.348秒。确认停机至恢复验收38.754秒。程序的监督墙钟为2.079秒，包含2秒轮询等待，不能作为GPU执行耗时或性能数据。任务未接近60分钟上限，无需创建定时监控。

独立监督器在取得服务控制权限后与SSH会话分离。原生程序使用hhtele身份运行。监督器持原实验GPU锁，在正常、异常或超时路径执行所属进程回收及原unit恢复。工作截止点保守设置为12:00，保留10分钟恢复；本轮没有触发截止点。没有改systemd unit或创建常驻任务。

## 2. 首个硬门

实际程序为D0B冻结的`drafter_qualification`，SHA256：

`dd81db40825ea253339df28e1b9eb5d7c2927d4148b698efca1638582d815200`

实际pack为D0冻结的Q8 pack，SHA256：

`c7d83c0cdfeadc7c692a1587795adb0181cfd94dacd96ac1a91f71ea7ecc62ed`

首组为32 context rows、seed 1。使用最终`fixtures-q8act/drafter-n32-seed1.bin`，没有使用旧FP32激活参考。原始stderr：

```text
DF01 qualification FAIL: /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d0b-20261102/fixtures-q8act/drafter-n32-seed1.bin: selector probability 0
```

原始stdout为空。按冻结源码的检查顺序，当前证据支持：

- 原生drafter的load、bind、context、draft与debug_rows调用均返回成功。
- 输出shape为8×2560；八行全部通过finite、cosine≥0.98、norm比例0.95–1.05检查。
- 第0个提案token通过精确匹配，为116188。
- 第0个提案概率未通过finite、[0,1]范围、绝对参考差≤0.05组成的检查。

冻结CPU参考的第0项概率为0.7341100573539734。程序没有输出GPU实际概率及差值。因此无法区分非有限值、越界或差值过大。不能声称实际误差数值，也不能声称后六项token全部一致；比较器在第0项概率处返回。

原因仍`UNCONFIRMED`。运行时概率、CPU参考的概率定义及数值路径尚未定位到唯一原因。该失败不直接证明目标模型采样错误或生产缺陷。按照原合同，任何该类资格失败均停止整个候选。本轮没有改容差、改权重、修夹具、重编译或追加GPU探针。

独立selector三组位于四组drafter前向之后，因此本轮也没有执行。target-state九组、greedy配对、生产采样短/长配对均`NOT_RUN`。CLI的真实DFlash2开启日志、非零draft轮数与无回退合同仍未验证。

## 3. 预检与CPU控制

停机前验证31个冻结文件身份，包含13项保护文件、预登记合同、Q8 pack、两项资格binary、计量binary、参考夹具与D1输入。生产argv与STRATA环境白名单均匹配D0冻结记录。生产健康、GPU唯一归属、无在途18343/28343连接、磁盘余量及上下文预算检查符合合同。没有重新认证约47GB的目标GGUF全文件内容。

首次CPU预检失败属于本轮适配器的字段映射错误：把compact-JSON整数序列的`token_ids_sha256`用于比较空白分隔tokens-file字节。两份实际文件均匹配D0B `INPUTS.json.tokens_file_sha256`，不是输入漂移。修正后分别检查两个哈希命名空间，没有改输入或D0B冻结合同。原始`HASH_MISMATCH.json`、适配器版本与授权版本均保留。修正发生在停机和GPU启动之前。

监督器的四项CPU控制检查通过：正常退出、native exit 7、工作截止、4096MiB内存门。每项均检查只启动一次并回收所属进程。控制程序是CPU Python子进程，不是额外GPU验证程序或推理样本。

实际检查命令：

```bash
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1-20261102/cpu_controls.py'
ssh 29 'python3 -B /home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1-20261102/supervisor.py --preflight'
```

随后通过经认证的sudo启动同一监督器`--detach`。实际native argv、环境、PID/starttime/exe在`STATE.json.steps[0]`，原程序、夹具和生产参数没有变更。

## 4. 资源与生产恢复

本轮未触发资源停止门。验证进程短于采样间隔，仅产生一次护栏采样：43°C、MemAvailable 57888.11MiB。采样未捕获有效显存占用；不能把采样的1MiB当作DFlash2显存占用。真实显存峰值、专家槽减少量与CPU/搬运成本均未知。没有启动目标引擎，不能形成真实资源成本比较。

11:16:02恢复验收与11:17:13独立复核确认：

| 恢复项 | 结果 |
|---|---|
| `openclaw-qwen38-next.service` | active/running/enabled，NRestarts 0，MainPID 2545029 |
| 后端健康 | HTTP200、status=ok、loaded=true |
| 模型/上下文 | `openclaw/Qwen3.8-next` / 131072 |
| GPU归属 | 仅原v0.2.3生产native PID 2545035 |
| 生产exe | `/home/hhtele/strata-0.2.3/engine/strata`，原SHA匹配 |
| 原生产argv/环境 | 匹配冻结记录 |
| NGINX未认证访问 | HTTP401 |
| 13项保护SHA256 | 全部匹配 |
| 实验PID/18089监听 | 无残留 / 无监听 |

恢复时GPU显存23598MiB；44°C；MemAvailable约11969.59MiB。未改变缓存预算、PT0、生产配置、模型、Pi设置、NGINX、驱动或CUDA。现有unit执行一次stop和一次start。

## 5. 原件与验证边界

远端原件：`/home/hhtele/strata-lab-4090/workspace/dflash2/df01-d1-20261102/`。本地镜像：`workspace/dflash2/df01-d1-20261102/`。该目录Git忽略，原始证据不作为公开报告包内容提交。

关键原件：`AUTHORIZATION.json`、`PREFLIGHT.json`、`CPU_CONTROLS.json`、`STATE.json`、`drafter.stderr`、`TELEMETRY.jsonl`、`RESULT.json`、`RESOURCE_SUMMARY.json`、`RESTORE.json`、`FINAL_READBACK.json`、`RAW_MANIFEST.json`。首个CPU预检失败及修正说明同目录保留。

23个原件，共87172bytes，逐文件bytes/SHA验证一致。导出包16535bytes，SHA256：

`518e7aaaf5fde3eb96b5b943c11458f814b3c0f5c215164508e47b4c741f1d01`

`PACKAGE_CHECKS.json`单独记录本轮报告包验证。CPU比较器和旧exact-match枚举沿用D0B已有证据，不重复执行。应用apps/packages没有变更，未运行pnpm五项应用检查。没有commit或push。

## 6. 当前停止点

D1按失败合同收口，`D1_GPU_qualified=false`。数值/状态资格未建立。性能、绝对/相对质量与服务接入均未验证。不能推进D2，不能将其记录为DFlash2实测无收益，也不能据此升级生产。

下一项有价值的工作是单独授权的CPU源码审计：核对运行时selector概率定义和参考概率定义，解释首项失败；如需GPU实际值，必须另立有界复测合同。本轮不自动执行该审计、不调整门槛、不补样本。

## Why

火山 ASR 已在 utterance 的 `additions.speaker` 中返回多个说话人簇，但当前标准化逻辑忽略该字段并把所有片段回退为 `Speaker 0`，导致后续角色判断和报告标签全部失真。修复必须覆盖从 ASR 响应到报告输出的完整链路，并在外部结果不足时明确降级而不是伪造确定角色。

## What Changes

- 正确解析火山 utterance 顶层及 `additions` 中的说话人字段。
- 在标准化阶段输出不含转写内容的说话人诊断，并检测原始/标准化 Speaker 数量不一致。
- 将角色判断从“一名角色对应一个 Speaker”扩展为“多个 Speaker 簇可归属于同一角色”。
- 当只有一个 Speaker 或模型返回无效映射时，输出不可可靠判定状态，不再把同一 Speaker 同时标成面试官和候选人。
- 仅接受引用现有 Speaker 的 LLM 角色映射，并为无效输出提供确定性降级。
- 保留可用于说话人分离的音频信息；仅在必要时转码，并针对独立双声道提供明确处理策略。

## Capabilities

### New Capabilities

- `speaker-diarization-reliability`: 定义 ASR Speaker 标准化、诊断、多簇角色归并、可靠降级和音频预处理行为。

### Modified Capabilities

无。

## Impact

- CLI 流水线：`audio -> transcript -> analysis -> output`。
- 受影响代码：`pipeline/audio.py`、`pipeline/transcript.py`、`pipeline/analysis.py`、`models.py`、`cli.py` 及相关测试。
- `summary.json` 的角色映射会增加逐 Speaker 的角色信息；保留现有 `interviewer`、`candidate` 字段以兼容已有输出消费者。
- 不新增运行时依赖，不上传额外数据。

## Non-goals

- 不引入 Web UI、数据库、用户系统或远程任务队列。
- 不实现独立声纹注册、身份识别或新的第三方 diarization 服务。
- 不承诺将低质量单轨录音恢复成可靠的逐人声纹结果。

## Context

现有 ASR 请求已启用 utterance 和 speaker 信息。真实响应把 speaker ID 放在 `result.utterances[].additions.speaker`，而标准化器只检查 utterance 顶层字段并在缺失时回退为 `0`。因此 ASR 返回的多个声纹簇在进入分析层前被错误压成 `Speaker 0`。真实录音还显示两人对话可能被聚类为四个 Speaker，说明角色模型也不能假设 Speaker 与自然人严格一一对应。

## Goals / Non-Goals

**Goals:**

- 无损读取火山当前响应中的 speaker ID，并兼容已有顶层字段变体。
- 在 ASR、标准化和分析边界提供不含转写正文的可验证诊断。
- 支持多个 Speaker 簇映射为同一面试角色。
- 对单 Speaker、缺失 speaker 和无效 LLM 映射进行显式降级。
- 避免转码阶段无条件丢弃可能有用的独立声道。

**Non-Goals:**

- 不训练声纹模型，不识别现实身份，不接入新的 diarization 服务。
- 不根据低质量音频强行承诺角色准确率。
- 不改变 CLI 的本地运行边界和外部 API 供应商。

## Decisions

### 1. 在 transcript 边界统一解析并校验 speaker

标准化器按“顶层已知字段 -> `additions` 已知字段 -> unknown”的顺序读取 speaker，使用 `is not None` 而不是布尔 `or`，确保数值 `0` 不会被误判为空。缺失 speaker 使用 `Speaker unknown`，不再伪造 `Speaker 0`。

标准化后计算原始及规范化 Speaker 计数。若原始响应明确包含多个 speaker，而规范化结果少于两个，CLI 抛出可操作错误并保留 `raw-asr.json`。

替代方案是只增加 `additions.speaker` 一行读取逻辑；该方案无法发现后续响应结构漂移，因此拒绝。

### 2. 角色映射同时保留兼容锚点和逐 Speaker 映射

`RoleMapping` 保留可选的 `interviewer`、`candidate` 作为主要 Speaker 锚点，并增加 `speaker_roles`，值限定为 `面试官`、`候选人` 或 `未知`。报告重标记和问答分组统一通过逐 Speaker 映射判断角色。

两 Speaker 场景保持当前行为。多 Speaker 场景先用问题/回答标记和文本长度产生确定性映射，再允许 Ark LLM 基于完整转写修正。单 Speaker 场景的两个锚点均为空，原 Speaker 标签保持不变。

替代方案一是强行选择两个最大簇，可能丢失同一人的碎片簇；替代方案二是接入独立声纹模型，超出本地 CLI 的最小范围。二者均不采用。

### 3. LLM 输出必须经过语义校验

模型输出的 `speaker_roles` 只能引用输入转写中存在的 Speaker，角色值必须在允许集合内。缺失 Speaker 使用启发式结果补齐；引用不存在 Speaker、把同一 Speaker 作为两个锚点或无法形成面试官/候选人双方时，回退到完整启发式映射。问题复盘等其他合法字段仍可保留。

### 4. 转码按源声道数保留至多两个声道

单声道源文件继续转为单声道；双声道及以上源文件保留两个声道，不再无条件 `-ac 1`。这不会假设声道必然对应不同角色，但避免在进入 ASR 前不可逆地丢弃可能独立的通话声道。输出格式和码率保持不变，避免扩大长录音上传体积。

## Risks / Trade-offs

- [ASR 将同一人切成多个簇] -> 通过逐 Speaker 角色映射聚合，不删除原始 Speaker ID。
- [启发式对非典型面试误判] -> 输出置信度和原因，并允许经过校验的 LLM 映射修正。
- [双声道只是重复或混合信号] -> 保留声道不会制造角色结论，只避免提前丢失信息。
- [summary.json 结构扩展影响消费者] -> 保留原有锚点字段，新字段采用向后兼容的附加方式。

## Migration Plan

无需数据迁移。旧 `raw-asr.json` 可直接重新执行标准化和分析逻辑。回滚时恢复旧模型与标准化器即可，现有输出文件无需转换。

## Open Questions

无。当前真实响应结构和两份录音的 Speaker 分布足以覆盖本次修复范围。

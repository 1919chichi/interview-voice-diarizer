## Why

历史运行已经保存了完整 `raw-asr.json`，但当前 CLI 只能从录音重新调用 ASR，无法让旧数据应用新的 Speaker 标准化和角色映射逻辑。长录音重复上传既慢又产生不必要的外部调用，因此需要正式的仅重分析入口。

## What Changes

- 新增 `ivd reanalyze <raw-asr.json>` 命令，从已有 ASR 响应重新生成派生报告。
- `reanalyze` 禁止调用 ASR，并复用与 `debrief` 相同的标准化、诊断、角色分析和报告输出流程。
- 仅在 JSON 解析和分析全部成功后，备份现有 `summary.json`、`transcript.md`、`qa-review.md` 并覆盖新版本。
- 支持 `--skip-analysis` 进行完全本地的启发式修复；默认仅重新调用方舟分析。
- 支持重新传入公司、岗位和轮次元数据。
- 为当前两份历史输出执行安全回填，保留旧报告备份和原始 `raw-asr.json`。

## Capabilities

### New Capabilities

- `history-reanalysis`: 定义从历史 ASR JSON 安全重建报告、备份旧派生文件和避免重复 ASR 调用的行为。

### Modified Capabilities

无。

## Impact

- CLI 流水线增加旁路：`raw-asr.json -> transcript normalization -> role analysis -> output`。
- 受影响代码：`cli.py`、报告输出辅助逻辑、README 和 CLI 测试。
- 不改变 ASR 客户端，不修改或覆盖历史 `raw-asr.json`、录音和转码文件。

## Non-goals

- 不从缺失 Speaker 信息的纯文本中重建声纹边界。
- 不新增数据库、任务队列或 Web 批处理系统。
- 不自动从旧 Markdown 猜测结构化公司、岗位和轮次元数据。

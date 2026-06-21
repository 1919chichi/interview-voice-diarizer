## Context

`debrief` 当前把 ASR 调用、标准化、分析和写报告串在一个命令中。历史目录虽然保留了 `raw-asr.json`，却没有受支持的入口可以绕过 ASR。两份现有历史响应已经包含四个 Speaker，因此只需重新执行 ASR 之后的流水线即可修复错误报告。

## Goals / Non-Goals

**Goals:**

- 提供可重复的历史重分析 CLI，不重新上传录音或调用 ASR。
- 让新旧入口共用同一标准化、诊断、角色分析和输出实现。
- 分析成功后才备份并替换旧派生报告，保留原始 ASR JSON。
- 支持方舟深度分析和无外部调用的启发式模式。

**Non-Goals:**

- 不实现目录监听、数据库迁移或远程批处理。
- 不从旧 Markdown 反向解析结构化面试元数据。
- 不修复原始 ASR 本身缺失的声纹信息。

## Decisions

### 1. 新增独立 `reanalyze` 命令

命令接受 `raw-asr.json` 路径，输出目录默认是该文件的父目录。它只加载 JSON 和可选方舟配置，不加载 ASR 配置、不创建 ASR 客户端。

替代方案一是提供一次性 Python 脚本，但无法形成长期可测试能力；替代方案二是在 `debrief` 增加互斥的 `--raw-asr`，会让录音参数和 JSON 参数混在同一命令中。独立命令边界更清晰。

### 2. 提取 ASR 后处理编排

新增 `pipeline/debrief.py`：负责加载历史 JSON，并把 `normalize -> validate -> analyze -> relabel` 组合成一个返回结构。`debrief` 和 `reanalyze` 都调用该编排，避免两条路径产生行为漂移。

### 3. 输出层负责备份和落盘

`output/report.py` 增加统一写入函数。重分析在写入前把现有三个派生文件复制到 `backups/reanalysis-YYYYMMDD-HHMMSS/`；没有旧文件时不创建空备份。备份发生在 JSON 加载和分析成功之后，因此外部 API 失败不会触碰旧报告。

同一秒重复执行时为备份目录增加数字后缀，避免覆盖之前的备份。`raw-asr.json`、录音和转码文件不在备份或覆盖列表中。

### 4. 历史元数据显式重传

`reanalyze` 提供与 `debrief` 相同的 `--company`、`--role`、`--round`。未传入时使用默认标题，不通过旧 Markdown 猜测字段。修复当前已知目录时显式传入仍可确认的元数据。

## Risks / Trade-offs

- [方舟分析再次超时] -> 分析完成前不修改旧报告；可改用 `--skip-analysis` 本地修复。
- [旧报告包含仍有价值的人工修改] -> 默认备份三个派生文件后才覆盖。
- [启发式仍有未知 Speaker] -> 保留“未知”而非伪造角色，方舟模式可进一步判断。
- [历史元数据缺失] -> 命令允许显式补传，不做脆弱的 Markdown 解析。

## Migration Plan

先实现并验证命令，再对当前两个 `outputs/*/raw-asr.json` 逐个执行。确认 Speaker 基数和报告标签后保留备份目录。回滚时从最新备份复制三个派生文件即可。

## Open Questions

无。当前历史文件、输出目录和元数据保留情况已完成只读核对。

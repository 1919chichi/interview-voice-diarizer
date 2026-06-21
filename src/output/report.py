from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from models import DebriefReport, InterviewMeta, TranscriptTurn

DERIVED_REPORT_FILES = ("summary.json", "transcript.md", "qa-review.md")


def write_json(path: Path, data: object) -> None:
    """将对象序列化为缩进 JSON 并写入文件，使用 UTF-8 编码保留中文字符。"""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_debrief_outputs(
    output_dir: Path,
    meta: InterviewMeta,
    turns: list[TranscriptTurn],
    report: DebriefReport,
    *,
    backup_existing: bool = False,
) -> Path | None:
    """渲染并写入三份派生报告（summary.json/transcript.md/qa-review.md），可选先备份旧文件。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered = {
        "summary.json": json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        "transcript.md": render_transcript(meta, turns),
        "qa-review.md": render_review(meta, report),
    }
    backup_dir = _backup_existing_reports(output_dir) if backup_existing else None
    for name, contents in rendered.items():
        (output_dir / name).write_text(contents, encoding="utf-8")
    return backup_dir


def _backup_existing_reports(output_dir: Path) -> Path | None:
    """将已有派生报告复制到 backups/reanalysis-<时间戳>/ 子目录，无文件可备份时返回 None。"""
    existing = [output_dir / name for name in DERIVED_REPORT_FILES if (output_dir / name).is_file()]
    if not existing:
        return None
    backups_dir = output_dir / "backups"
    stamp = _backup_stamp()
    backup_dir = backups_dir / f"reanalysis-{stamp}"
    suffix = 2
    while backup_dir.exists():
        backup_dir = backups_dir / f"reanalysis-{stamp}-{suffix}"
        suffix += 1
    backup_dir.mkdir(parents=True)
    for source in existing:
        shutil.copy2(source, backup_dir / source.name)
    return backup_dir


def _backup_stamp() -> str:
    """生成备份目录使用的时间戳字符串（格式：YYYYMMDD-HHMMSS）。"""
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def render_transcript(meta: InterviewMeta, turns: list[TranscriptTurn]) -> str:
    """将说话人 turns 渲染为 Markdown 完整对话格式，包含时间戳标记。"""
    lines = [f"# {meta.title} 完整对话", ""]
    for turn in turns:
        timestamp = _timestamp(turn.start_ms)
        prefix = f"**{turn.speaker}**"
        if timestamp:
            prefix += f" `{timestamp}`"
        lines.append(f"{prefix}: {turn.text}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_review(meta: InterviewMeta, report: DebriefReport) -> str:
    """将复盘报告渲染为 Markdown 问答复盘格式，包含角色判断、每题分析和整体总结。"""
    role_mapping = report.role_mapping
    lines = [
        f"# {meta.title} 问答复盘",
        "",
        "## 角色判断",
        "",
        f"- 置信度：{role_mapping.confidence:.2f}",
        f"- 判断依据：{role_mapping.reason}",
    ]
    if role_mapping.interviewer is None or role_mapping.candidate is None:
        lines.append("- 角色状态：无法可靠判断面试官与候选人")
    for speaker, role in role_mapping.speaker_roles.items():
        lines.append(f"- {speaker}：{role}")
    lines.extend(
        [
            "",
            "## 问题列表与回答复盘",
            "",
        ]
    )
    if not report.questions:
        lines.extend(["暂无明确问答对。", ""])
    for index, item in enumerate(report.questions, start=1):
        lines.extend(
            [
                f"### {index}. {item.question}",
                "",
                "**回答内容**",
                "",
                item.answer or "未识别到候选人回答。",
                "",
                "**回答缺陷**",
                "",
                *_bullet_list(item.defects),
                "",
                "**优化建议**",
                "",
                *_bullet_list(item.suggestions),
                "",
                "**后续学习点**",
                "",
                *_bullet_list(item.learning_points),
                "",
            ]
        )
    lines.extend(["## 整体缺陷", "", *_bullet_list(report.overall_defects), ""])
    lines.extend(["## 整体优化建议", "", *_bullet_list(report.overall_suggestions), ""])
    lines.extend(["## 后续学习点", "", *_bullet_list(report.learning_points), ""])
    return "\n".join(lines).rstrip() + "\n"


def _bullet_list(items: list[str]) -> list[str]:
    """将字符串列表格式化为 Markdown 无序列表，列表为空时返回默认占位项。"""
    if not items:
        return ["- 暂无"]
    return [f"- {item}" for item in items]


def _timestamp(ms: int | None) -> str | None:
    """将毫秒时间戳格式化为 MM:SS 或 HH:MM:SS，None 时返回 None。"""
    if ms is None:
        return None
    total_seconds = max(0, ms // 1000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

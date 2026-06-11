from __future__ import annotations

import json
from pathlib import Path

from interview_voice_diarizer.models import DebriefReport, InterviewMeta, TranscriptTurn


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def render_transcript(meta: InterviewMeta, turns: list[TranscriptTurn]) -> str:
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
    lines = [
        f"# {meta.title} 问答复盘",
        "",
        "## 角色判断",
        "",
        f"- 置信度：{report.role_mapping.confidence:.2f}",
        f"- 判断依据：{report.role_mapping.reason}",
        "",
        "## 问题列表与回答复盘",
        "",
    ]
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
    if not items:
        return ["- 暂无"]
    return [f"- {item}" for item in items]


def _timestamp(ms: int | None) -> str | None:
    if ms is None:
        return None
    total_seconds = max(0, ms // 1000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

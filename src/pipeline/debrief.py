"""Shared ASR post-processing for new and historical runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from errors import IvdError
from models import DebriefReport, InterviewMeta, SpeakerDiagnostics, TranscriptTurn
from pipeline.analysis import analyze_interview
from pipeline.transcript import (
    normalize_asr_turns,
    relabel_turns,
    validate_speaker_normalization,
)
from providers.volcengine import VolcArkClient


@dataclass(frozen=True)
class ProcessedDebrief:
    diagnostics: SpeakerDiagnostics
    turns: list[TranscriptTurn]
    labeled_turns: list[TranscriptTurn]
    report: DebriefReport


def load_raw_asr(path: Path) -> dict[str, Any]:
    """从历史 raw-asr.json 文件加载原始 ASR 结果，文件不存在或格式非法时抛出 IvdError。"""
    path = path.expanduser().resolve()
    if not path.exists():
        raise IvdError(f"历史 ASR 文件不存在：{path}")
    if not path.is_file():
        raise IvdError(f"历史 ASR 路径不是文件：{path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise IvdError(f"历史 ASR 文件不是合法 JSON：{path}") from exc
    except OSError as exc:
        raise IvdError(f"无法读取历史 ASR 文件：{path}") from exc
    if not isinstance(data, dict):
        raise IvdError(f"历史 ASR 内容必须是 JSON 对象：{path}")
    return data


def process_raw_asr(
    raw_asr: dict[str, Any],
    meta: InterviewMeta,
    ark_client: VolcArkClient | None,
) -> ProcessedDebrief:
    """对 ASR 原始结果执行完整后处理：标准化、校验、分析、角色重标记，返回 ProcessedDebrief。"""
    turns = normalize_asr_turns(raw_asr)
    diagnostics = validate_speaker_normalization(raw_asr, turns)
    if not turns:
        raise IvdError("火山 ASR 返回中没有识别到可用文本。")
    report = analyze_interview(turns, meta, ark_client)
    labeled_turns = relabel_turns(turns, report.role_mapping)
    return ProcessedDebrief(
        diagnostics=diagnostics,
        turns=turns,
        labeled_turns=labeled_turns,
        report=report,
    )

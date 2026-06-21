from __future__ import annotations

from collections import Counter
from typing import Any

from errors import IvdError
from models import RoleMapping, SpeakerDiagnostics, TranscriptTurn


def normalize_asr_turns(raw: dict[str, Any]) -> list[TranscriptTurn]:
    """将 ASR 原始响应解析为标准 TranscriptTurn 列表，优先使用 utterances，退化为纯文本。"""
    utterances = _find_utterances(raw)
    if utterances:
        turns = [_turn_from_utterance(item) for item in utterances]
        return [turn for turn in turns if turn.text]

    text = _find_text(raw)
    if text:
        return [TranscriptTurn(speaker="Speaker unknown", text=text.strip())]
    return []


def collect_speaker_diagnostics(
    raw: dict[str, Any], turns: list[TranscriptTurn]
) -> SpeakerDiagnostics:
    """统计原始 ASR 和标准化后的说话人分布，用于诊断展示。"""
    utterances = _find_utterances(raw)
    raw_counts = Counter(_speaker_label(_extract_speaker(item)) for item in utterances)
    normalized_counts = Counter(turn.speaker for turn in turns)
    return SpeakerDiagnostics(
        raw_counts=dict(raw_counts),
        normalized_counts=dict(normalized_counts),
    )


def validate_speaker_normalization(
    raw: dict[str, Any], turns: list[TranscriptTurn]
) -> SpeakerDiagnostics:
    """校验标准化后的说话人数量未发生异常折叠，多说话人被合并为一个时抛出 IvdError。"""
    diagnostics = collect_speaker_diagnostics(raw, turns)
    raw_count = diagnostics.raw_speaker_count
    normalized_count = diagnostics.normalized_speaker_count
    if raw_count >= 2 and normalized_count < 2:
        raise IvdError(
            "说话人标准化异常："
            f"ASR 原始结果包含 {raw_count} 个说话人，标准化后只剩 {normalized_count} 个。"
        )
    return diagnostics


def relabel_turns(turns: list[TranscriptTurn], roles: RoleMapping) -> list[TranscriptTurn]:
    """按角色映射将 turns 中的说话人 ID 替换为角色名（面试官/候选人）。"""
    return [
        turn.model_copy(update={"speaker": roles.role_for(turn.speaker) or turn.speaker})
        for turn in turns
    ]


def transcript_as_text(turns: list[TranscriptTurn], max_chars: int | None = None) -> str:
    """将 turns 渲染为 "说话人: 文本" 纯文本，超过 max_chars 时截断并附加省略提示。"""
    lines = []
    total = 0
    for turn in turns:
        line = f"{turn.speaker}: {turn.text.strip()}"
        if max_chars is not None and total + len(line) > max_chars:
            lines.append("...[内容过长，已截断]")
            break
        lines.append(line)
        total += len(line)
    return "\n".join(lines)


def _turn_from_utterance(item: dict[str, Any]) -> TranscriptTurn:
    """将单条 ASR utterance 字典转换为 TranscriptTurn，兼容多种字段命名方案。"""
    return TranscriptTurn(
        speaker=_speaker_label(_extract_speaker(item)),
        text=str(_first_present(item, "text", "utterance", "sentence") or "").strip(),
        start_ms=_optional_int(_first_present(item, "start_time", "start", "begin_time")),
        end_ms=_optional_int(_first_present(item, "end_time", "end")),
    )


def _extract_speaker(item: dict[str, Any]) -> Any:
    """从 utterance 字典中提取说话人 ID，同时检查顶层字段和 additions 子字典。"""
    speaker = _first_present(item, "speaker", "speaker_id", "speakerId", "spk", "user_id")
    if speaker is not None:
        return speaker
    additions = item.get("additions")
    if isinstance(additions, dict):
        return _first_present(
            additions,
            "speaker",
            "speaker_id",
            "speakerId",
            "spk",
            "user_id",
        )
    return None


def _speaker_label(speaker: Any) -> str:
    """将说话人原始值规范化为 'Speaker X' 格式，为空时返回 'Speaker unknown'。"""
    if speaker is None or str(speaker).strip() == "":
        return "Speaker unknown"
    speaker_label = str(speaker).strip()
    if speaker_label.lower().startswith("speaker"):
        return speaker_label
    return f"Speaker {speaker_label}"


def _first_present(value: dict[str, Any], *keys: str) -> Any:
    """返回字典中第一个非 None 值，所有 key 均缺失时返回 None。"""
    for key in keys:
        candidate = value.get(key)
        if candidate is not None:
            return candidate
    return None


def _find_utterances(value: Any) -> list[dict[str, Any]]:
    """递归遍历 ASR 响应树，查找第一个 utterances/segments/sentences 列表。"""
    if isinstance(value, dict):
        for key in ("utterances", "utterance", "segments", "sentences"):
            candidate = value.get(key)
            if _looks_like_utterances(candidate):
                return candidate
        for child in value.values():
            found = _find_utterances(child)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = _find_utterances(child)
            if found:
                return found
    return []


def _looks_like_utterances(value: Any) -> bool:
    """判断一个值是否为包含文本字段的 utterance 列表。"""
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, dict) for item in value)
        and any("text" in item or "utterance" in item or "sentence" in item for item in value)
    )


def _find_text(value: Any) -> str | None:
    """递归遍历 ASR 响应树，查找 text/result_text/transcript 纯文本字段。"""
    if isinstance(value, dict):
        for key in ("text", "result_text", "transcript"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate
        for child in value.values():
            found = _find_text(child)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = _find_text(child)
            if found:
                return found
    return None


def _optional_int(value: Any) -> int | None:
    """将值安全转换为 int，None 或无法转换时返回 None。"""
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None

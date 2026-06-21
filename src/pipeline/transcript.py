from __future__ import annotations

from collections import Counter
from typing import Any

from errors import IvdError
from models import RoleMapping, SpeakerDiagnostics, TranscriptTurn


def normalize_asr_turns(raw: dict[str, Any]) -> list[TranscriptTurn]:
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
    return [
        turn.model_copy(update={"speaker": roles.role_for(turn.speaker) or turn.speaker})
        for turn in turns
    ]


def transcript_as_text(turns: list[TranscriptTurn], max_chars: int | None = None) -> str:
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
    return TranscriptTurn(
        speaker=_speaker_label(_extract_speaker(item)),
        text=str(_first_present(item, "text", "utterance", "sentence") or "").strip(),
        start_ms=_optional_int(_first_present(item, "start_time", "start", "begin_time")),
        end_ms=_optional_int(_first_present(item, "end_time", "end")),
    )


def _extract_speaker(item: dict[str, Any]) -> Any:
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
    if speaker is None or str(speaker).strip() == "":
        return "Speaker unknown"
    speaker_label = str(speaker).strip()
    if speaker_label.lower().startswith("speaker"):
        return speaker_label
    return f"Speaker {speaker_label}"


def _first_present(value: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        candidate = value.get(key)
        if candidate is not None:
            return candidate
    return None


def _find_utterances(value: Any) -> list[dict[str, Any]]:
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
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, dict) for item in value)
        and any("text" in item or "utterance" in item or "sentence" in item for item in value)
    )


def _find_text(value: Any) -> str | None:
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
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None

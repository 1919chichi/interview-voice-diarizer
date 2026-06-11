from __future__ import annotations

from typing import Any

from interview_voice_diarizer.models import TranscriptTurn


def normalize_asr_turns(raw: dict[str, Any]) -> list[TranscriptTurn]:
    utterances = _find_utterances(raw)
    if utterances:
        turns = [_turn_from_utterance(item) for item in utterances]
        return [turn for turn in turns if turn.text]

    text = _find_text(raw)
    if text:
        return [TranscriptTurn(speaker="Speaker 0", text=text.strip())]
    return []


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
    speaker = item.get("speaker") or item.get("speaker_id") or item.get("speakerId")
    if speaker is None:
        speaker = item.get("spk") or item.get("user_id") or 0
    speaker_label = str(speaker)
    if not speaker_label.lower().startswith("speaker"):
        speaker_label = f"Speaker {speaker_label}"
    return TranscriptTurn(
        speaker=speaker_label,
        text=str(item.get("text") or item.get("utterance") or item.get("sentence") or "").strip(),
        start_ms=_optional_int(
            item.get("start_time") or item.get("start") or item.get("begin_time")
        ),
        end_ms=_optional_int(item.get("end_time") or item.get("end") or item.get("end_time")),
    )


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

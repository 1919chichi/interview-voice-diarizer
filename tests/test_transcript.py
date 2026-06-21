import pytest

from errors import IvdError
from models import RoleMapping, TranscriptTurn
from pipeline import transcript
from pipeline.transcript import normalize_asr_turns, relabel_turns, transcript_as_text


def test_normalize_asr_turns_from_nested_utterances() -> None:
    raw = {
        "result": {
            "utterances": [
                {"speaker": 0, "text": "请介绍一下项目", "start_time": 0, "end_time": 1000},
                {"speaker": 1, "text": "我负责订单系统", "start_time": 1000, "end_time": 3000},
            ]
        }
    }

    turns = normalize_asr_turns(raw)

    assert [turn.speaker for turn in turns] == ["Speaker 0", "Speaker 1"]
    assert turns[0].text == "请介绍一下项目"
    assert turns[1].start_ms == 1000


def test_normalize_asr_turns_reads_volcengine_additions_speaker() -> None:
    raw = {
        "result": {
            "utterances": [
                {
                    "additions": {"speaker": "1"},
                    "text": "请介绍一下项目",
                    "start_time": 0,
                    "end_time": 1000,
                },
                {
                    "additions": {"speaker": "2"},
                    "text": "我负责订单系统",
                    "start_time": 1000,
                    "end_time": 3000,
                },
            ]
        }
    }

    turns = normalize_asr_turns(raw)

    assert [turn.speaker for turn in turns] == ["Speaker 1", "Speaker 2"]
    assert turns[0].start_ms == 0


def test_normalize_asr_turns_preserves_zero_and_marks_missing_speaker_unknown() -> None:
    raw = {
        "result": {
            "utterances": [
                {"speaker": 0, "text": "第一个片段"},
                {"text": "第二个片段"},
            ]
        }
    }

    turns = normalize_asr_turns(raw)

    assert [turn.speaker for turn in turns] == ["Speaker 0", "Speaker unknown"]


def test_collect_speaker_diagnostics_counts_raw_and_normalized_speakers() -> None:
    raw = {
        "result": {
            "utterances": [
                {"additions": {"speaker": "1"}, "text": "问题"},
                {"additions": {"speaker": "2"}, "text": "回答"},
                {"additions": {"speaker": "2"}, "text": "补充"},
            ]
        }
    }
    turns = normalize_asr_turns(raw)

    diagnostics = transcript.collect_speaker_diagnostics(raw, turns)

    assert diagnostics.raw_counts == {"Speaker 1": 1, "Speaker 2": 2}
    assert diagnostics.normalized_counts == {"Speaker 1": 1, "Speaker 2": 2}


def test_validate_speaker_normalization_rejects_multi_speaker_collapse() -> None:
    raw = {
        "result": {
            "utterances": [
                {"additions": {"speaker": "1"}, "text": "问题"},
                {"additions": {"speaker": "2"}, "text": "回答"},
            ]
        }
    }
    collapsed = [TranscriptTurn(speaker="Speaker 0", text="问题回答")]

    with pytest.raises(IvdError, match="2 个说话人.*1 个"):
        transcript.validate_speaker_normalization(raw, collapsed)


def test_validate_speaker_normalization_ignores_unknown_as_distinct_raw_speaker() -> None:
    raw = {
        "result": {
            "utterances": [
                {"additions": {"speaker": "1"}, "text": "有效文本"},
                {"text": ""},
            ]
        }
    }
    turns = normalize_asr_turns(raw)

    diagnostics = transcript.validate_speaker_normalization(raw, turns)

    assert diagnostics.raw_counts == {"Speaker 1": 1, "Speaker unknown": 1}
    assert diagnostics.normalized_counts == {"Speaker 1": 1}
    assert diagnostics.raw_speaker_count == 1
    assert diagnostics.normalized_speaker_count == 1


def test_relabel_turns_uses_per_speaker_role_mapping() -> None:
    turns = [
        TranscriptTurn(speaker="Speaker 1", text="问题一"),
        TranscriptTurn(speaker="Speaker 2", text="回答一"),
        TranscriptTurn(speaker="Speaker 3", text="问题二"),
        TranscriptTurn(speaker="Speaker 4", text="回答二"),
    ]
    roles = RoleMapping(
        interviewer="Speaker 1",
        candidate="Speaker 2",
        speaker_roles={
            "Speaker 1": "面试官",
            "Speaker 2": "候选人",
            "Speaker 3": "面试官",
            "Speaker 4": "候选人",
        },
    )

    labeled = relabel_turns(turns, roles)

    assert [turn.speaker for turn in labeled] == ["面试官", "候选人", "面试官", "候选人"]


def test_transcript_as_text_can_truncate() -> None:
    raw = {"result": {"utterances": [{"speaker": 0, "text": "请介绍一下项目"}]}}
    turns = normalize_asr_turns(raw)

    text = transcript_as_text(turns, max_chars=5)

    assert "已截断" in text

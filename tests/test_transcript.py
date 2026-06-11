from interview_voice_diarizer.pipeline.transcript import normalize_asr_turns, transcript_as_text


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


def test_transcript_as_text_can_truncate() -> None:
    raw = {"result": {"utterances": [{"speaker": 0, "text": "请介绍一下项目"}]}}
    turns = normalize_asr_turns(raw)

    text = transcript_as_text(turns, max_chars=5)

    assert "已截断" in text

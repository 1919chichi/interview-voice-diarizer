import importlib.util
from pathlib import Path

import pytest

from errors import IvdError
from models import InterviewMeta
from pipeline import debrief


def test_debrief_pipeline_module_is_available() -> None:
    assert importlib.util.find_spec("pipeline.debrief") is not None


def test_load_raw_asr_reads_json_object(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw-asr.json"
    raw_path.write_text('{"result": {"text": "hello"}}', encoding="utf-8")

    assert debrief.load_raw_asr(raw_path) == {"result": {"text": "hello"}}


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("not json", "不是合法 JSON"),
        ("[]", "必须是 JSON 对象"),
    ],
)
def test_load_raw_asr_rejects_invalid_json(tmp_path: Path, contents: str, message: str) -> None:
    raw_path = tmp_path / "raw-asr.json"
    raw_path.write_text(contents, encoding="utf-8")

    with pytest.raises(IvdError, match=message):
        debrief.load_raw_asr(raw_path)


def test_load_raw_asr_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(IvdError, match="不存在"):
        debrief.load_raw_asr(tmp_path / "missing.json")


def test_process_raw_asr_returns_shared_diagnostics_and_reports() -> None:
    raw = {
        "result": {
            "utterances": [
                {"additions": {"speaker": "1"}, "text": "请介绍项目？"},
                {"additions": {"speaker": "2"}, "text": "我负责交易链路。"},
            ]
        }
    }

    processed = debrief.process_raw_asr(raw, InterviewMeta(company="示例公司"), None)

    assert processed.diagnostics.raw_speaker_count == 2
    assert processed.diagnostics.normalized_speaker_count == 2
    assert processed.report.role_mapping.interviewer == "Speaker 1"
    assert [turn.speaker for turn in processed.labeled_turns] == ["面试官", "候选人"]


def test_process_raw_asr_rejects_response_without_text() -> None:
    with pytest.raises(IvdError, match="没有识别到可用文本"):
        debrief.process_raw_asr({}, InterviewMeta(), None)

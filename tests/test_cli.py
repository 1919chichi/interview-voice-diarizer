import json
import tomllib
from pathlib import Path

from typer.testing import CliRunner

import cli
from errors import ApiError
from models import PreparedAudio, TranscriptTurn


def test_project_metadata_installs_flattened_cli_modules() -> None:
    pyproject_path = Path(__file__).parents[1] / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["ivd"] == "cli:app"
    wheel = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert wheel["sources"] == ["src"]
    assert "src/cli.py" in wheel["only-include"]
    assert "src/pipeline" in wheel["only-include"]


def test_debrief_stops_when_raw_speakers_collapse_during_normalization(
    monkeypatch, tmp_path: Path
) -> None:
    audio_path = tmp_path / "interview.mp3"
    audio_path.write_bytes(b"audio")
    output_dir = tmp_path / "out"
    raw = {
        "result": {
            "utterances": [
                {"additions": {"speaker": "1"}, "text": "问题"},
                {"additions": {"speaker": "2"}, "text": "回答"},
            ]
        }
    }

    class FakeAsrClient:
        def recognize_flash(self, path: Path, audio_format: str) -> dict:
            return raw

    monkeypatch.setattr(cli, "load_environment", lambda: None)
    monkeypatch.setattr(cli, "load_asr_config", lambda: object())
    monkeypatch.setattr(cli, "VolcAsrClient", lambda config: FakeAsrClient())
    monkeypatch.setattr(
        cli,
        "prepare_audio",
        lambda path, target: PreparedAudio(
            source_path=path,
            upload_path=path,
            audio_format="mp3",
            converted=False,
        ),
    )
    monkeypatch.setattr(
        "pipeline.debrief.normalize_asr_turns",
        lambda response: [TranscriptTurn(speaker="Speaker 0", text="问题回答")],
    )

    result = CliRunner().invoke(
        cli.app,
        [
            "debrief",
            str(audio_path),
            "--output-dir",
            str(output_dir),
            "--skip-analysis",
        ],
    )

    assert result.exit_code == 1
    assert "原始结果包含 2 个说话人，标准化后只剩 1 个" in result.output
    assert (output_dir / "raw-asr.json").exists()


def test_reanalyze_rebuilds_reports_without_asr_or_ark(monkeypatch, tmp_path: Path) -> None:
    raw_path = tmp_path / "raw-asr.json"
    raw_bytes = json.dumps(
        {
            "result": {
                "utterances": [
                    {"additions": {"speaker": "1"}, "text": "请介绍项目？"},
                    {"additions": {"speaker": "2"}, "text": "我负责交易链路。"},
                ]
            }
        },
        ensure_ascii=False,
    ).encode()
    raw_path.write_bytes(raw_bytes)
    for name in ("summary.json", "transcript.md", "qa-review.md"):
        (tmp_path / name).write_text(f"old {name}", encoding="utf-8")

    def fail_external_call(*args, **kwargs):
        raise AssertionError("skip-analysis 不应加载 ASR 或 Ark")

    monkeypatch.setattr(cli, "load_asr_config", fail_external_call)
    monkeypatch.setattr(cli, "load_ark_config", fail_external_call)
    monkeypatch.setattr(cli, "VolcAsrClient", fail_external_call)
    monkeypatch.setattr(cli, "VolcArkClient", fail_external_call)

    result = CliRunner().invoke(
        cli.app,
        [
            "reanalyze",
            str(raw_path),
            "--skip-analysis",
            "--company",
            "示例公司",
        ],
    )

    assert result.exit_code == 0, result.output
    assert raw_path.read_bytes() == raw_bytes
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["role_mapping"]["interviewer"] == "Speaker 1"
    assert summary["role_mapping"]["candidate"] == "Speaker 2"
    assert "# 示例公司 完整对话" in (tmp_path / "transcript.md").read_text(encoding="utf-8")
    backups = list((tmp_path / "backups").glob("reanalysis-*"))
    assert len(backups) == 1
    assert (backups[0] / "summary.json").read_text(encoding="utf-8") == "old summary.json"


def test_reanalyze_invalid_json_keeps_existing_reports(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw-asr.json"
    raw_path.write_text("not json", encoding="utf-8")
    summary_path = tmp_path / "summary.json"
    summary_path.write_text("old summary", encoding="utf-8")

    result = CliRunner().invoke(
        cli.app,
        ["reanalyze", str(raw_path), "--skip-analysis"],
    )

    assert result.exit_code == 1
    assert "不是合法 JSON" in result.output
    assert summary_path.read_text(encoding="utf-8") == "old summary"
    assert not (tmp_path / "backups").exists()


def test_reanalyze_model_failure_keeps_existing_reports(monkeypatch, tmp_path: Path) -> None:
    raw_path = tmp_path / "raw-asr.json"
    raw_path.write_text(
        json.dumps(
            {
                "result": {
                    "utterances": [
                        {"additions": {"speaker": "1"}, "text": "请介绍项目？"},
                        {"additions": {"speaker": "2"}, "text": "我负责交易链路。"},
                    ]
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    summary_path = tmp_path / "summary.json"
    summary_path.write_text("old summary", encoding="utf-8")

    class FailingArkClient:
        def chat_json(self, messages: list[dict[str, str]]) -> dict:
            raise ApiError("方舟暂时不可用")

    monkeypatch.setattr(cli, "load_ark_config", lambda: object())
    monkeypatch.setattr(cli, "VolcArkClient", lambda config: FailingArkClient())
    monkeypatch.setattr(
        cli,
        "VolcAsrClient",
        lambda config: (_ for _ in ()).throw(AssertionError("不应创建 ASR 客户端")),
    )

    result = CliRunner().invoke(cli.app, ["reanalyze", str(raw_path)])

    assert result.exit_code == 1
    assert "方舟暂时不可用" in result.output
    assert summary_path.read_text(encoding="utf-8") == "old summary"
    assert not (tmp_path / "backups").exists()


def test_readme_documents_history_reanalysis() -> None:
    readme = (Path(__file__).parents[1] / "README.md").read_text(encoding="utf-8")

    assert "ivd reanalyze" in readme
    assert "--skip-analysis" in readme
    assert "backups/reanalysis-" in readme

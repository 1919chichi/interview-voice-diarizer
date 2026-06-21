import tomllib
from pathlib import Path

from typer.testing import CliRunner

import cli
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
        cli,
        "normalize_asr_turns",
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

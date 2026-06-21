from pathlib import Path
from subprocess import CompletedProcess

import pytest

from errors import AudioError
from pipeline.audio import convert_to_mp3, prepare_audio


def test_prepare_audio_rejects_unknown_extension(tmp_path: Path) -> None:
    source = tmp_path / "interview.txt"
    source.write_text("not audio", encoding="utf-8")

    with pytest.raises(AudioError, match="不支持的录音格式"):
        prepare_audio(source, tmp_path / "out")


def test_prepare_audio_direct_mp3_upload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "interview.mp3"
    source.write_bytes(b"fake mp3")

    monkeypatch.setattr(
        "pipeline.audio.probe_audio",
        lambda path: {"format": {"duration": "12.5"}},
    )

    prepared = prepare_audio(source, tmp_path / "out")

    assert prepared.upload_path == source.resolve()
    assert prepared.audio_format == "mp3"
    assert prepared.converted is False
    assert prepared.duration_seconds == 12.5
    assert prepared.channels == 1


def test_prepare_audio_converts_m4a(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "interview.m4a"
    source.write_bytes(b"fake m4a")

    monkeypatch.setattr("pipeline.audio.probe_audio", lambda path: {"format": {}})

    called: dict[str, Path | int] = {}

    def fake_convert(input_path: Path, target_path: Path, channels: int) -> None:
        called["input"] = input_path
        called["target"] = target_path
        called["channels"] = channels
        target_path.write_bytes(b"mp3")

    monkeypatch.setattr("pipeline.audio.convert_to_mp3", fake_convert)

    prepared = prepare_audio(source, tmp_path / "out")

    assert called["input"] == source.resolve()
    assert prepared.upload_path.name == "converted.mp3"
    assert prepared.audio_format == "mp3"
    assert prepared.converted is True
    assert prepared.channels == 1
    assert called["channels"] == 1


def test_prepare_audio_preserves_two_channels_when_converting(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "interview.m4a"
    source.write_bytes(b"fake m4a")
    monkeypatch.setattr(
        "pipeline.audio.probe_audio",
        lambda path: {
            "format": {"duration": "30"},
            "streams": [{"codec_type": "audio", "channels": 2}],
        },
    )
    called: dict[str, int] = {}

    def fake_convert(input_path: Path, target_path: Path, channels: int) -> None:
        called["channels"] = channels
        target_path.write_bytes(b"mp3")

    monkeypatch.setattr("pipeline.audio.convert_to_mp3", fake_convert)

    prepared = prepare_audio(source, tmp_path / "out")

    assert called["channels"] == 2
    assert prepared.channels == 2


def test_convert_to_mp3_uses_requested_channel_count(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "source.m4a"
    target = tmp_path / "target.mp3"
    captured: dict[str, list[str]] = {}

    def fake_run(command: list[str], **kwargs) -> CompletedProcess:
        captured["command"] = command
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("pipeline.audio.ensure_audio_tools", lambda: None)
    monkeypatch.setattr("pipeline.audio.subprocess.run", fake_run)

    convert_to_mp3(source, target, channels=2)

    command = captured["command"]
    channel_flag = command.index("-ac")
    assert command[channel_flag + 1] == "2"

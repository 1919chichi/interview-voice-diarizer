from pathlib import Path

import pytest

from interview_voice_diarizer.audio import prepare_audio
from interview_voice_diarizer.errors import AudioError


def test_prepare_audio_rejects_unknown_extension(tmp_path: Path) -> None:
    source = tmp_path / "interview.txt"
    source.write_text("not audio", encoding="utf-8")

    with pytest.raises(AudioError, match="不支持的录音格式"):
        prepare_audio(source, tmp_path / "out")


def test_prepare_audio_direct_mp3_upload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "interview.mp3"
    source.write_bytes(b"fake mp3")

    monkeypatch.setattr(
        "interview_voice_diarizer.audio.probe_audio",
        lambda path: {"format": {"duration": "12.5"}},
    )

    prepared = prepare_audio(source, tmp_path / "out")

    assert prepared.upload_path == source.resolve()
    assert prepared.audio_format == "mp3"
    assert prepared.converted is False
    assert prepared.duration_seconds == 12.5


def test_prepare_audio_converts_m4a(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "interview.m4a"
    source.write_bytes(b"fake m4a")

    monkeypatch.setattr("interview_voice_diarizer.audio.probe_audio", lambda path: {"format": {}})

    called: dict[str, Path] = {}

    def fake_convert(input_path: Path, target_path: Path) -> None:
        called["input"] = input_path
        called["target"] = target_path
        target_path.write_bytes(b"mp3")

    monkeypatch.setattr("interview_voice_diarizer.audio.convert_to_mp3", fake_convert)

    prepared = prepare_audio(source, tmp_path / "out")

    assert called["input"] == source.resolve()
    assert prepared.upload_path.name == "converted.mp3"
    assert prepared.audio_format == "mp3"
    assert prepared.converted is True

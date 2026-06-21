from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from errors import AudioError
from models import PreparedAudio

DIRECT_UPLOAD_FORMATS = {"wav", "mp3", "ogg"}
CONVERTIBLE_FORMATS = {"m4a", "qma", "mp4", "aac", "flac"}


def ensure_audio_tools() -> None:
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        joined = ", ".join(missing)
        raise AudioError(f"缺少音频工具：{joined}。请先安装 ffmpeg。")


def probe_audio(path: Path) -> dict:
    ensure_audio_tools()
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AudioError(_probe_error(path, result.stderr.strip()))
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AudioError(f"无法解析 ffprobe 输出：{path}") from exc


def prepare_audio(source_path: Path, output_dir: Path) -> PreparedAudio:
    source_path = source_path.expanduser().resolve()
    if not source_path.exists():
        raise AudioError(f"录音文件不存在：{source_path}")
    if not source_path.is_file():
        raise AudioError(f"录音路径不是文件：{source_path}")

    suffix = source_path.suffix.lower().lstrip(".")
    if suffix not in DIRECT_UPLOAD_FORMATS | CONVERTIBLE_FORMATS:
        raise AudioError(f"不支持的录音格式：.{suffix}。请使用 m4a、qma、wav、mp3 或 ogg。")

    metadata = probe_audio(source_path)
    duration = _duration_seconds(metadata)
    channels = _audio_channels(metadata)

    output_dir.mkdir(parents=True, exist_ok=True)
    if suffix in DIRECT_UPLOAD_FORMATS:
        return PreparedAudio(
            source_path=source_path,
            upload_path=source_path,
            audio_format=suffix,
            converted=False,
            duration_seconds=duration,
            channels=channels,
        )

    converted_path = output_dir / "converted.mp3"
    convert_to_mp3(source_path, converted_path, channels=channels)
    return PreparedAudio(
        source_path=source_path,
        upload_path=converted_path,
        audio_format="mp3",
        converted=True,
        duration_seconds=duration,
        channels=channels,
    )


def convert_to_mp3(source_path: Path, target_path: Path, channels: int = 1) -> None:
    ensure_audio_tools()
    channels = min(max(channels, 1), 2)
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-vn",
            "-ac",
            str(channels),
            "-ar",
            "16000",
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "64k",
            str(target_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AudioError(_convert_error(source_path, result.stderr.strip()))


def _duration_seconds(metadata: dict) -> float | None:
    raw = metadata.get("format", {}).get("duration")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _audio_channels(metadata: dict) -> int:
    streams = metadata.get("streams", [])
    for stream in streams:
        if not isinstance(stream, dict):
            continue
        if stream.get("codec_type") not in {None, "audio"}:
            continue
        try:
            channels = int(stream.get("channels", 1))
        except (TypeError, ValueError):
            continue
        return min(max(channels, 1), 2)
    return 1


def _probe_error(path: Path, stderr: str) -> str:
    if path.suffix.lower() == ".qma":
        return (
            f"ffprobe 无法识别 .qma 文件：{path}。"
            "如果这是受保护或非标准音频，请先从录音来源导出为 m4a、mp3 或 wav。"
        )
    return f"ffprobe 无法识别音频文件：{path}。{stderr}"


def _convert_error(path: Path, stderr: str) -> str:
    if path.suffix.lower() == ".qma":
        return (
            f"ffmpeg 无法解码 .qma 文件：{path}。"
            "如果这是受保护或非标准音频，请先从录音来源导出为 m4a、mp3 或 wav。"
        )
    return f"音频转码失败：{path}。{stderr}"

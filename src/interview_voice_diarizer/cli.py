from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from interview_voice_diarizer.config import load_ark_config, load_asr_config, load_environment
from interview_voice_diarizer.errors import IvdError
from interview_voice_diarizer.models import InterviewMeta
from interview_voice_diarizer.output.report import render_review, render_transcript, write_json
from interview_voice_diarizer.pipeline.analysis import analyze_interview
from interview_voice_diarizer.pipeline.audio import prepare_audio
from interview_voice_diarizer.pipeline.transcript import normalize_asr_turns, relabel_turns
from interview_voice_diarizer.providers.volcengine import VolcArkClient, VolcAsrClient

app = typer.Typer(help="本地面试录音转写、说话人分离与复盘 CLI。")


@app.callback()
def main() -> None:
    """本地面试录音转写、说话人分离与复盘 CLI。"""


@app.command()
def debrief(
    audio_path: Annotated[Path, typer.Argument(help="本地录音文件路径。")],
    company: Annotated[str | None, typer.Option("--company", "-c", help="公司名。")] = None,
    role: Annotated[str | None, typer.Option("--role", "-r", help="岗位名。")] = None,
    round_name: Annotated[str | None, typer.Option("--round", help="面试轮次。")] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="输出目录，默认 outputs/<录音文件名>/。"),
    ] = None,
    mode: Annotated[
        str,
        typer.Option("--mode", help="识别模式：flash 使用本地文件；standard 使用 --audio-url。"),
    ] = "flash",
    audio_url: Annotated[
        str | None,
        typer.Option("--audio-url", help="标准版识别使用的公网音频 URL。"),
    ] = None,
    skip_analysis: Annotated[
        bool,
        typer.Option("--skip-analysis", help="跳过方舟模型分析，只生成启发式复盘。"),
    ] = False,
) -> None:
    load_environment()
    try:
        meta = InterviewMeta(company=company, role=role, round_name=round_name)
        target_dir = _resolve_output_dir(audio_path=audio_path, output_dir=output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        typer.echo(f"输出目录：{target_dir}")
        asr_config = load_asr_config()
        asr_client = VolcAsrClient(asr_config)

        if mode == "flash":
            prepared = prepare_audio(audio_path, target_dir)
            if prepared.converted:
                typer.echo(f"已转码：{prepared.upload_path}")
            typer.echo("开始调用火山语音识别极速版...")
            raw_asr = asr_client.recognize_flash(prepared.upload_path, prepared.audio_format)
        elif mode == "standard":
            if not audio_url:
                raise IvdError("standard 模式需要传入 --audio-url。")
            typer.echo("开始提交火山语音识别标准版任务...")
            raw_asr = asr_client.submit_url_and_poll(audio_url, _guess_audio_format(audio_url))
        else:
            raise IvdError("--mode 只支持 flash 或 standard。")

        write_json(target_dir / "raw-asr.json", raw_asr)
        turns = normalize_asr_turns(raw_asr)
        if not turns:
            raise IvdError("火山 ASR 返回中没有识别到可用文本。raw-asr.json 已保存供排查。")

        ark_client = None if skip_analysis else VolcArkClient(load_ark_config())
        typer.echo("开始生成面试复盘...")
        report = analyze_interview(turns, meta, ark_client)

        labeled_turns = relabel_turns(turns, report.role_mapping)
        write_json(target_dir / "summary.json", report.model_dump(mode="json"))
        (target_dir / "transcript.md").write_text(render_transcript(meta, labeled_turns), encoding="utf-8")
        (target_dir / "qa-review.md").write_text(render_review(meta, report), encoding="utf-8")

        typer.echo("完成：")
        typer.echo(f"- {target_dir / 'transcript.md'}")
        typer.echo(f"- {target_dir / 'qa-review.md'}")
        typer.echo(f"- {target_dir / 'summary.json'}")
        typer.echo(f"- {target_dir / 'raw-asr.json'}")
    except IvdError as exc:
        typer.secho(f"错误：{exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc


def _resolve_output_dir(audio_path: Path, output_dir: Path | None) -> Path:
    if output_dir:
        return output_dir.expanduser().resolve()
    stem = audio_path.expanduser().name
    if "." in stem:
        stem = ".".join(stem.split(".")[:-1])
    return (Path.cwd() / "outputs" / stem).resolve()


def _guess_audio_format(audio_url: str) -> str:
    suffix = audio_url.rsplit("?", 1)[0].rsplit(".", 1)[-1].lower()
    if suffix in {"wav", "mp3", "ogg"}:
        return suffix
    return "mp3"

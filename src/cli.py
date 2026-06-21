from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from config import load_ark_config, load_asr_config, load_environment
from errors import IvdError
from models import InterviewMeta
from output.report import write_debrief_outputs, write_json
from pipeline.audio import prepare_audio
from pipeline.debrief import ProcessedDebrief, load_raw_asr, process_raw_asr
from providers.volcengine import VolcArkClient, VolcAsrClient

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
    """执行完整面试复盘流程：识别录音、生成转写和分析报告。"""
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
        ark_client = None if skip_analysis else VolcArkClient(load_ark_config())
        typer.echo("开始生成面试复盘...")
        processed = process_raw_asr(raw_asr, meta, ark_client)
        _echo_diagnostics(processed)
        write_debrief_outputs(
            target_dir,
            meta,
            processed.labeled_turns,
            processed.report,
        )
        _echo_report_paths(target_dir)
        typer.echo(f"- {target_dir / 'raw-asr.json'}")
    except IvdError as exc:
        typer.secho(f"错误：{exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc


@app.command()
def reanalyze(
    raw_asr_path: Annotated[Path, typer.Argument(help="历史 raw-asr.json 文件路径。")],
    company: Annotated[str | None, typer.Option("--company", "-c", help="公司名。")] = None,
    role: Annotated[str | None, typer.Option("--role", "-r", help="岗位名。")] = None,
    round_name: Annotated[str | None, typer.Option("--round", help="面试轮次。")] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="输出目录，默认 raw-asr.json 所在目录。"),
    ] = None,
    skip_analysis: Annotated[
        bool,
        typer.Option("--skip-analysis", help="跳过方舟模型分析，只生成启发式复盘。"),
    ] = False,
) -> None:
    """从历史 raw-asr.json 重新生成面试复盘，不重新调用 ASR。"""
    load_environment()
    try:
        source_path = raw_asr_path.expanduser().resolve()
        target_dir = (
            output_dir.expanduser().resolve() if output_dir is not None else source_path.parent
        )
        typer.echo(f"历史 ASR：{source_path}")
        typer.echo(f"输出目录：{target_dir}")
        raw_asr = load_raw_asr(source_path)
        meta = InterviewMeta(company=company, role=role, round_name=round_name)
        ark_client = None if skip_analysis else VolcArkClient(load_ark_config())
        typer.echo("开始重新生成面试复盘（不会调用 ASR）...")
        processed = process_raw_asr(raw_asr, meta, ark_client)
        _echo_diagnostics(processed)
        backup_dir = write_debrief_outputs(
            target_dir,
            meta,
            processed.labeled_turns,
            processed.report,
            backup_existing=True,
        )
        if backup_dir is not None:
            typer.echo(f"旧报告备份：{backup_dir}")
        _echo_report_paths(target_dir)
    except IvdError as exc:
        typer.secho(f"错误：{exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc


def _echo_diagnostics(processed: ProcessedDebrief) -> None:
    """打印说话人诊断信息到终端。"""
    diagnostics = processed.diagnostics
    typer.echo(
        "说话人诊断："
        f"ASR {diagnostics.raw_speaker_count} 个，"
        f"标准化 {diagnostics.normalized_speaker_count} 个。"
    )


def _echo_report_paths(target_dir: Path) -> None:
    """打印生成的报告文件路径到终端。"""
    typer.echo("完成：")
    typer.echo(f"- {target_dir / 'transcript.md'}")
    typer.echo(f"- {target_dir / 'qa-review.md'}")
    typer.echo(f"- {target_dir / 'summary.json'}")


def _resolve_output_dir(audio_path: Path, output_dir: Path | None) -> Path:
    """根据录音路径或用户指定推导输出目录。"""
    if output_dir:
        return output_dir.expanduser().resolve()
    stem = audio_path.expanduser().name
    if "." in stem:
        stem = ".".join(stem.split(".")[:-1])
    return (Path.cwd() / "outputs" / stem).resolve()


def _guess_audio_format(audio_url: str) -> str:
    """从 URL 后缀猜测音频格式，未识别时回退到 mp3。"""
    suffix = audio_url.rsplit("?", 1)[0].rsplit(".", 1)[-1].lower()
    if suffix in {"wav", "mp3", "ogg"}:
        return suffix
    return "mp3"

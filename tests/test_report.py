import json
from pathlib import Path

import output.report as report_output
from models import (
    DebriefReport,
    InterviewMeta,
    QuestionReview,
    RoleMapping,
    TranscriptTurn,
)
from output.report import render_review, render_transcript


def test_render_transcript() -> None:
    markdown = render_transcript(
        InterviewMeta(company="示例公司", role="后端", round_name="一面"),
        [TranscriptTurn(speaker="Speaker 0", text="请介绍一下项目", start_ms=1000)],
    )

    assert "# 示例公司 / 后端 / 一面 完整对话" in markdown
    assert "**Speaker 0** `00:01`: 请介绍一下项目" in markdown


def test_render_review() -> None:
    report = DebriefReport(
        role_mapping=RoleMapping(interviewer="Speaker 0", candidate="Speaker 1"),
        questions=[
            QuestionReview(
                question="请介绍项目？",
                answer="我负责交易链路。",
                defects=["缺少量化结果"],
                suggestions=["补充 QPS 和耗时变化"],
                learning_points=["复习事务消息"],
            )
        ],
    )

    markdown = render_review(InterviewMeta(company="示例公司"), report)

    assert "## 角色判断" in markdown
    assert "### 1. 请介绍项目？" in markdown
    assert "- 缺少量化结果" in markdown


def test_render_review_lists_all_speaker_role_assignments() -> None:
    report = DebriefReport(
        role_mapping=RoleMapping(
            interviewer="Speaker 1",
            candidate="Speaker 2",
            speaker_roles={
                "Speaker 1": "面试官",
                "Speaker 2": "候选人",
                "Speaker 3": "面试官",
                "Speaker 4": "候选人",
            },
        )
    )

    markdown = render_review(InterviewMeta(), report)

    assert "- Speaker 1：面试官" in markdown
    assert "- Speaker 2：候选人" in markdown
    assert "- Speaker 3：面试官" in markdown
    assert "- Speaker 4：候选人" in markdown


def test_render_review_marks_indeterminate_single_speaker_roles() -> None:
    report = DebriefReport(
        role_mapping=RoleMapping(
            speaker_roles={"Speaker 0": "未知"},
            confidence=0.2,
            reason="仅识别到一个说话人。",
        )
    )

    markdown = render_review(InterviewMeta(), report)

    assert "- 角色状态：无法可靠判断面试官与候选人" in markdown
    assert "- Speaker 0：未知" in markdown


def _sample_report() -> DebriefReport:
    return DebriefReport(
        role_mapping=RoleMapping(
            interviewer="Speaker 1",
            candidate="Speaker 2",
            speaker_roles={"Speaker 1": "面试官", "Speaker 2": "候选人"},
        )
    )


def test_write_debrief_outputs_does_not_create_empty_backup(tmp_path: Path) -> None:
    backup_dir = report_output.write_debrief_outputs(
        tmp_path,
        InterviewMeta(company="示例公司"),
        [TranscriptTurn(speaker="面试官", text="问题")],
        _sample_report(),
        backup_existing=True,
    )

    assert backup_dir is None
    assert not (tmp_path / "backups").exists()
    assert (
        json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))["role_mapping"][
            "interviewer"
        ]
        == "Speaker 1"
    )
    assert "# 示例公司 完整对话" in (tmp_path / "transcript.md").read_text(encoding="utf-8")


def test_write_debrief_outputs_backs_up_existing_reports(monkeypatch, tmp_path: Path) -> None:
    old_contents = {
        "summary.json": '{"old": true}',
        "transcript.md": "old transcript",
        "qa-review.md": "old review",
    }
    for name, contents in old_contents.items():
        (tmp_path / name).write_text(contents, encoding="utf-8")
    monkeypatch.setattr(
        report_output,
        "_backup_stamp",
        lambda: "20260621-120000",
        raising=False,
    )

    backup_dir = report_output.write_debrief_outputs(
        tmp_path,
        InterviewMeta(),
        [TranscriptTurn(speaker="面试官", text="new transcript")],
        _sample_report(),
        backup_existing=True,
    )

    assert backup_dir == tmp_path / "backups" / "reanalysis-20260621-120000"
    for name, contents in old_contents.items():
        assert (backup_dir / name).read_text(encoding="utf-8") == contents
    assert "new transcript" in (tmp_path / "transcript.md").read_text(encoding="utf-8")


def test_write_debrief_outputs_uses_unique_backup_directory(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        report_output,
        "_backup_stamp",
        lambda: "20260621-120000",
        raising=False,
    )
    (tmp_path / "summary.json").write_text("first", encoding="utf-8")
    first = report_output.write_debrief_outputs(
        tmp_path,
        InterviewMeta(),
        [],
        _sample_report(),
        backup_existing=True,
    )
    (tmp_path / "summary.json").write_text("second", encoding="utf-8")

    second = report_output.write_debrief_outputs(
        tmp_path,
        InterviewMeta(),
        [],
        _sample_report(),
        backup_existing=True,
    )

    assert first is not None
    assert second is not None
    assert first != second
    assert (first / "summary.json").read_text(encoding="utf-8") == "first"
    assert (second / "summary.json").read_text(encoding="utf-8") == "second"

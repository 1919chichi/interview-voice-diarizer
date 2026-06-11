from interview_voice_diarizer.analysis import heuristic_report, infer_roles
from interview_voice_diarizer.models import TranscriptTurn


def test_infer_roles_by_question_and_answer_pattern() -> None:
    turns = [
        TranscriptTurn(speaker="Speaker 0", text="请介绍一下你的项目？"),
        TranscriptTurn(speaker="Speaker 1", text="我负责交易链路，实现了库存扣减和消息补偿。"),
        TranscriptTurn(speaker="Speaker 0", text="你怎么解决并发问题？"),
        TranscriptTurn(speaker="Speaker 1", text="我们使用 Redis 和数据库唯一约束做防重。"),
    ]

    roles = infer_roles(turns)

    assert roles.interviewer == "Speaker 0"
    assert roles.candidate == "Speaker 1"
    assert roles.confidence > 0.5


def test_heuristic_report_extracts_question_answer_pair() -> None:
    turns = [
        TranscriptTurn(speaker="Speaker 0", text="请介绍一下你的项目？"),
        TranscriptTurn(speaker="Speaker 1", text="我负责交易链路。"),
    ]

    report = heuristic_report(turns)

    assert report.questions[0].question == "请介绍一下你的项目？"
    assert report.questions[0].answer == "我负责交易链路。"

from models import InterviewMeta, TranscriptTurn
from pipeline.analysis import analyze_interview, heuristic_report, infer_roles


class FakeArkClient:
    def __init__(self, response: dict) -> None:
        self.response = response

    def chat_json(self, messages: list[dict[str, str]]) -> dict:
        return self.response


def _llm_report(role_mapping: dict) -> dict:
    return {
        "role_mapping": role_mapping,
        "questions": [],
        "overall_defects": [],
        "overall_suggestions": [],
        "learning_points": [],
    }


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
    assert roles.speaker_roles == {"Speaker 0": "面试官", "Speaker 1": "候选人"}
    assert roles.confidence > 0.5


def test_infer_roles_aggregates_multiple_speaker_clusters() -> None:
    turns = [
        TranscriptTurn(speaker="Speaker 1", text="请介绍一下你的项目？"),
        TranscriptTurn(speaker="Speaker 2", text="我负责交易链路，实现了库存扣减。"),
        TranscriptTurn(speaker="Speaker 3", text="你怎么解决并发问题？"),
        TranscriptTurn(speaker="Speaker 4", text="我们使用 Redis 和唯一约束做防重。"),
    ]

    roles = infer_roles(turns)

    assert roles.interviewer == "Speaker 1"
    assert roles.candidate == "Speaker 2"
    assert roles.speaker_roles == {
        "Speaker 1": "面试官",
        "Speaker 2": "候选人",
        "Speaker 3": "面试官",
        "Speaker 4": "候选人",
    }


def test_infer_roles_does_not_assign_one_speaker_to_both_roles() -> None:
    turns = [TranscriptTurn(speaker="Speaker 0", text="请介绍项目？我负责交易链路。")]

    roles = infer_roles(turns)

    assert roles.interviewer is None
    assert roles.candidate is None
    assert roles.speaker_roles == {"Speaker 0": "未知"}
    assert roles.confidence <= 0.3


def test_heuristic_report_extracts_question_answer_pair() -> None:
    turns = [
        TranscriptTurn(speaker="Speaker 0", text="请介绍一下你的项目？"),
        TranscriptTurn(speaker="Speaker 1", text="我负责交易链路。"),
    ]

    report = heuristic_report(turns)

    assert report.questions[0].question == "请介绍一下你的项目？"
    assert report.questions[0].answer == "我负责交易链路。"


def test_heuristic_report_groups_answers_from_multiple_candidate_clusters() -> None:
    turns = [
        TranscriptTurn(speaker="Speaker 1", text="请介绍一下你的项目？"),
        TranscriptTurn(speaker="Speaker 2", text="我负责交易链路。"),
        TranscriptTurn(speaker="Speaker 4", text="还实现了库存扣减。"),
    ]

    report = heuristic_report(turns)

    assert report.questions[0].answer == "我负责交易链路。\n还实现了库存扣减。"


def test_analyze_interview_rejects_model_mapping_with_unknown_speaker() -> None:
    turns = [
        TranscriptTurn(speaker="Speaker 0", text="请介绍项目？"),
        TranscriptTurn(speaker="Speaker 1", text="我负责交易链路。"),
    ]
    response = _llm_report(
        {
            "interviewer": "Speaker 0（提问方）",
            "candidate": "Speaker 1",
            "speaker_roles": {
                "Speaker 0（提问方）": "面试官",
                "Speaker 1": "候选人",
            },
            "confidence": 0.9,
            "reason": "模型判断",
        }
    )

    report = analyze_interview(turns, InterviewMeta(), FakeArkClient(response))

    assert report.role_mapping.interviewer == "Speaker 0"
    assert report.role_mapping.candidate == "Speaker 1"
    assert "Speaker 0（提问方）" not in report.role_mapping.speaker_roles


def test_analyze_interview_fills_model_mapping_missing_known_speaker() -> None:
    turns = [
        TranscriptTurn(speaker="Speaker 0", text="请介绍项目？"),
        TranscriptTurn(speaker="Speaker 1", text="我负责交易链路。"),
    ]
    response = _llm_report(
        {
            "interviewer": "Speaker 0",
            "candidate": "Speaker 1",
            "speaker_roles": {"Speaker 0": "面试官"},
            "confidence": 0.9,
            "reason": "模型判断",
        }
    )

    report = analyze_interview(turns, InterviewMeta(), FakeArkClient(response))

    assert report.role_mapping.speaker_roles == {
        "Speaker 0": "面试官",
        "Speaker 1": "候选人",
    }
    assert report.role_mapping.confidence == 0.9


def test_analyze_interview_rejects_same_speaker_for_both_role_anchors() -> None:
    turns = [
        TranscriptTurn(speaker="Speaker 0", text="请介绍项目？"),
        TranscriptTurn(speaker="Speaker 1", text="我负责交易链路。"),
    ]
    response = _llm_report(
        {
            "interviewer": "Speaker 0",
            "candidate": "Speaker 0",
            "speaker_roles": {"Speaker 0": "面试官", "Speaker 1": "候选人"},
            "confidence": 0.9,
            "reason": "模型判断",
        }
    )

    report = analyze_interview(turns, InterviewMeta(), FakeArkClient(response))

    assert report.role_mapping.interviewer == "Speaker 0"
    assert report.role_mapping.candidate == "Speaker 1"
    assert report.role_mapping.confidence == 0.75

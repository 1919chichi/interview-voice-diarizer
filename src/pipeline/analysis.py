from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import ValidationError

from models import (
    DebriefReport,
    InterviewMeta,
    QuestionReview,
    RoleMapping,
    TranscriptTurn,
)
from pipeline.transcript import transcript_as_text
from providers.volcengine import VolcArkClient

QUESTION_MARKERS = (
    "?",
    "？",
    "介绍",
    "说一下",
    "讲一下",
    "聊一下",
    "为什么",
    "怎么",
    "如何",
    "什么",
)
ANSWER_MARKERS = ("我", "我们", "项目", "负责", "实现", "遇到", "优化", "使用", "经验")


def infer_roles(turns: list[TranscriptTurn]) -> RoleMapping:
    if not turns:
        return RoleMapping()

    question_counts: Counter[str] = Counter()
    answer_counts: Counter[str] = Counter()
    char_counts: Counter[str] = Counter()
    for turn in turns:
        text = turn.text
        char_counts[turn.speaker] += len(text)
        if any(marker in text for marker in QUESTION_MARKERS):
            question_counts[turn.speaker] += 1
        if any(marker in text for marker in ANSWER_MARKERS):
            answer_counts[turn.speaker] += 1

    speakers = sorted(char_counts, key=lambda speaker: char_counts[speaker], reverse=True)
    if len(speakers) == 1:
        return RoleMapping(interviewer=speakers[0], candidate=speakers[0], confidence=0.3)

    interviewer = max(
        speakers,
        key=lambda speaker: question_counts[speaker] - answer_counts[speaker],
    )
    candidate = max(
        [speaker for speaker in speakers if speaker != interviewer],
        key=lambda speaker: answer_counts[speaker] + char_counts[speaker] / 500,
    )
    confidence = 0.75 if question_counts[interviewer] > 0 else 0.55
    return RoleMapping(
        interviewer=interviewer,
        candidate=candidate,
        confidence=confidence,
        reason="面试官通常提问更多，候选人通常回答更长且包含项目/负责/实现等表述。",
    )


def analyze_interview(
    turns: list[TranscriptTurn],
    meta: InterviewMeta,
    ark_client: VolcArkClient | None,
) -> DebriefReport:
    fallback = heuristic_report(turns)
    if ark_client is None:
        return fallback

    messages = [
        {
            "role": "system",
            "content": (
                "你是资深技术面试复盘助手。你必须只输出合法 JSON，不能输出 Markdown。"
                "请判断每个 Speaker 的角色，并整理问题、回答内容、回答缺陷、优化建议、后续学习点。"
            ),
        },
        {
            "role": "user",
            "content": _analysis_prompt(turns=turns, meta=meta, fallback=fallback),
        },
    ]
    data = ark_client.chat_json(messages)
    try:
        return DebriefReport.model_validate(data)
    except ValidationError:
        merged = fallback.model_dump()
        merged.update(_compatible_report_data(data))
        return DebriefReport.model_validate(merged)


def heuristic_report(turns: list[TranscriptTurn]) -> DebriefReport:
    role_mapping = infer_roles(turns)
    grouped_answers = _group_question_answers(turns, role_mapping)
    questions = [
        QuestionReview(
            question=item["question"],
            answer=item["answer"],
            defects=["未经过模型深度分析；请配置 VOLC_ARK_API_KEY 后重新运行以获取更准确缺陷。"],
            suggestions=["补充 STAR 结构、技术细节、量化结果和权衡过程。"],
            learning_points=["复盘该问题涉及的核心技术点，并准备 2-3 分钟结构化回答。"],
        )
        for item in grouped_answers
    ]
    return DebriefReport(
        role_mapping=role_mapping,
        questions=questions,
        overall_defects=[] if questions else ["未识别到明确问答对。"],
        overall_suggestions=["建议配置火山方舟模型生成完整复盘。"],
        learning_points=[],
    )


def _group_question_answers(
    turns: list[TranscriptTurn],
    roles: RoleMapping,
) -> list[dict[str, str]]:
    pairs: list[dict[str, str]] = []
    current_question: str | None = None
    answer_parts: list[str] = []
    for turn in turns:
        is_interviewer_question = turn.speaker == roles.interviewer and any(
            marker in turn.text for marker in QUESTION_MARKERS
        )
        if is_interviewer_question:
            if current_question:
                pairs.append(
                    {"question": current_question, "answer": "\n".join(answer_parts).strip()}
                )
            current_question = turn.text
            answer_parts = []
        elif current_question and turn.speaker == roles.candidate:
            answer_parts.append(turn.text)
    if current_question:
        pairs.append({"question": current_question, "answer": "\n".join(answer_parts).strip()})
    return pairs


def _analysis_prompt(
    turns: list[TranscriptTurn],
    meta: InterviewMeta,
    fallback: DebriefReport,
) -> str:
    return f"""
面试信息：{meta.title}

请基于下面的说话人转写，输出 JSON，结构必须匹配：
{{
  "role_mapping": {{
    "interviewer": "Speaker 0",
    "candidate": "Speaker 1",
    "confidence": 0.0,
    "reason": "判断依据"
  }},
  "questions": [
    {{
      "question": "面试官问题",
      "answer": "候选人回答",
      "defects": ["回答缺陷"],
      "suggestions": ["优化建议"],
      "learning_points": ["后续学习点"]
    }}
  ],
  "overall_defects": ["整体缺陷"],
  "overall_suggestions": ["整体建议"],
  "learning_points": ["后续学习点"]
}}

启发式初判：
{fallback.role_mapping.model_dump_json(ensure_ascii=False)}

转写文本：
{transcript_as_text(turns, max_chars=60000)}
""".strip()


def _compatible_report_data(data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if isinstance(data.get("role_mapping"), dict):
        result["role_mapping"] = data["role_mapping"]
    if isinstance(data.get("questions"), list):
        result["questions"] = data["questions"]
    for key in ("overall_defects", "overall_suggestions", "learning_points"):
        if isinstance(data.get(key), list):
            result[key] = data[key]
    return result

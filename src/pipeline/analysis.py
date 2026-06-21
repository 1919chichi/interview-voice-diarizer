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
    """基于问答词频启发式推断每个 Speaker 的面试角色（面试官/候选人）。"""
    if not turns:
        return RoleMapping()

    question_counts: Counter[str] = Counter()
    answer_counts: Counter[str] = Counter()
    char_counts: Counter[str] = Counter()
    for turn in turns:
        text = turn.text
        char_counts[turn.speaker] += len(text)
        is_question = any(marker in text for marker in QUESTION_MARKERS)
        if is_question:
            question_counts[turn.speaker] += 1
        elif any(marker in text for marker in ANSWER_MARKERS):
            answer_counts[turn.speaker] += 1

    speakers = list(char_counts)
    if len(speakers) == 1:
        return RoleMapping(
            speaker_roles={speakers[0]: "未知"},
            confidence=0.2,
            reason="仅识别到一个说话人，无法可靠区分面试官与候选人。",
        )

    speaker_roles: dict[str, str] = {}
    for speaker in speakers:
        if question_counts[speaker] > answer_counts[speaker]:
            speaker_roles[speaker] = "面试官"
        elif answer_counts[speaker] > question_counts[speaker]:
            speaker_roles[speaker] = "候选人"
        else:
            speaker_roles[speaker] = "未知"

    if "面试官" not in speaker_roles.values():
        interviewer = max(
            speakers,
            key=lambda speaker: question_counts[speaker] - answer_counts[speaker],
        )
        speaker_roles[interviewer] = "面试官"
    if "候选人" not in speaker_roles.values():
        interviewer_speakers = {
            speaker for speaker, role in speaker_roles.items() if role == "面试官"
        }
        candidates = [speaker for speaker in speakers if speaker not in interviewer_speakers]
        if candidates:
            candidate = max(
                candidates,
                key=lambda speaker: answer_counts[speaker] + char_counts[speaker] / 500,
            )
            speaker_roles[candidate] = "候选人"

    interviewer = next(
        (speaker for speaker in speakers if speaker_roles[speaker] == "面试官"),
        None,
    )
    candidate = next(
        (speaker for speaker in speakers if speaker_roles[speaker] == "候选人"),
        None,
    )
    confidence = 0.75 if question_counts[interviewer] > 0 else 0.55
    return RoleMapping(
        interviewer=interviewer,
        candidate=candidate,
        speaker_roles=speaker_roles,
        confidence=confidence,
        reason="按每个 Speaker 的提问与回答证据聚合，多个声纹簇可以归属于同一角色。",
    )


def analyze_interview(
    turns: list[TranscriptTurn],
    meta: InterviewMeta,
    ark_client: VolcArkClient | None,
) -> DebriefReport:
    """调用方舟 LLM 生成面试复盘报告，ark_client 为 None 或调用失败时回退到启发式报告。"""
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
    compatible = _compatible_report_data(data)
    model_role_mapping = compatible.pop("role_mapping", None)
    merged = fallback.model_dump()
    merged.update(compatible)
    try:
        report = DebriefReport.model_validate(merged)
    except ValidationError:
        report = fallback
    report.role_mapping = _validated_role_mapping(
        model_role_mapping,
        turns=turns,
        fallback=fallback.role_mapping,
    )
    return report


def heuristic_report(turns: list[TranscriptTurn]) -> DebriefReport:
    """纯本地启发式生成问答复盘报告，缺陷和建议均为通用提示，不依赖 LLM。"""
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
    """按角色映射将 turns 聚合为面试官问题和候选人回答的配对列表。"""
    pairs: list[dict[str, str]] = []
    current_question: str | None = None
    answer_parts: list[str] = []
    for turn in turns:
        is_interviewer_question = roles.role_for(turn.speaker) == "面试官" and any(
            marker in turn.text for marker in QUESTION_MARKERS
        )
        if is_interviewer_question:
            if current_question:
                pairs.append(
                    {"question": current_question, "answer": "\n".join(answer_parts).strip()}
                )
            current_question = turn.text
            answer_parts = []
        elif current_question and roles.role_for(turn.speaker) == "候选人":
            answer_parts.append(turn.text)
    if current_question:
        pairs.append({"question": current_question, "answer": "\n".join(answer_parts).strip()})
    return pairs


def _analysis_prompt(
    turns: list[TranscriptTurn],
    meta: InterviewMeta,
    fallback: DebriefReport,
) -> str:
    """拼装发送给方舟模型的分析提示词，包含 JSON 输出格式约束和启发式初判结果。"""
    return f"""
面试信息：{meta.title}

请基于下面的说话人转写，输出 JSON，结构必须匹配：
{{
  "role_mapping": {{
    "interviewer": "Speaker 0",
    "candidate": "Speaker 1",
    "speaker_roles": {{
      "Speaker 0": "面试官",
      "Speaker 1": "候选人"
    }},
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

只能使用转写中实际存在的 Speaker 标识。多个 Speaker 可以映射到同一角色；
无法判断的 Speaker 使用“未知”，不得给 Speaker 标识添加括号或解释文字。

转写文本：
{transcript_as_text(turns, max_chars=60000)}
""".strip()


def _compatible_report_data(data: dict[str, Any]) -> dict[str, Any]:
    """从 LLM JSON 响应中提取兼容字段，丢弃类型不匹配或结构异常的内容。"""
    result: dict[str, Any] = {}
    if isinstance(data.get("role_mapping"), dict):
        result["role_mapping"] = data["role_mapping"]
    if isinstance(data.get("questions"), list):
        result["questions"] = data["questions"]
    for key in ("overall_defects", "overall_suggestions", "learning_points"):
        if isinstance(data.get(key), list):
            result[key] = data[key]
    return result


def _validated_role_mapping(
    value: Any,
    turns: list[TranscriptTurn],
    fallback: RoleMapping,
) -> RoleMapping:
    """校验并合并模型返回的角色映射，锚点或角色不合规时回退到启发式结果。"""
    if not isinstance(value, dict):
        return fallback
    try:
        candidate = RoleMapping.model_validate(value)
    except ValidationError:
        return fallback

    known_speakers = list(dict.fromkeys(turn.speaker for turn in turns))
    known_set = set(known_speakers)
    anchors = (candidate.interviewer, candidate.candidate)
    if any(anchor is not None and anchor not in known_set for anchor in anchors):
        return fallback
    if not set(candidate.speaker_roles).issubset(known_set):
        return fallback

    speaker_roles = dict(fallback.speaker_roles)
    speaker_roles.update(candidate.speaker_roles)
    for speaker in known_speakers:
        speaker_roles.setdefault(speaker, "未知")

    if candidate.interviewer is not None:
        existing = candidate.speaker_roles.get(candidate.interviewer)
        if existing not in {None, "面试官"}:
            return fallback
        speaker_roles[candidate.interviewer] = "面试官"
    if candidate.candidate is not None:
        existing = candidate.speaker_roles.get(candidate.candidate)
        if existing not in {None, "候选人"}:
            return fallback
        speaker_roles[candidate.candidate] = "候选人"

    if len(known_speakers) < 2:
        if {"面试官", "候选人"} & set(speaker_roles.values()):
            return fallback
    elif not {"面试官", "候选人"}.issubset(set(speaker_roles.values())):
        return fallback

    interviewer = candidate.interviewer or next(
        (speaker for speaker in known_speakers if speaker_roles[speaker] == "面试官"),
        None,
    )
    candidate_speaker = candidate.candidate or next(
        (speaker for speaker in known_speakers if speaker_roles[speaker] == "候选人"),
        None,
    )
    try:
        return RoleMapping(
            interviewer=interviewer,
            candidate=candidate_speaker,
            speaker_roles=speaker_roles,
            confidence=candidate.confidence,
            reason=candidate.reason,
        )
    except ValidationError:
        return fallback

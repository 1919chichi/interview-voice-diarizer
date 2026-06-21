from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PreparedAudio(BaseModel):
    source_path: Path
    upload_path: Path
    audio_format: str
    converted: bool
    duration_seconds: float | None = None
    channels: int = Field(default=1, ge=1, le=2)


class TranscriptTurn(BaseModel):
    speaker: str
    text: str
    start_ms: int | None = None
    end_ms: int | None = None


class SpeakerDiagnostics(BaseModel):
    raw_counts: dict[str, int] = Field(default_factory=dict)
    normalized_counts: dict[str, int] = Field(default_factory=dict)

    @property
    def raw_speaker_count(self) -> int:
        """原始 ASR 中识别到的有效说话人数量（不含 Speaker unknown）。"""
        return self._known_speaker_count(self.raw_counts)

    @property
    def normalized_speaker_count(self) -> int:
        """标准化后的有效说话人数量（不含 Speaker unknown）。"""
        return self._known_speaker_count(self.normalized_counts)

    @staticmethod
    def _known_speaker_count(counts: dict[str, int]) -> int:
        """统计 counts 中非 'Speaker unknown' 的说话人数。"""
        return sum(speaker != "Speaker unknown" for speaker in counts)


class RoleMapping(BaseModel):
    interviewer: str | None = None
    candidate: str | None = None
    speaker_roles: dict[str, Literal["面试官", "候选人", "未知"]] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0, le=1)
    reason: str = "基于提问与回答模式的启发式判断。"

    @model_validator(mode="after")
    def validate_distinct_anchors(self) -> RoleMapping:
        """校验面试官和候选人不能是同一个 Speaker。"""
        if self.interviewer is not None and self.interviewer == self.candidate:
            raise ValueError("同一个 Speaker 不能同时作为面试官和候选人")
        return self

    def role_for(self, speaker: str) -> str | None:
        """查询指定说话人对应的角色标签，优先返回 speaker_roles 映射中的值。"""
        role = self.speaker_roles.get(speaker)
        if role in {"面试官", "候选人"}:
            return role
        if speaker == self.interviewer:
            return "面试官"
        if speaker == self.candidate:
            return "候选人"
        return None


class QuestionReview(BaseModel):
    question: str
    answer: str
    defects: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    learning_points: list[str] = Field(default_factory=list)


class DebriefReport(BaseModel):
    role_mapping: RoleMapping
    questions: list[QuestionReview] = Field(default_factory=list)
    overall_defects: list[str] = Field(default_factory=list)
    overall_suggestions: list[str] = Field(default_factory=list)
    learning_points: list[str] = Field(default_factory=list)


class InterviewMeta(BaseModel):
    company: str | None = None
    role: str | None = None
    round_name: str | None = None

    @property
    def title(self) -> str:
        """格式化面试标题，未填写任何信息时返回默认值"面试复盘"。"""
        parts = [self.company, self.role, self.round_name]
        return " / ".join(part for part in parts if part) or "面试复盘"

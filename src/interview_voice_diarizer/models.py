from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class PreparedAudio(BaseModel):
    source_path: Path
    upload_path: Path
    audio_format: str
    converted: bool
    duration_seconds: float | None = None


class TranscriptTurn(BaseModel):
    speaker: str
    text: str
    start_ms: int | None = None
    end_ms: int | None = None


class RoleMapping(BaseModel):
    interviewer: str = "Speaker 0"
    candidate: str = "Speaker 1"
    confidence: float = Field(default=0.5, ge=0, le=1)
    reason: str = "基于提问与回答模式的启发式判断。"


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
        parts = [self.company, self.role, self.round_name]
        return " / ".join(part for part in parts if part) or "面试复盘"

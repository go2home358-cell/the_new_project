from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProgressSummary(BaseModel):
    questions_attempted: int
    questions_correct: int
    accuracy: float
    tests_completed: int
    average_score: float
    study_seconds: int
    streak_count: int
    xp: int
    level: int


class ScopePerformance(BaseModel):
    id: int | None
    name: str
    attempted: int
    correct: int
    accuracy: float
    completion_percent: float = 0.0


class ContinueLearning(BaseModel):
    subject_id: int
    subject_name: str
    chapter_id: int
    chapter_name: str
    completion_percent: float
    last_studied_at: datetime | None


class DashboardOut(BaseModel):
    user_name: str
    summary: ProgressSummary
    continue_learning: ContinueLearning | None
    subjects: list[ScopePerformance]
    daily_challenge_test_id: int | None
    daily_challenge_questions: int


class WeakTopic(BaseModel):
    topic_id: int
    topic_name: str
    chapter_name: str
    subject_name: str
    attempted: int
    correct: int
    accuracy: float


class StudySessionRequest(BaseModel):
    seconds: int = Field(ge=1, le=24 * 3600)
    subject_id: int | None = None
    chapter_id: int | None = None


class BadgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    title: str
    description: str
    icon: str
    earned: bool = False
    earned_at: datetime | None = None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    title: str
    body: str
    scheduled_for: datetime
    read_at: datetime | None = None


class BookmarkRequest(BaseModel):
    target_type: str = Field(pattern="^(question|concept)$")
    target_id: int
    note: str = ""


class BookmarkOut(BaseModel):
    id: int
    target_type: str
    target_id: int
    title: str
    subtitle: str = ""
    note: str = ""
    created_at: datetime

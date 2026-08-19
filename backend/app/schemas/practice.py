from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.question import QuestionOut


class PracticeStartRequest(BaseModel):
    mode: str = Field(default="topic", pattern="^(topic|random|weak|wrong|bookmark)$")
    subject_id: int | None = None
    chapter_id: int | None = None
    topic_id: int | None = None
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")
    count: int = Field(default=10, ge=1, le=50)


class AttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mode: str
    status: str
    started_at: datetime
    duration_seconds: int | None = None
    total: int
    test_id: int | None = None
    title: str = ""
    questions: list[QuestionOut] = []


class AnswerRequest(BaseModel):
    question_id: int
    selected_option_id: int | None = None
    marked_for_review: bool = False
    time_spent_seconds: int = Field(default=0, ge=0)


class AnswerFeedback(BaseModel):
    question_id: int
    is_correct: bool | None
    correct_option_id: int | None
    correct_option_label: str | None
    explanation: str
    marked_for_review: bool


class TopicPerformance(BaseModel):
    topic_id: int | None
    topic_name: str
    total: int
    correct: int
    accuracy: float


class AttemptResult(BaseModel):
    attempt_id: int
    mode: str
    total: int
    attempted: int
    correct: int
    incorrect: int
    unattempted: int
    accuracy: float
    score: float
    time_used_seconds: int
    duration_seconds: int | None
    xp_earned: int = 0
    new_badges: list[str] = []
    topic_performance: list[TopicPerformance] = []
    weak_topics: list[str] = []


class AttemptReviewItem(BaseModel):
    question: QuestionOut
    selected_option_id: int | None
    correct_option_id: int | None
    is_correct: bool | None
    explanation: str


class TestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    kind: str
    subject_id: int | None = None
    chapter_id: int | None = None
    difficulty: str | None = None
    duration_seconds: int
    total_questions: int


class TestCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    kind: str = Field(default="mock", pattern="^(chapter|mock|daily)$")
    subject_id: int | None = None
    chapter_id: int | None = None
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")
    duration_seconds: int = Field(default=600, ge=60, le=14400)
    total_questions: int = Field(default=10, ge=1, le=200)
    question_ids: list[int] | None = None

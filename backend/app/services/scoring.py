"""Answer grading and attempt scoring.

Scoring rules: +1 per correct answer, 0 for unattempted/incorrect, score reported
as a percentage of the attempt's total questions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Question, QuestionOption, TestAttempt, UserAnswer
from app.models.test import ATTEMPT_SUBMITTED


class AttemptExpired(Exception):
    """Raised when an answer arrives after a timed attempt's window closed."""


@dataclass
class TopicStat:
    topic_id: int | None
    topic_name: str
    total: int = 0
    correct: int = 0

    @property
    def accuracy(self) -> float:
        return round(self.correct / self.total * 100, 2) if self.total else 0.0


@dataclass
class AttemptTotals:
    total: int = 0
    attempted: int = 0
    correct: int = 0
    incorrect: int = 0
    unattempted: int = 0
    accuracy: float = 0.0
    score: float = 0.0
    time_used_seconds: int = 0
    topics: list[TopicStat] = field(default_factory=list)


def seconds_elapsed(attempt: TestAttempt, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    started = attempt.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return max(0, int((now - started).total_seconds()))


def is_expired(attempt: TestAttempt, now: datetime | None = None) -> bool:
    if not attempt.duration_seconds:
        return False
    return seconds_elapsed(attempt, now) > attempt.duration_seconds


def grade_answer(
    db: Session,
    attempt: TestAttempt,
    answer: UserAnswer,
    selected_option_id: int | None,
    marked_for_review: bool,
    time_spent_seconds: int,
    now: datetime | None = None,
) -> Question:
    """Record a student's selection and grade it. Raises AttemptExpired past the timer."""
    if attempt.status == ATTEMPT_SUBMITTED:
        raise AttemptExpired("attempt already submitted")
    if is_expired(attempt, now):
        raise AttemptExpired("time limit exceeded")

    question = db.get(Question, answer.question_id)
    if question is None:
        raise ValueError("question not found")

    if selected_option_id is not None:
        option = db.get(QuestionOption, selected_option_id)
        if option is None or option.question_id != question.id:
            raise ValueError("option does not belong to question")
        answer.selected_option_id = option.id
        answer.is_correct = option.is_correct
        answer.answered_at = now or datetime.now(timezone.utc)
    else:
        answer.selected_option_id = None
        answer.is_correct = None
        answer.answered_at = None

    answer.marked_for_review = marked_for_review
    answer.time_spent_seconds = max(answer.time_spent_seconds, time_spent_seconds)
    return question


def compute_totals(db: Session, attempt: TestAttempt, now: datetime | None = None) -> AttemptTotals:
    totals = AttemptTotals(total=len(attempt.answers))
    topic_stats: dict[int | None, TopicStat] = {}

    for answer in attempt.answers:
        question = db.get(Question, answer.question_id)
        topic_id = question.topic_id if question else None
        topic_name = "General"
        if question is not None and question.topic_id is not None:
            from app.models import Topic

            topic = db.get(Topic, question.topic_id)
            topic_name = topic.name if topic else "General"
        stat = topic_stats.setdefault(topic_id, TopicStat(topic_id=topic_id, topic_name=topic_name))
        stat.total += 1

        if answer.selected_option_id is None:
            totals.unattempted += 1
            continue
        totals.attempted += 1
        if answer.is_correct:
            totals.correct += 1
            stat.correct += 1
        else:
            totals.incorrect += 1

    totals.accuracy = round(totals.correct / totals.attempted * 100, 2) if totals.attempted else 0.0
    totals.score = round(totals.correct / totals.total * 100, 2) if totals.total else 0.0
    elapsed = seconds_elapsed(attempt, now)
    totals.time_used_seconds = min(elapsed, attempt.duration_seconds) if attempt.duration_seconds else elapsed
    totals.topics = sorted(topic_stats.values(), key=lambda item: item.topic_name)
    return totals


def finalize_attempt(db: Session, attempt: TestAttempt, now: datetime | None = None) -> AttemptTotals:
    totals = compute_totals(db, attempt, now)
    attempt.total = totals.total
    attempt.attempted = totals.attempted
    attempt.correct = totals.correct
    attempt.incorrect = totals.incorrect
    attempt.unattempted = totals.unattempted
    attempt.accuracy = totals.accuracy
    attempt.score = totals.score
    attempt.time_used_seconds = totals.time_used_seconds
    attempt.status = ATTEMPT_SUBMITTED
    attempt.submitted_at = now or datetime.now(timezone.utc)
    return totals

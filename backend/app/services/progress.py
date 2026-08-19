"""Progress aggregation, completion percentages and daily streaks."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Chapter,
    Progress,
    Question,
    StudySession,
    Subject,
    TestAttempt,
    Topic,
    User,
    UserAnswer,
)
from app.models.test import ATTEMPT_SUBMITTED


def _get_or_create(
    db: Session, user_id: int, subject_id: int, chapter_id: int | None, topic_id: int | None
) -> Progress:
    stmt = select(Progress).where(
        Progress.user_id == user_id,
        Progress.subject_id == subject_id,
        Progress.chapter_id.is_(chapter_id) if chapter_id is None else Progress.chapter_id == chapter_id,
        Progress.topic_id.is_(topic_id) if topic_id is None else Progress.topic_id == topic_id,
    )
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        row = Progress(user_id=user_id, subject_id=subject_id, chapter_id=chapter_id, topic_id=topic_id)
        db.add(row)
        db.flush()
    return row


def _question_count(
    db: Session, chapter_id: int | None = None, topic_id: int | None = None, subject_id: int | None = None
) -> int:
    stmt = select(func.count(Question.id)).where(Question.is_active.is_(True))
    if subject_id is not None:
        stmt = stmt.where(Question.subject_id == subject_id)
    if chapter_id is not None:
        stmt = stmt.where(Question.chapter_id == chapter_id)
    if topic_id is not None:
        stmt = stmt.where(Question.topic_id == topic_id)
    return int(db.execute(stmt).scalar_one())


def _distinct_attempted(
    db: Session, user_id: int, chapter_id: int | None = None, subject_id: int | None = None, topic_id: int | None = None
) -> int:
    stmt = (
        select(func.count(func.distinct(UserAnswer.question_id)))
        .join(Question, Question.id == UserAnswer.question_id)
        .where(UserAnswer.user_id == user_id, UserAnswer.selected_option_id.is_not(None))
    )
    if subject_id is not None:
        stmt = stmt.where(Question.subject_id == subject_id)
    if chapter_id is not None:
        stmt = stmt.where(Question.chapter_id == chapter_id)
    if topic_id is not None:
        stmt = stmt.where(Question.topic_id == topic_id)
    return int(db.execute(stmt).scalar_one())


def record_attempt_progress(db: Session, user: User, attempt: TestAttempt) -> None:
    """Roll a submitted attempt into the per-scope progress rows."""
    buckets: dict[tuple[int, int | None, int | None], tuple[int, int]] = {}
    for answer in attempt.answers:
        if answer.selected_option_id is None:
            continue
        question = db.get(Question, answer.question_id)
        if question is None:
            continue
        for key in (
            (question.subject_id, None, None),
            (question.subject_id, question.chapter_id, None),
            (question.subject_id, question.chapter_id, question.topic_id),
        ):
            attempted, correct = buckets.get(key, (0, 0))
            buckets[key] = (attempted + 1, correct + (1 if answer.is_correct else 0))

    now = datetime.now(timezone.utc)
    for (subject_id, chapter_id, topic_id), (attempted, correct) in buckets.items():
        row = _get_or_create(db, user.id, subject_id, chapter_id, topic_id)
        row.attempted += attempted
        row.correct += correct
        row.last_studied_at = now
        pool = _question_count(db, chapter_id=chapter_id, topic_id=topic_id, subject_id=subject_id)
        seen = _distinct_attempted(db, user.id, chapter_id=chapter_id, subject_id=subject_id, topic_id=topic_id)
        row.completion_percent = round(min(seen / pool * 100, 100.0), 2) if pool else 0.0
    db.flush()


def touch_streak(db: Session, user: User, today: date | None = None) -> int:
    """Update the user's daily streak. Same-day activity keeps the streak unchanged."""
    today = today or datetime.now(timezone.utc).date()
    last = user.last_active_date
    if last == today:
        return user.streak_count
    if last is not None and last == today - timedelta(days=1):
        user.streak_count += 1
    else:
        user.streak_count = 1
    user.last_active_date = today
    db.flush()
    return user.streak_count


def summary(db: Session, user: User) -> dict[str, float]:
    attempted = int(
        db.execute(
            select(func.count(UserAnswer.id)).where(
                UserAnswer.user_id == user.id, UserAnswer.selected_option_id.is_not(None)
            )
        ).scalar_one()
    )
    correct = int(
        db.execute(
            select(func.count(UserAnswer.id)).where(UserAnswer.user_id == user.id, UserAnswer.is_correct.is_(True))
        ).scalar_one()
    )
    tests_completed = int(
        db.execute(
            select(func.count(TestAttempt.id)).where(
                TestAttempt.user_id == user.id, TestAttempt.status == ATTEMPT_SUBMITTED
            )
        ).scalar_one()
    )
    average_score = db.execute(
        select(func.coalesce(func.avg(TestAttempt.score), 0.0)).where(
            TestAttempt.user_id == user.id, TestAttempt.status == ATTEMPT_SUBMITTED
        )
    ).scalar_one()
    study_seconds = int(
        db.execute(
            select(func.coalesce(func.sum(StudySession.seconds), 0)).where(StudySession.user_id == user.id)
        ).scalar_one()
    )
    return {
        "questions_attempted": attempted,
        "questions_correct": correct,
        "accuracy": round(correct / attempted * 100, 2) if attempted else 0.0,
        "tests_completed": tests_completed,
        "average_score": round(float(average_score), 2),
        "study_seconds": study_seconds,
        "streak_count": user.streak_count,
        "xp": user.xp,
        "level": user.level,
    }


def subject_performance(db: Session, user: User) -> list[dict[str, float]]:
    rows = db.execute(select(Subject).order_by(Subject.order_index, Subject.name)).scalars().all()
    out: list[dict[str, float]] = []
    for subject in rows:
        record = db.execute(
            select(Progress).where(
                Progress.user_id == user.id,
                Progress.subject_id == subject.id,
                Progress.chapter_id.is_(None),
                Progress.topic_id.is_(None),
            )
        ).scalar_one_or_none()
        attempted = record.attempted if record else 0
        correct = record.correct if record else 0
        out.append(
            {
                "id": subject.id,
                "name": subject.name,
                "attempted": attempted,
                "correct": correct,
                "accuracy": round(correct / attempted * 100, 2) if attempted else 0.0,
                "completion_percent": record.completion_percent if record else 0.0,
            }
        )
    return out


def chapter_performance(db: Session, user: User, subject_id: int | None = None) -> list[dict[str, float]]:
    stmt = select(Chapter).order_by(Chapter.subject_id, Chapter.order_index)
    if subject_id is not None:
        stmt = stmt.where(Chapter.subject_id == subject_id)
    out: list[dict[str, float]] = []
    for chapter in db.execute(stmt).scalars().all():
        record = db.execute(
            select(Progress).where(
                Progress.user_id == user.id,
                Progress.chapter_id == chapter.id,
                Progress.topic_id.is_(None),
            )
        ).scalar_one_or_none()
        attempted = record.attempted if record else 0
        correct = record.correct if record else 0
        out.append(
            {
                "id": chapter.id,
                "name": chapter.name,
                "attempted": attempted,
                "correct": correct,
                "accuracy": round(correct / attempted * 100, 2) if attempted else 0.0,
                "completion_percent": record.completion_percent if record else 0.0,
            }
        )
    return out


def weak_topics(db: Session, user: User, threshold: float = 60.0, min_attempts: int = 3, limit: int = 10) -> list[dict]:
    stmt = (
        select(Progress, Topic, Chapter, Subject)
        .join(Topic, Topic.id == Progress.topic_id)
        .join(Chapter, Chapter.id == Topic.chapter_id)
        .join(Subject, Subject.id == Chapter.subject_id)
        .where(Progress.user_id == user.id, Progress.topic_id.is_not(None), Progress.attempted >= min_attempts)
    )
    results = []
    for record, topic, chapter, subject in db.execute(stmt).all():
        accuracy = round(record.correct / record.attempted * 100, 2) if record.attempted else 0.0
        if accuracy >= threshold:
            continue
        results.append(
            {
                "topic_id": topic.id,
                "topic_name": topic.name,
                "chapter_name": chapter.name,
                "subject_name": subject.name,
                "attempted": record.attempted,
                "correct": record.correct,
                "accuracy": accuracy,
            }
        )
    results.sort(key=lambda item: item["accuracy"])
    return results[:limit]


def continue_learning(db: Session, user: User) -> dict | None:
    record = db.execute(
        select(Progress)
        .where(
            Progress.user_id == user.id,
            Progress.chapter_id.is_not(None),
            Progress.topic_id.is_(None),
            Progress.last_studied_at.is_not(None),
        )
        .order_by(Progress.last_studied_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if record is None:
        return None
    chapter = db.get(Chapter, record.chapter_id)
    subject = db.get(Subject, record.subject_id)
    if chapter is None or subject is None:
        return None
    return {
        "subject_id": subject.id,
        "subject_name": subject.name,
        "chapter_id": chapter.id,
        "chapter_name": chapter.name,
        "completion_percent": record.completion_percent,
        "last_studied_at": record.last_studied_at,
    }

"""Question selection for the practice modes."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Bookmark, Progress, Question, Topic, User, UserAnswer


def _base_query(subject_id: int | None, chapter_id: int | None, topic_id: int | None, difficulty: str | None):
    stmt = select(Question).where(Question.is_active.is_(True)).options(selectinload(Question.options))
    if subject_id is not None:
        stmt = stmt.where(Question.subject_id == subject_id)
    if chapter_id is not None:
        stmt = stmt.where(Question.chapter_id == chapter_id)
    if topic_id is not None:
        stmt = stmt.where(Question.topic_id == topic_id)
    if difficulty is not None:
        stmt = stmt.where(Question.difficulty == difficulty)
    return stmt


def select_questions(
    db: Session,
    user: User,
    mode: str,
    count: int,
    subject_id: int | None = None,
    chapter_id: int | None = None,
    topic_id: int | None = None,
    difficulty: str | None = None,
) -> list[Question]:
    if mode == "wrong":
        return _wrong_questions(db, user, count, subject_id)
    if mode == "bookmark":
        return _bookmarked_questions(db, user, count, subject_id)
    if mode == "weak":
        return _weak_topic_questions(db, user, count, subject_id, difficulty)

    stmt = _base_query(subject_id, chapter_id, topic_id, difficulty).order_by(func.random()).limit(count)
    return list(db.execute(stmt).scalars().all())


def _wrong_questions(db: Session, user: User, count: int, subject_id: int | None) -> list[Question]:
    wrong_ids = select(UserAnswer.question_id).where(UserAnswer.user_id == user.id, UserAnswer.is_correct.is_(False))
    correct_ids = select(UserAnswer.question_id).where(UserAnswer.user_id == user.id, UserAnswer.is_correct.is_(True))
    stmt = (
        select(Question)
        .where(Question.is_active.is_(True), Question.id.in_(wrong_ids), Question.id.not_in(correct_ids))
        .options(selectinload(Question.options))
    )
    if subject_id is not None:
        stmt = stmt.where(Question.subject_id == subject_id)
    return list(db.execute(stmt.order_by(func.random()).limit(count)).scalars().all())


def _bookmarked_questions(db: Session, user: User, count: int, subject_id: int | None) -> list[Question]:
    bookmarked = select(Bookmark.target_id).where(Bookmark.user_id == user.id, Bookmark.target_type == "question")
    stmt = (
        select(Question)
        .where(Question.is_active.is_(True), Question.id.in_(bookmarked))
        .options(selectinload(Question.options))
    )
    if subject_id is not None:
        stmt = stmt.where(Question.subject_id == subject_id)
    return list(db.execute(stmt.order_by(func.random()).limit(count)).scalars().all())


def _weak_topic_questions(
    db: Session, user: User, count: int, subject_id: int | None, difficulty: str | None
) -> list[Question]:
    stmt = select(Progress).where(Progress.user_id == user.id, Progress.topic_id.is_not(None), Progress.attempted >= 1)
    if subject_id is not None:
        stmt = stmt.where(Progress.subject_id == subject_id)
    records = db.execute(stmt).scalars().all()
    ranked = sorted(records, key=lambda r: (r.correct / r.attempted) if r.attempted else 0.0)
    weak_topic_ids = [r.topic_id for r in ranked if r.attempted and (r.correct / r.attempted) < 0.6]

    questions: list[Question] = []
    for topic_id in weak_topic_ids:
        remaining = count - len(questions)
        if remaining <= 0:
            break
        found = (
            db.execute(_base_query(subject_id, None, topic_id, difficulty).order_by(func.random()).limit(remaining))
            .scalars()
            .all()
        )
        questions.extend(found)

    if len(questions) < count:
        # Not enough history yet: top up with random questions from the same scope.
        existing = {q.id for q in questions}
        top_up = (
            db.execute(_base_query(subject_id, None, None, difficulty).order_by(func.random()).limit(count * 2))
            .scalars()
            .all()
        )
        for question in top_up:
            if question.id in existing:
                continue
            questions.append(question)
            existing.add(question.id)
            if len(questions) >= count:
                break
    return questions[:count]


def topic_name(db: Session, topic_id: int | None) -> str:
    if topic_id is None:
        return "General"
    topic = db.get(Topic, topic_id)
    return topic.name if topic else "General"

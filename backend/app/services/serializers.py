from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Bookmark, Question
from app.schemas.question import OptionOut, QuestionOut


def bookmarked_ids(db: Session, user_id: int, target_type: str) -> set[int]:
    rows = (
        db.execute(select(Bookmark.target_id).where(Bookmark.user_id == user_id, Bookmark.target_type == target_type))
        .scalars()
        .all()
    )
    return set(rows)


def question_out(question: Question, bookmarks: set[int] | None = None) -> QuestionOut:
    """Student-facing question payload. Correct answers are deliberately omitted."""
    bookmarks = bookmarks or set()
    return QuestionOut(
        id=question.id,
        text=question.text,
        difficulty=question.difficulty,
        subject_id=question.subject_id,
        chapter_id=question.chapter_id,
        topic_id=question.topic_id,
        source=question.source,
        year=question.year,
        image_url=question.image_url,
        options=[OptionOut(id=option.id, label=option.label, text=option.text) for option in question.options],
        is_bookmarked=question.id in bookmarks,
    )


def questions_out(questions: Iterable[Question], bookmarks: set[int] | None = None) -> list[QuestionOut]:
    return [question_out(question, bookmarks) for question in questions]

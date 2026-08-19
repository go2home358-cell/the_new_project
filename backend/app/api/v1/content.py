from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Chapter, Concept, Progress, Question, Subject, Topic, User
from app.schemas.content import (
    ChapterDetailOut,
    ChapterOut,
    ConceptOut,
    SubjectOut,
    TopicOut,
)
from app.services.serializers import bookmarked_ids

router = APIRouter(tags=["content"])


def _question_counts(db: Session, column) -> dict[int, int]:
    rows = db.execute(
        select(column, func.count(Question.id)).where(Question.is_active.is_(True)).group_by(column)
    ).all()
    return {key: count for key, count in rows if key is not None}


def _completion(
    db: Session, user_id: int, *, subject_id: int | None = None, chapter_id: int | None = None
) -> dict[int, float]:
    stmt = select(Progress).where(Progress.user_id == user_id, Progress.topic_id.is_(None))
    if chapter_id is None and subject_id is None:
        stmt = stmt.where(Progress.chapter_id.is_(None))
    if subject_id is not None:
        stmt = stmt.where(Progress.subject_id == subject_id, Progress.chapter_id.is_not(None))
    rows = db.execute(stmt).scalars().all()
    key = "chapter_id" if subject_id is not None else "subject_id"
    return {getattr(row, key): row.completion_percent for row in rows if getattr(row, key) is not None}


@router.get("/subjects", response_model=list[SubjectOut])
def list_subjects(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[SubjectOut]:
    subjects = db.execute(select(Subject).order_by(Subject.order_index, Subject.name)).scalars().all()
    chapter_counts = {
        subject_id: count
        for subject_id, count in db.execute(
            select(Chapter.subject_id, func.count(Chapter.id)).group_by(Chapter.subject_id)
        ).all()
    }
    question_counts = _question_counts(db, Question.subject_id)
    completion = _completion(db, user.id)
    return [
        SubjectOut(
            id=subject.id,
            name=subject.name,
            slug=subject.slug,
            icon=subject.icon,
            color=subject.color,
            description=subject.description,
            chapter_count=chapter_counts.get(subject.id, 0),
            question_count=question_counts.get(subject.id, 0),
            completion_percent=completion.get(subject.id, 0.0),
        )
        for subject in subjects
    ]


@router.get("/subjects/{subject_id}/chapters", response_model=list[ChapterOut])
def list_chapters(
    subject_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ChapterOut]:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    chapters = (
        db.execute(select(Chapter).where(Chapter.subject_id == subject_id).order_by(Chapter.order_index))
        .scalars()
        .all()
    )
    question_counts = _question_counts(db, Question.chapter_id)
    completion = _completion(db, user.id, subject_id=subject_id)
    return [
        ChapterOut(
            id=chapter.id,
            subject_id=chapter.subject_id,
            name=chapter.name,
            slug=chapter.slug,
            description=chapter.description,
            order_index=chapter.order_index,
            question_count=question_counts.get(chapter.id, 0),
            completion_percent=completion.get(chapter.id, 0.0),
        )
        for chapter in chapters
    ]


@router.get("/chapters/{chapter_id}", response_model=ChapterDetailOut)
def chapter_detail(
    chapter_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ChapterDetailOut:
    chapter = db.execute(
        select(Chapter)
        .where(Chapter.id == chapter_id)
        .options(selectinload(Chapter.topics), selectinload(Chapter.concepts), selectinload(Chapter.subject))
    ).scalar_one_or_none()
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")

    bookmarked = bookmarked_ids(db, user.id, "concept")
    topic_question_counts = _question_counts(db, Question.topic_id)
    topic_progress = {
        row.topic_id: row
        for row in db.execute(
            select(Progress).where(
                Progress.user_id == user.id, Progress.chapter_id == chapter_id, Progress.topic_id.is_not(None)
            )
        )
        .scalars()
        .all()
    }

    def as_concept(concept: Concept) -> ConceptOut:
        return ConceptOut(
            id=concept.id,
            kind=concept.kind,
            title=concept.title,
            body=concept.body,
            topic_id=concept.topic_id,
            is_bookmarked=concept.id in bookmarked,
        )

    grouped: dict[str, list[ConceptOut]] = {kind: [] for kind in Concept.KINDS}
    for concept in chapter.concepts:
        grouped.setdefault(concept.kind, []).append(as_concept(concept))

    chapter_progress = db.execute(
        select(Progress).where(
            Progress.user_id == user.id, Progress.chapter_id == chapter_id, Progress.topic_id.is_(None)
        )
    ).scalar_one_or_none()

    topics = []
    for topic in chapter.topics:
        record = topic_progress.get(topic.id)
        accuracy = round(record.correct / record.attempted * 100, 2) if record and record.attempted else None
        topics.append(
            TopicOut(
                id=topic.id,
                name=topic.name,
                slug=topic.slug,
                question_count=topic_question_counts.get(topic.id, 0),
                accuracy=accuracy,
            )
        )

    return ChapterDetailOut(
        id=chapter.id,
        subject_id=chapter.subject_id,
        subject_name=chapter.subject.name,
        name=chapter.name,
        slug=chapter.slug,
        description=chapter.description,
        order_index=chapter.order_index,
        question_count=_question_counts(db, Question.chapter_id).get(chapter.id, 0),
        completion_percent=chapter_progress.completion_percent if chapter_progress else 0.0,
        topics=topics,
        concepts=grouped.get("concept", []),
        formulas=grouped.get("formula", []),
        examples=grouped.get("example", []),
        points=grouped.get("point", []),
    )


@router.get("/chapters/{chapter_id}/topics", response_model=list[TopicOut])
def list_topics(chapter_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[TopicOut]:
    if db.get(Chapter, chapter_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")
    topics = db.execute(select(Topic).where(Topic.chapter_id == chapter_id).order_by(Topic.order_index)).scalars().all()
    counts = _question_counts(db, Question.topic_id)
    return [
        TopicOut(id=topic.id, name=topic.name, slug=topic.slug, question_count=counts.get(topic.id, 0))
        for topic in topics
    ]


@router.get("/concepts/{concept_id}", response_model=ConceptOut)
def concept_detail(
    concept_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ConceptOut:
    concept = db.get(Concept, concept_id)
    if concept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")
    bookmarked = bookmarked_ids(db, user.id, "concept")
    return ConceptOut(
        id=concept.id,
        kind=concept.kind,
        title=concept.title,
        body=concept.body,
        topic_id=concept.topic_id,
        is_bookmarked=concept.id in bookmarked,
    )

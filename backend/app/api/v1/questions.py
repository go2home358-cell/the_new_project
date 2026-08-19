from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Chapter, Concept, Question, Subject, Topic, User
from app.schemas.content import SearchResponse, SearchResultItem
from app.schemas.question import QuestionOut
from app.services.serializers import bookmarked_ids, question_out, questions_out

router = APIRouter(tags=["questions"])


@router.get("/questions", response_model=list[QuestionOut])
def list_questions(
    subject_id: int | None = None,
    chapter_id: int | None = None,
    topic_id: int | None = None,
    difficulty: str | None = Query(default=None, pattern="^(easy|medium|hard)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[QuestionOut]:
    stmt = select(Question).where(Question.is_active.is_(True)).options(selectinload(Question.options))
    if subject_id is not None:
        stmt = stmt.where(Question.subject_id == subject_id)
    if chapter_id is not None:
        stmt = stmt.where(Question.chapter_id == chapter_id)
    if topic_id is not None:
        stmt = stmt.where(Question.topic_id == topic_id)
    if difficulty is not None:
        stmt = stmt.where(Question.difficulty == difficulty)
    rows = db.execute(stmt.order_by(Question.id).offset(offset).limit(limit)).scalars().all()
    return questions_out(rows, bookmarked_ids(db, user.id, "question"))


@router.get("/questions/{question_id}", response_model=QuestionOut)
def get_question(
    question_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> QuestionOut:
    question = db.get(Question, question_id)
    if question is None or not question.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return question_out(question, bookmarked_ids(db, user.id, "question"))


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SearchResponse:
    like = f"%{q.strip().lower()}%"
    results: list[SearchResultItem] = []

    for subject in db.execute(select(Subject).where(func.lower(Subject.name).like(like)).limit(limit)).scalars().all():
        results.append(SearchResultItem(kind="subject", id=subject.id, title=subject.name, subject_id=subject.id))

    for chapter in db.execute(select(Chapter).where(func.lower(Chapter.name).like(like)).limit(limit)).scalars().all():
        results.append(
            SearchResultItem(
                kind="chapter",
                id=chapter.id,
                title=chapter.name,
                subtitle=chapter.subject.name,
                subject_id=chapter.subject_id,
                chapter_id=chapter.id,
            )
        )

    for topic in db.execute(select(Topic).where(func.lower(Topic.name).like(like)).limit(limit)).scalars().all():
        results.append(
            SearchResultItem(
                kind="topic",
                id=topic.id,
                title=topic.name,
                subtitle=topic.chapter.name,
                subject_id=topic.chapter.subject_id,
                chapter_id=topic.chapter_id,
            )
        )

    for concept in (
        db.execute(
            select(Concept)
            .where(or_(func.lower(Concept.title).like(like), func.lower(Concept.body).like(like)))
            .limit(limit)
        )
        .scalars()
        .all()
    ):
        results.append(
            SearchResultItem(
                kind=concept.kind,
                id=concept.id,
                title=concept.title,
                subtitle=concept.chapter.name,
                subject_id=concept.chapter.subject_id,
                chapter_id=concept.chapter_id,
            )
        )

    for question in (
        db.execute(
            select(Question).where(Question.is_active.is_(True), func.lower(Question.text).like(like)).limit(limit)
        )
        .scalars()
        .all()
    ):
        results.append(
            SearchResultItem(
                kind="question",
                id=question.id,
                title=question.text[:140],
                subtitle=f"{question.difficulty.title()} • question",
                subject_id=question.subject_id,
                chapter_id=question.chapter_id,
            )
        )

    return SearchResponse(query=q, results=results[:limit])

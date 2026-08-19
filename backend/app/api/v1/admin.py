import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.deps import get_current_admin
from app.db.session import get_db
from app.models import (
    Chapter,
    Concept,
    Question,
    QuestionOption,
    Subject,
    Test,
    TestAttempt,
    TestQuestion,
    Topic,
    User,
    UserAnswer,
)
from app.schemas.auth import UserOut
from app.schemas.content import ChapterOut, SubjectOut, TopicOut
from app.schemas.practice import TestCreateRequest, TestOut
from app.schemas.question import QuestionAdminIn, QuestionAdminOut
from app.services.selection import select_questions
from app.services.serializers import question_out

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])

ALLOWED_IMAGE_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


class SubjectIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    slug: str = Field(min_length=2, max_length=80, pattern="^[a-z0-9-]+$")
    icon: str = "science"
    color: str = "#3F51B5"
    description: str = ""
    order_index: int = 0


class ChapterIn(BaseModel):
    subject_id: int
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=2, max_length=160, pattern="^[a-z0-9-]+$")
    description: str = ""
    order_index: int = 0


class TopicIn(BaseModel):
    chapter_id: int
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=2, max_length=160, pattern="^[a-z0-9-]+$")
    order_index: int = 0


class ConceptIn(BaseModel):
    chapter_id: int
    topic_id: int | None = None
    kind: str = Field(default="concept", pattern="^(concept|formula|example|point)$")
    title: str = Field(min_length=2, max_length=200)
    body: str = ""
    order_index: int = 0


class QuestionStat(BaseModel):
    question_id: int
    text: str
    times_attempted: int
    times_correct: int
    accuracy: float


@router.post("/subjects", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
def create_subject(payload: SubjectIn, db: Session = Depends(get_db)) -> SubjectOut:
    if db.execute(select(Subject).where(Subject.slug == payload.slug)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already exists")
    subject = Subject(**payload.model_dump())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return SubjectOut.model_validate(subject)


@router.post("/chapters", response_model=ChapterOut, status_code=status.HTTP_201_CREATED)
def create_chapter(payload: ChapterIn, db: Session = Depends(get_db)) -> ChapterOut:
    if db.get(Subject, payload.subject_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    chapter = Chapter(**payload.model_dump())
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return ChapterOut.model_validate(chapter)


@router.post("/topics", response_model=TopicOut, status_code=status.HTTP_201_CREATED)
def create_topic(payload: TopicIn, db: Session = Depends(get_db)) -> TopicOut:
    if db.get(Chapter, payload.chapter_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")
    topic = Topic(**payload.model_dump())
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return TopicOut.model_validate(topic)


@router.post("/concepts", status_code=status.HTTP_201_CREATED)
def create_concept(payload: ConceptIn, db: Session = Depends(get_db)) -> dict:
    if db.get(Chapter, payload.chapter_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")
    concept = Concept(**payload.model_dump())
    db.add(concept)
    db.commit()
    db.refresh(concept)
    return {"id": concept.id}


def _validate_question_payload(db: Session, payload: QuestionAdminIn) -> None:
    if db.get(Subject, payload.subject_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    chapter = db.get(Chapter, payload.chapter_id)
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")
    if chapter.subject_id != payload.subject_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chapter belongs to another subject")
    if payload.topic_id is not None:
        topic = db.get(Topic, payload.topic_id)
        if topic is None or topic.chapter_id != payload.chapter_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Topic does not belong to chapter")
    correct = [option for option in payload.options if option.is_correct]
    if len(correct) != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exactly one option must be correct")
    labels = [option.label for option in payload.options]
    if len(set(labels)) != len(labels):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Option labels must be unique")


def _question_admin_out(db: Session, question: Question) -> QuestionAdminOut:
    attempted = int(
        db.execute(
            select(func.count(UserAnswer.id)).where(
                UserAnswer.question_id == question.id, UserAnswer.selected_option_id.is_not(None)
            )
        ).scalar_one()
    )
    correct = int(
        db.execute(
            select(func.count(UserAnswer.id)).where(
                UserAnswer.question_id == question.id, UserAnswer.is_correct.is_(True)
            )
        ).scalar_one()
    )
    base = question_out(question).model_dump()
    correct_option = question.correct_option
    return QuestionAdminOut(
        **base,
        explanation=question.explanation,
        is_active=question.is_active,
        correct_option_id=correct_option.id if correct_option else None,
        times_attempted=attempted,
        times_correct=correct,
    )


@router.get("/questions", response_model=list[QuestionAdminOut])
def list_questions(
    subject_id: int | None = None,
    chapter_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[QuestionAdminOut]:
    stmt = select(Question).options(selectinload(Question.options))
    if subject_id is not None:
        stmt = stmt.where(Question.subject_id == subject_id)
    if chapter_id is not None:
        stmt = stmt.where(Question.chapter_id == chapter_id)
    rows = db.execute(stmt.order_by(Question.id.desc()).offset(offset).limit(limit)).scalars().all()
    return [_question_admin_out(db, question) for question in rows]


@router.post("/questions", response_model=QuestionAdminOut, status_code=status.HTTP_201_CREATED)
def create_question(
    payload: QuestionAdminIn, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
) -> QuestionAdminOut:
    _validate_question_payload(db, payload)
    data = payload.model_dump()
    options = data.pop("options")
    question = Question(**data, created_by=admin.id)
    question.options = [QuestionOption(**option) for option in options]
    db.add(question)
    db.commit()
    db.refresh(question)
    return _question_admin_out(db, question)


@router.put("/questions/{question_id}", response_model=QuestionAdminOut)
def update_question(question_id: int, payload: QuestionAdminIn, db: Session = Depends(get_db)) -> QuestionAdminOut:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    _validate_question_payload(db, payload)
    data = payload.model_dump()
    options = data.pop("options")
    for field, value in data.items():
        setattr(question, field, value)
    question.options.clear()
    db.flush()
    question.options = [QuestionOption(**option) for option in options]
    db.commit()
    db.refresh(question)
    return _question_admin_out(db, question)


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(question_id: int, db: Session = Depends(get_db)) -> None:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    db.delete(question)
    db.commit()
    return None


@router.post("/uploads", status_code=status.HTTP_201_CREATED)
async def upload_image(file: UploadFile = File(...)) -> dict:
    extension = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PNG, JPEG or WebP images allowed")
    os.makedirs(settings.upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{extension}"
    destination = os.path.join(settings.upload_dir, filename)
    with open(destination, "wb") as handle:
        handle.write(await file.read())
    return {"url": f"/uploads/{filename}"}


@router.post("/tests", response_model=TestOut, status_code=status.HTTP_201_CREATED)
def create_test(
    payload: TestCreateRequest, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
) -> TestOut:
    test = Test(
        title=payload.title,
        kind=payload.kind,
        subject_id=payload.subject_id,
        chapter_id=payload.chapter_id,
        difficulty=payload.difficulty,
        duration_seconds=payload.duration_seconds,
        total_questions=payload.total_questions,
        created_by=admin.id,
    )
    db.add(test)
    db.flush()

    question_ids = payload.question_ids
    if not question_ids:
        drawn = select_questions(
            db,
            admin,
            mode="random",
            count=payload.total_questions,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            difficulty=payload.difficulty,
        )
        question_ids = [question.id for question in drawn]
    for index, question_id in enumerate(question_ids):
        if db.get(Question, question_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Question {question_id} not found")
        db.add(TestQuestion(test_id=test.id, question_id=question_id, order_index=index))
    test.total_questions = len(question_ids)
    db.commit()
    db.refresh(test)
    return TestOut.model_validate(test)


@router.delete("/tests/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test(test_id: int, db: Session = Depends(get_db)) -> None:
    test = db.get(Test, test_id)
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    db.delete(test)
    db.commit()
    return None


@router.get("/users", response_model=list[UserOut])
def list_users(
    limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)
) -> list[UserOut]:
    rows = db.execute(select(User).order_by(User.id).offset(offset).limit(limit)).scalars().all()
    return [UserOut.model_validate(row) for row in rows]


@router.get("/stats/questions", response_model=list[QuestionStat])
def question_stats(limit: int = Query(default=25, ge=1, le=100), db: Session = Depends(get_db)) -> list[QuestionStat]:
    rows = db.execute(
        select(
            Question.id,
            Question.text,
            func.count(UserAnswer.selected_option_id).label("attempted"),
            func.coalesce(func.sum(case((UserAnswer.is_correct.is_(True), 1), else_=0)), 0).label("correct"),
        )
        .join(UserAnswer, UserAnswer.question_id == Question.id, isouter=True)
        .group_by(Question.id, Question.text)
        .order_by(func.count(UserAnswer.selected_option_id).desc())
        .limit(limit)
    ).all()
    stats: list[QuestionStat] = []
    for question_id, text, attempted, correct in rows:
        attempted = int(attempted or 0)
        correct = int(correct or 0)
        stats.append(
            QuestionStat(
                question_id=question_id,
                text=text[:140],
                times_attempted=attempted,
                times_correct=correct,
                accuracy=round(correct / attempted * 100, 2) if attempted else 0.0,
            )
        )
    return stats


@router.get("/stats/overview")
def overview(db: Session = Depends(get_db)) -> dict:
    return {
        "users": int(db.execute(select(func.count(User.id))).scalar_one()),
        "subjects": int(db.execute(select(func.count(Subject.id))).scalar_one()),
        "chapters": int(db.execute(select(func.count(Chapter.id))).scalar_one()),
        "questions": int(db.execute(select(func.count(Question.id))).scalar_one()),
        "tests": int(db.execute(select(func.count(Test.id))).scalar_one()),
        "attempts": int(db.execute(select(func.count(TestAttempt.id))).scalar_one()),
    }

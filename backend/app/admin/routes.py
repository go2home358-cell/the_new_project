"""Server-rendered admin panel.

Authentication reuses the API's JWT: the login form stores the access token in an
HttpOnly cookie and every page re-checks that the token belongs to an admin.
"""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.security import ACCESS_TOKEN, create_access_token, decode_token, verify_password
from app.db.session import get_db
from app.models import (
    ROLE_ADMIN,
    Chapter,
    Concept,
    Question,
    QuestionOption,
    Subject,
    Test,
    Topic,
    User,
    UserAnswer,
)

router = APIRouter(prefix="/admin", include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

COOKIE_NAME = "admin_token"


def current_admin(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    payload = decode_token(token, ACCESS_TOKEN) if token else None
    if payload is None:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/admin/login"})
    user = db.get(User, int(payload["sub"]))
    if user is None or user.role != ROLE_ADMIN:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/admin/login"})
    return user


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.execute(select(User).where(func.lower(User.email) == email.lower())).scalar_one_or_none()
    if user is None or user.role != ROLE_ADMIN or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid admin credentials"}, status_code=status.HTTP_401_UNAUTHORIZED
        )
    response = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        COOKIE_NAME,
        create_access_token(user.id, user.role),
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, admin: User = Depends(current_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    counts = {
        "users": int(db.execute(select(func.count(User.id))).scalar_one()),
        "subjects": int(db.execute(select(func.count(Subject.id))).scalar_one()),
        "chapters": int(db.execute(select(func.count(Chapter.id))).scalar_one()),
        "topics": int(db.execute(select(func.count(Topic.id))).scalar_one()),
        "questions": int(db.execute(select(func.count(Question.id))).scalar_one()),
        "tests": int(db.execute(select(func.count(Test.id))).scalar_one()),
    }
    return templates.TemplateResponse(request, "dashboard.html", {"admin": admin, "counts": counts})


@router.get("/questions", response_class=HTMLResponse)
def question_list(
    request: Request,
    subject_id: int | None = None,
    admin: User = Depends(current_admin),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    stmt = select(Question).options(selectinload(Question.options)).order_by(Question.id.desc()).limit(100)
    if subject_id is not None:
        stmt = stmt.where(Question.subject_id == subject_id)
    questions = db.execute(stmt).scalars().all()
    stats = {
        question_id: (int(attempted or 0), int(correct or 0))
        for question_id, attempted, correct in db.execute(
            select(
                UserAnswer.question_id,
                func.count(UserAnswer.selected_option_id),
                func.count(UserAnswer.id).filter(UserAnswer.is_correct.is_(True)),
            ).group_by(UserAnswer.question_id)
        ).all()
    }
    subjects = db.execute(select(Subject).order_by(Subject.order_index)).scalars().all()
    return templates.TemplateResponse(
        request,
        "questions.html",
        {
            "admin": admin,
            "questions": questions,
            "subjects": subjects,
            "selected_subject": subject_id,
            "stats": stats,
        },
    )


@router.get("/questions/new", response_class=HTMLResponse)
def question_new(request: Request, admin: User = Depends(current_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "question_form.html",
        {
            "admin": admin,
            "question": None,
            "subjects": db.execute(select(Subject).order_by(Subject.order_index)).scalars().all(),
            "chapters": db.execute(select(Chapter).order_by(Chapter.subject_id, Chapter.order_index)).scalars().all(),
            "topics": db.execute(select(Topic).order_by(Topic.chapter_id, Topic.order_index)).scalars().all(),
            "error": None,
        },
    )


@router.get("/questions/{question_id}/edit", response_class=HTMLResponse)
def question_edit(
    question_id: int, request: Request, admin: User = Depends(current_admin), db: Session = Depends(get_db)
) -> HTMLResponse:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return templates.TemplateResponse(
        request,
        "question_form.html",
        {
            "admin": admin,
            "question": question,
            "subjects": db.execute(select(Subject).order_by(Subject.order_index)).scalars().all(),
            "chapters": db.execute(select(Chapter).order_by(Chapter.subject_id, Chapter.order_index)).scalars().all(),
            "topics": db.execute(select(Topic).order_by(Topic.chapter_id, Topic.order_index)).scalars().all(),
            "error": None,
        },
    )


@router.post("/questions/save")
async def question_save(
    request: Request,
    question_id: int | None = Form(default=None),
    subject_id: int = Form(...),
    chapter_id: int = Form(...),
    topic_id: int | None = Form(default=None),
    text: str = Form(...),
    explanation: str = Form(default=""),
    difficulty: str = Form(default="medium"),
    source: str = Form(default=""),
    year: int | None = Form(default=None),
    option_a: str = Form(...),
    option_b: str = Form(...),
    option_c: str = Form(...),
    option_d: str = Form(...),
    correct: str = Form(...),
    image: UploadFile | None = File(default=None),
    admin: User = Depends(current_admin),
    db: Session = Depends(get_db),
):
    if correct not in {"A", "B", "C", "D"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Correct option must be A-D")

    image_url = None
    if image is not None and image.filename:
        os.makedirs(settings.upload_dir, exist_ok=True)
        destination = os.path.join(settings.upload_dir, image.filename)
        with open(destination, "wb") as handle:
            handle.write(await image.read())
        image_url = f"/uploads/{image.filename}"

    question = db.get(Question, question_id) if question_id else None
    if question is None:
        question = Question(created_by=admin.id)
        db.add(question)

    question.subject_id = subject_id
    question.chapter_id = chapter_id
    question.topic_id = topic_id or None
    question.text = text
    question.explanation = explanation
    question.difficulty = difficulty
    question.source = source
    question.year = year
    if image_url:
        question.image_url = image_url

    question.options.clear()
    db.flush()
    for label, option_text in (("A", option_a), ("B", option_b), ("C", option_c), ("D", option_d)):
        question.options.append(QuestionOption(label=label, text=option_text, is_correct=label == correct))
    db.commit()
    return RedirectResponse(url="/admin/questions", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/questions/{question_id}/delete")
def question_delete(question_id: int, admin: User = Depends(current_admin), db: Session = Depends(get_db)):
    question = db.get(Question, question_id)
    if question is not None:
        db.delete(question)
        db.commit()
    return RedirectResponse(url="/admin/questions", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/content", response_class=HTMLResponse)
def content_page(request: Request, admin: User = Depends(current_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "content.html",
        {
            "admin": admin,
            "subjects": db.execute(select(Subject).order_by(Subject.order_index)).scalars().all(),
            "chapters": db.execute(select(Chapter).order_by(Chapter.subject_id, Chapter.order_index)).scalars().all(),
            "topics": db.execute(select(Topic).order_by(Topic.chapter_id, Topic.order_index)).scalars().all(),
            "concept_counts": {
                chapter_id: count
                for chapter_id, count in db.execute(
                    select(Concept.chapter_id, func.count(Concept.id)).group_by(Concept.chapter_id)
                ).all()
            },
        },
    )


@router.post("/content/subjects")
def content_create_subject(
    name: str = Form(...),
    slug: str = Form(...),
    color: str = Form(default="#3F51B5"),
    admin: User = Depends(current_admin),
    db: Session = Depends(get_db),
):
    db.add(Subject(name=name, slug=slug, color=color, order_index=0))
    db.commit()
    return RedirectResponse(url="/admin/content", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/content/chapters")
def content_create_chapter(
    subject_id: int = Form(...),
    name: str = Form(...),
    slug: str = Form(...),
    admin: User = Depends(current_admin),
    db: Session = Depends(get_db),
):
    order_index = int(
        db.execute(
            select(func.coalesce(func.max(Chapter.order_index), 0)).where(Chapter.subject_id == subject_id)
        ).scalar_one()
    )
    db.add(Chapter(subject_id=subject_id, name=name, slug=slug, order_index=order_index + 1))
    db.commit()
    return RedirectResponse(url="/admin/content", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/content/topics")
def content_create_topic(
    chapter_id: int = Form(...),
    name: str = Form(...),
    slug: str = Form(...),
    admin: User = Depends(current_admin),
    db: Session = Depends(get_db),
):
    order_index = int(
        db.execute(
            select(func.coalesce(func.max(Topic.order_index), 0)).where(Topic.chapter_id == chapter_id)
        ).scalar_one()
    )
    db.add(Topic(chapter_id=chapter_id, name=name, slug=slug, order_index=order_index + 1))
    db.commit()
    return RedirectResponse(url="/admin/content", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/content/concepts")
def content_create_concept(
    chapter_id: int = Form(...),
    kind: str = Form(default="concept"),
    title: str = Form(...),
    body: str = Form(default=""),
    admin: User = Depends(current_admin),
    db: Session = Depends(get_db),
):
    db.add(Concept(chapter_id=chapter_id, kind=kind, title=title, body=body))
    db.commit()
    return RedirectResponse(url="/admin/content", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/tests", response_class=HTMLResponse)
def tests_page(request: Request, admin: User = Depends(current_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "tests.html",
        {
            "admin": admin,
            "tests": db.execute(select(Test).order_by(Test.id.desc())).scalars().all(),
            "subjects": db.execute(select(Subject).order_by(Subject.order_index)).scalars().all(),
        },
    )


@router.post("/tests")
def create_test_page(
    title: str = Form(...),
    kind: str = Form(default="mock"),
    subject_id: int | None = Form(default=None),
    duration_minutes: int = Form(default=10),
    total_questions: int = Form(default=10),
    admin: User = Depends(current_admin),
    db: Session = Depends(get_db),
):
    test = Test(
        title=title,
        kind=kind,
        subject_id=subject_id or None,
        duration_seconds=duration_minutes * 60,
        total_questions=total_questions,
        created_by=admin.id,
    )
    db.add(test)
    db.commit()
    return RedirectResponse(url="/admin/tests", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request, admin: User = Depends(current_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    users = db.execute(select(User).order_by(User.id)).scalars().all()
    return templates.TemplateResponse(request, "users.html", {"admin": admin, "users": users})

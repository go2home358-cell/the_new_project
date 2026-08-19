import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Achievement, Chapter, Question, QuestionOption, Subject, Test, TestQuestion, Topic, User
from app.models.user import ROLE_ADMIN
from app.services.gamification import BADGE_DEFINITIONS

os.environ.setdefault("ENVIRONMENT", "test")

engine = create_engine(settings.test_database_url, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "AdminPass1!"
STUDENT_EMAIL = "student@example.com"
STUDENT_PASSWORD = "StudentPass1!"


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_tables() -> Iterator[None]:
    tables = ", ".join(f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables))
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def db() -> Iterator[Session]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded(db: Session) -> dict[str, object]:
    """A minimal but realistic content tree: 1 subject, 1 chapter, 2 topics, 4 questions, 1 timed test."""
    for definition in BADGE_DEFINITIONS:
        db.add(Achievement(**definition))

    subject = Subject(name="Physics", slug="physics", description="Test subject")
    db.add(subject)
    db.flush()
    chapter = Chapter(subject_id=subject.id, name="Motion", slug="motion")
    db.add(chapter)
    db.flush()
    topic_a = Topic(chapter_id=chapter.id, name="Speed", slug="speed")
    topic_b = Topic(chapter_id=chapter.id, name="Acceleration", slug="acceleration")
    db.add_all([topic_a, topic_b])
    db.flush()

    questions = []
    for index in range(4):
        topic = topic_a if index < 2 else topic_b
        question = Question(
            subject_id=subject.id,
            chapter_id=chapter.id,
            topic_id=topic.id,
            text=f"Question {index}?",
            explanation=f"Because of reason {index}.",
            difficulty="easy",
        )
        db.add(question)
        db.flush()
        for label_index, label in enumerate("ABCD"):
            db.add(
                QuestionOption(
                    question_id=question.id,
                    label=label,
                    text=f"Option {label}",
                    is_correct=label_index == 1,
                )
            )
        db.flush()
        questions.append(question)

    test = Test(title="Timed Mock", kind="mock", subject_id=subject.id, duration_seconds=600, total_questions=4)
    db.add(test)
    db.flush()
    for index, question in enumerate(questions):
        db.add(TestQuestion(test_id=test.id, question_id=question.id, order_index=index))

    admin = User(
        name="Admin",
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        role=ROLE_ADMIN,
    )
    db.add(admin)
    db.commit()
    return {
        "subject": subject,
        "chapter": chapter,
        "topics": [topic_a, topic_b],
        "questions": questions,
        "test": test,
        "admin": admin,
    }


def register(client: TestClient, email: str = STUDENT_EMAIL, password: str = STUDENT_PASSWORD) -> dict[str, str]:
    response = client.post("/api/v1/auth/register", json={"name": "Student", "email": email, "password": password})
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def student_headers(client: TestClient) -> dict[str, str]:
    return register(client)


@pytest.fixture
def admin_headers(client: TestClient, seeded: dict[str, object]) -> dict[str, str]:
    return login(client, ADMIN_EMAIL, ADMIN_PASSWORD)

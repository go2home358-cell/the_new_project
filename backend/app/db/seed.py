"""Idempotent seeding of subjects, chapters, topics, learning material, MCQs, tests and badges.

Run with `python -m app.db.seed`.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.init_db import init_db
from app.db.seed_data import SUBJECTS
from app.db.session import SessionLocal
from app.models import (
    Achievement,
    Chapter,
    Concept,
    Question,
    QuestionOption,
    Subject,
    Test,
    TestQuestion,
    Topic,
    User,
)
from app.models.user import ROLE_ADMIN
from app.services.gamification import BADGE_DEFINITIONS

OPTION_LABELS = ("A", "B", "C", "D")


def _slugify(value: str) -> str:
    return "-".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def seed_admin(db: Session) -> None:
    if not settings.admin_email or not settings.admin_password:
        return
    existing = db.execute(select(User).where(User.email == settings.admin_email)).scalar_one_or_none()
    if existing:
        if existing.role != ROLE_ADMIN:
            existing.role = ROLE_ADMIN
        return
    db.add(
        User(
            name=settings.admin_name,
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            role=ROLE_ADMIN,
        )
    )


def seed_badges(db: Session) -> None:
    for definition in BADGE_DEFINITIONS:
        existing = db.execute(select(Achievement).where(Achievement.code == definition["code"])).scalar_one_or_none()
        if existing:
            continue
        db.add(Achievement(**definition))


def seed_content(db: Session) -> dict[str, int]:
    counts = {"subjects": 0, "chapters": 0, "topics": 0, "concepts": 0, "questions": 0}

    for subject_index, subject_data in enumerate(SUBJECTS):
        subject = db.execute(select(Subject).where(Subject.slug == subject_data["slug"])).scalar_one_or_none()
        if subject is None:
            subject = Subject(
                name=subject_data["name"],
                slug=subject_data["slug"],
                icon=subject_data["icon"],
                color=subject_data["color"],
                description=subject_data["description"],
                order_index=subject_index,
            )
            db.add(subject)
            db.flush()
            counts["subjects"] += 1

        for chapter_index, chapter_data in enumerate(subject_data["chapters"]):
            chapter = db.execute(
                select(Chapter).where(Chapter.subject_id == subject.id, Chapter.slug == chapter_data["slug"])
            ).scalar_one_or_none()
            if chapter is None:
                chapter = Chapter(
                    subject_id=subject.id,
                    name=chapter_data["name"],
                    slug=chapter_data["slug"],
                    description=chapter_data.get("description", ""),
                    order_index=chapter_index,
                )
                db.add(chapter)
                db.flush()
                counts["chapters"] += 1

            topics: dict[str, Topic] = {}
            for topic_index, topic_name in enumerate(chapter_data.get("topics", [])):
                slug = _slugify(topic_name)
                topic = db.execute(
                    select(Topic).where(Topic.chapter_id == chapter.id, Topic.slug == slug)
                ).scalar_one_or_none()
                if topic is None:
                    topic = Topic(chapter_id=chapter.id, name=topic_name, slug=slug, order_index=topic_index)
                    db.add(topic)
                    db.flush()
                    counts["topics"] += 1
                topics[topic_name] = topic

            for concept_index, concept_data in enumerate(chapter_data.get("concepts", [])):
                exists = db.execute(
                    select(Concept.id).where(Concept.chapter_id == chapter.id, Concept.title == concept_data["title"])
                ).scalar_one_or_none()
                if exists:
                    continue
                db.add(
                    Concept(
                        chapter_id=chapter.id,
                        kind=concept_data["kind"],
                        title=concept_data["title"],
                        body=concept_data["body"],
                        order_index=concept_index,
                    )
                )
                counts["concepts"] += 1

            for question_data in chapter_data.get("questions", []):
                exists = db.execute(
                    select(Question.id).where(Question.chapter_id == chapter.id, Question.text == question_data["text"])
                ).scalar_one_or_none()
                if exists:
                    continue
                topic = topics.get(question_data.get("topic", ""))
                question = Question(
                    subject_id=subject.id,
                    chapter_id=chapter.id,
                    topic_id=topic.id if topic else None,
                    text=question_data["text"],
                    explanation=question_data.get("explanation", ""),
                    difficulty=question_data.get("difficulty", "medium"),
                    source=question_data.get("source", "Seed bank"),
                    year=question_data.get("year"),
                )
                db.add(question)
                db.flush()
                for label, option_text in zip(OPTION_LABELS, question_data["options"], strict=False):
                    db.add(
                        QuestionOption(
                            question_id=question.id,
                            label=label,
                            text=option_text,
                            is_correct=label == question_data["correct"],
                        )
                    )
                counts["questions"] += 1

    return counts


def seed_tests(db: Session) -> int:
    created = 0
    subjects = db.execute(select(Subject)).scalars().all()

    def build(title: str, kind: str, subject: Subject | None, total: int, minutes: int) -> None:
        nonlocal created
        if db.execute(select(Test.id).where(Test.title == title)).scalar_one_or_none():
            return
        query = select(Question.id).where(Question.is_active.is_(True))
        if subject is not None:
            query = query.where(Question.subject_id == subject.id)
        question_ids = db.execute(query.order_by(func.random()).limit(total)).scalars().all()
        if not question_ids:
            return
        test = Test(
            title=title,
            kind=kind,
            subject_id=subject.id if subject else None,
            duration_seconds=minutes * 60,
            total_questions=len(question_ids),
        )
        db.add(test)
        db.flush()
        for index, question_id in enumerate(question_ids):
            db.add(TestQuestion(test_id=test.id, question_id=question_id, order_index=index))
        created += 1

    build("Daily Challenge", "daily", None, 5, 5)
    build("Full Syllabus Mock Test", "mock", None, 20, 20)
    for subject in subjects:
        build(f"{subject.name} Mock Test", "mock", subject, 10, 10)

    return created


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_admin(db)
        seed_badges(db)
        counts = seed_content(db)
        db.flush()
        tests = seed_tests(db)
        db.commit()
    finally:
        db.close()
    print(f"Seeded: {counts}, tests={tests}")


if __name__ == "__main__":
    main()

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Question, Test, TestAttempt, User, UserAnswer
from app.models.test import ATTEMPT_IN_PROGRESS, ATTEMPT_SUBMITTED
from app.schemas.practice import (
    AnswerFeedback,
    AnswerRequest,
    AttemptOut,
    AttemptResult,
    AttemptReviewItem,
    PracticeStartRequest,
    TestOut,
    TopicPerformance,
)
from app.services import gamification, notifications, scoring, selection
from app.services import progress as progress_service
from app.services.serializers import bookmarked_ids, question_out, questions_out

router = APIRouter(tags=["practice"])


def _load_attempt(db: Session, attempt_id: int, user: User) -> TestAttempt:
    attempt = db.execute(
        select(TestAttempt).where(TestAttempt.id == attempt_id).options(selectinload(TestAttempt.answers))
    ).scalar_one_or_none()
    if attempt is None or attempt.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    return attempt


def _create_attempt(
    db: Session,
    user: User,
    questions: list[Question],
    mode: str,
    duration_seconds: int | None,
    test: Test | None = None,
    subject_id: int | None = None,
    chapter_id: int | None = None,
    topic_id: int | None = None,
) -> TestAttempt:
    if not questions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No questions available for this selection")
    attempt = TestAttempt(
        user_id=user.id,
        test_id=test.id if test else None,
        mode=mode,
        status=ATTEMPT_IN_PROGRESS,
        started_at=datetime.now(timezone.utc),
        duration_seconds=duration_seconds,
        total=len(questions),
        unattempted=len(questions),
        subject_id=subject_id,
        chapter_id=chapter_id,
        topic_id=topic_id,
    )
    db.add(attempt)
    db.flush()
    for index, question in enumerate(questions):
        db.add(
            UserAnswer(
                attempt_id=attempt.id,
                user_id=user.id,
                question_id=question.id,
                order_index=index,
            )
        )
    progress_service.touch_streak(db, user)
    db.commit()
    db.refresh(attempt)
    return attempt


def _attempt_out(
    db: Session, attempt: TestAttempt, questions: list[Question], user: User, title: str = ""
) -> AttemptOut:
    bookmarked = bookmarked_ids(db, user.id, "question")
    return AttemptOut(
        id=attempt.id,
        mode=attempt.mode,
        status=attempt.status,
        started_at=attempt.started_at,
        duration_seconds=attempt.duration_seconds,
        total=attempt.total,
        test_id=attempt.test_id,
        title=title,
        questions=questions_out(questions, bookmarked),
    )


@router.post("/practice/sessions", response_model=AttemptOut, status_code=status.HTTP_201_CREATED)
def start_practice(
    payload: PracticeStartRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AttemptOut:
    questions = selection.select_questions(
        db,
        user,
        mode=payload.mode,
        count=payload.count,
        subject_id=payload.subject_id,
        chapter_id=payload.chapter_id,
        topic_id=payload.topic_id,
        difficulty=payload.difficulty,
    )
    attempt = _create_attempt(
        db,
        user,
        questions,
        mode=payload.mode,
        duration_seconds=None,
        subject_id=payload.subject_id,
        chapter_id=payload.chapter_id,
        topic_id=payload.topic_id,
    )
    return _attempt_out(db, attempt, questions, user, title=f"{payload.mode.title()} practice")


@router.get("/tests", response_model=list[TestOut])
def list_tests(
    kind: str | None = Query(default=None, pattern="^(chapter|mock|daily)$"),
    subject_id: int | None = None,
    chapter_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[TestOut]:
    stmt = select(Test).where(Test.is_active.is_(True))
    if kind is not None:
        stmt = stmt.where(Test.kind == kind)
    if subject_id is not None:
        stmt = stmt.where(Test.subject_id == subject_id)
    if chapter_id is not None:
        stmt = stmt.where(Test.chapter_id == chapter_id)
    return [TestOut.model_validate(test) for test in db.execute(stmt.order_by(Test.id)).scalars().all()]


@router.post("/tests/{test_id}/start", response_model=AttemptOut, status_code=status.HTTP_201_CREATED)
def start_test(test_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> AttemptOut:
    test = db.get(Test, test_id)
    if test is None or not test.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")

    question_ids = [link.question_id for link in test.test_questions]
    if question_ids:
        questions = list(
            db.execute(select(Question).where(Question.id.in_(question_ids)).options(selectinload(Question.options)))
            .scalars()
            .all()
        )
        order = {qid: index for index, qid in enumerate(question_ids)}
        questions.sort(key=lambda question: order[question.id])
    else:
        # Dynamic test: draw a fresh random set matching the test's configuration.
        questions = selection.select_questions(
            db,
            user,
            mode="random",
            count=test.total_questions,
            subject_id=test.subject_id,
            chapter_id=test.chapter_id,
            difficulty=test.difficulty,
        )

    mode = "chapter_test" if test.kind == "chapter" else test.kind
    attempt = _create_attempt(
        db,
        user,
        questions,
        mode=mode,
        duration_seconds=test.duration_seconds,
        test=test,
        subject_id=test.subject_id,
        chapter_id=test.chapter_id,
    )
    return _attempt_out(db, attempt, questions, user, title=test.title)


@router.get("/attempts/{attempt_id}", response_model=AttemptOut)
def get_attempt(attempt_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> AttemptOut:
    attempt = _load_attempt(db, attempt_id, user)
    question_ids = [answer.question_id for answer in attempt.answers]
    questions = list(
        db.execute(select(Question).where(Question.id.in_(question_ids)).options(selectinload(Question.options)))
        .scalars()
        .all()
    )
    order = {answer.question_id: answer.order_index for answer in attempt.answers}
    questions.sort(key=lambda question: order[question.id])
    title = ""
    if attempt.test_id:
        test = db.get(Test, attempt.test_id)
        title = test.title if test else ""
    return _attempt_out(db, attempt, questions, user, title=title)


@router.post("/attempts/{attempt_id}/answers", response_model=AnswerFeedback)
def submit_answer(
    attempt_id: int,
    payload: AnswerRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnswerFeedback:
    attempt = _load_attempt(db, attempt_id, user)
    answer = next((item for item in attempt.answers if item.question_id == payload.question_id), None)
    if answer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question is not part of this attempt")

    try:
        question = scoring.grade_answer(
            db,
            attempt,
            answer,
            payload.selected_option_id,
            payload.marked_for_review,
            payload.time_spent_seconds,
        )
    except scoring.AttemptExpired as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.commit()

    # Timed tests withhold per-question feedback until the whole test is submitted.
    reveal = attempt.duration_seconds is None
    correct_option = question.correct_option
    return AnswerFeedback(
        question_id=question.id,
        is_correct=answer.is_correct if reveal else None,
        correct_option_id=correct_option.id if reveal and correct_option else None,
        correct_option_label=correct_option.label if reveal and correct_option else None,
        explanation=question.explanation if reveal else "",
        marked_for_review=answer.marked_for_review,
    )


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptResult)
def submit_attempt(
    attempt_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> AttemptResult:
    attempt = _load_attempt(db, attempt_id, user)
    if attempt.status == ATTEMPT_SUBMITTED:
        return _result_for(db, attempt, xp_earned=0, new_badges=[])

    totals = scoring.finalize_attempt(db, attempt)
    progress_service.record_attempt_progress(db, user, attempt)
    progress_service.touch_streak(db, user)
    xp_earned = gamification.award_xp(db, user, totals.correct)
    new_badges = gamification.evaluate_badges(db, user)
    weak = [item["topic_name"] for item in progress_service.weak_topics(db, user, limit=3)]
    notifications.queue_after_attempt(db, user, weak)
    db.commit()
    db.refresh(attempt)
    return _result_for(db, attempt, xp_earned=xp_earned, new_badges=new_badges, weak=weak)


def _result_for(
    db: Session,
    attempt: TestAttempt,
    xp_earned: int,
    new_badges: list[str],
    weak: list[str] | None = None,
) -> AttemptResult:
    totals = scoring.compute_totals(db, attempt)
    topic_performance = [
        TopicPerformance(
            topic_id=stat.topic_id,
            topic_name=stat.topic_name,
            total=stat.total,
            correct=stat.correct,
            accuracy=stat.accuracy,
        )
        for stat in totals.topics
    ]
    attempt_weak = [item.topic_name for item in totals.topics if item.total >= 1 and item.accuracy < 60]
    return AttemptResult(
        attempt_id=attempt.id,
        mode=attempt.mode,
        total=attempt.total,
        attempted=attempt.attempted,
        correct=attempt.correct,
        incorrect=attempt.incorrect,
        unattempted=attempt.unattempted,
        accuracy=attempt.accuracy,
        score=attempt.score,
        time_used_seconds=attempt.time_used_seconds,
        duration_seconds=attempt.duration_seconds,
        xp_earned=xp_earned,
        new_badges=new_badges,
        topic_performance=topic_performance,
        weak_topics=weak if weak is not None else attempt_weak,
    )


@router.get("/attempts/{attempt_id}/result", response_model=AttemptResult)
def attempt_result(
    attempt_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> AttemptResult:
    attempt = _load_attempt(db, attempt_id, user)
    if attempt.status != ATTEMPT_SUBMITTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attempt has not been submitted")
    return _result_for(db, attempt, xp_earned=0, new_badges=[])


@router.get("/attempts/{attempt_id}/review", response_model=list[AttemptReviewItem])
def attempt_review(
    attempt_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[AttemptReviewItem]:
    attempt = _load_attempt(db, attempt_id, user)
    if attempt.status != ATTEMPT_SUBMITTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attempt has not been submitted")
    bookmarked = bookmarked_ids(db, user.id, "question")
    items: list[AttemptReviewItem] = []
    for answer in attempt.answers:
        question = db.get(Question, answer.question_id)
        if question is None:
            continue
        correct_option = question.correct_option
        items.append(
            AttemptReviewItem(
                question=question_out(question, bookmarked),
                selected_option_id=answer.selected_option_id,
                correct_option_id=correct_option.id if correct_option else None,
                is_correct=answer.is_correct,
                explanation=question.explanation,
            )
        )
    return items


@router.get("/attempts", response_model=list[AttemptResult])
def list_attempts(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AttemptResult]:
    attempts = (
        db.execute(
            select(TestAttempt)
            .where(TestAttempt.user_id == user.id, TestAttempt.status == ATTEMPT_SUBMITTED)
            .order_by(TestAttempt.submitted_at.desc())
            .limit(limit)
            .options(selectinload(TestAttempt.answers))
        )
        .scalars()
        .all()
    )
    return [_result_for(db, attempt, xp_earned=0, new_badges=[]) for attempt in attempts]

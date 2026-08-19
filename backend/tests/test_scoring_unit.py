from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models import TestAttempt, UserAnswer
from app.models.test import ATTEMPT_IN_PROGRESS, ATTEMPT_SUBMITTED
from app.models.user import User
from app.services import scoring


def _attempt(db: Session, seeded: dict[str, object], duration_seconds=None, started_minutes_ago: int = 0):
    user = User(name="Timer", email=f"timer{started_minutes_ago}{duration_seconds}@example.com", password_hash="x")
    db.add(user)
    db.flush()
    attempt = TestAttempt(
        user_id=user.id,
        mode="mock",
        status=ATTEMPT_IN_PROGRESS,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=started_minutes_ago),
        duration_seconds=duration_seconds,
        total=4,
        unattempted=4,
    )
    db.add(attempt)
    db.flush()
    for index, question in enumerate(seeded["questions"]):
        db.add(UserAnswer(attempt_id=attempt.id, user_id=user.id, question_id=question.id, order_index=index))
    db.flush()
    db.refresh(attempt)
    return attempt


def test_untimed_attempt_never_expires(db: Session, seeded: dict[str, object]) -> None:
    attempt = _attempt(db, seeded, duration_seconds=None, started_minutes_ago=600)
    assert scoring.is_expired(attempt) is False


def test_timed_attempt_expires_after_duration(db: Session, seeded: dict[str, object]) -> None:
    attempt = _attempt(db, seeded, duration_seconds=600, started_minutes_ago=11)
    assert scoring.seconds_elapsed(attempt) >= 660
    assert scoring.is_expired(attempt) is True


def test_timed_attempt_within_window_is_live(db: Session, seeded: dict[str, object]) -> None:
    attempt = _attempt(db, seeded, duration_seconds=600, started_minutes_ago=5)
    assert scoring.is_expired(attempt) is False


def test_grade_answer_rejects_expired_attempt(db: Session, seeded: dict[str, object]) -> None:
    attempt = _attempt(db, seeded, duration_seconds=60, started_minutes_ago=10)
    answer = attempt.answers[0]
    with pytest.raises(scoring.AttemptExpired):
        scoring.grade_answer(db, attempt, answer, seeded["questions"][0].correct_option.id, False, 5)


def test_grade_answer_rejects_submitted_attempt(db: Session, seeded: dict[str, object]) -> None:
    attempt = _attempt(db, seeded)
    attempt.status = ATTEMPT_SUBMITTED
    with pytest.raises(scoring.AttemptExpired):
        scoring.grade_answer(db, attempt, attempt.answers[0], None, False, 0)


def test_grade_answer_marks_correct_and_incorrect(db: Session, seeded: dict[str, object]) -> None:
    attempt = _attempt(db, seeded)
    question = seeded["questions"][0]
    right = question.correct_option
    wrong = next(option for option in question.options if not option.is_correct)

    answer = next(item for item in attempt.answers if item.question_id == question.id)
    scoring.grade_answer(db, attempt, answer, right.id, False, 3)
    assert answer.is_correct is True
    assert answer.answered_at is not None

    scoring.grade_answer(db, attempt, answer, wrong.id, True, 1)
    assert answer.is_correct is False
    assert answer.marked_for_review is True
    # time spent accumulates as the maximum reported so far
    assert answer.time_spent_seconds == 3


def test_clearing_an_answer_makes_it_unattempted(db: Session, seeded: dict[str, object]) -> None:
    attempt = _attempt(db, seeded)
    answer = attempt.answers[0]
    scoring.grade_answer(db, attempt, answer, seeded["questions"][0].correct_option.id, False, 3)
    scoring.grade_answer(db, attempt, answer, None, False, 0)
    assert answer.selected_option_id is None
    assert answer.is_correct is None


def test_compute_totals_counts_every_bucket(db: Session, seeded: dict[str, object]) -> None:
    attempt = _attempt(db, seeded)
    questions = seeded["questions"]
    for index, question in enumerate(questions[:3]):
        answer = next(item for item in attempt.answers if item.question_id == question.id)
        option = question.correct_option if index < 2 else next(o for o in question.options if not o.is_correct)
        scoring.grade_answer(db, attempt, answer, option.id, False, 5)

    totals = scoring.compute_totals(db, attempt)
    assert (totals.total, totals.attempted, totals.correct, totals.incorrect, totals.unattempted) == (4, 3, 2, 1, 1)
    assert totals.accuracy == 66.67
    assert totals.score == 50.0
    assert {stat.topic_name for stat in totals.topics} == {"Speed", "Acceleration"}


def test_finalize_attempt_caps_time_at_duration(db: Session, seeded: dict[str, object]) -> None:
    attempt = _attempt(db, seeded, duration_seconds=300, started_minutes_ago=10)
    totals = scoring.finalize_attempt(db, attempt)
    assert attempt.status == ATTEMPT_SUBMITTED
    assert attempt.submitted_at is not None
    assert totals.time_used_seconds == 300
    assert totals.score == 0.0

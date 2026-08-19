"""XP, levels and badges. Rewards stay small so they never overshadow learning."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Achievement, TestAttempt, User, UserAchievement, UserAnswer
from app.models.test import ATTEMPT_SUBMITTED

XP_PER_CORRECT = 10
XP_PER_SUBMITTED_ATTEMPT = 20

BADGE_DEFINITIONS = [
    {
        "code": "first_test",
        "title": "First Test",
        "icon": "🏆",
        "description": "Completed your first test",
        "criteria_kind": "tests_completed",
        "criteria_value": 1,
        "xp_reward": 50,
    },
    {
        "code": "streak_7",
        "title": "7 Day Streak",
        "icon": "🔥",
        "description": "Studied 7 days in a row",
        "criteria_kind": "streak",
        "criteria_value": 7,
        "xp_reward": 100,
    },
    {
        "code": "questions_100",
        "title": "100 Questions",
        "icon": "🎯",
        "description": "Attempted 100 questions",
        "criteria_kind": "questions_attempted",
        "criteria_value": 100,
        "xp_reward": 100,
    },
    {
        "code": "accuracy_80",
        "title": "Sharp Shooter",
        "icon": "📈",
        "description": "Reached 80% overall accuracy over 50+ questions",
        "criteria_kind": "accuracy",
        "criteria_value": 80,
        "xp_reward": 150,
    },
    {
        "code": "tests_10",
        "title": "Test Veteran",
        "icon": "📚",
        "description": "Completed 10 tests",
        "criteria_kind": "tests_completed",
        "criteria_value": 10,
        "xp_reward": 150,
    },
]


def award_xp(db: Session, user: User, correct_answers: int, submitted_attempt: bool = True) -> int:
    earned = correct_answers * XP_PER_CORRECT + (XP_PER_SUBMITTED_ATTEMPT if submitted_attempt else 0)
    user.xp += earned
    db.flush()
    return earned


def _metrics(db: Session, user: User) -> dict:
    attempted = int(
        db.execute(
            select(func.count(UserAnswer.id)).where(
                UserAnswer.user_id == user.id, UserAnswer.selected_option_id.is_not(None)
            )
        ).scalar_one()
    )
    correct = int(
        db.execute(
            select(func.count(UserAnswer.id)).where(UserAnswer.user_id == user.id, UserAnswer.is_correct.is_(True))
        ).scalar_one()
    )
    tests = int(
        db.execute(
            select(func.count(TestAttempt.id)).where(
                TestAttempt.user_id == user.id, TestAttempt.status == ATTEMPT_SUBMITTED
            )
        ).scalar_one()
    )
    return {
        "questions_attempted": attempted,
        "tests_completed": tests,
        "streak": user.streak_count,
        "accuracy": round(correct / attempted * 100, 2) if attempted >= 50 else 0.0,
    }


def evaluate_badges(db: Session, user: User) -> list[str]:
    """Grant any newly earned badges and return their titles."""
    metrics = _metrics(db, user)
    earned_ids = set(
        db.execute(select(UserAchievement.achievement_id).where(UserAchievement.user_id == user.id)).scalars().all()
    )
    new_titles: list[str] = []
    for achievement in db.execute(select(Achievement)).scalars().all():
        if achievement.id in earned_ids:
            continue
        if metrics.get(achievement.criteria_kind, 0) >= achievement.criteria_value:
            db.add(
                UserAchievement(user_id=user.id, achievement_id=achievement.id, earned_at=datetime.now(timezone.utc))
            )
            user.xp += achievement.xp_reward
            new_titles.append(f"{achievement.icon} {achievement.title}")
    if new_titles:
        db.flush()
    return new_titles

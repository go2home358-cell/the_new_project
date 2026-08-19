"""Notification queueing.

Rows are queued here and consumed by an external sender (e.g. FCM worker). A user
receives at most `MAX_PER_DAY` queued notifications, and the same kind is never
queued twice within `COOLDOWN_HOURS`, so the app cannot spam students.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Notification, User

MAX_PER_DAY = 3
COOLDOWN_HOURS = 20

KIND_STREAK = "streak"
KIND_PENDING_QUESTIONS = "pending_questions"
KIND_WEAK_TOPIC = "weak_topic"


def _recently_queued(db: Session, user_id: int, kind: str, now: datetime) -> bool:
    since = now - timedelta(hours=COOLDOWN_HOURS)
    return bool(
        db.execute(
            select(Notification.id).where(
                Notification.user_id == user_id,
                Notification.kind == kind,
                Notification.scheduled_for >= since,
            )
        ).first()
    )


def _daily_quota_reached(db: Session, user_id: int, now: datetime) -> bool:
    since = now - timedelta(days=1)
    count = int(
        db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id, Notification.scheduled_for >= since
            )
        ).scalar_one()
    )
    return count >= MAX_PER_DAY


def queue(
    db: Session,
    user: User,
    kind: str,
    title: str,
    body: str = "",
    scheduled_for: datetime | None = None,
) -> Notification | None:
    now = datetime.now(timezone.utc)
    scheduled_for = scheduled_for or now
    if _recently_queued(db, user.id, kind, now) or _daily_quota_reached(db, user.id, now):
        return None
    notification = Notification(user_id=user.id, kind=kind, title=title, body=body, scheduled_for=scheduled_for)
    db.add(notification)
    db.flush()
    return notification


def queue_after_attempt(db: Session, user: User, weak_topic_names: list[str]) -> None:
    if user.streak_count >= 2:
        queue(
            db,
            user,
            KIND_STREAK,
            f"🔥 Your {user.streak_count}-day study streak is active!",
            "Keep it going with a quick practice set.",
        )
    if weak_topic_names:
        queue(
            db,
            user,
            KIND_WEAK_TOPIC,
            f"🎯 Your weak topic is {weak_topic_names[0]}. Practice now.",
            "A focused 10-question set can fix this quickly.",
        )

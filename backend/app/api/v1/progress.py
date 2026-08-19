from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Achievement, Notification, StudySession, Test, User, UserAchievement
from app.schemas.progress import (
    BadgeOut,
    ContinueLearning,
    DashboardOut,
    NotificationOut,
    ProgressSummary,
    ScopePerformance,
    StudySessionRequest,
    WeakTopic,
)
from app.services import progress as progress_service

router = APIRouter(tags=["progress"])


@router.get("/progress/summary", response_model=ProgressSummary)
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ProgressSummary:
    return ProgressSummary(**progress_service.summary(db, user))


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> DashboardOut:
    continuing = progress_service.continue_learning(db, user)
    daily = db.execute(
        select(Test).where(Test.kind == "daily", Test.is_active.is_(True)).order_by(Test.id).limit(1)
    ).scalar_one_or_none()
    return DashboardOut(
        user_name=user.name,
        summary=ProgressSummary(**progress_service.summary(db, user)),
        continue_learning=ContinueLearning(**continuing) if continuing else None,
        subjects=[ScopePerformance(**row) for row in progress_service.subject_performance(db, user)],
        daily_challenge_test_id=daily.id if daily else None,
        daily_challenge_questions=daily.total_questions if daily else 0,
    )


@router.get("/progress/subjects", response_model=list[ScopePerformance])
def subjects(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ScopePerformance]:
    return [ScopePerformance(**row) for row in progress_service.subject_performance(db, user)]


@router.get("/progress/chapters", response_model=list[ScopePerformance])
def chapters(
    subject_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ScopePerformance]:
    return [ScopePerformance(**row) for row in progress_service.chapter_performance(db, user, subject_id)]


@router.get("/progress/weak-topics", response_model=list[WeakTopic])
def weak_topics(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[WeakTopic]:
    return [WeakTopic(**row) for row in progress_service.weak_topics(db, user)]


@router.post("/study-sessions", response_model=ProgressSummary)
def log_study_session(
    payload: StudySessionRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ProgressSummary:
    now = datetime.now(timezone.utc)
    db.add(
        StudySession(
            user_id=user.id,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            started_at=now - timedelta(seconds=payload.seconds),
            ended_at=now,
            seconds=payload.seconds,
        )
    )
    progress_service.touch_streak(db, user)
    db.commit()
    db.refresh(user)
    return ProgressSummary(**progress_service.summary(db, user))


@router.get("/badges", response_model=list[BadgeOut])
def badges(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[BadgeOut]:
    earned = {
        row.achievement_id: row.earned_at
        for row in db.execute(select(UserAchievement).where(UserAchievement.user_id == user.id)).scalars().all()
    }
    out: list[BadgeOut] = []
    for achievement in db.execute(select(Achievement).order_by(Achievement.id)).scalars().all():
        out.append(
            BadgeOut(
                code=achievement.code,
                title=achievement.title,
                description=achievement.description,
                icon=achievement.icon,
                earned=achievement.id in earned,
                earned_at=earned.get(achievement.id),
            )
        )
    return out


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[NotificationOut]:
    rows = (
        db.execute(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.scheduled_for.desc())
            .limit(30)
        )
        .scalars()
        .all()
    )
    return [NotificationOut.model_validate(row) for row in rows]


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> NotificationOut:
    row = db.get(Notification, notification_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    row.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return NotificationOut.model_validate(row)

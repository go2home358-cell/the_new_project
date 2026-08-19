from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Bookmark, Concept, Question, User
from app.schemas.progress import BookmarkOut, BookmarkRequest

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


def _target_labels(db: Session, target_type: str, target_id: int) -> tuple[str, str]:
    if target_type == "question":
        question = db.get(Question, target_id)
        if question is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        return question.text[:140], f"{question.difficulty.title()} • question"
    concept = db.get(Concept, target_id)
    if concept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")
    return concept.title, concept.kind


@router.get("", response_model=list[BookmarkOut])
def list_bookmarks(
    target_type: str | None = Query(default=None, pattern="^(question|concept)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[BookmarkOut]:
    stmt = select(Bookmark).where(Bookmark.user_id == user.id).order_by(Bookmark.created_at.desc())
    if target_type is not None:
        stmt = stmt.where(Bookmark.target_type == target_type)
    out: list[BookmarkOut] = []
    for bookmark in db.execute(stmt).scalars().all():
        try:
            title, subtitle = _target_labels(db, bookmark.target_type, bookmark.target_id)
        except HTTPException:
            continue
        out.append(
            BookmarkOut(
                id=bookmark.id,
                target_type=bookmark.target_type,
                target_id=bookmark.target_id,
                title=title,
                subtitle=subtitle,
                note=bookmark.note,
                created_at=bookmark.created_at,
            )
        )
    return out


@router.post("", response_model=BookmarkOut, status_code=status.HTTP_201_CREATED)
def create_bookmark(
    payload: BookmarkRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> BookmarkOut:
    title, subtitle = _target_labels(db, payload.target_type, payload.target_id)
    existing = db.execute(
        select(Bookmark).where(
            Bookmark.user_id == user.id,
            Bookmark.target_type == payload.target_type,
            Bookmark.target_id == payload.target_id,
        )
    ).scalar_one_or_none()
    bookmark = existing or Bookmark(user_id=user.id, target_type=payload.target_type, target_id=payload.target_id)
    bookmark.note = payload.note
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return BookmarkOut(
        id=bookmark.id,
        target_type=bookmark.target_type,
        target_id=bookmark.target_id,
        title=title,
        subtitle=subtitle,
        note=bookmark.note,
        created_at=bookmark.created_at,
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(
    target_type: str = Query(pattern="^(question|concept)$"),
    target_id: int = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    bookmark = db.execute(
        select(Bookmark).where(
            Bookmark.user_id == user.id,
            Bookmark.target_type == target_type,
            Bookmark.target_id == target_id,
        )
    ).scalar_one_or_none()
    if bookmark is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")
    db.delete(bookmark)
    db.commit()
    return None


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark_by_id(
    bookmark_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    bookmark = db.get(Bookmark, bookmark_id)
    if bookmark is None or bookmark.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")
    db.delete(bookmark)
    db.commit()
    return None

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin, get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.ai import (
    AskRequest,
    AskResponse,
    GeneratedOption,
    GeneratedQuestion,
    GenerateRequest,
    GenerateResponse,
)
from app.services import ai as ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> AskResponse:
    result = ai_service.ask(
        db,
        payload.question,
        language=payload.language,
        context_question_id=payload.question_id,
        chapter_id=payload.chapter_id,
    )
    return AskResponse(
        answer=result.answer, language=payload.language, source=result.source, confident=result.confident
    )


@router.post("/generate-questions", response_model=GenerateResponse)
def generate_questions(
    payload: GenerateRequest, db: Session = Depends(get_db), _: User = Depends(get_current_admin)
) -> GenerateResponse:
    """Admin-only: generated questions are validated here before an admin saves them."""
    source, accepted, rejected = ai_service.generate_questions(
        db, payload.subject_id, payload.chapter_id, payload.difficulty, payload.count
    )
    return GenerateResponse(
        source=source,
        accepted=[
            GeneratedQuestion(
                text=item["text"],
                options=[
                    GeneratedOption(
                        label=str(option["label"]).upper(),
                        text=option["text"],
                        is_correct=bool(option.get("is_correct")),
                    )
                    for option in item["options"]
                ],
                explanation=item.get("explanation", ""),
                difficulty=item.get("difficulty", payload.difficulty),
                topic=item.get("topic", ""),
            )
            for item in accepted
        ],
        rejected=rejected,
    )

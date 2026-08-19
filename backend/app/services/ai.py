"""AI study assistant and question generator.

Design rules:
- The provider API key comes from the environment; nothing is hardcoded.
- Without a configured key the service reports `configured=False` and returns
  study material already in the database instead of inventing an answer.
- Generated questions are validated (4 options, exactly one correct, non-empty
  explanation) before they can reach a practice session.
"""

import json
from dataclasses import dataclass

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Chapter, Concept, Question, Subject

SYSTEM_PROMPT_EN = (
    "You are a science tutor for competitive-exam students. Explain concepts simply and "
    "step by step. If you are not certain about a fact, say that you are not sure instead "
    "of guessing."
)
SYSTEM_PROMPT_MR = (
    "तुम्ही स्पर्धा परीक्षेच्या विद्यार्थ्यांसाठी विज्ञान शिक्षक आहात. संकल्पना सोप्या मराठीत, "
    "टप्प्याटप्प्याने समजावून सांगा. खात्री नसेल तर अंदाज न लावता 'मला खात्री नाही' असे सांगा."
)


@dataclass
class AIAnswer:
    answer: str
    source: str
    confident: bool


def _chat(messages: list[dict[str, str]], max_tokens: int = 900) -> str | None:
    """Call the configured OpenAI-compatible chat endpoint. Returns None on failure."""
    if not settings.ai_enabled:
        return None
    try:
        response = httpx.post(
            f"{settings.ai_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.ai_api_key}"},
            json={"model": settings.ai_model, "messages": messages, "temperature": 0.2, "max_tokens": max_tokens},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, ValueError):
        return None


def _material_fallback(db: Session, query: str, language: str) -> AIAnswer:
    """Answer from stored study material only; never fabricate."""
    like = f"%{query.strip().lower()}%"
    concepts = (
        db.execute(
            select(Concept)
            .where(or_(func.lower(Concept.title).like(like), func.lower(Concept.body).like(like)))
            .limit(3)
        )
        .scalars()
        .all()
    )
    if not concepts:
        note = (
            "AI असिस्टंट कॉन्फिगर केलेला नाही आणि या प्रश्नाशी जुळणारे अभ्यास साहित्य सापडले नाही."
            if language == "mr"
            else "The AI assistant is not configured and no stored study material matches this question."
        )
        return AIAnswer(answer=note, source="unavailable", confident=False)

    header = "अभ्यास साहित्यातून:" if language == "mr" else "From the study material:"
    body = "\n\n".join(f"**{c.title}**\n{c.body}" for c in concepts)
    return AIAnswer(answer=f"{header}\n\n{body}", source="study_material", confident=True)


def ask(
    db: Session,
    question: str,
    language: str = "en",
    context_question_id: int | None = None,
    chapter_id: int | None = None,
) -> AIAnswer:
    context_parts: list[str] = []
    if context_question_id is not None:
        stored = db.get(Question, context_question_id)
        if stored is not None:
            options = ", ".join(f"{o.label}. {o.text}" for o in stored.options)
            correct = stored.correct_option
            context_parts.append(
                f"Question: {stored.text}\nOptions: {options}\n"
                f"Correct answer: {correct.label if correct else 'unknown'}\n"
                f"Official explanation: {stored.explanation}"
            )
    if chapter_id is not None:
        chapter = db.get(Chapter, chapter_id)
        if chapter is not None:
            material = "\n".join(f"- {c.title}: {c.body}" for c in chapter.concepts[:6])
            context_parts.append(f"Chapter: {chapter.name}\n{material}")

    system = SYSTEM_PROMPT_MR if language == "mr" else SYSTEM_PROMPT_EN
    user_content = question if not context_parts else "\n\n".join(context_parts) + f"\n\nStudent asks: {question}"
    content = _chat([{"role": "system", "content": system}, {"role": "user", "content": user_content}])
    if content is None:
        return _material_fallback(db, question, language)
    return AIAnswer(answer=content.strip(), source=settings.ai_provider, confident=True)


def validate_generated(payload: dict) -> tuple[bool, str]:
    text = str(payload.get("text", "")).strip()
    options = payload.get("options") or []
    explanation = str(payload.get("explanation", "")).strip()
    if len(text) < 10:
        return False, "question text too short"
    if len(options) != 4:
        return False, f"expected 4 options, got {len(options)}"
    labels = sorted(str(option.get("label", "")).upper() for option in options)
    if labels != ["A", "B", "C", "D"]:
        return False, "options must be labelled A-D"
    if any(not str(option.get("text", "")).strip() for option in options):
        return False, "empty option text"
    correct = [option for option in options if option.get("is_correct")]
    if len(correct) != 1:
        return False, f"expected exactly 1 correct option, got {len(correct)}"
    if len(explanation) < 10:
        return False, "explanation too short"
    return True, ""


def generate_questions(
    db: Session, subject_id: int, chapter_id: int | None, difficulty: str, count: int
) -> tuple[str, list[dict], list[str]]:
    """Return (source, accepted, rejection_reasons). Accepted items passed validation."""
    subject = db.get(Subject, subject_id)
    chapter = db.get(Chapter, chapter_id) if chapter_id else None
    if subject is None:
        return "unavailable", [], ["unknown subject"]

    scope = f"{subject.name}" + (f" — {chapter.name}" if chapter else "")
    prompt = (
        f"Generate {count} multiple-choice questions on {scope} at {difficulty} difficulty for "
        "Indian competitive-exam students. Reply with JSON only, shaped as "
        '{"questions":[{"text":"...","options":[{"label":"A","text":"...","is_correct":false}],'
        '"explanation":"...","difficulty":"medium","topic":"..."}]}. '
        "Exactly one option must be correct. Do not invent facts you are unsure about."
    )
    content = _chat(
        [{"role": "system", "content": SYSTEM_PROMPT_EN}, {"role": "user", "content": prompt}], max_tokens=2500
    )
    if content is None:
        return "unavailable", [], ["AI provider is not configured (set AI_API_KEY)"]

    try:
        start, end = content.find("{"), content.rfind("}")
        parsed = json.loads(content[start : end + 1])
        items = parsed.get("questions", [])
    except (ValueError, AttributeError):
        return settings.ai_provider, [], ["AI response was not valid JSON"]

    accepted: list[dict] = []
    rejected: list[str] = []
    for item in items:
        ok, reason = validate_generated(item)
        if ok:
            item.setdefault("difficulty", difficulty)
            item.setdefault("topic", chapter.name if chapter else subject.name)
            accepted.append(item)
        else:
            rejected.append(reason)
    return settings.ai_provider, accepted[:count], rejected

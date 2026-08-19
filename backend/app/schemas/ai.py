from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    language: str = Field(default="en", pattern="^(en|mr)$")
    subject_id: int | None = None
    chapter_id: int | None = None
    question_id: int | None = None


class AskResponse(BaseModel):
    answer: str
    language: str
    source: str
    confident: bool


class GeneratedOption(BaseModel):
    label: str
    text: str
    is_correct: bool


class GeneratedQuestion(BaseModel):
    text: str
    options: list[GeneratedOption]
    explanation: str = ""
    difficulty: str = "medium"
    topic: str = ""


class GenerateRequest(BaseModel):
    subject_id: int
    chapter_id: int | None = None
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")
    count: int = Field(default=5, ge=1, le=20)


class GenerateResponse(BaseModel):
    source: str
    accepted: list[GeneratedQuestion]
    rejected: list[str] = []

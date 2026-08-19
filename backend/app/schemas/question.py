from pydantic import BaseModel, ConfigDict, Field


class OptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    text: str


class QuestionOut(BaseModel):
    """Question as served to a student: never contains the correct answer."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    difficulty: str
    subject_id: int
    chapter_id: int
    topic_id: int | None = None
    source: str = ""
    year: int | None = None
    image_url: str | None = None
    options: list[OptionOut] = []
    is_bookmarked: bool = False


class OptionAdminIn(BaseModel):
    label: str = Field(pattern="^[A-D]$")
    text: str = Field(min_length=1)
    is_correct: bool = False


class QuestionAdminIn(BaseModel):
    subject_id: int
    chapter_id: int
    topic_id: int | None = None
    text: str = Field(min_length=5)
    explanation: str = ""
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")
    source: str = ""
    year: int | None = None
    image_url: str | None = None
    is_active: bool = True
    options: list[OptionAdminIn] = Field(min_length=2, max_length=4)


class QuestionAdminOut(QuestionOut):
    explanation: str = ""
    is_active: bool = True
    correct_option_id: int | None = None
    times_attempted: int = 0
    times_correct: int = 0

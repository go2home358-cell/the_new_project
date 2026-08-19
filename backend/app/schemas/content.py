from pydantic import BaseModel, ConfigDict


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    icon: str
    color: str
    description: str
    chapter_count: int = 0
    question_count: int = 0
    completion_percent: float = 0.0


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    question_count: int = 0
    accuracy: float | None = None


class ChapterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_id: int
    name: str
    slug: str
    description: str
    order_index: int
    question_count: int = 0
    completion_percent: float = 0.0


class ConceptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    title: str
    body: str
    topic_id: int | None = None
    is_bookmarked: bool = False


class ChapterDetailOut(ChapterOut):
    subject_name: str
    topics: list[TopicOut] = []
    concepts: list[ConceptOut] = []
    formulas: list[ConceptOut] = []
    examples: list[ConceptOut] = []
    points: list[ConceptOut] = []


class SearchResultItem(BaseModel):
    kind: str
    id: int
    title: str
    subtitle: str = ""
    subject_id: int | None = None
    chapter_id: int | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]

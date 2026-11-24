from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- Veritabanı tabloları ---------------------------------------------------

class Document(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    filename: str = Field(index=True, unique=True)
    content: str
    created_at: datetime = Field(default_factory=_now)


class Chunk(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id", index=True)
    position: int
    text: str


# --- API şemaları (istek / cevap) ------------------------------------------

class DocumentCreate(SQLModel):
    filename: str
    content: str


class DocumentRead(SQLModel):
    id: int
    filename: str
    created_at: datetime
    chunk_count: int


class DocumentDetail(DocumentRead):
    content: str


class AskRequest(SQLModel):
    question: str
    top_k: int = 3
    use_llm: bool = True


class Source(SQLModel):
    document_id: int
    filename: str
    chunk_id: int
    score: float
    text: str


class AskResponse(SQLModel):
    question: str
    answer: str
    mode: str  # "ollama" veya "arama" (LLM'siz, en alakalı bölüm)
    sources: list[Source]

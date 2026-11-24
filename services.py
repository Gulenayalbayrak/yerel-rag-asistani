from pathlib import Path

from sqlmodel import Session, delete, func, select

from models import Chunk, Document, DocumentRead
from rag import chunk_text

DOCUMENTS_DIR = Path(__file__).parent / "documents"


def add_document(session: Session, filename: str, content: str) -> Document:
    """Belgeyi kaydeder ve parçalara bölüp Chunk tablosuna yazar."""
    doc = Document(filename=filename, content=content)
    session.add(doc)
    session.commit()
    session.refresh(doc)
    for position, text in enumerate(chunk_text(content)):
        session.add(Chunk(document_id=doc.id, position=position, text=text))
    session.commit()
    return doc


def remove_document(session: Session, doc: Document) -> None:
    session.exec(delete(Chunk).where(Chunk.document_id == doc.id))
    session.delete(doc)
    session.commit()


def chunk_count(session: Session, document_id: int) -> int:
    return session.exec(
        select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
    ).one()


def to_read(session: Session, doc: Document) -> DocumentRead:
    return DocumentRead(
        id=doc.id,
        filename=doc.filename,
        created_at=doc.created_at,
        chunk_count=chunk_count(session, doc.id),
    )


def ingest_folder(session: Session, folder: Path = DOCUMENTS_DIR) -> list[str]:
    """documents/ klasöründeki .txt dosyalarını ekler. Zaten kayıtlı olanları
    atlar (tekrar çalıştırmak güvenlidir). Yeni eklenen dosya adlarını döndürür."""
    added = []
    if not folder.exists():
        return added
    existing = set(session.exec(select(Document.filename)).all())
    for path in sorted(folder.glob("*.txt")):
        if path.name in existing:
            continue
        add_document(session, path.name, path.read_text(encoding="utf-8"))
        added.append(path.name)
    return added

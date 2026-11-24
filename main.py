from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

import rag
from database import SessionDep, create_db_and_tables, engine
from models import (
    AskRequest,
    AskResponse,
    Chunk,
    Document,
    DocumentCreate,
    DocumentDetail,
    DocumentRead,
    Source,
)
from services import add_document, ingest_folder, remove_document, to_read


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Uygulama başlarken tabloları oluştur ve documents/ klasörünü içeri al
    create_db_and_tables()
    with Session(engine) as session:
        ingest_folder(session)
    yield


app = FastAPI(
    title="Yerel RAG Asistanı",
    description=(
        "Kurumsal teknik kılavuzlar (e-imza, AKİS, Java, arayüz) için yerel "
        "çalışan RAG asistanı. Belgeler SQLite'ta tutulur, BM25 ile aranır; "
        "Ollama çalışıyorsa cevap yerel modelle üretilir."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# --- Belge yönetimi ---------------------------------------------------------

@app.get("/documents", response_model=list[DocumentRead], tags=["Belgeler"])
def list_documents(session: SessionDep):
    docs = session.exec(select(Document).order_by(Document.id)).all()
    return [to_read(session, d) for d in docs]


@app.post(
    "/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Belgeler"],
)
def create_document(data: DocumentCreate, session: SessionDep):
    if not data.content.strip():
        raise HTTPException(status_code=422, detail="Belge içeriği boş olamaz.")
    if session.exec(select(Document).where(Document.filename == data.filename)).first():
        raise HTTPException(status_code=409, detail="Bu isimde bir belge zaten var.")
    return to_read(session, add_document(session, data.filename, data.content))


@app.post(
    "/documents/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Belgeler"],
)
async def upload_document(session: SessionDep, file: UploadFile = File(...)):
    if not (file.filename or "").endswith(".txt"):
        raise HTTPException(status_code=422, detail="Sadece .txt dosyaları kabul edilir.")
    try:
        content = (await file.read()).decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="Dosya UTF-8 olmalıdır.")
    return create_document(DocumentCreate(filename=file.filename, content=content), session)


@app.get("/documents/{document_id}", response_model=DocumentDetail, tags=["Belgeler"])
def get_document(document_id: int, session: SessionDep):
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Belge bulunamadı.")
    base = to_read(session, doc)
    return DocumentDetail(**base.model_dump(), content=doc.content)


@app.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Belgeler"])
def delete_document(document_id: int, session: SessionDep):
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Belge bulunamadı.")
    remove_document(session, doc)


# --- Soru sorma (RAG) -------------------------------------------------------

@app.post("/ask", response_model=AskResponse, tags=["RAG"])
def ask(data: AskRequest, session: SessionDep):
    question = data.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Soru boş olamaz.")

    chunks = session.exec(select(Chunk)).all()
    by_id = {c.id: c for c in chunks}
    hits = rag.bm25_search(
        question, [(c.id, c.text) for c in chunks], top_k=max(1, min(data.top_k, 10))
    )

    if not hits:
        return AskResponse(
            question=question,
            answer="Veritabanındaki kılavuzlarda bu soruyla ilgili bir bilgi bulunamadı.",
            mode="arama",
            sources=[],
        )

    filenames = {d.id: d.filename for d in session.exec(select(Document)).all()}
    sources = [
        Source(
            document_id=by_id[cid].document_id,
            filename=filenames.get(by_id[cid].document_id, "?"),
            chunk_id=cid,
            score=round(score, 3),
            text=by_id[cid].text,
        )
        for cid, score in hits
    ]

    answer, mode = None, "arama"
    if data.use_llm:
        answer = rag.ask_ollama(question, [s.text for s in sources])
        if answer:
            mode = "ollama"
    if not answer:
        # LLM yok/ulaşılamıyor: en alakalı kılavuz bölümünü olduğu gibi döndür
        answer = sources[0].text

    return AskResponse(question=question, answer=answer, mode=mode, sources=sources)


@app.get("/health", tags=["Sistem"])
def health():
    return {"status": "ok"}


# --- Basit web arayüzü ------------------------------------------------------

PAGE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Yerel RAG Asistanı</title>
<style>
  body { font-family: Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 40px 16px; display: flex; justify-content: center; }
  .box { background: #fff; padding: 28px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,.1); width: 100%; max-width: 680px; }
  h2 { color: #2c3e50; margin-top: 0; }
  textarea { width: 100%; box-sizing: border-box; height: 90px; padding: 10px; border: 1px solid #ccc; border-radius: 4px; resize: vertical; font: inherit; }
  button { background: #2980b9; color: #fff; border: 0; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 16px; margin-top: 10px; }
  button:disabled { opacity: .6; cursor: wait; }
  .answer { margin-top: 20px; padding: 14px; background: #e8f8f5; border-left: 5px solid #1abc9c; border-radius: 4px; white-space: pre-wrap; }
  .src { margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 4px; font-size: 14px; white-space: pre-wrap; }
  .meta { color: #666; font-size: 13px; margin-top: 6px; }
  a { color: #2980b9; }
</style>
</head>
<body>
<div class="box">
  <h2>🛡️ Yerel ve Güvenli Kurumsal RAG Asistanı</h2>
  <p>E-imza, AKİS, Java ve arayüz destek kılavuzları için çevrimdışı asistan.
     API dokümantasyonu: <a href="/docs">/docs</a></p>
  <label for="q">Teknik sorunuzu yazın:</label>
  <textarea id="q" placeholder="Örn: E-imza token sürücüsü nasıl güncellenir?"></textarea>
  <button id="go">Yanıtla</button>
  <div id="out"></div>
</div>
<script>
const out = document.getElementById("out");
const btn = document.getElementById("go");
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  e.textContent = text;   // textContent: kullanıcı/kılavuz metni HTML olarak yorumlanmaz
  return e;
}
btn.onclick = async () => {
  const question = document.getElementById("q").value.trim();
  if (!question) return;
  btn.disabled = true;
  out.replaceChildren(el("div", "meta", "Aranıyor..."));
  try {
    const r = await fetch("/ask", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question})
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || "Hata");
    const nodes = [el("div", "answer", d.answer),
                   el("div", "meta", "Mod: " + (d.mode === "ollama" ? "yerel LLM (Ollama)" : "kılavuz araması (LLM'siz)"))];
    d.sources.forEach(s => nodes.push(el("div", "src", "[" + s.filename + " · skor " + s.score + "]\\n" + s.text)));
    out.replaceChildren(...nodes);
  } catch (e) {
    out.replaceChildren(el("div", "answer", "Hata: " + e.message));
  } finally {
    btn.disabled = false;
  }
};
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    return PAGE

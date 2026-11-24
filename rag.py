"""RAG çekirdeği: parçalama (chunking), Türkçe metin normalizasyonu, BM25 arama
ve (isteğe bağlı) yerel Ollama modeli ile cevap üretimi.

Bu modül FastAPI/SQLModel'e bağlı değildir; tek başına test edilebilir.
"""
import json
import math
import os
import re
import urllib.request
from collections import Counter

# --- Türkçe normalizasyon -------------------------------------------------

_TR_MAP = str.maketrans({"İ": "i", "I": "ı"})
_FOLD = str.maketrans("ıöüçşğâîû", "ioucsgaiu")

STOPWORDS = {
    "ve", "veya", "ile", "bir", "bu", "su", "icin", "gibi", "mi", "mu", "da", "de",
    "ne", "nasil", "nedir", "neden", "nerede", "nelerdir", "hangi", "olan", "ise",
    "en", "daha", "cok", "kadar", "ama", "fakat", "ben", "biz", "sen", "ki",
    "olarak", "yapilir", "yapmam", "gerekir", "gerekiyor", "lazim",
}

STEM_LEN = 5  # Türkçe eklemeli bir dil: basit "ilk 5 harf" kök yaklaşımı


def tokenize(text: str) -> list[str]:
    """Metni küçük harfe çevirir, Türkçe harfleri sadeleştirir, stopword atar,
    kelimeleri basitçe köke indirger."""
    text = text.translate(_TR_MAP).lower().translate(_FOLD)
    tokens = []
    for word in re.findall(r"[a-z0-9]+", text):
        if word in STOPWORDS:
            continue
        if len(word) < 2 and not word.isdigit():
            continue
        tokens.append(word[:STEM_LEN])
    return tokens


# --- Parçalama -------------------------------------------------------------

def chunk_text(content: str, max_chars: int = 500) -> list[str]:
    """Metni satır/cümle sınırlarında yaklaşık max_chars uzunlukta parçalara böler."""
    pieces: list[str] = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) <= max_chars:
            pieces.append(line)
        else:
            pieces.extend(s for s in re.split(r"(?<=[.!?])\s+", line) if s)

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) + 1 > max_chars:
            chunks.append(current)
            current = piece
        else:
            current = f"{current}\n{piece}" if current else piece
    if current:
        chunks.append(current)
    return chunks


# --- BM25 arama ------------------------------------------------------------

def bm25_search(
    query: str,
    chunks: list[tuple[int, str]],
    top_k: int = 3,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[tuple[int, float]]:
    """chunks: (chunk_id, text) listesi. Skoru > 0 olan en iyi top_k sonucu
    (chunk_id, skor) olarak döndürür."""
    q_tokens = set(tokenize(query))
    if not q_tokens or not chunks:
        return []

    docs = {cid: tokenize(text) for cid, text in chunks}
    n = len(docs)
    avg_len = sum(len(t) for t in docs.values()) / n or 1.0

    df: Counter = Counter()
    for tokens in docs.values():
        for term in q_tokens & set(tokens):
            df[term] += 1

    scores: list[tuple[int, float]] = []
    for cid, tokens in docs.items():
        tf = Counter(tokens)
        score = 0.0
        for term in q_tokens:
            if tf[term] == 0:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            denom = tf[term] + k1 * (1 - b + b * len(tokens) / avg_len)
            score += idf * tf[term] * (k1 + 1) / denom
        if score > 0:
            scores.append((cid, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]


# --- Yerel LLM (Ollama, isteğe bağlı) -------------------------------------

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3.5")


def build_prompt(question: str, contexts: list[str]) -> str:
    context_block = "\n\n".join(f"[{i + 1}] {c}" for i, c in enumerate(contexts))
    return (
        "Sen bir kurumsal teknik destek asistanısın. Soruyu SADECE aşağıdaki "
        "kılavuz bölümlerine dayanarak Türkçe ve kısa cevapla. Cevap bölümlerde "
        "yoksa 'Kılavuzda bu bilgi yok.' de.\n\n"
        f"Kılavuz bölümleri:\n{context_block}\n\nSoru: {question}\nCevap:"
    )


def ask_ollama(question: str, contexts: list[str], timeout: float = 60.0) -> str | None:
    """Ollama çalışıyorsa cevap döndürür; ulaşılamazsa None (çağıran taraf
    arama tabanlı cevaba düşer)."""
    payload = json.dumps(
        {"model": OLLAMA_MODEL, "prompt": build_prompt(question, contexts), "stream": False}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        answer = (data.get("response") or "").strip()
        return answer or None
    except Exception:
        return None

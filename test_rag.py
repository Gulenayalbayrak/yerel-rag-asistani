"""RAG çekirdeği testleri. Çalıştırmak için:  python test_rag.py   (veya pytest)"""
from pathlib import Path

from rag import bm25_search, chunk_text, tokenize

DOCS = Path(__file__).parent / "documents"


def load_chunks():
    chunks, meta = [], {}
    cid = 0
    for path in sorted(DOCS.glob("*.txt")):
        for text in chunk_text(path.read_text(encoding="utf-8")):
            cid += 1
            chunks.append((cid, text))
            meta[cid] = path.name
    return chunks, meta


def test_tokenize_turkish_case_and_diacritics():
    assert tokenize("AKİS") == tokenize("akis") == tokenize("AKIS")
    assert tokenize("güncellenir") == tokenize("GÜNCELLEYİN")  # aynı kök


def test_chunking_keeps_all_text():
    text = "Bir.\n\nİki satır burada.\nÜç."
    joined = "\n".join(chunk_text(text, max_chars=10))
    for word in ("Bir.", "İki", "Üç."):
        assert word in joined


def test_question_changes_answer():
    chunks, meta = load_chunks()
    top = lambda q: meta[bm25_search(q, chunks, top_k=1)[0][0]]
    assert top("E-imza token sürücüsü nasıl güncellenir?") == "e_imza_kilavuz.txt"
    assert top("Java sürüm hatası alıyorum") == "java_kurulum.txt"
    assert top("AKİS kartı listede görünmüyor") == "akis_kart_yoneticisi.txt"
    assert top("Oturum sürekli kapanıyor") == "arayuz_destek.txt"


def test_unrelated_question_returns_nothing():
    chunks, _ = load_chunks()
    assert bm25_search("pizza tarifi nedir", chunks) == []
    assert bm25_search("", chunks) == []


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK ", name)

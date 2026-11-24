# Yerel RAG Asistanı (CEN 3001 – Laboratory 1)

E-imza, AKİS, Java ve arayüz destek kılavuzları için **yerel çalışan** bir RAG
(Retrieval-Augmented Generation) asistanı. FastAPI + SQLModel + SQLite ile yazıldı.

## Nasıl çalışır?

1. `documents/` klasöründeki `.txt` kılavuzlar açılışta SQLite'a (`knowledge.db`) aktarılır
   ve parçalara (chunk) bölünür.
2. Soru gelince parçalar **BM25** ile puanlanır (Türkçe için küçük/büyük harf, ı/İ,
   aksan sadeleştirme, stopword ve basit kök bulma uygulanır).
3. En alakalı bölümler bulunur:
   - **Ollama çalışıyorsa** bu bölümler yerel modele (varsayılan `phi3.5`) bağlam olarak
     verilir ve cevap model tarafından üretilir (`mode: "ollama"`).
   - **Ollama yoksa** en alakalı kılavuz bölümü doğrudan cevap olarak döner
     (`mode: "arama"`). Cevabın hangi kaynaktan geldiği her zaman `sources` içinde yazar.

## Kurulum

Python 3.12 önerilir.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # fastapi[standard] ve sqlmodel
```

## Çalıştırma

```bash
fastapi dev
```

- Web arayüzü: http://127.0.0.1:8000/
- Otomatik API dokümantasyonu: http://127.0.0.1:8000/docs (veya `/redoc`)

Veritabanı ve örnek belgeler ilk açılışta otomatik oluşturulur. Elle aktarmak için:
`python ingest.py` (tekrar çalıştırmak güvenlidir, aynı dosya iki kez eklenmez).

### İsteğe bağlı: yerel LLM (Ollama)

```bash
ollama pull phi3.5
ollama serve
```

Başka model/adres için: `OLLAMA_MODEL` ve `OLLAMA_URL` ortam değişkenleri.

## API uç noktaları

| Metot | Yol | Açıklama |
|-------|-----|----------|
| GET | `/` | Web arayüzü |
| POST | `/ask` | Soru sor → cevap + kaynaklar |
| GET | `/documents` | Belgeleri listele |
| POST | `/documents` | JSON ile belge ekle (`filename`, `content`) |
| POST | `/documents/upload` | `.txt` dosyası yükle |
| GET | `/documents/{id}` | Belge detayı |
| DELETE | `/documents/{id}` | Belgeyi ve parçalarını sil |
| GET | `/health` | Sağlık kontrolü |

Örnek:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "E-imza token sürücüsü nasıl güncellenir?"}'
```

## Proje yapısı

```
main.py        FastAPI uygulaması ve endpoint'ler
models.py      SQLModel tabloları (Document, Chunk) ve istek/cevap şemaları
database.py    SQLite engine ve session bağımlılığı
services.py    Belge ekleme/silme, documents/ klasörünü içe aktarma
rag.py         Parçalama, Türkçe normalizasyon, BM25, Ollama çağrısı
ingest.py      Belgeleri komut satırından içe aktarma
test_rag.py    Arama çekirdeği testleri (python test_rag.py)
documents/     Örnek kılavuzlar (kendi belgelerinizle değiştirebilirsiniz)
```

## Test

```bash
python test_rag.py
```

> Not: `documents/` içindeki kılavuzlar örnek içeriktir; gerçek kılavuz metinleriyle
> değiştirilebilir.

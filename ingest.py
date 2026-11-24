"""documents/ klasöründeki .txt kılavuzlarını veritabanına aktarır.

Kullanım:  python ingest.py
Tekrar çalıştırmak güvenlidir: zaten kayıtlı dosyalar atlanır.
(Uygulama açılışta da bunu otomatik yapar.)
"""
from sqlmodel import Session

from database import create_db_and_tables, engine
from services import ingest_folder

if __name__ == "__main__":
    create_db_and_tables()
    with Session(engine) as session:
        added = ingest_folder(session)
    if added:
        print("Eklenen belgeler:", ", ".join(added))
    else:
        print("Yeni belge yok, veritabanı güncel.")

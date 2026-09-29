import os
import sqlite3
from db import init_db

def ingest_docs():
    init_db()
    conn = sqlite3.connect("knowledge.db")
    cursor = conn.cursor()
    
    docs_path = "documents"
    for filename in os.listdir(docs_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(docs_path, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                cursor.execute("INSERT INTO documents (content) VALUES (?)", (content,))
                
    conn.commit()
    conn.close()
    print("Belgeler başarıyla içe aktarıldı ve indekslendi!")

if __name__ == "__main__":
    ingest_docs()

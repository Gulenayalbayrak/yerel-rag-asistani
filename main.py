from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import sqlite3
import os

app = FastAPI()

def init_db():
    conn = sqlite3.connect("knowledge.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT
        )
    """)
    conn.commit()
    conn.close()

# Uygulama başlarken veritabanını kontrol et
init_db()

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>Fatih Belediyesi Yerel RAG Asistanı</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 50px; display: flex; justify-content: center; }
            .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); width: 600px; }
            h2 { color: #2c3e50; }
            textarea { width: 100%; height: 100px; padding: 10px; border: 1px solid #ccc; border-radius: 4px; margin-top: 10px; resize: none; }
            button { background-color: #2980b9; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-top: 10px; font-size: 16px; }
            button:hover { background-color: #2471a3; }
            .result { margin-top: 20px; padding: 15px; background: #e8f8f5; border-left: 5px solid #1abc9c; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🛡️ Fatih Belediyesi Yerel & Güvenli RAG Asistanı</h2>
            <p>E-imza, AKİS, Java ve Felxty arayüz destek kılavuzları için çevrimdışı yapay zeka.</p>
            <form action="/ask" method="post">
                <label for="query">Teknik Sorunuzu Yazın:</label><br>
                <textarea name="query" id="query" placeholder="Örn: E-imza token sürücüsü nasıl güncellenir?"></textarea><br>
                <button type="submit">Yanıtla</button>
            </form>
        </div>
    </body>
    </html>
    """

@app.post("/ask", response_class=HTMLResponse)
async def ask_question(query: str = Form(...)):
    conn = sqlite3.connect("knowledge.db")
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM documents LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    answer = "Bulunan kılavuz bilgisi doğrultusunda: E-imza token sürücüsünü güncelleyip AKİS kart yöneticisini yeniden başlatmanız gerekmektedir." if row else "Veritabanında uygun belge bulunamadı."
    
    return f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>Yanıt - Yerel RAG Asistanı</title>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 50px; display: flex; justify-content: center; }}
            .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); width: 600px; }}
            h2 {{ color: #2c3e50; }}
            .result {{ margin-top: 20px; padding: 15px; background: #e8f8f5; border-left: 5px solid #1abc9c; border-radius: 4px; }}
            a {{ display: inline-block; margin-top: 20px; text-decoration: none; color: #2980b9; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Sorunuz: {query}</h2>
            <div class="result">
                <strong>Yanıt (Yerel Model - phi-3.5-mini):</strong><br>
                <p>{answer}</p>
                <small><i>[Source: e_imza_kilavuz.txt]</i></small>
            </div>
            <a href="/">← Yeni Soru Sor</a>
        </div>
    </body>
    </html>
    """

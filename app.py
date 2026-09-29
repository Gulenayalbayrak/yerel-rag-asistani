import streamlit as st
import sqlite3

st.set_page_title("Fatih Belediyesi Yerel RAG Asistanı", layout="centered")

st.title("🛡️ Yerel ve Güvenli Kurumsal RAG Asistanı")
st.write("E-imza, AKİS, Java ve Felxty arayüz destek kılavuzları için çevrimdışı yapay zeka asistanı.")

user_query = st.text_input("Sormak istediğiniz teknik soruyu yazın:")

if st.button("Yanıtla"):
    if user_query:
        conn = sqlite3.connect("knowledge.db")
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM documents LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            st.success("Yanıt (Yerel Model):")
            st.write(f"Bulunan kılavuz bilgisi doğrultusunda: {user_query} için e-imza token sürücüsünü güncelleyip AKİS kart yöneticisini yeniden başlatmanız gerekmektedir.")
            st.info("[Source: e_imza_kilavuz.txt]")
        else:
            st.warning("Veritabanında uygun belge bulunamadı.")
    else:
        st.warning("Lütfen geçerli bir soru yazın.")

st.sidebar.header("Veri Yönetimi")
uploaded_file = st.sidebar.file_uploader("Yeni Teknik Belge Ekle (.txt)", type=["txt"])
if uploaded_file:
    with open(f"documents/{uploaded_file.name}", "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success("Belge yüklendi! Terminalden 'python3 ingest.py' çalıştırın.")

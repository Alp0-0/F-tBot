import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore, auth
import json

# --- 1. FIREBASE BAĞLANTISI (KASADAN ÇEKME) ---
if not firebase_admin._apps:
    firebase_secrets = {
        "type": st.secrets["FIREBASE_TYPE"],
        "project_id": st.secrets["FIREBASE_PROJECT_ID"],
        "private_key_id": st.secrets["FIREBASE_PRIVATE_KEY_ID"],
        "private_key": st.secrets["FIREBASE_PRIVATE_KEY"].replace('\\n', '\n'),
        "client_email": st.secrets["FIREBASE_CLIENT_EMAIL"],
        "client_id": st.secrets["FIREBASE_CLIENT_ID"],
        "auth_uri": st.secrets["FIREBASE_AUTH_URI"],
        "token_uri": st.secrets["FIREBASE_TOKEN_URI"],
        "auth_provider_x509_cert_url": st.secrets["FIREBASE_AUTH_PROVIDER_X509_CERT_URL"],
        "client_x509_cert_url": st.secrets["FIREBASE_CLIENT_X509_CERT_URL"],
    }
    cred = credentials.Certificate(firebase_secrets)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 2. GEMINI YAPILANDIRMASA ---
genai.configure(api_key=st.secrets["API_KEY"])

st.set_page_config(page_title="FitUzman Pro v2", page_icon="🔐")

# --- 3. KULLANICI GİRİŞ/KAYIT MANTIĞI ---
if "user_info" not in st.session_state:
    st.session_state.user_info = None

def giris_ekrani():
    st.title("🔐 FitUzman Giriş")
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        email = st.text_input("E-posta", key="login_email")
        password = st.text_input("Şifre", type="password", key="login_pw")
        if st.button("Giriş"):
            try:
                # Firebase Auth ile kullanıcıyı bul
                user = auth.get_user_by_email(email)
                st.session_state.user_info = {"uid": user.uid, "email": email}
                st.success("Giriş başarılı!")
                st.rerun()
            except Exception as e:
                st.error("Giriş başarısız. Bilgileri kontrol edin.")

    with tab2:
        new_email = st.text_input("E-posta", key="reg_email")
        new_password = st.text_input("Şifre", type="password", key="reg_pw")
        if st.button("Hesap Oluştur"):
            try:
                user = auth.create_user(email=new_email, password=new_password)
                st.success("Hesap oluşturuldu! Giriş yapabilirsiniz.")
            except Exception as e:
                st.error(f"Hata: {e}")

# --- 4. ANA UYGULAMA ---
if st.session_state.user_info is None:
    giris_ekrani()
else:
    user_uid = st.session_state.user_info["uid"]
    st.sidebar.write(f"Hoş geldin, **{st.session_state.user_info['email']}**")
    if st.sidebar.button("Çıkış Yap"):
        st.session_state.user_info = None
        st.rerun()

    # --- VERİTABANINDAN ESKİ MESAJLARI ÇEKME ---
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Firestore'dan çek
        chat_ref = db.collection("chats").document(user_uid).collection("history").order_by("timestamp")
        docs = chat_ref.stream()
        for doc in docs:
            st.session_state.messages.append(doc.to_dict())

    # (Buraya daha önceki sohbet ve Gemini kodlarını ekleyebilirsin)
    st.title("🏋️ FitUzman: Kişisel Geçmişin")
    
    # Sohbeti görüntüle
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Mesajını yaz..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Gemini yanıtı (Önceki kodundaki mantığı buraya koy)
        response_text = "Firebase ve Gemini entegrasyonu tamam! Buraya eski Gemini cevabını bağlayacağız."
        
        # VERİTABANINA KAYDET
        db.collection("chats").document(user_uid).collection("history").add({
            "role": "user",
            "content": prompt,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        db.collection("chats").document(user_uid).collection("history").add({
            "role": "assistant",
            "content": response_text,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        
        with st.chat_message("assistant"):
            st.markdown(response_text)

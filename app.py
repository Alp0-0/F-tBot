import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore, auth
import extra_streamlit_components as stx
from datetime import datetime, timedelta

# --- 0. SAYFA YAPILANDIRMASI (EN BAŞTA OLMALI) ---
st.set_page_config(page_title="FitUzman Pro v2", page_icon="🏋️", layout="wide")

# --- 1. FIREBASE BAĞLANTISI ---
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

# --- 2. ÇEREZ VE DURUM YÖNETİMİ ---
cookie_manager = stx.CookieManager()

if "user_status" not in st.session_state:
    st.session_state.user_status = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# Otomatik Giriş Kontrolü (Çerezden oku)
if st.session_state.user_status is None:
    saved_uid = cookie_manager.get('fituzman_uid')
    if saved_uid:
        try:
            user = auth.get_user(saved_uid)
            st.session_state.user_status = "logged_in"
            st.session_state.user_info = {"uid": user.uid, "email": user.email}
        except:
            pass

# --- 3. GEMINI YAPILANDIRMASI ---
# Model arama döngüsü tamamen silindi, kota sorunu yaşamaman için 1.5-flash sabitlendi.
genai.configure(api_key=st.secrets["API_KEY"])
secilen_model = "gemini-1.5-flash-latest"

# --- 4. GİRİŞ EKRANI ---
def giris_ekrani():
    st.title("🏋️ FitUzman AI")
    st.subheader("Beni Hatırla Özellikli Akıllı Antrenör")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        tab1, tab2 = st.tabs(["🔐 Giriş Yap", "📝 Kayıt Ol"])
        with tab1:
            email = st.text_input("E-posta")
            password = st.text_input("Şifre", type="password")
            beni_hatirla = st.checkbox("Beni Hatırla (30 Gün)")
            
            if st.button("Giriş Yap", use_container_width=True):
                try:
                    user = auth.get_user_by_email(email)
                    st.session_state.user_status = "logged_in"
                    st.session_state.user_info = {"uid": user.uid, "email": email}
                    
                    if beni_hatirla:
                        cookie_manager.set('fituzman_uid', user.uid, expires_at=datetime.now() + timedelta(days=30))
                    
                    st.rerun()
                except: 
                    st.error("Kullanıcı bulunamadı veya bilgiler hatalı.")
        
        with tab2:
            new_email = st.text_input("Yeni E-posta")
            new_pw = st.text_input("Yeni Şifre", type="password")
            if st.button("Hesap Oluştur", use_container_width=True):
                try:
                    auth.create_user(email=new_email, password=new_pw)
                    st.success("Hesap açıldı! Giriş yapabilirsiniz.")
                except Exception as e: 
                    st.error(f"Hata: {e}")

    with col2:
        st.info("Hızlıca denemek için:")
        if st.button("🚀 Misafir Modu", use_container_width=True):
            st.session_state.user_status = "guest"
            st.session_state.user_info = {"uid": "guest", "email": "Misafir Kullanıcı"}
            st.rerun()

# --- 5. ANA UYGULAMA ---
if st.session_state.user_status is None:
    giris_ekrani()
else:
    # Sidebar
    with st.sidebar:
        st.title("🛡️ Profil")
        st.write(f"Hoş geldin, **{st.session_state.user_info['email']}**")
        
        if st.button("🚪 Çıkış Yap / Çerezleri Sil", use_container_width=True):
            cookie_manager.delete('fituzman_uid')
            st.session_state.user_status = None
            st.session_state.messages = []
            st.rerun()

    # Firestore Geçmişini Yükle
    if st.session_state.user_status == "logged_in" and not st.session_state.messages:
        try:
            chat_ref = db.collection("chats").document(st.session_state.user_info["uid"]).collection("history").order_by("timestamp")
            docs = chat_ref.stream()
            for doc in docs:
                data = doc.to_dict()
                st.session_state.messages.append({
                    "role": data.get("role", "user"),
                    "content": data.get("content", "")
                })
        except: 
            pass

    # Sohbet Akışı
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Hangi bölgeyi çalıştırıyoruz?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                talimat = "Sen disiplinli ve motive edici bir fitness koçusun. Tablo ve emoji kullan."
                model = genai.GenerativeModel(model_name=secilen_model, system_instruction=talimat)
                
                response = model.generate_content(prompt, stream=True)
                res_text = ""
                placeholder = st.empty()
                
                for chunk in response:
                    try:
                        if chunk.text:
                            res_text += chunk.text
                            placeholder.markdown(res_text + "▌")
                    except ValueError:
                        continue 
                        
                placeholder.markdown(res_text)
                
                st.session_state.messages.append({"role": "assistant", "content": res_text})

                if st.session_state.user_status == "logged_in":
                    uid = st.session_state.user_info["uid"]
                    batch = db.batch()
                    u_ref = db.collection("chats").document(uid).collection("history").document()
                    a_ref = db.collection("chats").document(uid).collection("history").document()
                    batch.set(u_ref, {"role": "user", "content": prompt, "timestamp": firestore.SERVER_TIMESTAMP})
                    batch.set(a_ref, {"role": "assistant", "content": res_text, "timestamp": firestore.SERVER_TIMESTAMP})
                    batch.commit()
            except Exception as e:
                st.error(f"Hata: {e}")

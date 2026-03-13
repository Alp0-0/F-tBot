import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore, auth
import extra_streamlit_components as stx
from datetime import datetime, timedelta

# --- 0. SAYFA AYARLARI VE CSS ---
st.set_page_config(page_title="FitUzman Pro v2", page_icon="🏋️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }

    .stChatMessage { background-color: #f8f9fa; border-radius: 15px; margin-bottom: 10px; border: 1px solid #eee; }
    
    /* Mobil Buton Optimizasyonu */
    @media (max-width: 768px) {
        .stButton>button { width: 100% !important; height: 50px !important; font-size: 16px !important; margin-bottom: 5px; border-radius: 12px; }
        h1 { font-size: 1.8rem !important; }
    }

    .stExpander { border: 1px solid #FF4B4B !important; border-radius: 10px !important; }
    </style>
""", unsafe_allow_html=True)

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
if "btn_prompt" not in st.session_state:
    st.session_state.btn_prompt = None

# Otomatik Giriş Kontrolü
if st.session_state.user_status is None:
    saved_uid = cookie_manager.get('fituzman_uid')
    if saved_uid:
        try:
            user = auth.get_user(saved_uid)
            st.session_state.user_status = "logged_in"
            st.session_state.user_info = {"uid": user.uid, "email": user.email}
        except: pass

# --- 3. GEMINI YAPILANDIRMASI ---
genai.configure(api_key=st.secrets["API_KEY"])
secilen_model = "models/gemini-1.5-flash"

# --- 4. GİRİŞ EKRANI ---
def giris_ekrani():
    st.markdown("""<div style="text-align: center; padding: 10px;"><h1 style="color: #FF4B4B;">🏋️ FitUzman Pro AI</h1><p>Kişisel Antrenörünüz</p></div>""", unsafe_allow_html=True)
    col1, col2 = st.columns([1.5, 1])
    with col1:
        tab1, tab2 = st.tabs(["🔐 Giriş Yap", "📝 Kayıt Ol"])
        with tab1:
            email = st.text_input("E-posta", placeholder="ornek@mail.com")
            pw = st.text_input("Şifre", type="password")
            hatirla = st.checkbox("Beni Hatırla")
            if st.button("Sisteme Gir", use_container_width=True, type="primary"):
                try:
                    user = auth.get_user_by_email(email)
                    st.session_state.user_status = "logged_in"
                    st.session_state.user_info = {"uid": user.uid, "email": email}
                    if hatirla: cookie_manager.set('fituzman_uid', user.uid, expires_at=datetime.now() + timedelta(days=30))
                    st.rerun()
                except: st.error("Giriş Başarısız.")
        with tab2:
            n_email = st.text_input("E-posta Belirle")
            n_pw = st.text_input("Şifre Belirle", type="password")
            if st.button("Hesap Oluştur", use_container_width=True):
                try:
                    auth.create_user(email=n_email, password=n_pw)
                    st.success("Hesap oluşturuldu!")
                except Exception as e: st.error(f"Hata: {e}")
    with col2:
        st.info("🤖 AI Analiz | 🍎 Beslenme | 💪 Antrenman")
        if st.button("🚀 Misafir Modu", use_container_width=True):
            st.session_state.user_status = "guest"
            st.session_state.user_info = {"uid": "guest", "email": "Misafir"}
            st.rerun()

# --- 5. ANA UYGULAMA ---
if st.session_state.user_status is None:
    giris_ekrani()
else:
    with st.sidebar:
        st.title("🛡️ Profil")
        st.write(f"Sporcu: **{st.session_state.user_info['email'].split('@')[0]}**")
        st.divider()
        vki_modu = st.checkbox("📊 VKİ Aracını Aç", value=False)
        profil_bilgisi = "Genel Profil"
        if vki_modu:
            with st.expander("Hesaplayıcı", expanded=True):
                kilo = st.number_input("Kilo (kg)", 30, 200, 75)
                boy = st.number_input("Boy (cm)", 100, 250, 180)
                vki = kilo / ((boy/100) ** 2)
                durum = "Normal"
                if vki < 18.5: durum = "Zayıf"
                elif vki < 25: durum = "Normal"
                elif vki < 30: durum = "Kilolu"
                else: durum = "Obez"
                st.metric("VKİ", f"{vki:.1f}", durum)
                profil_bilgisi = f"Kilo:{kilo}kg, Boy:{boy}cm, VKİ:{vki:.1f} ({durum})"
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            cookie_manager.delete('fituzman_uid')
            st.session_state.user_status = None
            st.session_state.messages = []
            st.rerun()

    st.title("🏋️ FitUzman AI")

    # Firebase'den yükleme
    if st.session_state.user_status == "logged_in" and not st.session_state.messages:
        try:
            docs = db.collection("chats").document(st.session_state.user_info["uid"]).collection("history").order_by("timestamp").stream()
            for doc in docs: st.session_state.messages.append(doc.to_dict())
        except: pass

    # Geçmişi Yazdır
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    # --- HIZLI KOMUTLAR ---
    st.write("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🍎 Beslenme Listesi", use_container_width=True):
            st.session_state.btn_prompt = "Bana bugüne özel bir beslenme programı hazırla."
            st.rerun()
    with c2:
        if st.button("💪 Antrenman Öner", use_container_width=True):
            st.session_state.btn_prompt = "Bugün hangi bölgeleri çalıştırmalıyım?"
            st.rerun()
    with c3:
        if st.button("🔥 Yağ Yakımı", use_container_width=True):
            st.session_state.btn_prompt = "Hızlı yağ yakmak için 3 ipucu verir misin?"
            st.rerun()

    # Giriş Yakalama (Buton veya Yazı)
    final_prompt = None
    if st.session_state.btn_prompt:
        final_prompt = st.session_state.btn_prompt
        st.session_state.btn_prompt = None # Tekrar çalışmasın diye temizle
    else:
        chat_input = st.chat_input("Mesajınızı buraya yazın...")
        if chat_input:
            final_prompt = chat_input

    # --- AI CEVAP DÖNGÜSÜ ---
    if final_prompt:
        st.session_state.messages.append({"role": "user", "content": final_prompt})
        with st.chat_message("user"): st.markdown(final_prompt)

        with st.chat_message("assistant"):
            try:
                safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
                talimat = f"Sen disiplinli fitness koçusun. Kullanıcı: {profil_bilgisi}. Tablo ve emoji kullan. İlaç önerme, doğal beslenme ve antrenman anlat."
                model = genai.GenerativeModel(model_name=secilen_model, system_instruction=talimat)
                
                response = model.generate_content(final_prompt, stream=True, safety_settings=safety)
                res_text = ""
                placeholder = st.empty()
                for chunk in response:
                    if chunk.text:
                        res_text += chunk.text
                        placeholder.markdown(res_text + "▌")
                placeholder.markdown(res_text)
                st.session_state.messages.append({"role": "assistant", "content": res_text})

                if st.session_state.user_status == "logged_in":
                    uid = st.session_state.user_info["uid"]
                    batch = db.batch()
                    u_ref = db.collection("chats").document(uid).collection("history").document()
                    a_ref = db.collection("chats").document(uid).collection("history").document()
                    batch.set(u_ref, {"role": "user", "content": final_prompt, "timestamp": firestore.SERVER_TIMESTAMP})
                    batch.set(a_ref, {"role": "assistant", "content": res_text, "timestamp": firestore.SERVER_TIMESTAMP})
                    batch.commit()
            except Exception as e:
                st.error("AI şu an yanıt veremiyor, lütfen tekrar deneyin.")

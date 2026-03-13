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
    /* Genel Modern Font ve Renkler */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }

    /* Mesaj Balonları */
    .stChatMessage { background-color: #f8f9fa; border-radius: 15px; margin-bottom: 10px; border: 1px solid #eee; }
    
    /* Mobil Buton Optimizasyonu */
    @media (max-width: 768px) {
        .stButton>button { width: 100% !important; height: 50px !important; font-size: 16px !important; margin-bottom: 5px; border-radius: 12px; }
        h1 { font-size: 1.8rem !important; }
    }

    /* VKİ Expander Stili */
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
secilen_model = "models/gemini-1.5-flash" # Daha hızlı yanıt için Flash önerilir

# --- 4. GİRİŞ EKRANI FONKSİYONU ---
def giris_ekrani():
    st.markdown("""
        <div style="text-align: center; padding: 10px;">
            <h1 style="color: #FF4B4B;">🏋️ FitUzman Pro AI</h1>
            <p>Kişisel Antrenörün ve Beslenme Uzmanınız</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1.5, 1])
    with col1:
        tab1, tab2 = st.tabs(["🔐 Giriş Yap", "📝 Kayıt Ol"])
        with tab1:
            email = st.text_input("E-posta", placeholder="ornek@mail.com")
            pw = st.text_input("Şifre", type="password")
            hatirla = st.checkbox("Beni Hatırla (30 Gün)")
            if st.button("Giriş Yap", use_container_width=True, type="primary"):
                try:
                    user = auth.get_user_by_email(email)
                    st.session_state.user_status = "logged_in"
                    st.session_state.user_info = {"uid": user.uid, "email": email}
                    if hatirla:
                        cookie_manager.set('fituzman_uid', user.uid, expires_at=datetime.now() + timedelta(days=30))
                    st.rerun()
                except: st.error("Hatalı bilgiler.")
        with tab2:
            n_email = st.text_input("Yeni E-posta")
            n_pw = st.text_input("Yeni Şifre", type="password")
            if st.button("Kayıt Ol", use_container_width=True):
                try:
                    auth.create_user(email=n_email, password=n_pw)
                    st.success("Hesap açıldı, giriş yapabilirsiniz.")
                except Exception as e: st.error(f"Hata: {e}")
    with col2:
        st.info("🤖 AI Destekli Analiz\n\n🍎 Kişiye Özel Beslenme\n\n💪 Antrenman Planları")
        if st.button("🚀 Misafir Olarak Dene", use_container_width=True):
            st.session_state.user_status = "guest"
            st.session_state.user_info = {"uid": "guest", "email": "Misafir"}
            st.rerun()

# --- 5. ANA UYGULAMA DÖNGÜSÜ ---
if st.session_state.user_status is None:
    giris_ekrani()
else:
    # --- SIDEBAR ---
    with st.sidebar:
        st.title("🛡️ Profil")
        st.write(f"Merhaba, **{st.session_state.user_info['email'].split('@')[0]}**")
        
        st.divider()
        vki_modu = st.checkbox("📊 VKİ Aracını Kullan", value=False)
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
                profil_bilgisi = f"Kilo:{kilo}, Boy:{boy}, VKİ:{vki:.1f}, Durum:{durum}"

        if st.button("🚪 Çıkış Yap", use_container_width=True):
            cookie_manager.delete('fituzman_uid')
            st.session_state.user_status = None
            st.session_state.messages = []
            st.rerun()

    # --- SOHBET ALANI ---
    st.title("🏋️ FitUzman AI")

    # Mesajları Yükle
    if st.session_state.user_status == "logged_in" and not st.session_state.messages:
        try:
            docs = db.collection("chats").document(st.session_state.user_info["uid"]).collection("history").order_by("timestamp").stream()
            for doc in docs: st.session_state.messages.append(doc.to_dict())
        except: pass

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    # --- HIZLI KOMUTLAR ---
    st.write("---")
    prompt = None
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🍎 Beslenme Listesi", use_container_width=True):
            prompt = "Bana bugüne özel bir beslenme programı hazırla."
    with c2:
        if st.button("💪 Antrenman Öner", use_container_width=True):
            prompt = "Bugün hangi bölgeleri çalıştırmalıyım?"
    with c3:
        if st.button("🔥 Yağ Yakımı", use_container_width=True):
            prompt = "Hızlı yağ yakmak için 3 ipucu verir misin?"

    # Chat Girişi (Eğer buton basılmadıysa inputtan al)
    chat_input = st.chat_input("Mesajınızı yazın...")
    if chat_input:
        prompt = chat_input

    # --- AI YANIT SİSTEMİ ---
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                safety = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
                talimat = f"Sen disiplinli fitness koçusun. Kullanıcı Verisi: {profil_bilgisi}. Tablo ve emoji kullan. Tıbbi ilaç önerme."
                model = genai.GenerativeModel(model_name=secilen_model, system_instruction=talimat)
                
                response = model.generate_content(prompt, stream=True, safety_settings=safety)
                res_text = ""
                placeholder = st.empty()
                
                for chunk in response:
                    if chunk.text:
                        res_text += chunk.text
                        placeholder.markdown(res_text + "▌")
                
                placeholder.markdown(res_text)
                st.session_state.messages.append({"role": "assistant", "content": res_text})

                # Kayıt
                if st.session_state.user_status == "logged_in":
                    uid = st.session_state.user_info["uid"]
                    u_ref = db.collection("chats").document(uid).collection("history").document()
                    a_ref = db.collection("chats").document(uid).collection("history").document()
                    batch = db.batch()
                    batch.set(u_ref, {"role": "user", "content": prompt, "timestamp": firestore.SERVER_TIMESTAMP})
                    batch.set(a_ref, {"role": "assistant", "content": res_text, "timestamp": firestore.SERVER_TIMESTAMP})
                    batch.commit()
            except Exception as e:
                st.error(f"Bir hata oluştu. Lütfen tekrar deneyin.")

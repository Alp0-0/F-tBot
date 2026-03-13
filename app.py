import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore, auth
import extra_streamlit_components as stx
from datetime import datetime, timedelta

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
genai.configure(api_key=st.secrets["API_KEY"])
secilen_model = None
try:
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            if "1.5" in m.name:
                secilen_model = m.name
                break
    if not secilen_model: secilen_model = "models/gemini-pro"
except: secilen_model = "models/gemini-pro"

st.set_page_config(page_title="FitUzman Pro v2", page_icon="🏋️", layout="wide")

# --- 4. GİRİŞ EKRANI ---
def giris_ekrani():
    # Sayfa başlığı ve Görsel bir Banner (Markdown ile)
    st.markdown("""
        <div style="text-align: center; padding: 20px;">
            <h1 style="color: #FF4B4B; font-size: 3rem;">🏋️ FitUzman Pro AI</h1>
            <p style="font-size: 1.2rem; color: #555;">Kişisel Antrenörün, Beslenme Uzmanın ve Motivasyon Kaynağın.</p>
            <hr style="border-top: 2px solid #bbb; border-radius: 5px;">
        </div>
    """, unsafe_allow_input=False, unsafe_allow_html=True)

    # İki sütunlu yapı: Sol tarafta giriş, sağ tarafta özellikler
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.markdown("### 🚀 Hemen Başla")
        tab1, tab2 = st.tabs(["🔐 Giriş Yap", "📝 Kayıt Ol"])
        
        with tab1:
            email = st.text_input("E-posta Adresi", placeholder="ornek@mail.com")
            password = st.text_input("Şifre", type="password", placeholder="******")
            beni_hatirla = st.checkbox("Oturumu 30 gün açık tut (Beni Hatırla)")
            
            if st.button("Sisteme Giriş Yap", use_container_width=True, type="primary"):
                try:
                    user = auth.get_user_by_email(email)
                    st.session_state.user_status = "logged_in"
                    st.session_state.user_info = {"uid": user.uid, "email": email}
                    
                    if beni_hatirla:
                        cookie_manager.set('fituzman_uid', user.uid, expires_at=datetime.now() + timedelta(days=30))
                    
                    st.success("Giriş Başarılı! Yönlendiriliyorsunuz...")
                    st.rerun()
                except: 
                    st.error("Giriş yapılamadı. Lütfen bilgilerinizi kontrol edin.")
        
        with tab2:
            new_email = st.text_input("E-posta Belirle", placeholder="yeni_hesap@mail.com")
            new_pw = st.text_input("Güçlü Bir Şifre", type="password", placeholder="En az 6 karakter")
            if st.button("Hesabımı Oluştur", use_container_width=True):
                try:
                    auth.create_user(email=new_email, password=new_pw)
                    st.balloons() # Tebrik efekti!
                    st.success("Hesabın başarıyla oluşturuldu! Şimdi Giriş Yap sekmesine geçebilirsin.")
                except Exception as e: 
                    st.error(f"Kayıt hatası: {e}")

    with col2:
        # Sağ sütun: Neden FitUzman?
        st.markdown("""
        <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #FF4B4B;">
            <h4 style="margin-top: 0;">Neler Sunuyoruz?</h4>
            <ul style="font-size: 0.9rem; color: #333;">
                <li><b>🤖 Akıllı Analiz:</b> Boy, kilo ve VKİ değerlerine göre özel tavsiyeler.</li>
                <li><b>📚 Kalıcı Hafıza:</b> Eski konuşmaların asla silinmez, kaldığın yerden devam edersin.</li>
                <li><b>🍎 Beslenme Planı:</b> Sana özel makro ve öğün takipleri.</li>
                <li><b>⚡ Hızlı Yanıt:</b> Gemini 1.5 Flash ile saniyeler içinde çözüm.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("") # Boşluk
        if st.button("🚀 Kayıt Olmadan Dene (Misafir Modu)", use_container_width=True):
            st.session_state.user_status = "guest"
            st.session_state.user_info = {"uid": "guest", "email": "Misafir Kullanıcı"}
            st.rerun()

    # Alt kısma küçük bir bilgi
    st.markdown("""
        <div style="text-align: center; margin-top: 50px; font-size: 0.8rem; color: #888;">
            © 2026 FitUzman AI System Design Project | Tüm Veriler Firebase ile Korunmaktadır.
        </div>
    """, unsafe_allow_html=True)
# --- 5. ANA UYGULAMA ---
if st.session_state.user_status is None:
    giris_ekrani()
else:
    # Sidebar
    with st.sidebar:
        st.title("🛡️ Profil")
        st.write(f"Hoş geldin, **{st.session_state.user_info['email']}**")
        
        vki_aktif = st.toggle("VKİ Analizi", value=True)
        profil_bilgisi = "Genel Profil"
        if vki_aktif:
            kilo = st.number_input("Kilo (kg)", 30, 200, 75)
            boy = st.number_input("Boy (cm)", 100, 250, 180)
            vki = kilo / ((boy/100) ** 2)
            st.metric("VKİ", f"{vki:.1f}")
            profil_bilgisi = f"Kilo: {kilo}kg, Boy: {boy}cm, VKİ: {vki:.1f}"
        
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
                st.session_state.messages.append(doc.to_dict())
        except: pass

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
                talimat = f"Sen disiplinli ve motive edici bir fitness koçusun. Kullanıcı: {profil_bilgisi}. Tablo ve emoji kullan."
                model = genai.GenerativeModel(model_name=secilen_model, system_instruction=talimat)
                
                response = model.generate_content(prompt, stream=True)
                res_text = ""
                placeholder = st.empty()
                for chunk in response:
                    res_text += chunk.text
                    placeholder.markdown(res_text + "▌")
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

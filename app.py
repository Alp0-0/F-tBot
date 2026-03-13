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

# Otomatik Giriş Kontrolü
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
except: 
    secilen_model = "models/gemini-pro"

st.set_page_config(page_title="FitUzman Pro v2", page_icon="🏋️", layout="wide")

# --- 4. GİRİŞ EKRANI ---
def giris_ekrani():
    st.markdown("""
        <div style="text-align: center; padding: 20px;">
            <h1 style="color: #FF4B4B; font-size: 3rem;">🏋️ FitUzman Pro AI</h1>
            <p style="font-size: 1.2rem; color: #555;">Kişisel Antrenörün, Beslenme Uzmanın ve Motivasyon Kaynağın.</p>
            <hr style="border-top: 2px solid #bbb; border-radius: 5px;">
        </div>
    """, unsafe_allow_html=True)

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
                    st.success("Giriş Başarılı!")
                    st.rerun()
                except: st.error("Giriş başarısız.")
        
        with tab2:
            new_email = st.text_input("E-posta Belirle", placeholder="yeni_hesap@mail.com")
            new_pw = st.text_input("Güçlü Bir Şifre", type="password")
            if st.button("Hesabımı Oluştur", use_container_width=True):
                try:
                    auth.create_user(email=new_email, password=new_pw)
                    st.balloons()
                    st.success("Hesap oluşturuldu!")
                except Exception as e: st.error(f"Hata: {e}")

    with col2:
        st.markdown("""
        <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #FF4B4B;">
            <h4 style="margin-top: 0; color: #333;">Neler Sunuyoruz?</h4>
            <ul style="font-size: 0.9rem; color: #333;">
                <li><b>🤖 Akıllı Analiz:</b> Verilerine göre özel tavsiyeler.</li>
                <li><b>📚 Kalıcı Hafıza:</b> Geçmişin hep seninle.</li>
                <li><b>🍎 Beslenme Planı:</b> Makro ve öğün takipleri.</li>
                <li><b>⚡ Hızlı Yanıt:</b> Saniyeler içinde çözüm.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚀 Misafir Modu", use_container_width=True):
            st.session_state.user_status = "guest"
            st.session_state.user_info = {"uid": "guest", "email": "Misafir"}
            st.rerun()

# --- 5. ANA UYGULAMA ---
if st.session_state.user_status is None:
    giris_ekrani()
else:
    # Sidebar: Tüm araçları buraya topluyoruz
    with st.sidebar:
        st.title("🛡️ Kontrol Paneli")
        st.write(f"Sporcu: **{st.session_state.user_info['email'].split('@')[0]}**")
        
        st.divider()
        
        # İstediğimiz zaman bu özelliği katabilmek için bir kontrol:
        vki_modu = st.checkbox("VKİ Analiz Aracını Aç", value=False)
        profil_bilgisi = "Genel Fitness Profili"

        if vki_modu:
            # Sadece tıklandığında görünen, küçük bir kutu
            with st.expander("📊 VKİ Hesapla", expanded=True):
                kilo = st.number_input("Kilo (kg)", 30, 200, 75, key="kilo_input")
                boy = st.number_input("Boy (cm)", 100, 250, 180, key="boy_input")
                vki = kilo / ((boy/100) ** 2)
                
                # Durum belirleme
                if vki < 18.5: durum = "Zayıf"
                elif 18.5 <= vki < 25: durum = "Normal"
                elif 25 <= vki < 30: durum = "Kilolu"
                else: durum = "Obez"
                
                st.metric("VKİ", f"{vki:.1f}", durum)
                profil_bilgisi = f"Kilo: {kilo}kg, Boy: {boy}cm, VKİ: {vki:.1f} ({durum})"

        st.divider()
        
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            cookie_manager.delete('fituzman_uid')
            st.session_state.user_status = None
            st.session_state.messages = []
            st.rerun()

    # --- ANA EKRAN ---
    st.title("🏋️ FitUzman AI")
    
    # Firestore'dan geçmiş mesajları yükleme (Sadece ilk girişte)
    if st.session_state.user_status == "logged_in" and not st.session_state.messages:
        try:
            docs = db.collection("chats").document(st.session_state.user_info["uid"]).collection("history").order_by("timestamp").stream()
            for doc in docs:
                st.session_state.messages.append(doc.to_dict())
        except: pass

    # Sohbet Geçmişini Görüntüle
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Girişi
    if prompt := st.chat_input("Hangi bölgeyi çalıştıralım?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
                
                talimat = f"Sen disiplinli fitness koçusun. Kullanıcı: {profil_bilgisi}. Tablo ve emoji kullan. İlaç tavsiyesi verme, antrenman ve doğal beslenme anlat."
                model = genai.GenerativeModel(model_name=secilen_model, system_instruction=talimat)
                
                response = model.generate_content(prompt, stream=True, safety_settings=safety_settings)
                res_text = ""
                placeholder = st.empty()
                
                for chunk in response:
                    try:
                        if chunk.text:
                            res_text += chunk.text
                            placeholder.markdown(res_text + "▌")
                    except: continue
                
                if not res_text:
                    res_text = "Güvenlik nedeniyle bu soruyu yanıtlayamıyorum. Lütfen antrenman odaklı bir soru sor!"
                
                placeholder.markdown(res_text)
                st.session_state.messages.append({"role": "assistant", "content": res_text})

                # Firebase Kayıt
                if st.session_state.user_status == "logged_in":
                    uid = st.session_state.user_info["uid"]
                    batch = db.batch()
                    u_ref = db.collection("chats").document(uid).collection("history").document()
                    a_ref = db.collection("chats").document(uid).collection("history").document()
                    batch.set(u_ref, {"role": "user", "content": prompt, "timestamp": firestore.SERVER_TIMESTAMP})
                    batch.set(a_ref, {"role": "assistant", "content": res_text, "timestamp": firestore.SERVER_TIMESTAMP})
                    batch.commit()
            except Exception as e:
                st.error(f"Sistem Hatası: {e}")

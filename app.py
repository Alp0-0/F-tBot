import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore, auth
import extra_streamlit_components as stx
from datetime import datetime, timedelta

# --- SAYFA AYARLARI (En üstte olmalıdır) ---
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
@st.cache_resource
def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

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
# System Instruction destekleyen güncel ve hızlı model doğrudan seçildi
secilen_model = "gemini-1.5-flash" 

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
                except Exception as e: 
                    st.error("Giriş başarısız. Lütfen bilgilerinizi kontrol edin.")
        
        with tab2:
            new_email = st.text_input("E-posta Belirle", placeholder="yeni_hesap@mail.com")
            new_pw = st.text_input("Güçlü Bir Şifre", type="password")
            if st.button("Hesabımı Oluştur", use_container_width=True):
                try:
                    auth.create_user(email=new_email, password=new_pw)
                    st.balloons()
                    st.success("Hesap oluşturuldu! Şimdi giriş yapabilirsiniz.")
                except Exception as e: 
                    st.error(f"Hata: {e}")

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
    # Sidebar: Profil ve Çıkış
    with st.sidebar:
        st.title("🛡️ Profil")
        st.write(f"Hoş geldin,\n**{st.session_state.user_info['email']}**")
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            cookie_manager.delete('fituzman_uid')
            st.session_state.user_status = None
            st.session_state.messages = []
            st.rerun()

    # --- ANA EKRAN VKİ PANELİ ---
    st.markdown("### 👋 Merhaba Şampiyon!")
    
    with st.expander("📊 Fiziksel Analiz ve VKİ Takibi", expanded=True):
        col_vki1, col_vki2, col_vki3 = st.columns(3)
        with col_vki1:
            kilo = st.number_input("Kilo (kg)", 30, 200, 75)
        with col_vki2:
            boy = st.number_input("Boy (cm)", 100, 250, 180)
        with col_vki3:
            vki = kilo / ((boy/100) ** 2)
            if vki < 18.5: durum = "Zayıf"
            elif 18.5 <= vki < 25: durum = "Normal"
            elif 25 <= vki < 30: durum = "Fazla Kilolu"
            else: durum = "Obezite"
            st.metric("VKİ Değerin", f"{vki:.1f}", delta=durum)
        
        st.info(f"💡 **Analiz:** Şu an **{durum}** kategorisindesin. Gemini buna göre sana özel tavsiyeler verecek.")
        profil_bilgisi = f"Kilo: {kilo}kg, Boy: {boy}cm, VKİ: {vki:.1f} ({durum})"

    st.divider()

    # Firestore'dan Geçmişi Yükleme
    if st.session_state.user_status == "logged_in" and not st.session_state.messages:
        try:
            docs = db.collection("chats").document(st.session_state.user_info["uid"]).collection("history").order_by("timestamp").stream()
            for doc in docs: 
                st.session_state.messages.append(doc.to_dict())
        except Exception as e: 
            pass

    # Sohbet Akışını Ekrana Basma
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): 
            st.markdown(msg["content"])

    # Yeni Mesaj Girişi
    if prompt := st.chat_input("Hangi bölgeyi çalıştıralım?"):
        
        # Kullanıcı mesajını ekrana ve state'e ekle
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
                
                # Gemini'nin hatırlaması için geçmiş mesajları modele uygun formata çeviriyoruz
                gemini_history = []
                for msg in st.session_state.messages[:-1]: # Son mesajı (prompt) hariç tut
                    role = "model" if msg["role"] == "assistant" else "user"
                    gemini_history.append({"role": role, "parts": [msg["content"]]})
                
                # Hafızalı sohbeti başlat
                chat = model.start_chat(history=gemini_history)
                
                # Soru gönder ve yanıtı akıcı (stream) olarak al
                response = chat.send_message(prompt, stream=True, safety_settings=safety_settings)
                
                res_text = ""
                placeholder = st.empty()
                
                for chunk in response:
                    try:
                        if chunk.text:
                            res_text += chunk.text
                            placeholder.markdown(res_text + "▌")
                    except Exception: 
                        continue
                
                if not res_text:
                    res_text = "Güvenlik nedeniyle bu soruyu yanıtlayamıyorum. Lütfen antrenman odaklı bir soru sor!"
                
                placeholder.markdown(res_text)
                st.session_state.messages.append({"role": "assistant", "content": res_text})

                # Veritabanına Kaydetme (Yalnızca giriş yapmış kullanıcılar için)
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

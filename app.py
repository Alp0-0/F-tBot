import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore, auth

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

# --- 2. GEMINI YAPILANDIRMASI ---
genai.configure(api_key=st.secrets["API_KEY"])

# En iyi modeli seçme
secilen_model = "gemini-1.5-flash" # Varsayılan en hızlı model

st.set_page_config(page_title="FitUzman Pro v2", page_icon="🔐", layout="wide")

# --- 3. KULLANICI GİRİŞ/KAYIT SİSTEMİ ---
if "user_info" not in st.session_state:
    st.session_state.user_info = None

def giris_ekrani():
    st.title("🔐 FitUzman Pro'ya Hoş Geldin")
    st.info("Devam etmek için giriş yapın veya yeni bir hesap oluşturun.")
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        email = st.text_input("E-posta", key="login_email")
        password = st.text_input("Şifre", type="password", key="login_pw")
        if st.button("Sisteme Gir"):
            try:
                # ÖNEMLİ: Streamlit üzerinde doğrudan şifre doğrulaması yapılamaz (Firebase Admin SDK kısıtı)
                # Bu yüzden kullanıcıyı email ile buluyoruz. Gerçek projede Firebase Client SDK kullanılır.
                user = auth.get_user_by_email(email)
                st.session_state.user_info = {"uid": user.uid, "email": email}
                st.success("Giriş Başarılı!")
                st.rerun()
            except:
                st.error("Kullanıcı bulunamadı veya bilgiler hatalı.")

    with tab2:
        new_email = st.text_input("E-posta", key="reg_email")
        new_password = st.text_input("Şifre (min. 6 karakter)", type="password", key="reg_pw")
        if st.button("Hesap Oluştur"):
            try:
                user = auth.create_user(email=new_email, password=new_password)
                st.success("Hesap başarıyla oluşturuldu! Şimdi Giriş Yap sekmesine geçebilirsiniz.")
            except Exception as e:
                st.error(f"Hata: {e}")

# --- 4. ANA UYGULAMA DÖNGÜSÜ ---
if st.session_state.user_info is None:
    giris_ekrani()
else:
    user_uid = st.session_state.user_info["uid"]
    
    # --- YAN PANEL ---
    with st.sidebar:
        st.write(f"👤 **{st.session_state.user_info['email']}**")
        vki_aktif = st.toggle("VKİ Analizini Kullan", value=True)
        
        if vki_aktif:
            kilo = st.number_input("Kilo (kg)", 30, 200, 75)
            boy = st.number_input("Boy (cm)", 100, 250, 180)
            vki = kilo / ((boy/100) ** 2)
            st.metric("VKİ Endeksiniz", f"{vki:.1f}")
        
        if st.button("🗑️ Sohbeti Temizle", use_container_width=True):
            # Firestore'daki geçmişi silme (Opsiyonel: Sadece session temizliyoruz)
            st.session_state.messages = []
            st.rerun()
            
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            st.session_state.user_info = None
            st.session_state.messages = []
            st.rerun()

    # --- MESAJLARI FİREBASE'DEN ÇEKME ---
    if "messages" not in st.session_state:
        st.session_state.messages = []
        try:
            chat_ref = db.collection("chats").document(user_uid).collection("history").order_by("timestamp")
            docs = chat_ref.stream()
            for doc in docs:
                st.session_state.messages.append(doc.to_dict())
        except:
            pass

    st.title("🏋️ FitUzman AI: Akıllı Koç")
    
    # Mesajları ekrana bas
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # --- SOHBET GİRİŞİ ---
    if prompt := st.chat_input("Hedefini veya sorunu yaz..."):
        # 1. Kullanıcı mesajını göster ve kaydet
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Gemini Talimatlarını Hazırla
        profil = f"Kilo: {kilo}kg, Boy: {boy}cm, VKİ: {vki:.1f}" if vki_aktif else "Genel profil"
        talimat = f"Sen profesyonel bir fitness koçusun. Kullanıcı verisi: {profil}. Bilimsel ve motive edici yanıtlar ver."
        
        # 3. Gemini'dan Yanıt Al
        with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel(model_name=secilen_model, system_instruction=talimat)
                response = model.generate_content(prompt)
                response_text = response.text
                st.markdown(response_text)
                
                # 4. Yanıtı Firebase'e ve Session'a Kaydet
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
                # Firebase Kayıt
                batch = db.batch()
                user_msg_ref = db.collection("chats").document(user_uid).collection("history").document()
                asst_msg_ref = db.collection("chats").document(user_uid).collection("history").document()
                
                batch.set(user_msg_ref, {"role": "user", "content": prompt, "timestamp": firestore.SERVER_TIMESTAMP})
                batch.set(asst_msg_ref, {"role": "assistant", "content": response_text, "timestamp": firestore.SERVER_TIMESTAMP})
                batch.commit()
                
            except Exception as e:
                st.error(f"Bir hata oluştu: {e}")

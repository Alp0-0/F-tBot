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

# --- 3. DURUM YÖNETİMİ ---
if "user_status" not in st.session_state:
    st.session_state.user_status = None # "logged_in", "guest" veya None

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. GİRİŞ VE MİSAFİR EKRANI ---
def giris_ekrani():
    st.title("🏋️ FitUzman AI")
    st.subheader("Geleceğin Fitness Asistanına Hoş Geldin")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        tab1, tab2 = st.tabs(["🔐 Giriş Yap", "📝 Kayıt Ol"])
        with tab1:
            email = st.text_input("E-posta")
            password = st.text_input("Şifre", type="password")
            if st.button("Giriş Yap"):
                try:
                    user = auth.get_user_by_email(email)
                    st.session_state.user_status = "logged_in"
                    st.session_state.user_info = {"uid": user.uid, "email": email}
                    st.rerun()
                except: st.error("Bilgiler hatalı veya kullanıcı bulunamadı.")
        
        with tab2:
            new_email = st.text_input("Yeni E-posta")
            new_pw = st.text_input("Yeni Şifre", type="password")
            if st.button("Hesap Oluştur"):
                try:
                    auth.create_user(email=new_email, password=new_pw)
                    st.success("Hesap açıldı! Giriş yapabilirsiniz.")
                except Exception as e: st.error(f"Hata: {e}")

    with col2:
        st.info("Kayıt olmadan denemek ister misin?")
        if st.button("🚀 Misafir Olarak Devam Et", use_container_width=True):
            st.session_state.user_status = "guest"
            st.session_state.user_info = {"uid": "guest", "email": "Misafir Kullanıcı"}
            st.rerun()

# --- 5. ANA UYGULAMA DÖNGÜSÜ ---
if st.session_state.user_status is None:
    giris_ekrani()
else:
    # Sidebar
    with st.sidebar:
        st.title("🛡️ Profil")
        st.write(f"Durum: **{st.session_state.user_info['email']}**")
        
        if st.session_state.user_status == "guest":
            st.warning("⚠️ Misafir modundasınız. Konuşmalarınız kaydedilmez.")
        
        vki_aktif = st.toggle("VKİ Analizi", value=True)
        if vki_aktif:
            kilo = st.number_input("Kilo (kg)", 30, 200, 75)
            boy = st.number_input("Boy (cm)", 100, 250, 180)
            vki = kilo / ((boy/100) ** 2)
            st.metric("VKİ", f"{vki:.1f}")
        
        if st.button("🚪 Çıkış Yap / Ana Menü", use_container_width=True):
            st.session_state.user_status = None
            st.session_state.messages = []
            st.rerun()

    # Geçmişi Yükle (Sadece Giriş Yapılmışsa)
    if st.session_state.user_status == "logged_in" and not st.session_state.messages:
        try:
            chat_ref = db.collection("chats").document(st.session_state.user_info["uid"]).collection("history").order_by("timestamp")
            docs = chat_ref.stream()
            for doc in docs:
                st.session_state.messages.append(doc.to_dict())
        except: pass

    # Sohbet Arayüzü
    st.title("🏋️ FitUzman AI")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Sorunu buraya yaz..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Gemini Yanıtı
      with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel(model_name=secilen_model, system_instruction=talimat)
                # Stream=True ile cevabı parça parça alıyoruz
                response = model.generate_content(prompt, stream=True)
                
                res_text = ""
                placeholder = st.empty() # Cevabın yazılacağı boş alan
                
                for chunk in response:
                    res_text += chunk.text
                    placeholder.markdown(res_text + "▌") # Yazma efekti
                
                placeholder.markdown(res_text) # Yazma bitince imleci kaldır
                
                st.session_state.messages.append({"role": "assistant", "content": res_text})
                # ... (Firebase kayıt kodların burada devam edecek)
            try:
                talimat = f"""
Sen, dünyanın en iyi spor salonlarında çalışmış, sempatik ama disiplinli bir 'Baş Antrenör' ve 'Beslenme Uzmanı' karakterisin. 
Adın: FitUzman AI. 

DAVRANIŞ KURALLARIN:
1. **Persona:** Enerjik, motive edici ve profesyonel bir dil kullan. Cümle aralarına sporcu jargonları (Set, reps, bulk, definasyon, makrolar) serpiştir.
2. **Kişiselleştirme:** {profil} verilerini asla unutma. Eğer kullanıcı obezite sınırındaysa ona 'şampiyon, eklemlerini korumak için bugün koşu bandı yerine eliptik yapalım' gibi spesifik tavsiyeler ver.
3. **Görsellik:** Liste verirken mutlaka emoji kullan. Program yazarken mutlaka Markdown TABLO formatını kullan. Önemli uyarıları **kalın** yaz.
4. **Bilimsellik:** Bir öneri verdiğinde (örn: neden yüksek protein?) bunun arkasındaki fizyolojik nedeni kısaca açıkla.
5. **Diyaloğu Canlı Tut:** Her cevabın sonunda mutlaka kullanıcıya süreci devam ettirecek, onu düşündürecek bir soru sor. (Örn: 'Peki, bugün antrenman için 45 dakikan var mı?', 'Bu diyet listesindeki öğünlerden hangisi seni en çok zorlar?')
6. **Yasaklar:** Fitness, spor, sağlık ve beslenme dışındaki soruları 'Benim uzmanlık alanım demir ve ter şampiyon, gel biz hedeflerine odaklanalım' diyerek nazikçe reddet.
"""
                model = genai.GenerativeModel(model_name=secilen_model, system_instruction=talimat)
                response = model.generate_content(prompt)
                res_text = response.text
                st.markdown(res_text)
                st.session_state.messages.append({"role": "assistant", "content": res_text})

                # --- KAYIT MANTIĞI ---
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

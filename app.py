import streamlit as st
import google.generativeai as genai

# --- YAPILANDIRMA ---
genai.configure(api_key=st.secrets["API_KEY"])
st.set_page_config(page_title="FitUzman AI", page_icon="💪")
st.title("🏋️ FitUzman: 7/24 Spor Koçun")

# --- AKILLI MODEL BULUCU ---
# Google'a Kadir'in kullanabileceği modelleri soruyoruz
secilen_model = None
try:
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            # İsmin başındaki 'models/' kısmını temizliyoruz
            model_adi = m.name.replace("models/", "")
            # İçinde 'flash' veya 'pro' geçen güncel bir model bulursak seçiyoruz
            if "flash" in model_adi or "pro" in model_adi:
                secilen_model = model_adi
                break
    
    # Eğer özel bir isim bulamazsa, listedeki ilk çalışan modeli alır
    if not secilen_model:
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                secilen_model = m.name.replace("models/", "")
                break
                
    if secilen_model:
        st.caption(f"✅ Sistem hazır. Bağlanılan motor: {secilen_model}")
    else:
        st.error("API anahtarınıza tanımlı geçerli bir model bulunamadı.")
        
except Exception as e:
    st.error(f"Model listesi alınırken bağlantı hatası: {e}")


# --- SOHBET ARAYÜZÜ ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Hangi bölgeyi çalıştırmak istersin?"):
    if not secilen_model:
        st.warning("Motor bulunamadığı için şu an cevap veremiyorum.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                # Bulunan otomatik model ismiyle botu çalıştır
                model = genai.GenerativeModel(
                    model_name=secilen_model,
                    system_instruction="Sen uzman bir fitness koçusun. Sadece spor ve beslenme konuş."
                )
                response = model.generate_content(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Cevap üretilirken teknik bir pürüz çıktı: {e}")

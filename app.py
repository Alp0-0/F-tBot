import streamlit as st
import google.generativeai as genai

# --- YAPILANDIRMA ---
# Buraya tırnak içinde kendi anahtarını yapıştır
genai.configure(api_key=st.secrets["API_KEY"])
genai.configure(api_key=st.secrets["API_KEY"])
# --- WEB ARAYÜZÜ ---
st.set_page_config(page_title="FitUzman AI", page_icon="💪")
st.title("🏋️ FitUzman: 7/24 Spor Koçun")
st.markdown("Hedeflerini yaz, sana özel bilimsel yanıtlar al!")

# Sohbet geçmişini sakla
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mesajları ekrana bas
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Kullanıcı girişi
if prompt := st.chat_input("Hangi bölgeyi çalıştırmak istersin?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Yapay zekadan yanıt al
    with st.chat_message("assistant"):
        try:
            # Modeli tam burada, istek anında tanımlıyoruz (Daha güvenli)
            model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", # Sonuna -latest ekledik
            system_instruction="Sen uzman bir fitness koçusun. Sadece spor ve beslenme konuş."
            )
            
            response = model.generate_content(prompt)
            
            if response.text:
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            else:
                st.error("Model boş cevap döndürdü.")
                
        except Exception as e:
            # Hatanın ne olduğunu ekranda tam görelim ki teşhis koyalım
            st.error(f"Teknik bir hata oluştu: {e}")

import streamlit as st
import google.generativeai as genai

# --- YAPILANDIRMA ---
# Gemini API Anahtarını buraya ekle (Daha sonra güvenli yöntemle saklayacağız)
genai.configure(api_key="SENIN_GEMINI_API_ANAHTARIN")

# Botun Uzmanlık Tanımı (System Instruction)
fitness_coach_instruction = (
    "Sen uzman bir Fitness, Spor ve Sağlıklı Beslenme koçusun. "
    "Sadece şu konularda cevap ver: Antrenman programları, egzersiz formları, "
    "makro/mikro besinler, supplementler ve sporcu sağlığı. "
    "BUNUN DIŞINDAKİ (siyaset, teknoloji, yemek tarifleri -sporla ilgisiz ise-, vb.) "
    "tüm sorulara 'Üzgünüm, ben sadece fitness ve beslenme konularında uzmanım.' cevabını ver."
)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=fitness_coach_instruction
)

# --- WEB ARAYÜZÜ ---
st.set_page_config(page_title="FitUzman AI", page_icon="💪")
st.title("🏋️ FitUzman: 7/24 Spor Koçun")
st.markdown("Hedeflerini yaz, sana özel bilimsel yanıtlar al!")

# Sohbet geçmişini sakla (Her kullanıcı için ayrı çalışır)
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
            response = model.generate_content(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error("Bir hata oluştu, lütfen API anahtarınızı kontrol edin.")
import streamlit as st
import google.generativeai as genai

# --- YAPILANDIRMA ---
genai.configure(api_key=st.secrets["API_KEY"])

st.set_page_config(page_title="FitUzman Pro", page_icon="🌐", layout="wide")

# --- AKILLI MODEL BULUCU ---
secilen_model = None
try:
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            model_adi = m.name.replace("models/", "")
            if "flash" in model_adi or "pro" in model_adi:
                secilen_model = model_adi
                break
    if not secilen_model:
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                secilen_model = m.name.replace("models/", "")
                break
except Exception as e:
    st.error(f"Model hatası: {e}")

# --- YAN PANEL (SIDEBAR) ---
with st.sidebar:
    st.header("📊 Vücut Analizi")
    
    kilo = st.number_input("Kilo (kg)", 30, 200, 75)
    boy = st.number_input("Boy (cm)", 100, 250, 180)
    vki = kilo / ((boy/100) ** 2)
    
    st.metric("VKİ Endeksiniz", f"{vki:.1f}")
    
    if vki < 18.5: st.warning("Durum: Zayıf")
    elif 18.5 <= vki < 25: st.success("Durum: Normal")
    elif 25 <= vki < 30: st.warning("Durum: Fazla Kilolu")
    else: st.error("Durum: Obezite Sınırı")

    st.divider()
    st.success("🌐 Bu yapay zeka, internetteki en güncel ve bilimsel fitness veritabanlarına bağlıdır.")

# --- ANA EKRAN ---
st.title("🌐 FitUzman AI: Global Fitness Veritabanı")
st.caption(f"✅ Sistem hazır. Bağlanılan motor: {secilen_model}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Hedefini yaz, en güncel bilimsel kaynaklardan planını al..."):
    if not secilen_model:
        st.warning("Motor bulunamadığı için cevap veremiyorum.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Botun Zekası: Boy, Kilo ve Gemini'ın Devasa İnternet Bilgisi!
        dinamik_talimat = f"""
        Sen, internetteki en güvenilir spor ve beslenme bilimleri (NSCA, ACSM, güncel makaleler) verilerini analiz edebilen dünya çapında bir Baş Antrenörsün.
        KULLANICI PROFİLİ: Kilo: {kilo}kg, Boy: {boy}cm, VKİ: {vki:.1f}.
        
        KURALLAR:
        1. Sadece fitness, spor, sağlık ve beslenme konularında cevap ver.
        2. Her zaman kullanıcının VKİ değerini dikkate alarak konuş. Zayıfsa hacim, obezite sınırındaysa kardiyo/kalori açığı odaklı konuş.
        3. Bir antrenman veya diyet listesi verirken, bunun arkasındaki "bilimsel mantığı" (neden bu hareket, neden bu kalori) internetteki modern spor bilimlerine dayanarak kısaca açıkla.
        4. Kesin kurallar koy. Örneğin "istiyorsan yapabilirsin" demek yerine "şu kas grubu için bu yapılmalıdır" şeklinde profesyonel bir dil kullan.
        """

        with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel(
                    model_name=secilen_model,
                    system_instruction=dinamik_talimat
                )
                response = model.generate_content(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Cevap üretilirken teknik bir pürüz çıktı: {e}")

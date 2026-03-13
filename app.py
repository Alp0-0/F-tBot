import streamlit as st
import google.generativeai as genai

# --- YAPILANDIRMA ---
genai.configure(api_key=st.secrets["API_KEY"])

# ==========================================
# 👑 ADMİN BÖLGESİ: BURAYA KENDİ SİSTEMİNİ YAZ
# ==========================================
ADMIN_PROGRAMI = """
GENEL BİLGİLER VE KURALLAR:
- Yeni başlayanlar (VKİ 25 üstü) için ilk 2 hafta sadece kardiyo (yürüyüş/yüzme) önerilecek.
- Ağırlık antrenmanları: Pazartesi (Göğüs/Sırt), Çarşamba (Bacak/Omuz), Cuma (Tüm Vücut).
- Beslenme kuralı: İşlenmiş şeker kesinlikle yasak. Günlük en az 2.5 litre su içilecek.
- Egzersiz formları sorulduğunda, hareketin doğru yapılışını adım adım anlat.
(Not: Bu kısmı Kadir Hoca hazırlamıştır, sadece bu kuralların dışına çıkma.)
"""
# ==========================================

st.set_page_config(page_title="FitUzman Pro", page_icon="💪", layout="wide")

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
    st.info("💡 Sistem, Kadir Hoca'nın özel antrenman prensipleriyle çalışmaktadır.")

# --- ANA EKRAN ---
st.title("🏋️ FitUzman Pro")
st.caption(f"✅ Sistem hazır. Bağlanılan motor: {secilen_model}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Hedefini yaz, Kadir Hoca'nın sistemine göre planını al..."):
    if not secilen_model:
        st.warning("Motor bulunamadığı için cevap veremiyorum.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Botun Zekası: Boy, kilo ve senin Admin Kuralların birleşiyor!
        dinamik_talimat = f"""
        Sen uzman bir fitness ve beslenme koçusun.
        KULLANICI PROFİLİ: Kilo: {kilo}kg, Boy: {boy}cm, VKİ: {vki:.1f}.
        
        UYGULAMAN GEREKEN ANA SİSTEM VE PROGRAM (Kadir Hoca'nın Kuralları):
        {ADMIN_PROGRAMI}
        
        KURALLAR:
        1. Sadece fitness, spor, sağlık ve beslenme konularında cevap ver.
        2. Her zaman kullanıcının VKİ değerini dikkate alarak konuş.
        3. Antrenman veya beslenme tavsiyesi verirken SADECE yukarıdaki "ANA SİSTEM VE PROGRAM" kurallarını uygula.
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

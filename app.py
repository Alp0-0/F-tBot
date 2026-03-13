import streamlit as st
import google.generativeai as genai
import PyPDF2
import os

# --- YAPILANDIRMA ---
genai.configure(api_key=st.secrets["API_KEY"])

# --- GİZLİ ADMİN PDF'İNİ OKUMA FONKSİYONU ---
@st.cache_data # Performans için PDF'i her soruda değil, site açıldığında 1 kez okur
def admin_pdf_oku():
    dosya_adi = "admin_program.pdf" # GitHub'a yükleyeceğimiz dosyanın tam adı
    metin = ""
    if os.path.exists(dosya_adi):
        try:
            okuyucu = PyPDF2.PdfReader(dosya_adi)
            for sayfa in okuyucu.pages:
                metin += sayfa.extract_text() or ""
            return metin
        except Exception as e:
            return f"Sistem hatası: PDF okunamadı ({e})"
    else:
        return "Admin (Kadir Hoca) henüz sisteme bir PDF programı yüklemedi."

# Arka planda PDF'i oku ve hafızaya al
GIZLI_ADMIN_BİLGİSİ = admin_pdf_oku()

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

    

# --- ANA EKRAN ---
st.title("🏋️ FitUzman Pro")
st.caption(f"✅ Sistem hazır. Bağlanılan motor: {secilen_model}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Hedefini yaz, sana özel planını al..."):
    if not secilen_model:
        st.warning("Motor bulunamadığı için cevap veremiyorum.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Botun Zekası: Boy, kilo ve arka plandaki Admin PDF'i birleşiyor!
        dinamik_talimat = f"""
        Sen uzman bir fitness ve beslenme koçusun.
        KULLANICI PROFİLİ: Kilo: {kilo}kg, Boy: {boy}cm, VKİ: {vki:.1f}.
        
        UYGULAMAN GEREKEN ANA SİSTEM VE PROGRAM BİLGİLERİ (Aşağıdaki metin admin PDF'inden gelmektedir):
        {GIZLI_ADMIN_BİLGİSİ}
        
        KURALLAR:
        1. Sadece fitness, spor, sağlık ve beslenme konularında cevap ver.
        2. Her zaman kullanıcının VKİ değerini dikkate alarak konuş.
        3. Antrenman veya beslenme tavsiyesi verirken SADECE yukarıdaki "ANA SİSTEM" bilgilerini referans al. Eğer PDF'te o konuyla ilgili bilgi yoksa, genel fitness bilginle ama PDF'in kurallarıyla çelişmeyecek şekilde cevap ver.
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

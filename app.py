import streamlit as st
import google.generativeai as genai
import PyPDF2

# --- YAPILANDIRMA ---
genai.configure(api_key=st.secrets["API_KEY"])

def pdf_metnini_oku(pdf_dosyasi):
    pdf_reader = PyPDF2.PdfReader(pdf_dosyasi)
    metin = ""
    for sayfa in pdf_reader.pages:
        metin += sayfa.extract_text() or ""
    return metin

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
    st.header("📊 Profil ve Dosyalar")
    
    kilo = st.number_input("Kilo (kg)", 30, 200, 75)
    boy = st.number_input("Boy (cm)", 100, 250, 180)
    vki = kilo / ((boy/100) ** 2)
    
    st.metric("VKİ Endeksiniz", f"{vki:.1f}")
    
    # VKİ'ye göre renkli uyarılar
    if vki < 18.5: st.warning("Durum: Zayıf")
    elif 18.5 <= vki < 25: st.success("Durum: Normal")
    elif 25 <= vki < 30: st.warning("Durum: Fazla Kilolu")
    else: st.error("Durum: Obezite Sınırı")

    st.divider()

    yuklenen_pdf = st.file_uploader("Antrenman Programını Yükle (PDF)", type="pdf")
    pdf_metni = ""
    if yuklenen_pdf:
        pdf_metni = pdf_metnini_oku(yuklenen_pdf)
        st.success("Program başarıyla yüklendi ve yapay zekanın hafızasına aktarıldı!")

# --- ANA EKRAN ---
st.title("🏋️ FitUzman Pro")
st.caption(f"✅ Sistem hazır. Bağlanılan motor: {secilen_model}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Bana hedeflerinden bahset veya PDF'indeki programı sor..."):
    if not secilen_model:
        st.warning("Motor bulunamadığı için cevap veremiyorum.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Botun Zekası: Boy, kilo, VKİ ve PDF'i birleştiriyoruz!
        dinamik_talimat = f"""
        Sen uzman bir fitness ve beslenme koçusun. 
        KULLANICI PROFİLİ: Kilo: {kilo}kg, Boy: {boy}cm, VKİ: {vki:.1f}.
        ANTRENMAN PROGRAMI: {pdf_metni if pdf_metni else 'Henüz PDF yüklenmedi.'}
        
        KURALLAR:
        1. Sadece fitness, spor, sağlık ve beslenme konularında cevap ver. Başka konuları reddet.
        2. Cevap verirken kullanıcının VKİ değerini dikkate al.
        3. Kullanıcı programıyla ilgili bir şey sorarsa, ANTRENMAN PROGRAMI metnine bakarak cevap ver.
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

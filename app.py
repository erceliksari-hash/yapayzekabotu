import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# 1. OTURUM AYARLARI
if 'watchlist' not in st.session_state: st.session_state.watchlist = ['BTC-USD', 'ETH-USD']
if 'alarms' not in st.session_state: st.session_state.alarms = {}

st.set_page_config(page_title="Borsa Ajanı Pro - Otonom", layout="wide")
st.title("🤖 Borsa Ajanı Pro - Otonom İzleme Sistemi")

# Yardımcı Fonksiyonlar
def telegram_bildir(mesaj, token, chat_id):
    try:
        if token and chat_id:
            requests.get(f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={mesaj}")
    except: pass

def coin_listesi_cek():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1"
        data = requests.get(url).json()
        return [f"{c['symbol'].upper()}-USD" for c in data]
    except: return ['BTC-USD', 'ETH-USD']

# 2. SOL MENÜ (AYARLAR VE ALARMLAR)
st.sidebar.header("Portföy Yönetimi")
token = st.sidebar.text_input("Telegram Bot Token", type="password")
cid = st.sidebar.text_input("Chat ID")

st.sidebar.markdown("---")
populer_coins = coin_listesi_cek()
yeni_eklenen = st.sidebar.selectbox("Varlık Seç ve Ekle:", populer_coins)
if st.sidebar.button("Listeye Ekle"):
    if yeni_eklenen not in st.session_state.watchlist:
        st.session_state.watchlist.append(yeni_eklenen)
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Alarm Kur")
secili_alarm = st.sidebar.selectbox("Alarm Kurulacak Varlık:", st.session_state.watchlist)
fiyat_seviyesi = st.sidebar.number_input("Alarm Fiyatı:", value=0.0)
if st.sidebar.button("Alarmı Kur"):
    st.session_state.alarms[secili_alarm] = fiyat_seviyesi
    st.sidebar.success("Alarm başarıyla eklendi!")

# 3. OTONOM KONTROL MEKANİZMASI (Sayfa açıldığında otomatik çalışır)
if st.session_state.alarms:
    st.info("🔄 Otonom Kontrol: Alarmlarınız taranıyor...")
    for sembol, seviye in st.session_state.alarms.items():
        df = yf.download(sembol, period="1d", interval="1h", progress=False)
        if not df.empty:
            fiyat = float(df['Close'].iloc[-1])
            if fiyat <= seviye:
                mesaj = f"⚠️ ALARM! {sembol} fiyatı {fiyat:.2f} seviyesine geriledi!"
                telegram_bildir(mesaj, token, cid)
                st.warning(mesaj)

# 4. GRAFİK VE ANALİZ
st.subheader("Varlık Analizi")
secili_sembol = st.selectbox("Grafiğini İncele:", st.session_state.watchlist)

if st.button("Güncel Analiz Et"):
    df = yf.download(secili_sembol, period="1mo", interval="1h")
    if not df.empty:
        # Mum Grafiği
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # Mum Grafiği Anatomisi
        
        
        # İndirme
        csv = df.to_csv().encode('utf-8')
        st.download_button("📊 Verileri Excel (CSV) Olarak İndir", csv, f"{secili_sembol}_data.csv", "text/csv")
        
        st.success(f"{secili_sembol} teknik analizi güncellendi.")
    else:
        st.error("Veri alınamadı.")

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests # Telegram için eklendi

# 1. OTURUM AYARLARI
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ['BTC-USD', 'ETH-USD']

st.set_page_config(page_title="Borsa Ajanı Pro - Final", layout="wide")
st.title("📈 Borsa Ajanı Pro - Otonom Asistan")

# Telegram Gönderim Fonksiyonu
def telegram_bildir(mesaj, token, chat_id):
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={mesaj}"
    requests.get(url)

# 2. İZLEME LİSTESİ VE TELEGRAM AYARLARI (Sol Menü)
st.sidebar.header("Ayarlar")
telegram_token = st.sidebar.text_input("Telegram Bot Token", type="password")
chat_id = st.sidebar.text_input("Chat ID")

st.sidebar.markdown("---")
yeni_sembol = st.sidebar.text_input("Varlık Ekle").upper()
if st.sidebar.button("Listeye Ekle"):
    if yeni_sembol and yeni_sembol not in st.session_state.watchlist:
        st.session_state.watchlist.append(yeni_sembol)
        st.rerun()

# 3. VERİ İŞLEME
@st.cache_data
def veri_isle(sembol, periyot, interval):
    veri = yf.download(sembol, period=periyot, interval=interval)
    if veri.empty: return veri
    if isinstance(veri.columns, pd.MultiIndex): veri.columns = veri.columns.droplevel(1)
    # Basit İndikatörler
    veri['RSI'] = 100 - (100 / (1 + (veri['Close'].diff().clip(lower=0).ewm(com=13).mean() / (-veri['Close'].diff().clip(upper=0)).ewm(com=13).mean())))
    veri['MACD'] = veri['Close'].ewm(span=12, adjust=False).mean() - veri['Close'].ewm(span=26, adjust=False).mean()
    veri['MACD_Sinyal'] = veri['MACD'].ewm(span=9, adjust=False).mean()
    return veri

# 4. ANALİZ VE İŞLEMLER
secili_sembol = st.selectbox("Varlık Seç:", st.session_state.watchlist)
df = veri_isle(secili_sembol, "1mo", "1h")

if st.button("Analiz Et ve Raporla"):
    if not df.empty:
        son = df.iloc[-1]
        
        # 1. Mum Grafiği
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        st.plotly_chart(fig, use_container_width=True)
        
        # 2. Excel'e Aktarma
        csv = df.to_csv().encode('utf-8')
        st.download_button("📊 Verileri Excel (CSV) Olarak İndir", csv, f"{secili_sembol}_analiz.csv", "text/csv")
        
        # 3. Karar ve Telegram Bildirimi
        sinyal = "BEKLE"
        if son['RSI'] < 40 and son['MACD'] > son['MACD_Sinyal']: sinyal = "GÜÇLÜ AL"
        elif son['RSI'] > 60 and son['MACD'] < son['MACD_Sinyal']: sinyal = "GÜÇLÜ SAT"
        
        st.subheader(f"Sinyal: {sinyal}")
        
        if sinyal != "BEKLE" and telegram_token and chat_id:
            telegram_bildir(f"Sinyal: {secili_sembol} - {sinyal}", telegram_token, chat_id)
            st.success("Telegram üzerinden bildirim gönderildi!")

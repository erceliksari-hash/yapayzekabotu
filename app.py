import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# 1. OTURUM VE AYARLAR
if 'watchlist' not in st.session_state: st.session_state.watchlist = ['BTC-USD', 'ETH-USD']
if 'alarms' not in st.session_state: st.session_state.alarms = {}

st.set_page_config(page_title="Borsa Ajanı Pro - Final", layout="wide")
st.title("🤖 Borsa Ajanı Pro - Otonom Analiz İstasyonu")

# YARDIMCI FONKSİYONLAR
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

def hesapla_indikatorler(df):
    # RSI Hesaplama
    delta = df['Close'].diff()
    gain = delta.clip(lower=0); loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    # MACD Hesaplama
    df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD_Sinyal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

# 2. SOL MENÜ (AYARLAR)
st.sidebar.header("Portföy ve Alarm")
token = st.sidebar.text_input("Telegram Token", type="password")
cid = st.sidebar.text_input("Chat ID")

st.sidebar.markdown("---")
populer_coins = coin_listesi_cek()
yeni_eklenen = st.sidebar.selectbox("Popüler Kriptolar:", populer_coins)
if st.sidebar.button("Listeye Ekle"):
    if yeni_eklenen not in st.session_state.watchlist:
        st.session_state.watchlist.append(yeni_eklenen)
        st.rerun()

st.sidebar.markdown("---")
secili_alarm = st.sidebar.selectbox("Alarm Kur:", st.session_state.watchlist)
fiyat_seviyesi = st.sidebar.number_input("Alarm Fiyat Seviyesi:", value=0.0)
if st.sidebar.button("Alarmı Kur"):
    st.session_state.alarms[secili_alarm] = fiyat_seviyesi
    st.sidebar.success("Alarm kuruldu!")

# 3. OTONOM KONTROL
if st.session_state.alarms:
    for sembol, seviye in st.session_state.alarms.items():
        df_anlik = yf.download(sembol, period="1d", interval="1h", progress=False)
        if not df_anlik.empty:
            if float(df_anlik['Close'].iloc[-1]) <= seviye:
                telegram_bildir(f"⚠️ ALARM: {sembol} fiyatı {seviye} seviyesine geldi!", token, cid)

# 4. ANALİZ VE GÖRSELLEŞTİRME
secili_sembol = st.selectbox("Analiz edilecek varlık:", st.session_state.watchlist)

if st.button("Analiz Et"):
    df = yf.download(secili_sembol, period="1mo", interval="1h")
    if not df.empty:
        df = hesapla_indikatorler(df)
        
        # Mum Grafiği
        st.subheader(f"{secili_sembol} - Teknik Analiz")
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(xaxis_rangeslider_visible=False, height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # İndikatör Grafikleri
        c1, c2 = st.columns(2)
        c1.subheader("RSI Göstergesi")
        c1.line_chart(df['RSI'])
        c2.subheader("MACD Göstergesi")
        c2.line_chart(df[['MACD', 'MACD_Sinyal']])
        
        
        
        csv = df.to_csv().encode('utf-8')
        st.download_button("📊 Verileri Excel Olarak İndir", csv, "analiz_raporu.csv", "text/csv")
    else:
        st.error("Veri alınamadı.")

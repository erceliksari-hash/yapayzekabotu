import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# 1. OTURUM AYARLARI
if 'watchlist' not in st.session_state: st.session_state.watchlist = ['BTC-USD', 'ETH-USD']
if 'alarms' not in st.session_state: st.session_state.alarms = {}

st.set_page_config(page_title="Borsa Ajanı Pro - Otonom", layout="wide")
st.title("🤖 Borsa Ajanı Pro - Otonom Analiz İstasyonu")

# --- YARDIMCI FONKSİYONLAR ---
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

def veriyi_temizle(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
    return df

def kendi_indikatorun_hesapla(df):
    df['Ozel_SMA'] = df['Close'].rolling(window=20).mean()
    return df

def hesapla_tum_indikatorler(df):
    df = veriyi_temizle(df)
    delta = df['Close'].diff()
    avg_gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (avg_gain / avg_loss)))
    df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD_Sinyal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return kendi_indikatorun_hesapla(df)

# 2. SOL MENÜ
st.sidebar.header("Kontrol Paneli")
token = st.sidebar.text_input("Telegram Token", type="password")
cid = st.sidebar.text_input("Chat ID")
zaman_secenekleri = {"1 Dakika": "1m", "5 Dakika": "5m", "1 Saat": "1h", "1 Gün": "1d"}
interval = st.sidebar.selectbox("Zaman Aralığı:", list(zaman_secenekleri.keys()))
interval_val = zaman_secenekleri[interval]

st.sidebar.markdown("---")
populer_coins = coin_listesi_cek()
yeni_eklenen = st.sidebar.selectbox("Kripto Seç:", populer_coins)
if st.sidebar.button("Listeye Ekle"):
    if yeni_eklenen not in st.session_state.watchlist:
        st.session_state.watchlist.append(yeni_eklenen)
        st.rerun()

secili_sembol = st.sidebar.selectbox("Analiz Edilecek:", st.session_state.watchlist)
fiyat_seviyesi = st.sidebar.number_input("Alarm Seviyesi:", value=0.0)
if st.sidebar.button("Alarmı Kur"):
    st.session_state.alarms[secili_sembol] = fiyat_seviyesi
    st.sidebar.success("Alarm kuruldu!")

# 3. ANLIK FİYAT VE OTONOM KONTROL
ticker = yf.Ticker(secili_sembol)
data = ticker.history(period="1d")
anlik_fiyat = float(data['Close'].iloc[-1]) if not data.empty else 0.0
st.subheader(f"📊 {secili_sembol} - Anlık Fiyat: ${anlik_fiyat:.2f}")

if st.session_state.alarms:
    for sembol, seviye in st.session_state.alarms.items():
        if anlik_fiyat <= seviye:
            telegram_bildir(f"⚠️ ALARM! {sembol} fiyatı {anlik_fiyat:.2f} seviyesine geriledi!", token, cid)

# 4. GRAFİK VE ANALİZ
if st.button("Analiz Et"):
    df = yf.download(secili_sembol, period="1mo", interval=interval_val)
    if not df.empty:
        df = hesapla_tum_indikatorler(df)
        
        st.subheader(f"{secili_sembol} Teknik Analiz Grafiği")
        
        # Plotly grafiklerini tetiklemek için açıkça tanımlıyoruz
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.add_trace(go.Scatter(x=df.index, y=df['Ozel_SMA'], name='Özel İndikatör', line=dict(color='orange')))
        st.plotly_chart(fig, use_container_width=True)
        
        
        
        c1, c2 = st.columns(2)
        c1.line_chart(df['RSI'])
        c2.line_chart(df[['MACD', 'MACD_Sinyal']])
        
        df_export = df.sort_index(ascending=False)
        csv = df_export.to_csv().encode('utf-8')
        st.download_button("📊 Verileri İndir (En güncel tarih üstte)", csv, "rapor.csv", "text/csv")
    else:
        st.error("Veri alınamadı. Lütfen seçili kriptonun seçilen zaman aralığında veri ürettiğinden emin olun.")

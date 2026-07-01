import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# 1. OTURUM AYARLARI
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ['BTC-USD', 'ETH-USD']

st.set_page_config(page_title="Borsa Ajanı Pro - Final", layout="wide")
st.title("📈 Borsa Ajanı Pro - Otonom Kripto Ajanı")

# Telegram Bildirim Fonksiyonu
def telegram_bildir(mesaj, token, chat_id):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={mesaj}"
        requests.get(url)
    except:
        pass

# CoinGecko'dan En İyi 20 Kriptoyu Çekme
def coin_listesi_cek():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return [f"{coin['symbol'].upper()}-USD" for coin in data]
    except:
        return ['BTC-USD', 'ETH-USD', 'SOL-USD']
    return ['BTC-USD', 'ETH-USD']

# 2. SOL MENÜ VE PORTFÖY YÖNETİMİ
st.sidebar.header("Portföy Yönetimi")
telegram_token = st.sidebar.text_input("Telegram Bot Token", type="password")
chat_id = st.sidebar.text_input("Chat ID")

st.sidebar.markdown("---")
populer_coins = coin_listesi_cek()
yeni_eklenen = st.sidebar.selectbox("Popüler Kriptolardan Seç:", populer_coins)

if st.sidebar.button("Listeye Ekle"):
    if yeni_eklenen not in st.session_state.watchlist:
        st.session_state.watchlist.append(yeni_eklenen)
        st.rerun()

st.sidebar.markdown("### İzleme Listeniz")
for sembol in st.session_state.watchlist:
    col_a, col_b = st.sidebar.columns([3, 1])
    col_a.write(sembol)
    if col_b.button("🗑️", key=f"del_{sembol}"):
        st.session_state.watchlist.remove(sembol)
        st.rerun()

# 3. VERİ İŞLEME
@st.cache_data
def veri_isle(sembol, periyot, interval):
    df = yf.download(sembol, period=periyot, interval=interval)
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
    
    # İndikatörler
    delta = df['Close'].diff()
    df['RSI'] = 100 - (100 / (1 + (delta.clip(lower=0).ewm(com=13).mean() / (-delta.clip(upper=0)).ewm(com=13).mean())))
    df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD_Sinyal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

# 4. ANALİZ EKRANI
secili_sembol = st.selectbox("Analiz edilecek varlığı seç:", st.session_state.watchlist)

if st.button("Analiz Et ve Raporla"):
    with st.spinner(f"{secili_sembol} analiz ediliyor..."):
        df = veri_isle(secili_sembol, "1mo", "1h")
        
        if not df.empty:
            st.subheader(f"{secili_sembol} Fiyat Hareketi")
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
            fig.update_layout(xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            
            # Excel İndirme
            csv = df.to_csv().encode('utf-8')
            st.download_button("📊 Verileri İndir (CSV)", csv, f"{secili_sembol}_data.csv", "text/csv")
            
            # Karar ve Bildirim
            son = df.iloc[-1]
            sinyal = "BEKLE"
            if son['RSI'] < 40 and son['MACD'] > son['MACD_Sinyal']: sinyal = "GÜÇLÜ AL"
            elif son['RSI'] > 60 and son['MACD'] < son['MACD_Sinyal']: sinyal = "GÜÇLÜ SAT"
            
            st.info(f"Karar: {sinyal} | RSI: {son['RSI']:.2f}")
            
            if sinyal != "BEKLE" and telegram_token and chat_id:
                telegram_bildir(f"Sinyal: {secili_sembol} - {sinyal}", telegram_token, chat_id)
                st.success("Telegram bildirimi gönderildi!")
        else:
            st.error("Veri alınamadı.")

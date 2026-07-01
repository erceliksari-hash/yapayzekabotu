import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# 1. OTURUM AYARLARI
if 'watchlist' not in st.session_state: st.session_state.watchlist = ['BTC-USD', 'ETH-USD']
if 'alarms' not in st.session_state: st.session_state.alarms = {}

st.set_page_config(page_title="Borsa Ajanı Pro - Final", layout="wide")
st.title("🤖 Borsa Ajanı Pro - Strateji ve Analiz İstasyonu")

# --- KENDİ İNDİKATÖRÜNÜ EKLEME ALANI ---
def kendi_indikatorun_hesapla(df):
    # Örnek: 20 periyotluk Hareketli Ortalama (SMA)
    # Buraya kendi formülünü (örn: EMA, Bollinger, VWAP) yazabilirsin
    df['Ozel_SMA'] = df['Close'].rolling(window=20).mean()
    return df

# --- YARDIMCI FONKSİYONLAR ---
def veriyi_temizle(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
    return df

def hesapla_tum_indikatorler(df):
    df = veriyi_temizle(df)
    # Standartlar
    delta = df['Close'].diff()
    avg_gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (avg_gain / avg_loss)))
    df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD_Sinyal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # Özel İndikatörünü Çalıştır
    df = kendi_indikatorun_hesapla(df)
    return df

def analiz_motoru(df):
    son = df.iloc[-1]
    # Destek/Direnç hesaplama
    destek = df['Low'].rolling(20).min().iloc[-1]
    direnc = df['High'].rolling(20).max().iloc[-1]
    
    sinyal = "BEKLE"
    if son['RSI'] < 40 and son['MACD'] > son['MACD_Sinyal']: sinyal = "🚀 GÜÇLÜ AL"
    elif son['RSI'] > 60 and son['MACD'] < son['MACD_Sinyal']: sinyal = "📉 GÜÇLÜ SAT"
    
    return sinyal, destek, direnc

# 2. SOL MENÜ
st.sidebar.header("Portföy ve Strateji")
token = st.sidebar.text_input("Telegram Token", type="password")
cid = st.sidebar.text_input("Chat ID")

populer_coins = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD']
secim = st.sidebar.selectbox("Kripto Ekle:", populer_coins)
if st.sidebar.button("Listeye Ekle"):
    if secim not in st.session_state.watchlist: st.session_state.watchlist.append(secim)

# 3. ANALİZ EKRANI
secili_sembol = st.selectbox("Analiz edilecek varlık:", st.session_state.watchlist)

if st.button("Analiz Et ve Strateji Uygula"):
    df = hesapla_tum_indikatorler(yf.download(secili_sembol, period="1mo", interval="1h"))
    sinyal, destek, direnc = analiz_motoru(df)
    
    st.subheader(f"Sinyal: {sinyal}")
    col1, col2 = st.columns(2)
    col1.metric("Tahmini Destek (Alış)", f"{destek:.2f}")
    col2.metric("Tahmini Direnç (Satış)", f"{direnc:.2f}")
    
    # Grafik
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.add_trace(go.Scatter(x=df.index, y=df['Ozel_SMA'], name='Özel SMA İndikatörü', line=dict(color='orange')))
    st.plotly_chart(fig, use_container_width=True)
    
    # İndikatörler
    c1, c2 = st.columns(2)
    c1.line_chart(df['RSI'])
    c2.line_chart(df[['MACD', 'MACD_Sinyal']])
    
    st.info("Destek ve Direnç seviyeleri, son 20 mumun en düşük ve en yüksek değerlerine göre belirlenmiştir.")

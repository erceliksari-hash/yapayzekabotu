import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# 1. OTURUM AYARLARI
if 'watchlist' not in st.session_state: st.session_state.watchlist = ['BTC-USD', 'ETH-USD']
if 'alarms' not in st.session_state: st.session_state.alarms = {}

st.set_page_config(page_title="Borsa Ajanı Pro", layout="wide")
st.title("🤖 Borsa Ajanı Pro - Otonom Analiz İstasyonu")

# --- YARDIMCI FONKSİYONLAR ---
def veriyi_temizle(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
    return df

def hesapla_indikatorler(df):
    df = veriyi_temizle(df)
    # RSI
    delta = df['Close'].diff()
    gain = delta.clip(lower=0); loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    # MACD
    df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD_Sinyal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

def grafik_analiz_et(df):
    son = df.iloc[-1]
    rsi = son['RSI']
    macd = son['MACD']
    sig = son['MACD_Sinyal']
    
    yorum = f"### 🧠 Yapay Zeka Grafik Yorumu\n"
    yorum += f"- **RSI:** {rsi:.2f} " + ("(Aşırı Alım)" if rsi > 70 else ("(Aşırı Satım)" if rsi < 30 else "(Nötr)")) + "\n"
    yorum += f"- **MACD:** " + ("Pozitif Momentum" if macd > sig else "Negatif Momentum") + "\n"
    yorum += "- **Karar:** " + ("🚀 ALIM FIRSATI OLABİLİR" if (rsi < 40 and macd > sig) else ("📉 DİKKAT: SATIŞ BASKISI" if (rsi > 60 and macd < sig) else "⚖️ BEKLE/İZLE"))
    return yorum

# 2. SOL MENÜ (AYARLAR)
st.sidebar.header("Portföy ve Alarm")
token = st.sidebar.text_input("Telegram Token", type="password")
cid = st.sidebar.text_input("Chat ID")

# Kripto Seçimi ve Ekleme
populer_coins = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD', 'BNB-USD', 'XRP-USD']
yeni_eklenen = st.sidebar.selectbox("Kripto Seç:", populer_coins)
if st.sidebar.button("Listeye Ekle"):
    if yeni_eklenen not in st.session_state.watchlist:
        st.session_state.watchlist.append(yeni_eklenen)
        st.rerun()

# Alarm Kurma
secili_alarm = st.sidebar.selectbox("Alarm Kur:", st.session_state.watchlist)
fiyat_seviyesi = st.sidebar.number_input("Alarm Seviyesi:", value=0.0)
if st.sidebar.button("Alarmı Kur"):
    st.session_state.alarms[secili_alarm] = fiyat_seviyesi

# 3. OTONOM KONTROL
if st.session_state.alarms:
    for sembol, seviye in st.session_state.alarms.items():
        df_anlik = veriyi_temizle(yf.download(sembol, period="1d", interval="1h", progress=False))
        if not df_anlik.empty and float(df_anlik['Close'].iloc[-1]) <= seviye:
            try: requests.get(f"https://api.telegram.org/bot{token}/sendMessage?chat_id={cid}&text=⚠️ ALARM! {sembol} düştü.")
            except: pass

# 4. ANALİZ VE GÖRSELLEŞTİRME
secili_sembol = st.selectbox("Analiz edilecek varlık:", st.session_state.watchlist)

if st.button("Analiz Et"):
    df = yf.download(secili_sembol, period="1mo", interval="1h")
    if not df.empty:
        df = hesapla_indikatorler(df)
        
        # Mum Grafiği
        st.subheader(f"{secili_sembol} - Teknik Analiz")
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # Mum Grafiği Nedir?
        st.info("Mum grafikleri, bir zaman dilimindeki fiyat hareketlerini gösterir.")
        
        
        # Analiz ve İndikatörler
        st.markdown(grafik_analiz_et(df))
        
        c1, c2 = st.columns(2)
        c1.line_chart(df['RSI'])
        c2.line_chart(df[['MACD', 'MACD_Sinyal']])
        
        csv = df.to_csv().encode('utf-8')
        st.download_button("📊 Raporu İndir", csv, "rapor.csv", "text/csv")

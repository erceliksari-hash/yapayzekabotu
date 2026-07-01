import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Borsa Ajanı Pro - Final", layout="wide")
st.title("📈 Borsa Ajanı Pro - Otonom Analiz Sistemi")
st.markdown("---")

# 2. AYARLAR MENÜSÜ
st.sidebar.header("Kontrol Paneli")
sembol = st.sidebar.text_input("Varlık Sembolü (Örn: BTC-USD, AAPL)", value="BTC-USD")

zaman_secenekleri = {
    "1 Dakikalık (Son 7 Gün)": ("7d", "1m"),
    "5 Dakikalık (Son 5 Gün)": ("5d", "5m"),
    "15 Dakikalık (Son 1 Ay)": ("1mo", "15m"),
    "30 Dakikalık (Son 1 Ay)": ("1mo", "30m"),
    "1 Saatlik (Son 1 Ay)": ("1mo", "1h"),
    "Günlük (Son 6 Ay)": ("6mo", "1d"),
    "Haftalık (Son 2 Yıl)": ("2y", "1wk")
}

secilen_zaman = st.sidebar.selectbox("Mum Zaman Aralığı", list(zaman_secenekleri.keys()), index=1)
periyot_degeri, interval_degeri = zaman_secenekleri[secilen_zaman]

st.sidebar.markdown("---")
st.sidebar.subheader("İndikatör Parametreleri")
rsi_p = st.sidebar.slider("RSI Periyodu", 5, 30, 14)
macd_f = st.sidebar.slider("MACD Hızlı", 5, 20, 12)
macd_s = st.sidebar.slider("MACD Yavaş", 21, 50, 26)
macd_sig = st.sidebar.slider("MACD Sinyal", 5, 15, 9)

# 3. VERİ İŞLEME
@st.cache_data
def veri_isle(sembol, periyot, interval, rsi_p, macd_f, macd_s, macd_sig):
    veri = yf.download(sembol, period=periyot, interval=interval)
    if veri.empty: return veri
    if isinstance(veri.columns, pd.MultiIndex): veri.columns = veri.columns.droplevel(1)
    
    # RSI
    delta = veri['Close'].diff()
    gain = delta.clip(lower=0); loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=rsi_p - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=rsi_p - 1, adjust=False).mean()
    rs = avg_gain / avg_loss
    veri['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = veri['Close'].ewm(span=macd_f, adjust=False).mean()
    exp2 = veri['Close'].ewm(span=macd_s, adjust=False).mean()
    veri['MACD'] = exp1 - exp2
    veri['MACD_Sinyal'] = veri['MACD'].ewm(span=macd_sig, adjust=False).mean()
    return veri

# 4. ÇALIŞTIRMA VE GÖRSELLEŞTİRME
if st.sidebar.button("Stratejiyi Analiz Et"):
    with st.spinner("Piyasa verileri işleniyor..."):
        df = veri_isle(sembol, periyot_degeri, interval_degeri, rsi_p, macd_f, macd_s, macd_sig)
        
        if not df.empty:
            # Mumu Anlama Rehberi
            st.write("### 1. Fiyat Hareketi (Mum Grafiği)")
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
            fig.update_layout(xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("2. RSI")
                st.line_chart(df['RSI'])
            with col2:
                st.subheader("3. MACD")
                st.line_chart(df[['MACD', 'MACD_Sinyal']])

            # OTOMATİK ANALİZ
            st.markdown("---")
            st.subheader("📊 Otomatik Grafik Analizi")
            son = df.iloc[-1]
            analiz = f"**Durum:** {sembol} şu an {son['Close']:.2f} seviyesinde. "
            analiz += f"RSI değeri {son['RSI']:.2f} ile " + ("aşırı alım bölgesinde!" if son['RSI'] > 70 else ("aşırı satım bölgesinde!" if son['RSI'] < 30 else "nötr bölgede."))
            st.info(analiz)

            # KARAR MOTORU
            st.markdown("---")
            st.header("🤖 Karar Motoru")
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("RSI", f"{son['RSI']:.2f}")
            with c2: st.metric("MACD", f"{son['MACD']:.2f}")
            
            if (son['RSI'] < 40) and (son['MACD'] > son['MACD_Sinyal']):
                st.success("🚀 GÜÇLÜ AL SİNYALİ!")
            elif (son['RSI'] > 60) and (son['MACD'] < son['MACD_Sinyal']):
                st.error("📉 GÜÇLÜ SAT SİNYALİ!")
            else:
                st.warning("⚖️ KARARSIZ - BEKLE")
        else:
            st.error("Veri bulunamadı. Lütfen sembolü kontrol edin.")

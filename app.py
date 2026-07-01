import streamlit as st
import yfinance as yf
import pandas as pd

# Sayfa tasarımı ayarları
st.set_page_config(page_title="Borsa Ajanı Pro v2", layout="wide")
st.title("Borsa Ajanı Pro - Teknik Analiz Paneli")
st.markdown("---")

# Sol menü - Dinamik Parametre Ayarları
st.sidebar.header("Strateji ve İndikatör Ayarları")
sembol = st.sidebar.text_input("Varlık Sembolü (Örn: BTC-USD, ETH-USD, GC=F)", value="BTC-USD")
periyot = st.sidebar.selectbox("Zaman Aralığı", ["1mo", "3mo", "6mo", "1y"], index=2)

st.sidebar.markdown("---")
st.sidebar.subheader("İndikatör Parametreleri")
rsi_periyot = st.sidebar.slider("RSI Periyodu", 5, 30, 14)
macd_hizli = st.sidebar.slider("MACD Hızlı Dönem", 5, 20, 12)
macd_yavas = st.sidebar.slider("MACD Yavaş Dönem", 21, 50, 26)
macd_sinyal = st.sidebar.slider("MACD Sinyal Dönemi", 5, 15, 9)

# Veri çekme ve İndikatör Hesaplama Fonksiyonu
@st.cache_data
def veri_isle(sembol, periyot, rsi_p, macd_f, macd_s, macd_sig):
    # Veriyi indiriyoruz
    veri = yf.download(sembol, period=periyot, interval="1d")
    if veri.empty:
        return veri
        
    # yfinance bazen çoklu indeks döndürebilir, bunu düzeltiyoruz
    if isinstance(veri.columns, pd.MultiIndex):
        veri.columns = veri.columns.droplevel(1)
        
    # --- RSI HESAPLAMA (Wilder's Smoothing) ---
    delta = veri['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=rsi_p - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=rsi_p - 1, adjust=False).mean()
    rs = avg_gain / avg_loss
    veri['RSI'] = 100 - (100 / (1 + rs))
    
    # --- MACD HESAPLAMA ---
    exp1 = veri['Close'].ewm(span=macd_f, adjust=False).mean()
    exp2 = veri['Close'].ewm(span=macd_s, adjust=False).mean()
    veri['MACD'] = exp1 - exp2
    veri['MACD_Sinyal'] = veri['MACD'].ewm(span=macd_sig, adjust=False).mean()
    veri['MACD_Hist'] = veri['MACD'] - veri['MACD_Sinyal']
    
    return veri

# Uygulamayı Çalıştırma Butonu
if st.sidebar.button("Stratejiyi Analiz Et"):
    with st.spinner("Piyasa verileri taranıyor ve indikatörler hesaplanıyor..."):
        df = veri_isle(sembol, periyot, rsi_periyot, macd_hizli, macd_yavas, macd_sinyal)
        
        if not df.empty:
            st.success(f"{sembol} İçin Analiz Tamamlandı!")
            
            # 1. GRAFİK: FİYAT HAREKETİ
            st.subheader("1. Varlık Kapanış Fiyatı")
            st.line_chart(df['Close'])
            
            # Ekranı yan yana iki bölüme ayırarak indikatörleri yerleştiriyoruz
            col1, col2 = st.columns(2)
            
            with col1:
                # 2. GRAFİK: RSI
                st.subheader(f"2. RSI (Periyot: {rsi_periyot})")
                st.line_chart(df['RSI'])
                st.caption("Kılavuz: 70 Üzeri Aşırı Alım (Satış Baskısı), 30 Altı Aşırı Satım (Alım Baskısı)")
                
            with col2:
                # 3. GRAFİK: MACD
                st.subheader("3. MACD & Sinyal Çizgisi")
                st.line_chart(df[['MACD', 'MACD_Sinyal']])
                st.caption("Kılavuz: MACD çizgisi Sinyal çizgisini yukarı keserse AL, aşağı keserse SAT sinyali üretilir.")
                
            # Son Değerlerin Tablosu
            st.markdown("---")
            st.subheader("Son 3 Günün İndikatör Değer Özetleri")
            st.dataframe(df[['Close', 'RSI', 'MACD', 'MACD_Sinyal']].tail(3))
            
        else:
            st.error("Veri alınamadı. Sembolün doğruluğundan emin olun.")
# --- KARAR MEKANİZMASI (BOTUN BEYNİ) ---
            st.markdown("---")
            st.header("🤖 Yapay Zeka Karar Motoru")
            
            # DataFrame'deki en son satırı (en güncel veriyi) alıyoruz
            son_veri = df.iloc[-1]
            son_rsi = son_veri['RSI']
            son_macd = son_veri['MACD']
            son_sinyal = son_veri['MACD_Sinyal']
            
            # Karar ekranı için 3 kolon oluşturuyoruz
            karar_col1, karar_col2, karar_col3 = st.columns(3)
            
            with karar_col1:
                st.subheader("RSI Stratejisi")
                if son_rsi < 30:
                    st.success(f"🟢 GÜÇLÜ AL\nRSI: {son_rsi:.2f}")
                    st.caption("Aşırı satım bölgesinde, fiyat ucuzlamış olabilir.")
                elif son_rsi > 70:
                    st.error(f"🔴 GÜÇLÜ SAT\nRSI: {son_rsi:.2f}")
                    st.caption("Aşırı alım bölgesinde, fiyatta şişkinlik olabilir.")
                else:
                    st.warning(f"🟡 BEKLE\nRSI: {son_rsi:.2f}")
                    st.caption("Piyasa şu an nötr bölgede (30-70 arası).")

            with karar_col2:
                st.subheader("MACD Stratejisi")
                if son_macd > son_sinyal:
                    st.success(f"🟢 AL YÖNÜNDE\nMACD, Sinyalin Üzerinde")
                    st.caption("Yükseliş trendi (Boğa piyasası) sinyali.")
                elif son_macd < son_sinyal:
                    st.error(f"🔴 SAT YÖNÜNDE\nMACD, Sinyalin Altında")
                    st.caption("Düşüş trendi (Ayı piyasası) sinyali.")
                else:
                    st.warning("🟡 YÖNSÜZ\nKesişim Noktasında")
                    
            with karar_col3:
                st.subheader("BİRLEŞTİRİLMİŞ SONUÇ")
                # İki indikatör de AL diyorsa
                if (son_rsi < 30 or son_rsi < 40) and (son_macd > son_sinyal):
                    st.success("🚀 KESİN AL SİNYALİ!")
                # İki indikatör de SAT diyorsa
                elif (son_rsi > 70 or son_rsi > 60) and (son_macd < son_sinyal):
                    st.error("📉 KESİN SAT SİNYALİ!")
                # İndikatörler uyumsuzsa
                else:
                    st.info("⚖️ KARARSIZ PİYASA (İŞLEME GİRME)")
      

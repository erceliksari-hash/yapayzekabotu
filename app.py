import streamlit as st
import yfinance as yf
import pandas as pd

# 1. SAYFA TASARIMI
st.set_page_config(page_title="Borsa Ajanı Pro v4", layout="wide")
st.title("Borsa Ajanı Pro - Otonom Analiz Sistemi")
st.markdown("---")

# 2. SOL MENÜ VE ZAMAN AYARLARI
st.sidebar.header("Strateji ve İndikatör Ayarları")
sembol = st.sidebar.text_input("Varlık Sembolü (Örn: BTC-USD, ETH-USD, AAPL)", value="BTC-USD")

# Zaman Aralıkları Sözlüğü (Periyot ve Mum Aralığı)
zaman_secenekleri = {
    "5 Dakikalık Mumlar (Son 5 Gün)": ("5d", "5m"),
    "15 Dakikalık Mumlar (Son 1 Ay)": ("1mo", "15m"),
    "30 Dakikalık Mumlar (Son 1 Ay)": ("1mo", "30m"),
    "1 Saatlik Mumlar (Son 1 Ay)": ("1mo", "1h"),
    "Günlük Mumlar (Son 6 Ay)": ("6mo", "1d"),
    "Günlük Mumlar (Son 1 Yıl)": ("1y", "1d"),
    "Haftalık Mumlar (Son 2 Yıl)": ("2y", "1wk")
}

secilen_zaman = st.sidebar.selectbox("Mum Zaman Aralığı", list(zaman_secenekleri.keys()), index=4)
periyot_degeri, interval_degeri = zaman_secenekleri[secilen_zaman]

st.sidebar.markdown("---")
st.sidebar.subheader("İndikatör Parametreleri")
rsi_periyot = st.sidebar.slider("RSI Periyodu", 5, 30, 14)
macd_hizli = st.sidebar.slider("MACD Hızlı Dönem", 5, 20, 12)
macd_yavas = st.sidebar.slider("MACD Yavaş Dönem", 21, 50, 26)
macd_sinyal = st.sidebar.slider("MACD Sinyal Dönemi", 5, 15, 9)

# 3. VERİ ÇEKME VE İNDİKATÖR HESAPLAMA
@st.cache_data
def veri_isle(sembol, periyot, interval, rsi_p, macd_f, macd_s, macd_sig):
    veri = yf.download(sembol, period=periyot, interval=interval)
    if veri.empty:
        return veri
        
    if isinstance(veri.columns, pd.MultiIndex):
        veri.columns = veri.columns.droplevel(1)
        
    # --- RSI HESAPLAMA ---
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

# 4. ARAYÜZ VE KARAR MOTORU
if st.sidebar.button("Stratejiyi Analiz Et"):
    with st.spinner("Piyasa verileri taranıyor..."):
        df = veri_isle(sembol, periyot_degeri, interval_degeri, rsi_periyot, macd_hizli, macd_yavas, macd_sinyal)
        
        if not df.empty:
            st.success(f"{sembol} İçin Analiz Tamamlandı! ({secilen_zaman})")
            
            # --- 1. GRAFİKLER BÖLÜMÜ ---
            st.subheader("1. Varlık Kapanış Fiyatı")
            st.line_chart(df['Close'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("2. RSI Grafiği")
                st.line_chart(df['RSI'])
            with col2:
                st.subheader("3. MACD Grafiği")
                st.line_chart(df[['MACD', 'MACD_Sinyal']])
                
            # --- 2. OTOMATİK GRAFİK ANALİZİ (YENİ MODÜL) ---
            st.markdown("---")
            st.subheader("📊 Otomatik Grafik Analizi ve Yorumu")
            
            son_veri = df.iloc[-1]
            eski_veri = df.iloc[-5] if len(df) >= 5 else df.iloc[0] # Son 5 mumluk değişime bakıyoruz
            
            fiyat_degisimi = son_veri['Close'] - eski_veri['Close']
            trend_yonu = "yükseliş" if fiyat_degisimi > 0 else "düşüş"
            
            # Analiz Metnini Dinamik Olarak Oluşturma
            analiz_metni = f"**Fiyat Hareketi:** {sembol} varlığının fiyatı son 5 mumluk periyotta **{trend_yonu}** eğilimindedir. Güncel kapanış fiyatı **{son_veri['Close']:.2f}** seviyesinde bulunuyor.\n\n"
            
            analiz_metni += f"**RSI (Göreceli Güç Endeksi):** Güncel RSI değeri **{son_veri['RSI']:.2f}**. "
            if son_veri['RSI'] > 70:
                analiz_metni += "Bu durum, varlığın 'Aşırı Alım' bölgesinde olduğunu gösterir. Piyasada alıcılar çok yorulmuş olabilir ve fiyatta aşağı yönlü bir düzeltme ihtimali masadadır."
            elif son_veri['RSI'] < 30:
                analiz_metni += "Bu durum, varlığın 'Aşırı Satım' bölgesinde olduğunu gösterir. Varlık kısa vadede ucuzlamış olabilir ve yukarı yönlü bir tepki alımı gelebilir."
            else:
                analiz_metni += "RSI nötr bölgede (30-70 arası) yer alıyor. Şu an için piyasada net bir aşırı alım veya aşırı satım baskısı gözlemlenmiyor."
                
            analiz_metni += f"\n\n**MACD (Hareketli Ortalamalar):** MACD çizgisi ({son_veri['MACD']:.2f}), Sinyal çizgisinin ({son_veri['MACD_Sinyal']:.2f}) "
            if son_veri['MACD'] > son_veri['MACD_Sinyal']:
                analiz_metni += "**üzerinde** yer alıyor. Bu kesişim, kısa vadeli momentumun pozitif olduğunu ve alıcıların (boğaların) piyasaya hakim olmaya çalıştığını işaret eder."
            else:
                analiz_metni += "**altında** yer alıyor. Bu kesişim, kısa vadeli momentumun negatif olduğunu ve satıcıların (ayıların) baskın olduğunu gösterir."
            
            # Metni ekrana mavi bir bilgi kutusu içinde yazdır
            st.info(analiz_metni)

            # --- 3. YAPAY ZEKA KARAR MOTORU (BEYİN) ---
            st.markdown("---")
            st.header("🤖 Karar Motoru Sonuçları")
            
            son_rsi = son_veri['RSI']
            son_macd = son_veri['MACD']
            son_sinyal = son_veri['MACD_Sinyal']
            
            karar_col1, karar_col2, karar_col3 = st.columns(3)
            
            with karar_col1:
                st.subheader("RSI Stratejisi")
                if son_rsi < 30:
                    st.success(f"🟢 GÜÇLÜ AL (RSI: {son_rsi:.2f})")
                elif son_rsi > 70:
                    st.error(f"🔴 GÜÇLÜ SAT (RSI: {son_rsi:.2f})")
                else:
                    st.warning(f"🟡 BEKLE (RSI: {son_rsi:.2f})")

            with karar_col2:
                st.subheader("MACD Stratejisi")
                if son_macd > son_sinyal:
                    st.success("🟢 AL YÖNÜNDE")
                elif son_macd < son_sinyal:
                    st.error("🔴 SAT YÖNÜNDE")
                else:
                    st.warning("🟡 YÖNSÜZ")
                    
            with karar_col3:
                st.subheader("BİRLEŞTİRİLMİŞ SONUÇ")
                if (son_rsi < 40) and (son_macd > son_sinyal):
                    st.success("🚀 KESİN AL SİNYALİ!")
                elif (son_rsi > 60) and (son_macd < son_sinyal):
                    st.error("📉 KESİN SAT SİNYALİ!")
                else:
                    st.info("⚖️ KARARSIZ PİYASA (BEKLE)")
        else:
            st.error("Veri alınamadı. Sembol veya zaman aralığı uyumsuz olabilir.")

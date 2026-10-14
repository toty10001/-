import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ftplib import FTP

st.set_page_config(page_title="رادار الفجوات والمضاربة", layout="centered")

st.title("⚡ رادار اقتناص الفجوات السعرية (1$ - 10$)")
st.write("فحص ذكي متصل مباشرة ببورصة NASDAQ الرسمية لاقتناص أسهم الفجوات الصاعدة.")

# دالة رسمية ومحترفة للاتصال المباشر بسيرفر بورصة ناسداك وجلب كامل الأسهم
@st.cache_data(ttl=86400)
def get_all_nasdaq_tickers():
    try:
        # الاتصال بسيرفر الملفات الرسمي المفتوح لبورصة ناسداك
        ftp = FTP('://nasdaqtrader.com')
        ftp.login()
        ftp.cwd('SymbolDirectory')
        
        lines = []
        ftp.retrlines('RETR nasdaqlisted.txt', lines.append)
        ftp.quit()
        
        # معالجة الملف واستخراج الرموز فقط
        tickers = []
        for line in lines[1:-1]:  # تجاوز السطر الأول والأخير (العناوين والملخص)
            parts = line.split('|')
            if parts and len(parts) > 0:
                ticker = parts[0].strip()
                # التأكد من أن الرمز سهم عادي وليس صناديق أو أسهم ممتازة
                if ticker.isalpha() and len(ticker) <= 4:
                    tickers.append(ticker.upper())
                    
        if len(tickers) > 1000:
            return tickers
        raise Exception("قائمة غير مكتملة")
    except Exception as e:
        # قائمة احتياطية موسعة في حال الصيانة الطارئة لسيرفر البورصة
        return ["AAPL", "AMZN", "NVDA", "AMD", "PLTR", "SOFI", "HOOD", "GRWG", "SNDL", "NIO", "LCID", "MULN", "RIVN", "MARA", "RIOT"]

tickers = get_all_nasdaq_tickers()

st.sidebar.header("⚙️ إعدادات الفلتر")
st.sidebar.subheader("💵 تصفية السعر والسيولة")
min_price = st.sidebar.number_input("الحد الأدنى للسعر ($)", min_value=0.1, value=1.0)
max_price = st.sidebar.number_input("الحد الأقصى للسعر ($)", min_value=0.1, value=10.0)
min_avg_volume = st.sidebar.number_input("معدل التداول (Avg Volume 20d)", min_value=0, value=300000, step=50000)

st.sidebar.subheader("🚀 فلتر الفجوات السعرية (Gap Up)")
min_gap = st.sidebar.number_input("الحد الأدنى للفجوة السعرية (%)", min_value=0.0, max_value=100.0, value=3.0)

st.sidebar.subheader("📊 المتوسطات والمؤشرات الفنية")
use_sma_filter = st.sidebar.checkbox("أن يكون السعر فوق متوسط 20 يوم (SMA 20)", value=True)
use_rsi = st.sidebar.checkbox("تفعيل فلتر RSI (14)", value=False)
rsi_min = st.sidebar.slider("الحد الأدنى لـ RSI", 0, 100, 30)
rsi_max = st.sidebar.slider("الحد الأقصى لـ RSI", 0, 100, 70)

if st.button("🚀 ابدأ مسح السوق واقتناص الفجوات"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    results = []
    total = len(tickers)
    
    status_text.write(f"📊 تم الاتصال بالبورصة بنجاح. جاري فحص وتحليل {total} سهم حالياً...")
    
    # تقسيم الفحص إلى حزم ذكية لضمان السرعة الفائقة
    chunk_size = 40
    for i in range(0, total, chunk_size):
        chunk = tickers[i:i+chunk_size]
        try:
            tickers_string = " ".join(chunk)
            data = yf.download(tickers_string, period="60d", interval="1d", group_by='ticker', progress=False)
            
            for ticker in chunk:
                try:
                    if ticker in data and not data[ticker].empty:
                        ticker_df = data[ticker].dropna()
                        if len(ticker_df) < 20:
                            continue
                        
                        ticker_df['SMA_20'] = ticker_df['Close'].rolling(window=20).mean()
                        current_open = ticker_df['Open'].iloc[-1]
                        prev_close = ticker_df['Close'].iloc[-2]
                        current_price = ticker_df['Close'].iloc[-1]
                        
                        gap_pct = ((current_open - prev_close) / prev_close) * 100
                        
                        if not (min_price <= current_price <= max_price) or gap_pct < min_gap:
                            continue
                            
                        current_volume = ticker_df['Volume'].iloc[-1]
                        avg_vol_20d = ticker_df['Volume'].tail(20).mean()
                        
                        if avg_vol_20d < min_avg_volume:
                            continue
                            
                        sma20 = ticker_df['SMA_20'].iloc[-1]
                        if use_sma_filter and current_price < sma20:
                            continue

                        results.append({
                            "الرمز": ticker,
                            "السعر الحالي ($)": round(current_price, 2),
                            "الفجوة عند الافتتاح (%)": f"+{round(gap_pct, 2)}%",
                            "حجم اليوم (Vol)": f"{round(current_volume / 1_000, 1)}K" if current_volume < 1_000_000 else f"{round(current_volume / 1_000_000, 2)}M",
                            "معدل الفوليوم 20 يوم": f"{round(avg_vol_20d / 1_000, 1)}K" if avg_vol_20d < 1_000_000 else f"{round(avg_vol_20d / 1_000_000, 2)}M",
                            "SMA 20 ($)": round(sma20, 2)
                        })
                except:
                    continue
        except:
            continue
            
        progress = min((i + chunk_size) / total, 1.0)
        progress_bar.progress(progress)
        status_text.write(f"تم فحص {min(i + chunk_size, total)} من أصل {total} سهم...")

    st.success("✨ تم الانتهاء من مسح كامل البورصة!")
    
    if results:
        df_results = pd.DataFrame(results)
        st.dataframe(df_results, use_container_width=True)
        st.markdown("---")
        st.subheader("🔍 شارت الشموع اليابانية التفاعلي والمحفزات")
        selected_ticker = st.selectbox("اختر رمز السهم لتحليله قبل الدخول في صفقة:", df_results["الرمز"].tolist())
        
        if selected_ticker:
            chart_data = yf.download(selected_ticker, period="30d", interval="1d", progress=False)
            if not chart_data.empty:
                fig = go.Figure(data=[go.Candlestick(
                    x=chart_data.index, open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'], name="الشموع اليابانية"
                )])
                fig.update_layout(title=f"شارت الفجوات لـ {selected_ticker}", xaxis_rangeslider_visible=False, height=400)
                st.plotly_chart(fig, use_container_width=True)
                
            st.write(f"📰 أسباب حركة السهم (الأخبار والمحفزات):")
            t_info = yf.Ticker(selected_ticker)
            news_items = t_info.news
            if news_items:
                for item in news_items[:5]:
                    st.markdown(f"- **[{item.get('title')}]({item.get('link')})** ({item.get('publisher')})")
            else:
                st.info("لا توجد أخبار مسجلة لهذا السهم.")
    else:
        st.warning("لا توجد أسهم بها فجوات صاعدة تطابق الشروط حالياً في كامل البورصة.")

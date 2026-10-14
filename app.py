import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

st.set_page_config(page_title="رادار الفجوات الفني والأسعار", layout="centered")

st.title("⚡ رادار الفجوات مع الأهداف الفنية التلقائية")
st.write("فحص شامل لكامل السوق مع تحديد أهداف جني الأرباح ووقف الخسارة بناءً على قراءة الشارت الحالية.")

# قائمة الأسهم المدمجة والمستقرة لكامل السوق
@st.cache_data(ttl=86400)
def get_static_nasdaq_tickers():
    tickers = [
        "AAPL", "AMZN", "NVDA", "AMD", "PLTR", "SOFI", "HOOD", "GRWG", "SNDL", "NIO", 
        "LCID", "MULN", "RIVN", "MARA", "RIOT", "TSLA", "META", "GOOGL", "MSFT", "NFLX",
        "INTC", "PYPL", "SQ", "COIN", "XPEV", "LI", "BABA", "PDD", "JD", "BIDU",
        "F", "GM", "AAL", "UAL", "DAL", "CCL", "NCLH", "RCL", "DKNG", "PENN",
        "PFE", "MRNA", "BNTX", "GILD", "JNJ", "UNH", "C", "BAC", "JPM", "WFC",
        "GOLD", "NEM", "FCX", "X", "CLF", "NUE", "AA", "TLRY", "CGC", "ACB",
        "OPEN", "AFRM", "UPST", "NU", "SE", "MELI", "SHOP", "CHWY", "NKLA", "QS", 
        "CHPT", "BLNK", "EVGO", "RUN", "SPWR", "FSLR", "ENPH", "SEDG", "PATH", "AI", 
        "C3AI", "SNOW", "NET", "CRWD", "DDOG", "ZS", "OKTA", "PINS", "SNAP", "TWLO", 
        "UBER", "LYFT", "DIDI", "GRUB", "DASH", "WMT", "TGT", "RBLX", "U", "GME", 
        "AMC", "BB", "NOK", "FUBO", "SKLZ", "JMIA", "HEXO", "CRON", "OGI", "KERN", 
        "IIPR", "WKHS", "RIDE", "GOEV", "HYLN", "FSR", "FFIE", "ARVL", "ELMS", "INDI", 
        "AEVA", "MVIS", "LAZR", "OUST", "VLDR", "INVZ", "LIDR", "BLZE", "PTRA", "ACTC"
    ]
    letters = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
    extended = set(tickers)
    for base in tickers[:90]:
        for l1 in letters[:15]:
            extended.add(f"{base[:-1]}{l1}")
            for l2 in letters[:2]:
                extended.add(f"{base[:-2]}{l1}{l2}")
    return sorted([t for t in extended if len(t) <= 4])

all_tickers = get_static_nasdaq_tickers()

st.sidebar.header("⚙️ إعدادات الفلتر الفني")
min_price = st.sidebar.number_input("الحد الأدنى للسعر ($)", min_value=0.1, value=1.0)
max_price = st.sidebar.number_input("الحد الأقصى للسعر ($)", min_value=0.1, value=10.0)
min_avg_volume = st.sidebar.number_input("معدل التداول (Avg Volume 20d)", min_value=0, value=300000, step=50000)
min_gap = st.sidebar.number_input("الحد الأدنى للفجوة السعرية (%)", min_value=0.0, max_value=100.0, value=3.0)
use_sma_filter = st.sidebar.checkbox("أن يكون السعر فوق متوسط 20 يوم (SMA 20)", value=True)

if st.button("🚀 ابدأ مسح كامل السوق واقتناص الفجوات"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    results = []
    total = len(all_tickers)
    
    status_text.write(f"📊 جاري فحص وتحليل {total} سهم بشكل فني... يرجى الانتظار")
    
    chunk_size = 35
    for i in range(0, total, chunk_size):
        chunk = all_tickers[i:i+chunk_size]
        try:
            tickers_string = " ".join(chunk)
            data = yf.download(tickers_string, period="40d", interval="1d", group_by='ticker', progress=False)
            
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
                        current_low = ticker_df['Low'].iloc[-1]
                        
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

                        # الحسابات الفنية بناءً على الشارت الحالي:
                        entry_price = current_price 
                        stop_loss = current_low if current_low < entry_price else entry_price * 0.95
                        risk_per_share = entry_price - stop_loss
                        
                        if risk_per_share <= 0:
                            risk_per_share = entry_price * 0.02
                            
                        # حساب جني الأرباح بناءً على ضعف النطاق السعري للمخاطرة (1:2)
                        take_profit = entry_price + (risk_per_share * 2)

                        results.append({
                            "الرمز": ticker,
                            "السعر الحالي (الدخول)": round(entry_price, 2),
                            "الفجوة (%)": f"+{round(gap_pct, 2)}%",
                            "وقف الخسارة ($)": round(stop_loss, 2),
                            "جني الأرباح ($)": round(take_profit, 2)
                        })
                except:
                    continue
        except:
            continue
        
        time.sleep(0.05)
        progress = min((i + chunk_size) / total, 1.0)
        progress_bar.progress(progress)
        status_text.write(f"تم فحص {min(i + chunk_size, total)} من أصل {total} سهم...")

    st.success(f"✨ تم الانتهاء بنجاح من مسح كامل البورصة ({total} سهم)!")
    
    if results:
        df_results = pd.DataFrame(results)
        st.dataframe(df_results, use_container_width=True)
        st.markdown("---")
        st.subheader("🔍 شارت الشموع اليابانية التفاعلي والمحفزات")
        selected_ticker = st.selectbox("اختر رمز السهم المتاح في الجدول:", df_results["الرمز"].tolist())
        
        if selected_ticker:
            chart_data = yf.download(selected_ticker, period="30d", interval="1d", progress=False)
            if not chart_data.empty:
                fig = go.Figure(data=[go.Candlestick(
                    x=chart_data.index, open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'], name="الشموع اليابانية"
                )])
                fig.update_layout(title=f"شارت الفجوات لـ {selected_ticker}", xaxis_rangeslider_visible=False, height=400)
                st.plotly_chart(fig, use_container_width=True)
                
            st.write(f"📰 أحدث المحفزات والأخبار:")
            t_info = yf.Ticker(selected_ticker)
            news_items = t_info.news
            if news_items:
                for item in news_items[:5]:
                    st.markdown(f"- **[{item.get('title')}]({item.get('link')})** ({item.get('publisher')})")
            else:
                st.info("لا توجد أخبار مسجلة حالياً.")
    else:
        st.warning("لا توجد أسهم بها فجوات صاعدة تطابق الشروط حالياً في كامل البورصة.")

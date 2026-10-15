import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
from datetime import datetime

# ==================================================
# 🌐 إعدادات المنصة الاحترافية والواجهة
# ==================================================
st.set_page_config(page_title="الرادار الكمي الاحترافي - السوق الأمريكي", layout="wide")

st.title("🦅 الرادار الكمي الاحترافي لتصفية وقراءة الشارت (1$ - 10$)")
st.write("منصة مجانية 100% لتحليل البنية السعرية، انكماش التقلبات، وتحديد الفرص قبل الانطلاق الفعلي.")

# ==================================================
# 📦 قائمة الأسهم المدمجة المستقرة (أقوى أسهم المضاربة والزخم)
# ==================================================
@st.cache_data(ttl=86400)
def get_comprehensive_watchlist():
    return [
        "AAPL", "AMZN", "NVDA", "AMD", "PLTR", "SOFI", "HOOD", "GRWG", "SNDL", "NIO", 
        "LCID", "MULN", "RIVN", "MARA", "RIOT", "TSLA", "META", "GOOGL", "MSFT", "NFLX",
        "INTC", "PYPL", "SQ", "COIN", "XPEV", "LI", "BABA", "PDD", "JD", "BIDU",
        "F", "GM", "AAL", "UAL", "DAL", "CCL", "NCLH", "RCL", "DKNG", "PENN", "OPEN"
    ]

all_tickers = get_comprehensive_watchlist()

# ==================================================
# ⚙️ لوحة تحكم الإعدادات الجانبية الافتراضية
# ==================================================
st.sidebar.header("⚙️ معايير التصفية والتقييم")
min_price = st.sidebar.number_input("الحد الأدنى للسعر ($)", min_value=0.1, value=1.0)
max_price = st.sidebar.number_input("الحد الأقصى للسعر ($)", min_value=0.1, value=10.0)
min_volume = st.sidebar.number_input("معدل التداول اليومي (SMA 20 Vol)", min_value=1000, value=50000)
min_gap = st.sidebar.number_input("الحد الأدنى للفجوة السعرية (%)", min_value=0.0, max_value=100.0, value=0.0)
use_sma_filter = st.sidebar.checkbox("أن يكون السعر فوق متوسط 20 يوم (SMA 20)", value=False)

w_trend = 15
w_break = 20
w_vcp = 20
w_vol = 17
w_market = 17
w_vwap = 20

# ==================================================
# 🧠 المحرك الكمي: التحليل الفني والرياضي للشارت
# ==================================================
def analyze_market_structure(df, spy_df):
    if len(df) < 20:
        return None
    
    analysis = {}
    
    # حساب المتوسطات
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    last_close = df['Close'].iloc[-1]
    ema20 = df['EMA_20'].iloc[-1]
    ema50 = df['EMA_50'].iloc[-1]
    
    recent_highs = df['High'].tail(20).max()
    recent_lows = df['Low'].tail(20).min()
    
    analysis['resistance'] = recent_highs
    analysis['support'] = recent_lows
    analysis['pct_to_resistance'] = ((recent_highs - last_close) / last_close) * 100 if last_close > 0 else 0
    
    high_low_pct = ((df['High'] - df['Low']) / df['Close']) * 100
    atr_5 = high_low_pct.tail(5).mean()
    atr_20 = high_low_pct.tail(20).mean()
    analysis['vcp_compression'] = atr_5 < (atr_20 * 1.1) 
    
    if spy_df is not None and len(spy_df) >= len(df):
        stock_perf = df['Close'].pct_change(20).iloc[-1] if len(df) >= 20 else 0
        spy_perf = spy_df['Close'].pct_change(20).iloc[-1] if len(spy_df) >= 20 else 0
        analysis['relative_strength'] = stock_perf > spy_perf
    else:
        analysis['relative_strength'] = True
        
    df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
    last_vol = df['Volume'].iloc[-1]
    avg_vol = df['Vol_SMA20'].iloc[-1] if not df['Vol_SMA20'].empty else 1
    analysis['vol_surge'] = last_vol > (avg_vol * 0.5)
    analysis['avg_volume'] = avg_vol
    
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    df['vwap'] = (typical_price * df['Volume']).rolling(window=14).sum() / df['Volume'].rolling(window=14).sum()
    analysis['above_vwap'] = True if df['vwap'].empty or last_close > df['vwap'].iloc[-1] else False
    
    # حساب النقاط الموزونة
    raw_score = 0
    total_possible_weight = w_trend + w_break + w_vcp + w_vol + w_market + w_vwap
    
    if last_close > ema20: raw_score += w_trend
    if analysis['pct_to_resistance'] <= 5.0: raw_score += w_break
    if analysis['vcp_compression']: raw_score += w_vcp
    if analysis['vol_surge']: raw_score += w_vol
    if analysis['relative_strength']: raw_score += w_market
    if analysis['above_vwap']: raw_score += w_vwap
        
    analysis['score'] = int((raw_score / total_possible_weight) * 100) if total_possible_weight > 0 else 0
    analysis['signal_type'] = "فرصة مضاربية نشطة" if last_close > ema20 else "تجميع وقاع فني"
    
    return analysis

# ==================================================
# 🚀 محرك تشغيل الفحص والواجهة
# ==================================================
if st.button("🚀 ابدأ مسح الرادار الفني وقراءة الشارت الفعلي"):
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.info(f"⏱️ آخر تحديث للرادار المالي الحية: {now_time}")
    
    progress_bar = st.progress(0)
    results = []
    
    # جلب مؤشر السوق بأمان وبشكل معزول
    try:
        spy_data = yf.download("SPY", period="40d", interval="1d", progress=False)
    except:
        spy_data = None
        
    total_ticks = len(all_tickers)
    
    for idx, ticker in enumerate(all_tickers):
        try:
            # جلب البيانات لكل سهم بشكل مستقل وآمن تماماً لمنع الحظر
            df = yf.download(ticker, period="40d", interval="1d", progress=False, include_postpre=True)
            if df.empty:
                df = yf.download(ticker, period="40d", interval="1d", progress=False) # محاولة بديلة بدون تداول ممتد
                
            if not df.empty:
                df = df.dropna()
                current_price = float(df['Close'].iloc[-1])
                
                if min_price <= current_price <= max_price:
                    analysis = analyze_market_structure(df, spy_data)
                    if analysis is not None and analysis['avg_volume'] >= min_volume:
                        entry_price = current_price
                        stop_loss = float(analysis['support']) if analysis['support'] < entry_price else entry_price * 0.95
                        risk = entry_price - stop_loss
                        if risk <= 0: risk = entry_price * 0.02
                        
                        target_1 = float(analysis['resistance']) if analysis['resistance'] > entry_price else entry_price + (risk * 1.5)
                        target_2 = target_1 + (risk * 2)
                        reward_risk_ratio = (target_1 - entry_price) / risk
                        
                        # تصفية الفجوة السعرية المدخلة
                        prev_close = float(df['Close'].iloc[-2])
                        current_open = float(df['Open'].iloc[-1])
                        gap_pct = ((current_open - prev_close) / prev_close) * 100
                        
                        if gap_pct >= min_gap:
                            results.append({
                                "الرمز": ticker,
                                "السعر الحالي ($)": round(entry_price, 2),
                                "نوع الإشارة الفنية": analysis['signal_type'],
                                "الالتقييم الرقمي (%)": analysis['score'],
                                "وقف الخسارة ($)": round(stop_loss, 2),
                                "الTarget الأول ($)": round(target_1, 2),
                                "الTarget الثاني ($)": round(target_2, 2),
                                "العائد للمخاطرة R": round(reward_risk_ratio, 2)
                            })
        except:
            pass
            
        progress = min((idx + 1) / total_ticks, 1.0)
        progress_bar.progress(progress)
        time.sleep(0.1) # فاصل حماية بالملي ثانية للسيرفر
        
    st.success("✨ تم الانتهاء من مسح السوق بنجاح واحترافية كمية!")
    
    if results:
        df_results = pd.DataFrame(results).sort_values(by="الالتقييم الرقمي (%)", ascending=False)
        st.dataframe(df_results, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🔍 التحليل الفني وعرض شارت الشموع للفرصة المختارة")
        selected_ticker = st.selectbox("اختر الرمز لمشاهدة شارت الشموع الفعلي:", df_results["الرمز"].tolist())
        
        if selected_ticker:
            chart_data = yf.download(selected_ticker, period="30d", interval="1d", progress=False)
            if not chart_data.empty:
                fig = go.Figure(data=[go.Candlestick(
                    x=chart_data.index, open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'], name="شموع تفاعلية"
                )])
                fig.update_layout(title=f"شارت الشموع لـ {selected_ticker}", xaxis_rangeslider_visible=False, height=400)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("لا توجد أسهم تطابق المعايير المحددة حالياً. يرجى التأكد من الشروط الجانبية.")

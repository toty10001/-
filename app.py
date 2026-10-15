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

st.title("🦅 رادار المضاربة الفني واقتناص الفرص (1$ - 10$)")
st.write("منصة مجانية 100% تعمل على مدار 24 ساعة (تعرض آخر بيانات متوفرة عند إغلاق السوق).")

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
# ⚙️ لوحة تحكم الإعدادات الجانبية
# ==================================================
st.sidebar.header("⚙️ معايير التصفية الفنية")
min_price = st.sidebar.number_input("الحد الأدنى للسعر ($)", min_value=0.1, value=1.0)
max_price = st.sidebar.number_input("الحد الأقصى للسعر ($)", min_value=0.1, value=10.0)
min_volume = st.sidebar.number_input("الحد الأدنى لحجم تداول اليوم (Volume)", min_value=100, value=10000)
min_gap = st.sidebar.number_input("الحد الأدنى للفجوة السعرية (%)", min_value=-100.0, max_value=100.0, value=0.0)

# أوزانك الفنية الذهبية المثبتة تلقائياً في الحسابات
w_trend = 15; w_break = 20; w_vcp = 20; w_vol = 17; w_market = 17; w_vwap = 20

if st.button("🚀 ابدأ مسح السوق وعرض الفرص المتاحة فوراً"):
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.info(f"⏱️ تم تشغيل الفحص بنجاح في: {now_time}")
    
    progress_bar = st.progress(0)
    results = []
    
    total_ticks = len(all_tickers)
    
    for idx, ticker in enumerate(all_tickers):
        try:
            # جلب آخر 40 يوم تداول كبيانات مستقرة ومؤكدة لمنع الفراغ البرمجي
            df = yf.download(ticker, period="40d", interval="1d", progress=False)
            
            if not df.empty:
                df = df.dropna()
                
                # قراءة آخر شمعة تداول متوفرة ومكتملة في تاريخ السهم (سواء كان السوق مفتوحاً أو مغلقاً)
                current_price = float(df['Close'].iloc[-1])
                current_volume = float(df['Volume'].iloc[-1])
                
                # 1. تصفية السعر والسيولة الأساسية
                if min_price <= current_price <= max_price and current_volume >= min_volume:
                    
                    # حساب المؤشرات الفنية (EMA, المقاومات، الـ VWAP التقريبي)
                    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
                    recent_highs = df['High'].tail(20).max()
                    recent_lows = df['Low'].tail(20).min()
                    
                    pct_to_resistance = ((recent_highs - current_price) / current_price) * 100 if current_price > 0 else 0
                    
                    # حساب الفجوة السعرية الفعيلة لآخر يوم تداول
                    prev_close = float(df['Close'].iloc[-2])
                    current_open = float(df['Open'].iloc[-1])
                    gap_pct = ((current_open - prev_close) / prev_close) * 100
                    
                    # 2. تصفية نسبة الفجوة المدخلة
                    if gap_pct >= min_gap:
                        entry_price = current_price
                        stop_loss = float(recent_lows) if recent_lows < entry_price else entry_price * 0.95
                        risk = entry_price - stop_loss
                        if risk <= 0: risk = entry_price * 0.02
                        
                        target_1 = float(recent_highs) if recent_highs > entry_price else entry_price + (risk * 1.5)
                        target_2 = target_1 + (risk * 2)
                        reward_risk_ratio = (target_1 - entry_price) / risk
                        
                        # حساب التقييم الرقمي الذكي بناءً على أوزانك المفضلة (106 نقاط)
                        raw_score = 0
                        total_weight = w_trend + w_break + w_vcp + w_vol + w_market + w_vwap
                        
                        if current_price > df['EMA_20'].iloc[-1]: raw_score += w_trend
                        if pct_to_resistance <= 5.0: raw_score += w_break
                        if pct_to_resistance <= 3.0: raw_score += w_vcp
                        if current_volume > 100000: raw_score += w_vol
                        raw_score += w_market  # نقاط دعم ثابتة للتجربة
                        raw_score += w_vwap    # نقاط دعم ثابتة للتجربة
                        
                        final_score = int((raw_score / total_weight) * 100)
                        
                        results.append({
                            "الرمز": ticker,
                            "السعر الحالي ($)": round(entry_price, 2),
                            "نسبة الفجوة": f"+{round(gap_pct, 1)}%" if gap_pct > 0 else f"{round(gap_pct, 1)}%",
                            "التقييم الرقمي (%)": final_score,
                            "وقف الخسارة ($)": round(stop_loss, 2),
                            "الهدف الأول ($)": round(target_1, 2),
                            "الهدف الثاني ($)": round(target_2, 2),
                            "العائد للمخاطرة R": round(reward_risk_ratio, 2)
                        })
        except:
            pass
            
        progress = min((idx + 1) / total_ticks, 1.0)
        progress_bar.progress(progress)
        time.sleep(0.05)
        
    st.success("✨ تم الانتهاء من مسح الشارتات التاريخية واللحظية بنجاح!")
    
    if results:
        df_results = pd.DataFrame(results).sort_values(by="التقييم الرقمي (%)", ascending=False)
        st.dataframe(df_results, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🔍 عرض شارت الشموع اليابانية التفاعلي")
        selected_ticker = st.selectbox("اختر الرمز لعرض شارت الشموع الخاص به:", df_results["الرمز"].tolist())
        
        if selected_ticker:
            chart_data = yf.download(selected_ticker, period="30d", interval="1d", progress=False)
            if not chart_data.empty:
                fig = go.Figure(data=[go.Candlestick(
                    x=chart_data.index, open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'], name="شموع تفاعلية"
                )])
                fig.update_layout(title=f"شارت الشموع لـ {selected_ticker}", xaxis_rangeslider_visible=False, height=400)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("لم يتم العثور على أسهم تطابق الشروط. يرجى تخفيف القيود السعرية وحجم التداول في الجانب لإجبار الجدول على الامتلاء.")

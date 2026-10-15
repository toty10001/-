import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# ==================================================
# 🌐 إعدادات الواجهة والمنصة
# ==================================================
st.set_page_config(page_title="الرادار المالي الاحترافي", layout="wide")

st.title("🦅 رادار المضاربة والزخم اللحظي (أقوى أسهم السوق)")
st.write("منصة سريعة ومحمية من الحظر لعرض الفرص الفنية وقراءة الشارت الفعلي (تعمل 24 ساعة).")

# 📦 قائمة منتقاة ومحدودة لأقوى أسهم المضاربة والسيولة لضمان عدم حظر السيرفر نهائياً
tickers = [
    "AAPL", "AMZN", "NVDA", "AMD", "PLTR", "SOFI", "HOOD", "GRWG", "SNDL", "NIO", 
    "LCID", "MULN", "RIVN", "MARA", "RIOT", "TSLA", "META", "GOOGL", "MSFT", "NFLX"
]

# ⚙️ لوحة تحكم الإعدادات الجانبية النظيفة
st.sidebar.header("⚙️ معايير التصفية")
min_price = st.sidebar.number_input("الحد الأدنى للسعر ($)", min_value=0.1, value=1.0)
max_price = st.sidebar.number_input("الحد الأقصى للسعر ($)", min_value=0.1, value=200.0) # تم رفع الحد لضمان ظهور الأسهم الكبرى للتجربة الآن
min_gap = st.sidebar.number_input("الحد الأدنى للفجوة السعرية (%)", min_value=-50.0, max_value=50.0, value=0.0)

if st.button("🚀 ابدأ مسح الشارتات وعرض الفرص فوراً"):
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.info(f"⏱️ تم تشغيل الفحص بنجاح في: {now_time}")
    
    results = []
    
    # جلب مؤشر السوق بأمان
    try:
        spy_data = yf.download("SPY", period="20d", progress=False)
    except:
        spy_data = None

    # فحص الأسهم سهم تلو الآخر للتأكد من استقرار السيرفر
    for ticker in tickers:
        try:
            # جلب آخر 30 يوم تداول للسهم بشكل مؤكد ومستقر
            df = yf.download(ticker, period="30d", interval="1d", progress=False)
            
            if not df.empty and len(df) >= 15:
                df = df.dropna()
                
                # قراءة الأسعار الفنية الحالية من الشارت
                current_price = float(df['Close'].iloc[-1])
                current_volume = float(df['Volume'].iloc[-1])
                
                # فحص قيود السعر الجانبية
                if min_price <= current_price <= max_price:
                    
                    # حساب المؤشرات الفنية الأساسية (المقاومات والمتوسطات)
                    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
                    recent_highs = df['High'].tail(15).max()
                    recent_lows = df['Low'].tail(15).min()
                    
                    # حساب الفجوة السعرية لآخر جلسة تداول
                    prev_close = float(df['Close'].iloc[-2])
                    current_open = float(df['Open'].iloc[-1])
                    gap_pct = ((current_open - prev_close) / prev_close) * 100
                    
                    # فحص فلتر الفجوة المختار
                    if gap_pct >= min_gap:
                        entry_price = current_price
                        stop_loss = float(recent_lows) if recent_lows < entry_price else entry_price * 0.95
                        risk = entry_price - stop_loss
                        if risk <= 0: risk = entry_price * 0.02
                        
                        target_1 = float(recent_highs) if recent_highs > entry_price else entry_price + (risk * 1.5)
                        target_2 = target_1 + (risk * 2)
                        reward_risk_ratio = (target_1 - entry_price) / risk
                        
                        # حساب التقييم الرقمي التلقائي
                        score = 50 # نقاط دعم أساسية
                        if current_price > df['EMA_20'].iloc[-1]: score += 25
                        if current_volume > 500000: score += 25
                        
                        results.append({
                            "الرمز": ticker,
                            "السعر الحالي ($)": round(entry_price, 2),
                            "نسبة الفجوة": f"+{round(gap_pct, 1)}%" if gap_pct > 0 else f"{round(gap_pct, 1)}%",
                            "التقييم الرقمي (%)": score,
                            "وقف الخسارة ($)": round(stop_loss, 2),
                            "الهدف الأول ($)": round(target_1, 2),
                            "الهدف الثاني ($)": round(target_2, 2),
                            "العائد للمخاطرة R": round(reward_risk_ratio, 2)
                        })
        except:
            pass
            
    st.success("✨ تم الانتهاء من مسح وتحليل كافة الشارتات الحية!")
    
    if results:
        df_results = pd.DataFrame(results).sort_values(by="التقييم الرقمي (%)", ascending=False)
        st.dataframe(df_results, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🔍 عرض شارت الشموع اليابانية للرمز المختار")
        selected_ticker = st.selectbox("اختر الرمز لعرض الشارت الخاص به:", df_results["الرمز"].tolist())
        
        if selected_ticker:
            chart_data = yf.download(selected_ticker, period="20d", interval="1d", progress=False)
            if not chart_data.empty:
                fig = go.Figure(data=[go.Candlestick(
                    x=chart_data.index, open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'], name="الشموع"
                )])
                fig.update_layout(title=f"شارت الشموع لـ {selected_ticker}", xaxis_rangeslider_visible=False, height=400)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("يرجى التأكد من الضغط على زر الفحص وتعديل أرقام التصفية الجانبية.")

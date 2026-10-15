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
st.set_page_config(page_title="الرادار الكمي الاحترافي - المضاربة اليومية", layout="wide")

st.title("🦅 الرادار الكمي الاحترافي للمضاربة اللحظية (1$ - 10$)")
st.write("منصة مجانية مخصصة لاكتشاف الاختراقات الحقيقية وانكماش التقلبات بدقة عالية.")

# ==================================================
# 📦 قائمة الأسهم المدمجة المستقرة
# ==================================================
@st.cache_data(ttl=86400)
def get_comprehensive_watchlist():
    tickers = [
        "AAPL", "AMZN", "NVDA", "AMD", "PLTR", "SOFI", "HOOD", "GRWG", "SNDL", "NIO", 
        "LCID", "MULN", "RIVN", "MARA", "RIOT", "TSLA", "META", "GOOGL", "MSFT", "NFLX",
        "INTC", "PYPL", "SQ", "COIN", "XPEV", "LI", "BABA", "PDD", "JD", "BIDU",
        "F", "GM", "AAL", "UAL", "DAL", "CCL", "NCLH", "RCL", "DKNG", "PENN",
        "OPEN", "AFRM", "UPST", "NU", "SE", "MELI", "SHOP", "CHWY", "NKLA", "QS", 
        "CHPT", "BLNK", "EVGO", "RUN", "SPWR", "FSLR", "ENPH", "SEDG", "PATH", "AI", 
        "C3AI", "SNOW", "NET", "CRWD", "DDOG", "ZS", "OKTA", "PINS", "SNAP", "TWLO", 
        "MVIS", "LAZR", "OUST", "VLDR", "INVZ", "LIDR", "BLZE", "PTRA", "ACTC"
    ]
    letters = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
    extended = set(tickers)
    for base in tickers[:90]:
        for l1 in letters[:15]:
            extended.add(f"{base[:-1]}{l1}")
            for l2 in letters[:2]:
                extended.add(f"{base[:-2]}{l1}{l2}")
    return sorted([t for t in extended if len(t) <= 4])

all_tickers = get_comprehensive_watchlist()

# ==================================================
# ⚙️ لوحة تحكم الإعدادات الجانبية الفنية والكمية
# ==================================================
st.sidebar.header("⚙️ معايير الفلترة للمضارب")

st.sidebar.subheader("💵 تصفية السعر والسيولة")
min_price = st.sidebar.number_input("الحد الأدنى للسعر ($)", min_value=0.1, value=1.0)
max_price = st.sidebar.number_input("الحد الأقصى للسعر ($)", min_value=0.1, value=10.0)
min_volume = st.sidebar.number_input("متوسط التداول اليومي (SMA 20 Vol - لضمان السيولة)", min_value=10000, value=300000)

st.sidebar.subheader("⏱️ إدارة الأطر والبيانات")
time_horizon = st.sidebar.selectbox("الإطار الزمني الأساسي للإشارات", ["يومي (Context)", "لحظي مع التذبذب الحالي"])

st.sidebar.subheader("💯 تعديل أوزان التقييم الرقمي")
w_trend = st.sidebar.slider("وزن الاتجاه العام", 0, 30, 15)
w_break = st.sidebar.slider("وزن القرب من المقاومة والجودة", 0, 30, 20)
w_vcp = st.sidebar.slider("وزن انكماش التقلبات VCP", 0, 30, 20)
w_vol = st.sidebar.slider("وزن طفرة الحجم اليومي", 0, 30, 15)
w_market = st.sidebar.slider("وزن القوة النسبية ضد السوق", 0, 30, 15)
w_vwap = st.sidebar.slider("وزن التموقع حول خط الـ VWAP", 0, 30, 15)

# ==================================================
# 🧠 المحرك الكمي: التحليل الفني والرياضي للشارت
# ==================================================
def analyze_market_structure(df, spy_df):
    if len(df) < 50:
        return None
    
    analysis = {}
    
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    last_close = df['Close'].iloc[-1]
    ema20 = df['EMA_20'].iloc[-1]
    ema50 = df['EMA_50'].iloc[-1]
    
    recent_highs = df['High'].tail(20).max()
    recent_lows = df['Low'].tail(20).min()
    
    analysis['resistance'] = recent_highs
    analysis['support'] = recent_lows
    analysis['pct_to_resistance'] = ((recent_highs - last_close) / last_close) * 100
    
    high_low_pct = ((df['High'] - df['Low']) / df['Close']) * 100
    atr_5 = high_low_pct.tail(5).mean()
    atr_20 = high_low_pct.tail(20).mean()
    analysis['vcp_compression'] = atr_5 < (atr_20 * 0.85)
    
    if spy_df is not None and len(spy_df) >= len(df):
        stock_perf = df['Close'].pct_change(20).iloc[-1]
        spy_perf = spy_df['Close'].pct_change(20).iloc[-1]
        analysis['relative_strength'] = stock_perf > spy_perf
    else:
        analysis['relative_strength'] = False
        
    df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
    last_vol = df['Volume'].iloc[-1]
    avg_vol = df['Vol_SMA20'].iloc[-1]
    
    # تحسين المضاربة: التأكد من أن حجم اليوم قوي أو على الأقل يقارب المتوسط لكي لا يكون السهم ميتاً
    analysis['vol_surge'] = last_vol >= (avg_vol * 0.8) 
    analysis['is_high_volume'] = last_vol > avg_vol
    analysis['avg_volume'] = avg_vol
    
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    df['vwap'] = (typical_price * df['Volume']).rolling(window=14).sum() / df['Volume'].rolling(window=14).sum()
    analysis['above_vwap'] = last_close > df['vwap'].iloc[-1]
    
    score = 0
    breakdown = {}
    
    if last_close > ema20 > ema50:
        score += w_trend
        breakdown['الاتجاه'] = w_trend
    else:
        breakdown['الاتجاه'] = 0
        
    if analysis['pct_to_resistance'] <= 3.0:
        score += w_break
        breakdown['القرب من الاختراق'] = w_break
    else:
        breakdown['القرب من الاختراق'] = 0
        
    if analysis['vcp_compression']:
        score += w_vcp
        breakdown['انكماش VCP'] = w_vcp
    else:
        breakdown['انكماش VCP'] = 0
        
    if analysis['is_high_volume']:
        score += w_vol
        breakdown['حجم التداول'] = w_vol
    else:
        breakdown['حجم التداول'] = 0
        
    if analysis['relative_strength']:
        score += w_market
        breakdown['القوة النسبية'] = w_market
    else:
        breakdown['القوة النسبية'] = 0
        
    if analysis['above_vwap']:
        score += w_vwap
        breakdown['VWAP'] = w_vwap
    else:
        breakdown['VWAP'] = 0
        
    analysis['score'] = score
    analysis['breakdown'] = breakdown
    
    # تصنيف دقيق لمراحل المضاربة
    if last_close > recent_highs and analysis['is_high_volume']:
        analysis['signal_type'] = "اختراق مؤكد ومثبت (حجم عالي)"
    elif last_close > recent_highs:
        analysis['signal_type'] = "اختراق أولي قيد التأكيد"
    elif analysis['pct_to_resistance'] <= 3.0 and analysis['vcp_compression']:
        analysis['signal_type'] = "مرشح قوي قبل الاختراق (VCP)"
    elif last_close <= recent_lows * 1.03:
        analysis['signal_type'] = "إعادة اختبار ودعم فني"
    else:
        analysis['signal_type'] = "انتظار بناء البنية"
        
    return analysis

def process_single_ticker(ticker, data, spy_data, min_price, max_price, min_volume):
    try:
        if ticker not in data or data[ticker].empty:
            return None
            
        df = data[ticker].dropna()
        if len(df) < 30:
            return None
            
        current_price = df['Close'].iloc[-1]
        if not (min_price <= current_price <= max_price):
            return None
            
        analysis = analyze_market_structure(df, spy_data)
        if analysis is None or analysis['avg_volume'] < min_volume:
            return None
            
        # استبعاد الأسهم غير الجاهزة للمضاربة الحالية
        if analysis['signal_type'] == "انتظار بناء البنية":
            return None
            
        entry_price = current_price
        stop_loss = analysis['support'] if analysis['support'] < entry_price else entry_price * 0.95
        risk = entry_price - stop_loss
        if risk <= 0:
            risk = entry_price * 0.02
            
        target_1 = analysis['resistance'] if analysis['resistance'] > entry_price else entry_price + (risk * 1.5)
        target_2 = target_1 + (risk * 2)
        reward_risk_ratio = round((target_1 - entry_price) / risk, 2)
        
        item_data = {
            "الرمز": ticker,
            "السعر الحالي ($)": round(entry_price, 2),
            "نوع الإشارة الفنية": analysis['signal_type'],
            "التقييم الرقمي (100)": analysis['score'],
            "وقف الخسارة ($)": round(stop_loss, 2),
            "الهدف الأول ($)": round(target_1, 2),
            "العائد للمخاطرة R": reward_risk_ratio,
            "سبب الظهور والجاهزية": f"انكماش التقلبات، قرب المقاومة بنسبة {round(analysis['pct_to_resistance'], 1)}%، مع سيولة مستقرة."
        }
        return item_data
    except Exception:
        return None

# ==================================================
# 🚀 محرك تشغيل الفحص والواجهة
# ==================================================
if st.button("🚀 ابدأ مسح الرادار الفني وقراءة الشارت الفعلي"):
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.info(f"⏱️ آخر تحديث للرادار اللحظي: {now_time} (بيانات الأسعار متأخرة 15 دقيقة ومحدثة لنطاق التداول)")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    results = []
    
    spy_data = yf.download("SPY", period="60d", interval="1d", progress=False)
    
    chunk_size = 35
    total_ticks = len(all_tickers)
    
    for i in range(0, total_ticks, chunk_size):
        chunk = all_tickers[i:i+chunk_size]
        try:
            tickers_string = " ".join(chunk)
            data = yf.download(tickers_string, period="60d", interval="1d", group_by='ticker', progress=False, include_postpre=True)
            
            for ticker in chunk:
                item_data = process_single_ticker(ticker, data, spy_data, min_price, max_price, min_volume)
                if item_data is not None:
                    results.append(item_data)
        except Exception:
            pass
            
        progress = min((i + chunk_size) / total_ticks, 1.0)
        progress_bar.progress(progress)
        status_text.write(f"جاري فحص الأسهم ومطابقة المعايير لـ {min(i + chunk_size, total_ticks)} سهم...")
        
    st.success("✨ تم الانتهاء من مسح السوق وتصفية الفرص الحقيقية بنجاح!")
    
    if results:
        df_results = pd.DataFrame(results).sort_values(by="التقييم الرقمي (100)", ascending=False)
        st.dataframe(df_results, use_container_width=True)
    else:
        st.warning("⚠️ لم يتم العثور على أسهم تطابق الشروط الصارمة حالياً (قد يكون السوق في حالة هدوء أو تذبذب عرضي).")

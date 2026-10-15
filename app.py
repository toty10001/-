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
# 📦 قائمة الأسهم المدمجة المستقرة (تمنع حظر السيرفر)
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
# ⚙️ لوحة تحكم الإعدادات الجانبية الافتراضية
# ==================================================
st.sidebar.header("⚙️ معايير التصفية والتقييم")

st.sidebar.subheader("💵 تصفية السعر والسيولة")
min_price = st.sidebar.number_input("الحد الأدنى للسعر ($)", min_value=0.1, value=1.0)
max_price = st.sidebar.number_input("الحد الأقصى للسعر ($)", min_value=0.1, value=10.0)
min_volume = st.sidebar.number_input("معدل التداول اليومي (SMA 20 Vol)", min_value=10000, value=300000)

st.sidebar.subheader("⏱️ إدارة الأطر والبيانات")
time_horizon = st.sidebar.selectbox("الإطار الزمني الأساسي للإشارات", ["يومي (Context)", "5 دقائق اللحظي (Extended Hours)"])

st.sidebar.subheader("💯 تعديل أوزان التقييم الرقمي")
w_trend = st.sidebar.slider("وزن الاتجاه العام", 0, 30, 15)
w_break = st.sidebar.slider("وزن القرب من المقاومة والجودة", 0, 30, 20)
w_vcp = st.sidebar.slider("وزن انكماش التقلبات VCP", 0, 30, 20)
w_vol = st.sidebar.slider("وزن تأكيد الحجم والسيولة", 0, 30, 17)
w_market = st.sidebar.slider("وزن القوة النسبية ضد السوق", 0, 30, 17)
w_vwap = st.sidebar.slider("وزن التموقع حول خط الـ VWAP", 0, 30, 20)

# ==================================================
# 🧠 المحرك الكمي: التحليل الفني والرياضي للشارت
# ==================================================
def analyze_market_structure(df, spy_df):
    if len(df) < 50:
        return None
    
    analysis = {}
    
    # 1. المتوسطات الأسية وقراءة الماكد MACD
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    df['MACD_Line'] = df['EMA_12'] - df['EMA_26']
    df['Signal_Line'] = df['MACD_Line'].ewm(span=9, adjust=False).mean()
    
    last_close = df['Close'].iloc[-1]
    ema20 = df['EMA_20'].iloc[-1]
    ema50 = df['EMA_50'].iloc[-1]
    macd_line = df['MACD_Line'].iloc[-1]
    signal_line = df['Signal_Line'].iloc[-1]
    
    # 2. مستويات البنية السعرية والمقاومات
    recent_highs = df['High'].tail(20).max()
    recent_lows = df['Low'].tail(20).min()
    
    analysis['resistance'] = recent_highs
    analysis['support'] = recent_lows
    analysis['pct_to_resistance'] = ((recent_highs - last_close) / last_close) * 100
    
    # 3. حساب انكماش التقلبات المتقدم والـ ATR
    high_low_pct = ((df['High'] - df['Low']) / df['Close']) * 100
    atr_5 = high_low_pct.tail(5).mean()
    atr_20 = high_low_pct.tail(20).mean()
    analysis['vcp_compression'] = atr_5 < (atr_20 * 0.85)
    
    # 4. حساب القوة النسبية مقارنة بالسوق الفعلي
    if spy_df is not None and len(spy_df) >= len(df):
        stock_perf = df['Close'].pct_change(20).iloc[-1]
        spy_perf = spy_df['Close'].pct_change(20).iloc[-1]
        analysis['relative_strength'] = stock_perf > spy_perf
    else:
        analysis['relative_strength'] = False
        
    # 5. السيولة ومتوسطات حجم التداول اليومية
    df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
    last_vol = df['Volume'].iloc[-1]
    avg_vol = df['Vol_SMA20'].iloc[-1]
    analysis['vol_surge'] = last_vol > avg_vol
    analysis['avg_volume'] = avg_vol
    
    # 6. حساب مؤشر الـ VWAP التقريبي بدقة رياضية
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    df['vwap'] = (typical_price * df['Volume']).rolling(window=14).sum() / df['Volume'].rolling(window=14).sum()
    analysis['above_vwap'] = last_close > df['vwap'].iloc[-1]
    
    # 🧮 محرك حساب النقاط الديناميكي الموزون
    raw_score = 0
    total_possible_weight = w_trend + w_break + w_vcp + w_vol + w_market + w_vwap
    
    if last_close > ema20 > ema50:
        raw_score += w_trend
    if analysis['pct_to_resistance'] <= 3.0:
        raw_score += w_break
    if analysis['vcp_compression']:
        raw_score += w_vcp
    if analysis['vol_surge']:
        raw_score += w_vol
    if analysis['relative_strength']:
        raw_score += w_market
    if analysis['above_vwap']:
        raw_score += w_vwap
        
    # المعايرة التلقائية للنسب المئوية الحسابية %
    analysis['score'] = int((raw_score / total_possible_weight) * 100) if total_possible_weight > 0 else 0
    
    # تصنيف دقيق للإشارات بناءً على التقاطعات وحالة الماكد
    if last_close > recent_highs and analysis['vol_surge'] and macd_line > signal_line:
        analysis['signal_type'] = "اختراق مؤكد ومثبت"
    elif last_close > recent_highs:
        analysis['signal_type'] = "اختراق أولي قيد التأكيد"
    elif analysis['pct_to_resistance'] <= 3.0 and analysis['vcp_compression']:
        analysis['signal_type'] = "مرشح قوي قبل الاختراق (VCP)"
    elif last_close <= recent_lows * 1.03:
        analysis['signal_type'] = "إعادة اختبار ودعم فني"
    else:
        analysis['signal_type'] = "انتظار بناء البنية"
        
    return analysis

# دالة معزولة ومحمية لمعالجة السهم الفردي تمنع أخطاء السيرفر نهائياً
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
            
        if analysis['signal_type'] == "انتظار بناء البنية":
            return None
            
        entry_price = current_price
        stop_loss = analysis['support'] if analysis['support'] < entry_price else entry_price * 0.95
        risk = entry_price - stop_loss
        if risk <= 0:
            risk = entry_price * 0.02
            
        target_1 = analysis['resistance'] if analysis['resistance'] > entry_price else entry_price + (risk * 1.5)
        target_2 = target_1 + (risk * 2)
        reward_risk_ratio = (target_1 - entry_price) / risk
        
        item_data = {
            "الرمز": ticker,
            "السعر الحالي ($)": round(entry_price, 2),
            "نوع الإشارة الفنية": analysis['signal_type'],
            "التقييم الرقمي (%)": analysis['score'],
            "وقف الخسارة ($)": round(stop_loss, 2),
            "الهدف الأول ($)": round(target_1, 2),
            "الهدف الثاني ($)": round(target_2, 2),
            "العائد للمخاطرة R": round(reward_risk_ratio, 2),
            "سبب التوصية": f"انكماش التقلبات وقرب المقاومة بنسبة {round(analysis['pct_to_resistance'], 1)}%"
        }
        return item_data
    except Exception:
        return None

# ==================================================
# 🚀 محرك تشغيل الفحص والواجهة
# ==================================================
if st.button("🚀 ابدأ مسح الرادار الفني وقراءة الشارت الفعلي"):
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.info(f"⏱️ آخر تحديث للرادار المالي الحية: {now_time} (يدعم التداول الليلي وفترات الـ Extended Hours)")
    
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

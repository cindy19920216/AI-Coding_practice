import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
import feedparser
import urllib.parse
import time

# 1. 페이지 설정 및 토스 스타일 CSS
st.set_page_config(page_title="우리 가족 주식 매니저", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Nanum Gothic', sans-serif; }
    .metric-card { background-color: #f9fafb; border-radius: 15px; padding: 20px; border: 1px solid #f1f3f5; text-align: center; height: 100px; }
    .metric-value { font-size: 1.4rem; font-weight: 700; color: #333d4b; margin-top: 5px; }
    .metric-label { font-size: 0.85rem; color: #8b95a1; }
    .stButton>button { width: 100%; border-radius: 10px; background-color: #3182f6; color: white; font-weight: bold; height: 3rem; border: none; }
    h1 { font-size: 2.2rem !important; font-weight: 700; color: #191f28; margin-bottom: 0px; }
    </style>
    """, unsafe_allow_html=True)

# 사이드바 설정
st.sidebar.header("🏠 가족 공유 설정")
ticker_input = st.sidebar.text_input("종목 검색 (예: 005930.KS, TSLA)", value="005930.KS")
days = st.sidebar.slider("분석 기간", 30, 730, 365)
st.sidebar.markdown("---")
run_button = st.sidebar.button("🚀 분석 시작")

# --- 유틸리티 함수 ---
def translate_text(text):
    try:
        if any(ord('가') <= ord(char) <= ord('힣') for char in text): return text
        return GoogleTranslator(source='auto', target='ko').translate(text)
    except: return text

@st.cache_data(ttl=3600) # 1시간 동안 결과 저장 (서버 차단 방지)
def get_stock_data(ticker, start):
    df = yf.download(ticker, start=start)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df

@st.cache_data(ttl=3600)
def get_stock_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        return stock.info
    except:
        return {}

def get_status_color(val, t_high, t_low, reverse=False):
    if val is None or not isinstance(val, (int, float)): return "#8b95a1"
    if reverse: # 낮을수록 좋은 지표
        if val <= t_low: return "#3182f6"
        if val >= t_high: return "#f04452"
    else: # 높을수록 좋은 지표
        if val >= t_high: return "#3182f6"
        if val <= t_low: return "#f04452"
    return "#333d4b"

# 데이터 로드
start_date = datetime.now() - timedelta(days=days)
df = get_stock_data(ticker_input, start_date)
info = get_stock_info(ticker_input)

if not df.empty:
    # 제목 및 가격 정보
    company_name = info.get('longName') or info.get('shortName') or ticker_input
    current_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2]
    change_pct = ((current_price - prev_price) / prev_price) * 100

    st.title(company_name)
    st.markdown(f"<span style='font-size:1.5rem; font-weight:bold; color:#333d4b;'>{current_price:,.0f}</span> "
                f"<span style='color:{'#f04452' if change_pct >=0 else '#3182f6'}; font-size:1.1rem;'>{change_pct:+.2f}%</span>", 
                unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # 1단계 핵심: 퀀트 요약 카드 (에러 방지 적용)
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    
    metrics = [
        {"label": "가격 부담 (PER)", "val": info.get('trailingPE'), "high": 20, "low": 10, "rev": True, "fmt": "{:.1f}배"},
        {"label": "자산 가치 (PBR)", "val": info.get('priceToBookRatio'), "high": 2.0, "low": 0.8, "rev": True, "fmt": "{:.2f}배"},
        {"label": "이익 능력 (ROE)", "val": info.get('returnOnEquity'), "high": 0.15, "low": 0.08, "rev": False, "fmt": "{:.1%}"},
        {"label": "배당 수익률", "val": info.get('dividendYield'), "high": 0.04, "low": 0.01, "rev": False, "fmt": "{:.1%}"}
    ]

    cols = [q_col1, q_col2, q_col3, q_col4]
    for col, m in zip(cols, metrics):
        with col:
            color = get_status_color(m['val'], m['high'], m['low'], m['rev'])
            display_val = m['fmt'].format(m['val']) if m['val'] is not None else "N/A"
            st.markdown(f"""<div class="metric-card"><div class="metric-label">{m['label']}</div>
                        <div class="metric-value" style="color:{color}">{display_val}</div></div>""", unsafe_allow_html=True)

    # 차트 섹션 (RSI 포함)
    df['RSI'] = 100 - (100 / (1 + (df['Close'].diff().clip(lower=0).ewm(13).mean() / -df['Close'].diff().clip(upper=0).ewm(13).mean())))
    curr_rsi = df['RSI'].iloc[-1]
    rsi_stat = "과매수" if curr_rsi >= 70 else "과매도" if curr_rsi <= 30 else "보통"

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, 
                        subplot_titles=("", f"RSI: {curr_rsi:.1f} ({rsi_stat})"), row_width=[0.3, 0.7])
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], 
                                 increasing_line_color='#f04452', decreasing_line_color='#3182f6'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#FFD700', width=1)), row=2, col=1)
    fig.update_layout(template="plotly_white", height=500, xaxis_rangeslider_visible=False, showlegend=False, margin=dict(t=30, b=0))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

    # 뉴스 섹션 (KeyError 방지 적용)
    st.subheader("📰 최신 소식")
    encoded_ticker = urllib.parse.quote(company_name)
    feed = feedparser.parse(f"https://news.google.com/rss/search?q={encoded_ticker}+when:7d&hl=ko&gl=KR&ceid=KR:ko")
    
    for item in sorted(feed.entries, key=lambda x: x.get('published_parsed', 0), reverse=True)[:5]:
        title = item.get('title', '제목 없음')
        st.write(f"**🔗 {translate_text(title)}**")
        st.caption(f"{item.get('published', '')} | [열기]({item.get('link', '#')})")
        st.write("---")
else:
    st.error("데이터를 가져올 수 없습니다. 잠시 후 다시 시도해 주세요.")

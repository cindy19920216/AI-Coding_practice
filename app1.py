import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
import feedparser
import urllib.parse

# 1. 페이지 설정 및 토스 스타일 CSS 적용
st.set_page_config(page_title="우리 가족 주식 매니저", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Nanum Gothic', sans-serif;
    }
    /* 토스 느낌의 카드 스타일 */
    .metric-card {
        background-color: #f9fafb;
        border-radius: 15px;
        padding: 20px;
        border: 1px solid #f1f3f5;
        text-align: center;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #333d4b;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #8b95a1;
        margin-bottom: 5px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        background-color: #3182f6; /* 토스 블루 */
        color: white;
        font-weight: bold;
        border: none;
        height: 3rem;
    }
    h1 { font-size: 2rem !important; font-weight: 700; color: #191f28; }
    </style>
    """, unsafe_allow_html=True)

# 사이드바 설정
st.sidebar.header("🏠 가족 공유 설정")
ticker_input = st.sidebar.text_input("종목 검색 (티커 입력)", value="005930.KS")
days = st.sidebar.slider("분석 기간", 30, 730, 365)
run_button = st.sidebar.button("분석 시작")

# --- 퀀트 보조 함수 ---
def get_status_color(val, threshold_high, threshold_low, reverse=False):
    if val is None: return "#8b95a1"
    if reverse: # 낮을수록 좋은 지표 (예: PER)
        if val <= threshold_low: return "#3182f6" # 블루 (좋음)
        if val >= threshold_high: return "#f04452" # 레드 (주의)
    else: # 높을수록 좋은 지표 (예: ROE)
        if val >= threshold_high: return "#3182f6"
        if val <= threshold_low: return "#f04452"
    return "#333d4b"

# 데이터 및 정보 로드
start_date = datetime.now() - timedelta(days=days)
df = yf.download(ticker_input, start=start_date)
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

stock = yf.Ticker(ticker_input)
info = stock.info
company_name = info.get('longName') or info.get('shortName') or ticker_input

if not df.empty:
    # 제목 및 현재가
    current_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2]
    change = current_price - prev_price
    change_percent = (change / prev_price) * 100

    st.title(f"{company_name}")
    col_p1, col_p2 = st.columns([1, 5])
    with col_p1:
        st.metric("", f"{current_price:,.0f}원", f"{change_percent:+.2f}%")

    st.markdown("---")

    # 2단계: 토스형 퀀트 요약 카드 섹션
    st.subheader("📊 퀀트 분석 요약")
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)

    # 지표 추출 (전문가용 데이터를 일반인용 언어로 변환)
    per = info.get('trailingPE')
    pbr = info.get('priceToBookRatio')
    roe = info.get('returnOnEquity')
    div_yield = info.get('dividendYield')

    with q_col1:
        color = get_status_color(per, 20, 10, reverse=True)
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">가격 부담 (PER)</div>
            <div class="metric-value" style="color:{color}">{f"{per:.1f}배" if per else "데이터 없음"}</div>
        </div>""", unsafe_allow_html=True)

    with q_col2:
        color = get_status_color(pbr, 2.0, 0.8, reverse=True)
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">자산 가치 (PBR)</div>
            <div class="metric-value" style="color:{color}">{f"{pbr:.2f}배" if pbr else "데이터 없음"}</div>
        </div>""", unsafe_allow_html=True)

    with q_col3:
        color = get_status_color(roe, 0.15, 0.08)
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">이익 능력 (ROE)</div>
            <div class="metric-value" style="color:{color}">{f"{roe*100:.1;f}%" if roe else "데이터 없음"}</div>
        </div>""", unsafe_allow_html=True)

    with q_col4:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">배당 수익률</div>
            <div class="metric-value" style="color:#3182f6">{f"{div_yield*100:.1f}%" if div_yield else "0.0%"}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # (이후 차트 및 뉴스 코드는 기존과 동일하게 유지하거나 필요시 슬림화)
    # ... [차트 및 뉴스 로직 생략 - 이전 코드의 내용을 여기에 붙여넣으시면 됩니다]

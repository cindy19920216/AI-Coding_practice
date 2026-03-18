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

# --- 1. 페이지 설정 및 토스/모바일 스타일 CSS ---
st.set_page_config(page_title="매니저 JS", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Nanum Gothic', sans-serif; background-color: #f2f4f6; }
    
    /* 메인페이지 카드 스타일 */
    .main-card {
        background-color: Black;
        border-radius: 15px;
        padding: 30px;
        border: 1px solid #e5e8eb;
        text-align: center;
        transition: transform 0.2s, box-shadow 0.2s;
        cursor: pointer;
        height: 100%;
        margin-bottom: 15px;
    }
    .main-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.05);
        border-color: #3182f6;
    }
    .card-icon { font-size: 3rem; margin-bottom: 15px; }
    .card-title { font-size: 1.3rem; font-weight: 700; color: #191f28; margin-bottom: 8px; }
    .card-desc { font-size: 0.9rem; color: #8b95a1; line-height: 1.4; }

    /* 기존 퀀트 카드 스타일 (유지) */
    .metric-card { background-color: white; border-radius: 15px; padding: 20px; border: 1px solid #e5e8eb; text-align: center; height: 100px; }
    .metric-value { font-size: 1.4rem; font-weight: 700; color: #333d4b; margin-top: 5px; }
    .metric-label { font-size: 0.85rem; color: #8b95a1; }

    /* 버튼 스타일 */
    .stButton>button { width: 100%; border-radius: 10px; background-color: #3182f6; color: white; font-weight: bold; height: 3rem; border: none; }
    
    /* 제목 스타일 */
    h1 { font-size: 2.2rem !important; font-weight: 700; color: #191f28; margin-bottom: 20px; }
    h2 { font-size: 1.6rem !important; font-weight: 700; color: #333d4b; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 앱 내 세션 상태 (Navigation) 설정 ---
# 사용자가 어떤 페이지에 있는지 기억하는 변수입니다.
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'Home' # 처음 키면 홈화면

# 페이지 이동 함수
def move_to(page_name):
    st.session_state['current_page'] = page_name
    st.rerun() # 화면을 다시 그려서 페이지 이동 효과를 냅니다.

# --- 3. 각 페이지별 기능 정의 (함수화) ---

# A. 메인페이지 (홈화면)
def show_home():
    st.title("우리가족 금융 Dashboard")
    st.markdown("<h2 style='text-align:center; color:#8b95a1;'>♡ </h2><br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""<div class="main-card">
            <div class="card-icon">📈</div>
            <div class="card-title">Stock Dashboard</div>
            <div class="card-desc">증시와 지표를<br>한눈에 분석합니다.</div>
        </div>""", unsafe_allow_html=True)
        if st.button("들어가기", key="go_stock"): move_to('StockAnalysis')

    with col2:
        st.markdown("""<div class="main-card">
            <div class="card-icon">💰</div>
            <div class="card-title">Portfolio </div>
            <div class="card-desc">우리 가족 가상 수익률과<br>자산 현황을 관리합니다.</div>
        </div>""", unsafe_allow_html=True)
        if st.button("준비 중", key="go_port", disabled=True): pass # disabled=True로 나중에 구현 예정 표시

    with col3:
        st.markdown("""<div class="main-card">
            <div class="card-icon">🧑‍🏫</div>
            <div class="card-title">개인 일상</div>
            <div class="card-desc">일상 이야기를 공유합니다.</div>
        </div>""", unsafe_allow_html=True)
        if st.button("준비 중", key="go_edu", disabled=True): pass

# B. 주식 분석 대시보드 페이지 (기존 코드)
def show_stock_analysis():
    # 상단에 '홈으로' 버튼 추가
    col_back, _ = st.columns([1, 10])
    with col_back:
        if st.button("🔙 홈으로", key="back_home"): move_to('Home')

    # 사이드바 설정 (이 페이지에서만 보이게)
    st.sidebar.header("📈 주식 분석 설정")
    ticker_input = st.sidebar.text_input("종목 검색 (예: 005930.KS)", value="005930.KS")
    days = st.sidebar.slider("분석 기간", 30, 730, 365)
    run_button = st.sidebar.button("🚀 분석 시작")

    # --- 기존 주식 분석 로직 (복사해서 붙여넣기) ---
    # [!] 안정화된 1단계 코드를 여기에 모두 집어넣으시면 됩니다.
    # (코드가 너무 길어져서 핵심 예시만 남기고 생략합니다. 실제로는 이전 단계 최종 코드를 넣어야 합니다.)
    
    # 예시 데이터 (실제 코드를 넣어주세요)
    st.title(f"{ticker_input} 분석 대시보드")
    st.info("여기에 기존의 퀀트 카드, 차트, 뉴스 코드가 들어갑니다.")
    # ... [기존 1단계 코드를 여기에 복사]

# --- 4. 메인 컨트롤러 (Navigation 실행) ---
# 세션 상태에 따라 어떤 페이지 함수를 실행할지 결정합니다.
if st.session_state['current_page'] == 'Home':
    show_home()
elif st.session_state['current_page'] == 'StockAnalysis':
    show_stock_analysis()

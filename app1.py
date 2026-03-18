import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# --- 1. 토스 익스클루시브 디자인 (CSS) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    
    /* 전체 배경색 및 폰트 설정 (토스 전용 프리텐다드 폰트 느낌) */
    html, body, [class*="css"] { 
        font-family: 'Pretendard', -apple-system, sans-serif !important;
        background-color: #F2F4F6 !important; /* 토스 배경색 */
    }

    /* 메인 컨테이너 여백 조절 */
    .main .block-container { padding-top: 2rem; max-width: 800px; }

    /* 토스형 섹션 카드 */
    .toss-card {
        background-color: white;
        border-radius: 24px;
        padding: 24px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        transition: all 0.2s ease-in-out;
        border: none;
        cursor: pointer;
    }
    .toss-card:hover {
        background-color: #EBF4FF; /* 살짝 푸른 빛 도는 하이라이트 */
        transform: scale(1.02);
    }
    
    .icon-box {
        width: 56px;
        height: 56px;
        background-color: #F9FAFB;
        border-radius: 16px;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 28px;
        margin-right: 20px;
    }

    .text-box { flex-grow: 1; text-align: left; }
    .title-text { font-size: 18px; font-weight: 700; color: #191F28; margin-bottom: 4px; }
    .desc-text { font-size: 14px; color: #8B95A1; }
    .arrow-icon { color: #B0B8C1; font-size: 20px; }

    /* 버튼 숨기기 및 커스텀 클릭 처리용 스타일 */
    .stButton>button {
        background: transparent; border: none; padding: 0; width: 100%; height: auto;
    }
    .stButton>button:hover { background: transparent; border: none; }
    
    /* 상단 배너 */
    .header-banner {
        padding: 20px 0;
        margin-bottom: 20px;
    }
    .user-name { font-size: 24px; font-weight: 700; color: #191F28; }
    .sub-greeting { font-size: 16px; color: #4E5968; margin-top: 4px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 페이지 내비게이션 로직 ---
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'Home'

def move_to(page_name):
    st.session_state['current_page'] = page_name
    st.rerun()

# --- 3. 홈화면 구성 (토스 UI) ---
def show_home():
    # 상단 인사말
    st.markdown("""
        <div class="header-banner">
            <div class="user-name">재선님, 반가워요 👋</div>
            <div class="sub-greeting">오늘 우리 가족의 금융 상태는 어떤가요?</div>
        </div>
    """, unsafe_allow_html=True)

    # 섹션 1: 주식 분석
    with st.container():
        if st.button("", key="btn_stock"): move_to('StockAnalysis')
        st.markdown("""
            <div class="toss-card">
                <div class="icon-box">📈</div>
                <div class="text-box">
                    <div class="title-text">주식 분석 대시보드</div>
                    <div class="desc-text">전문가용 퀀트 지표를 알기 쉽게 보여드려요</div>
                </div>
                <div class="arrow-icon">❯</div>
            </div>
        """, unsafe_allow_html=True)

    # 섹션 2: 가상 포트폴리오
    with st.container():
        if st.button("", key="btn_portfolio"): move_to('Portfolio')
        st.markdown("""
            <div class="toss-card">
                <div class="icon-box">💰</div>
                <div class="text-box">
                    <div class="title-text">가족 가상 포트폴리오</div>
                    <div class="desc-text">우리 가족의 투자 성적표를 확인해 보세요</div>
                </div>
                <div class="arrow-icon">❯</div>
            </div>
        """, unsafe_allow_html=True)

    # 섹션 3: 퀀트 교실
    with st.container():
        if st.button("", key="btn_edu"): move_to('Education')
        st.markdown("""
            <div class="toss-card">
                <div class="icon-box">🏫</div>
                <div class="text-box">
                    <div class="title-text">쉬운 퀀트 투자 교실</div>
                    <div class="desc-text">투자가 어려운 가족들을 위한 기초 가이드</div>
                </div>
                <div class="arrow-icon">❯</div>
            </div>
        """, unsafe_allow_html=True)

# --- 4. 주식 분석 페이지 (간략화된 뼈대) ---
def show_stock_analysis():
    # 상단 네비게이션바 (토스 스타일)
    nav_col, _ = st.columns([1, 8])
    with nav_col:
        if st.button("❮ 뒤로", key="back_home"): move_to('Home')
    
    st.title("📈 주식 분석")
    st.write("전문가님의 퀀트 로직이 들어갈 공간입니다.")
    # 여기에 이전 단계에서 만든 상세 분석 코드를 함수로 호출하면 됩니다.

# --- 5. 페이지 렌더링 컨트롤러 ---
if st.session_state['current_page'] == 'Home':
    show_home()
elif st.session_state['current_page'] == 'StockAnalysis':
    show_stock_analysis()
else:
    st.write("준비 중인 페이지입니다.")
    if st.button("홈으로 돌아가기"): move_to('Home')

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# --- 1. 토스 익스클루시브 디자인 (CSS) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    
    html, body, [class*="css"] { 
        font-family: 'Pretendard', -apple-system, sans-serif !important;
        background-color: #F2F4F6 !important;
    }

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
        background-color: #EBF4FF;
        transform: scale(1.01);
    }
    
    .icon-box {
        width: 56px; height: 56px;
        background-color: #F9FAFB;
        border-radius: 16px;
        display: flex; justify-content: center; align-items: center;
        font-size: 28px; margin-right: 20px;
    }

    .text-box { flex-grow: 1; text-align: left; }
    .title-text { font-size: 18px; font-weight: 700; color: #191F28; margin-bottom: 4px; }
    .desc-text { font-size: 14px; color: #8B95A1; }
    .arrow-icon { color: #B0B8C1; font-size: 20px; }

    /* 버튼 투명화 (카드 클릭 효과용) */
    .stButton>button {
        background: transparent; border: none; padding: 0; width: 100%; height: auto;
    }
    
    .header-banner { padding: 20px 0; margin-bottom: 20px; }
    .user-name { font-size: 26px; font-weight: 700; color: #191F28; }
    .sub-greeting { font-size: 16px; color: #4E5968; margin-top: 6px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 5인 가족 개인화 로직 (URL 파라미터 자동화) ---
# 주소창의 ?user=ID 부분을 읽어옵니다.
query_params = st.query_params
user_id = query_params.get("user", "chanhee") # 기본값은 아빠(찬희님)

# 전문가님의 가족 매핑 테이블
user_map = {
    "chanhee": "찬희",   # 아빠
    "jiwoo": "지우",     # 엄마
    "jaeseon": "재선",   # 큰딸
    "gyubi": "규비",     # 작은딸
    "seunggyu": "승규"   # 막내
}
display_name = user_map.get(user_id, "찬희") # 등록되지 않은 ID면 기본값 '찬희'

# --- 3. 페이지 내비게이션 ---
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'Home'

def move_to(page_name):
    st.session_state['current_page'] = page_name
    st.rerun()

# --- 4. 홈화면 구성 ---
def show_home():
    st.markdown(f"""
        <div class="header-banner">
            <div class="user-name">{display_name}님, 반가워요 👋</div>
            <div class="sub-greeting">오늘 우리 가족의 금융 상태를 확인해 보세요.</div>
        </div>
    """, unsafe_allow_html=True)

    # 1. 주식 분석 카드
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

    # 2. 포트폴리오 카드
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

    # 3. 퀀트 교실 카드
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

# --- 5. 페이지 실행 컨트롤러 ---
if st.session_state['current_page'] == 'Home':
    show_home()
elif st.session_state['current_page'] == 'StockAnalysis':
    # 주식 분석 페이지 상단 네비게이션
    if st.button("❮ 홈으로", key="back_home"): move_to('Home')
    st.title(f"📈 {display_name}님을 위한 주식 분석")
    st.write("전문가님의 퀀트 로직 코드가 여기에 들어갑니다.")
else:
    if st.button("❮ 홈으로", key="back_home_err"): move_to('Home')
    st.write(f"현재 {st.session_state['current_page']} 페이지는 준비 중입니다.")

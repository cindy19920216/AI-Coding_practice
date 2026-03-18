import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
import feedparser
import urllib.parse

# --- 1. 전용 디자인 (토스 & 모바일 최적화 CSS) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    .main .block-container { max-width: 800px; padding-top: 2rem; }

    /* 프로필 및 일상 공유 카드 스타일 */
    .profile-card {
        background-color: white; border-radius: 20px; padding: 20px;
        text-align: center; transition: all 0.2s; border: 1px solid #e5e8eb;
        box-shadow: 0 4px 12px rgba(0,0,0,0.02);
    }
    .profile-emoji { font-size: 40px; margin-bottom: 10px; }
    .profile-name { font-size: 16px; font-weight: 700; color: #191f28; }
    
    .sns-tab {
        background-color: white; border-radius: 20px; padding: 20px; 
        display: flex; align-items: center; border: 1px solid #e5e8eb;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-top: 20px;
    }

    /* 토스형 메인 메뉴 카드 */
    .toss-card {
        background-color: white; border-radius: 24px; padding: 24px; margin-bottom: 16px;
        display: flex; align-items: center; transition: all 0.2s; border: none;
    }
    .icon-box { width: 50px; height: 50px; background-color: #F9FAFB; border-radius: 14px; 
                display: flex; justify-content: center; align-items: center; font-size: 24px; margin-right: 15px; }
    
    /* 버튼 투명화 로직 */
    .stButton>button { background: transparent; border: none; padding: 0; width: 100%; height: auto; color: inherit; }
    .stButton>button:hover { background: transparent; border: none; color: #3182f6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 및 세션 관리 ---
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'current_page' not in st.session_state: st.session_state['current_page'] = 'Home'

family_members = [
    {"id": "chanhee", "name": "찬희", "role": "아빠", "emoji": "👨🏻‍💻"},
    {"id": "jiwoo", "name": "지우", "role": "엄마", "emoji": "👩🏻‍💼"},
    {"id": "jaeseon", "name": "재선", "role": "큰딸", "emoji": "👩🏻‍🎨"},
    {"id": "gyubi", "name": "규비", "role": "작은딸", "emoji": "👧🏻"},
    {"id": "seunggyu", "name": "승규", "role": "막내", "emoji": "👦🏻"}
]

# 구글 시트 연동 (전문가님: 시트 ID를 입력하세요)
def load_watchlist(user_id):
    try:
        sheet_url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit#gid=0"
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=sheet_url)
        return df[df['user_id'] == user_id]['ticker'].tolist()
    except: return []

# --- 3. 화면별 함수 정의 ---

# [화면 1] 로그인/프로필 선택 + 일상 공유 탭
def show_login_screen():
    st.markdown("<h1 style='text-align: center; color: #191f28; margin-top: 30px;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b95a1; margin-bottom: 40px;'>가족 금융 매니저에 오신 것을 환영합니다</p>", unsafe_allow_html=True)
    
    # 가족 프로필 (5인)
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            if st.button("", key=f"sel_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()
            st.markdown(f"""
                <div class="profile-card">
                    <div class="profile-emoji">{m['emoji']}</div>
                    <div class="profile-name">{m['name']}</div>
                    <div style="font-size:12px; color:#8b95a1;">{m['role']}</div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # [일상 공유하기] 탭 (프로필 하단 배치)
    if st.button("", key="go_sns_tab"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()
    st.markdown("""
        <div class="sns-tab">
            <div style="font-size: 24px; margin-right: 15px;">📸</div>
            <div style="text-align: left; flex-grow:1;">
                <div style="font-size: 16px; font-weight: 700; color: #191f28;">일상 공유하기</div>
                <div style="font-size: 13px; color: #8b95a1;">오늘 가족들에게 하고 싶은 말이 있나요?</div>
            </div>
            <div style="color: #B0B8C1;">❯</div>
        </div>
    """, unsafe_allow_html=True)

# [화면 2] 홈화면 (로그인 후)
def show_home():
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    
    # 상단 바
    col_h, col_l = st.columns([8, 2])
    with col_h: st.markdown(f"<h1>{user['name']}님, 반가워요 👋</h1>", unsafe_allow_html=True)
    with col_l: 
        if st.button("가족 바꾸기"): 
            st.session_state['user_id'] = None
            st.rerun()

    # 관심 종목 리스트 (구글 시트 연동)
    st.markdown("<h3 style='font-size:18px; margin-top:20px;'>내가 찜한 주식</h3>", unsafe_allow_html=True)
    watchlist = load_watchlist(user['id'])
    if watchlist:
        for tk in watchlist:
            st.markdown(f'<div style="background:white; padding:15px; border-radius:15px; margin-bottom:8px; border:1px solid #e5e8eb;"><b>{tk}</b> <span style="float:right; color:#3182f6;">상세보기 ❯</span></div>', unsafe_allow_html=True)
    else:
        st.info("구글 시트에 종목을 등록해 주세요.")

    # 메인 메뉴
    if st.button("", key="go_stock_page"): st.session_state['current_page'] = 'Stock'; st.rerun()
    st.markdown('<div class="toss-card"><div class="icon-box">📈</div><div><div style="font-weight:700;">주식 분석 대시보드</div><div style="color:#8b95a1; font-size:13px;">전문가용 퀀트 분석</div></div></div>', unsafe_allow_html=True)

# [화면 3] 일상 공유 페이지
def show_sns_page():
    if st.button("❮ 홈으로", key="back_from_sns"):
        st.session_state['current_page'] = 'Home'
        st.rerun()
    st.title("📸 가족 일상 공유")
    st.write("가족들과 오늘 하루를 공유해 보세요!")
    # 여기에 추후 메시지 입력/출력 기능 추가 예정
if st.button("", key="go_sns_fixed"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

# --- 4. 메인 컨트롤러 ---
if st.session_state['user_id'] is None:
    show_login_screen()
else:
    if st.session_state['current_page'] == 'Home':
        show_home()
    elif st.session_state['current_page'] == 'FamilySNS':
        show_sns_page()
    elif st.session_state['current_page'] == 'Stock':
        # 이전 단계의 주식 분석 상세 코드를 여기에 연결
        if st.button("❮ 뒤로가기"): st.session_state['current_page'] = 'Home'; st.rerun()
        st.write("상세 분석 페이지입니다.")

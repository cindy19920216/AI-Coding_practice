import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. 전용 디자인 (가로폭 꽉 채우고 버튼 크게 키우기) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #0F1117; }
    
    /* 모바일 화면 최적화 너비 설정 */
    .main .block-container { 
        max-width: 550px !important; 
        padding-top: 3rem !important; 
    }

    /* [중요] 모든 버튼 공통: 카드 디자인으로 변신 */
    div.stButton > button {
        background-color: #1F2128 !important;
        border: 1px solid #30343D !important;
        border-radius: 24px !important;
        color: white !important;
        transition: all 0.2s ease-in-out !important;
        width: 100% !important;
        display: block !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
    }

    /* 1. 가족 프로필 버튼 (세로로 길고 큼직하게) */
    div.stButton > button[key^="sel_"] {
        height: 180px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        white-space: pre-line !important;
        line-height: 1.6 !important;
    }

    /* 2. 일상 공유하기 블루 탭 (가로로 꽉 차고 파란색 강조) */
    div.stButton > button[key="go_sns_tab"] {
        height: 110px !important;
        background-color: #3182f6 !important; /* 토스 블루 */
        border: none !important;
        text-align: left !important;
        padding-left: 25px !important;
        font-size: 20px !important;
        font-weight: 700 !important;
        margin-top: 25px !important;
        box-shadow: 0 8px 20px rgba(49, 130, 246, 0.3) !important;
    }

    div.stButton > button:hover {
        transform: translateY(-5px) scale(1.02);
        border-color: #3182f6 !important;
    }

    .main-title { color: white; text-align: center; font-size: 26px; margin-bottom: 35px; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 및 세션 관리 ---
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'current_page' not in st.session_state: st.session_state['current_page'] = 'Home'
if 'family_feed' not in st.session_state: st.session_state['family_feed'] = []
if 'speaking_id' not in st.session_state: st.session_state['speaking_id'] = None

family_members = [
    {"id": "chanhee", "name": "찬희", "role": "아빠", "emoji": "👨🏻‍💻"},
    {"id": "jiwoo", "name": "지우", "role": "엄마", "emoji": "👩🏻‍💼"},
    {"id": "jaeseon", "name": "재선", "role": "큰딸", "emoji": "👩🏻‍🎨"},
    {"id": "gyubi", "name": "규비", "role": "작은딸", "emoji": "👧🏻"},
    {"id": "seunggyu", "name": "승규", "role": "막내", "emoji": "👦🏻"}
]

# --- 3. 화면 구현 ---

def show_login_screen():
    st.markdown("<h1 class='main-title'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    
    # 가족 프로필 (5열 나열)
    cols = st.columns(5, gap="small")
    for i, m in enumerate(family_members):
        with cols[i]:
            # 이모티콘 크게, 이름은 아래에
            label = f"{m['emoji']}\n{m['name']}"
            if st.button(label, key=f"sel_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 일상 공유하기 (파란색 와이드 버튼)
    sns_label = "📸   일상 공유하기\n우리 가족 소식 보러가기      ❯"
    if st.button(sns_label, key="go_sns_tab"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

def show_sns_page():
    # 게시판 내부도 시원하게 구성
    if st.button("❮  홈으로 돌아가기", key="back_home"):
        st.session_state['current_page'] = 'Home'; st.rerun()
    
    st.markdown("<h1 style='color:white;'>📸 가족 게시판</h1>", unsafe_allow_html=True)
    st.write("성공적으로 들어왔습니다! 이제 여기서 대화를 나눠보세요.")

# --- 4. 메인 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    show_sns_page()
else:
    # 로그인 성공 후 메인 화면
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.markdown(f"<h1 style='color:white; text-align:center;'>{user['name']}님 반가워요!</h1>", unsafe_allow_html=True)
    if st.button("❮  가족 바꾸기", key="logout"):
        st.session_state['user_id'] = None; st.rerun()

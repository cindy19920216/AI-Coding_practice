import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. 전용 디자인 (버튼 자체를 카드로 변신시킴) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #0F1117; } /* 배경을 어둡게 설정 */
    .main .block-container { max-width: 800px; padding-top: 2rem; }

    /* 모든 버튼 기본 스타일 초기화 */
    div.stButton > button {
        background-color: white !important;
        border: none !important;
        border-radius: 20px !important;
        color: #191f28 !important;
        transition: all 0.2s;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        width: 100% !important;
    }

    /* 1. 프로필 버튼 전용 (5개 나열용) */
    div.stButton > button[key^="sel_"] {
        height: 150px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        white-space: pre-line !important; /* 줄바꿈 허용 */
        line-height: 1.5 !important;
    }
    
    /* 2. 일상 공유하기 와이드 버튼 전용 */
    div.stButton > button[key="go_sns_tab"] {
        height: 100px !important;
        text-align: left !important;
        padding-left: 25px !important;
        font-size: 16px !important;
        margin-top: 20px !important;
    }

    div.stButton > button:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(49, 130, 246, 0.2);
    }
    
    /* 제목 스타일 */
    .main-title { color: #E5E8EB; text-align: center; margin-bottom: 30px; font-weight: 700; }
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
    
    # 1. 프로필 선택 (이모티콘과 텍스트를 버튼 라벨에 직접 입력)
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            # \n (줄바꿈)을 써서 이모티콘과 이름을 배치합니다.
            label = f"{m['emoji']}\n\n{m['name']}\n{m['role']}"
            if st.button(label, key=f"sel_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. 일상 공유하기 와이드 탭
    # HTML 태그 없이 텍스트와 이모지만 사용합니다.
    sns_label = "📸   일상 공유하기\n오늘 가족들에게 하고 싶은 말이 있나요?       ❯"
    if st.button(sns_label, key="go_sns_tab"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

# --- 4. 메인 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    # 일상 공유 상세 페이지 (기존에 드린 show_sns_page 코드를 여기에 넣으시면 됩니다)
    if st.button("❮ 홈으로", key="back_home"):
        st.session_state['current_page'] = 'Home'; st.rerun()
    st.title("📸 가족 게시판")
    st.write("성공적으로 들어왔습니다!")
else:
    # 홈화면 (주식 등)
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.markdown(f"<h1 style='color:white;'>{user['name']}님 반가워요!</h1>", unsafe_allow_html=True)
    if st.button("❮ 가족 바꾸기", key="logout"):
        st.session_state['user_id'] = None; st.rerun()

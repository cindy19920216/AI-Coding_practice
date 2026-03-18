import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. 전용 디자인 (넷플릭스 스타일 & 대형 아이콘 CSS) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #0F1117; }
    
    .main .block-container { 
        max-width: 600px !important; 
        padding-top: 3rem !important; 
    }

    /* 프로필 카드: 아이콘을 주인공으로 (넷플릭스 스타일) */
    div.stButton > button[key^="sel_"] {
        height: 180px !important;
        background-color: #1F1F1F !important;
        color: white !important;
        border: 2px solid transparent !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        white-space: pre-line !important;
        line-height: 1.2 !important;
        transition: all 0.2s ease-in-out !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* 아이콘(이모지) 크기 대폭 확대 및 이름과 간격 조절 */
    div.stButton > button[key^="sel_"] p {
        font-size: 60px !important; /* 이모지 크기 */
        margin-bottom: 15px !important;
    }

    div.stButton > button[key^="sel_"]:hover {
        border-color: white !important;
        transform: scale(1.05);
        background-color: #2F2F2F !important;
    }

    /* 일상 공유하기 와이드 배너 */
    div.stButton > button[key="go_sns_tab"] {
        height: 110px !important;
        background: linear-gradient(90deg, #3182f6, #4d94f7) !important;
        color: white !important;
        border: none !important;
        border-radius: 20px !important;
        text-align: left !important;
        padding-left: 30px !important;
        font-size: 20px !important;
        font-weight: 700 !important;
        margin-top: 30px !important;
        box-shadow: 0 8px 20px rgba(49, 130, 246, 0.3) !important;
    }

    .main-title { color: white; text-align: center; font-size: 28px; margin-bottom: 40px; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 관리 ---
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'current_page' not in st.session_state: st.session_state['current_page'] = 'Home'

family_members = [
    {"id": "chanhee", "name": "찬희", "emoji": "👨🏻‍💻"},
    {"id": "jiwoo", "name": "지우", "emoji": "👩🏻‍💼"},
    {"id": "jaeseon", "name": "재선", "emoji": "👩🏻‍🎨"},
    {"id": "gyubi", "name": "규비", "emoji": "👧🏻"},
    {"id": "seunggyu", "name": "승규", "emoji": "👦🏻"}
]

# --- 3. 화면 구현 ---

def show_login_screen():
    st.markdown("<h1 class='main-title'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    
    # 배치를 2행으로 분리 (3인 / 2인)
    # 1행: 찬희, 지우, 재선
    row1 = st.columns(3, gap="medium")
    for i in range(3):
        m = family_members[i]
        with row1[i]:
            if st.button(f"{m['emoji']}\n\n{m['name']}", key=f"sel_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()

    st.write("") # 행 간격

    # 2행: 규비, 승규 (가운데 정렬을 위해 5컬럼 중 중앙 2~4번 사용하거나 2컬럼 사용)
    # 여기서는 꽉 차 보이기 위해 2컬럼으로 크게 배치합니다.
    row2_cols = st.columns([1, 2, 2, 1], gap="medium")
    with row2_cols[1]:
        m = family_members[3]
        if st.button(f"{m['emoji']}\n\n{m['name']}", key=f"sel_{m['id']}"):
            st.session_state['user_id'] = m['id']
            st.rerun()
    with row2_cols[2]:
        m = family_members[4]
        if st.button(f"{m['emoji']}\n\n{m['name']}", key=f"sel_{m['id']}"):
            st.session_state['user_id'] = m['id']
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 일상 공유하기 배너
    if st.button("📸   일상 공유하기\n우리 가족 소식 보러가기      ❯", key="go_sns_tab"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

# --- 4. 메인 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    if st.button("❮  홈으로 돌아가기", key="back_home"):
        st.session_state['current_page'] = 'Home'; st.rerun()
    st.title("📸 가족 게시판")
else:
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.markdown(f"<h1 style='color:white; text-align:center;'>{user['name']}님 반가워요!</h1>", unsafe_allow_html=True)
    if st.button("❮  가족 바꾸기", key="logout"):
        st.session_state['user_id'] = None; st.rerun()

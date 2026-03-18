import streamlit as st
from datetime import datetime

# --- 1. 디자인 고정 (올 화이트 아이콘 & 한 줄 배치 강제 유지) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #0F1117; }
    
    /* 화면 전체 너비를 넉넉하게 사용 */
    .main .block-container { 
        max-width: 900px !important; 
        padding-top: 3rem !important; 
    }

    /* 버튼 디자인: 한 줄에 있어도 크기가 죽지 않게 설정 */
    div.stButton > button {
        background-color: #1F1F1F !important; /* 약간 밝은 회색으로 카드 구분 */
        border: 2px solid transparent !important;
        border-radius: 12px !important;
        color: white !important; /* 글씨 하얗게 */
        transition: all 0.2s ease-in-out !important;
        width: 100% !important;
        display: block !important;
        white-space: pre-line !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
    }

    /* 1. 프로필 카드: 한 줄(5열)에서도 큼직한 높이 유지 */
    div.stButton > button[key^="sel_"] {
        height: 160px !important; /* 높이 고정 */
        min-width: 100px !important; /* 모바일에서 찌그러짐 방지 */
        font-size: 16px !important;
        font-weight: 700 !important;
    }

    /* 이모지(아이콘) 크기: 카드 안에서 꽉 차게, 하얗게 (자동 반영) */
    div.stButton > button[key^="sel_"] p {
        font-size: 55px !important; 
        margin-bottom: 5px !important;
        display: block !important;
    }

    /* 2. 일상 공유하기 배너: 가로로 꽉 차는 와이드 스타일 */
    div.stButton > button[key="go_sns_tab"] {
        height: 100px !important;
        background: linear-gradient(90deg, #3182f6, #4d94f7) !important;
        text-align: left !important;
        padding-left: 25px !important;
        font-size: 18px !important;
        margin-top: 40px !important;
    }

    /* 호버 효과 */
    div.stButton > button:hover {
        border-color: white !important;
        transform: translateY(-5px);
        background-color: #2F2F2F !important;
    }

    .main-title { color: white; text-align: center; font-size: 28px; margin-bottom: 40px; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 및 세션 관리 ---
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
    
    # 5명 한 줄(5열) 배치
    cols = st.columns(5, gap="small")
    for i, m in enumerate(family_members):
        with cols[i]:
            # 올 화이트 이모지와 이름을 버튼 라벨로 사용 (에러 방지)
            if st.button(f"{m['emoji']}\n{m['name']}", key=f"sel_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 하단 일상 공유하기 배너
    sns_label = "📸   일상 공유하기\n우리 가족 소식 보러가기       ❯"
    if st.button(sns_label, key="go_sns_tab"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

# --- 4. 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    if st.button("❮ 홈으로 돌아가기", key="back_home"):
        st.session_state['current_page'] = 'Home'; st.rerun()
    st.markdown("<h1 style='color:white;'>📸 가족 게시판</h1>", unsafe_allow_html=True)
else:
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.markdown(f"<h1 style='color:white; text-align:center;'>{user['emoji']} {user['name']}님 반가워요!</h1>", unsafe_allow_html=True)
    if st.button("❮ 가족 바꾸기", key="logout"):
        st.session_state['user_id'] = None; st.rerun()

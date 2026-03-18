import streamlit as st
from datetime import datetime

# --- 1. 디자인 고정 (5인 한 줄 & 여백 삭제 & 화이트 카드) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    
    /* [핵심] 모바일 화면에서 좌우 여백을 최소화하여 5명이 꽉 차게 함 */
    .main .block-container { 
        max-width: 100% !important; 
        padding-left: 10px !important; 
        padding-right: 10px !important; 
        padding-top: 2rem !important; 
    }

    /* 버튼 디자인: 너비를 100%로 설정하여 컬럼을 꽉 채움 */
    div.stButton > button {
        background-color: white !important;
        border: 1px solid #e5e8eb !important;
        border-radius: 16px !important;
        color: #191f28 !important;
        transition: all 0.2s ease-in-out !important;
        width: 100% !important; /* 컬럼 너비에 맞게 꽉 채움 */
        display: block !important;
        white-space: pre-line !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02) !important;
        padding: 10px 5px !important;
    }

    /* 1. 프로필 카드: 5인 배치 시 최적의 높이와 폰트 크기 */
    div.stButton > button[key^="sel_"] {
        height: 120px !important; /* 5개 나열 시 너무 높으면 답답하므로 적절히 조절 */
    }

    /* 이모지 크기: 5개 나열 시 적당히 큼직하게 (45px) */
    div.stButton > button[key^="sel_"] p {
        font-size: 40px !important; 
        margin-bottom: 5px !important;
        display: block !important;
    }

    /* 이름 폰트: 5개 나열 시 깨지지 않도록 적당한 크기 (14px) */
    div.stButton > button[key^="sel_"] {
        font-size: 14px !important;
        font-weight: 700 !important;
    }

    /* 2. 하단 일상 공유하기 배너: 가로로 길게 꽉 채움 */
    div.stButton > button[key="go_sns_tab"] {
        height: 90px !important;
        text-align: left !important;
        padding-left: 20px !important;
        margin-top: 20px !important;
    }

    /* 호버 효과 */
    div.stButton > button:hover {
        border-color: #3182f6 !important;
        background-color: #F9FAFB !important;
    }

    .main-title { color: #191f28; text-align: center; font-size: 24px; margin-bottom: 30px; font-weight: 700; }
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
    
    # 5인 한 줄 배치 (gap을 최소화하여 꽉 채움)
    cols = st.columns(5, gap="small")
    for i, m in enumerate(family_members):
        with cols[i]:
            if st.button(f"{m['emoji']}\n{m['name']}", key=f"sel_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 하단 일상 공유하기 배너 (가로 전체 사용)
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
    st.title("📸 가족 게시판")
else:
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.markdown(f"<h2 style='text-align:center;'>{user['emoji']} {user['name']}님 반가워요!</h2>", unsafe_allow_html=True)
    if st.button("❮ 가족 바꾸기", key="logout"):
        st.session_state['user_id'] = None; st.rerun()

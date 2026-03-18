import streamlit as st
from datetime import datetime

# --- 1. 디자인 고정 (화이트 배경 카드 & 한 줄 배치) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    
    /* 화면 전체 너비를 넉넉하게 사용 */
    .main .block-container { 
        max-width: 1000px !important; 
        padding-top: 3rem !important; 
    }

    /* [핵심] 버튼을 화이트 카드 디자인으로 개조 */
    div.stButton > button {
        background-color: white !important;
        border: 1px solid #e5e8eb !important;
        border-radius: 20px !important;
        color: #191f28 !important;
        transition: all 0.2s ease-in-out !important;
        width: 100% !important;
        display: block !important;
        white-space: pre-line !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.02) !important;
    }

    /* 1. 프로필 카드: 한 줄(5열)에서도 큼직한 높이 유지 */
    div.stButton > button[key^="sel_"] {
        height: 170px !important; /* 높이 시원하게 확대 */
        min-width: 120px !important; 
        font-size: 18px !important;
        font-weight: 700 !important;
        line-height: 1.4 !important;
    }

    /* 이모지(아이콘) 크기: 카드 안에서 주인공처럼 크게 */
    div.stButton > button[key^="sel_"] p {
        font-size: 60px !important; 
        margin-bottom: 10px !important;
        display: block !important;
    }

    /* 2. 일상 공유하기 배너: 화이트 톤 유지하며 포인트 컬러 */
    div.stButton > button[key="go_sns_tab"] {
        height: 100px !important;
        background-color: white !important;
        border: 1px solid #e5e8eb !important;
        text-align: left !important;
        padding-left: 30px !important;
        font-size: 18px !important;
        margin-top: 40px !important;
    }

    /* 호버 효과: 살짝 커지면서 파란색 테두리 */
    div.stButton > button:hover {
        border-color: #3182f6 !important;
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.05) !important;
    }

    .main-title { color: #191f28; text-align: center; font-size: 28px; margin-bottom: 40px; font-weight: 700; }
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
    cols = st.columns(5, gap="medium")
    for i, m in enumerate(family_members):
        with cols[i]:
            # 화이트 배경 버튼에 이모지와 이름 출력
            if st.button(f"{m['emoji']}\n{m['name']}", key=f"sel_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 하단 일상 공유하기 배너 (화이트 카드 스타일)
    sns_label = "📸   일상 공유하기\n\n오늘 가족들에게 하고 싶은 말이 있나요?       ❯"
    if st.button(sns_label, key="go_sns_tab"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

# --- 4. 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    if st.button("❮ 홈으로 돌아가기", key="back_home"):
        st.session_state['current_page'] = 'Home'; st.rerun()
    st.markdown("<h1>📸 가족 게시판</h1>", unsafe_allow_html=True)
else:
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.markdown(f"<h1 style='text-align:center;'>{user['emoji']} {user['name']}님 반가워요!</h1>", unsafe_allow_html=True)
    if st.button("❮ 가족 바꾸기", key="logout"):
        st.session_state['user_id'] = None; st.rerun()

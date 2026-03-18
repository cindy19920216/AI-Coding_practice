import streamlit as st
from datetime import datetime

# --- 1. 디자인 고정 (2열 격자 & 화이트 카드 & 클릭 최적화) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    
    /* 모바일 가로폭에 맞춰 컨테이너 최적화 */
    .main .block-container { 
        max-width: 500px !important; 
        padding-left: 1.5rem !important; 
        padding-right: 1.5rem !important; 
        padding-top: 2rem !important; 
    }

    /* 버튼을 큼직한 화이트 카드로 변신 */
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
        padding: 20px 10px !important;
    }

    /* 프로필 카드 전용 스타일 (높이 및 폰트) */
    div.stButton > button[key^="sel_"] {
        height: 150px !important;
        margin-bottom: 15px !important;
    }

    /* 이모지 크기 확대 */
    div.stButton > button[key^="sel_"] p {
        font-size: 50px !important; 
        margin-bottom: 8px !important;
        display: block !important;
    }

    /* 이름 폰트 스타일 */
    div.stButton > button[key^="sel_"] {
        font-size: 18px !important;
        font-weight: 700 !important;
    }

    /* 하단 일상 공유하기 배너 스타일 */
    div.stButton > button[key="go_sns_tab"] {
        height: 100px !important;
        text-align: left !important;
        padding-left: 25px !important;
        margin-top: 10px !important;
        background: white !important;
    }

    div.stButton > button:hover {
        border-color: #3182f6 !important;
        transform: translateY(-5px);
        background-color: #F9FAFB !important;
    }

    .main-title { color: #191f28; text-align: center; font-size: 26px; margin-bottom: 30px; font-weight: 700; }
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
    
    # [격자 배치 로직]
    # 1행: 찬희, 지우
    row1 = st.columns(2, gap="medium")
    for i in range(2):
        m = family_members[i]
        with row1[i]:
            if st.button(f"{m['emoji']}\n{m['name']}", key=f"sel_{m['id']}"):
                st.session_state['user_id'] = m['id']; st.rerun()

    # 2행: 재선, 규비
    row2 = st.columns(2, gap="medium")
    for i in range(2, 4):
        m = family_members[i]
        with row2[i-2]:
            if st.button(f"{m['emoji']}\n{m['name']}", key=f"sel_{m['id']}"):
                st.session_state['user_id'] = m['id']; st.rerun()

    # 3행: 승규 (가운데 정렬을 위해 3분할 중 가운데 사용)
    row3 = st.columns([1, 2, 1], gap="medium")
    with row3[1]:
        m = family_members[4]
        if st.button(f"{m['emoji']}\n{m['name']}", key=f"sel_{m['id']}"):
            st.session_state['user_id'] = m['id']; st.rerun()

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
    st.title("📸 가족 게시판")
else:
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.markdown(f"<h2 style='text-align:center;'>{user['emoji']} {user['name']}님 반가워요!</h2>", unsafe_allow_html=True)
    if st.button("❮ 가족 바꾸기", key="logout"):
        st.session_state['user_id'] = None; st.rerun()

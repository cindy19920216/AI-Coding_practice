import streamlit as st

# --- 1. 디자인 고도화 (버튼 크기 강제 고정) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #0F1117; }
    
    /* 모바일 화면에서도 여백 없이 꽉 차게 */
    .main .block-container { 
        max-width: 600px !important; 
        padding: 2rem 1rem !important; 
    }

    /* 프로필 카드 크기 강제 고정 (픽셀 단위로 크게 설정) */
    div.stButton > button[key^="sel_"] {
        min-height: 160px !important; /* 높이 고정 */
        min-width: 140px !important;  /* 너비 고정 */
        background-color: #1F1F1F !important;
        color: white !important;
        border: 2px solid transparent !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        white-space: pre-line !important;
        line-height: 1.2 !important;
        transition: all 0.2s ease-in-out !important;
        margin: 5px auto !important;
    }

    /* 이모지 아이콘 크기를 왕창 키움 (가장 중요) */
    div.stButton > button[key^="sel_"] p {
        font-size: 70px !important; 
        margin-bottom: 5px !important;
        display: block !important;
    }

    div.stButton > button[key^="sel_"]:hover {
        border-color: white !important;
        transform: scale(1.08);
        background-color: #2F2F2F !important;
    }

    /* 하단 일상 공유 배너 크기 확대 */
    div.stButton > button[key="go_sns_tab"] {
        min-height: 100px !important;
        background: linear-gradient(90deg, #3182f6, #4d94f7) !important;
        color: white !important;
        border: none !important;
        border-radius: 18px !important;
        text-align: left !important;
        padding-left: 25px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        margin-top: 40px !important;
        width: 100% !important;
    }

    .main-title { color: white; text-align: center; font-size: 26px; margin-bottom: 40px; font-weight: 700; }
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
    
    # 1행 (3인): 화면 가로폭에 맞춰 큼직하게 배치
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(f"{family_members[0]['emoji']}\n{family_members[0]['name']}", key=f"sel_{family_members[0]['id']}"):
            st.session_state['user_id'] = family_members[0]['id']; st.rerun()
    with c2:
        if st.button(f"{family_members[1]['emoji']}\n{family_members[1]['name']}", key=f"sel_{family_members[1]['id']}"):
            st.session_state['user_id'] = family_members[1]['id']; st.rerun()
    with c3:
        if st.button(f"{family_members[2]['emoji']}\n{family_members[2]['name']}", key=f"sel_{family_members[2]['id']}"):
            st.session_state['user_id'] = family_members[2]['id']; st.rerun()

    # 2행 (2인): 가운데 정렬을 위해 1:2:2:1 비율 사용
    st.write("") 
    r2_c1, r2_c2, r2_c3, r2_c4 = st.columns([1, 2.5, 2.5, 1])
    with r2_c2:
        if st.button(f"{family_members[3]['emoji']}\n{family_members[3]['name']}", key=f"sel_{family_members[3]['id']}"):
            st.session_state['user_id'] = family_members[3]['id']; st.rerun()
    with r2_c3:
        if st.button(f"{family_members[4]['emoji']}\n{family_members[4]['name']}", key=f"sel_{family_members[4]['id']}"):
            st.session_state['user_id'] = family_members[4]['id']; st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 일상 공유하기 배너
    if st.button("📸  일상 공유하기\n우리 가족 소식 보러가기  ❯", key="go_sns_tab"):
        st.session_state['current_page'] = 'FamilySNS'; st.rerun()

# --- 4. 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    if st.button("❮ 홈으로", key="back_home"):
        st.session_state['current_page'] = 'Home'; st.rerun()
    st.title("📸 가족 게시판")
else:
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.markdown(f"<h2 style='color:white; text-align:center;'>{user['emoji']} {user['name']}님 반가워요!</h2>", unsafe_allow_html=True)
    if st.button("❮ 가족 바꾸기", key="logout"):
        st.session_state['user_id'] = None; st.rerun()

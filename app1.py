import streamlit as st
from datetime import datetime

st.markdown("""
    <style>
    /* 1. 컨테이너 너비를 모바일 가로폭에 딱 맞춤 */
    .main .block-container { 
        max-width: 500px !important; 
        padding-left: 1.5rem !important; 
        padding-right: 1.5rem !important; 
    }

    /* 2. 버튼을 가로로 꽉 차는 와이드 카드로 변경 */
    div.stButton > button[key^="sel_"] {
        height: 100px !important; /* 높이는 적당히 유지 */
        width: 100% !important;   /* 가로폭을 100%로 꽉 채움 */
        display: flex !important;
        flex-direction: row !important; /* 이모지와 이름을 가로로 배치 */
        align-items: center !important;
        justify-content: flex-start !important; /* 왼쪽 정렬 */
        padding-left: 25px !important;
        margin-bottom: 12px !important;
    }

    /* 3. 이모지 크기 및 간격 조정 */
    div.stButton > button[key^="sel_"] p {
        font-size: 35px !important; 
        margin-right: 20px !important;
        margin-bottom: 0px !important;
    }
    
    /* 4. 이름 폰트 크기 확대 */
    div.stButton > button[key^="sel_"] {
        font-size: 20px !important;
    }
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

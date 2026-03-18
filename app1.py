import streamlit as st
from datetime import datetime

# --- 1. 디자인 고정 (와이드 카드 & 게시판 디자인 통합) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    
    /* 1. 컨테이너 너비를 모바일 가로폭에 딱 맞춤 */
    .main .block-container { 
        max-width: 500px !important; 
        padding-left: 1.5rem !important; 
        padding-right: 1.5rem !important; 
        padding-top: 2rem !important;
    }

    /* 2. 메인 버튼: 가로로 꽉 차는 와이드 카드 디자인 */
    div.stButton > button[key^="sel_"] {
        height: 100px !important;
        width: 100% !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: flex-start !important;
        padding-left: 25px !important;
        margin-bottom: 12px !important;
        background-color: white !important;
        border: 1px solid #e5e8eb !important;
        border-radius: 20px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.02) !important;
    }

    /* 이모지 및 이름 폰트 제어 */
    div.stButton > button[key^="sel_"] p {
        font-size: 35px !important; 
        margin-right: 20px !important;
        margin-bottom: 0px !important;
    }
    div.stButton > button[key^="sel_"] { font-size: 20px !important; font-weight: 700 !important; color: #191f28 !important; }

    /* 하단 일상 공유 배너 전용 */
    div.stButton > button[key="go_sns_tab"] {
        height: 120px !important;
        width: 100% !important;
        border-radius: 20px !important;
        background-color: white !important;
        border: 1px solid #e5e8eb !important;
        text-align: left !important;
        padding-left: 25px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
    }

    /* 게시판 말풍선 버튼 스타일 (카톡 노란색) */
    div.stButton > button[key^="bubble_"] {
        background-color: #fef01b !important;
        border: none !important;
        border-radius: 15px !important;
        color: #371d1e !important;
        font-weight: 700 !important;
        padding: 8px 15px !important;
        width: auto !important;
    }

    /* 입력 중 강조 레이블 (SAYS...) */
    .active-bubble-label {
        background-color: #3182f6; color: white; padding: 5px 12px;
        border-radius: 8px; font-size: 12px; font-weight: 700;
        margin-bottom: 5px; display: inline-block;
    }

    /* 피드 카드 디자인 */
    .feed-card {
        background: white; padding: 15px; border-radius: 18px;
        margin-bottom: 12px; border: 1px solid #e5e8eb;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    
    div.stButton > button:hover { border-color: #3182f6 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 데이터 및 세션 관리 ---
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'current_page' not in st.session_state: st.session_state['current_page'] = 'Home'
if 'family_feed' not in st.session_state: st.session_state['family_feed'] = []
if 'speaking_id' not in st.session_state: st.session_state['speaking_id'] = None

family_members = [
    {"id": "chanhee", "name": "찬희", "emoji": "👨🏻‍💻"},
    {"id": "jiwoo", "name": "지우", "emoji": "👩🏻‍💼"},
    {"id": "jaeseon", "name": "재선", "emoji": "👩🏻‍🎨"},
    {"id": "gyubi", "name": "규비", "emoji": "👧🏻"},
    {"id": "seunggyu", "name": "승규", "emoji": "👦🏻"}
]

# --- 3. 화면 구현 함수 ---

# [화면 1] 로그인/프로필 선택 (와이드 카드 리스트)
def show_login_screen():
    st.markdown("<h1 style='text-align: center; color: #191f28; font-size: 26px; margin-bottom: 25px;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    
    # 5명 세로 와이드 리스트 배치
    for m in family_members:
        if st.button(f"{m['emoji']}  {m['name']}", key=f"sel_{m['id']}"):
            st.session_state['user_id'] = m['id']
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 하단 일상 공유하기 배너
    sns_label = "📸   일상 공유하기\n\n오늘 가족들에게 하고 싶은 말이 있나요?       ❯"
    if st.button(sns_label, key="go_sns_tab"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

# [화면 2] 가족 게시판 (카톡 UX 스타일)
def show_sns_page():
    if st.button("❮ 홈으로 돌아가기", key="back_home"):
        st.session_state['current_page'] = 'Home'; st.session_state['speaking_id'] = None; st.rerun()
    
    st.markdown("<h2 style='margin-bottom:10px;'>📸 가족 게시판</h2>", unsafe_allow_html=True)
    st.write("말풍선을 클릭하여 소식을 남겨보세요.")

    # 1) 가족 나열 및 개별 말풍선 버튼
    for m in family_members:
        col_name, col_bubble = st.columns([1.5, 3])
        with col_name:
            st.markdown(f"<div style='font-size:18px; font-weight:700; padding-top:10px;'>{m['emoji']} {m['name']}</div>", unsafe_allow_html=True)
        with col_bubble:
            if st.button("이야기하기 💬", key=f"bubble_{m['id']}"):
                st.session_state['speaking_id'] = m['id']
                st.rerun()

        # 2) 특정 인물 클릭 시 해당 위치에만 입력창 오픈 (UX 깔끔 유지)
        if st.session_state['speaking_id'] == m['id']:
            st.markdown(f"<div class='active-bubble-label'>{m['name']} SAYS...</div>", unsafe_allow_html=True)
            with st.form(key=f"form_{m['id']}", clear_on_submit=True):
                msg = st.text_input("메시지 입력", placeholder="오늘 어떤 일이 있었나요?", label_visibility="collapsed")
                if st.form_submit_button("가족과 공유"):
                    if msg:
                        # 3) 입력 즉시 하단 피드 업데이트 (시간 포함)
                        time_now = datetime.now().strftime("%H:%M")
                        st.session_state['family_feed'].insert(0, {"name": m['name'], "emoji": m['emoji'], "msg": msg, "time": time_now})
                        st.session_state['speaking_id'] = None
                        st.rerun()
        st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("💬 실시간 가족 피드")
    if st.session_state['family_feed']:
        for post in st.session_state['family_feed'][:10]:
            st.markdown(f"""
                <div class="feed-card">
                    <span style="font-weight:700;">{post['emoji']} {post['name']}</span>
                    <span style="float:right; color:#8b95a1; font-size:12px;">{post['time']}</span>
                    <div style="margin-top:8px; color:#191f28;">{post['msg']}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("아직 소식이 없어요. 첫 글을 남겨보세요!")

# --- 4. 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    show_sns_page()
else:
    # 로그인 후 홈화면
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.markdown(f"<h1 style='text-align:center;'>{user['emoji']} {user['name']}님 반가워요!</h1>", unsafe_allow_html=True)
    if st.button("❮ 가족 바꾸기", key="logout"):
        st.session_state['user_id'] = None; st.rerun()

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. 전용 디자인 (전문가님 맞춤형 사이즈 & 클릭 최적화) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    
    /* 모바일 최적화 컨테이너 */
    .main .block-container { max-width: 600px; padding-top: 2rem; }

    /* 핵심: 모든 버튼을 전문가님이 원하시는 '화이트 카드' 디자인으로 개조 */
    div.stButton > button {
        background-color: white !important;
        border: 1px solid #e5e8eb !important;
        border-radius: 20px !important;
        color: #191f28 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.02) !important;
        transition: all 0.2s ease-in-out !important;
        width: 100% !important;
        display: block !important;
        white-space: pre-line !important; /* 줄바꿈 허용 */
    }

    /* 1. 프로필 카드 사이즈 고정 */
    div.stButton > button[key^="sel_"] {
        height: 140px !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        text-align: center !important;
        line-height: 1.5 !important;
    }

    /* 2. 일상 공유하기 배너 사이즈 고정 */
    div.stButton > button[key="go_sns_tab"] {
        height: 90px !important;
        text-align: left !important;
        padding-left: 20px !important;
        font-size: 16px !important;
        margin-top: 15px !important;
    }

    div.stButton > button:hover {
        border-color: #3182f6 !important;
        transform: translateY(-3px);
        background-color: #F9FAFB !important;
    }

    /* 말풍선 & 피드 스타일 */
    .active-bubble { background-color: #3182f6; color: white; border-radius: 12px; padding: 12px; margin: 10px 0; font-weight: 600; text-align: center; }
    .feed-item { background: white; padding: 15px; border-radius: 15px; margin-bottom: 10px; border: 1px solid #e5e8eb; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 및 세션 초기화 ---
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

# --- 3. 화면 구현 함수 ---

def show_login_screen():
    st.markdown("<h2 style='text-align: center; color: #191f28; margin-top: 10px;'>누가 오셨나요?</h2>", unsafe_allow_html=True)
    
    # 전문가님이 원하시던 5인 카드 배열
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            # HTML 대신 줄바꿈(\n)을 쓴 텍스트를 버튼 라벨로 사용
            label = f"{m['emoji']}\n\n{m['name']}\n{m['role']}"
            if st.button(label, key=f"sel_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 일상 공유하기 탭 (디자인과 버튼을 하나로 합침)
    sns_label = "📸  일상 공유하기\n우리 가족 소식 보러가기       ❯"
    if st.button(sns_label, key="go_sns_tab"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

def show_sns_page():
    if st.button("❮ 홈으로", key="back_home"):
        st.session_state['current_page'] = 'Home'; st.session_state['speaking_id'] = None; st.rerun()
    
    st.title("📸 가족 게시판")
    
    for m in family_members:
        with st.container():
            col_name, col_bubble = st.columns([1, 4])
            with col_name:
                st.markdown(f"<div style='margin-top:10px; font-weight:700;'>{m['emoji']} {m['name']}</div>", unsafe_allow_html=True)
            with col_bubble:
                # 게시판 안의 말풍선 버튼도 카드 스타일 적용
                if st.button(f"{m['name']} SAYS... 💬", key=f"bubble_{m['id']}"):
                    st.session_state['speaking_id'] = m['id']
                    st.rerun()

        if st.session_state['speaking_id'] == m['id']:
            st.markdown(f'<div class="active-bubble">{m["name"]}님이 입력 중...</div>', unsafe_allow_html=True)
            with st.form(key=f"form_{m['id']}", clear_on_submit=True):
                msg = st.text_input("메시지 입력", placeholder="이야기를 들려주세요", label_visibility="collapsed")
                if st.form_submit_button("가족과 공유"):
                    if msg:
                        time_now = datetime.now().strftime("%H:%M")
                        st.session_state['family_feed'].insert(0, f"[{time_now}] {m['emoji']} {m['name']}: {msg}")
                        st.session_state['speaking_id'] = None
                        st.rerun()

    st.markdown("---")
    for post in st.session_state['family_feed'][:10]:
        st.markdown(f'<div class="feed-item">{post}</div>', unsafe_allow_html=True)

# --- 4. 메인 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    show_sns_page()
else:
    # 로그인 후 홈화면
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.header(f"📈 {user['name']}님 반가워요!")
    if st.button("❮ 가족 바꾸기", key="logout"): 
        st.session_state['user_id'] = None; st.rerun()

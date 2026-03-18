import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. 전용 디자인 (클릭 영역 완전 통합 CSS) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    .main .block-container { max-width: 600px; padding-top: 2rem; }

    /* 핵심: Streamlit 버튼 자체를 카드 디자인으로 개조 */
    /* 1. 프로필 버튼 (5개 나열) */
    div.stButton > button[key^="sel_"] {
        height: 140px !important;
        background-color: white !important;
        border: 1px solid #e5e8eb !important;
        border-radius: 20px !important;
        padding: 0 !important;
        display: block !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.02) !important;
        transition: all 0.2s;
    }

    /* 2. 일상 공유하기 와이드 탭 버튼 */
    div.stButton > button[key="go_sns_tab"] {
        height: 100px !important;
        background-color: white !important;
        border: 1px solid #e5e8eb !important;
        border-radius: 20px !important;
        padding: 0 !important;
        width: 100% !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03) !important;
        margin-top: 10px !important;
        display: block !important;
    }

    /* 버튼 안의 HTML 레이아웃 정렬 */
    .card-content {
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        height: 100%; width: 100%;
    }
    .sns-content {
        display: flex; align-items: center; padding: 20px;
        height: 100%; width: 100%; text-align: left;
    }

    div.stButton > button:hover {
        border-color: #3182f6 !important;
        transform: translateY(-3px);
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

# --- 3. 화면 구현 ---

def show_login_screen():
    st.markdown("<h1 style='text-align: center; color: #191f28; margin-top: 30px;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    
    # 1. 5인 프로필 디자인 고정 + 클릭 보장
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            # 버튼의 label 안에 HTML 디자인을 직접 삽입
            profile_html = f"""
                <div class="card-content">
                    <div style="font-size: 35px; margin-bottom: 5px;">{m['emoji']}</div>
                    <div style="font-size: 15px; font-weight: 700; color: #191f28;">{m['name']}</div>
                    <div style="font-size: 11px; color: #8b95a1;">{m['role']}</div>
                </div>
            """
            if st.button(profile_html, key=f"sel_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. 일상 공유하기 탭 디자인 고정 + 클릭 보장
    sns_html = """
        <div class="sns-content">
            <div style="font-size: 24px; margin-right: 15px;">📸</div>
            <div style="flex-grow:1;">
                <div style="font-size: 16px; font-weight: 700; color: #191f28;">일상 공유하기</div>
                <div style="font-size: 13px; color: #8b95a1;">오늘 가족들에게 하고 싶은 말이 있나요?</div>
            </div>
            <div style="color: #B0B8C1; font-weight: bold;">❯</div>
        </div>
    """
    if st.button(sns_html, key="go_sns_tab"):
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
                if st.button(f"{m['name']} SAYS... 💬", key=f"bubble_{m['id']}", use_container_width=True):
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
    # 로그인 후 홈화면 (주식 등)
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.header(f"📈 {user['name']}님 반가워요!")
    if st.button("❮ 가족 바꾸기", key="logout"): 
        st.session_state['user_id'] = None; st.rerun()

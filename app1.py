import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. 디자인 및 스타일 (가로폭 꽉 채우기 & 클릭 최적화) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    
    /* 모바일 중심 컨테이너 (너비를 500px로 조여서 앱처럼 보이게 함) */
    .main .block-container { max-width: 500px; padding-top: 2rem; padding-bottom: 2rem; }

    /* 넷플릭스 스타일 프로필 버튼 커스텀 */
    div.stButton > button {
        width: 100% !important;
        background-color: white !important;
        border: 1px solid #e5e8eb !important;
        border-radius: 20px !important;
        aspect-ratio: 1 / 1.2; /* 세로로 약간 긴 직사각형 고정 */
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.02) !important;
        transition: all 0.2s ease-in-out !important;
        white-space: pre-line !important; /* 줄바꿈 허용 */
        line-height: 1.4 !important;
    }
    div.stButton > button:hover {
        border-color: #3182f6 !important;
        background-color: #f9fafb !important;
        transform: translateY(-5px);
    }

    /* 일상 공유하기 와이드 버튼 (가로로 꽉 차게) */
    div.stButton > button[key="btn_go_sns"] {
        aspect-ratio: auto !important; /* 고정 비율 해제 */
        height: 100px !important;
        padding: 20px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        text-align: left !important;
        margin-top: 20px !important;
        display: flex !important;
        align-items: center !important;
    }

    /* 말풍선 및 피드 스타일 */
    .bubble-box {
        background-color: #3182f6; color: white; border-radius: 15px;
        padding: 15px; margin-top: 20px; position: relative; font-weight: bold; text-align: center;
    }
    .bubble-box::after {
        content: ''; position: absolute; bottom: 100%; left: 50%;
        border-width: 10px; border-style: solid;
        border-color: transparent transparent #3182f6 transparent;
        transform: translateX(-50%);
    }
    .feed-item {
        background: white; padding: 18px; border-radius: 18px; 
        margin-bottom: 12px; border: 1px solid #e5e8eb;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 및 세션 관리 ---
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'current_page' not in st.session_state: st.session_state['current_page'] = 'Home'
if 'temp_messages' not in st.session_state: st.session_state['temp_messages'] = []
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
    st.markdown("<h1 style='text-align: center; margin-bottom: 30px;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    
    # 1. 넷플릭스 프로필 (5개 컬럼 활용하여 꽉 채움)
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            # 버튼 텍스트에 이모티콘과 이름을 크게 배치
            # 이모티콘 크기를 더 키우고 싶다면 CSS에서 조정 가능
            if st.button(f"{m['emoji']}\n{m['name']}", key=f"login_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()

    # 2. 일상 공유하기 와이드 탭 (가로폭 100% 연결)
    if st.button("📸  일상 공유하기          ❯", key="btn_go_sns"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

def show_sns_page():
    if st.button("❮ 홈으로 돌아가기", key="back_btn"):
        st.session_state['current_page'] = 'Home'
        st.session_state['speaking_id'] = None
        st.rerun()

    st.title("📸 가족 게시판")
    
    # 이모티콘 버튼 행
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            if st.button(f"{m['emoji']}\n{m['name']}", key=f"emoji_{m['id']}"):
                st.session_state['speaking_id'] = m['id']
                st.rerun()

    # 말풍선 타이핑
    if st.session_state['speaking_id']:
        spk = next(m for m in family_members if m['id'] == st.session_state['speaking_id'])
        st.markdown(f'<div class="bubble-box">{spk["name"]} SAYS...</div>', unsafe_allow_html=True)
        
        with st.form(key="msg_form", clear_on_submit=True):
            user_msg = st.text_input("메시지", placeholder="이야기를 입력하세요", label_visibility="collapsed")
            if st.form_submit_button("전송하기") and user_msg:
                time_str = datetime.now().strftime("%m/%d %H:%M")
                st.session_state['temp_messages'].insert(0, {
                    "time": time_str, 
                    "name": spk['name'], 
                    "emoji": spk['emoji'], 
                    "msg": user_msg
                })
                st.session_state['speaking_id'] = None
                st.rerun()

    # 피드 출력
    st.markdown("---")
    for m in st.session_state['temp_messages'][:10]:
        st.markdown(f"""
            <div class="feed-item">
                <b>{m['emoji']} {m['name']}</b> <span style="float:right; color:#8b95a1; font-size:12px;">{m['time']}</span><br>
                <div style="margin-top:8px;">{m['msg']}</div>
            </div>
        """, unsafe_allow_html=True)

# --- 4. 메인 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    show_sns_page()
else:
    # 홈화면 (주식 분석 연결부)
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.title(f"{user['name']}님 반가워요!")
    if st.button("❮ 가족 바꾸기", key="logout"): 
        st.session_state['user_id'] = None
        st.rerun()

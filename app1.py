import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. 디자인 및 스타일 (가독성 & 클릭 최적화) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    
    /* 모바일 중심 컨테이너 (600px) */
    .main .block-container { max-width: 600px; padding-top: 2rem; padding-bottom: 2rem; }

    /* 넷플릭스 스타일 프로필 버튼 커스텀 */
    div.stButton > button[key^="p_"] {
        background-color: white; border-radius: 20px; border: 1px solid #e5e8eb;
        height: 150px; width: 100%; display: flex; flex-direction: column;
        align-items: center; justify-content: center; font-size: 16px; font-weight: 700;
        box-shadow: 0 4px 10px rgba(0,0,0,0.02); transition: all 0.2s;
    }
    div.stButton > button[key^="p_"]:hover { border-color: #3182f6; transform: translateY(-5px); background-color: #f9fafb; }

    /* 일상 공유하기 와이드 버튼 커스텀 */
    div.stButton > button[key="sns_wide_btn"] {
        background-color: white; border-radius: 24px; border: 1px solid #e5e8eb;
        padding: 25px; width: 100%; text-align: left; font-size: 18px; font-weight: 700;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-top: 20px; display: block;
    }
    div.stButton > button[key="sns_wide_btn"]:hover { border-color: #3182f6; background-color: #f9fafb; }

    /* 말풍선 스타일 */
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

    /* 피드 아이템 */
    .feed-item {
        background: white; padding: 18px; border-radius: 18px; 
        margin-bottom: 12px; border: 1px solid #e5e8eb;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 및 세션 관리 ---
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'current_page' not in st.session_state: st.session_state['current_page'] = 'Home'
if 'speaking_id' not in st.session_state: st.session_state['speaking_id'] = None
if 'family_feed' not in st.session_state: st.session_state['family_feed'] = []

family_members = [
    {"id": "chanhee", "name": "찬희", "role": "아빠", "emoji": "👨🏻‍💻"},
    {"id": "jiwoo", "name": "지우", "role": "엄마", "emoji": "👩🏻‍💼"},
    {"id": "jaeseon", "name": "재선", "role": "큰딸", "emoji": "👩🏻‍🎨"},
    {"id": "gyubi", "name": "규비", "role": "작은딸", "emoji": "👧🏻"},
    {"id": "seunggyu", "name": "승규", "role": "막내", "emoji": "👦🏻"}
]

# --- 3. 화면 구현 ---

def show_login_screen():
    st.markdown("<h1 style='text-align: center; color: #191f28;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b95a1; margin-bottom: 40px;'>가족 금융 매니저</p>", unsafe_allow_html=True)
    
    # 1. 큼직한 넷플릭스 프로필 (5개 행)
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            # 버튼 텍스트에 이모티콘과 이름을 줄바꿈으로 넣음
            if st.button(f"{m['emoji']}\n\n{m['name']}", key=f"p_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. 일상 공유하기 와이드 탭 (가로폭 100% 버튼)
    if st.button("📸  일상 공유하기                          ❯", key="sns_wide_btn"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

def show_sns_page():
    if st.button("❮ 홈으로 돌아가기", key="back_home"):
        st.session_state['current_page'] = 'Home'; st.session_state['speaking_id'] = None; st.rerun()
    
    st.title("📸 가족 게시판")
    
    # 이모티콘 + 이름 행 나열 (디자인 버튼 활용)
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            if st.button(f"{m['emoji']}\n{m['name']}", key=f"s_{m['id']}"):
                st.session_state['speaking_id'] = m['id']
                st.rerun()

    # 말풍선 타이핑 영역
    if st.session_state['speaking_id']:
        speaker = next(m for m in family_members if m['id'] == st.session_state['speaking_id'])
        st.markdown(f'<div class="bubble-box">{speaker["name"]} SAYS...</div>', unsafe_allow_html=True)
        
        with st.form(key="msg_input", clear_on_submit=True):
            msg = st.text_input("메시지", placeholder="이야기를 들려주세요", label_visibility="collapsed")
            if st.form_submit_button("가족들과 공유하기") and msg:
                new_post = {
                    "time": datetime.now().strftime("%m/%d %H:%M"),
                    "name": speaker['name'],
                    "emoji": speaker['emoji'],
                    "msg": msg
                }
                st.session_state['family_feed'].insert(0, new_post)
                st.session_state['speaking_id'] = None
                st.rerun()

    # 피드 출력
    st.markdown("---")
    for post in st.session_state['family_feed'][:10]:
        st.markdown(f"""
            <div class="feed-item">
                <b>{post['emoji']} {post['name']}</b> <span style="float:right; color:#8b95a1; font-size:12px;">{post['time']}</span><br>
                <div style="margin-top:8px;">{post['msg']}</div>
            </div>
        """, unsafe_allow_html=True)

# --- 4. 메인 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    show_sns_page()
else:
    # 로그인 후 홈화면 (주식 분석 대시보드 연결부)
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.title(f"{user['name']}님, 안녕하세요!")
    if st.button("❮ 가족 바꾸기 (로그아웃)", key="logout_btn"):
        st.session_state['user_id'] = None
        st.rerun()

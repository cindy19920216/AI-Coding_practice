import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. 디자인 및 스타일 (클릭 영역 완전 고정) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    .main .block-container { max-width: 500px; padding-top: 2rem; }

    /* 넷플릭스 스타일 프로필 버튼 */
    .stButton>button.profile-btn {
        background-color: white; border-radius: 20px; border: 1px solid #e5e8eb;
        height: 140px; width: 100%; display: flex; flex-direction: column;
        align-items: center; justify-content: center; transition: all 0.2s;
    }
    .stButton>button.profile-btn:hover { border-color: #3182f6; transform: translateY(-5px); }

    /* 일상 공유 와이드 버튼 (디자인과 버튼 통합) */
    .stButton>button.sns-btn {
        background-color: white; border-radius: 20px; border: 1px solid #e5e8eb;
        padding: 20px; width: 100%; height: auto; display: flex;
        justify-content: flex-start; align-items: center; margin-top: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    .stButton>button.sns-btn:hover { background-color: #f9fafb; border-color: #3182f6; }

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
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 및 세션 관리 ---
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'current_page' not in st.session_state: st.session_state['current_page'] = 'Home'
if 'speaking_id' not in st.session_state: st.session_state['speaking_id'] = None
# 영구 저장을 위해 CSV 파일이 있다면 읽어오고, 없다면 세션에 저장 (Supabase 연결 전 단계)
if 'family_feed' not in st.session_state: st.session_state['family_feed'] = []

family_members = [
    {"id": "chanhee", "name": "찬희", "role": "아빠", "emoji": "👨🏻‍💻"},
    {"id": "jiwoo", "name": "지우", "role": "엄마", "emoji": "👩🏻‍💼"},
    {"id": "jaeseon", "name": "재선", "role": "큰딸", "emoji": "👩🏻‍🎨"},
    {"id": "gyubi", "name": "규비", "role": "작은딸", "emoji": "👧🏻"},
    {"id": "seunggyu", "name": "승규", "role": "막내", "emoji": "👦🏻"}
]

# --- 3. 화면 구현 함수 ---

def show_login_screen():
    st.markdown("<h2 style='text-align: center;'>누가 오셨나요?</h2><br>", unsafe_allow_html=True)
    
    # 1. 큼직한 넷플릭스 프로필 (5개 행 나열)
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            # 버튼에 클래스 부여 (CSS 연동)
            if st.button(f"{m['emoji']}\n\n{m['name']}", key=f"p_{m['id']}", help=m['role']):
                st.session_state['user_id'] = m['id']
                st.rerun()

    # 2. 일상 공유하기 와이드 탭 (가로폭 100% 버튼)
    st.write("") # 간격
    if st.button("📸  일상 공유하기           ❯", key="sns_wide_btn"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

def show_sns_page():
    col_back, _ = st.columns([2, 8])
    with col_back:
        if st.button("❮ 홈"):
            st.session_state['current_page'] = 'Home'
            st.rerun()
    
    st.title("📸 가족 게시판")
    
    # 이모티콘 + 이름 행 나열
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            if st.button(f"{m['emoji']}\n{m['name']}", key=f"sns_{m['id']}"):
                st.session_state['speaking_id'] = m['id']
                st.rerun()

    # 말풍선 타이핑 및 실시간 피드 저장
    if st.session_state['speaking_id']:
        speaker = next(m for m in family_members if m['id'] == st.session_state['speaking_id'])
        st.markdown(f'<div class="bubble-box">{speaker["name"]} SAYS...</div>', unsafe_allow_html=True)
        
        with st.form(key="msg_input", clear_on_submit=True):
            msg = st.text_input("메시지", placeholder="여기에 내용을 입력하세요", label_visibility="collapsed")
            if st.form_submit_button("가족들과 공유하기") and msg:
                new_post = {"time": datetime.now().strftime("%m/%d %H:%M"), "name": speaker['name'], "emoji": speaker['emoji'], "msg": msg}
                st.session_state['family_feed'].insert(0, new_post)
                st.session_state['speaking_id'] = None
                st.rerun()

    # 피드 출력
    st.markdown("---")
    for post in st.session_state['family_feed'][:10]:
        st.markdown(f"""
            <div style="background:white; padding:15px; border-radius:15px; margin-bottom:10px; border:1px solid #e5e8eb;">
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
    # 홈화면 (로그인 후)
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.title(f"{user['name']}님 반가워요!")
    if st.button("❮ 가족 바꾸기"):
        st.session_state['user_id'] = None
        st.rerun()

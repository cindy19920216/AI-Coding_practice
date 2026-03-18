import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. 전용 디자인 (클릭 영역 완전 고정 & 모바일 최적화) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    
    /* 모바일 중심 컨테이너 (최대 600px) */
    .main .block-container { max-width: 600px; padding-top: 2rem; padding-bottom: 2rem; }

    /* 클릭을 방해하는 기본 패딩 제거 */
    .element-container { margin-bottom: 0px; }

    /* 1) 넷플릭스 스타일 프로필 카드 */
    .profile-container {
        position: relative; background-color: white; border-radius: 20px; 
        padding: 25px 10px; text-align: center; border: 1px solid #e5e8eb;
        height: 160px; display: flex; flex-direction: column; align-items: center; justify-content: center;
    }
    .profile-emoji { font-size: 50px; display: block; margin-bottom: 5px; }
    .profile-name { font-size: 18px; font-weight: 700; color: #191f28; display: block; }
    .profile-role { font-size: 12px; color: #8b95a1; display: block; }

    /* 2) 일상 공유하기 와이드 탭 (클릭 영역 100% 확보) */
    .sns-container {
        position: relative; background-color: white; border-radius: 24px; 
        padding: 22px; display: flex; align-items: center; border: 1px solid #e5e8eb;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-top: 20px; width: 100%;
    }
    .sns-icon { font-size: 30px; margin-right: 18px; }
    .sns-title { font-size: 18px; font-weight: 700; color: #191f28; }
    .sns-desc { font-size: 14px; color: #8b95a1; }

    /* 핵심: 버튼을 카드 전체에 투명하게 덮기 */
    .stButton>button {
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background: transparent !important; border: none !important; color: transparent !important;
        z-index: 10; cursor: pointer;
    }
    .stButton>button:hover { background: rgba(49, 130, 246, 0.05) !important; }

    /* 말풍선 & 피드 스타일 */
    .bubble-box { background-color: #3182f6; color: white; border-radius: 15px; padding: 15px; margin-top: 20px; position: relative; font-weight: bold; text-align: center; }
    .bubble-box::after { content: ''; position: absolute; bottom: 100%; left: 50%; border: 10px solid transparent; border-bottom-color: #3182f6; transform: translateX(-50%); }
    .feed-item { background: white; padding: 18px; border-radius: 18px; margin-bottom: 12px; border: 1px solid #e5e8eb; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 관리 ---
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
    st.markdown("<h1 style='text-align: center;'>누가 오셨나요?</h1><br>", unsafe_allow_html=True)
    
    # 1. 큼직한 프로필 선택
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            # 카드 디자인 위에 투명 버튼 배치
            st.markdown(f"""
                <div class="profile-container">
                    <span class="profile-emoji">{m['emoji']}</span>
                    <span class="profile-name">{m['name']}</span>
                    <span class="profile-role">{m['role']}</span>
                </div>
            """, unsafe_allow_html=True)
            if st.button("", key=f"sel_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. 일상 공유하기 와이드 탭 (클릭 해결 버전)
    st.markdown(f"""
        <div class="sns-container">
            <div class="sns-icon">📸</div>
            <div style="flex-grow:1;">
                <div class="sns-title">일상 공유하기</div>
                <div class="sns-desc">오늘 우리 가족에게 하고 싶은 말이 있나요?</div>
            </div>
            <div style="color: #B0B8C1;">❯</div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("", key="go_sns_tab"): # 이 버튼이 위 카드를 100% 덮고 있음
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

def show_sns_page():
    if st.button("❮ 홈으로", key="back_home"):
        st.session_state['current_page'] = 'Home'; st.session_state['speaking_id'] = None; st.rerun()
    
    st.title("📸 가족 게시판")
    
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            # 버튼과 이름을 가깝게 배치하기 위해 CSS 간격 조정
            st.markdown(f"<div style='text-align:center; font-size:40px;'>{m['emoji']}</div>", unsafe_allow_html=True)
            if st.button(m['name'], key=f"btn_{m['id']}"):
                st.session_state['speaking_id'] = m['id']
                st.rerun()

    if st.session_state['speaking_id']:
        speaker = next(m for m in family_members if m['id'] == st.session_state['speaking_id'])
        st.markdown(f"<div class='bubble-box'>{speaker['name']} SAYS...</div>", unsafe_allow_html=True)
        
        with st.form(key="msg_form", clear_on_submit=True):
            user_msg = st.text_input("메시지", placeholder="이야기를 들려주세요", label_visibility="collapsed")
            if st.form_submit_button("가족들과 공유하기") and user_msg:
                new_post = {"time": datetime.now().strftime("%m/%d %H:%M"), "name": speaker['name'], "emoji": speaker['emoji'], "msg": user_msg}
                st.session_state['family_feed'].insert(0, new_post)
                st.session_state['speaking_id'] = None
                st.rerun()

    # 실시간 피드 출력
    st.markdown("---")
    for f in st.session_state['family_feed'][:10]:
        st.markdown(f"""<div class="feed-item"><b>{f['emoji']} {f['name']}</b> <span style="float:right; color:#8b95a1; font-size:12px;">{f['time']}</span><p style="margin-top:8px;">{f['msg']}</p></div>""", unsafe_allow_html=True)

# --- 4. 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    show_sns_page()
else:
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.title(f"{user['name']}님, 안녕하세요!")
    if st.button("❮ 가족 바꾸기"): st.session_state['user_id'] = None; st.rerun()

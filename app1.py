import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. 디자인 및 스타일 (위치 고정 & 말풍선 UI) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    
    /* 모바일 중심 컨테이너 (600px 고정) */
    .main .block-container { max-width: 600px; padding-top: 2rem; margin: 0 auto; }

    /* 일상 공유하기 탭 고정 디자인 */
    .sns-fixed-tab {
        background-color: white; border-radius: 20px; padding: 20px;
        display: flex; align-items: center; border: 1px solid #e5e8eb;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-bottom: 25px;
        width: 100%; height: 90px; /* 크기 고정 */
    }

    /* 가족 행 배열 스타일 */
    .family-row {
        display: flex; align-items: center; background: white; 
        padding: 15px; border-radius: 18px; margin-bottom: 10px;
        border: 1px solid #f2f4f6;
    }
    .family-name-tag { width: 60px; font-weight: 700; color: #191f28; font-size: 15px; }

    /* 말풍선 버튼 스타일 */
    div.stButton > button.bubble-btn {
        background-color: #F2F4F6 !important; border: none !important;
        border-radius: 12px !important; padding: 10px 15px !important;
        text-align: left !important; color: #4E5968 !important;
        width: 100% !important; height: auto !important;
    }
    div.stButton > button.bubble-btn:hover { background-color: #EBF4FF !important; color: #3182f6 !important; }

    /* 입력 중인 말풍선 강조 */
    .active-bubble {
        background-color: #3182f6; color: white; border-radius: 12px;
        padding: 12px; margin-top: 5px; font-weight: 600; font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 및 세션 관리 ---
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'current_page' not in st.session_state: st.session_state['current_page'] = 'Home'
if 'speaking_id' not in st.session_state: st.session_state['speaking_id'] = None # 누구의 말풍선을 눌렀나
if 'family_feed' not in st.session_state: st.session_state['family_feed'] = [] # 메시지 저장

family_members = [
    {"id": "chanhee", "name": "찬희", "role": "아빠", "emoji": "👨🏻‍💻"},
    {"id": "jiwoo", "name": "지우", "role": "엄마", "emoji": "👩🏻‍💼"},
    {"id": "jaeseon", "name": "재선", "role": "큰딸", "emoji": "👩🏻‍🎨"},
    {"id": "gyubi", "name": "규비", "role": "작은딸", "emoji": "👧🏻"},
    {"id": "seunggyu", "name": "승규", "role": "막내", "emoji": "👦🏻"}
]

# --- 3. 화면 구현 ---

# [화면 1] 홈/로그인 화면
def show_login_screen():
    st.markdown("<h2 style='text-align: center;'>가족 매니저 접속</h2><br>", unsafe_allow_html=True)
    
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            if st.button(f"{m['emoji']}\n{m['name']}", key=f"login_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 1) 일상 공유하기 탭 (위치와 크기 고정)
    st.markdown("""
        <div class="sns-fixed-tab">
            <div style="font-size: 28px; margin-right: 15px;">📸</div>
            <div style="flex-grow:1;">
                <div style="font-size: 17px; font-weight: 700; color: #191f28;">일상 공유하기</div>
                <div style="font-size: 13px; color: #8b95a1;">우리 가족의 오늘을 기록하세요</div>
            </div>
            <div style="color: #B0B8C1;">❯</div>
        </div>
    """, unsafe_allow_html=True)
    
    # 탭 클릭 버튼 (디자인 위에 투명하게 겹침)
    if st.button("", key="go_sns_fixed"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

# [화면 2] 일상 공유 상세 페이지 (말풍선 타이핑)
def show_sns_page():
    if st.button("❮ 홈으로", key="back_home"):
        st.session_state['current_page'] = 'Home'; st.session_state['speaking_id'] = None; st.rerun()
    
    st.title("📸 가족 게시판")
    st.write("말풍선을 클릭하여 메시지를 남겨보세요.")

    # 2) 5명 이름을 행으로 나열 + 3) 옆에 말풍선 버튼
    for m in family_members:
        with st.container():
            col_name, col_bubble = st.columns([1, 4])
            with col_name:
                st.markdown(f"<div style='margin-top:10px; font-weight:700;'>{m['emoji']} {m['name']}</div>", unsafe_allow_html=True)
            with col_bubble:
                # 4) 말풍선 클릭 시 타이핑 영역 활성화
                if st.button(f"이야기 듣고 싶어요! 💬", key=f"bubble_{m['id']}", help=f"{m['name']} SAYS..."):
                    st.session_state['speaking_id'] = m['id']
                    st.rerun()

        # 클릭한 사람 아래에만 타이핑 란 노출
        if st.session_state['speaking_id'] == m['id']:
            st.markdown(f'<div class="active-bubble">{m["name"]} SAYS...</div>', unsafe_allow_html=True)
            with st.form(key=f"form_{m['id']}", clear_on_submit=True):
                msg = st.text_input("메시지 입력", placeholder="오늘 어떤 일이 있었나요?", label_visibility="collapsed")
                if st.form_submit_button("가족과 공유"):
                    if msg:
                        time_now = datetime.now().strftime("%H:%M")
                        st.session_state['family_feed'].insert(0, f"[{time_now}] {m['emoji']} {m['name']}: {msg}")
                        st.session_state['speaking_id'] = None
                        st.rerun()

    # 실시간 피드
    st.markdown("---")
    st.subheader("💬 실시간 가족 피드")
    if st.session_state['family_feed']:
        for post in st.session_state['family_feed'][:10]:
            st.write(post)
    else:
        st.caption("아직 올라온 이야기가 없어요.")

# --- 4. 메인 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    show_sns_page()
else:
    # 로그인 후 홈화면 (나중에 주식 대시보드 연결)
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.header(f"{user['name']}님 반가워요!")
    if st.button("❮ 가족 바꾸기"): 
        st.session_state['user_id'] = None; st.rerun()

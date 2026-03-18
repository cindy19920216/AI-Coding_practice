import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. 전용 디자인 (클릭 레이어 완전 통합) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    
    .main .block-container { max-width: 600px; padding-top: 2rem; padding-bottom: 2rem; }

    /* 프로필 & SNS 탭 공통 스타일 (HTML 전용) */
    .clickable-card {
        background-color: white; border-radius: 20px; border: 1px solid #e5e8eb;
        transition: all 0.2s; cursor: pointer; text-decoration: none; color: inherit;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
    }
    .clickable-card:hover { border-color: #3182f6; background-color: #f9fafb; transform: translateY(-3px); }

    /* 넷플릭스 프로필 그리드 레이아웃 */
    .profile-grid {
        display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 30px;
    }
    .p-card { padding: 15px 5px; height: 130px; }
    .p-emoji { font-size: 35px; margin-bottom: 5px; }
    .p-name { font-size: 14px; font-weight: 700; color: #191f28; }

    /* 일상 공유 와이드 탭 전용 */
    .sns-wide-card {
        flex-direction: row; justify-content: flex-start; padding: 20px; width: 100%; margin-top: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    .sns-icon { font-size: 28px; margin-right: 15px; }
    .sns-text-box { flex-grow: 1; text-align: left; }

    /* Streamlit 기본 버튼 숨기기 (로직용으로만 사용) */
    .stButton { display: none; }
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

# --- 3. 화면 로직 ---

def show_login_screen():
    st.markdown("<h2 style='text-align: center; color: #191f28;'>누가 오셨나요?</h2><br>", unsafe_allow_html=True)
    
    # 1. 프로필 선택 (쿼리 파라미터를 활용한 클릭 처리)
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            # 실제 버튼 대신 카드 형태의 버튼 사용
            if st.button(f"{m['emoji']}\n{m['name']}", key=f"login_{m['id']}", use_container_width=True):
                st.session_state['user_id'] = m['id']
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. 일상 공유하기 탭 (Streamlit 공식 버튼을 카드로 디자인)
    # CSS에서 .stButton의 display를 제거하고 다시 스타일링합니다.
    st.markdown("""
        <style>
        div.stButton > button:first-child {
            background-color: white; border-radius: 24px; padding: 25px;
            border: 1px solid #e5e8eb; width: 100%; text-align: left;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03); display: block !important;
        }
        div.stButton > button:hover { border-color: #3182f6; background-color: #f9fafb; }
        </style>
    """, unsafe_allow_html=True)

    if st.button("📸  일상 공유하기                          ❯", key="go_sns_tab"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

def show_sns_page():
    # 뒤로가기 버튼은 상단에 작게 배치
    if st.button("❮ 홈으로 돌아가기", key="back_home"):
        st.session_state['current_page'] = 'Home'; st.session_state['speaking_id'] = None; st.rerun()
    
    st.title("📸 가족 게시판")
    
    # 이모티콘 + 이름 행 나열 (여기서도 버튼 디자인 커스텀)
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            if st.button(f"{m['emoji']}\n{m['name']}", key=f"msg_{m['id']}"):
                st.session_state['speaking_id'] = m['id']
                st.rerun()

    # 말풍선 타이핑
    if st.session_state['speaking_id']:
        spk = next(m for m in family_members if m['id'] == st.session_state['speaking_id'])
        st.info(f"💬 {spk['name']}님의 이야기를 입력 중...")
        
        with st.form(key="msg_form", clear_on_submit=True):
            user_msg = st.text_input("메시지", placeholder="이야기를 입력하세요", label_visibility="collapsed")
            if st.form_submit_button("가족들과 공유하기") and user_msg:
                st.session_state['family_feed'].insert(0, {
                    "time": datetime.now().strftime("%m/%d %H:%M"),
                    "name": spk['name'], "emoji": spk['emoji'], "msg": user_msg
                })
                st.session_state['speaking_id'] = None
                st.rerun()

    # 피드 출력
    st.markdown("---")
    for f in st.session_state['family_feed'][:10]:
        st.markdown(f"""
            <div style="background:white; padding:15px; border-radius:15px; margin-bottom:10px; border:1px solid #e5e8eb;">
                <b>{f['emoji']} {f['name']}</b> <span style="color:#8b95a1; font-size:12px; float:right;">{f['time']}</span><br>
                <div style="margin-top:8px;">{f['msg']}</div>
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

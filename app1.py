import streamlit as st
import pandas as pd

# --- 1. 디자인 및 스타일 (클릭 영역 최적화) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    .main .block-container { max-width: 600px; padding-top: 2rem; }

    /* 프로필 카드 */
    .profile-card {
        background-color: white; border-radius: 20px; padding: 15px;
        text-align: center; border: 1px solid #e5e8eb; height: 120px;
    }
    .profile-emoji { font-size: 30px; }
    .profile-name { font-size: 14px; font-weight: 700; color: #191f28; margin-top:5px; }

    /* 말풍선 스타일 */
    .bubble-box {
        background-color: #3182f6; color: white; border-radius: 15px;
        padding: 15px; margin-top: 20px; position: relative; font-weight: bold;
    }
    .bubble-box::after {
        content: ''; position: absolute; bottom: 100%; left: 50%;
        border-width: 10px; border-style: solid;
        border-color: transparent transparent #3182f6 transparent;
        transform: translateX(-50%);
    }

    /* 탭 클릭 버튼 스타일 (Streamlit 버튼을 카드처럼 보이게) */
    .stButton>button {
        border-radius: 20px; border: 1px solid #e5e8eb; background-color: white;
        padding: 20px; width: 100%; text-align: left; height: auto;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 관리 (임시 저장소) ---
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'current_page' not in st.session_state: st.session_state['current_page'] = 'Home'
if 'temp_messages' not in st.session_state: st.session_state['temp_messages'] = [] # 메시지 저장용 리스트
if 'speaking_id' not in st.session_state: st.session_state['speaking_id'] = None # 현재 선택된 말풍선 주인

family_members = [
    {"id": "chanhee", "name": "찬희", "role": "아빠", "emoji": "👨🏻‍💻"},
    {"id": "jiwoo", "name": "지우", "role": "엄마", "emoji": "👩🏻‍💼"},
    {"id": "jaeseon", "name": "재선", "role": "큰딸", "emoji": "👩🏻‍🎨"},
    {"id": "gyubi", "name": "규비", "role": "작은딸", "emoji": "👧🏻"},
    {"id": "seunggyu", "name": "승규", "role": "막내", "emoji": "👦🏻"}
]

# --- 3. 화면 구현 ---

# [화면 1] 프로필 선택 + 일상 공유 탭
def show_login_screen():
    st.markdown("<h2 style='text-align: center;'>누가 오셨나요?</h2><br>", unsafe_allow_html=True)
    
    # 5인 프로필 행 나열
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            if st.button(f"{m['emoji']}\n{m['name']}", key=f"login_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 일상 공유하기 탭 (디자인 입힌 버튼으로 교체)
    st.markdown("### ✨ 가족 소식")
    if st.button("📸 일상 공유하기  ❯", key="btn_go_sns"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

# [화면 2] 일상 공유 상세 페이지
def show_sns_page():
    if st.button("❮ 홈으로 돌아가기"):
        st.session_state['current_page'] = 'Home'
        st.rerun()

    st.title("📸 우리 가족 게시판")
    st.write("이모티콘을 선택하고 메시지를 입력하세요.")

    # 1. 5명 이모티콘 나열
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            if st.button(m['emoji'], key=f"emoji_{m['id']}"):
                st.session_state['speaking_id'] = m['id']
                st.rerun()
            st.caption(f"<p style='text-align:center;'>{m['name']}</p>", unsafe_allow_html=True)

    # 2. 말풍선 및 실시간 타이핑 영역
    if st.session_state['speaking_id']:
        speaker = next(m for m in family_members if m['id'] == st.session_state['speaking_id'])
        
        st.markdown(f"""<div class="bubble-box">{speaker['name']} SAYS...</div>""", unsafe_allow_html=True)
        
        # 폼(Form)을 사용하여 엔터키로 전송 가능하게 설정
        with st.form(key="msg_form", clear_on_submit=True):
            user_msg = st.text_input(label="메시지 입력", placeholder="여기에 타이핑하세요...", label_visibility="collapsed")
            submit = st.form_submit_button("전송하기")
            
            if submit and user_msg:
                # 리스트에 저장 (시간, 이름, 메시지)
                timestamp = datetime.now().strftime("%H:%M")
                st.session_state['temp_messages'].insert(0, f"[{timestamp}] {speaker['name']}: {user_msg}")
                st.session_state['speaking_id'] = None # 입력 후 닫기
                st.rerun()

    # 3. 실시간 피드 출력
    st.markdown("---")
    st.subheader("💬 실시간 가족 피드")
    if st.session_state['temp_messages']:
        for m in st.session_state['temp_messages'][:10]: # 최근 10개만
            st.write(m)
    else:
        st.caption("아직 올라온 소식이 없어요.")

# --- 4. 메인 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    show_sns_page()
else:
    # 홈화면 (로그인 후)
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.title(f"{user['name']}님, 안녕하세요!")
    if st.button("로그아웃"): 
        st.session_state['user_id'] = None
        st.rerun()

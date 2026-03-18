import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. 전용 디자인 (모바일 넷플릭스 스타일 & 와이드 탭 CSS) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    
    /* 모바일 중심 컨테이너 여백 */
    .main .block-container { max-width: 600px; padding-top: 2rem; padding-bottom: 2rem; }

    /* 1) 홈화면 가족 프로필 (넷플릭스 스타일: 크고 아름답게) */
    .netflix-profile {
        background-color: white; border-radius: 20px; padding: 25px 15px;
        text-align: center; border: 1px solid #e5e8eb;
        transition: transform 0.2s; cursor: pointer;
    }
    .netflix-profile:hover { transform: scale(1.05); border-color: #3182f6; }
    .profile-emoji { font-size: 50px; margin-bottom: 10px; } /* 이모티콘 크기 대폭 확대 */
    .profile-name { font-size: 18px; font-weight: 700; color: #191f28; }
    .profile-role { font-size: 13px; color: #8b95a1; margin-top: 2px; }

    /* 2) 일상 공유하기 탭 (가로폭 꽉 차게) */
    .sns-wide-tab {
        background-color: white; border-radius: 20px; padding: 20px;
        display: flex; align-items: center; border: 1px solid #e5e8eb;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-top: 30px;
        cursor: pointer; width: 100%; /* 가로폭 100% */
    }
    .sns-icon { font-size: 28px; margin-right: 18px; }
    .sns-title { font-size: 17px; font-weight: 700; color: #191f28; }
    .sns-desc { font-size: 14px; color: #8b95a1; margin-top: 2px; }

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

    /* 피드 스타일 */
    .feed-item {
        background: white; padding: 15px; border-radius: 15px; 
        margin-bottom: 10px; border: 1px solid #e5e8eb;
    }

    /* Streamlit 기본 버튼 숨기기 (카드 클릭 효과용) */
    .stButton>button { background: transparent; border: none; padding: 0; width: 100%; height: auto; color: inherit; }
    .stButton>button:hover { background: transparent; border: none; color: #3182f6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 및 세션 관리 ---
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'current_page' not in st.session_state: st.session_state['current_page'] = 'Home'
if 'speaking_id' not in st.session_state: st.session_state['speaking_id'] = None # 말풍선 주인 ID
if 'family_feed' not in st.session_state: st.session_state['family_feed'] = [] # 실시간 피드 저장소

family_members = [
    {"id": "chanhee", "name": "찬희", "role": "아빠", "emoji": "👨🏻‍💻"},
    {"id": "jiwoo", "name": "지우", "role": "엄마", "emoji": "👩🏻‍💼"},
    {"id": "jaeseon", "name": "재선", "role": "큰딸", "emoji": "👩🏻‍🎨"},
    {"id": "gyubi", "name": "규비", "role": "작은딸", "emoji": "👧🏻"},
    {"id": "seunggyu", "name": "승규", "role": "막내", "emoji": "👦🏻"}
]

# --- 3. 화면 구현 함수 ---

# [화면 1] 프로필 선택 + 일상 공유 탭
def show_login_screen():
    st.markdown("<h1 style='text-align: center; color: #191f28; margin-top: 20px;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b95a1; margin-bottom: 40px;'>가족 금융 매니저</p>", unsafe_allow_html=True)
    
    # 1. 가족 프로필 (넷플릭스 스타일: 크고 아름답게)
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            # 버튼 클릭 기능
            if st.button("", key=f"sel_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()
            # 디자인 카드
            st.markdown(f"""
                <div class="netflix-profile">
                    <div class="profile-emoji">{m['emoji']}</div>
                    <div class="profile-name">{m['name']}</div>
                    <div class="profile-role">{m['role']}</div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. [일상 공유하기] 탭 (가로폭 찬희~승규까지 넓게 연결)
    if st.button("", key="go_sns_tab"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()
    st.markdown("""
        <div class="sns-wide-tab">
            <div class="sns-icon">📸</div>
            <div style="flex-grow:1;">
                <div class="sns-title">일상 공유하기</div>
                <div class="sns-desc">오늘 우리 가족에게 하고 싶은 말이 있나요?</div>
            </div>
            <div style="color: #B0B8C1;">❯</div>
        </div>
    """, unsafe_allow_html=True)

# [화면 2] 일상 공유 상세 페이지
def show_sns_page():
    # 상단 헤더
    col_back, _ = st.columns([2, 8])
    with col_back:
        if st.button("❮ 홈으로", key="back_home"):
            st.session_state['current_page'] = 'Home'
            st.session_state['speaking_id'] = None # 페이지 나갈 때 말풍선 초기화
            st.rerun()
    
    st.title("📸 가족 게시판")
    st.write("이모티콘을 선택하고 오늘의 한마디를 남겨보세요.")

    # 1 & 3-1. 이모티콘 + 이름 세트 행 나열
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            # 이모티콘 버튼
            if st.button(m['emoji'], key=f"emoji_{m['id']}"):
                st.session_state['speaking_id'] = m['id']
                st.rerun()
            # 3-1) 이모티콘 바로 밑에 가족 이름 붙이기
            st.markdown(f"<p style='text-align:center; font-weight:700; font-size:14px; margin-top:-5px;'>{m['name']}</p>", unsafe_allow_html=True)

    # 3-2 & 3-3. 말풍선 입력 및 실시간 피드 저장
    if st.session_state['speaking_id']:
        speaker = next(m for m in family_members if m['id'] == st.session_state['speaking_id'])
        
        # SAYS.. 말풍선 디자인
        st.markdown(f"""<div class="bubble-box">{speaker['name']} SAYS...</div>""", unsafe_allow_html=True)
        
        # 3-3) 타이핑 후 전송 시 피드에 저장 (Form 사용)
        with st.form(key="msg_form", clear_on_submit=True):
            user_msg = st.text_input(label="메시지 입력", placeholder=f"{speaker['name']}님의 이야기를 들려주세요...", label_visibility="collapsed")
            submit = st.form_submit_button("가족들과 공유하기")
            
            if submit and user_msg:
                # 데이터 저장 (시간, 이름, 이모티콘, 메시지)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.session_state['family_feed'].insert(0, {
                    "time": timestamp,
                    "name": speaker['name'],
                    "emoji": speaker['emoji'],
                    "msg": user_msg
                })
                st.session_state['speaking_id'] = None # 입력 후 말풍선 닫기
                st.success("메시지가 공유되었습니다!")
                st.rerun()

    # 하단: 실시간 가족 피드 출력
    st.markdown("<hr style='border: 0.5px solid #e5e8eb; margin: 40px 0;'>", unsafe_allow_html=True)
    st.subheader("💬 실시간 가족 피드")
    if st.session_state['family_feed']:
        # 최근 10개만 표시
        for f in st.session_state['family_feed'][:10]:
            st.markdown(f"""
                <div class="feed-item">
                    <span style="font-size:20px; margin-right:8px;">{f['emoji']}</span>
                    <b>{f['name']}</b> <span style="color:#8b95a1; font-size:12px; float:right;">{f['time']}</span>
                    <p style="margin-top:8px; color:#333d4b; font-size:15px;">{f['msg']}</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("아직 올라온 소식이 없어요.")

# --- 4. 메인 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    show_sns_page()
else:
    # 홈화면 (로그인 후 - 기존 주식 분석 코드를 여기에 연결하세요)
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.title(f"📈 {user['name']}님, 안녕하세요!")
    if st.button("로그아웃"): 
        st.session_state['user_id'] = None
        st.rerun()

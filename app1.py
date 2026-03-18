import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
import feedparser
import urllib.parse

# --- 1. 전용 디자인 (토스 & 모바일 최적화 CSS) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    .main .block-container { max-width: 800px; padding-top: 2rem; }

    /* 프로필 및 일상 공유 카드 스타일 */
    .profile-card {
        background-color: white; border-radius: 20px; padding: 20px;
        text-align: center; transition: all 0.2s; border: 1px solid #e5e8eb;
        box-shadow: 0 4px 12px rgba(0,0,0,0.02);
    }
    .profile-emoji { font-size: 40px; margin-bottom: 10px; }
    .profile-name { font-size: 16px; font-weight: 700; color: #191f28; }
    
    .sns-tab {
        background-color: white; border-radius: 20px; padding: 20px; 
        display: flex; align-items: center; border: 1px solid #e5e8eb;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-top: 20px;
    }

    /* 토스형 메인 메뉴 카드 */
    .toss-card {
        background-color: white; border-radius: 24px; padding: 24px; margin-bottom: 16px;
        display: flex; align-items: center; transition: all 0.2s; border: none;
    }
    .icon-box { width: 50px; height: 50px; background-color: #F9FAFB; border-radius: 14px; 
                display: flex; justify-content: center; align-items: center; font-size: 24px; margin-right: 15px; }
    
    /* 버튼 투명화 로직 */
    .stButton>button { background: transparent; border: none; padding: 0; width: 100%; height: auto; color: inherit; }
    .stButton>button:hover { background: transparent; border: none; color: #3182f6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 및 세션 관리 ---
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'current_page' not in st.session_state: st.session_state['current_page'] = 'Home'

family_members = [
    {"id": "chanhee", "name": "찬희", "role": "아빠", "emoji": "👨🏻‍💻"},
    {"id": "jiwoo", "name": "지우", "role": "엄마", "emoji": "👩🏻‍💼"},
    {"id": "jaeseon", "name": "재선", "role": "큰딸", "emoji": "👩🏻‍🎨"},
    {"id": "gyubi", "name": "규비", "role": "작은딸", "emoji": "👧🏻"},
    {"id": "seunggyu", "name": "승규", "role": "막내", "emoji": "👦🏻"}
]

# 구글 시트 연동 (전문가님: 시트 ID를 입력하세요)
def load_watchlist(user_id):
    try:
        sheet_url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit#gid=0"
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=sheet_url)
        return df[df['user_id'] == user_id]['ticker'].tolist()
    except: return []

# --- 3. 화면별 함수 정의 ---

# [화면 1] 로그인/프로필 선택 + 일상 공유 탭
def show_login_screen():
    st.markdown("<h1 style='text-align: center; color: #191f28; margin-top: 30px;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b95a1; margin-bottom: 40px;'>가족 금융 매니저에 오신 것을 환영합니다</p>", unsafe_allow_html=True)
    
    # 가족 프로필 (5인)
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            if st.button("", key=f"sel_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()
            st.markdown(f"""
                <div class="profile-card">
                    <div class="profile-emoji">{m['emoji']}</div>
                    <div class="profile-name">{m['name']}</div>
                    <div style="font-size:12px; color:#8b95a1;">{m['role']}</div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # [일상 공유하기] 탭 (프로필 하단 배치)
    if st.button("", key="go_sns_tab"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()
    st.markdown("""
        <div class="sns-tab">
            <div style="font-size: 24px; margin-right: 15px;">📸</div>
            <div style="text-align: left; flex-grow:1;">
                <div style="font-size: 16px; font-weight: 700; color: #191f28;">일상 공유하기</div>
                <div style="font-size: 13px; color: #8b95a1;">오늘 가족들에게 하고 싶은 말이 있나요?</div>
            </div>
            <div style="color: #B0B8C1;">❯</div>
        </div>
    """, unsafe_allow_html=True)

# [화면 2] 홈화면 (로그인 후)
def show_home():
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    
    # 상단 바
    col_h, col_l = st.columns([8, 2])
    with col_h: st.markdown(f"<h1>{user['name']}님, 반가워요 👋</h1>", unsafe_allow_html=True)
    with col_l: 
        if st.button("가족 바꾸기"): 
            st.session_state['user_id'] = None
            st.rerun()

    # 관심 종목 리스트 (구글 시트 연동)
    st.markdown("<h3 style='font-size:18px; margin-top:20px;'>내가 찜한 주식</h3>", unsafe_allow_html=True)
    watchlist = load_watchlist(user['id'])
    if watchlist:
        for tk in watchlist:
            st.markdown(f'<div style="background:white; padding:15px; border-radius:15px; margin-bottom:8px; border:1px solid #e5e8eb;"><b>{tk}</b> <span style="float:right; color:#3182f6;">상세보기 ❯</span></div>', unsafe_allow_html=True)
    else:
        st.info("구글 시트에 종목을 등록해 주세요.")

    # 메인 메뉴
    if st.button("", key="go_stock_page"): st.session_state['current_page'] = 'Stock'; st.rerun()
    st.markdown('<div class="toss-card"><div class="icon-box">📈</div><div><div style="font-weight:700;">주식 분석 대시보드</div><div style="color:#8b95a1; font-size:13px;">전문가용 퀀트 분석</div></div></div>', unsafe_allow_html=True)

# [화면 3] 일상 공유 페이지
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

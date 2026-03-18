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
    .main .block-container { max-width: 600px; padding-top: 2rem; }

    /* 프로필 카드 스타일 */
    .profile-card {
        background-color: white; border-radius: 20px; padding: 20px;
        text-align: center; border: 1px solid #e5e8eb;
        box-shadow: 0 4px 12px rgba(0,0,0,0.02);
        height: 140px; position: relative;
    }
    .profile-emoji { font-size: 40px; margin-bottom: 10px; }
    .profile-name { font-size: 16px; font-weight: 700; color: #191f28; }
    
    /* 일상 공유하기 탭 디자인 (클릭 가능하도록 Z-index 조정) */
    .sns-tab-ui {
        background-color: white; border-radius: 20px; padding: 20px; 
        display: flex; align-items: center; border: 1px solid #e5e8eb;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-top: 20px;
        position: relative;
    }

    /* 토스형 메인 메뉴 카드 */
    .toss-card {
        background-color: white; border-radius: 24px; padding: 24px; margin-bottom: 16px;
        display: flex; align-items: center; border: none;
    }
    .icon-box { width: 50px; height: 50px; background-color: #F9FAFB; border-radius: 14px; 
                display: flex; justify-content: center; align-items: center; font-size: 24px; margin-right: 15px; }
    
    /* 말풍선 SAYS... 스타일 */
    .active-bubble {
        background-color: #3182f6; color: white; border-radius: 15px;
        padding: 12px; margin: 10px 0; font-weight: 600; text-align: center;
        position: relative;
    }

    /* 투명 버튼을 디자인 위에 100% 덮는 로직 (클릭 에러 해결) */
    .stButton>button {
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background: transparent !important; border: none !important; color: transparent !important;
        z-index: 10; cursor: pointer;
    }
    .stButton>button:hover { background: rgba(0,0,0,0.02) !important; }

    /* 피드 아이템 디자인 */
    .feed-item {
        background: white; padding: 15px; border-radius: 15px; 
        margin-bottom: 10px; border: 1px solid #e5e8eb;
    }
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

def load_watchlist(user_id):
    try:
        sheet_url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit#gid=0"
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=sheet_url)
        return df[df['user_id'] == user_id]['ticker'].tolist()
    except: return []

# --- 3. 화면 구현 함수 ---

def show_login_screen():
    st.markdown("<h1 style='text-align: center; color: #191f28; margin-top: 30px;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            st.markdown(f"""
                <div class="profile-card">
                    <div class="profile-emoji">{m['emoji']}</div>
                    <div class="profile-name">{m['name']}</div>
                    <div style="font-size:12px; color:#8b95a1;">{m['role']}</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("", key=f"sel_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 일상 공유하기 탭 (클릭 영역 보정)
    st.markdown("""
        <div class="sns-tab-ui">
            <div style="font-size: 24px; margin-right: 15px;">📸</div>
            <div style="text-align: left; flex-grow:1;">
                <div style="font-size: 16px; font-weight: 700; color: #191f28;">일상 공유하기</div>
                <div style="font-size: 13px; color: #8b95a1;">오늘 가족들에게 하고 싶은 말이 있나요?</div>
            </div>
            <div style="color: #B0B8C1;">❯</div>
        </div>
    """, unsafe_allow_html=True)
    # 디자인 레이어 높이에 맞춰 빈 공간 확보 후 투명 버튼 배치
    st.markdown("<div style='margin-top: -90px;'>", unsafe_allow_html=True)
    if st.button("", key="go_sns_tab"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_home():
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    col_h, col_l = st.columns([8, 2])
    with col_h: st.markdown(f"<h1>{user['name']}님, 반가워요 👋</h1>", unsafe_allow_html=True)
    with col_l: 
        if st.button("바꾸기"): 
            st.session_state['user_id'] = None
            st.rerun()

    st.markdown("<h3 style='font-size:18px; margin-top:20px;'>내가 찜한 주식</h3>", unsafe_allow_html=True)
    watchlist = load_watchlist(user['id'])
    if watchlist:
        for tk in watchlist:
            st.markdown(f'<div style="background:white; padding:15px; border-radius:15px; margin-bottom:8px; border:1px solid #e5e8eb;"><b>{tk}</b> <span style="float:right; color:#3182f6;">상세보기 ❯</span></div>', unsafe_allow_html=True)
    else: st.info("구글 시트에 종목을 등록해 주세요.")

    # 주식 분석 대시보드 카드
    st.markdown('<div class="toss-card"><div class="icon-box">📈</div><div><div style="font-weight:700;">주식 분석 대시보드</div><div style="color:#8b95a1; font-size:13px;">전문가용 퀀트 분석</div></div></div>', unsafe_allow_html=True)
    st.markdown("<div style='margin-top: -95px;'>", unsafe_allow_html=True)
    if st.button("", key="go_stock_page"):
        st.session_state['current_page'] = 'Stock'
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_sns_page():
    if st.button("❮ 홈으로", key="back_home"):
        st.session_state['current_page'] = 'Home'; st.session_state['speaking_id'] = None; st.rerun()
    
    st.title("📸 가족 게시판")
    
    # 가족 5인 행 나열 + 말풍선 버튼 로직
    for m in family_members:
        with st.container():
            col_name, col_bubble = st.columns([1, 4])
            with col_name:
                st.markdown(f"<div style='margin-top:10px; font-weight:700;'>{m['emoji']} {m['name']}</div>", unsafe_allow_html=True)
            with col_bubble:
                # 개별 말풍선 버튼 (디자인과 클릭 기능 통합)
                is_active = st.session_state['speaking_id'] == m['id']
                btn_label = f"{m['name']} SAYS... 💬" if not is_active else "지금 입력 중... ✍️"
                if st.button(btn_label, key=f"bubble_{m['id']}"):
                    st.session_state['speaking_id'] = m['id']
                    st.rerun()

        # 클릭한 사람 아래에만 타이핑 란 노출
        if st.session_state['speaking_id'] == m['id']:
            st.markdown(f'<div class="active-bubble">{m["name"]}님이 입력 중입니다...</div>', unsafe_allow_html=True)
            with st.form(key=f"form_{m['id']}", clear_on_submit=True):
                msg = st.text_input("메시지 입력", placeholder="오늘 어떤 일이 있었나요?", label_visibility="collapsed")
                if st.form_submit_button("가족과 공유하기"):
                    if msg:
                        time_now = datetime.now().strftime("%H:%M")
                        st.session_state['family_feed'].insert(0, {"name": m['name'], "emoji": m['emoji'], "msg": msg, "time": time_now})
                        st.session_state['speaking_id'] = None
                        st.rerun()

    # 실시간 피드 출력
    st.markdown("---")
    st.subheader("💬 실시간 가족 피드")
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
    if st.session_state['current_page'] == 'Home':
        show_home()
    elif st.session_state['current_page'] == 'Stock':
        if st.button("❮ 뒤로가기"): st.session_state['current_page'] = 'Home'; st.rerun()
        st.write("📈 주식 상세 분석 페이지입니다.")

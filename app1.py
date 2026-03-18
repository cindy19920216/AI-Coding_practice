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

    /* 프로필 및 일상 공유 카드 스타일 */
    .profile-card {
        background-color: white; border-radius: 20px; padding: 20px;
        text-align: center; transition: all 0.2s; border: 1px solid #e5e8eb;
        box-shadow: 0 4px 12px rgba(0,0,0,0.02); height: 140px;
    }
    .profile-emoji { font-size: 40px; margin-bottom: 10px; }
    .profile-name { font-size: 16px; font-weight: 700; color: #191f28; }
    
    /* 일상 공유 탭 스타일 (클릭 가능하게 개선) */
    .sns-tab-ui {
        background-color: white; border-radius: 20px; padding: 20px; 
        display: flex; align-items: center; border: 1px solid #e5e8eb;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-top: 10px;
    }

    /* 말풍선 디자인 */
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
        background: white; padding: 15px; border-radius: 15px; 
        margin-bottom: 10px; border: 1px solid #e5e8eb;
    }

    /* 버튼 투명화 및 레이어 겹치기 최적화 */
    .stButton>button { background: transparent; border: none; padding: 0; width: 100%; height: auto; color: inherit; }
    .stButton>button:hover { background: transparent; border: none; color: #3182f6; }
    
    /* 실제 클릭용 투명 버튼 위치 조정 */
    .overlay-btn { position: relative; z-index: 10; margin-top: -85px; height: 85px; }
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

# 구글 시트 연동 함수 (예외 처리 강화)
def load_watchlist(user_id):
    try:
        sheet_url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit#gid=0"
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=sheet_url)
        return df[df['user_id'] == user_id]['ticker'].tolist()
    except: return []

# --- 3. 화면별 함수 정의 ---

def show_login_screen():
    st.markdown("<h1 style='text-align: center; color: #191f28; margin-top: 30px;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b95a1; margin-bottom: 40px;'>가족 금융 매니저</p>", unsafe_allow_html=True)
    
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
            if st.button("", key=f"sel_{m['id']}", help=f"{m['name']} 선택"):
                st.session_state['user_id'] = m['id']
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 일상 공유하기 탭
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
    if st.button("", key="go_sns_tab"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

def show_home():
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    
    col_h, col_l = st.columns([8, 2])
    with col_h: st.markdown(f"<h1>{user['name']}님, 반가워요 👋</h1>", unsafe_allow_html=True)
    with col_l: 
        if st.button("가족 바꾸기"): 
            st.session_state['user_id'] = None
            st.rerun()

    st.markdown("<h3 style='font-size:18px; margin-top:20px;'>내가 찜한 주식</h3>", unsafe_allow_html=True)
    watchlist = load_watchlist(user['id'])
    if watchlist:
        for tk in watchlist:
            st.markdown(f'<div style="background:white; padding:15px; border-radius:15px; margin-bottom:8px; border:1px solid #e5e8eb;"><b>{tk}</b> <span style="float:right; color:#3182f6;">상세보기 ❯</span></div>', unsafe_allow_html=True)
    else: st.info("구글 시트에 종목을 등록해 주세요.")

    if st.button("", key="go_stock_page"): st.session_state['current_page'] = 'Stock'; st.rerun()
    st.markdown('<div class="toss-card"><div class="icon-box">📈</div><div><div style="font-weight:700;">주식 분석 대시보드</div><div style="color:#8b95a1; font-size:13px;">전문가용 퀀트 분석</div></div></div>', unsafe_allow_html=True)

def show_sns_page():
    if st.button("❮ 홈으로", key="back_from_sns"):
        st.session_state['current_page'] = 'Home'; st.session_state['speaking_id'] = None; st.rerun()
    
    st.title("📸 가족 게시판")
    st.markdown("<p style='color:#8b95a1;'>이모티콘을 눌러 오늘의 한마디를 남겨보세요.</p>", unsafe_allow_html=True)

    # 1. 5명 이모티콘 나열 (행 정렬)
    cols = st.columns(5)
    for i, m in enumerate(family_members):
        with cols[i]:
            if st.button(m['emoji'], key=f"emoji_{m['id']}"):
                st.session_state['speaking_id'] = m['id']
                st.rerun()
            st.markdown(f"<p style='text-align:center; font-weight:700; margin-top:-10px;'>{m['name']}</p>", unsafe_allow_html=True)

    # 2. 말풍선 및 실시간 입력 영역
    if st.session_state['speaking_id']:
        spk = next(m for m in family_members if m['id'] == st.session_state['speaking_id'])
        st.markdown(f'<div class="bubble-box">{spk["name"]} SAYS...</div>', unsafe_allow_html=True)
        
        with st.form(key="msg_form", clear_on_submit=True):
            user_msg = st.text_input("메시지", placeholder="여기에 이야기를 입력하세요", label_visibility="collapsed")
            if st.form_submit_button("가족들과 공유하기") and user_msg:
                time_str = datetime.now().strftime("%m/%d %H:%M")
                st.session_state['temp_messages'].insert(0, {
                    "time": time_str, "name": spk['name'], "emoji": spk['emoji'], "msg": user_msg
                })
                st.session_state['speaking_id'] = None
                st.rerun()

    # 3. 실시간 피드 출력
    st.markdown("<hr style='border:0.5px solid #e5e8eb; margin:30px 0;'>", unsafe_allow_html=True)
    st.subheader("💬 실시간 가족 피드")
    if st.session_state['temp_messages']:
        for m in st.session_state['temp_messages'][:10]:
            st.markdown(f"""
                <div class="feed-item">
                    <b>{m['emoji']} {m['name']}</b> <span style="float:right; color:#8b95a1; font-size:12px;">{m['time']}</span><br>
                    <div style="margin-top:8px; color:#333d4b;">{m['msg']}</div>
                </div>
            """, unsafe_allow_html=True)
    else: st.caption("아직 올라온 소식이 없어요.")

# --- 4. 메인 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    show_sns_page()
else:
    if st.session_state['current_page'] == 'Home': show_home()
    elif st.session_state['current_page'] == 'Stock':
        if st.button("❮ 뒤로가기"): st.session_state['current_page'] = 'Home'; st.rerun()
        st.write("상세 분석 페이지입니다.")

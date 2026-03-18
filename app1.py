import streamlit as st
from datetime import datetime
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. 디자인 고정 (기존 전문가님 스타일 100% 유지) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    .main .block-container { max-width: 500px !important; padding: 2rem 1.5rem !important; }
    div.stButton > button[key^="sel_"] {
        height: 100px !important; width: 100% !important; display: flex !important;
        flex-direction: row !important; align-items: center !important; justify-content: flex-start !important;
        padding-left: 25px !important; margin-bottom: 12px !important;
        background-color: white !important; border: 1px solid #e5e8eb !important;
        border-radius: 20px !important; box-shadow: 0 4px 12px rgba(0,0,0,0.02) !important;
    }
    div.stButton > button[key^="sel_"] p { font-size: 35px !important; margin-right: 20px !important; margin-bottom: 0px !important; }
    div.stButton > button[key^="sel_"] { font-size: 20px !important; font-weight: 700 !important; color: #191f28 !important; }
    div.stButton > button[key="go_sns_tab"] {
        height: 120px !important; width: 100% !important; border-radius: 20px !important;
        background-color: white !important; border: 1px solid #e5e8eb !important;
        text-align: left !important; padding-left: 25px !important; font-size: 18px !important; font-weight: 700 !important;
    }
    div.stButton > button[key^="bubble_"] {
        background-color: #fef01b !important; border: none !important; border-radius: 15px !important;
        color: #371d1e !important; font-weight: 700 !important; padding: 8px 15px !important; width: auto !important;
    }
    .feed-card { background: white; padding: 15px; border-radius: 18px; margin-bottom: 12px; border: 1px solid #e5e8eb; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
    </style>
""", unsafe_allow_html=True)

# --- 2. 구글 시트 연동 설정 ---
# 시트 URL은 전문가님의 시트 주소로 변경이 필요합니다.
SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 불러오기 함수
def get_feed_data():
    try:
        # 시트에서 데이터 읽기 (영구 저장된 데이터 로드)
        df = conn.read(spreadsheet=SHEET_URL, ttl="0") # 실시간성을 위해 ttl=0
        return df.sort_values(by="time", ascending=False) # 최신순 정렬
    except:
        return pd.DataFrame(columns=["name", "emoji", "msg", "time"])

# 데이터 저장 함수
def save_to_sheet(name, emoji, msg):
    df = get_feed_data()
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_data = pd.DataFrame([{"name": name, "emoji": emoji, "msg": msg, "time": time_now}])
    updated_df = pd.concat([df, new_data], ignore_index=True)
    # 구글 시트에 업데이트 (영구 저장 실행)
    conn.update(spreadsheet=SHEET_URL, data=updated_df)

# --- 3. 세션 관리 ---
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'current_page' not in st.session_state: st.session_state['current_page'] = 'Home'
if 'speaking_id' not in st.session_state: st.session_state['speaking_id'] = None

family_members = [
    {"id": "chanhee", "name": "찬희", "emoji": "👨🏻‍💻"},
    {"id": "jiwoo", "name": "지우", "emoji": "👩🏻‍💼"},
    {"id": "jaeseon", "name": "재선", "emoji": "👩🏻‍🎨"},
    {"id": "gyubi", "name": "규비", "emoji": "👧🏻"},
    {"id": "seunggyu", "name": "승규", "emoji": "👦🏻"}
]

# --- 4. 화면 구현 ---

def show_login_screen():
    st.markdown("<h1 style='text-align: center; color: #191f28; font-size: 26px;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    for m in family_members:
        if st.button(f"{m['emoji']}  {m['name']}", key=f"sel_{m['id']}"):
            st.session_state['user_id'] = m['id']; st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📸   일상 공유하기\n\n오늘 가족들에게 하고 싶은 말이 있나요?       ❯", key="go_sns_tab"):
        st.session_state['current_page'] = 'FamilySNS'; st.rerun()

def show_sns_page():
    if st.button("❮ 홈으로 돌아가기", key="back_home"):
        st.session_state['current_page'] = 'Home'; st.session_state['speaking_id'] = None; st.rerun()
    
    st.markdown("## 📸 가족 게시판")
    
    # 가족 나열 및 입력 로직
    for m in family_members:
        col_n, col_b = st.columns([1.5, 3])
        with col_n: st.markdown(f"<div style='font-size:18px; font-weight:700; padding-top:10px;'>{m['emoji']} {m['name']}</div>", unsafe_allow_html=True)
        with col_b:
            if st.button("이야기하기 💬", key=f"bubble_{m['id']}"):
                st.session_state['speaking_id'] = m['id']; st.rerun()

        if st.session_state['speaking_id'] == m['id']:
            with st.form(key=f"form_{m['id']}", clear_on_submit=True):
                msg = st.text_input("메시지 입력", placeholder="오늘 어떤 일이 있었나요?", label_visibility="collapsed")
                if st.form_submit_button("영구 저장 및 공유"):
                    if msg:
                        # [영구 저장 실행] 시트로 데이터 전송
                        save_to_sheet(m['name'], m['emoji'], msg)
                        st.session_state['speaking_id'] = None
                        st.success("시트에 기록되었습니다!")
                        st.rerun()
        st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("💬 실시간 가족 피드 (영구 저장됨)")
    
    # 시트에서 최신 데이터 불러오기
    feed_df = get_feed_data()
    if not feed_df.empty:
        for _, row in feed_df.head(15).iterrows():
            st.markdown(f"""
                <div class="feed-card">
                    <span style="font-weight:700;">{row['emoji']} {row['name']}</span>
                    <span style="float:right; color:#8b95a1; font-size:12px;">{row['time']}</span>
                    <div style="margin-top:8px; color:#191f28;">{row['msg']}</div>
                </div>
            """, unsafe_allow_html=True)

# --- 5. 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    show_sns_page()
else:
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.markdown(f"<h1 style='text-align:center;'>{user['emoji']} {user['name']}님 반가워요!</h1>", unsafe_allow_html=True)
    if st.button("❮ 가족 바꾸기", key="logout"): st.session_state['user_id'] = None; st.rerun()

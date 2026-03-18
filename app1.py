import streamlit as st
from datetime import datetime
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. 디자인 고정 (전문가님 5인 와이드 스타일) ---
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

# --- 2. 구글 시트 연결 (에러 방지용) ---
# 전문가님이 만드신 시트 ID 반영
SHEET_URL = "https://docs.google.com/spreadsheets/d/1zTU8HRcaA79bSDgqOA7yYlkXXbC3OcJaBz9x511C1PQ/edit#gid=0"

# 연결 인터페이스 (기존 방식 유지하되 업데이트 로직 강화)
conn = st.connection("gsheets", type=GSheetsConnection)

def load_feed():
    try:
        # 캐시 없이 실시간으로 읽기
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        return df
    except:
        return pd.DataFrame(columns=["name", "emoji", "msg", "time"])

def post_msg(name, emoji, msg):
    try:
        existing_data = load_feed()
        new_row = pd.DataFrame([{
            "name": name, 
            "emoji": emoji, 
            "msg": msg, 
            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
        }])
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        
        # 핵심: update 메서드 에러를 피하기 위해 명시적으로 시트 지정
        conn.update(spreadsheet=SHEET_URL, data=updated_df)
        st.cache_data.clear() # 캐시 강제 삭제
        return True
    except Exception as e:
        st.error(f"저장 중 오류 발생: {e}")
        return False

# --- 3. 데이터 및 세션 ---
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

# --- 4. 화면 로직 ---

def show_login_screen():
    st.markdown("<h1 style='text-align:center;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
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
    
    for m in family_members:
        col_n, col_b = st.columns([1.5, 3])
        with col_n: 
            st.markdown(f"<div style='font-size:18px; font-weight:700; padding-top:10px;'>{m['emoji']} {m['name']}</div>", unsafe_allow_html=True)
        with col_b:
            if st.button("이야기하기 💬", key=f"bubble_{m['id']}"):
                st.session_state['speaking_id'] = m['id']; st.rerun()

        if st.session_state['speaking_id'] == m['id']:
            # 폼을 사용하여 전송 후 새로고침 유도
            with st.form(key=f"form_{m['id']}", clear_on_submit=True):
                msg = st.text_input("메시지 입력", placeholder="소식을 남겨주세요", label_visibility="collapsed")
                if st.form_submit_button("가족과 공유"):
                    if msg:
                        if post_msg(m['name'], m['emoji'], msg):
                            st.session_state['speaking_id'] = None
                            st.rerun()
        st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("💬 실시간 가족 피드")
    
    df = load_feed()
    if not df.empty:
        # 역순 정렬 (최신순)
        for _, row in df.iloc[::-1].head(15).iterrows():
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

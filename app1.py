import streamlit as st
from datetime import datetime
import pandas as pd
import requests

# --- 1. 디자인 고정 ---
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
    div.stButton > button[key^="bubble_"] {
        background-color: #fef01b !important; border: none !important; border-radius: 15px !important;
        color: #371d1e !important; font-weight: 700 !important; padding: 8px 15px !important; width: auto !important;
    }
    .feed-card { background: white; padding: 15px; border-radius: 18px; margin-bottom: 12px; border: 1px solid #e5e8eb; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 구글 시트 우회 연결 ---
# 1) 읽기용 (전문가님 시트 URL)
READ_URL = "https://docs.google.com/spreadsheets/d/1zTU8HRcaA79bSDgqOA7yYlkXXbC3OcJaBz9x511C1PQ/gviz/tq?tqx=out:csv"
# 2) 쓰기용 (위에서 만든 Apps Script 웹 앱 URL을 여기에 넣으세요)
API_URL = "https://script.google.com/macros/s/AKfycbxyrGGYC9Ik-eBunTjyaSyvT5TK40G0XceCU-0oNKw/dev" 

def load_data():
    try:
        return pd.read_csv(READ_URL)
    except:
        return pd.DataFrame(columns=["name", "emoji", "msg", "time"])

def save_data(name, emoji, msg):
    payload = {
        "name": name, "emoji": emoji, "msg": msg,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    try:
        requests.post(API_URL, json=payload)
        return True
    except:
        return False

# --- 3. 세션 및 화면 로직 ---
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

def show_login_screen():
    st.markdown("<h1 style='text-align:center;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    for m in family_members:
        if st.button(f"{m['emoji']}  {m['name']}", key=f"sel_{m['id']}"):
            st.session_state['user_id'] = m['id']; st.rerun()
    st.write("")
    if st.button("📸   일상 공유하기\n\n오늘 가족들에게 하고 싶은 말이 있나요?       ❯", key="go_sns_tab"):
        st.session_state['current_page'] = 'FamilySNS'; st.rerun()

def show_sns_page():
    if st.button("❮ 홈으로 돌아가기", key="back_home"):
        st.session_state['current_page'] = 'Home'; st.session_state['speaking_id'] = None; st.rerun()
    
    st.markdown("## 📸 가족 게시판")
    
    for m in family_members:
        col_n, col_b = st.columns([1.5, 3])
        with col_n: st.markdown(f"**{m['emoji']} {m['name']}**")
        with col_b:
            if st.button("이야기하기 💬", key=f"bubble_{m['id']}"):
                st.session_state['speaking_id'] = m['id']; st.rerun()

        if st.session_state['speaking_id'] == m['id']:
            with st.form(key=f"form_{m['id']}", clear_on_submit=True):
                msg = st.text_input("소식을 남겨주세요", label_visibility="collapsed")
                if st.form_submit_button("가족과 공유"):
                    if msg and save_data(m['name'], m['emoji'], msg):
                        st.session_state['speaking_id'] = None
                        st.rerun()
    
    st.markdown("---")
    st.subheader("💬 실시간 가족 피드")
    df = load_data()
    if not df.empty:
        for _, row in df.iloc[::-1].head(10).iterrows():
            st.markdown(f"""
                <div class="feed-card">
                    <b>{row['emoji']} {row['name']}</b> <span style="float:right; color:gray; font-size:12px;">{row['time']}</span>
                    <div style="margin-top:5px;">{row['msg']}</div>
                </div>
            """, unsafe_allow_html=True)

if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    show_sns_page()
else:
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.markdown(f"### {user['emoji']} {user['name']}님 반가워요!")
    if st.button("로그아웃"): st.session_state['user_id'] = None; st.rerun()

import streamlit as st
from styles import apply_styles
from database import load_data, save_data

st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")
apply_styles()

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
    # app.py의 show_login_screen 함수 하단에 추가
def show_login_screen():
    # ... 기존 로그인 버튼 코드 ...

    st.markdown("---") # 구분선
    
    # 우측 빈 공간을 채울 위젯 구성
    col_info, col_img = st.columns([2, 1])
    with col_info:
        st.markdown("### 🌤️ 오늘의 가족 날씨")
        st.info("현재 서울은 맑음! 기분 좋은 하루 보내세요.")
        st.markdown("#### 💌 오늘의 한마디")
        st.warning("✨ '재선'님, 오늘 하루도 반짝반짝 빛나길 응원해요!")
    with col_img:
        # 여기에 귀여운 가족 캐릭터나 날씨 아이콘 배치
        st.write("🌞")
    
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

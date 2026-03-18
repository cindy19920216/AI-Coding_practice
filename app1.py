import streamlit as st
from styles import apply_styles
from database import load_data, save_data, get_market_indices # 지수 함수 추가

st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")
apply_styles()

# 세션 상태 초기화
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
    st.markdown("<h1 style='text-align:center;'>누가 오셨나요?</h1></h1>", unsafe_allow_html=True)
    
    # 가족 버튼들을 가로로 배치
    cols = st.columns(len(family_members))
    for i, m in enumerate(family_members):
        with cols[i]:
            if st.button(f"{m['emoji']}\n{m['name']}", key=f"sel_{m['id']}"):
                st.session_state['user_id'] = m['id']
                st.rerun()
                
    st.write("")
    if st.button("📸 일상 공유하기 ❯", key="go_sns_tab", use_container_width=True):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()

    st.markdown("---") 
    col_info, col_img = st.columns([2, 1])
    with col_info:
        st.markdown("### 🌤️ 오늘의 날씨")
        st.info("현재 서울은 맑음! 기분 좋은 하루 보내세요.")
        st.markdown("#### 💌 오늘의 한마디")
        st.warning("✨ 오늘 하루도 반짝반짝 빛나길 응원해요!")
    with col_img:
        st.write("# 🌞")

def show_sns_page():
    if st.button("❮ 홈으로 돌아가기", key="back_home"):
        st.session_state['current_page'] = 'Home'
        st.session_state['speaking_id'] = None
        st.rerun()
    
    st.markdown("## 📸 가족 게시판")
    
    # 1. 메시지 입력 구역
    for m in family_members:
        col_n, col_b = st.columns([1, 4])
        with col_n: st.markdown(f"### {m['emoji']} {m['name']}")
        with col_b:
            if st.button(f"{m['name']}님 소식 남기기 💬", key=f"bubble_{m['id']}"):
                st.session_state['speaking_id'] = m['id']
                st.rerun()

        if st.session_state['speaking_id'] == m['id']:
            with st.form(key=f"form_{m['id']}", clear_on_submit=True):
                msg_input = st.text_input("가족들에게 보낼 소식을 남겨주세요", placeholder="내용을 입력하세요...")
                submit = st.form_submit_button("가족과 공유")
                
                if submit:
                    if msg_input:
                        if save_data(m['name'], m['emoji'], msg_input):
                            st.success("메시지가 시트에 저장되었습니다!")
                            st.rerun()
                        else:
                            st.error("저장에 실패했습니다. 주소와 권한을 확인해주세요.")
                    else:
                        st.warning("내용을 입력해주세요.")
    
    st.markdown("---")
    
    # 2. 실시간 피드 구역 (최신순)
    st.subheader("💬 실시간 가족 피드")
    df = load_data()
    if not df.empty:
        # 최신 글이 위로 오도록 정렬 (데이터프레임 역순)
        for _, row in df.iloc[::-1].iterrows():
            st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #ff4b4b;">
                    <b>{row['emoji']} {row['name']}</b> <span style="float:right; color:gray; font-size:12px;">{row['time']}</span>
                    <div style="margin-top:5px; font-size: 16px;">{row['msg']}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("아직 등록된 소식이 없습니다. 첫 소식을 남겨보세요!")

# --- 메인 실행 로직 ---
if st.session_state['current_page'] == 'FamilySNS':
    show_sns_page()
elif st.session_state['user_id'] is None:
    show_login_screen()
else:
    # 로그인 후 개인 페이지 (여기에 시장 지표 띠 추가)
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    
    # 📈 경제 지표 띠(Ticker) 표시
    indices = get_market_indices()
    ticker_text = f"📈 KOSPI {indices['KOSPI']} | 📉 KOSDAQ {indices['KOSDAQ']} | 💵 USD/KRW {indices['USD/KRW']} | 🏦 수급: {indices['SUPPLY']}"
    
    st.markdown(f"""
        <div style="background: #191f28; color: #00ff00; padding: 10px; border-radius: 5px; overflow: hidden; white-space: nowrap;">
            <marquee scrollamount="5"><b>{ticker_text} &nbsp;&nbsp;&nbsp;&nbsp; {ticker_text}</b></marquee>
        </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    st.markdown(f"## {user['emoji']} {user['name']} 전문가님")
    
    if st.button("돌아가기"): 
        st.session_state['user_id'] = None
        st.rerun()

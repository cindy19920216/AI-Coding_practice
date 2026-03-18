import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime

# --- 1. 기본 설정 ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

# 세션 상태 초기화
if 'current_page' not in st.session_state: st.session_state['current_page'] = 'Home'
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'family_feed' not in st.session_state: st.session_state['family_feed'] = []

family_members = [
    {"id": "chanhee", "name": "찬희", "role": "아빠", "emoji": "👨🏻‍💻"},
    {"id": "jiwoo", "name": "지우", "role": "엄마", "emoji": "👩🏻‍💼"},
    {"id": "jaeseon", "name": "재선", "role": "큰딸", "emoji": "👩🏻‍🎨"},
    {"id": "gyubi", "name": "규비", "role": "작은딸", "emoji": "👧🏻"},
    {"id": "seunggyu", "name": "승규", "role": "막내", "emoji": "👦🏻"}
]

# --- 2. 핵심 함수: HTML 카드 렌더러 ---
# 전문가님이 원하는 모든 HTML/CSS 디자인을 여기에 넣으시면 됩니다.
def render_html_card(id, content_html, height=150):
    # 자바스크립트를 통해 부모 창(Streamlit)의 쿼리 파라미터를 변경하여 클릭을 알림
    card_wrapper = f"""
    <div id="card-{id}" style="cursor: pointer; width: 100%;">
        {content_html}
    </div>
    <script>
        const card = document.getElementById('card-{id}');
        card.onclick = function() {{
            // 부모창의 URL을 변경하여 Streamlit에 신호를 보냄
            const url = new URL(window.parent.location.href);
            url.searchParams.set('clicked_id', '{id}');
            window.parent.location.href = url.href;
        }};
    </script>
    """
    components.html(card_wrapper, height=height)

# --- 3. 클릭 신호 처리 (자바스크립트 통신 수신) ---
# URL 파라미터에 'clicked_id'가 있으면 세션 상태를 업데이트하고 파라미터를 지웁니다.
query_params = st.query_params
if "clicked_id" in query_params:
    clicked_id = query_params["clicked_id"]
    
    if clicked_id == "go_sns":
        st.session_state['current_page'] = 'FamilySNS'
    elif clicked_id in [m['id'] for m in family_members]:
        st.session_state['user_id'] = clicked_id
    
    # 신호 처리 후 URL 깔끔하게 정리 (Rerun 효과)
    st.query_params.clear()
    st.rerun()

# --- 4. 화면 구현 ---

def show_login_screen():
    st.markdown("<h1 style='text-align: center; font-family: Pretendard;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    
    # 넷플릭스 스타일 3+2 배치
    row1 = st.columns(3)
    for i in range(3):
        m = family_members[i]
        with row1[i]:
            # [전문가님 고정 디자인 영역]
            design = f"""
            <div style="background: #1F1F1F; border-radius: 15px; padding: 20px; text-align: center; border: 2px solid transparent; transition: 0.3s;" 
                 onmouseover="this.style.borderColor='white'" onmouseout="this.style.borderColor='transparent'">
                <div style="font-size: 50px;">{m['emoji']}</div>
                <div style="color: white; font-weight: bold; margin-top: 10px;">{m['name']}</div>
            </div>
            """
            render_html_card(m['id'], design, height=160)

    row2 = st.columns([1, 2, 2, 1])
    for i in range(3, 5):
        m = family_members[i]
        with row2[i-2]:
            design = f"""
            <div style="background: #1F1F1F; border-radius: 15px; padding: 20px; text-align: center; border: 2px solid transparent; transition: 0.3s;" 
                 onmouseover="this.style.borderColor='white'" onmouseout="this.style.borderColor='transparent'">
                <div style="font-size: 50px;">{m['emoji']}</div>
                <div style="color: white; font-weight: bold; margin-top: 10px;">{m['name']}</div>
            </div>
            """
            render_html_card(m['id'], design, height=160)

    st.write("")
    # 일상 공유 배너 (와이드 HTML 디자인)
    sns_design = """
    <div style="background: linear-gradient(90deg, #3182f6, #4d94f7); border-radius: 20px; padding: 25px; color: white; display: flex; align-items: center;">
        <div style="font-size: 30px; margin-right: 20px;">📸</div>
        <div>
            <div style="font-size: 18px; font-weight: bold;">일상 공유하기</div>
            <div style="font-size: 14px; opacity: 0.9;">우리 가족 소식 보러가기</div>
        </div>
        <div style="margin-left: auto; font-size: 20px;">❯</div>
    </div>
    """
    render_html_card("go_sns", sns_design, height=120)

def show_sns_page():
    if st.button("❮ 홈으로 돌아가기"):
        st.session_state['current_page'] = 'Home'; st.rerun()
    st.title("📸 가족 게시판")
    st.info("HTML 컴포넌트로 접속에 성공했습니다!")

# --- 5. 메인 로직 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    show_sns_page()
else:
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.header(f"{user['name']}님 접속 중")
    if st.button("로그아웃"):
        st.session_state['user_id'] = None; st.rerun()

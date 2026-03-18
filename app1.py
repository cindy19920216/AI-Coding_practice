import streamlit as st
import streamlit.components.v1 as components
from streamlit_js_eval import streamlit_js_eval

# --- 1. 설정 및 세션 초기화 ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

if 'current_page' not in st.session_state: st.session_state['current_page'] = 'Home'
if 'user_id' not in st.session_state: st.session_state['user_id'] = None

family_members = [
    {"id": "chanhee", "name": "찬희", "emoji": "👨🏻‍💻"},
    {"id": "jiwoo", "name": "지우", "emoji": "👩🏻‍💼"},
    {"id": "jaeseon", "name": "재선", "emoji": "👩🏻‍🎨"},
    {"id": "gyubi", "name": "규비", "emoji": "👧🏻"},
    {"id": "seunggyu", "name": "승규", "emoji": "👦🏻"}
]

# --- 2. 핵심 함수: 클릭 신호를 보내는 HTML 카드 ---
def render_clickable_card(id, html_content, height=160):
    # 자바스크립트가 클릭을 감지하면 URL에 파라미터를 붙여 강제 새로고침 유도
    wrapped_html = f"""
    <div id="btn-{id}" style="cursor: pointer; width: 100%;">
        {html_content}
    </div>
    <script>
        const btn = document.getElementById('btn-{id}');
        btn.onclick = function() {{
            window.parent.postMessage({{type: 'streamlit:setComponentValue', value: '{id}'}}, '*');
            // 부모창 URL에 신호를 남겨서 이동을 알림
            const url = new URL(window.parent.location.href);
            url.searchParams.set('target', '{id}');
            window.parent.location.href = url.href;
        }};
    </script>
    """
    components.html(wrapped_html, height=height)

# --- 3. URL 신호 감지 및 페이지 전환 로직 ---
# 자바스크립트가 URL에 남긴 'target' 신호를 Streamlit이 읽어들입니다.
params = st.query_params
if "target" in params:
    target = params["target"]
    if target == "go_sns":
        st.session_state['current_page'] = 'FamilySNS'
    elif target in [m['id'] for m in family_members]:
        st.session_state['user_id'] = target
    
    # 신호 확인 후 URL 깨끗하게 정리 (중요!)
    st.query_params.clear()
    st.rerun()

# --- 4. 화면 구현 ---

def show_login_screen():
    st.markdown("<h1 style='text-align: center; color: white; background: #0F1117; padding: 20px;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    st.markdown("<style>body { background-color: #0F1117; }</style>", unsafe_allow_html=True)
    
    # 1행: 3인 배치
    row1 = st.columns(3)
    for i in range(3):
        m = family_members[i]
        with row1[i]:
            design = f"""
            <div style="background: #1F1F1F; border-radius: 20px; padding: 30px; text-align: center; border: 2px solid transparent; transition: 0.3s;" 
                 onmouseover="this.style.borderColor='white'" onmouseout="this.style.borderColor='transparent'">
                <div style="font-size: 55px;">{m['emoji']}</div>
                <div style="color: white; font-weight: bold; font-size: 20px; margin-top: 15px;">{m['name']}</div>
            </div>
            """
            render_clickable_card(m['id'], design, height=180)

    # 2행: 2인 배치
    st.write("")
    row2 = st.columns([1, 2, 2, 1])
    for i in range(3, 5):
        m = family_members[i]
        with row2[i-2]:
            design = f"""
            <div style="background: #1F1F1F; border-radius: 20px; padding: 30px; text-align: center; border: 2px solid transparent; transition: 0.3s;" 
                 onmouseover="this.style.borderColor='white'" onmouseout="this.style.borderColor='transparent'">
                <div style="font-size: 55px;">{m['emoji']}</div>
                <div style="color: white; font-weight: bold; font-size: 20px; margin-top: 15px;">{m['name']}</div>
            </div>
            """
            render_clickable_card(m['id'], design, height=180)

    st.write("")
    # 일상 공유 배너 (완벽한 HTML 디자인)
    sns_design = """
    <div style="background: linear-gradient(90deg, #3182f6, #4d94f7); border-radius: 24px; padding: 30px; color: white; display: flex; align-items: center; box-shadow: 0 10px 20px rgba(49, 130, 246, 0.2);">
        <div style="font-size: 35px; margin-right: 25px;">📸</div>
        <div>
            <div style="font-size: 20px; font-weight: bold;">일상 공유하기</div>
            <div style="font-size: 15px; opacity: 0.9;">우리 가족의 소중한 순간들을 확인하세요</div>
        </div>
        <div style="margin-left: auto; font-size: 24px; font-weight: bold;">❯</div>
    </div>
    """
    render_clickable_card("go_sns", sns_design, height=140)

def show_sns_page():
    if st.button("❮ 홈으로 돌아가기"):
        st.session_state['current_page'] = 'Home'; st.rerun()
    st.title("📸 가족 게시판")
    st.success("HTML 카드 클릭으로 이동에 성공했습니다!")

# --- 5. 메인 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    show_sns_page()
else:
    # 로그인 성공 시
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.markdown(f"## {user['emoji']} {user['name']}님 환영합니다!")
    if st.button("로그아웃"):
        st.session_state['user_id'] = None; st.rerun()

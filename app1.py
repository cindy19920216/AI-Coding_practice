import streamlit as st
import streamlit.components.v1 as components

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

# --- 2. 핵심 함수: 클릭 가능한 HTML 카드 (보안 에러 방지형) ---
def render_html_card(id, html_content, height=180):
    # 이 방식은 URL을 건드리지 않고 브라우저의 전역 이벤트를 활용합니다.
    wrapped_html = f"""
    <div id="card-{id}" style="cursor: pointer; width: 100%;">
        {html_content}
    </div>
    <script>
        const card = document.getElementById('card-{id}');
        card.onclick = function() {{
            // 부모창(Streamlit)에 직접 신호를 보냄
            window.parent.postMessage({{
                isStreamlitMessage: true,
                type: "streamlit:setComponentValue",
                value: "{id}"
            }}, "*");
            
            // 클릭 즉시 부모창에 쿼리 파라미터 전달 (가장 확실한 방법)
            const url = new URL(window.parent.location.href);
            url.searchParams.set("target", "{id}");
            window.parent.location.href = url.href;
        }};
    </script>
    """
    components.html(wrapped_html, height=height)

# --- 3. 클릭 신호 수신부 ---
# URL 파라미터를 읽어서 페이지 이동을 처리합니다.
params = st.query_params
if "target" in params:
    target = params["target"]
    if target == "go_sns":
        st.session_state['current_page'] = 'FamilySNS'
    elif target in [m['id'] for m in family_members]:
        st.session_state['user_id'] = target
    
    # 처리 후 URL에서 target 파라미터 삭제 (중요)
    st.query_params.clear()
    st.rerun()

# --- 4. 화면 구현부 ---

def show_login_screen():
    st.markdown("<h1 style='text-align: center; color: white;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    st.markdown("<style>body { background-color: #0F1117; }</style>", unsafe_allow_html=True)

    # 1행 3인 배치
    c1, c2, c3 = st.columns(3)
    rows = [c1, c2, c3]
    for i in range(3):
        m = family_members[i]
        with rows[i]:
            design = f"""
            <div style="background: #1F1F1F; border-radius: 20px; padding: 30px; text-align: center; border: 2px solid transparent; transition: 0.3s; color: white;">
                <div style="font-size: 55px;">{m['emoji']}</div>
                <div style="font-weight: bold; font-size: 20px; margin-top: 15px;">{m['name']}</div>
            </div>
            """
            render_html_card(m['id'], design)

    # 2행 2인 배치
    st.write("")
    c4, c5, c6, c7 = st.columns([1, 2, 2, 1])
    family_row2 = [family_members[3], family_members[4]]
    for i, m in enumerate(family_row2):
        with [c5, c6][i]:
            design = f"""
            <div style="background: #1F1F1F; border-radius: 20px; padding: 30px; text-align: center; border: 2px solid transparent; transition: 0.3s; color: white;">
                <div style="font-size: 55px;">{m['emoji']}</div>
                <div style="font-weight: bold; font-size: 20px; margin-top: 15px;">{m['name']}</div>
            </div>
            """
            render_html_card(m['id'], design)

    st.write("")
    # 일상 공유 배너
    sns_design = """
    <div style="background: linear-gradient(90deg, #3182f6, #4d94f7); border-radius: 24px; padding: 30px; color: white; display: flex; align-items: center;">
        <div style="font-size: 35px; margin-right: 25px;">📸</div>
        <div>
            <div style="font-size: 20px; font-weight: bold;">일상 공유하기</div>
            <div style="font-size: 15px; opacity: 0.9;">우리 가족의 소식을 확인하세요</div>
        </div>
        <div style="margin-left: auto; font-size: 24px;">❯</div>
    </div>
    """
    render_html_card("go_sns", sns_design, height=140)

def show_sns_page():
    if st.button("❮ 홈으로 돌아가기"):
        st.session_state['current_page'] = 'Home'; st.rerun()
    st.title("📸 가족 게시판")
    st.success("드디어 성공했습니다! 🎉")

# --- 5. 메인 컨트롤러 ---
if st.session_state['user_id'] is None and st.session_state['current_page'] == 'Home':
    show_login_screen()
elif st.session_state['current_page'] == 'FamilySNS':
    show_sns_page()
else:
    user = next(m for m in family_members if m['id'] == st.session_state['user_id'])
    st.markdown(f"# {user['emoji']} {user['name']}님 반가워요!")
    if st.button("로그아웃"):
        st.session_state['user_id'] = None; st.rerun()

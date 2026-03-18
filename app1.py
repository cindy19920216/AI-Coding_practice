import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# --- 1. 페이지 설정 및 토스 디자인 ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    .main .block-container { max-width: 800px; padding-top: 3rem; }

    /* 프로필 선택 카드 */
    .profile-card {
        background-color: white; border-radius: 20px; padding: 20px;
        text-align: center; transition: all 0.2s; cursor: pointer; border: 1px solid #e5e8eb;
    }
    .profile-card:hover { transform: translateY(-5px); border-color: #3182f6; }
    .profile-emoji { font-size: 40px; margin-bottom: 10px; }
    .profile-name { font-size: 16px; font-weight: 700; color: #191f28; }
    .profile-role { font-size: 12px; color: #8b95a1; }

    /* 토스형 메인 카드 */
    .toss-card {
        background-color: white; border-radius: 24px; padding: 24px; margin-bottom: 16px;
        display: flex; align-items: center; transition: all 0.2s; border: none; cursor: pointer;
    }
    .toss-card:hover { background-color: #EBF4FF; }
    .icon-box { width: 50px; height: 50px; background-color: #F9FAFB; border-radius: 14px; 
                display: flex; justify-content: center; align-items: center; font-size: 24px; margin-right: 15px; }
    .text-box { flex-grow: 1; }
    .title-text { font-size: 17px; font-weight: 700; color: #191F28; }
    .desc-text { font-size: 13px; color: #8B95A1; }
    
    .stButton>button { background: transparent; border: none; padding: 0; width: 100%; height: auto; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 세션 상태 관리 (누가 로그인했는지 기억) ---
if 'user_name' not in st.session_state:
    st.session_state['user_name'] = None
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'Home'

# 가족 데이터 정의
family_members = [
    {"id": "chanhee", "name": "찬희", "role": "아빠", "emoji": "👨🏻‍💻"},
    {"id": "jiwoo", "name": "지우", "role": "엄마", "emoji": "👩🏻‍💼"},
    {"id": "jaeseon", "name": "재선", "role": "큰딸", "emoji": "👩🏻‍🎨"},
    {"id": "gyubi", "name": "규비", "role": "작은딸", "emoji": "👧🏻"},
    {"id": "seunggyu", "name": "승규", "role": "막내", "emoji": "👦🏻"}
]

# --- 3. 페이지 함수 ---

# [화면 1] 프로필 선택 화면
def show_profile_selection():
    st.markdown("<h1 style='text-align: center; color: #191f28;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b95a1; margin-bottom: 40px;'>우리 가족 금융 매니저를 시작합니다</p>", unsafe_allow_html=True)
    
    cols = st.columns(5)
    for i, member in enumerate(family_members):
        with cols[i]:
            if st.button("", key=f"select_{member['id']}"):
                st.session_state['user_name'] = member['name']
                st.rerun()
            st.markdown(f"""
                <div class="profile-card">
                    <div class="profile-emoji">{member['emoji']}</div>
                    <div class="profile-name">{member['name']}</div>
                    <div class="profile-role">{member['role']}</div>
                </div>
            """, unsafe_allow_html=True)

# [화면 2] 홈화면
def show_home():
    user = st.session_state['user_name']
    
    # 상단 헤더 (로그아웃 버튼 포함)
    header_col, logout_col = st.columns([8, 2])
    with header_col:
        st.markdown(f"<h1>{user}님, 반가워요 👋</h1>", unsafe_allow_html=True)
    with logout_col:
        if st.button("다른 가족 선택", key="logout"):
            st.session_state['user_name'] = None
            st.rerun()

    st.markdown("<p style='color:#4E5968; margin-top:-10px;'>오늘 우리 가족의 금융 상태를 확인해 보세요.</p><br>", unsafe_allow_html=True)

    # 메뉴 리스트
    menu_items = [
        {"id": "Stock", "icon": "📈", "title": "주식 분석 대시보드", "desc": "전문가용 퀀트 지표 분석"},
        {"id": "Portfolio", "icon": "💰", "title": "가족 가상 포트폴리오", "desc": "우리 가족 투자 성적표"},
        {"id": "Edu", "icon": "🏫", "title": "쉬운 퀀트 투자 교실", "desc": "가족을 위한 투자 가이드"}
    ]

    for item in menu_items:
        with st.container():
            if st.button("", key=f"btn_{item['id']}"):
                st.session_state['current_page'] = item['id']
                st.rerun()
            st.markdown(f"""
                <div class="toss-card">
                    <div class="icon-box">{item['icon']}</div>
                    <div class="text-box">
                        <div class="title-text">{item['title']}</div>
                        <div class="desc-text">{item['desc']}</div>
                    </div>
                    <div style="color: #B0B8C1;">❯</div>
                </div>
            """, unsafe_allow_html=True)

# --- 4. 메인 컨트롤러 ---
if st.session_state['user_name'] is None:
    show_profile_selection()
else:
    if st.session_state['current_page'] == 'Home':
        show_home()
    elif st.session_state['current_page'] == 'Stock':
        if st.button("❮ 홈으로"): st.session_state['current_page'] = 'Home'; st.rerun()
        st.title(f"📈 {st.session_state['user_name']}님의 주식 분석")
        # 여기에 이전의 상세 주식 분석 코드를 연결
def show_profile_selection():
    st.markdown("<h1 style='text-align: center; color: #191f28; margin-top: 50px;'>누가 오셨나요?</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b95a1; margin-bottom: 40px;'>우리 가족 금융 매니저</p>", unsafe_allow_html=True)
    
    # 1. 가족 프로필 선택 (기존 코드)
    cols = st.columns(5)
    for i, member in enumerate(family_members):
        with cols[i]:
            if st.button("", key=f"select_{member['id']}"):
                st.session_state['user_id'] = member['id']
                st.session_state['user_name'] = member['name']
                st.rerun()
            st.markdown(f"""
                <div class="profile-card">
                    <div class="profile-emoji">{member['emoji']}</div>
                    <div class="profile-name">{member['name']}</div>
                    <div class="profile-role">{member['role']}</div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # 2. [NEW] 일상 공유하기 탭 (프로필과 유사한 UI/DX)
    st.markdown("<div style='max-width: 500px; margin: 0 auto;'>", unsafe_allow_html=True)
    
    # 버튼 기능을 위해 투명 버튼을 카드 위에 겹치는 방식
    if st.button("✨ 가족 일상 공유하러 가기", key="go_sns"):
        st.session_state['current_page'] = 'FamilySNS'
        st.rerun()
        
    st.markdown("""
        <div style="
            background-color: white; 
            border-radius: 20px; 
            padding: 20px; 
            display: flex; 
            align-items: center; 
            justify-content: center;
            border: 1px solid #e5e8eb;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            cursor: pointer;
            margin-top: -45px; /* 버튼 위치 조정을 위한 마진 */
        ">
            <div style="font-size: 24px; margin-right: 15px;">📸</div>
            <div style="text-align: left;">
                <div style="font-size: 16px; font-weight: 700; color: #191f28;">일상 공유하기</div>
                <div style="font-size: 13px; color: #8b95a1;">오늘 가족들에게 하고 싶은 말이 있나요?</div>
            </div>
            <div style="margin-left: auto; color: #B0B8C1;">❯</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- 새로운 페이지: FamilySNS 정의 ---
def show_family_sns():
    st.markdown("<h2 style='text-align:center;'>📸 일상 공유 </h2>", unsafe_allow_html=True)
    if st.button("❮ 뒤로가기"):
        st.session_state['current_page'] = 'Home'
        st.rerun()
    
    st.info("가족들이 올린 사진이나 짧은 글이 피드 형태로 나타나게 됩니다")

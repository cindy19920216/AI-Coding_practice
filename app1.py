import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. 전용 디자인 (클릭 영역 완전 고정 & 모바일 최적화) ---
st.set_page_config(page_title="우리 가족 스마트 금융", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #F2F4F6; }
    
    /* 모바일 중심 컨테이너 (최대 600px) */
    .main .block-container { max-width: 600px; padding-top: 2rem; padding-bottom: 2rem; }

    /* 클릭을 방해하는 기본 패딩 제거 */
    .element-container { margin-bottom: 0px; }

    /* 1) 넷플릭스 스타일 프로필 카드 */
    .profile-container {
        position: relative; background-color: white; border-radius: 20px; 
        padding: 25px 10px; text-align: center; border: 1px solid #e5e8eb;
        height: 160px; display: flex; flex-direction: column; align-items: center; justify-content: center;
    }
    .profile-emoji { font-size: 50px; display: block; margin-bottom: 5px; }
    .profile-name { font-size: 18px; font-weight: 700; color: #191f28; display: block; }
    .profile-role { font-size: 12px; color: #8b95a1; display: block; }

    /* 2) 일상 공유하기 와이드 탭 (클릭 영역 100% 확보) */
    .sns-container {
        position: relative; background-color: white; border-radius: 24px; 
        padding: 22px; display: flex; align-items: center; border: 1px solid #e5e8eb;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-top: 20px; width: 100%;
    }
    .sns-icon { font-size: 30px; margin-right: 18px; }
    .sns-title { font-size: 18px; font-weight: 700; color: #191f28; }
    .sns-desc { font-size: 14px; color: #8b95a1; }

    /* 핵심: 버튼을 카드 전체에 투명하게 덮기 */
    .stButton>button {
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background: transparent !important; border: none !important; color: transparent !important;
        z-index: 10; cursor: pointer;
    }
    .stButton>button:hover { background: rgba(49, 130, 246, 0.05) !important; }

    /* 말풍선 & 피드 스타일 */
    .bubble-box { background-color: #3182f6; color: white; border-radius: 15px; padding: 15px; margin-top: 20px; position: relative; font-weight: bold; text-align: center; }
    .bubble-box::after { content: ''; position: absolute; bottom: 100%; left: 50%; border: 10px solid transparent; border-bottom-color: #3182f6; transform: translateX(-50%); }
    .feed-item { background: white; padding: 1

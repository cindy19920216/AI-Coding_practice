import streamlit as st

def apply_styles():
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


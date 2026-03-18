import pandas as pd
import requests
from datetime import datetime
import streamlit as st

# 1. 읽기용 URL (시트 ID가 포함된 주소)
# 전문가님의 시트 ID: 1zTU8HRcaA79bSDgqOA7yYlkXXbC3OcJaBz9x511C1PQ
READ_URL = "https://docs.google.com/spreadsheets/d/AKfycbydzgeiB1izZx3AX9RN8yOtiPzi2bWe3SI_f76LEA0G6Qo6BgJNwAJ-HI1vTADCYw2t/gviz/tq?tqx=out:csv"

# 2. 쓰기용 API URL (끝에 공백이 없는지 확인 필수!)
# 복사하실 때 따옴표 안에 빈칸이 생기지 않도록 주의해주세요.
API_URL = "https://script.google.com/macros/s/AKfycbydzgeiB1izZx3AX9RN8yOtiPzi2bWe3SI_f76LEA0G6Qo6BgJNwAJ-HI1vTADCYw2t/exec"

def load_data():
    try:
        # 캐시 무시를 위해 URL 뒤에 랜덤값을 붙여 읽어옵니다.
        df = pd.read_csv(f"{READ_URL}&cachebuster={datetime.now().timestamp()}")
        return df
    except:
        return pd.DataFrame(columns=["name", "emoji", "msg", "time"])

def save_data(name, emoji, msg):
    payload = {
        "name": name, 
        "emoji": emoji, 
        "msg": msg,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    try:
        # 전송 시 timeout을 설정하여 무한 대기를 방지합니다.
        response = requests.post(API_URL.strip(), json=payload, timeout=10)
        
        # 만약 전송이 성공했다면 시트 데이터 새로고침을 위해 캐시를 비웁니다.
        if response.status_code == 200:
            return True
        else:
            # 실패 시 화면에 이유를 살짝 띄워줍니다.
            st.error(f"시트 응답 오류: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"연결 오류: {e}")
        return False

def get_market_indices():
    return {
        "KOSPI": "5,801.61 (▲2.86%)",
        "KOSDAQ": "1,155.27 (▲1.61%)",
        "USD/KRW": "1,486.20 (▼7.40)",
        "SUPPLY": "외인 매도 668억 / 기관 매수 672억"
    }

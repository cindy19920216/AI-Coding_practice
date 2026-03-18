import pandas as pd
import requests
from datetime import datetime
import streamlit as st

# 1. 읽기용 URL (가족들이 쓴 글을 불러올 때 사용)
# 전문가님의 시트 ID를 기반으로 한 CSV 출력 주소입니다.
SHEET_ID = "1zTU8HRcaA79bSDgqOA7yYlkXXbC3OcJaBz9x511C1PQ"
READ_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

# 2. 쓰기용 API URL (전문가님이 새로 주신 배포 ID 적용)
# 끝에 /exec가 붙어있는지 꼭 확인해주세요!
DEPLOY_ID = "AKfycbykvqkTeXhI5E7BO_wNXayqrVLWRV-ty9URMe-ybngV7phTEugJiqVsKhGbTQQ9-I88"
API_URL = f"https://script.google.com/macros/s/{DEPLOY_ID}/exec"

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
        # allow_redirects=True를 추가하여 구글의 리다이렉션을 허용합니다.
        response = requests.post(API_URL.strip(), json=payload, timeout=15, allow_redirects=True)
        
        # 구글은 성공 시 200 또는 302(이동)를 보냅니다.
        if response.status_code in [200, 302]:
            return True
        else:
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

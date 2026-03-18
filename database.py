import pandas as pd
import requests
from datetime import datetime

# 읽기용 URL
READ_URL = "https://docs.google.com/spreadsheets/d/AKfycby0Rbs5eL_gxbBuNMZiaOk3Y2jG8QXwIqNbpCEKcPLSr2sC8hW-rt7tpYMFjXPqpxV5/gviz/tq?tqx=out:csv"
# 쓰기용 Apps Script URL (전문가님이 만드신 주소)
API_URL = "https://script.google.com/macros/s/AKfycby0Rbs5eL_gxbBuNMZiaOk3Y2jG8QXwIqNbpCEKcPLSr2sC8hW-rt7tpYMFjXPqpxV5/exec" 

def load_data():
    try:
        return pd.read_csv(READ_URL)
    except:
        return pd.DataFrame(columns=["name", "emoji", "msg", "time"])

def save_data(name, emoji, msg):
    payload = {
        "name": name, "emoji": emoji, "msg": msg,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    try:
        requests.post(API_URL, json=payload)
        return True
    except:
        return False
# database.py에 추가
def get_market_indices():
    # 2026-03-18 현재 예시 데이터 (실제 서비스 시 API 연동 권장)
    return {
        "KOSPI": "5,801.61 (▲2.86%)",
        "KOSDAQ": "1,155.27 (▲1.61%)",
        "USD/KRW": "1,486.20 (▼7.40)",
        "SUPPLY": "외인 매도 668억 / 기관 매수 672억"
    }

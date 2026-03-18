import pandas as pd
import requests
from datetime import datetime

# [수정됨] 읽기용 URL: 시트의 실제 ID를 사용해야 합니다.
# 전문가님의 시트 ID: 1zTU8HRcaA79bSDgqOA7yYlkXXbC3OcJaBz9x511C1PQ
SHEET_ID = "AKfycbydzgeiB1izZx3AX9RN8yOtiPzi2bWe3SI_f76LEA0G6Qo6BgJNwAJ-HI1vTADCYw2t"
READ_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

# [유지] 쓰기용 Apps Script URL (이건 그대로 쓰시면 됩니다)
API_URL = "https://script.google.com/macros/s/AKfycbydzgeiB1izZx3AX9RN8yOtiPzi2bWe3SI_f76LEA0G6Qo6BgJNwAJ-HI1vTADCYw2t/exec"

def load_data():
    try:
        # 시트에서 데이터 읽기
        df = pd.read_csv(READ_URL)
        return df
    except Exception as e:
        # 에러가 날 경우 빈 데이터프레임 반환
        return pd.DataFrame(columns=["name", "emoji", "msg", "time"])

def save_data(name, emoji, msg):
    payload = {
        "name": name, 
        "emoji": emoji, 
        "msg": msg,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    try:
        # Apps Script로 전송
        response = requests.post(API_URL, json=payload)
        # 성공적으로 보냈는지 확인 (200번대가 성공)
        return response.status_code == 200
    except:
        return False

# 시장 지표 데이터 (아이콘 클릭 시 띠 노출용)
def get_market_indices():
    return {
        "KOSPI": "5,801.61 (▲2.86%)",
        "KOSDAQ": "1,155.27 (▲1.61%)",
        "USD/KRW": "1,486.20 (▼7.40)",
        "SUPPLY": "외인 매도 668억 / 기관 매수 672억"
    }

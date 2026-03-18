import pandas as pd
import requests
from datetime import datetime

# 읽기용 URL
READ_URL = "https://docs.google.com/spreadsheets/d/1zTU8HRcaA79bSDgqOA7yYlkXXbC3OcJaBz9x511C1PQ/gviz/tq?tqx=out:csv"
# 쓰기용 Apps Script URL (전문가님이 만드신 주소)
API_URL = "https://script.google.com/macros/s/AKfycbxyrGGYC9Ik-eBunTjyaSyvT5TK40G0XceCU-0oNKw/exec" 

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

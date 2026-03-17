import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="재선의 주식 대시보드", layout="wide")
st.title("📈 주식 데이터 분석 대시보드")

# 사이드바
ticker = st.sidebar.text_input("티커 입력 (예: AAPL, TSLA, 005930.KS)", value="AAPL")
days = st.sidebar.slider("분석 기간(일)", 30, 730, 365)
start_date = datetime.now() - timedelta(days=days)

# 데이터 로드
@st.cache_data
def load_data(symbol, start):
    df = yf.download(symbol, start=start)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

df = load_data(ticker, start_date)

if df is not None and not df.empty:
    # 지표 계산
    last_p = float(df['Close'].iloc[-1])
    prev_p = float(df['Close'].iloc[-2])
    chg = last_p - prev_p
    
    col1, col2 = st.columns(2)
    col1.metric("현재가", f"${last_p:.2f}", f"{chg:.2f}")
    col2.metric("거래량", f"{int(df['Volume'].iloc[-1]):,}")

    # 차트
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(template="plotly_dark", height=500, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("데이터를 찾을 수 없습니다. 티커를 확인해 주세요!")

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="금융 데이터 분석 대시보드", layout="wide")
st.title("📈 주식 데이터 분석 대시보드")

# 사이드바 설정
ticker = st.sidebar.text_input("주식 티커 입력 (예: AAPL, TSLA, 005930.KS)", value="AAPL")
start_date = st.sidebar.date_input("시작일", datetime.now() - timedelta(days=365))
end_date = st.sidebar.date_input("종료일", datetime.now())

@st.cache_data
def load_data(symbol, start, end):
    # 문제가 되었던 인자를 제거하고 기본형으로 다운로드합니다.
    df = yf.download(symbol, start=start, end=end)
    
    # 만약 데이터가 Multi-index로 들어오면 단일 레벨로 압축합니다.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    return df

data_load_state = st.text('데이터 불러오는 중...')
df = load_data(ticker, start_date, end_date)
data_load_state.text('데이터 로드 완료!')

if df is not None and not df.empty and len(df) > 1:
    # 1. 지표 계산 (안전하게 float 변환)
    last_close = float(df['Close'].iloc[-1])
    prev_close = float(df['Close'].iloc[-2])
    change = last_close - prev_close
    pct_change = (change / prev_close) * 100

    # 2. 상단 지표 표시
    col1, col2, col3 = st.columns(3)
    col1.metric("현재가", f"${last_close:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
    col2.metric("기간 내 최고가", f"${float(df['High'].max()):.2f}")
    col3.metric("거래량", f"{int(df['Volume'].iloc[-1]):,}")

    # 3. 차트 시각화
    st.subheader(f"{ticker} 주가 차트")
    
    ma_window = st.sidebar.slider("이동평균선(MA) 설정", 5, 100, 20)
    df['MA'] = df['Close'].rolling(window=ma_window).mean()

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'], 
        name='Price'
    ))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA'], line=dict(color='orange', width=1.5), name=f'{ma_window}일 이평선'))
    
    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=600)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("데이터 상세 보기"):
        st.write(df.tail(20))
else:
    st.warning("데이터를 불러오지 못했습니다. 티커(AAPL 등)를 다시 확인해 주세요.")

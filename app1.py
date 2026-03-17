import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator

# 1. 페이지 설정 및 폰트/스타일 적용
st.set_page_config(page_title="재선의 스마트 주식 대시보드", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Nanum Gothic', sans-serif;
        font-size: 0.8rem !important;
    }
    h1 { font-size: 1.8rem !important; }
    h2 { font-size: 1.4rem !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 JS 주식 분석 대시보드 ")

# 사이드바 설정
ticker = st.sidebar.text_input("티커 입력 (예: AAPL, 005930.KS)", value="AAPL")
days = st.sidebar.slider("분석 기간(일)", 30, 730, 365)
start_date = datetime.now() - timedelta(days=days)

# 번역 함수 정의
def translate_text(text, target_lang='ko'):
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except:
        return text

# RSI 계산 함수
def calculate_rsi(data, window=14):
    delta = data.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=window-1, adjust=False).mean()
    ema_down = down.ewm(com=window-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

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
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    df['RSI'] = calculate_rsi(df['Close'])

    # 차트 구성
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, subplot_titles=(f'{ticker} 주가 및 이평선', 'RSI'),
                        row_width=[0.3, 0.7])

    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    for ma, color in zip(['MA5', 'MA20', 'MA60', 'MA120'], ['yellow', 'orange', 'red', 'purple']):
        fig.add_trace(go.Scatter(x=df.index, y=df[ma], line=dict(width=1), name=ma), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='aqua', width=1.5), name='RSI'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

   # 3. 최신 뉴스 섹션 (에러 방지 로직 추가)
    st.subheader(f"📰 {ticker} 최신 뉴스 ")
    stock = yf.Ticker(ticker)
    
    try:
        news = stock.news
        if news:
            for item in news[:5]:
                # .get()을 사용하면 데이터가 없어도 에러가 나지 않고 None을 반환합니다.
                original_title = item.get('title') or item.get('summary') # 제목이 없으면 요약이라도 가져옴
                
                if original_title:
                    with st.container():
                        translated_title = translate_text(original_title)
                        st.write(f"**🇰🇷 {translated_title}**")
                        st.caption(f"원문: {original_title}")
                        
                        link = item.get('link', '#')
                        publisher = item.get('publisher', 'Unknown')
                        st.write(f"출처: {publisher} | [기사 원문 읽기]({link})")
                        st.write("---")
        else:
            st.info("현재 표시할 수 있는 최신 뉴스가 없습니다.")
    except Exception as e:
        st.warning("뉴스 데이터를 가져오는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
import feedparser
import urllib.parse

# 1. 페이지 설정 및 스타일
st.set_page_config(page_title="재선의 스마트 주식 대시보드", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Nanum Gothic', sans-serif;
        font-size: 0.8rem !important;
    }
    h1 { font-size: 2.2rem !important; font-weight: 700; margin-bottom: 0px; }
    /* 버튼 스타일 커스텀 */
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        background-color: #FF4B4B;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# 사이드바 설정
st.sidebar.header("⚙️ 설정")
# 입력 기능을 수행할 배너/버튼 구조
ticker_input = st.sidebar.text_input("티커 입력 (예: 005930.KS, AAPL)", value="005930.KS")
days = st.sidebar.slider("분석 기간(일)", 30, 730, 365)
run_button = st.sidebar.button("🚀 분석 시작") # 분석 시작 버튼

# 기능 함수들
def translate_text(text, target_lang='ko'):
    try:
        if any(ord('가') <= ord(char) <= ord('힣') for char in text): return text
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except: return text

def get_korean_news(search_term):
    encoded_search = urllib.parse.quote(search_term)
    rss_url = f"https://news.google.com/rss/search?q={encoded_search}&hl=ko&gl=KR&ceid=KR:ko"
    return feedparser.parse(rss_url).entries[:5]

def calculate_rsi(data, window=14):
    delta = data.diff()
    up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=window-1, adjust=False).mean()
    ema_down = down.ewm(com=window-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

@st.cache_data
def load_data(symbol, start):
    df = yf.download(symbol, start=start)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# 데이터 로드
start_date = datetime.now() - timedelta(days=days)
df = load_data(ticker_input, start_date)
stock_info = yf.Ticker(ticker_input)

try:
    company_full_name = stock_info.info.get('longName') or stock_info.info.get('shortName') or ticker_input
except:
    company_full_name = ticker_input

if df is not None and not df.empty:
    # 지표 계산
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    df['RSI'] = calculate_rsi(df['Close'])
    current_rsi = df['RSI'].iloc[-1]

    # RSI 상태 판별
    if current_rsi >= 70: rsi_status = "⚠️ 과매수 구간"
    elif current_rsi <= 30: rsi_status = "✅ 과매도 구간"
    else: rsi_status = "⚖️ 보통"

    # 2) 대시보드 제목을 기업 이름만 표시
    st.title(f"{company_full_name}")

    # 3) 주가 및 이평선 제목 지우기 (subplot_titles 수정)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, 
                        # RSI 차트 옆에 단어 표시 (부제목 활용)
                        subplot_titles=("", f"RSI: {current_rsi:.2f} ({rsi_status})"),
                        row_width=[0.3, 0.7])

    # 캔들스틱 (상승 빨강 / 하락 파랑)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='가격', increasing_line_color='#FF3232', decreasing_line_color='#0066FF'
    ), row=1, col=1)
    
    # 이평선
    ma_colors = {'MA5': '#FF4500', 'MA20': '#1E90FF', 'MA60': '#32CD32', 'MA120': '#FF69B4'}
    for ma, color in ma_colors.items():
        fig.add_trace(go.Scatter(x=df.index, y=df[ma], line=dict(color=color, width=1.2), name=ma), row=1, col=1)

    # RSI (파랑, 1pt)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['RSI'], line=dict(color='#0000FF', width=1), name='RSI'
    ), row=2, col=1)
    
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="blue", row=2, col=1)

    fig.update_layout(template="plotly_white", height=650, xaxis_rangeslider_visible=False, margin=dict(t=30))
    st.plotly_chart(fig, use_container_width=True)

    # 뉴스 섹션
    st.subheader(f"📰 관련 최신 뉴스")
    search_keyword = company_full_name if ".KS" in ticker_input or ".KQ" in ticker_input else ticker_input
    news_items = get_korean_news(search_keyword)
    
    if news_items:
        for item in news_items:
            with st.container():
                display_title = translate_text(item.title)
                st.write(f"**🔗 {display_title}**")
                st.write(f"게시일: {item.published} | [기사 보기]({item.link})")
                st.write("---")
else:
    st.error("데이터 로드 실패.")

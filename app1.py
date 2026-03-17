import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
import feedparser
import urllib.parse

# 1. 페이지 설정 및 스타일 (나눔고딕 & 20% 축소)
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

# 사이드바 설정
st.sidebar.header("⚙️ 설정")
ticker = st.sidebar.text_input("티커 입력 (예: 005930.KS, AAPL)", value="005930.KS")
days = st.sidebar.slider("분석 기간(일)", 30, 730, 365)
start_date = datetime.now() - timedelta(days=days)

# --- 기능 함수 ---
def translate_text(text, target_lang='ko'):
    """영문 텍스트를 한국어로 번역 (한글은 그대로 유지)"""
    try:
        # 텍스트에 한글이 포함되어 있는지 확인 (한글이 있으면 번역 생략)
        if any(ord('가') <= ord(char) <= ord('힣') for char in text):
            return text
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except:
        return text

def get_korean_news(search_term):
    """구글 뉴스 RSS를 이용해 뉴스를 가져옵니다."""
    encoded_search = urllib.parse.quote(search_term)
    rss_url = f"https://news.google.com/rss/search?q={encoded_search}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(rss_url)
    return feed.entries[:5]

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
df = load_data(ticker, start_date)
stock_info = yf.Ticker(ticker)

try:
    company_name = stock_info.info.get('longName') or stock_info.info.get('shortName') or ticker
except:
    company_name = ticker

if df is not None and not df.empty:
    # 지표 계산
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    df['RSI'] = calculate_rsi(df['Close'])
    current_rsi = df['RSI'].iloc[-1]

    st.title(f"📈 {company_name} 분석 대시보드")

    # 차트 구성
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, 
                        subplot_titles=(f'{company_name} 주가 및 이평선', f'RSI (현재: {current_rsi:.2f})'),
                        row_width=[0.3, 0.7])

    # 1. 캔들스틱 (상승 빨강 / 하락 파랑)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='가격', increasing_line_color='#FF3232', decreasing_line_color='#0066FF'
    ), row=1, col=1)
    
    # 2. 이평선 (빨강, 파랑, 초록, 분홍)
    ma_colors = {'MA5': '#FF4500', 'MA20': '#1E90FF', 'MA60': '#32CD32', 'MA120': '#FF69B4'}
    for ma, color in ma_colors.items():
        fig.add_trace(go.Scatter(x=df.index, y=df[ma], line=dict(color=color, width=1.2), name=ma), row=1, col=1)

    # 3. RSI (파란색, 1pt 굵기)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['RSI'], 
        line=dict(color='#0000FF', width=1), # 파란색 및 1pt 설정
        name='RSI'
    ), row=2, col=1)
    
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="blue", row=2, col=1)

    fig.update_layout(template="plotly_white", height=700, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # 4. 뉴스 섹션 (번역 적용)
    st.subheader(f"📰 {company_name} 최신 뉴스")
    search_keyword = company_name if ".KS" in ticker or ".KQ" in ticker else ticker
    news_items = get_korean_news(search_keyword)
    
    if news_items:
        for item in news_items:
            with st.container():
                # 구글 뉴스 제목도 혹시 모를 영문을 대비해 번역 함수 통과
                display_title = translate_text(item.title)
                st.write(f"**🔗 {display_title}**")
                if display_title != item.title:
                    st.caption(f"원문: {item.title}")
                st.write(f"게시일: {item.published} | [기사 보기]({item.link})")
                st.write("---")
    else:
        st.write("최신 뉴스를 가져올 수 없습니다.")
else:
    st.error("데이터 로드 실패.")

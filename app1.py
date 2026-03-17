import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator

# 1. 페이지 설정 및 스타일
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
ticker = st.sidebar.text_input("티커 입력 (예: AAPL, 005930.KS)", value="AAPL")
days = st.sidebar.slider("분석 기간(일)", 30, 730, 365)
start_date = datetime.now() - timedelta(days=days)

# 기능 함수들
def translate_text(text, target_lang='ko'):
    try: return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except: return text

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

# 데이터 및 기업 정보 가져오기
df = load_data(ticker, start_date)
stock_info = yf.Ticker(ticker)
company_name = stock_info.info.get('longName', ticker) # 기업 전체 이름 가져오기

if df is not None and not df.empty:
    # 지표 계산
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    df['RSI'] = calculate_rsi(df['Close'])
    current_rsi = df['RSI'].iloc[-1] # 현재 RSI 수치

    st.title(f"📈 {company_name} 분석 대시보드")

    # 차트 구성 (상승: 빨강 / 하락: 파랑 테마 적용)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, 
                        subplot_titles=(f'{company_name} 주가 및 이평선', f'RSI (현재 수치: {current_rsi:.2f})'),
                        row_width=[0.3, 0.7])

    # 캔들스틱 차트 (빨강/파랑 색상 변경)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='가격',
        increasing_line_color='#FF3232', # 상승 빨강
        decreasing_line_color='#0066FF'  # 하락 파랑
    ), row=1, col=1)
    
    # 이평선 색상 설정 (빨강, 파랑, 초록, 분홍)
    ma_colors = {'MA5': '#FF4500', 'MA20': '#1E90FF', 'MA60': '#32CD32', 'MA120': '#FF69B4'}
    for ma, color in ma_colors.items():
        fig.add_trace(go.Scatter(x=df.index, y=df[ma], line=dict(color=color, width=1.2), name=ma), row=1, col=1)

    # RSI 차트 (검은색 변경)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='black', width=2), name='RSI'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="blue", row=2, col=1)

    fig.update_layout(template="plotly_white", height=700, xaxis_rangeslider_visible=False) # 가독성을 위해 화이트 테마 적용 가능
    st.plotly_chart(fig, use_container_width=True)

    # 뉴스 섹션
    st.subheader(f"📰 {company_name} 최신 뉴스")
    try:
        news = stock_info.news
        if news:
            for item in news[:5]:
                title = item.get('title') or item.get('summary')
                if title:
                    with st.container():
                        st.write(f"**🇰🇷 {translate_text(title)}**")
                        st.caption(f"원문: {title}")
                        st.write(f"출처: {item.get('publisher')} | [기사 원문]({item.get('link', '#')})")
                        st.write("---")
    except:
        st.write("뉴스를 불러올 수 없습니다.")
else:
    st.error("데이터 로드 실패.")

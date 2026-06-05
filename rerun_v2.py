# -*- coding: utf-8 -*-
"""
v2 재실행 스크립트
- 기존 news_monthly.csv / sentiment_result.csv 재사용 (Gemini API 불필요)
- STEP 4: 뉴스 감성점수 기반 테마 재선정
- STEP 5: 텔레그램 언급량 피처 (신규)
- STEP 6: 주가 수집 + 거래량·52주고점·KOSPI상대강도 (신규)
          KRX300→KRX500 자동 확장 / TICKER_MAP 보완
- STEP 7: 전체 병합
- STEP 8: XGBoost 12개 피처
- STEP 9: 랭킹 + 시각화 7종
"""

import os, re, time, sys
from datetime import datetime
from collections import Counter

import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

import yfinance as yf
import FinanceDataReader as fdr
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, roc_auc_score

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR     = r'C:\Users\Check\Desktop\AI 금융_FINAL'
RESULT_PATH  = os.path.join(BASE_DIR, 'results')
TG_DATA_PATH = os.path.join(BASE_DIR, 'telegram_data')

TOP_N                = 5
KRX300_TOP_N         = 300
KRX500_TOP_N         = 500
MIN_STOCKS_PER_THEME = 3

TICKER_MAP = {
    '스페이스X': {
        '켄코아에어로스페이스': '274400',
        '한화시스템':         '272210',
        '쎄트렉아이':         '099440',
        '한화에어로스페이스':  '012450',
        '스피어':             '348170',
        '인텔리안테크':        '189300',
    },
    '화이자': {
        '유한양행':   '000100',
        '한미약품':   '128940',
        '보령':       '003850',
        '종근당':     '185750',
        '대웅제약':   '069620',
    },
    '두나무': {
        '우리기술투자':       '041190',
        '에이티넘인베스트먼트': '021080',
        '한화투자증권':       '003530',
        '네오위즈홀딩스':     '095660',
        '카카오':             '035720',
    },
    'HBM': {
        '삼성전자':     '005930',
        'SK하이닉스':   '000660',
        '한미반도체':   '042700',
        '피에스케이홀딩스': '031980',
        '테크윙':       '089030',
        '케이씨텍':     '281820',
        '이오테크닉스':  '039030',
        'ISC':         '095340',
        '와이씨':       '232140',
        '고영':         '098460',
        '한화비전':     '489790',
    },
    '조선': {
        'HD한국조선해양': '009540',
        '삼성중공업':    '010140',
        '한화오션':     '042660',
        'HD현대중공업':  '329180',
        'HD현대미포':    '010620',
        'HJ중공업':     '097230',
    },
    'LNG': {
        '한국가스공사':   '036460',
        'SK가스':       '018670',
        '한화엔진':      '082740',
        '비에이치아이':   '083650',
    },
}

FEATURES = [
    'sentiment_score', 'sentiment_ma3', 'sentiment_ma5', 'news_count',
    'stock_sentiment',
    'return_1d', 'return_5d',
    'volume_change', 'high_52w_ratio', 'kospi_relative',
    'tg_mention_count', 'tg_mention_ma3', 'tg_news_ratio',
]
TARGET = 'up_next'

# 테마명 자체가 너무 일반적인 단어 → 종목명 직접 언급만 카운트
# 통신: "광통신", "무선통신" 등 False Positive 방지
# 조선: "조선일보", "조선왕조" 등 비투자 컨텍스트 방지
THEME_STOCK_ONLY = {'통신', '조선'}

# 2글자 이하 짧은 종목명 목록 (단어 경계 매칭 필요)
SHORT_TICKERS = {'KT', 'SK', 'GS', 'LG', 'NC', 'SI'}


def _build_tg_pattern(theme: str, stocks: list) -> str | None:
    """
    텔레그램 검색 패턴 생성.
    - THEME_STOCK_ONLY 테마: 테마명 제외, 종목명만 사용
    - SHORT_TICKERS: 앞뒤 비한글·비알파벳 경계 적용
    """
    parts = []
    if theme not in THEME_STOCK_ONLY:
        parts.append(re.escape(theme))
    for s in stocks:
        if len(s) <= 1:
            continue
        if s in SHORT_TICKERS:
            # 앞뒤가 한글·영문·숫자가 아닌 경우만 매칭
            parts.append(r'(?<![가-힣A-Za-z0-9])' + re.escape(s) + r'(?![가-힣A-Za-z0-9])')
        else:
            parts.append(re.escape(s))
    return '|'.join(parts) if parts else None

# ──────────────────────────────────────────────────────────────
# 기존 결과 로드
# ──────────────────────────────────────────────────────────────
print("=" * 60)
print("기존 CSV 로드")
print("=" * 60)

monthly_top_df = pd.read_csv(os.path.join(RESULT_PATH, 'monthly_top_themes.csv'))
sentiment_df   = pd.read_csv(os.path.join(RESULT_PATH, 'sentiment_result.csv'))
sentiment_df['date'] = pd.to_datetime(sentiment_df['date'], errors='coerce')

# Derive all_themes from sentiment_df to include all themes with news data
all_themes = set(sentiment_df['theme'].unique())

# monthly_tops: {str_month: [theme, ...]}
monthly_tops_str = {}
for _, row in monthly_top_df.iterrows():
    m = str(row['month'])
    # Only keep themes that are in all_themes (have news)
    if row['theme'] in all_themes:
        monthly_tops_str.setdefault(m, []).append(row['theme'])

print(f"로드 완료: {len(monthly_tops_str)}개월 / 테마: {sorted(all_themes)}")
print(f"감성 분석: {len(sentiment_df):,}건")

# ──────────────────────────────────────────────────────────────
# 네이버 테마 코드맵 수집 + TICKER_MAP 보완
# ──────────────────────────────────────────────────────────────
print("\n네이버 테마 종목 코드 수집 중...")
headers        = {'User-Agent': 'Mozilla/5.0'}
theme_map      = {}   # {theme: [stock_name]}
theme_code_map = {}   # {theme: {stock_name: code}}

for page in range(1, 11):
    url = f"https://finance.naver.com/sise/theme.naver?&page={page}"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'euc-kr'
        soup  = BeautifulSoup(res.text, 'html.parser')
        links = soup.select('td.col_type1 a')
        if not links:
            break
        for link in links:
            theme_name = re.sub(r'\(.*?\)', '', link.text).strip()
            if theme_name not in all_themes:
                continue
            detail_url = "https://finance.naver.com" + link['href']
            try:
                d = requests.get(detail_url, headers=headers, timeout=10)
                d.encoding = 'euc-kr'
                ds   = BeautifulSoup(d.text, 'html.parser')
                tags = ds.find_all('a', href=re.compile(r'/item/main\.naver\?code=\d{6}'))
                names, codes, seen = [], {}, set()
                for s in tags:
                    sname  = s.text.strip()
                    m_obj  = re.search(r'code=(\d{6})', s.get('href', ''))
                    if sname and m_obj and m_obj.group(1) not in seen:
                        code = m_obj.group(1)
                        names.append(sname)
                        codes[sname] = code
                        seen.add(code)
                theme_map[theme_name]      = names
                theme_code_map[theme_name] = codes
                print(f"  [{theme_name}] {len(codes)}종목")
                time.sleep(0.15)
            except Exception:
                continue
    except Exception as e:
        print(f"  page {page} 실패: {e}"); break

# TICKER_MAP 보완
for theme, ticker_dict in TICKER_MAP.items():
    if theme not in all_themes:
        continue
    if theme not in theme_map:
        theme_map[theme]      = list(ticker_dict.keys())
        theme_code_map[theme] = dict(ticker_dict)
    else:
        for stock, code in ticker_dict.items():
            if stock not in theme_map[theme]:
                theme_map[theme].append(stock)
            theme_code_map.setdefault(theme, {})[stock] = code

print(f"코드 수집 완료: {len(theme_code_map)}개 테마")

# ──────────────────────────────────────────────────────────────
# STEP 3.5. 텔레그램 기반 월별 TOP 테마 재산출 (수정된 키워드 로직)
# - 통신/조선 등 일반 단어 False Positive 제거
# - 짧은 종목명(KT 등) 단어 경계 적용
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3.5. 텔레그램 월별 TOP 테마 재산출 (노이즈 필터 적용)")
print("=" * 60)

from collections import Counter as _Counter

_tg_files_all = sorted([
    os.path.join(TG_DATA_PATH, f) for f in os.listdir(TG_DATA_PATH)
    if f.startswith('telegram_data_') and f.endswith('.csv')
])
_tg_raw = pd.concat([pd.read_csv(f) for f in _tg_files_all], ignore_index=True)
_tg_raw['Date']    = pd.to_datetime(_tg_raw['Date'])
_tg_raw['month']   = _tg_raw['Date'].dt.to_period('M').astype(str)
_tg_raw['Message'] = _tg_raw['Message'].astype(str)

# 테마별 검색 패턴 사전 컴파일
_compiled = {}
for _theme in all_themes:
    _stocks = theme_map.get(_theme, [])
    _pat    = _build_tg_pattern(_theme, _stocks)
    if _pat:
        try:
            _compiled[_theme] = re.compile(_pat)
        except re.error:
            _compiled[_theme] = re.compile(re.escape(_theme))

monthly_tops_str = {}   # 기존 CSV 기반 데이터 덮어쓰기
for _month in sorted(_tg_raw['month'].unique()):
    if _month == '2026-06':
        continue
    _msgs   = _tg_raw[_tg_raw['month'] == _month]['Message'].tolist()
    _counts = _Counter()
    for _msg in _msgs:
        _seen = set()
        for _theme, _cpat in _compiled.items():
            if _theme in _seen:
                continue
            if _cpat.search(_msg):
                _counts[_theme] += 1
                _seen.add(_theme)
    _top = [t for t, _ in _counts.most_common(TOP_N * 2)]  # 여유분 확보
    monthly_tops_str[_month] = _top
    _top_display = [f"{t}({_counts[t]})" for t in _top[:TOP_N]]
    print(f"  {_month}: {' / '.join(_top_display)}")

print(f"\n[통신 월별 순위 확인]")
for _m, _tops in sorted(monthly_tops_str.items()):
    _rank = _tops.index('통신') + 1 if '통신' in _tops else '-'
    print(f"  {_m}: 통신 순위={_rank}")

# ──────────────────────────────────────────────────────────────
# STEP 4. 뉴스 감성점수 기반 테마 재선정
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 4. 뉴스 감성점수 기반 테마 재선정")
print("=" * 60)

monthly_tops_final = {}
for month_str, candidates in sorted(monthly_tops_str.items()):
    sub = sentiment_df[sentiment_df['month'] == month_str]
    if sub.empty:
        monthly_tops_final[month_str] = candidates[:TOP_N]
        print(f"  {month_str}: 데이터 없음 → 기존 순위 유지")
        continue

    scores = []
    for theme in candidates:
        tsub = sub[sub['theme'] == theme]
        if tsub.empty:
            scores.append({'theme': theme, 'total': 0.0, 'pos_ratio': 0.0})
            continue
        scores.append({
            'theme': theme,
            'total': float(tsub['score'].sum()),
            'pos_ratio': float((tsub['score'] > 0).mean()),
        })

    sdf = pd.DataFrame(scores)
    rng = sdf['total'].max() - sdf['total'].min()
    sdf['norm']  = (sdf['total'] - sdf['total'].min()) / (rng if rng > 0 else 1)
    sdf['final'] = sdf['pos_ratio'] * 0.6 + sdf['norm'] * 0.4
    top = sdf.sort_values('final', ascending=False)['theme'].tolist()[:TOP_N]
    for c in candidates:
        if c not in top and len(top) < TOP_N:
            top.append(c)
    monthly_tops_final[month_str] = top
    print(f"  {month_str}: {' / '.join(top)}")

# Ensure all themes with news data (including MLCC) are included for analysis
all_final_themes = all_themes

# ──────────────────────────────────────────────────────────────
# STEP 5. 텔레그램 언급량 피처 생성
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 5. 텔레그램 언급량 피처 생성")
print("=" * 60)

tg_files = [
    os.path.join(TG_DATA_PATH, f) for f in os.listdir(TG_DATA_PATH)
    if f.startswith('telegram_data_') and f.endswith('.csv')
]
tg_feat = pd.DataFrame(columns=['date', 'theme', 'tg_mention_count', 'tg_mention_ma3'])

if tg_files:
    tg_df = pd.concat([pd.read_csv(f) for f in sorted(tg_files)], ignore_index=True)
    tg_df['Date']    = pd.to_datetime(tg_df['Date'])
    tg_df['Message'] = tg_df['Message'].astype(str)

    all_rows = []
    for theme in all_final_themes:
        stocks  = theme_map.get(theme, [])
        pattern = _build_tg_pattern(theme, stocks)
        if pattern is None:
            print(f"  [{theme}] 패턴 없음 - skip")
            continue
        try:
            mask = tg_df['Message'].str.contains(pattern, na=False, regex=True)
        except re.error:
            mask = tg_df['Message'].str.contains(re.escape(theme), na=False)
        daily = (
            tg_df[mask]
            .groupby(tg_df.loc[mask, 'Date'].dt.normalize())
            .size()
            .reset_index(name='tg_mention_count')
        )
        daily.columns = ['date', 'tg_mention_count']
        daily['theme'] = theme
        all_rows.append(daily)
        print(f"  [{theme}] {daily['tg_mention_count'].sum():.0f}건 언급")

    if all_rows:
        tg_feat = pd.concat(all_rows, ignore_index=True).sort_values(['theme', 'date'])
        tg_feat['tg_mention_ma3'] = (
            tg_feat.groupby('theme')['tg_mention_count']
            .transform(lambda x: x.rolling(3, min_periods=1).mean())
        )
        tg_feat['date'] = pd.to_datetime(tg_feat['date']).dt.normalize()
        print(f"텔레그램 피처: {len(tg_feat):,}행")
else:
    print("텔레그램 CSV 없음 → 피처 0으로 대체")

# ──────────────────────────────────────────────────────────────
# STEP 6. 주가 수집 (거래량·52주·KOSPI 상대강도)
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 6. 주가 수집 (신규 피처 포함)")
print("=" * 60)

def _get_krx_codes(top_n):
    try:
        frames = []
        for market in ['KOSPI', 'KOSDAQ']:
            df = fdr.StockListing(market)
            if 'Code' in df.columns and 'Marcap' in df.columns:
                frames.append(df[['Code', 'Marcap']].dropna())
        combined = pd.concat(frames, ignore_index=True)
        combined['Marcap'] = pd.to_numeric(combined['Marcap'], errors='coerce')
        top   = combined.nlargest(top_n, 'Marcap')
        codes = set(str(c).zfill(6) for c in top['Code'])
        print(f"  시총 상위 {top_n}종목 {len(codes)}개 코드 확보")
        return codes
    except Exception as e:
        print(f"  조회 실패: {e}")
        return set()

def _get_kospi(start_dt, end_dt):
    raw = yf.download('^KS11', start=start_dt, end=end_dt, progress=False, auto_adjust=True)
    if raw.empty:
        return pd.DataFrame(columns=['date', 'kospi_return'])
    df = pd.DataFrame({'kospi_close': raw['Close'].squeeze()})
    df['kospi_return'] = df['kospi_close'].pct_change()
    df.index.name = 'date'
    df = df.reset_index()
    df['date'] = pd.to_datetime(df['date']).dt.normalize()
    return df[['date', 'kospi_return']]

def _download_stock(code, start, end):
    for suffix in ['.KS', '.KQ']:
        try:
            raw = yf.download(code + suffix, start=start, end=end,
                              progress=False, auto_adjust=True)
            if not raw.empty:
                want = [c for c in ['Close', 'High', 'Volume'] if c in raw.columns]
                return raw[want].copy(), code + suffix
        except Exception:
            continue
    return pd.DataFrame(), None

print("KRX300 코드 조회...")
krx300 = _get_krx_codes(KRX300_TOP_N)
print("KRX500 코드 조회...")
krx500 = _get_krx_codes(KRX500_TOP_N)

month_keys  = sorted(monthly_tops_final.keys())
start_str   = month_keys[0]
start_dt    = f"{start_str[:4]}-{start_str[5:7]}-01"
end_dt      = datetime.now().strftime('%Y-%m-%d')

print(f"\nKOSPI 지수 수집 ({start_dt} ~ {end_dt})...")
kospi_df = _get_kospi(start_dt, end_dt)
print(f"KOSPI {len(kospi_df)}일")

all_data = []
for theme in all_final_themes:
    code_dict = theme_code_map.get(theme, {})
    if not code_dict:
        print(f"\n[{theme}] 코드 없음 - skip")
        continue

    large_dict = {n: c for n, c in code_dict.items() if c in krx300}
    label = 'KRX300'
    if len(large_dict) < MIN_STOCKS_PER_THEME:
        large_dict = {n: c for n, c in code_dict.items() if c in krx500}
        label = 'KRX500(확장)'

    print(f"\n[{theme}] 전체 {len(code_dict)}개 → {label} {len(large_dict)}개")
    if not large_dict:
        print("  종목 없음 - skip")
        continue

    for sname, code in large_dict.items():
        raw, ticker = _download_stock(code, start_dt, end_dt)
        if raw.empty:
            continue

        df = pd.DataFrame(index=raw.index)
        df['close']  = raw['Close'].squeeze()  if 'Close'  in raw.columns else np.nan
        df['high']   = raw['High'].squeeze()   if 'High'   in raw.columns else np.nan
        df['volume'] = raw['Volume'].squeeze()  if 'Volume' in raw.columns else np.nan
        df.index.name = 'date'
        df = df.reset_index()
        df['date'] = pd.to_datetime(df['date']).dt.normalize()

        df['return_1d']      = df['close'].pct_change()
        df['return_5d']      = df['close'].pct_change(5)
        df['up_next']        = (df['return_1d'].shift(-1) > 0).astype(int)
        df['volume_change']  = df['volume'].pct_change()
        df['high_52w']       = df['high'].rolling(252, min_periods=1).max()
        df['high_52w_ratio'] = df['close'] / df['high_52w'].replace(0, np.nan)

        # RSI 14일
        _delta = df['close'].diff()
        _gain  = _delta.clip(lower=0).rolling(14, min_periods=1).mean()
        _loss  = (-_delta.clip(upper=0)).rolling(14, min_periods=1).mean()
        df['rsi_14'] = 100 - (100 / (1 + _gain / _loss.replace(0, np.nan)))

        # 볼린저밴드 위치: (close - lower) / (upper - lower)
        _ma20  = df['close'].rolling(20, min_periods=1).mean()
        _std20 = df['close'].rolling(20, min_periods=1).std().replace(0, np.nan)
        df['bb_position']  = (df['close'] - (_ma20 - 2 * _std20)) / (4 * _std20)

        # 20일 수익률 변동성 (개별 종목 리스크)
        df['volatility_20'] = df['return_1d'].rolling(20, min_periods=5).std()

        # 20일 이동평균 대비 현재가 (추세 위치)
        df['ma_ratio'] = df['close'] / _ma20.replace(0, np.nan)

        df['stock']  = sname
        df['ticker'] = ticker
        df['theme']  = theme
        all_data.append(df)
        print(f"  {sname}({ticker}): {len(df)}일")
        time.sleep(0.1)

if not all_data:
    raise ValueError("주가 데이터 없음")

stock_df = pd.concat(all_data, ignore_index=True)

if not kospi_df.empty:
    stock_df = pd.merge(stock_df, kospi_df, on='date', how='left')
    stock_df['kospi_relative'] = stock_df['return_1d'] - stock_df['kospi_return']
else:
    stock_df['kospi_relative'] = np.nan

print(f"\n주가 수집 완료: {stock_df['stock'].nunique()}개 종목 / {stock_df['theme'].nunique()}개 테마")

# ──────────────────────────────────────────────────────────────
# 거래일 캘린더 + 헬퍼 함수
# ──────────────────────────────────────────────────────────────
_trading_days = np.sort(stock_df['date'].dropna().unique())

def _next_trading_day(dates: pd.Series) -> pd.Series:
    """달력 +1일 대신 실제 다음 거래일 반환 (주말·휴장일 자동 스킵)"""
    result = []
    for d in pd.to_datetime(dates):
        if pd.isna(d):
            result.append(pd.NaT)
            continue
        idx = np.searchsorted(_trading_days, np.datetime64(d), side='right')
        result.append(pd.Timestamp(_trading_days[idx]) if idx < len(_trading_days) else pd.NaT)
    return pd.Series(result, index=dates.index, dtype='datetime64[ns]')

def _compute_stock_sentiment(sent_df: pd.DataFrame, tmap: dict) -> pd.DataFrame:
    """기사 제목에서 종목명 탐색 → 종목별 일별 감성점수 산출"""
    rows = []
    for theme, stocks in tmap.items():
        tsub = sent_df[sent_df['theme'] == theme]
        if tsub.empty:
            continue
        for stock in stocks:
            if len(stock) < 2:
                continue
            mask = tsub['title'].str.contains(re.escape(stock), na=False)
            if mask.sum() < 2:
                continue
            matched = tsub.loc[mask, ['date', 'score']].copy()
            matched['stock'] = stock
            rows.append(matched)
    if not rows:
        print("  종목 직접 언급 기사 없음 → sentiment_score로 대체")
        return pd.DataFrame(columns=['date', 'stock', 'stock_sentiment'])
    df = pd.concat(rows, ignore_index=True)
    df['date'] = pd.to_datetime(df['date']).dt.normalize()
    out = (df.groupby(['date', 'stock'])['score']
             .mean().reset_index()
             .rename(columns={'score': 'stock_sentiment'}))
    print(f"  종목 직접 언급 기사: {len(df)}건 / {out['stock'].nunique()}개 종목")
    return out

# ──────────────────────────────────────────────────────────────
# STEP 7. 전체 병합
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 7. 감성 + 텔레그램 + 주가 병합")
print("=" * 60)

sent = (
    sentiment_df
    .groupby([pd.Grouper(key='date', freq='D'), 'theme'])['score']
    .agg(sentiment_score='mean', news_count='count')
    .reset_index()
)
sent['date']      = pd.to_datetime(sent['date']).dt.normalize()
sent['date_next'] = _next_trading_day(sent['date'])
sent = sent.dropna(subset=['date_next'])
print(f"  거래일 기준 매핑: {len(sent)}건 (주말·휴장일 자동 스킵)")

merged = pd.merge(
    stock_df,
    sent[['date_next', 'theme', 'sentiment_score', 'news_count']],
    left_on=['date', 'theme'], right_on=['date_next', 'theme'], how='inner'
).drop(columns=['date_next'])

merged = merged.sort_values(['stock', 'date'])
for w in [3, 5]:
    merged[f'sentiment_ma{w}'] = (
        merged.groupby('stock')['sentiment_score']
        .transform(lambda x: x.rolling(w, min_periods=1).mean())
    )

if not tg_feat.empty:
    merged = pd.merge(
        merged,
        tg_feat[['date', 'theme', 'tg_mention_count', 'tg_mention_ma3']],
        on=['date', 'theme'], how='left'
    )
else:
    merged['tg_mention_count'] = 0
    merged['tg_mention_ma3']   = 0

merged['tg_mention_count'] = merged['tg_mention_count'].fillna(0)
merged['tg_mention_ma3']   = merged['tg_mention_ma3'].fillna(0)
merged['tg_news_ratio']    = merged['tg_mention_count'] / (merged['news_count'] + 1)

# 종목별 감성점수 병합 (기사에서 종목명 직접 언급된 경우에만 반영)
print("\n종목별 감성점수 산출 중...")
stock_sent_df = _compute_stock_sentiment(sentiment_df, theme_map)
if not stock_sent_df.empty:
    stock_sent_df['date_trading'] = _next_trading_day(stock_sent_df['date'])
    stock_sent_df = stock_sent_df.dropna(subset=['date_trading'])
    merged = pd.merge(
        merged,
        stock_sent_df[['date_trading', 'stock', 'stock_sentiment']],
        left_on=['date', 'stock'], right_on=['date_trading', 'stock'],
        how='left'
    ).drop(columns=['date_trading'])
else:
    merged['stock_sentiment'] = np.nan
# 언급 없는 종목은 테마 감성점수로 대체
merged['stock_sentiment'] = merged['stock_sentiment'].fillna(merged['sentiment_score'])

merged = merged.dropna(subset=['return_1d', 'sentiment_score'])
print(f"병합 완료: {len(merged):,}행 / {merged['stock'].nunique()}개 종목")

# ──────────────────────────────────────────────────────────────
# STEP 8. XGBoost (12개 피처)
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 8. XGBoost 학습 (13개 피처)")
print("=" * 60)

avail   = [f for f in FEATURES if f in merged.columns]
# inf → NaN 치환 (volume_change·high_52w_ratio 등 division 이슈)
merged[avail] = merged[avail].replace([np.inf, -np.inf], np.nan)
df_xgb  = merged.dropna(subset=avail + [TARGET]).copy()
print(f"사용 피처 {len(avail)}개: {avail}")
print(f"학습 데이터: {len(df_xgb):,}행")

X, y  = df_xgb[avail].values, df_xgb[TARGET].values
aucs, model = [], None

for tr_idx, val_idx in TimeSeriesSplit(n_splits=5).split(X):
    if len(val_idx) == 0:
        continue
    m = XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        eval_metric='logloss', random_state=42, verbosity=0
    )
    m.fit(X[tr_idx], y[tr_idx],
          eval_set=[(X[val_idx], y[val_idx])], verbose=False)
    if len(np.unique(y[val_idx])) > 1:
        aucs.append(roc_auc_score(y[val_idx], m.predict_proba(X[val_idx])[:, 1]))
    model = m

print(f"\n[XGBoost] 평균 AUC: {np.mean(aucs):.4f} (±{np.std(aucs):.4f})")
print(classification_report(y, model.predict(X), target_names=['하락', '상승']))

df_xgb['up_prob'] = model.predict_proba(X)[:, 1]
stock_prob = (
    df_xgb.groupby(['theme', 'stock'])['up_prob'].mean().reset_index()
    .rename(columns={'up_prob': 'avg_up_prob'})
    .sort_values('avg_up_prob', ascending=False)
)
importance = pd.DataFrame({
    'feature': avail, 'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("\n[피처 중요도]")
print(importance.to_string(index=False))

# ──────────────────────────────────────────────────────────────
# STEP 9. 최종 랭킹 + 시각화 7종 (데이터 충분한 테마 위주 필터링)
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 9. 최종 랭킹 + 시각화")
print("=" * 60)

# 분석 가치가 떨어지는 소표본 테마 필터링
valid_themes = sentiment_df['theme'].value_counts()
valid_themes = valid_themes[valid_themes >= 40].index.tolist()

# 명시적 제외 테마
if 'SI' in valid_themes: valid_themes.remove('SI')
if '은행' in valid_themes: valid_themes.remove('은행')

# 명시적으로 제외할 테마 (예: 두나무 - 데이터 기간 부족)
if '두나무' in valid_themes: valid_themes.remove('두나무')

print(f"분석 대상 테마 선정: {len(valid_themes)}개")
print(f"제외된 테마: {set(sentiment_df['theme'].unique()) - set(valid_themes)}")

# 모든 데이터셋에 필터 적용 (일관성 유지)
merged = merged[merged['theme'].isin(valid_themes)]
stock_prob = stock_prob[stock_prob['theme'].isin(valid_themes)]
sentiment_df = sentiment_df[sentiment_df['theme'].isin(valid_themes)]

# 2026년 6월 데이터 제외 (불완전한 달 제거)
merged = merged[merged['date'] < '2026-06-01']
sentiment_df = sentiment_df[sentiment_df['date'] < '2026-06-01']
valid_months = [m for m in monthly_tops_final.keys() if m != '2026-06']

# monthly_tops_final 필터링 + 빈 자리 채우기 (제외 테마 자리를 텔레그램 6~10위로 보완)
monthly_tops_filtered = {}
for m, tops in monthly_tops_final.items():
    if m == '2026-06': continue
    filtered_tops = [t for t in tops if t in valid_themes]
    if len(filtered_tops) < TOP_N and m in monthly_tops_str:
        for t in monthly_tops_str[m]:
            if t in valid_themes and t not in filtered_tops:
                filtered_tops.append(t)
            if len(filtered_tops) >= TOP_N:
                break
    if filtered_tops:
        monthly_tops_filtered[m] = filtered_tops

corr_list = []
for stock, grp in merged.groupby('stock'):
    if len(grp) < 5:
        continue
    corr = grp['sentiment_score'].corr(grp['return_1d'])
    corr_list.append({'stock': stock, 'sentiment_corr': round(corr, 4)})
corr_df = pd.DataFrame(corr_list)

final = pd.merge(stock_prob, corr_df, on='stock', how='left')
s     = final['sentiment_corr'].fillna(0)
rng   = s.max() - s.min()
final['corr_norm']   = (s - s.min()) / (rng if rng > 0 else 1)
final['total_score'] = final['avg_up_prob'] * 0.6 + final['corr_norm'] * 0.4
final = final.sort_values('total_score', ascending=False).reset_index(drop=True)
final['rank'] = final.index + 1

all_themes_sorted = sorted(final['theme'].unique())

print("\n" + "=" * 65)
print("최종 테마별 핵심 관련주 랭킹 (v2 · 12개 피처)")
print("=" * 65)
for theme in all_themes_sorted:
    sub = final[final['theme'] == theme].head(5)
    print(f"\n▶ [{theme}]")
    print(f"  {'종목':<14} {'상승확률':>8} {'감성상관':>9} {'종합점수':>9}")
    print(f"  {'-'*44}")
    for _, r in sub.iterrows():
        print(f"  {r['stock']:<14} {r['avg_up_prob']:>8.1%} "
              f"{r.get('sentiment_corr', float('nan')):>+9.3f} {r['total_score']:>9.3f}")
print("=" * 65)

try:
    final.to_csv(os.path.join(RESULT_PATH, 'final_theme_stocks.csv'),
                 index=False, encoding='utf-8-sig')
    print("final_theme_stocks.csv 저장")
except Exception as e:
    print(f"final_theme_stocks.csv 저장 실패: {e}")

# ── 차트 1: 월별 테마 변화표 ──────────────────────────────────
monthly_final_df = pd.DataFrame([
    {'month': m, 'rank': i + 1, 'theme': t}
    for m, tops in monthly_tops_filtered.items() for i, t in enumerate(tops)
])
try:
    monthly_final_df.to_csv(os.path.join(RESULT_PATH, 'monthly_top_themes.csv'),
                            index=False, encoding='utf-8-sig')
    print("monthly_top_themes.csv 저장")
except Exception as e:
    print(f"monthly_top_themes.csv 저장 실패: {e}")

rank_pivot = monthly_final_df.pivot(index='month', columns='rank', values='theme')
rank_pivot.columns = [f'{c}위' for c in rank_pivot.columns]
fig, ax = plt.subplots(figsize=(10, len(rank_pivot) * 0.6 + 2))
ax.set_facecolor('#0f1117'); fig.patch.set_facecolor('#0f1117')
CELL_COLORS = ['#1d3557', '#457B9D', '#A8DADC', '#F1FAEE', '#E63946']
for ci, col in enumerate(rank_pivot.columns):
    for ri, val in enumerate(rank_pivot[col]):
        bg = CELL_COLORS[ci] if ci < len(CELL_COLORS) else '#888'
        ax.add_patch(plt.Rectangle((ci, ri), 1, 1, fill=True, color=bg,
                     alpha=0.9, linewidth=0.5, edgecolor='white'))
        ax.text(ci + 0.5, ri + 0.5, str(val) if pd.notna(val) else '-',
                ha='center', va='center', fontsize=10,
                color='white' if ci <= 2 else '#111')
ax.set_xlim(0, len(rank_pivot.columns)); ax.set_ylim(0, len(rank_pivot))
ax.set_xticks([i + 0.5 for i in range(len(rank_pivot.columns))])
ax.set_xticklabels(rank_pivot.columns, fontsize=11, color='white')
ax.set_yticks([i + 0.5 for i in range(len(rank_pivot))])
ax.set_yticklabels(rank_pivot.index, fontsize=10, color='white')
ax.set_title('월별 뉴스 감성 기반 TOP5 테마 변화 (v2)', fontsize=13,
             fontweight='bold', color='white', pad=12)
plt.tight_layout()
plt.savefig(os.path.join(RESULT_PATH, 'chart1_monthly_theme_change.png'),
            dpi=150, bbox_inches='tight', facecolor='#0f1117')
plt.close(); print("chart1 저장")

# ── 차트 2: 테마별 TOP5 상승확률 ──────────────────────────────
n = len(all_themes_sorted)
fig, axes = plt.subplots(1, n, figsize=(5 * n, 5))
if n == 1: axes = [axes]
for ax, theme in zip(axes, all_themes_sorted):
    sub    = final[final['theme'] == theme].head(5)
    colors = ['#E63946' if p > 0.55 else '#457B9D' for p in sub['avg_up_prob']]
    ax.barh(sub['stock'][::-1], sub['avg_up_prob'][::-1],
            color=colors[::-1], edgecolor='white')
    ax.axvline(0.5, color='gray', linestyle='--', linewidth=0.8)
    ax.set_title(f'{theme}\n핵심 관련주', fontsize=11, fontweight='bold')
    ax.set_xlabel('주가 상승 확률'); ax.set_xlim(0, 1)
    for i, (_, row) in enumerate(sub[::-1].iterrows()):
        ax.text(row['avg_up_prob'] + 0.01, i,
                f"{row['avg_up_prob']:.1%}", va='center', fontsize=9)
plt.suptitle('뉴스 감성 기반 테마별 핵심 관련주 (v2 · 12피처)', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(RESULT_PATH, 'chart2_top_stocks.png'), dpi=150, bbox_inches='tight')
plt.close(); print("chart2 저장")

# ── 차트 3: 감성점수 vs 익일 수익률 산점도 ────────────────────
fig, axes = plt.subplots(1, n, figsize=(5 * n, 4))
if n == 1: axes = [axes]
for ax, theme in zip(axes, all_themes_sorted):
    sub = merged[merged['theme'] == theme].dropna(subset=['sentiment_score', 'return_1d'])
    if sub.empty: continue
    ax.scatter(sub['sentiment_score'], sub['return_1d'], alpha=0.4, s=20, color='#2A9D8F')
    try:
        z  = np.polyfit(sub['sentiment_score'], sub['return_1d'], 1)
        xs = np.linspace(sub['sentiment_score'].min(), sub['sentiment_score'].max(), 100)
        ax.plot(xs, np.poly1d(z)(xs), 'r--', linewidth=1.5)
    except Exception:
        pass
    corr = sub['sentiment_score'].corr(sub['return_1d'])
    ax.set_title(f'{theme}\n상관계수: {corr:+.3f}', fontsize=11)
    ax.set_xlabel('감성 점수'); ax.set_ylabel('익일 수익률')
    ax.axhline(0, color='gray', linewidth=0.5)
    ax.axvline(0, color='gray', linewidth=0.5)
plt.suptitle('테마 감성점수 vs 익일 주가 수익률 (v2)', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(RESULT_PATH, 'chart3_sentiment_corr.png'), dpi=150, bbox_inches='tight')
plt.close(); print("chart3 저장")

# ── 차트 4: 월별 감성점수 히트맵 ──────────────────────────────
pivot = sentiment_df.groupby(['month', 'theme'])['score'].mean().unstack('theme')
if not pivot.empty:
    fig, ax = plt.subplots(figsize=(max(8, len(pivot.columns) * 1.5),
                                    max(5, len(pivot) * 0.6)))
    sns.heatmap(pivot, cmap='RdYlGn', center=0, annot=True, fmt='.2f',
                linewidths=0.5, ax=ax, cbar_kws={'label': '평균 감성점수 (Gemini)'})
    ax.set_title('월별 × 테마별 뉴스 감성점수 히트맵 (v2)', fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_PATH, 'chart4_sentiment_heatmap.png'), dpi=150, bbox_inches='tight')
    plt.close(); print("chart4 저장")

# ── 차트 5: 텔레그램 언급량 추이 ──────────────────────────────
if not tg_feat.empty:
    tg_feat['month_str'] = pd.to_datetime(tg_feat['date']).dt.to_period('M').astype(str)
    monthly_tg = tg_feat.groupby(['month_str', 'theme'])['tg_mention_count'].sum().reset_index()
    fig, ax = plt.subplots(figsize=(12, 5))
    for theme in all_themes_sorted:
        sub = monthly_tg[monthly_tg['theme'] == theme]
        ax.plot(sub['month_str'], sub['tg_mention_count'],
                marker='o', label=theme, linewidth=2)
    ax.set_title('텔레그램 월별 테마 언급량 추이 (시장반응 피처)', fontsize=13, fontweight='bold')
    ax.set_xlabel('월'); ax.set_ylabel('언급 횟수')
    ax.legend(fontsize=8); ax.grid(alpha=0.3); plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_PATH, 'chart5_tg_mention_trend.png'), dpi=150, bbox_inches='tight')
    plt.close(); print("chart5 저장")

# ── 차트 6: XGBoost 피처 중요도 ────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
colors = ['#E63946' if i == 0 else '#457B9D' for i in range(len(importance))]
ax.barh(importance['feature'][::-1], importance['importance'][::-1],
        color=colors[::-1], edgecolor='white')
ax.set_title(f'XGBoost 피처 중요도 ({len(avail)}개 피처 · v2)', fontsize=12, fontweight='bold')
ax.set_xlabel('Importance')
plt.tight_layout()
plt.savefig(os.path.join(RESULT_PATH, 'chart6_feature_importance.png'), dpi=150, bbox_inches='tight')
plt.close(); print("chart6 저장")

# ── 차트 7: tg_news_ratio 히트맵 (과열 감지) ─────────────────
if 'tg_news_ratio' in merged.columns:
    ratio_pivot = (
        merged.assign(month_str=merged['date'].dt.to_period('M').astype(str))
        .groupby(['month_str', 'theme'])['tg_news_ratio']
        .mean().unstack('theme')
    )
    if not ratio_pivot.empty:
        fig, ax = plt.subplots(figsize=(max(8, len(ratio_pivot.columns) * 1.5),
                                        max(5, len(ratio_pivot) * 0.6)))
        sns.heatmap(ratio_pivot, cmap='YlOrRd', annot=True, fmt='.2f',
                    linewidths=0.5, ax=ax,
                    cbar_kws={'label': '텔레그램/뉴스 비율 (높을수록 과열)'})
        ax.set_title('월별 텔레그램/뉴스 비율 히트맵 (과열 감지)', fontsize=13, fontweight='bold')
        plt.tight_layout()
        plt.savefig(os.path.join(RESULT_PATH, 'chart7_tg_news_ratio.png'), dpi=150, bbox_inches='tight')
        plt.close(); print("chart7 저장")

print("\n" + "=" * 55)
print(f"v2 파이프라인 완료! AUC: {np.mean(aucs):.4f}")
print(f"저장 경로: {RESULT_PATH}")
print("=" * 55)

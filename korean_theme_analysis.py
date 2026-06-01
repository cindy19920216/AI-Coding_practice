# -*- coding: utf-8 -*-
"""
==============================================================
 한국 주식 테마 감성 분석 → 핵심 관련주 발굴 파이프라인 Final
 핵심: 월별 텔레그램 TOP5 → Google 뉴스 수집 → 감성분석 → XGBoost 관련주 랭킹
==============================================================

[전체 흐름]
STEP 1. 텔레그램 CSV 로드 → 월별 TOP5 테마 추출
STEP 2. 월별 TOP5 기반 Google 뉴스 자동 수집 (API키 불필요)
STEP 3. 한국어 금융 키워드 감성 분석
STEP 4. yfinance 주가 데이터 수집
STEP 5. 감성점수 + 주가 수익률 병합
STEP 6. XGBoost로 주가 상승 확률 예측
STEP 7. 최종 관련주 리스트 + 시각화

[설치]
pip install yfinance xgboost scikit-learn pygooglenews feedparser
pip install pandas requests beautifulsoup4 matplotlib seaborn
"""

import os, re, time, calendar, requests, json
from datetime import datetime
from collections import Counter

import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import seaborn as sns

# ── 한글 폰트 (Windows) ──
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False


# ==============================================================
# STEP 0. 설정값
# ==============================================================

BASE_DIR     = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
TG_DATA_PATH = os.path.join(BASE_DIR, 'telegram_data')
RESULT_PATH  = os.path.join(BASE_DIR, 'results')

TOP_N      = 5
BATCH_SIZE = 50
STOPWORDS  = {'증권', '투자', '시장', '금융', '경제', '주식'}

# Gemini API 설정 (키워드 방식 대신 LLM 감성 분석 사용 시)
# 발급: https://aistudio.google.com/apikey
GEMINI_API_KEY   = os.environ.get('GEMINI_API_KEY', '')   # 환경변수 우선
GEMINI_MODEL     = 'gemini-2.0-flash'
GEMINI_BATCH_SIZE = 20   # 한 번 API 호출당 처리 기사 수 (rate limit 고려)

# 특정 테마가 노이즈 복합어로 언급될 때 제외
# 동작 방식: 메시지에서 아래 복합어를 먼저 지운 뒤 테마명이 남으면 카운트
THEME_NOISE_WORDS = {
    '은행': [
        '중앙은행', '한국은행', '일본은행', '연방준비은행', '유럽중앙은행',
        '인민은행', '영란은행', '산업은행', '수출입은행', '저축은행',
        '정책은행', '은행나무', '은행권', '은행법', '은행업',
        'BOK', 'BOJ', 'ECB', 'Fed', 'PBOC', 'BoE',
    ],
    # "통신"은 위성통신·무선통신·광통신 등 다른 테마 메시지에서 복합어로 자주 등장
    # 복합어를 먼저 제거해 순수 '통신주/통신섹터' 언급만 카운트
    '통신': [
        '위성통신', '통신위성', '무선통신', '광통신', '데이터통신',
        '통신모듈', '통신칩', '통신장비', '통신기술', '통신망',
        '통신프로토콜', '통신방식', '통신선', '단거리통신',
        '블루투스통신', '근거리통신', '이동통신기기',
        '뉴스통신', '국제통신', '우주통신',
    ],
}


POS_KEYWORDS = [
    '상승', '급등', '호재', '성장', '기대', '개선', '확대', '수주', '계약',
    '흑자', '돌파', '상향', '신고가', '호조', '기록', '달성', '수혜', '강세',
    '증가', '성공', '획득', '인기', '호실적', '어닝서프라이즈', '최고', '반등',
]
NEG_KEYWORDS = [
    '하락', '급락', '악재', '위기', '감소', '부진', '적자', '손실', '우려',
    '리스크', '약세', '저조', '실망', '경고', '하향', '신저가', '부채',
    '소송', '제재', '규제', '파산', '어닝쇼크', '실적부진', '최저',
]


# ==============================================================
# STEP 1. 텔레그램 CSV 로드 → 월별 TOP5 테마 추출
# ==============================================================

def load_telegram(path: str) -> pd.DataFrame:
    files = [
        os.path.join(path, f) for f in os.listdir(path)
        if f.startswith('telegram_data_') and f.endswith('.csv')
    ]
    if not files:
        raise FileNotFoundError(f"{path} 에 텔레그램 CSV 없음")
    df = pd.concat([pd.read_csv(f) for f in sorted(files)], ignore_index=True)
    df['Date']    = pd.to_datetime(df['Date'])
    df['month']   = df['Date'].dt.to_period('M')
    df['Message'] = df['Message'].astype(str)
    print(f"텔레그램 로드: {len(df):,}건 / {df['month'].nunique()}개월")
    return df


def get_naver_theme_map() -> tuple:
    """
    네이버 증권 테마 페이지 스크래핑
    반환:
        theme_map      : {테마명: [종목명, ...]}          ← 텔레그램 매칭용
        theme_code_map : {테마명: {종목명: KRX코드, ...}} ← 주가 수집용
    """
    print("네이버 테마 + 종목 수집 중...")
    headers        = {'User-Agent': 'Mozilla/5.0'}
    theme_map      = {}   # {theme: [stock_name]}
    theme_code_map = {}   # {theme: {stock_name: '005930'}}

    for page in range(1, 8):
        url = f"https://finance.naver.com/sise/theme.naver?&page={page}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'euc-kr'                          # Naver는 EUC-KR
            soup  = BeautifulSoup(res.text, 'html.parser')
            links = soup.select('td.col_type1 a')
            if not links:
                break
            for link in links:
                theme_name = re.sub(r'\(.*?\)', '', link.text).strip()
                if theme_name in STOPWORDS:
                    continue
                detail_url = "https://finance.naver.com" + link['href']
                try:
                    d = requests.get(detail_url, headers=headers, timeout=10)
                    d.encoding = 'euc-kr'                    # 상세 페이지도 EUC-KR

                    ds   = BeautifulSoup(d.text, 'html.parser')
                    # /item/main.naver?code=XXXXXX 패턴 링크만 수집
                    tags = ds.find_all(
                        'a', href=re.compile(r'/item/main\.naver\?code=\d{6}')
                    )

                    names, codes, seen = [], {}, set()
                    for s in tags:
                        sname = s.text.strip()
                        m     = re.search(r'code=(\d{6})', s.get('href', ''))
                        if sname and m and m.group(1) not in seen:
                            code = m.group(1)
                            names.append(sname)
                            codes[sname] = code
                            seen.add(code)

                    theme_map[theme_name]      = names
                    theme_code_map[theme_name] = codes
                    time.sleep(0.15)
                except Exception:
                    continue
        except Exception as e:
            print(f"  page {page} 실패: {e}"); break

    total_stocks = sum(len(v) for v in theme_code_map.values())
    print(f"테마 수집 완료: {len(theme_map)}개 테마 / 코드 확보 종목: {total_stocks}개")
    return theme_map, theme_code_map


def get_monthly_top_themes(tg_df: pd.DataFrame,
                            theme_map: dict,
                            top_n: int = TOP_N) -> dict:
    months, monthly_tops = sorted(tg_df['month'].unique()), {}
    def theme_matched(theme: str, msg: str) -> bool:
        """노이즈 복합어를 제거한 뒤 테마명이 남아있으면 True"""
        noise_list = THEME_NOISE_WORDS.get(theme, [])
        clean = msg
        for noise in noise_list:
            clean = clean.replace(noise, '')
        return theme in clean

    print("\n월별 TOP 테마 추출 중... (직접 언급, 노이즈 복합어 제외)")
    for month in months:
        msgs, counts = tg_df[tg_df['month'] == month]['Message'].tolist(), Counter()
        for msg in msgs:
            seen = set()
            for theme in theme_map:
                if theme in STOPWORDS or theme in seen:
                    continue
                if theme_matched(theme, msg):
                    counts[theme] += 1
                    seen.add(theme)
        top = [name for name, _ in counts.most_common(top_n)]
        monthly_tops[month] = top
        print(f"  {month}: {' / '.join(top) if top else '없음'}")
    return monthly_tops


# ==============================================================
# STEP 2. Google 뉴스 자동 수집 (API키 불필요)
# ==============================================================

def fetch_google_news(query: str, yyyymm: str, max_articles: int = BATCH_SIZE) -> list:
    from pygooglenews import GoogleNews
    gn = GoogleNews(lang='ko', country='KR')

    y, m      = int(yyyymm[:4]), int(yyyymm[4:])
    last_day  = calendar.monthrange(y, m)[1]
    from_date = f"{y}-{m:02d}-01"
    to_date   = f"{y}-{m:02d}-{last_day}"

    articles = []
    try:
        result = gn.search(query, from_=from_date, to_=to_date)
        for item in result.get('entries', [])[:max_articles]:
            pub_raw = item.get('published', '')
            try:
                pub = datetime.strptime(pub_raw, '%a, %d %b %Y %H:%M:%S %Z').strftime('%Y%m%d')
            except Exception:
                try:
                    pub = datetime.strptime(pub_raw, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y%m%d')
                except Exception:
                    pub = yyyymm + '01'
            title = re.sub(r'<[^>]+>', '', item.get('title', '')).strip()
            desc  = re.sub(r'<[^>]+>', '', item.get('summary', '')).strip()
            articles.append({'date': pub, 'title': title, 'desc': desc})
        time.sleep(0.5)
    except Exception as e:
        print(f"    Google News 오류: {e}")
    return articles


def collect_monthly_news(monthly_tops: dict) -> pd.DataFrame:
    all_rows = []
    for idx, (month, top_themes) in enumerate(sorted(monthly_tops.items())):
        month_str = str(month)
        yyyymm    = month_str.replace('-', '')
        print(f"\n[{idx+1}/{len(monthly_tops)}] {month_str}: {' / '.join(top_themes)}")
        for theme in top_themes:
            articles = fetch_google_news(f"{theme} 주식 뉴스", yyyymm)
            seen, unique = set(), []
            for a in articles:
                if a['title'] not in seen:
                    seen.add(a['title']); a['theme'] = theme; a['month'] = month_str
                    unique.append(a)
            print(f"  [{theme}] {len(unique)}건")
            all_rows.extend(unique)

    if not all_rows:
        print("  뉴스 수집 결과 없음")
        return pd.DataFrame(columns=['date', 'title', 'desc', 'theme', 'month', 'text'])

    df = pd.DataFrame(all_rows)
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d', errors='coerce')
    df['text'] = df['title'] + ' ' + df['desc']
    df.to_csv(os.path.join(RESULT_PATH, 'news_monthly.csv'), index=False, encoding='utf-8-sig')
    print(f"\n뉴스 수집 완료: 총 {len(df):,}건")
    return df


# ==============================================================
# STEP 3. 감성 분석 (키워드 방식 OR Gemini LLM 방식)
# ==============================================================

# ── 방식 A: 키워드 사전 ──────────────────────────────────────

def analyze_sentiment_keyword(text: str) -> dict:
    pos = sum(1 for k in POS_KEYWORDS if k in text)
    neg = sum(1 for k in NEG_KEYWORDS if k in text)
    if pos > neg:   return {'label': '긍정', 'score':  1}
    elif neg > pos: return {'label': '부정', 'score': -1}
    return {'label': '중립', 'score': 0}


# ── 방식 B: Gemini LLM (문맥 이해) ──────────────────────────

_GEMINI_SYSTEM = """당신은 한국 주식시장 전문 감성 분석가입니다.
뉴스 기사가 해당 주식·테마의 주가에 미칠 영향을 3단계로 분류하세요.

분류 기준:
- 긍정(1) : 실적 개선, 수주·계약, 신기술 성공, 투자 확대, 목표주가 상향 등 호재
- 부정(-1): 실적 악화, 손실·적자, 소송·제재, 구조조정, 목표주가 하향 등 악재
- 중립(0) : 단순 사실 전달, 방향성 불명확, 인사·일정 공지 등

핵심 규칙 (문맥 우선):
- "상승 기대감 꺾여" → 부정  |  "하락 우려 해소" → 긍정
- "선방했다" → 긍정  |  "기대에 못 미쳤다" → 부정
- 부정어 + 긍정단어 조합은 반드시 전체 문맥으로 판단"""


def _parse_gemini_json(text: str, batch_ids: list) -> list:
    """Gemini 응답 파싱, 실패 시 중립 fallback"""
    try:
        cleaned = text.strip()
        if '```' in cleaned:
            parts = cleaned.split('```')
            cleaned = parts[1].lstrip('json').strip() if len(parts) > 1 else cleaned
        return json.loads(cleaned)
    except Exception:
        return [{'id': i, 'label': '중립', 'score': 0} for i in batch_ids]


def _analyze_gemini_batch(model, batch_rows: list) -> dict:
    """
    batch_rows: [{'id': int, 'text': str}, ...]
    returns: {id: {'label': str, 'score': int}}
    """
    articles_json = json.dumps(
        [{'id': r['id'], 'text': r['text'][:300]} for r in batch_rows],
        ensure_ascii=False
    )
    prompt = (
        "다음 기사들을 분석하고 JSON 배열만 출력하세요. 다른 설명 없이 JSON만.\n\n"
        f"기사:\n{articles_json}\n\n"
        "출력 형식: [{\"id\":1,\"label\":\"긍정\",\"score\":1}, ...]"
    )
    try:
        resp = model.generate_content(prompt)
        results = _parse_gemini_json(resp.text, [r['id'] for r in batch_rows])
    except Exception as e:
        print(f"(Gemini 오류: {e})", end=" ")
        results = [{'id': r['id'], 'label': '중립', 'score': 0} for r in batch_rows]
    return {r['id']: r for r in results}


def analyze_sentiment_gemini(news_df: pd.DataFrame, api_key: str) -> pd.DataFrame:
    """Gemini API 배치 처리 감성 분석 (google-genai 신버전)"""
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        raise ImportError("pip install google-genai 실행 후 재시도하세요.")

    client = genai.Client(api_key=api_key)

    df = news_df.copy().reset_index(drop=True)
    total = len(df)
    id_to_result: dict = {}

    for start in range(0, total, GEMINI_BATCH_SIZE):
        end = min(start + GEMINI_BATCH_SIZE, total)
        batch_rows = [
            {'id': i, 'text': str(df.at[i, 'text'] if 'text' in df.columns else df.at[i, 'title'])[:300]}
            for i in range(start, end)
        ]
        prompt = (
            "다음 기사들을 분석하고 JSON 배열만 출력하세요. 다른 설명 없이 JSON만.\n\n"
            f"기사:\n{json.dumps(batch_rows, ensure_ascii=False)}\n\n"
            "출력 형식: [{\"id\":0,\"label\":\"긍정\",\"score\":1}, ...]"
        )
        print(f"  [{start+1}~{end}/{total}] Gemini 분석...", end=" ", flush=True)
        try:
            resp = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=_GEMINI_SYSTEM,
                    temperature=0.1,
                ),
            )
            results = _parse_gemini_json(resp.text, [r['id'] for r in batch_rows])
        except Exception as e:
            print(f"오류({e})", end=" ")
            results = [{'id': r['id'], 'label': '중립', 'score': 0} for r in batch_rows]
        id_to_result.update({r['id']: r for r in results})
        print("완료")
        time.sleep(2)  # 무료 15 RPM 대응

    rows = []
    for i, row in df.iterrows():
        res = id_to_result.get(i, {'label': '중립', 'score': 0})
        rows.append({
            'date': row['date'], 'month': row['month'],
            'theme': row['theme'], 'title': row.get('title', ''),
            'label': res.get('label', '중립'), 'score': int(res.get('score', 0)),
        })
    result_df = pd.DataFrame(rows)
    _print_sentiment_stats(result_df, method='Gemini')
    return result_df


def _print_sentiment_stats(df: pd.DataFrame, method: str = '키워드') -> None:
    pos = (df['label'] == '긍정').sum()
    neg = (df['label'] == '부정').sum()
    neu = (df['label'] == '중립').sum()
    total = len(df)
    print(f"\n[{method}] 감성 분석 완료: {total}건  "
          f"긍정:{pos}({pos/total*100:.0f}%) / "
          f"부정:{neg}({neg/total*100:.0f}%) / "
          f"중립:{neu}({neu/total*100:.0f}%)")


# ── 디스패처: API 키 유무에 따라 자동 선택 ──────────────────

def run_sentiment_analysis(news_df: pd.DataFrame,
                            gemini_api_key: str = GEMINI_API_KEY) -> pd.DataFrame:
    """
    감성 분석 실행.
    GEMINI_API_KEY 환경변수(또는 인자)가 있으면 Gemini LLM,
    없으면 키워드 사전 방식으로 자동 전환.
    """
    if news_df.empty:
        return pd.DataFrame(columns=['date', 'month', 'theme', 'title', 'label', 'score'])

    if gemini_api_key:
        print(f"[Gemini] 문맥 기반 감성 분석 (모델: {GEMINI_MODEL})")
        result_df = analyze_sentiment_gemini(news_df, gemini_api_key)
    else:
        print("[키워드] 사전 기반 감성 분석 (Gemini API 키 없음)")
        rows = []
        for _, row in news_df.iterrows():
            sent = analyze_sentiment_keyword(str(row.get('text', '')))
            rows.append({
                'date': row['date'], 'month': row['month'],
                'theme': row['theme'], 'title': row.get('title', ''),
                'label': sent['label'], 'score': sent['score'],
            })
        result_df = pd.DataFrame(rows)
        _print_sentiment_stats(result_df, method='키워드')

    result_df.to_csv(os.path.join(RESULT_PATH, 'sentiment_result.csv'),
                     index=False, encoding='utf-8-sig')
    return result_df


# ==============================================================
# STEP 4. yfinance 주가 데이터 수집
# ==============================================================
import yfinance as yf
import FinanceDataReader as fdr


KRX300_TOP_N = 300  # 시총 기준 상위 N개 = KRX300 근사치


def get_krx300_codes(top_n: int = KRX300_TOP_N) -> set:
    """
    FinanceDataReader로 KOSPI+KOSDAQ 시가총액 상위 300종목 코드 반환.
    (pykrx 1.2.4에서 get_index_portfolio_deposit_file API가 깨져 있어
     FinanceDataReader 기반 시총 상위 300종목으로 KRX300을 근사함)
    """
    print(f"KRX300 근사치 조회 중 (KOSPI+KOSDAQ 시총 상위 {top_n}종목)...")
    try:
        frames = []
        for market in ['KOSPI', 'KOSDAQ']:
            df = fdr.StockListing(market)
            if 'Code' in df.columns and 'Marcap' in df.columns:
                frames.append(df[['Code', 'Marcap']].dropna())
        if not frames:
            raise ValueError("StockListing 결과 없음")
        combined = pd.concat(frames, ignore_index=True)
        combined['Marcap'] = pd.to_numeric(combined['Marcap'], errors='coerce')
        top = combined.nlargest(top_n, 'Marcap')
        codes = set(str(c).zfill(6) for c in top['Code'])
        print(f"KRX300 근사 {len(codes)}종목 확인 (최소 시총: {top['Marcap'].min()/1e8:.0f}억원)")
        return codes
    except Exception as e:
        print(f"KRX300 조회 실패: {e} → 시가총액 1조원 기준으로 대체합니다.")
        codes = set()
        try:
            for market in ['KOSPI', 'KOSDAQ']:
                df = fdr.StockListing(market)
                if 'Code' in df.columns and 'Marcap' in df.columns:
                    df['Marcap'] = pd.to_numeric(df['Marcap'], errors='coerce')
                    large = df[df['Marcap'] >= 1_000_000_000_000]
                    codes.update(str(c).zfill(6) for c in large['Code'])
        except Exception as ex:
            print(f"  fallback도 실패: {ex}")
        print(f"시가총액 1조원 이상 {len(codes)}개 확인")
        return codes


def _download_with_fallback(code: str, start: str, end: str):
    """KRX 6자리 코드로 주가 다운로드. KOSPI(.KS) 먼저 시도, 실패 시 KOSDAQ(.KQ)"""
    for suffix in ['.KS', '.KQ']:
        ticker = code + suffix
        try:
            raw = yf.download(ticker, start=start, end=end,
                              progress=False, auto_adjust=True)
            if not raw.empty:
                return raw, ticker
        except Exception:
            continue
    return pd.DataFrame(), None


def get_stock_data(monthly_tops: dict, theme_code_map: dict) -> pd.DataFrame:
    """
    네이버 테마 페이지에서 추출한 KRX 코드로 전 테마 주가 수집
    KRX300 구성 종목만 포함 (실패 시 시가총액 1조원 기준 fallback)
    theme_code_map: {테마명: {종목명: KRX코드}}
    """
    all_themes = set(t for tops in monthly_tops.values() for t in tops)
    start_str  = str(min(monthly_tops)).replace('-', '')
    start_dt   = f"{start_str[:4]}-{start_str[4:6]}-01"
    end_dt     = datetime.now().strftime('%Y-%m-%d')

    # KRX300 구성 종목 코드 조회
    krx300_codes = get_krx300_codes()

    all_data = []
    for theme in all_themes:
        code_dict = theme_code_map.get(theme, {})
        if not code_dict:
            print(f"\n[{theme}] 코드 정보 없음 - skip")
            continue

        # KRX300 필터 적용
        large_dict = {name: code for name, code in code_dict.items()
                      if code in krx300_codes}
        print(f"\n[{theme}] 전체 {len(code_dict)}개 → KRX300 {len(large_dict)}개")

        if not large_dict:
            print(f"  KRX300 종목 없음 - skip")
            continue

        for stock_name, code in large_dict.items():
            raw, ticker = _download_with_fallback(code, start_dt, end_dt)
            if raw.empty:
                continue
            df = raw[['Close']].copy()
            df.columns    = ['close']
            df.index.name = 'date'
            df.reset_index(inplace=True)
            df['date']      = pd.to_datetime(df['date']).dt.normalize()
            df['stock']     = stock_name
            df['ticker']    = ticker
            df['theme']     = theme
            df['return_1d'] = df['close'].pct_change()
            df['return_5d'] = df['close'].pct_change(5)
            df['up_next']   = (df['return_1d'].shift(-1) > 0).astype(int)
            all_data.append(df)
            print(f"  {stock_name}({ticker}): {len(df)}일")
            time.sleep(0.15)

    if not all_data:
        raise ValueError("KRX300 종목 주가 데이터가 없습니다. KRX300 조회를 확인하세요.")
    stock_df = pd.concat(all_data, ignore_index=True)
    print(f"\n주가 수집 완료: {stock_df['stock'].nunique()}개 KRX300 종목 / {stock_df['theme'].nunique()}개 테마")
    return stock_df


# ==============================================================
# STEP 5. 감성점수 + 주가 수익률 병합
# ==============================================================

def merge_sentiment_stock(sentiment_df: pd.DataFrame,
                           stock_df: pd.DataFrame) -> pd.DataFrame:
    """감성점수(t일) → 익일 주가 수익률(t+1일) 매핑"""
    # sentiment_df 파라미터로부터 날짜별 집계 (전역변수 의존 없음)
    sent = (
        sentiment_df
        .groupby([pd.Grouper(key='date', freq='D'), 'theme'])['score']
        .agg(sentiment_score='mean', news_count='count')
        .reset_index()
    )
    sent['date']      = pd.to_datetime(sent['date']).dt.normalize()
    sent['date_next'] = sent['date'] + pd.Timedelta(days=1)

    merged = pd.merge(
        stock_df,
        sent[['date_next', 'theme', 'sentiment_score', 'news_count']],
        left_on=['date', 'theme'],
        right_on=['date_next', 'theme'],
        how='inner'
    ).drop(columns=['date_next'])

    merged = merged.sort_values(['stock', 'date'])
    for w in [3, 5]:
        merged[f'sentiment_ma{w}'] = (
            merged.groupby('stock')['sentiment_score']
            .transform(lambda x: x.rolling(w, min_periods=1).mean())
        )
    merged = merged.dropna(subset=['return_1d', 'sentiment_score'])
    print(f"병합 완료: {len(merged):,}행 / {merged['stock'].nunique()}개 종목")
    return merged


# ==============================================================
# STEP 6. XGBoost로 주가 상승 확률 예측
# ==============================================================
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, roc_auc_score

FEATURES = ['sentiment_score', 'sentiment_ma3', 'sentiment_ma5',
            'news_count', 'return_1d', 'return_5d']
TARGET   = 'up_next'


def train_xgboost(merged_df: pd.DataFrame) -> tuple:
    df = merged_df.dropna(subset=FEATURES + [TARGET]).copy()
    if len(df) < 20:
        raise ValueError(f"학습 데이터 부족: {len(df)}행")

    X, y = df[FEATURES].values, df[TARGET].values
    aucs, model = [], None

    for tr_idx, val_idx in TimeSeriesSplit(n_splits=5).split(X):
        if len(val_idx) == 0:
            continue
        m = XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            eval_metric='logloss', random_state=42, verbosity=0
        )
        m.fit(X[tr_idx], y[tr_idx], eval_set=[(X[val_idx], y[val_idx])], verbose=False)
        if len(np.unique(y[val_idx])) > 1:
            aucs.append(roc_auc_score(y[val_idx], m.predict_proba(X[val_idx])[:, 1]))
        model = m

    if aucs:
        print(f"\n[XGBoost] 평균 AUC: {np.mean(aucs):.4f} (±{np.std(aucs):.4f})")
    print(classification_report(y, model.predict(X), target_names=['하락', '상승']))

    df['up_prob'] = model.predict_proba(X)[:, 1]
    stock_prob = (
        df.groupby(['theme', 'stock'])['up_prob'].mean().reset_index()
        .rename(columns={'up_prob': 'avg_up_prob'})
        .sort_values('avg_up_prob', ascending=False)
    )
    importance = pd.DataFrame({
        'feature': FEATURES, 'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\n[피처 중요도]")
    print(importance.to_string(index=False))
    return model, stock_prob, importance


# ==============================================================
# STEP 7. 최종 관련주 리스트 + 시각화
# ==============================================================

def get_final_ranking(stock_prob: pd.DataFrame,
                       merged_df: pd.DataFrame) -> pd.DataFrame:
    corr_list = []
    for stock, grp in merged_df.groupby('stock'):
        if len(grp) < 5:
            continue
        corr = grp['sentiment_score'].corr(grp['return_1d'])
        corr_list.append({'stock': stock, 'sentiment_corr': round(corr, 4)})
    corr_df = pd.DataFrame(corr_list)

    final = pd.merge(stock_prob, corr_df, on='stock', how='left')
    s = final['sentiment_corr'].fillna(0)
    rng = s.max() - s.min()
    final['corr_norm']   = (s - s.min()) / (rng if rng > 0 else 1)
    final['total_score'] = final['avg_up_prob'] * 0.6 + final['corr_norm'] * 0.4
    final = final.sort_values('total_score', ascending=False).reset_index(drop=True)
    final['rank'] = final.index + 1
    return final


# ==============================================================
# 메인 실행
# ==============================================================

if __name__ == '__main__':
    os.makedirs(RESULT_PATH, exist_ok=True)

    # STEP 1
    print("=" * 60)
    print("STEP 1. 텔레그램 로드 + 월별 TOP5 테마 추출")
    print("=" * 60)
    tg_df                    = load_telegram(TG_DATA_PATH)
    theme_map, theme_code_map = get_naver_theme_map()
    monthly_tops             = get_monthly_top_themes(tg_df, theme_map)

    monthly_top_df = pd.DataFrame([
        {'month': str(m), 'rank': i + 1, 'theme': t}
        for m, tops in monthly_tops.items() for i, t in enumerate(tops)
    ])
    monthly_top_df.to_csv(os.path.join(RESULT_PATH, 'monthly_top_themes.csv'),
                          index=False, encoding='utf-8-sig')
    print(f"월별 TOP{TOP_N} 저장 완료")

    # STEP 2
    print("\n" + "=" * 60)
    print("STEP 2. Google 뉴스 수집")
    print("=" * 60)
    news_df = collect_monthly_news(monthly_tops)

    # STEP 3
    print("\n" + "=" * 60)
    print("STEP 3. 감성 분석")
    print("=" * 60)
    sentiment_df = run_sentiment_analysis(news_df)

    # STEP 4
    print("\n" + "=" * 60)
    print("STEP 4. 주가 데이터 수집")
    print("=" * 60)
    stock_df = get_stock_data(monthly_tops, theme_code_map)

    # STEP 5
    print("\n" + "=" * 60)
    print("STEP 5. 감성점수 + 주가 병합")
    print("=" * 60)
    merged_df = merge_sentiment_stock(sentiment_df, stock_df)

    # STEP 6
    print("\n" + "=" * 60)
    print("STEP 6. XGBoost 학습")
    print("=" * 60)
    model, stock_prob, importance_df = train_xgboost(merged_df)

    # STEP 7
    print("\n" + "=" * 60)
    print("STEP 7. 최종 랭킹 + 시각화")
    print("=" * 60)
    final_df   = get_final_ranking(stock_prob, merged_df)
    all_themes = sorted(final_df['theme'].unique())

    print("\n" + "=" * 65)
    print("최종 테마별 핵심 관련주 랭킹")
    print("(감성 뉴스 + 실제 주가 반응이 가장 일치하는 종목 순)")
    print("=" * 65)
    for theme in all_themes:
        sub = final_df[final_df['theme'] == theme].head(5)
        print(f"\n▶ [{theme}]")
        print(f"  {'종목':<14} {'상승확률':>8} {'감성상관':>9} {'종합점수':>9}")
        print(f"  {'-'*44}")
        for _, r in sub.iterrows():
            print(f"  {r['stock']:<14} {r['avg_up_prob']:>8.1%} "
                  f"{r['sentiment_corr']:>+9.3f} {r['total_score']:>9.3f}")
    print("=" * 65)
    final_df.to_csv(os.path.join(RESULT_PATH, 'final_theme_stocks.csv'),
                    index=False, encoding='utf-8-sig')

    # ── 시각화 1: 월별 테마 변화표 ──
    rank_pivot = monthly_top_df.pivot(index='month', columns='rank', values='theme')
    rank_pivot.columns = [f'{c}위' for c in rank_pivot.columns]
    fig, ax = plt.subplots(figsize=(10, len(rank_pivot) * 0.6 + 2))
    ax.set_facecolor('#0f1117'); fig.patch.set_facecolor('#0f1117')
    CELL_COLORS = ['#1d3557', '#457B9D', '#A8DADC', '#F1FAEE', '#E63946']
    for ci, col in enumerate(rank_pivot.columns):
        for ri, val in enumerate(rank_pivot[col]):
            bg = CELL_COLORS[ci] if ci < len(CELL_COLORS) else '#888888'
            ax.add_patch(plt.Rectangle((ci, ri), 1, 1, fill=True, color=bg,
                         alpha=0.9, linewidth=0.5, edgecolor='white'))
            ax.text(ci + 0.5, ri + 0.5, str(val) if pd.notna(val) else '-',
                    ha='center', va='center', fontsize=10,
                    color='white' if ci <= 2 else '#111111')
    ax.set_xlim(0, len(rank_pivot.columns)); ax.set_ylim(0, len(rank_pivot))
    ax.set_xticks([i + 0.5 for i in range(len(rank_pivot.columns))])
    ax.set_xticklabels(rank_pivot.columns, fontsize=11, color='white')
    ax.set_yticks([i + 0.5 for i in range(len(rank_pivot))])
    ax.set_yticklabels(rank_pivot.index, fontsize=10, color='white')
    ax.set_title('월별 텔레그램 TOP5 테마 변화', fontsize=13,
                 fontweight='bold', color='white', pad=12)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_PATH, 'chart1_monthly_theme_change.png'),
                dpi=150, bbox_inches='tight', facecolor='#0f1117')
    plt.show(); print("chart1_monthly_theme_change.png 저장")

    # ── 시각화 2: 테마별 TOP5 종목 상승 확률 바 차트 ──
    n = len(all_themes)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 5))
    if n == 1: axes = [axes]
    for ax, theme in zip(axes, all_themes):
        sub    = final_df[final_df['theme'] == theme].head(5)
        colors = ['#E63946' if p > 0.55 else '#457B9D' for p in sub['avg_up_prob']]
        ax.barh(sub['stock'][::-1], sub['avg_up_prob'][::-1],
                color=colors[::-1], edgecolor='white')
        ax.axvline(0.5, color='gray', linestyle='--', linewidth=0.8)
        ax.set_title(f'{theme}\n핵심 관련주', fontsize=12, fontweight='bold')
        ax.set_xlabel('주가 상승 확률'); ax.set_xlim(0, 1)
        for i, (_, row) in enumerate(sub[::-1].iterrows()):
            ax.text(row['avg_up_prob'] + 0.01, i,
                    f"{row['avg_up_prob']:.1%}", va='center', fontsize=9)
    plt.suptitle('텔레그램 주도 테마별 핵심 관련주', fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_PATH, 'chart2_top_stocks.png'),
                dpi=150, bbox_inches='tight')
    plt.show(); print("chart2_top_stocks.png 저장")

    # ── 시각화 3: 감성점수 vs 익일 수익률 산점도 ──
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 4))
    if n == 1: axes = [axes]
    for ax, theme in zip(axes, all_themes):
        sub = merged_df[merged_df['theme'] == theme].dropna(
            subset=['sentiment_score', 'return_1d'])
        if sub.empty: continue
        ax.scatter(sub['sentiment_score'], sub['return_1d'], alpha=0.4, s=20, color='#2A9D8F')
        try:
            z  = np.polyfit(sub['sentiment_score'], sub['return_1d'], 1)
            xs = np.linspace(sub['sentiment_score'].min(), sub['sentiment_score'].max(), 100)
            ax.plot(xs, np.poly1d(z)(xs), 'r--', linewidth=1.5)
        except (np.linalg.LinAlgError, ValueError):
            pass
        corr = sub['sentiment_score'].corr(sub['return_1d'])
        ax.set_title(f'{theme}\n상관계수: {corr:+.3f}', fontsize=11)
        ax.set_xlabel('감성 점수'); ax.set_ylabel('익일 수익률')
        ax.axhline(0, color='gray', linewidth=0.5); ax.axvline(0, color='gray', linewidth=0.5)
    plt.suptitle('테마 감성점수 vs 익일 주가 수익률', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_PATH, 'chart3_sentiment_corr.png'),
                dpi=150, bbox_inches='tight')
    plt.show(); print("chart3_sentiment_corr.png 저장")

    # ── 시각화 4: 월별 감성점수 히트맵 ──
    pivot = sentiment_df.groupby(['month', 'theme'])['score'].mean().unstack('theme')
    if not pivot.empty:
        fig, ax = plt.subplots(figsize=(max(8, len(pivot.columns) * 1.5),
                                        max(5, len(pivot) * 0.6)))
        sns.heatmap(pivot, cmap='RdYlGn', center=0, annot=True, fmt='.2f',
                    linewidths=0.5, ax=ax, cbar_kws={'label': '평균 감성점수'})
        ax.set_title('월별 × 테마별 감성점수 히트맵', fontsize=13, fontweight='bold')
        plt.tight_layout()
        plt.savefig(os.path.join(RESULT_PATH, 'chart4_sentiment_heatmap.png'),
                    dpi=150, bbox_inches='tight')
        plt.show(); print("chart4_sentiment_heatmap.png 저장")

    # ── 시각화 5: 텔레그램 월별 언급량 추이 ──
    tg_df['month_str'] = tg_df['Date'].dt.to_period('M').astype(str)
    monthly_counts = []
    for theme in all_themes:
        stocks   = theme_map.get(theme, [])
        keywords = [theme] + [s for s in stocks if len(s) > 1]
        pattern  = '|'.join(map(re.escape, keywords))
        mask     = tg_df['Message'].str.contains(pattern, na=False)
        counts   = tg_df[mask].groupby('month_str').size().reset_index(name='count')
        counts['theme'] = theme
        monthly_counts.append(counts)
    monthly_df = pd.concat(monthly_counts, ignore_index=True)
    fig, ax = plt.subplots(figsize=(12, 5))
    for theme in all_themes:
        sub = monthly_df[monthly_df['theme'] == theme]
        ax.plot(sub['month_str'], sub['count'], marker='o', label=theme, linewidth=2)
    ax.set_title('텔레그램 채널 월별 테마 언급량 추이', fontsize=13, fontweight='bold')
    ax.set_xlabel('월'); ax.set_ylabel('언급 횟수')
    ax.legend(); ax.grid(alpha=0.3); plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_PATH, 'chart5_monthly_trend.png'),
                dpi=150, bbox_inches='tight')
    plt.show(); print("chart5_monthly_trend.png 저장")

    # ── 시각화 6: XGBoost 피처 중요도 ──
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = ['#E63946' if i == 0 else '#457B9D' for i in range(len(importance_df))]
    ax.barh(importance_df['feature'][::-1], importance_df['importance'][::-1],
            color=colors[::-1], edgecolor='white')
    ax.set_title('XGBoost 피처 중요도', fontsize=12, fontweight='bold')
    ax.set_xlabel('Importance')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_PATH, 'chart6_feature_importance.png'),
                dpi=150, bbox_inches='tight')
    plt.show(); print("chart6_feature_importance.png 저장")

    print("\n" + "=" * 55)
    print("전체 파이프라인 완료!")
    print("=" * 55)
    print(f"저장 경로: {RESULT_PATH}")

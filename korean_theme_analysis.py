# -*- coding: utf-8 -*-
"""
==============================================================
 한국 주식 테마 감성 분석 → 핵심 관련주 발굴 파이프라인 v2
 뉴스 감성점수 기반 테마 선정 + 텔레그램 시장반응 피처 + 확장 XGBoost
==============================================================

[전체 흐름]
STEP 1. 텔레그램 후보 테마 추출 (TOP10/월) → 뉴스 수집 대상 결정
STEP 2. Google + 네이버 뉴스 병행 수집 (BATCH_SIZE=200)
STEP 3. Gemini LLM 감성 분석
STEP 4. 뉴스 감성점수 기반 월별 TOP5 테마 최종 선정
STEP 5. 텔레그램 언급량 피처 생성 (XGBoost 피처용)
STEP 6. yfinance 주가 + KOSPI 수집 (거래량·52주·상대강도)
         - KRX300 기준, 3개 미만 시 KRX500까지 자동 확장
         - TICKER_MAP으로 수동 종목 보완
STEP 7. 감성 + 텔레그램 + 주가 전체 병합
STEP 8. XGBoost 예측 (12개 피처)
STEP 9. 최종 관련주 랭킹 + 시각화

[설치]
pip install yfinance xgboost scikit-learn pygooglenews feedparser
pip install pandas requests beautifulsoup4 matplotlib seaborn
pip install FinanceDataReader google-genai
"""

import os, re, time, calendar, requests, json
from datetime import datetime
from collections import Counter

import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False


# ==============================================================
# STEP 0. 설정값
# ==============================================================

BASE_DIR     = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
TG_DATA_PATH = os.path.join(BASE_DIR, 'telegram_data')
RESULT_PATH  = os.path.join(BASE_DIR, 'results')

TOP_N           = 5    # 최종 선정 테마 수
CANDIDATE_TOP_N = 10   # 텔레그램 후보 테마 수 (감성 필터 전)
BATCH_SIZE      = 200  # 테마당 뉴스 수집 목표량 (Google)
STOPWORDS       = {'증권', '투자', '시장', '금융', '경제', '주식'}

GEMINI_API_KEY    = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL      = 'gemini-2.0-flash-lite'
GEMINI_BATCH_SIZE = 20

KRX300_TOP_N         = 300
KRX500_TOP_N         = 500
MIN_STOCKS_PER_THEME = 3   # 미만이면 KRX500으로 자동 확장

# 수동 종목 코드 보완 — 네이버 테마 페이지 미등재 또는 외국 기업명 테마
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
}

# 텔레그램 노이즈 복합어 필터 (후보 추출 시 사용)
THEME_NOISE_WORDS = {
    '은행': [
        '중앙은행', '한국은행', '일본은행', '연방준비은행', '유럽중앙은행',
        '인민은행', '영란은행', '산업은행', '수출입은행', '저축은행',
        '정책은행', '은행나무', '은행권', '은행법', '은행업',
    ],
    '통신': [
        '위성통신', '통신위성', '무선통신', '광통신', '데이터통신',
        '통신모듈', '통신칩', '통신장비', '통신기술', '통신망',
        '뉴스통신', '국제통신', '우주통신',
    ],
}

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


# ==============================================================
# 공통 유틸: 네이버 테마 맵 수집
# ==============================================================

def get_naver_theme_map() -> tuple:
    """
    네이버 증권 테마 페이지 스크래핑 후 TICKER_MAP으로 보완.
    반환: (theme_map, theme_code_map)
      theme_map      : {테마명: [종목명, ...]}
      theme_code_map : {테마명: {종목명: KRX코드}}
    """
    print("네이버 테마 + 종목 수집 중...")
    headers        = {'User-Agent': 'Mozilla/5.0'}
    theme_map      = {}
    theme_code_map = {}

    for page in range(1, 8):
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
                if theme_name in STOPWORDS:
                    continue
                detail_url = "https://finance.naver.com" + link['href']
                try:
                    d = requests.get(detail_url, headers=headers, timeout=10)
                    d.encoding = 'euc-kr'
                    ds   = BeautifulSoup(d.text, 'html.parser')
                    tags = ds.find_all('a', href=re.compile(r'/item/main\.naver\?code=\d{6}'))
                    names, codes, seen = [], {}, set()
                    for s in tags:
                        sname = s.text.strip()
                        m_obj = re.search(r'code=(\d{6})', s.get('href', ''))
                        if sname and m_obj and m_obj.group(1) not in seen:
                            code = m_obj.group(1)
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

    # TICKER_MAP으로 누락·보완
    for theme, ticker_dict in TICKER_MAP.items():
        if theme not in theme_map:
            theme_map[theme]      = list(ticker_dict.keys())
            theme_code_map[theme] = dict(ticker_dict)
        else:
            for stock, code in ticker_dict.items():
                if stock not in theme_map[theme]:
                    theme_map[theme].append(stock)
                theme_code_map.setdefault(theme, {})[stock] = code

    total = sum(len(v) for v in theme_code_map.values())
    print(f"테마 수집 완료: {len(theme_map)}개 테마 / 코드 확보: {total}개 종목")
    return theme_map, theme_code_map


# ==============================================================
# STEP 1. 텔레그램 → 후보 테마 추출 (TOP10/월)
#          ※ 최종 TOP5 선정은 STEP 4 (뉴스 감성점수 기반)
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


def _theme_matched(theme: str, msg: str) -> bool:
    clean = msg
    for noise in THEME_NOISE_WORDS.get(theme, []):
        clean = clean.replace(noise, '')
    return theme in clean


def get_candidate_themes(tg_df: pd.DataFrame,
                          theme_map: dict,
                          theme_code_map: dict,
                          candidate_n: int = CANDIDATE_TOP_N) -> dict:
    """
    텔레그램 언급 빈도로 후보 TOP10/월 추출.
    노이즈 필터: KRX 매칭 3개 미만 테마는 TICKER_MAP에 없으면 제거.
    """
    valid_themes = {
        t for t, codes in theme_code_map.items()
        if len(codes) >= MIN_STOCKS_PER_THEME
    }
    valid_themes.update(TICKER_MAP.keys())
    print(f"\n유효 테마: {len(valid_themes)}개 (KRX {MIN_STOCKS_PER_THEME}개↑ 또는 TICKER_MAP 등록)")
    print("STEP 1. 텔레그램 후보 테마 추출 (TOP10/월)...")

    monthly_candidates = {}
    for month in sorted(tg_df['month'].unique()):
        msgs   = tg_df[tg_df['month'] == month]['Message'].tolist()
        counts = Counter()
        for msg in msgs:
            seen = set()
            for theme in valid_themes:
                if theme in STOPWORDS or theme in seen:
                    continue
                if _theme_matched(theme, msg):
                    counts[theme] += 1
                    seen.add(theme)
        top = [name for name, _ in counts.most_common(candidate_n)]
        monthly_candidates[month] = top
        print(f"  {month}: {' / '.join(top[:5])} {'...' if len(top) > 5 else ''}")
    return monthly_candidates


# ==============================================================
# STEP 2. Google + 네이버 뉴스 병행 수집 (BATCH_SIZE=200)
# ==============================================================

def _parse_naver_date(date_str: str, yyyymm: str) -> str:
    if not date_str:
        return yyyymm + '01'
    m = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})', date_str)
    if m:
        return f"{m.group(1)}{int(m.group(2)):02d}{int(m.group(3)):02d}"
    return yyyymm + '01'


def fetch_naver_news(query: str, yyyymm: str, max_articles: int = 100) -> list:
    """네이버 뉴스 검색 스크래핑 (API 키 불필요)"""
    y, m = int(yyyymm[:4]), int(yyyymm[4:])
    last_day = calendar.monthrange(y, m)[1]
    ds, de = f"{y}.{m:02d}.01", f"{y}.{m:02d}.{last_day}"
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    }
    articles  = []
    encoded_q = requests.utils.quote(query)

    for start in range(1, min(max_articles + 1, 201), 10):
        url = (
            f"https://search.naver.com/search.naver?where=news"
            f"&query={encoded_q}&ds={ds}&de={de}&sort=1&start={start}"
        )
        try:
            res  = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            items = soup.select('div.news_area')
            if not items:
                break
            for item in items:
                title_tag = item.select_one('a.news_tit')
                desc_tag  = item.select_one('div.dsc_wrap')
                if not title_tag:
                    continue
                title    = title_tag.get('title', title_tag.text).strip()
                desc     = desc_tag.text.strip() if desc_tag else ''
                date_str = ''
                for info in item.select('span.info'):
                    t = info.text.strip()
                    if re.search(r'\d{4}\.\d{1,2}\.\d{1,2}', t):
                        date_str = t; break
                articles.append({
                    'date': _parse_naver_date(date_str, yyyymm),
                    'title': title, 'desc': desc,
                })
            if len(items) < 10:
                break
            time.sleep(0.3)
        except Exception as e:
            print(f"    네이버 뉴스 오류: {e}"); break

    return articles[:max_articles]


def fetch_google_news(query: str, yyyymm: str, max_articles: int = BATCH_SIZE) -> list:
    from pygooglenews import GoogleNews
    gn = GoogleNews(lang='ko', country='KR')
    y, m     = int(yyyymm[:4]), int(yyyymm[4:])
    last_day = calendar.monthrange(y, m)[1]
    articles = []
    try:
        result = gn.search(query,
                           from_=f"{y}-{m:02d}-01",
                           to_=f"{y}-{m:02d}-{last_day}")
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


def collect_monthly_news(monthly_candidates: dict) -> pd.DataFrame:
    """후보 테마 전체에 대해 Google + 네이버 병행 수집"""
    all_rows = []
    for idx, (month, candidates) in enumerate(sorted(monthly_candidates.items())):
        month_str = str(month)
        yyyymm    = month_str.replace('-', '')
        print(f"\n[{idx+1}/{len(monthly_candidates)}] {month_str}: {' / '.join(candidates[:5])} ...")
        for theme in candidates:
            query  = f"{theme} 주식 뉴스"
            google = fetch_google_news(query, yyyymm, max_articles=BATCH_SIZE)
            naver  = fetch_naver_news(query, yyyymm, max_articles=BATCH_SIZE // 2)

            # 소스 태깅 후 중복 제거
            for a in google:
                a['source'] = 'google'
            for a in naver:
                a['source'] = 'naver'

            seen, unique = set(), []
            for a in google + naver:
                if a['title'] not in seen:
                    seen.add(a['title'])
                    a['theme'] = theme
                    a['month'] = month_str
                    unique.append(a)
            print(f"  [{theme}] Google:{len(google)} + Naver:{len(naver)} → 중복제거:{len(unique)}건")
            all_rows.extend(unique)

    if not all_rows:
        return pd.DataFrame(columns=['date', 'title', 'desc', 'theme', 'month', 'text'])

    df = pd.DataFrame(all_rows)
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d', errors='coerce')
    df['text'] = df['title'] + ' ' + df['desc']
    df.to_csv(os.path.join(RESULT_PATH, 'news_monthly.csv'), index=False, encoding='utf-8-sig')
    print(f"\n뉴스 수집 완료: 총 {len(df):,}건")
    return df


# ==============================================================
# STEP 3. Gemini LLM 감성 분석
# ==============================================================

def _parse_gemini_json(text: str, batch_ids: list) -> list:
    try:
        cleaned = text.strip()
        if '```' in cleaned:
            parts   = cleaned.split('```')
            cleaned = parts[1].lstrip('json').strip() if len(parts) > 1 else cleaned
        return json.loads(cleaned)
    except Exception:
        return [{'id': i, 'label': '중립', 'score': 0} for i in batch_ids]


def analyze_sentiment_gemini(news_df: pd.DataFrame, api_key: str) -> pd.DataFrame:
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        raise ImportError("pip install google-genai 실행 후 재시도하세요.")

    client = genai.Client(api_key=api_key)
    df     = news_df.copy().reset_index(drop=True)
    total  = len(df)
    id_to_result: dict = {}

    for start in range(0, total, GEMINI_BATCH_SIZE):
        end        = min(start + GEMINI_BATCH_SIZE, total)
        batch_rows = [
            {'id': i,
             'text': str(df.at[i, 'text'] if 'text' in df.columns else df.at[i, 'title'])[:300]}
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
        time.sleep(2)

    rows = []
    for i, row in df.iterrows():
        res = id_to_result.get(i, {'label': '중립', 'score': 0})
        rows.append({
            'date': row['date'], 'month': row['month'],
            'theme': row['theme'], 'title': row.get('title', ''),
            'label': res.get('label', '중립'), 'score': int(res.get('score', 0)),
        })
    result_df = pd.DataFrame(rows)
    _print_sentiment_stats(result_df, 'Gemini')
    return result_df


def analyze_sentiment_keyword(text: str) -> dict:
    POS = ['상승','급등','호재','성장','기대','개선','확대','수주','계약',
           '흑자','돌파','상향','신고가','호조','달성','수혜','강세']
    NEG = ['하락','급락','악재','위기','감소','부진','적자','손실','우려',
           '리스크','약세','저조','실망','경고','하향','신저가','파산']
    pos = sum(1 for k in POS if k in text)
    neg = sum(1 for k in NEG if k in text)
    if pos > neg:   return {'label': '긍정', 'score':  1}
    elif neg > pos: return {'label': '부정', 'score': -1}
    return {'label': '중립', 'score': 0}


def _print_sentiment_stats(df: pd.DataFrame, method: str = '키워드') -> None:
    pos   = (df['label'] == '긍정').sum()
    neg   = (df['label'] == '부정').sum()
    neu   = (df['label'] == '중립').sum()
    total = len(df)
    print(f"\n[{method}] 감성 분석 완료: {total}건  "
          f"긍정:{pos}({pos/total*100:.0f}%) / "
          f"부정:{neg}({neg/total*100:.0f}%) / "
          f"중립:{neu}({neu/total*100:.0f}%)")


def run_sentiment_analysis(news_df: pd.DataFrame,
                            gemini_api_key: str = GEMINI_API_KEY) -> pd.DataFrame:
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
        _print_sentiment_stats(result_df, '키워드')

    result_df.to_csv(os.path.join(RESULT_PATH, 'sentiment_result.csv'),
                     index=False, encoding='utf-8-sig')
    return result_df


# ==============================================================
# STEP 4. 뉴스 감성점수 기반 월별 TOP5 테마 최종 선정
#          기존: 텔레그램 언급 빈도 → 변경: 공식 뉴스 감성점수
# ==============================================================

def select_themes_by_sentiment(sentiment_df: pd.DataFrame,
                                monthly_candidates: dict,
                                top_n: int = TOP_N) -> dict:
    """
    후보 테마 중 뉴스 감성점수가 높은 TOP5를 최종 선정.
    점수 = 긍정비율×0.6 + 정규화합계×0.4
    데이터 없는 후보는 텔레그램 순위 순서 그대로 보완.
    """
    print("\nSTEP 4. 뉴스 감성점수 기반 테마 선정...")
    monthly_tops = {}

    for month, candidates in sorted(monthly_candidates.items()):
        month_str = str(month)
        sub = sentiment_df[sentiment_df['month'] == month_str]

        if sub.empty:
            monthly_tops[month] = candidates[:top_n]
            print(f"  {month_str}: 뉴스 없음 → 텔레그램 순위 유지")
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
        top = sdf.sort_values('final', ascending=False)['theme'].tolist()[:top_n]

        # 감성 데이터 없는 후보로 부족분 보완
        for c in candidates:
            if c not in top and len(top) < top_n:
                top.append(c)

        monthly_tops[month] = top
        print(f"  {month_str}: {' / '.join(top)} (뉴스 감성 기반)")

    return monthly_tops


# ==============================================================
# STEP 5. 텔레그램 언급량 피처 생성 (XGBoost 피처용)
# ==============================================================

def get_telegram_features(tg_df: pd.DataFrame,
                           monthly_tops: dict,
                           theme_map: dict) -> pd.DataFrame:
    """
    날짜 × 테마별 텔레그램 언급량 집계.
    반환 컬럼: date, theme, tg_mention_count, tg_mention_ma3
    """
    all_themes = set(t for tops in monthly_tops.values() for t in tops)
    all_rows   = []

    for theme in all_themes:
        stocks   = theme_map.get(theme, [])
        keywords = [theme] + [s for s in stocks if len(s) > 1]
        pattern  = '|'.join(map(re.escape, keywords))
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
        daily.columns    = ['date', 'tg_mention_count']
        daily['theme']   = theme
        all_rows.append(daily)

    if not all_rows:
        return pd.DataFrame(columns=['date', 'theme', 'tg_mention_count', 'tg_mention_ma3'])

    feat = pd.concat(all_rows, ignore_index=True).sort_values(['theme', 'date'])
    feat['tg_mention_ma3'] = (
        feat.groupby('theme')['tg_mention_count']
        .transform(lambda x: x.rolling(3, min_periods=1).mean())
    )
    feat['date'] = pd.to_datetime(feat['date']).dt.normalize()
    print(f"텔레그램 피처 생성: {len(feat):,}행 / {feat['theme'].nunique()}개 테마")
    return feat


# ==============================================================
# STEP 6. yfinance 주가 + KOSPI 수집 (거래량·52주·상대강도)
# ==============================================================
import yfinance as yf
import FinanceDataReader as fdr


def _get_krx_codes(top_n: int) -> set:
    try:
        frames = []
        for market in ['KOSPI', 'KOSDAQ']:
            df = fdr.StockListing(market)
            if 'Code' in df.columns and 'Marcap' in df.columns:
                frames.append(df[['Code', 'Marcap']].dropna())
        if not frames:
            raise ValueError("StockListing 결과 없음")
        combined          = pd.concat(frames, ignore_index=True)
        combined['Marcap'] = pd.to_numeric(combined['Marcap'], errors='coerce')
        top   = combined.nlargest(top_n, 'Marcap')
        codes = set(str(c).zfill(6) for c in top['Code'])
        print(f"  상위 {top_n}종목 코드 {len(codes)}개 확보")
        return codes
    except Exception as e:
        print(f"  코드 조회 실패: {e}")
        return set()


def _get_kospi_data(start_dt: str, end_dt: str) -> pd.DataFrame:
    raw = yf.download('^KS11', start=start_dt, end=end_dt, progress=False, auto_adjust=True)
    if raw.empty:
        return pd.DataFrame(columns=['date', 'kospi_return'])
    df = pd.DataFrame({'kospi_close': raw['Close'].squeeze()})
    df['kospi_return'] = df['kospi_close'].pct_change()
    df.index.name = 'date'
    df = df.reset_index()
    df['date'] = pd.to_datetime(df['date']).dt.normalize()
    return df[['date', 'kospi_return']]


def _download_stock(code: str, start: str, end: str):
    for suffix in ['.KS', '.KQ']:
        ticker = code + suffix
        try:
            raw = yf.download(ticker, start=start, end=end,
                              progress=False, auto_adjust=True)
            if not raw.empty:
                want = [c for c in ['Close', 'High', 'Volume'] if c in raw.columns]
                return raw[want].copy(), ticker
        except Exception:
            continue
    return pd.DataFrame(), None


def get_stock_data(monthly_tops: dict, theme_code_map: dict) -> pd.DataFrame:
    all_themes = set(t for tops in monthly_tops.values() for t in tops)
    start_str  = str(min(monthly_tops)).replace('-', '')
    start_dt   = f"{start_str[:4]}-{start_str[4:6]}-01"
    end_dt     = datetime.now().strftime('%Y-%m-%d')

    print(f"KRX300 코드 조회...")
    krx300 = _get_krx_codes(KRX300_TOP_N)
    print(f"KRX500 코드 조회...")
    krx500 = _get_krx_codes(KRX500_TOP_N)

    print(f"\nKOSPI 지수 수집...")
    kospi_df = _get_kospi_data(start_dt, end_dt)

    all_data = []
    for theme in all_themes:
        code_dict = theme_code_map.get(theme, {})
        if not code_dict:
            print(f"\n[{theme}] 코드 정보 없음 - skip")
            continue

        # KRX300 필터
        large_dict = {n: c for n, c in code_dict.items() if c in krx300}
        label = 'KRX300'

        # 3개 미만이면 KRX500으로 자동 확장
        if len(large_dict) < MIN_STOCKS_PER_THEME:
            large_dict = {n: c for n, c in code_dict.items() if c in krx500}
            label = 'KRX500'

        print(f"\n[{theme}] 전체 {len(code_dict)}개 → {label} {len(large_dict)}개")
        if not large_dict:
            print(f"  종목 없음 - skip")
            continue

        for stock_name, code in large_dict.items():
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
            df['stock']          = stock_name
            df['ticker']         = ticker
            df['theme']          = theme
            all_data.append(df)
            print(f"  {stock_name}({ticker}): {len(df)}일")
            time.sleep(0.15)

    if not all_data:
        raise ValueError("주가 데이터 없음. 코드 확인 필요.")

    stock_df = pd.concat(all_data, ignore_index=True)

    # KOSPI 상대강도 병합
    if not kospi_df.empty:
        stock_df = pd.merge(stock_df, kospi_df, on='date', how='left')
        stock_df['kospi_relative'] = stock_df['return_1d'] - stock_df['kospi_return']
    else:
        stock_df['kospi_relative'] = np.nan

    print(f"\n주가 수집 완료: {stock_df['stock'].nunique()}개 종목 / {stock_df['theme'].nunique()}개 테마")
    return stock_df


# ==============================================================
# STEP 7. 감성 + 텔레그램 + 주가 전체 병합
# ==============================================================

def merge_all(sentiment_df: pd.DataFrame,
              tg_feat: pd.DataFrame,
              stock_df: pd.DataFrame) -> pd.DataFrame:
    """
    감성점수(t일) → 익일 주가(t+1일) 매핑 후
    텔레그램 언급량 피처 합류, tg_news_ratio 파생
    """
    # 날짜별 감성 집계
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
        left_on=['date', 'theme'], right_on=['date_next', 'theme'],
        how='inner'
    ).drop(columns=['date_next'])

    merged = merged.sort_values(['stock', 'date'])
    for w in [3, 5]:
        merged[f'sentiment_ma{w}'] = (
            merged.groupby('stock')['sentiment_score']
            .transform(lambda x: x.rolling(w, min_periods=1).mean())
        )

    # 텔레그램 피처 병합
    if not tg_feat.empty:
        tg_feat = tg_feat.copy()
        tg_feat['date'] = pd.to_datetime(tg_feat['date']).dt.normalize()
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
    # 텔레그램/뉴스 비율: 과열(소문) 대비 공식 뉴스 비중 감지
    merged['tg_news_ratio'] = merged['tg_mention_count'] / (merged['news_count'] + 1)

    merged = merged.dropna(subset=['return_1d', 'sentiment_score'])
    print(f"병합 완료: {len(merged):,}행 / {merged['stock'].nunique()}개 종목")
    return merged


# ==============================================================
# STEP 8. XGBoost 예측 (12개 피처)
# ==============================================================
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, roc_auc_score

FEATURES = [
    # 뉴스 감성
    'sentiment_score', 'sentiment_ma3', 'sentiment_ma5', 'news_count',
    # 주가 기술
    'return_1d', 'return_5d', 'volume_change', 'high_52w_ratio', 'kospi_relative',
    # 텔레그램 시장반응
    'tg_mention_count', 'tg_mention_ma3', 'tg_news_ratio',
]
TARGET = 'up_next'


def train_xgboost(merged_df: pd.DataFrame) -> tuple:
    avail = [f for f in FEATURES if f in merged_df.columns]
    df    = merged_df.dropna(subset=avail + [TARGET]).copy()
    if len(df) < 20:
        raise ValueError(f"학습 데이터 부족: {len(df)}행")

    X, y  = df[avail].values, df[TARGET].values
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
        'feature': avail, 'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\n[피처 중요도]")
    print(importance.to_string(index=False))
    return model, stock_prob, importance, avail


# ==============================================================
# STEP 9. 최종 랭킹 + 시각화
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
    s     = final['sentiment_corr'].fillna(0)
    rng   = s.max() - s.min()
    final['corr_norm']   = (s - s.min()) / (rng if rng > 0 else 1)
    final['total_score'] = final['avg_up_prob'] * 0.6 + final['corr_norm'] * 0.4
    final = final.sort_values('total_score', ascending=False).reset_index(drop=True)
    final['rank'] = final.index + 1
    return final


def save_visualizations(final_df, merged_df, sentiment_df,
                         monthly_tops, tg_feat, importance_df, theme_map):
    all_themes = sorted(final_df['theme'].unique())
    n          = len(all_themes)

    # 월별 TOP5 테마 변화표 (뉴스 감성 기반)
    monthly_top_df = pd.DataFrame([
        {'month': str(m), 'rank': i + 1, 'theme': t}
        for m, tops in monthly_tops.items() for i, t in enumerate(tops)
    ])
    rank_pivot = monthly_top_df.pivot(index='month', columns='rank', values='theme')
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
    ax.set_title('월별 뉴스 감성 기반 TOP5 테마 변화', fontsize=13,
                 fontweight='bold', color='white', pad=12)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_PATH, 'chart1_monthly_theme_change.png'),
                dpi=150, bbox_inches='tight', facecolor='#0f1117')
    plt.show(); print("chart1 저장")

    # 테마별 TOP5 종목 상승확률 바 차트
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
    plt.suptitle('뉴스 감성 기반 테마별 핵심 관련주', fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_PATH, 'chart2_top_stocks.png'),
                dpi=150, bbox_inches='tight')
    plt.show(); print("chart2 저장")

    # 감성점수 vs 익일 수익률 산점도
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 4))
    if n == 1: axes = [axes]
    for ax, theme in zip(axes, all_themes):
        sub = merged_df[merged_df['theme'] == theme].dropna(
            subset=['sentiment_score', 'return_1d'])
        if sub.empty: continue
        ax.scatter(sub['sentiment_score'], sub['return_1d'],
                   alpha=0.4, s=20, color='#2A9D8F')
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
    plt.suptitle('테마 감성점수 vs 익일 주가 수익률', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_PATH, 'chart3_sentiment_corr.png'),
                dpi=150, bbox_inches='tight')
    plt.show(); print("chart3 저장")

    # 월별 감성점수 히트맵
    pivot = sentiment_df.groupby(['month', 'theme'])['score'].mean().unstack('theme')
    if not pivot.empty:
        fig, ax = plt.subplots(figsize=(max(8, len(pivot.columns) * 1.5),
                                        max(5, len(pivot) * 0.6)))
        sns.heatmap(pivot, cmap='RdYlGn', center=0, annot=True, fmt='.2f',
                    linewidths=0.5, ax=ax, cbar_kws={'label': '평균 감성점수'})
        ax.set_title('월별 × 테마별 뉴스 감성점수 히트맵', fontsize=13, fontweight='bold')
        plt.tight_layout()
        plt.savefig(os.path.join(RESULT_PATH, 'chart4_sentiment_heatmap.png'),
                    dpi=150, bbox_inches='tight')
        plt.show(); print("chart4 저장")

    # 텔레그램 월별 언급량 추이 (피처 기반)
    if not tg_feat.empty:
        tg_feat['month_str'] = pd.to_datetime(tg_feat['date']).dt.to_period('M').astype(str)
        monthly_tg = tg_feat.groupby(['month_str', 'theme'])['tg_mention_count'].sum().reset_index()
        fig, ax = plt.subplots(figsize=(12, 5))
        for theme in all_themes:
            sub = monthly_tg[monthly_tg['theme'] == theme]
            ax.plot(sub['month_str'], sub['tg_mention_count'],
                    marker='o', label=theme, linewidth=2)
        ax.set_title('텔레그램 채널 월별 테마 언급량 추이 (시장반응 피처)',
                     fontsize=13, fontweight='bold')
        ax.set_xlabel('월'); ax.set_ylabel('언급 횟수')
        ax.legend(); ax.grid(alpha=0.3); plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(RESULT_PATH, 'chart5_tg_mention_trend.png'),
                    dpi=150, bbox_inches='tight')
        plt.show(); print("chart5 저장")

    # XGBoost 피처 중요도
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ['#E63946' if i == 0 else '#457B9D' for i in range(len(importance_df))]
    ax.barh(importance_df['feature'][::-1], importance_df['importance'][::-1],
            color=colors[::-1], edgecolor='white')
    ax.set_title('XGBoost 피처 중요도 (12개 피처)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Importance')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_PATH, 'chart6_feature_importance.png'),
                dpi=150, bbox_inches='tight')
    plt.show(); print("chart6 저장")

    # tg_news_ratio 히트맵 (과열 감지)
    if 'tg_news_ratio' in merged_df.columns:
        ratio_pivot = (
            merged_df.groupby([merged_df['date'].dt.to_period('M').astype(str), 'theme'])
            ['tg_news_ratio'].mean().unstack('theme')
        )
        if not ratio_pivot.empty:
            fig, ax = plt.subplots(figsize=(max(8, len(ratio_pivot.columns) * 1.5),
                                            max(5, len(ratio_pivot) * 0.6)))
            sns.heatmap(ratio_pivot, cmap='YlOrRd', annot=True, fmt='.2f',
                        linewidths=0.5, ax=ax,
                        cbar_kws={'label': '텔레그램/뉴스 비율 (과열지표)'})
            ax.set_title('월별 텔레그램/뉴스 비율 히트맵 (높을수록 과열)',
                         fontsize=13, fontweight='bold')
            plt.tight_layout()
            plt.savefig(os.path.join(RESULT_PATH, 'chart7_tg_news_ratio.png'),
                        dpi=150, bbox_inches='tight')
            plt.show(); print("chart7 저장")


# ==============================================================
# 메인 실행
# ==============================================================

if __name__ == '__main__':
    os.makedirs(RESULT_PATH, exist_ok=True)

    # 공통: 네이버 테마 맵
    theme_map, theme_code_map = get_naver_theme_map()

    # STEP 1. 텔레그램 후보 테마 추출
    print("\n" + "=" * 60)
    print("STEP 1. 텔레그램 후보 테마 추출 (TOP10/월)")
    print("=" * 60)
    tg_df              = load_telegram(TG_DATA_PATH)
    monthly_candidates = get_candidate_themes(tg_df, theme_map, theme_code_map)

    # STEP 2. 뉴스 수집
    print("\n" + "=" * 60)
    print("STEP 2. Google + 네이버 뉴스 병행 수집 (BATCH_SIZE=200)")
    print("=" * 60)
    news_df = collect_monthly_news(monthly_candidates)

    # STEP 3. 감성 분석
    print("\n" + "=" * 60)
    print("STEP 3. Gemini LLM 감성 분석")
    print("=" * 60)
    sentiment_df = run_sentiment_analysis(news_df)

    # STEP 4. 뉴스 감성점수 기반 테마 선정
    print("\n" + "=" * 60)
    print("STEP 4. 뉴스 감성점수 기반 월별 TOP5 테마 선정")
    print("=" * 60)
    monthly_tops = select_themes_by_sentiment(sentiment_df, monthly_candidates)

    monthly_top_df = pd.DataFrame([
        {'month': str(m), 'rank': i + 1, 'theme': t}
        for m, tops in monthly_tops.items() for i, t in enumerate(tops)
    ])
    monthly_top_df.to_csv(os.path.join(RESULT_PATH, 'monthly_top_themes.csv'),
                          index=False, encoding='utf-8-sig')

    # STEP 5. 텔레그램 피처 생성
    print("\n" + "=" * 60)
    print("STEP 5. 텔레그램 언급량 피처 생성 (시장반응)")
    print("=" * 60)
    tg_feat = get_telegram_features(tg_df, monthly_tops, theme_map)

    # STEP 6. 주가 수집
    print("\n" + "=" * 60)
    print("STEP 6. 주가 데이터 수집 (거래량·52주·KOSPI 상대강도)")
    print("=" * 60)
    stock_df = get_stock_data(monthly_tops, theme_code_map)

    # STEP 7. 전체 병합
    print("\n" + "=" * 60)
    print("STEP 7. 감성 + 텔레그램 + 주가 병합")
    print("=" * 60)
    merged_df = merge_all(sentiment_df, tg_feat, stock_df)

    # STEP 8. XGBoost
    print("\n" + "=" * 60)
    print("STEP 8. XGBoost 학습 (12개 피처)")
    print("=" * 60)
    model, stock_prob, importance_df, avail_features = train_xgboost(merged_df)

    # STEP 9. 랭킹 + 시각화
    print("\n" + "=" * 60)
    print("STEP 9. 최종 랭킹 + 시각화")
    print("=" * 60)
    final_df   = get_final_ranking(stock_prob, merged_df)
    all_themes = sorted(final_df['theme'].unique())

    print("\n" + "=" * 65)
    print("최종 테마별 핵심 관련주 랭킹")
    print("(뉴스 감성 기반 테마 선정 + 텔레그램 시장반응 피처 적용)")
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

    save_visualizations(final_df, merged_df, sentiment_df,
                        monthly_tops, tg_feat, importance_df, theme_map)

    print("\n" + "=" * 55)
    print("전체 파이프라인 완료!")
    print(f"저장 경로: {RESULT_PATH}")
    print("=" * 55)

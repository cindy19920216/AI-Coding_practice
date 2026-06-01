# -*- coding: utf-8 -*-
"""
Gemini LLM 감성 분석 재실행 스크립트
────────────────────────────────────
기존 news_monthly.csv를 재사용하여 감성 분석만 Gemini로 교체한 뒤
STEP 5~7(병합 → XGBoost → 랭킹)을 다시 실행합니다.
전체 파이프라인을 재실행하지 않아도 됩니다.

사용법:
  1. Gemini API 키 발급: https://aistudio.google.com/apikey
  2. 환경변수 설정:  set GEMINI_API_KEY=your_key_here
     또는 아래 GEMINI_API_KEY 변수에 직접 입력
  3. 실행: python improve_sentiment.py

설치 (없을 경우):
  pip install google-generativeai
"""

import os, sys, json, time, re
from datetime import datetime

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
from sklearn.metrics import roc_auc_score

sys.stdout.reconfigure(encoding='utf-8')

# ── 설정 ────────────────────────────────────────────────────
BASE_DIR     = r'C:\Users\Check\Desktop\AI 금융_FINAL'
RESULT_PATH  = os.path.join(BASE_DIR, 'results')
TG_DATA_PATH = os.path.join(BASE_DIR, 'telegram_data')

GEMINI_API_KEY    = os.environ.get('GEMINI_API_KEY', '')  # 여기에 직접 입력 가능
GEMINI_MODEL      = 'gemini-1.5-flash'
GEMINI_BATCH_SIZE = 20

FEATURES = ['sentiment_score', 'sentiment_ma3', 'sentiment_ma5',
            'news_count', 'return_1d', 'return_5d']
TARGET   = 'up_next'
KRX300_TOP_N = 300

# ── Gemini 감성 분석 ─────────────────────────────────────────

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


def _parse_gemini_json(text: str, fallback_ids: list) -> list:
    try:
        cleaned = text.strip()
        if '```' in cleaned:
            parts = cleaned.split('```')
            cleaned = parts[1].lstrip('json').strip() if len(parts) > 1 else cleaned
        return json.loads(cleaned)
    except Exception:
        return [{'id': i, 'label': '중립', 'score': 0} for i in fallback_ids]


def run_gemini_sentiment(news_df: pd.DataFrame, api_key: str) -> pd.DataFrame:
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("pip install google-generativeai 실행 후 재시도하세요.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=_GEMINI_SYSTEM)

    df = news_df.copy().reset_index(drop=True)
    total = len(df)
    id_to_result: dict = {}

    print(f"Gemini 감성 분석 시작: {total}건 / 배치 {GEMINI_BATCH_SIZE}개")
    for start in range(0, total, GEMINI_BATCH_SIZE):
        end = min(start + GEMINI_BATCH_SIZE, total)
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
        print(f"  [{start+1}~{end}/{total}]", end=" ", flush=True)
        try:
            resp = model.generate_content(prompt)
            results = _parse_gemini_json(resp.text, [r['id'] for r in batch_rows])
        except Exception as e:
            print(f"오류({e})", end=" ")
            results = [{'id': r['id'], 'label': '중립', 'score': 0} for r in batch_rows]
        id_to_result.update({r['id']: r for r in results})
        print("완료")
        time.sleep(2)  # 15 RPM 제한 대응

    rows = []
    for i, row in df.iterrows():
        res = id_to_result.get(i, {'label': '중립', 'score': 0})
        rows.append({
            'date': row['date'], 'month': row['month'],
            'theme': row['theme'], 'title': row.get('title', ''),
            'label': res.get('label', '중립'),
            'score': int(res.get('score', 0)),
        })
    result_df = pd.DataFrame(rows)

    pos = (result_df['label'] == '긍정').sum()
    neg = (result_df['label'] == '부정').sum()
    neu = (result_df['label'] == '중립').sum()
    print(f"\n[결과] 긍정:{pos}({pos/total*100:.0f}%) / "
          f"부정:{neg}({neg/total*100:.0f}%) / "
          f"중립:{neu}({neu/total*100:.0f}%)")
    print(f"  키워드 방식 대비 중립 비율: 72% → {neu/total*100:.0f}%")
    return result_df


# ── KRX300 + 주가 (기존 final_theme_stocks와 동일한 방식) ───

def get_krx300_codes(top_n: int = KRX300_TOP_N) -> set:
    print(f"KRX300 근사 조회 중 (시총 상위 {top_n}종목)...")
    frames = []
    for market in ['KOSPI', 'KOSDAQ']:
        df = fdr.StockListing(market)
        if 'Code' in df.columns and 'Marcap' in df.columns:
            frames.append(df[['Code', 'Marcap']].dropna())
    combined = pd.concat(frames, ignore_index=True)
    combined['Marcap'] = pd.to_numeric(combined['Marcap'], errors='coerce')
    top = combined.nlargest(top_n, 'Marcap')
    codes = set(str(c).zfill(6) for c in top['Code'])
    print(f"  KRX300 {len(codes)}종목 (최소 시총 {top['Marcap'].min()/1e8:.0f}억원)")
    return codes


def get_naver_theme_codes(all_themes: set) -> dict:
    print("네이버 테마 종목 코드 수집 중...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    theme_code_map = {}
    for page in range(1, 8):
        url = f"https://finance.naver.com/sise/theme.naver?&page={page}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'euc-kr'
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.select('td.col_type1 a')
            if not links:
                break
            for link in links:
                name = re.sub(r'\(.*?\)', '', link.text).strip()
                if name not in all_themes:
                    continue
                detail_url = "https://finance.naver.com" + link['href']
                try:
                    d = requests.get(detail_url, headers=headers, timeout=10)
                    d.encoding = 'euc-kr'
                    ds = BeautifulSoup(d.text, 'html.parser')
                    tags = ds.find_all('a', href=re.compile(r'/item/main\.naver\?code=\d{6}'))
                    codes, seen = {}, set()
                    for s in tags:
                        sname = s.text.strip()
                        m = re.search(r'code=(\d{6})', s.get('href', ''))
                        if sname and m and m.group(1) not in seen:
                            codes[sname] = m.group(1)
                            seen.add(m.group(1))
                    theme_code_map[name] = codes
                    print(f"  [{name}] {len(codes)}종목")
                    time.sleep(0.15)
                except Exception:
                    continue
        except Exception as e:
            print(f"  page {page} 실패: {e}")
            break
    return theme_code_map


def get_stock_data(monthly_tops: dict, theme_code_map: dict, krx300_codes: set) -> pd.DataFrame:
    all_themes = set(t for tops in monthly_tops.values() for t in tops)
    start_str = min(str(m) for m in monthly_tops)
    start_dt  = f"{start_str[:4]}-{start_str[5:7]}-01" if '-' in start_str else f"{start_str[:4]}-{start_str[4:6]}-01"
    end_dt    = datetime.now().strftime('%Y-%m-%d')

    all_data = []
    for theme in all_themes:
        code_dict = theme_code_map.get(theme, {})
        large_dict = {n: c for n, c in code_dict.items() if c in krx300_codes}
        print(f"\n[{theme}] 전체 {len(code_dict)}개 → KRX300 {len(large_dict)}개")
        if not large_dict:
            continue
        for sname, code in large_dict.items():
            for suffix in ['.KS', '.KQ']:
                try:
                    raw = yf.download(code + suffix, start=start_dt, end=end_dt,
                                      progress=False, auto_adjust=True)
                    if not raw.empty:
                        df = raw[['Close']].copy()
                        df.columns = ['close']
                        df.index.name = 'date'
                        df.reset_index(inplace=True)
                        df['date'] = pd.to_datetime(df['date']).dt.normalize()
                        df['stock'] = sname
                        df['ticker'] = code + suffix
                        df['theme'] = theme
                        df['return_1d'] = df['close'].pct_change()
                        df['return_5d'] = df['close'].pct_change(5)
                        df['up_next'] = (df['return_1d'].shift(-1) > 0).astype(int)
                        all_data.append(df)
                        print(f"  {sname}({code+suffix}): {len(df)}일")
                        time.sleep(0.1)
                        break
                except Exception:
                    continue

    if not all_data:
        raise ValueError("KRX300 주가 데이터 없음")
    return pd.concat(all_data, ignore_index=True)


# ── MAIN ────────────────────────────────────────────────────

if __name__ == '__main__':
    if not GEMINI_API_KEY:
        print("=" * 55)
        print("GEMINI_API_KEY가 설정되지 않았습니다.")
        print("  1. https://aistudio.google.com/apikey 에서 무료 발급")
        print("  2. 터미널에서: set GEMINI_API_KEY=your_key")
        print("  3. 또는 이 파일 상단 GEMINI_API_KEY 변수에 직접 입력")
        print("=" * 55)
        sys.exit(1)

    os.makedirs(RESULT_PATH, exist_ok=True)

    # 기존 데이터 로드
    print("=" * 55)
    print("기존 뉴스·테마 데이터 로드")
    print("=" * 55)
    monthly_top_df = pd.read_csv(os.path.join(RESULT_PATH, 'monthly_top_themes.csv'))
    news_df        = pd.read_csv(os.path.join(RESULT_PATH, 'news_monthly.csv'))
    news_df['date'] = pd.to_datetime(news_df['date'], errors='coerce')
    if 'text' not in news_df.columns:
        news_df['text'] = news_df['title'].astype(str) + ' ' + news_df.get('desc', '').astype(str)

    monthly_tops = {}
    for _, row in monthly_top_df.iterrows():
        m = row['month']
        monthly_tops.setdefault(m, []).append(row['theme'])

    print(f"  뉴스: {len(news_df):,}건 / 테마: {monthly_top_df['theme'].nunique()}개")

    # STEP 3: Gemini 감성 분석
    print("\n" + "=" * 55)
    print("STEP 3. Gemini 감성 분석")
    print("=" * 55)
    sentiment_df = run_gemini_sentiment(news_df, GEMINI_API_KEY)
    sentiment_df.to_csv(os.path.join(RESULT_PATH, 'sentiment_result.csv'),
                        index=False, encoding='utf-8-sig')
    print("sentiment_result.csv 저장 완료")

    # STEP 4: 주가 데이터 (기존 final_theme_stocks에서 종목 재사용)
    print("\n" + "=" * 55)
    print("STEP 4. KRX300 주가 데이터")
    print("=" * 55)
    all_themes    = set(t for tops in monthly_tops.values() for t in tops)
    krx300_codes  = get_krx300_codes()
    theme_code_map = get_naver_theme_codes(all_themes)
    stock_df = get_stock_data(monthly_tops, theme_code_map, krx300_codes)
    print(f"\n주가 수집: {stock_df['stock'].nunique()}개 종목 / {stock_df['theme'].nunique()}개 테마")

    # STEP 5: 병합
    print("\n" + "=" * 55)
    print("STEP 5. 감성 + 주가 병합")
    print("=" * 55)
    sent_agg = (
        sentiment_df
        .groupby([pd.Grouper(key='date', freq='D'), 'theme'])['score']
        .agg(sentiment_score='mean', news_count='count')
        .reset_index()
    )
    sent_agg['date']      = pd.to_datetime(sent_agg['date']).dt.normalize()
    sent_agg['date_next'] = sent_agg['date'] + pd.Timedelta(days=1)

    merged = pd.merge(
        stock_df,
        sent_agg[['date_next', 'theme', 'sentiment_score', 'news_count']],
        left_on=['date', 'theme'], right_on=['date_next', 'theme'], how='inner'
    ).drop(columns=['date_next']).sort_values(['stock', 'date'])

    for w in [3, 5]:
        merged[f'sentiment_ma{w}'] = (
            merged.groupby('stock')['sentiment_score']
            .transform(lambda x: x.rolling(w, min_periods=1).mean())
        )
    merged = merged.dropna(subset=['return_1d', 'sentiment_score'])
    print(f"병합: {len(merged):,}행 / {merged['stock'].nunique()}개 종목")

    # STEP 6: XGBoost
    print("\n" + "=" * 55)
    print("STEP 6. XGBoost")
    print("=" * 55)
    df_xgb = merged.dropna(subset=FEATURES + [TARGET]).copy()
    X, y = df_xgb[FEATURES].values, df_xgb[TARGET].values
    aucs, model = [], None
    for tr, val in TimeSeriesSplit(n_splits=5).split(X):
        if not len(val): continue
        m = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05,
                          subsample=0.8, colsample_bytree=0.8,
                          eval_metric='logloss', random_state=42, verbosity=0)
        m.fit(X[tr], y[tr], eval_set=[(X[val], y[val])], verbose=False)
        if len(np.unique(y[val])) > 1:
            aucs.append(roc_auc_score(y[val], m.predict_proba(X[val])[:, 1]))
        model = m
    print(f"[XGBoost] 평균 AUC: {np.mean(aucs):.4f} (±{np.std(aucs):.4f})")
    importance = pd.DataFrame({'feature': FEATURES,
                               'importance': model.feature_importances_}
                              ).sort_values('importance', ascending=False)
    print(importance.to_string(index=False))

    # STEP 7: 랭킹
    print("\n" + "=" * 55)
    print("STEP 7. 최종 랭킹")
    print("=" * 55)
    df_xgb['up_prob'] = model.predict_proba(X)[:, 1]
    stock_prob = (
        df_xgb.groupby(['theme', 'stock'])['up_prob'].mean().reset_index()
        .rename(columns={'up_prob': 'avg_up_prob'})
    )
    corr_list = [
        {'stock': s, 'sentiment_corr': round(g['sentiment_score'].corr(g['return_1d']), 4)}
        for s, g in merged.groupby('stock') if len(g) >= 5
    ]
    corr_df = pd.DataFrame(corr_list)
    final = pd.merge(stock_prob, corr_df, on='stock', how='left')
    s   = final['sentiment_corr'].fillna(0)
    rng = s.max() - s.min()
    final['corr_norm']   = (s - s.min()) / (rng if rng > 0 else 1)
    final['total_score'] = final['avg_up_prob'] * 0.6 + final['corr_norm'] * 0.4
    final = final.sort_values('total_score', ascending=False).reset_index(drop=True)
    final['rank'] = final.index + 1

    all_themes_sorted = sorted(final['theme'].unique())
    print("\n" + "=" * 65)
    print("테마별 핵심 관련주 (Gemini 감성 기준)")
    print("=" * 65)
    for theme in all_themes_sorted:
        sub = final[final['theme'] == theme].head(5)
        print(f"\n▶ [{theme}]")
        print(f"  {'종목':<14} {'상승확률':>8} {'감성상관':>9} {'종합점수':>9}")
        print(f"  {'-'*44}")
        for _, r in sub.iterrows():
            print(f"  {r['stock']:<14} {r['avg_up_prob']:>8.1%} "
                  f"{r.get('sentiment_corr', float('nan')):>+9.3f} {r['total_score']:>9.3f}")

    final.to_csv(os.path.join(RESULT_PATH, 'final_theme_stocks_gemini.csv'),
                 index=False, encoding='utf-8-sig')

    # 차트 저장
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = ['#E63946' if i == 0 else '#457B9D' for i in range(len(importance))]
    ax.barh(importance['feature'][::-1], importance['importance'][::-1],
            color=colors[::-1], edgecolor='white')
    ax.set_title('XGBoost 피처 중요도 (Gemini 감성 분석 적용)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Importance')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_PATH, 'chart6_feature_importance_gemini.png'),
                dpi=150, bbox_inches='tight')
    plt.close()

    print("\n" + "=" * 55)
    print("완료! 저장 파일:")
    print("  results/sentiment_result.csv          (Gemini 감성)")
    print("  results/final_theme_stocks_gemini.csv (Gemini 기반 랭킹)")
    print("  results/chart6_feature_importance_gemini.png")
    print("=" * 55)

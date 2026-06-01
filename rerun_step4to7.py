# -*- coding: utf-8 -*-
"""
기존 monthly_top_themes.csv + news/sentiment 데이터 재사용
STEP 4 (KRX300 필터) ~ STEP 7 (랭킹+시각화) 만 재실행
"""
import os, re, time, sys
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
from sklearn.metrics import classification_report, roc_auc_score

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR    = r'C:\Users\Check\Desktop\AI 금융_FINAL'
RESULT_PATH = os.path.join(BASE_DIR, 'results')
TG_DATA_PATH = os.path.join(BASE_DIR, 'telegram_data')

FEATURES = ['sentiment_score', 'sentiment_ma3', 'sentiment_ma5',
            'news_count', 'return_1d', 'return_5d']
TARGET   = 'up_next'
KRX300_TOP_N = 300

# ==============================================================
# 기존 결과 로드
# ==============================================================
print("기존 결과 로드 중...")
monthly_top_df   = pd.read_csv(os.path.join(RESULT_PATH, 'monthly_top_themes.csv'))
news_df          = pd.read_csv(os.path.join(RESULT_PATH, 'news_monthly.csv'))
sentiment_df     = pd.read_csv(os.path.join(RESULT_PATH, 'sentiment_result.csv'))

news_df['date']      = pd.to_datetime(news_df['date'], errors='coerce')
sentiment_df['date'] = pd.to_datetime(sentiment_df['date'], errors='coerce')

monthly_tops = {}
for _, row in monthly_top_df.iterrows():
    m = row['month']
    if m not in monthly_tops:
        monthly_tops[m] = []
    monthly_tops[m].append(row['theme'])

print(f"  monthly_top_themes: {len(monthly_tops)}개월 / {len(monthly_top_df)}행")
print(f"  news_monthly:       {len(news_df):,}건")
print(f"  sentiment_result:   {len(sentiment_df):,}건")

# ==============================================================
# 네이버 테마 코드맵 수집 (종목코드만 필요)
# ==============================================================
all_themes = set(t for tops in monthly_tops.values() for t in tops)
print(f"\n대상 테마: {sorted(all_themes)}")

print("\n네이버 테마 종목 코드 수집 중...")
headers = {'User-Agent': 'Mozilla/5.0'}
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
            if theme_name not in all_themes:
                continue
            detail_url = "https://finance.naver.com" + link['href']
            try:
                d = requests.get(detail_url, headers=headers, timeout=10)
                d.encoding = 'euc-kr'
                ds   = BeautifulSoup(d.text, 'html.parser')
                tags = ds.find_all('a', href=re.compile(r'/item/main\.naver\?code=\d{6}'))
                codes, seen = {}, set()
                for s in tags:
                    sname = s.text.strip()
                    m     = re.search(r'code=(\d{6})', s.get('href', ''))
                    if sname and m and m.group(1) not in seen:
                        codes[sname] = m.group(1)
                        seen.add(m.group(1))
                theme_code_map[theme_name] = codes
                print(f"  [{theme_name}] {len(codes)}종목")
                time.sleep(0.15)
            except Exception:
                continue
    except Exception as e:
        print(f"  page {page} 실패: {e}")
        break

print(f"코드 수집 완료: {len(theme_code_map)}개 테마")

# ==============================================================
# STEP 4. KRX300 필터 적용 주가 수집
# ==============================================================
print("\n" + "="*60)
print("STEP 4. KRX300 필터 주가 수집")
print("="*60)

def get_krx300_codes(top_n: int = KRX300_TOP_N):
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
        print(f"조회 실패: {e}")
        return set()

def _download(code, start, end):
    for suffix in ['.KS', '.KQ']:
        try:
            raw = yf.download(code + suffix, start=start, end=end,
                              progress=False, auto_adjust=True)
            if not raw.empty:
                return raw, code + suffix
        except Exception:
            continue
    return pd.DataFrame(), None

krx300_codes = get_krx300_codes()

start_str = min(monthly_tops)
start_dt  = f"{start_str[:4]}-{start_str[5:7]}-01" if '-' in start_str else f"{start_str[:4]}-{start_str[4:6]}-01"
end_dt    = datetime.now().strftime('%Y-%m-%d')

all_data = []
for theme in all_themes:
    code_dict = theme_code_map.get(theme, {})
    if not code_dict:
        print(f"\n[{theme}] 네이버 코드 없음 - skip")
        continue
    large_dict = {n: c for n, c in code_dict.items() if c in krx300_codes}
    print(f"\n[{theme}] 전체 {len(code_dict)}개 → KRX300 {len(large_dict)}개")
    if not large_dict:
        print(f"  KRX300 종목 없음 - skip")
        continue
    for sname, code in large_dict.items():
        raw, ticker = _download(code, start_dt, end_dt)
        if raw.empty:
            continue
        df = raw[['Close']].copy()
        df.columns    = ['close']
        df.index.name = 'date'
        df.reset_index(inplace=True)
        df['date']      = pd.to_datetime(df['date']).dt.normalize()
        df['stock']     = sname
        df['ticker']    = ticker
        df['theme']     = theme
        df['return_1d'] = df['close'].pct_change()
        df['return_5d'] = df['close'].pct_change(5)
        df['up_next']   = (df['return_1d'].shift(-1) > 0).astype(int)
        all_data.append(df)
        print(f"  {sname}({ticker}): {len(df)}일")
        time.sleep(0.1)

if not all_data:
    raise ValueError("KRX300 주가 데이터 없음")

stock_df = pd.concat(all_data, ignore_index=True)
print(f"\n주가 수집 완료: {stock_df['stock'].nunique()}개 KRX300 종목 / {stock_df['theme'].nunique()}개 테마")

# ==============================================================
# STEP 5. 감성 + 주가 병합
# ==============================================================
print("\n" + "="*60)
print("STEP 5. 감성점수 + 주가 병합")
print("="*60)

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
    left_on=['date', 'theme'], right_on=['date_next', 'theme'], how='inner'
).drop(columns=['date_next'])

merged = merged.sort_values(['stock', 'date'])
for w in [3, 5]:
    merged[f'sentiment_ma{w}'] = (
        merged.groupby('stock')['sentiment_score']
        .transform(lambda x: x.rolling(w, min_periods=1).mean())
    )
merged = merged.dropna(subset=['return_1d', 'sentiment_score'])
print(f"병합 완료: {len(merged):,}행 / {merged['stock'].nunique()}개 종목")

# ==============================================================
# STEP 6. XGBoost
# ==============================================================
print("\n" + "="*60)
print("STEP 6. XGBoost 학습")
print("="*60)

df_xgb = merged.dropna(subset=FEATURES + [TARGET]).copy()
if len(df_xgb) < 20:
    raise ValueError(f"학습 데이터 부족: {len(df_xgb)}행")

X, y = df_xgb[FEATURES].values, df_xgb[TARGET].values
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
    print(f"[XGBoost] 평균 AUC: {np.mean(aucs):.4f} (±{np.std(aucs):.4f})")

df_xgb['up_prob'] = model.predict_proba(X)[:, 1]
stock_prob = (
    df_xgb.groupby(['theme', 'stock'])['up_prob'].mean().reset_index()
    .rename(columns={'up_prob': 'avg_up_prob'})
    .sort_values('avg_up_prob', ascending=False)
)
importance = pd.DataFrame({
    'feature': FEATURES, 'importance': model.feature_importances_
}).sort_values('importance', ascending=False)
print("\n[피처 중요도]")
print(importance.to_string(index=False))

# ==============================================================
# STEP 7. 최종 랭킹 + 출력
# ==============================================================
print("\n" + "="*60)
print("STEP 7. 최종 랭킹")
print("="*60)

corr_list = []
for stock, grp in merged.groupby('stock'):
    if len(grp) < 5:
        continue
    corr = grp['sentiment_score'].corr(grp['return_1d'])
    corr_list.append({'stock': stock, 'sentiment_corr': round(corr, 4)})
corr_df = pd.DataFrame(corr_list)

final = pd.merge(stock_prob, corr_df, on='stock', how='left')
s   = final['sentiment_corr'].fillna(0)
rng = s.max() - s.min()
final['corr_norm']   = (s - s.min()) / (rng if rng > 0 else 1)
final['total_score'] = final['avg_up_prob'] * 0.6 + final['corr_norm'] * 0.4
final = final.sort_values('total_score', ascending=False).reset_index(drop=True)
final['rank'] = final.index + 1

all_themes_sorted = sorted(final['theme'].unique())

print("\n" + "="*65)
print("최종 테마별 핵심 관련주 랭킹 (KRX300 기준 대형주만)")
print("="*65)
for theme in all_themes_sorted:
    sub = final[final['theme'] == theme].head(5)
    print(f"\n▶ [{theme}]")
    print(f"  {'종목':<14} {'상승확률':>8} {'감성상관':>9} {'종합점수':>9}")
    print(f"  {'-'*44}")
    for _, r in sub.iterrows():
        print(f"  {r['stock']:<14} {r['avg_up_prob']:>8.1%} "
              f"{r.get('sentiment_corr', float('nan')):>+9.3f} {r['total_score']:>9.3f}")
print("="*65)

final.to_csv(os.path.join(RESULT_PATH, 'final_theme_stocks.csv'),
             index=False, encoding='utf-8-sig')
print(f"\nfinal_theme_stocks.csv 저장 완료")

# 시각화 2: 테마별 TOP5 바 차트
n = len(all_themes_sorted)
fig, axes = plt.subplots(1, n, figsize=(5 * n, 5))
if n == 1:
    axes = [axes]
for ax, theme in zip(axes, all_themes_sorted):
    sub    = final[final['theme'] == theme].head(5)
    colors = ['#E63946' if p > 0.55 else '#457B9D' for p in sub['avg_up_prob']]
    ax.barh(sub['stock'][::-1], sub['avg_up_prob'][::-1],
            color=colors[::-1], edgecolor='white')
    ax.axvline(0.5, color='gray', linestyle='--', linewidth=0.8)
    ax.set_title(f'{theme}\n핵심 관련주 (KRX300)', fontsize=11, fontweight='bold')
    ax.set_xlabel('주가 상승 확률'); ax.set_xlim(0, 1)
    for i, (_, row) in enumerate(sub[::-1].iterrows()):
        ax.text(row['avg_up_prob'] + 0.01, i,
                f"{row['avg_up_prob']:.1%}", va='center', fontsize=9)
plt.suptitle('KRX300 대형주 기준 테마별 핵심 관련주', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(RESULT_PATH, 'chart2_top_stocks.png'), dpi=150, bbox_inches='tight')
plt.close()
print("chart2_top_stocks.png 저장")

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
ax.set_title('월별 텔레그램 TOP5 테마 변화 (노이즈 필터 적용)', fontsize=13,
             fontweight='bold', color='white', pad=12)
plt.tight_layout()
plt.savefig(os.path.join(RESULT_PATH, 'chart1_monthly_theme_change.png'),
            dpi=150, bbox_inches='tight', facecolor='#0f1117')
plt.close()
print("chart1_monthly_theme_change.png 저장")

# ── 시각화 3: 감성점수 vs 익일 수익률 산점도 ──
n = len(all_themes_sorted)
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
    except (np.linalg.LinAlgError, ValueError):
        pass
    corr = sub['sentiment_score'].corr(sub['return_1d'])
    ax.set_title(f'{theme}\n상관계수: {corr:+.3f}', fontsize=11)
    ax.set_xlabel('감성 점수'); ax.set_ylabel('익일 수익률')
    ax.axhline(0, color='gray', linewidth=0.5); ax.axvline(0, color='gray', linewidth=0.5)
plt.suptitle('테마 감성점수 vs 익일 주가 수익률 (KRX300)', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(RESULT_PATH, 'chart3_sentiment_corr.png'),
            dpi=150, bbox_inches='tight')
plt.close()
print("chart3_sentiment_corr.png 저장")

# ── 시각화 4: 월별 감성점수 히트맵 ──
pivot = sentiment_df.groupby(['month', 'theme'])['score'].mean().unstack('theme')
if not pivot.empty:
    fig, ax = plt.subplots(figsize=(max(8, len(pivot.columns) * 1.5),
                                    max(5, len(pivot) * 0.6)))
    sns.heatmap(pivot, cmap='RdYlGn', center=0, annot=True, fmt='.2f',
                linewidths=0.5, ax=ax, cbar_kws={'label': '평균 감성점수'})
    ax.set_title('월별 × 테마별 감성점수 히트맵 (KRX300 기준 테마)', fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_PATH, 'chart4_sentiment_heatmap.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("chart4_sentiment_heatmap.png 저장")

# ── 시각화 5: 텔레그램 월별 언급량 추이 ──
tg_files = [
    os.path.join(TG_DATA_PATH, f) for f in os.listdir(TG_DATA_PATH)
    if f.startswith('telegram_data_') and f.endswith('.csv')
]
if tg_files:
    tg_df = pd.concat([pd.read_csv(f) for f in sorted(tg_files)], ignore_index=True)
    tg_df['Date']      = pd.to_datetime(tg_df['Date'])
    tg_df['month_str'] = tg_df['Date'].dt.to_period('M').astype(str)
    tg_df['Message']   = tg_df['Message'].astype(str)

    monthly_counts = []
    for theme in all_themes_sorted:
        stocks   = list(theme_code_map.get(theme, {}).keys())
        keywords = [theme] + [s for s in stocks if len(s) > 1]
        pattern  = '|'.join(map(re.escape, keywords))
        mask     = tg_df['Message'].str.contains(pattern, na=False)
        counts   = tg_df[mask].groupby('month_str').size().reset_index(name='count')
        counts['theme'] = theme
        monthly_counts.append(counts)

    monthly_df = pd.concat(monthly_counts, ignore_index=True)
    fig, ax = plt.subplots(figsize=(12, 5))
    for theme in all_themes_sorted:
        sub = monthly_df[monthly_df['theme'] == theme]
        ax.plot(sub['month_str'], sub['count'], marker='o', label=theme, linewidth=2)
    ax.set_title('텔레그램 채널 월별 테마 언급량 추이 (KRX300 기준)', fontsize=13, fontweight='bold')
    ax.set_xlabel('월'); ax.set_ylabel('언급 횟수')
    ax.legend(fontsize=8); ax.grid(alpha=0.3); plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_PATH, 'chart5_monthly_trend.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("chart5_monthly_trend.png 저장")

# ── 시각화 6: XGBoost 피처 중요도 ──
fig, ax = plt.subplots(figsize=(7, 4))
colors = ['#E63946' if i == 0 else '#457B9D' for i in range(len(importance))]
ax.barh(importance['feature'][::-1], importance['importance'][::-1],
        color=colors[::-1], edgecolor='white')
ax.set_title('XGBoost 피처 중요도 (KRX300 대형주 기준)', fontsize=12, fontweight='bold')
ax.set_xlabel('Importance')
plt.tight_layout()
plt.savefig(os.path.join(RESULT_PATH, 'chart6_feature_importance.png'),
            dpi=150, bbox_inches='tight')
plt.close()
print("chart6_feature_importance.png 저장")

print("\n전체 완료! 차트 1~6 모두 업데이트됨")

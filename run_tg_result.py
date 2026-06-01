# -*- coding: utf-8 -*-
"""
텔레그램 TOP 테마 분석 → 결과 이미지 저장
"""
import os, re, time
from collections import Counter
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import requests
from bs4 import BeautifulSoup

# ── 한글 폰트 ──
matplotlib.rcParams['font.family'] = 'Malgun Gothic'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
TG_PATH      = os.path.join(BASE_DIR, 'telegram_data')
RESULT_PATH  = os.path.join(BASE_DIR, 'results')
os.makedirs(RESULT_PATH, exist_ok=True)

# ── 1. 텔레그램 CSV 로드 ──
files = sorted([
    os.path.join(TG_PATH, f)
    for f in os.listdir(TG_PATH)
    if f.startswith('telegram_data_') and f.endswith('.csv')
])
print(f"CSV 파일 {len(files)}개 로드 중...")
df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
df['Date']    = pd.to_datetime(df['Date'])
df['Message'] = df['Message'].astype(str)
print(f"총 메시지: {len(df):,}건  |  기간: {df['Date'].min().date()} ~ {df['Date'].max().date()}")

# ── 2. 네이버 테마 수집 ──
print("\n네이버 테마 수집 중...")
headers    = {'User-Agent': 'Mozilla/5.0'}
theme_map  = {}

for page in range(1, 8):
    url  = f"https://finance.naver.com/sise/theme.naver?&page={page}"
    try:
        res  = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.select('td.col_type1 a')
        if not links:
            break
        for link in links:
            name = re.sub(r'\(.*?\)', '', link.text).strip()
            detail_url = "https://finance.naver.com/sise/" + link['href']
            try:
                d   = requests.get(detail_url, headers=headers, timeout=10)
                ds  = BeautifulSoup(d.text, 'html.parser')
                stocks = [s.text.strip() for s in ds.select('td.name a')]
                theme_map[name] = stocks
                time.sleep(0.15)
            except Exception:
                continue
    except Exception as e:
        print(f"  page {page} 실패: {e}")
        break

print(f"수집된 테마: {len(theme_map)}개")

# ── 3. 테마 언급 빈도 계산 ──
STOPWORDS = {'증권', '투자', '시장', '금융', '뱅킹'}
results   = []
for msg in df['Message']:
    seen = set()
    for theme, stocks in theme_map.items():
        if theme in STOPWORDS:
            continue
        if theme in msg and theme not in seen:
            results.append(theme); seen.add(theme); continue
        for stock in stocks:
            if len(stock) > 1 and stock in msg and theme not in seen:
                results.append(theme); seen.add(theme); break

counter   = Counter(results)
TOP_N     = 10
top_items = counter.most_common(TOP_N)

print("\n" + "="*45)
print(f"텔레그램 기반 주도 테마 TOP {TOP_N}")
print("="*45)
for i, (name, cnt) in enumerate(top_items):
    stocks_preview = ', '.join(theme_map.get(name, [])[:3])
    print(f"  {i+1:2d}위: {name:<15} {cnt:>5,}회  ({stocks_preview}...)")
print("="*45)

# ── 4. 월별 언급량 집계 ──
df['month'] = df['Date'].dt.to_period('M').astype(str)
TOP5        = [n for n, _ in top_items[:5]]

monthly_rows = []
for theme in TOP5:
    stocks   = theme_map.get(theme, [])
    keywords = [theme] + [s for s in stocks if len(s) > 1]
    pattern  = '|'.join(map(re.escape, keywords))
    mask     = df['Message'].str.contains(pattern, na=False)
    for month, cnt in df[mask].groupby('month').size().items():
        monthly_rows.append({'month': month, 'theme': theme, 'count': cnt})
monthly_df = pd.DataFrame(monthly_rows)

# ── 5. 이미지 저장 ──────────────────────────────────────────
fig = plt.figure(figsize=(16, 10))
fig.patch.set_facecolor('#0f1117')

# ── 5-A. 상단 표 ──
ax_table = fig.add_axes([0.03, 0.52, 0.94, 0.44])
ax_table.set_facecolor('#0f1117')
ax_table.axis('off')

col_labels = ['순위', '테마명', '언급 횟수', '주요 관련주']
table_data  = []
for i, (name, cnt) in enumerate(top_items):
    stocks_str = '  /  '.join(theme_map.get(name, [])[:4])
    table_data.append([f"{i+1}위", name, f"{cnt:,}회", stocks_str])

tbl = ax_table.table(
    cellText=table_data,
    colLabels=col_labels,
    cellLoc='center',
    loc='center',
    colWidths=[0.07, 0.15, 0.10, 0.65],
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(10)

HEADER_COLOR = '#1a73e8'
ROW_COLORS   = ['#1e2130', '#161926']
RANK_COLORS  = ['#FFD700', '#C0C0C0', '#CD7F32']  # 금·은·동

for (row, col), cell in tbl.get_celld().items():
    cell.set_edgecolor('#2d3250')
    if row == 0:
        cell.set_facecolor(HEADER_COLOR)
        cell.set_text_props(color='white', fontweight='bold')
    else:
        cell.set_facecolor(ROW_COLORS[(row - 1) % 2])
        cell.set_text_props(color='white')
        if col == 0 and row <= 3:
            cell.set_text_props(color=RANK_COLORS[row - 1], fontweight='bold')

ax_table.set_title('텔레그램 채널 기반 주도 테마 TOP 10', color='white',
                   fontsize=14, fontweight='bold', pad=10)

# ── 5-B. 하단 꺾은선 차트 ──
ax_line = fig.add_axes([0.07, 0.05, 0.90, 0.40])
ax_line.set_facecolor('#161926')

PALETTE = ['#4FC3F7', '#81C784', '#FFB74D', '#E57373', '#CE93D8']
if not monthly_df.empty:
    months = sorted(monthly_df['month'].unique())
    for theme, color in zip(TOP5, PALETTE):
        sub = monthly_df[monthly_df['theme'] == theme].set_index('month').reindex(months, fill_value=0)
        ax_line.plot(months, sub['count'], marker='o', label=theme,
                     color=color, linewidth=2, markersize=5)
    ax_line.set_xticks(range(len(months)))
    ax_line.set_xticklabels(months, rotation=40, ha='right', color='#aaaaaa', fontsize=8)
    ax_line.tick_params(axis='y', colors='#aaaaaa')
    ax_line.spines[:].set_edgecolor('#2d3250')
    ax_line.set_facecolor('#161926')
    ax_line.grid(alpha=0.2, color='gray')
    ax_line.legend(loc='upper left', framealpha=0.3, labelcolor='white',
                   facecolor='#0f1117', fontsize=9)
    ax_line.set_title('TOP 5 테마 월별 언급량 추이', color='white',
                      fontsize=12, fontweight='bold', pad=8)

for spine in ax_line.spines.values():
    spine.set_edgecolor('#2d3250')

out_path = os.path.join(RESULT_PATH, 'telegram_theme_result.png')
plt.savefig(out_path, dpi=150, bbox_inches='tight',
            facecolor=fig.get_facecolor())
plt.show()
print(f"\n이미지 저장 완료: {out_path}")

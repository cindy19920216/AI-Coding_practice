# -*- coding: utf-8 -*-
"""Gemini 결과 기반 차트 갱신 (chart2, chart3, chart4, chart6)"""
import os, sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR    = r'C:\Users\Check\Desktop\AI 금융_FINAL'
RESULT_PATH = os.path.join(BASE_DIR, 'results')

# 데이터 로드
sentiment_df = pd.read_csv(os.path.join(RESULT_PATH, 'sentiment_result.csv'))
final_gemini = pd.read_csv(os.path.join(RESULT_PATH, 'final_theme_stocks_gemini.csv'))
sentiment_df['date'] = pd.to_datetime(sentiment_df['date'], errors='coerce')

# final_theme_stocks.csv 갱신 (Gemini 버전으로 교체)
final_gemini.to_csv(os.path.join(RESULT_PATH, 'final_theme_stocks.csv'),
                    index=False, encoding='utf-8-sig')
print("final_theme_stocks.csv → Gemini 버전으로 교체 완료")

all_themes = sorted(final_gemini['theme'].unique())

# ── chart2: 테마별 TOP5 상승확률 바 차트 ──────────────────────
n = len(all_themes)
fig, axes = plt.subplots(1, n, figsize=(5 * n, 5))
if n == 1:
    axes = [axes]
for ax, theme in zip(axes, all_themes):
    sub    = final_gemini[final_gemini['theme'] == theme].head(5)
    colors = ['#E63946' if p > 0.55 else '#457B9D' for p in sub['avg_up_prob']]
    ax.barh(sub['stock'][::-1], sub['avg_up_prob'][::-1],
            color=colors[::-1], edgecolor='white')
    ax.axvline(0.5, color='gray', linestyle='--', linewidth=0.8)
    ax.set_title(f'{theme}\n핵심 관련주 (Gemini+KRX300)', fontsize=10, fontweight='bold')
    ax.set_xlabel('주가 상승 확률'); ax.set_xlim(0, 1)
    for i, (_, row) in enumerate(sub[::-1].iterrows()):
        ax.text(row['avg_up_prob'] + 0.01, i,
                f"{row['avg_up_prob']:.1%}", va='center', fontsize=8)
plt.suptitle('Gemini LLM 감성 분석 기반 테마별 핵심 관련주 (KRX300)',
             fontsize=13, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(RESULT_PATH, 'chart2_top_stocks.png'), dpi=150, bbox_inches='tight')
plt.close()
print("chart2_top_stocks.png 저장 완료")

# ── chart4: 월별 × 테마별 감성 히트맵 ──────────────────────────
pivot = sentiment_df.groupby(['month', 'theme'])['score'].mean().unstack('theme')
if not pivot.empty:
    fig, ax = plt.subplots(figsize=(max(10, len(pivot.columns) * 1.4),
                                    max(5, len(pivot) * 0.6)))
    sns.heatmap(pivot, cmap='RdYlGn', center=0, annot=True, fmt='.2f',
                linewidths=0.5, ax=ax, cbar_kws={'label': '평균 감성점수 (Gemini)'})
    ax.set_title('월별 × 테마별 감성점수 히트맵 (Gemini LLM)', fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_PATH, 'chart4_sentiment_heatmap.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("chart4_sentiment_heatmap.png 저장 완료")

# ── chart6: XGBoost 피처 중요도 (Gemini 버전 → 메인으로 교체) ─
import shutil
gemini_chart6 = os.path.join(RESULT_PATH, 'chart6_feature_importance_gemini.png')
main_chart6   = os.path.join(RESULT_PATH, 'chart6_feature_importance.png')
if os.path.exists(gemini_chart6):
    shutil.copy2(gemini_chart6, main_chart6)
    print("chart6_feature_importance.png → Gemini 버전으로 교체 완료")

# 감성 분포 비교 차트 (NEW)
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

labels = ['긍정', '부정', '중립']
keyword_vals = [466, 149, 1643]
gemini_vals  = [
    (sentiment_df['label'] == '긍정').sum(),
    (sentiment_df['label'] == '부정').sum(),
    (sentiment_df['label'] == '중립').sum(),
]
colors = ['#2ECC71', '#E74C3C', '#95A5A6']

# 키워드 방식
axes[0].pie(keyword_vals, labels=labels, colors=colors, autopct='%1.0f%%',
            startangle=90, textprops={'fontsize': 12})
axes[0].set_title('키워드 방식\n(중립 72% → 정보 손실)', fontsize=12, fontweight='bold')

# Gemini 방식
axes[1].pie(gemini_vals, labels=labels, colors=colors, autopct='%1.0f%%',
            startangle=90, textprops={'fontsize': 12})
axes[1].set_title(f'Gemini LLM 방식\n(중립 {gemini_vals[2]/sum(gemini_vals)*100:.0f}% → 문맥 이해)',
                  fontsize=12, fontweight='bold')

plt.suptitle('감성 분석 방식 비교: 키워드 vs Gemini LLM', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(RESULT_PATH, 'chart7_sentiment_comparison.png'),
            dpi=150, bbox_inches='tight')
plt.close()
print("chart7_sentiment_comparison.png 저장 완료 (NEW)")

print("\n모든 차트 업데이트 완료!")
print(f"\n[Gemini 감성 분석 결과]")
print(f"  긍정: {gemini_vals[0]}건 ({gemini_vals[0]/sum(gemini_vals)*100:.0f}%)")
print(f"  부정: {gemini_vals[1]}건 ({gemini_vals[1]/sum(gemini_vals)*100:.0f}%)")
print(f"  중립: {gemini_vals[2]}건 ({gemini_vals[2]/sum(gemini_vals)*100:.0f}%)")

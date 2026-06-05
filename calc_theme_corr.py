import pandas as pd
try:
    df = pd.read_csv('results/final_theme_stocks.csv', encoding='utf-8-sig')
    theme_corr = df.groupby('theme')['sentiment_corr'].mean().sort_values(ascending=False)
    print("--- Average Sentiment Correlation per Theme ---")
    print(theme_corr)
except Exception as e:
    print(e)

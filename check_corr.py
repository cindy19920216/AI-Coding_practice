import pandas as pd
try:
    df = pd.read_csv('results/final_theme_stocks.csv', encoding='utf-8-sig')
    res = df.groupby('theme')['sentiment_corr'].mean().sort_values(ascending=False)
    print(res)
except Exception as e:
    print(e)

import pandas as pd
try:
    df = pd.read_csv('results/sentiment_result.csv', encoding='utf-8-sig')
    print("--- News Count per Theme ---")
    print(df['theme'].value_counts())
    
    # Also check the correlation of the aggregated theme sentiment with the average return of the theme
    # This might be what the user is looking at.
    # But wait, I need return data.
except Exception as e:
    print(e)

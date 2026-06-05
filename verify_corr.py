import pandas as pd
import yfinance as yf
import numpy as np

def check_validity():
    df = pd.read_csv('results/sentiment_result.csv', encoding='utf-8-sig')
    df['date'] = pd.to_datetime(df['date'])
    
    # Representative stocks
    stock_map = {
        '화이자': ['000100.KS', '128940.KS'],
        '은행': ['105560.KS', '055550.KS'],
        '화장품': ['090430.KS', '051900.KS'],
        '리츠': ['330590.KS', '365550.KS']
    }
    
    results = []
    
    for theme, tickers in stock_map.items():
        theme_news = df[df['theme'] == theme].groupby('date')['score'].mean().reset_index()
        if theme_news.empty:
            continue
            
        start_date = theme_news['date'].min().strftime('%Y-%m-%d')
        end_date = (theme_news['date'].max() + pd.Timedelta(days=5)).strftime('%Y-%m-%d')
        
        try:
            data = yf.download(tickers, start=start_date, end=end_date)
            if 'Adj Close' in data.columns:
                prices = data['Adj Close']
            else:
                prices = data['Close']
            
            # If MultiIndex (multiple tickers), it will be a DataFrame
            # If single ticker, it might be a Series (but I passed a list)
            returns = prices.pct_change().shift(-1)
            if isinstance(returns, pd.DataFrame):
                avg_return = returns.mean(axis=1)
            else:
                avg_return = returns
            
            merged = pd.merge(theme_news, avg_return.rename('return_1d'), left_on='date', right_index=True)
            merged = merged.dropna()
            
            if len(merged) > 2:
                corr = merged['score'].corr(merged['return_1d'])
                results.append({
                    'Theme': theme,
                    'Days': len(merged),
                    'NewsCount': len(df[df['theme'] == theme]),
                    'Correlation': corr
                })
            else:
                results.append({
                    'Theme': theme,
                    'Days': len(merged),
                    'NewsCount': len(df[df['theme'] == theme]),
                    'Correlation': np.nan
                })
        except Exception as e:
            print(f"Error for {theme}: {e}")
            
    print(pd.DataFrame(results))

check_validity()

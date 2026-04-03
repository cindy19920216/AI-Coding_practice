import os
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from scipy import stats
import statsmodels.api as sm

# ============================================================
# 1. Download Data
# ============================================================
print("=" * 60)
print("CAPM: Capital Asset Pricing Model")
print("=" * 60)

tickers = ["AAPL", "MSFT", "NVDA", "JNJ", "PG", "KO", "TSLA", "XOM", "JPM", "META"]
market = "SPY"  # Market proxy
rf_ticker = "^IRX"  # 13-week Treasury Bill (annualized)

print(f"\nDownloading: {tickers} + {market}")
start, end = "2015-01-01", "2025-12-31"

# Download all at once
all_tickers = tickers + [market]
prices = yf.download(all_tickers, start=start, end=end, auto_adjust=True)["Close"]

# Check if prices are empty
if prices.empty:
    raise ValueError("Failed to download data. Please check your internet connection or ticker symbols.")

prices.columns = prices.columns.droplevel(1) if isinstance(prices.columns, pd.MultiIndex) else prices.columns

# Monthly returns
monthly_prices = prices.resample("ME").last()
monthly_returns = monthly_prices.pct_change().dropna()

# Risk-free rate
RF_MONTHLY = 0.04 / 12  # ~0.33% per month
excess_returns = monthly_returns.sub(RF_MONTHLY)
market_excess = excess_returns[market]
stock_excess = excess_returns[tickers]

print(f"Period: {monthly_returns.index[0].strftime('%Y-%m')} to {monthly_returns.index[-1].strftime('%Y-%m')}")
print(f"Months: {len(monthly_returns)}")
print(f"Risk-free rate: {RF_MONTHLY*100:.2f}% monthly ({RF_MONTHLY*12*100:.1f}% annual)")

# ============================================================
# 2. Estimate CAPM for Each Stock
# ============================================================
print("\n" + "=" * 60)
print("Step 2: CAPM Regression for Each Stock")
print("=" * 60)
print(f"\n{'Ticker':<8} {'Alpha':>8} {'Beta':>8} {'R²':>8} {'p(alpha)':>10} {'p(beta)':>10}")
print("-" * 55)

capm_results = {}
for ticker in tickers:
    y = stock_excess[ticker].dropna().values
    X = sm.add_constant(market_excess.dropna().values)  # Add intercept (alpha)

    # Ensure no NaN values in X and y
    if len(y) != len(X):
        raise ValueError(f"Mismatch in data length for {ticker}. Check for NaN values.")

    model = sm.OLS(y, X).fit()

    alpha = model.params[0]
    beta = model.params[1]
    r2 = model.rsquared
    p_alpha = model.pvalues[0]
    p_beta = model.pvalues[1]

    capm_results[ticker] = {
        "alpha": alpha, "beta": beta, "r2": r2,
        "p_alpha": p_alpha, "p_beta": p_beta,
        "alpha_annual": alpha * 12,
        "avg_excess": y.mean() * 12,
    }

    sig_alpha = "*" if p_alpha < 0.05 else " "
    print(f"{ticker:<8} {alpha:>8.4f}{sig_alpha} {beta:>7.2f}  {r2:>7.2f}  {p_alpha:>9.4f}  {p_beta:>9.4f}")

print("\n* = alpha significantly different from 0 at 5% level")
print("If CAPM holds perfectly, all alphas should be zero.")

# ============================================================
# 3. Security Market Line (SML)
# ============================================================
print("\n" + "=" * 60)
print("Step 3: Security Market Line")
print("=" * 60)

betas = [capm_results[t]["beta"] for t in tickers]
avg_excess = [capm_results[t]["avg_excess"] for t in tickers]

market_premium = market_excess.mean() * 12
beta_range = np.linspace(0, 2.5, 100)
sml_line = beta_range * market_premium

print(f"Market Risk Premium (annualized): {market_premium*100:.2f}%")

# ============================================================
# 4. Plots
# ============================================================
output_dir = "./output"
os.makedirs(output_dir, exist_ok=True)  # Ensure output directory exists

plt.figure(figsize=(10, 6))
plt.plot(beta_range, sml_line * 100, "r--", linewidth=2, label="SML (theoretical)")
for i, t in enumerate(tickers):
    plt.scatter(betas[i], avg_excess[i] * 100, s=80, zorder=5)
    plt.annotate(t, (betas[i], avg_excess[i] * 100), fontsize=8,
                 xytext=(5, 5), textcoords="offset points")
plt.xlabel("Beta (β)")
plt.ylabel("Average Excess Return (% annual)")
plt.title("Security Market Line (SML)")
plt.legend()
plt.grid(True, alpha=0.3)
plt.axhline(0, color="gray", linewidth=0.5)
plt.savefig(f"{output_dir}/capm_sml.png", dpi=150, bbox_inches="tight")
plt.show()

print(f"\nSaved: {output_dir}/capm_sml.png")

# 파일에서 비인쇄 문자(U+00A0)를 제거합니다
with open(__file__, 'r', encoding='utf-8') as file:
    content = file.read()

# 불필요한 공백 문자를 일반 공백으로 대체
content = content.replace('\u00A0', ' ')

with open(__file__, 'w', encoding='utf-8') as file:
    file.write(content)

print("비인쇄 문자가 제거되었습니다.")
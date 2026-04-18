import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="ETF Dashboard", layout="wide")

st.title("📊 ETF Scoring Dashboard (Advanced)")

# -----------------------------
# 🔌 DATA INGESTION (Yahoo Finance)
# -----------------------------

def load_data(tickers):
    data = []
    for t in tickers:
        try:
            etf = yf.Ticker(t)
            info = etf.info

            data.append({
                'ticker': t,
                'expense_ratio': info.get('annualReportExpenseRatio', 0.002),
                'avg_volume': info.get('averageVolume', 0),
                'aum': info.get('totalAssets', 0),
                'spread': 0.001,  # placeholder
                'tracking_diff': 0,  # placeholder
                'is_physical': 1,
                'is_accumulating': 1 if 'Acc' in t else 0,
                'issuer_score': issuer_score(t),
                'price': info.get('regularMarketPrice', 0)
            })
        except:
            continue

    return pd.DataFrame(data)

# -----------------------------
# 🏢 ISSUER SCORING
# -----------------------------

def issuer_score(ticker):
    if any(x in ticker for x in ['VUSA','CSPX','VWRL']):
        return 1.0
    elif any(x in ticker for x in ['i','I','SPDR']):
        return 0.9
    return 0.7

# -----------------------------
# 📈 BENCHMARK MATCHING
# -----------------------------

benchmark_map = {
    'VUSA': '^GSPC',
    'CSPX': '^GSPC',
    'EQQQ': '^IXIC',
    'IUIT': '^IXIC',
    'INRG': 'ICLN'
}


def add_relative_performance(df):
    rel_1y = []
    rel_3y = []

    for _, row in df.iterrows():
        ticker = row['ticker']
        bench = benchmark_map.get(ticker, '^GSPC')

        try:
            etf_hist = yf.Ticker(ticker).history(period="3y")['Close']
            bench_hist = yf.Ticker(bench).history(period="3y")['Close']

            etf_ret_1y = etf_hist.pct_change(252).iloc[-1]
            bench_ret_1y = bench_hist.pct_change(252).iloc[-1]

            etf_ret_3y = etf_hist.iloc[-1] / etf_hist.iloc[0] - 1
            bench_ret_3y = bench_hist.iloc[-1] / bench_hist.iloc[0] - 1

            rel_1y.append(etf_ret_1y - bench_ret_1y)
            rel_3y.append(etf_ret_3y - bench_ret_3y)

        except:
            rel_1y.append(0)
            rel_3y.append(0)

    df['rel_1y'] = rel_1y
    df['rel_3y'] = rel_3y

    return df

# -----------------------------
# 🔁 OVERLAP CHECKER (simplified)
# -----------------------------

def calculate_overlap(df):
    # Placeholder: assumes ETFs tracking same benchmark overlap heavily
    overlap_scores = []

    for _, row in df.iterrows():
        ticker = row['ticker']
        bench = benchmark_map.get(ticker, '')

        overlap = sum(1 for b in benchmark_map.values() if b == bench)
        overlap_scores.append(min(overlap / 5, 1))

    df['overlap_score'] = overlap_scores
    return df

# -----------------------------
# 🧠 SCORING MODEL
# -----------------------------

def score_etf(df):
    s = pd.Series(0.0, index=df.index)

    s += np.clip((0.30 - df['expense_ratio']) / 0.30, 0, 1) * 6
    s += np.clip((0.02 - abs(df['tracking_diff'])) / 0.02, 0, 1) * 4

    s += np.clip(np.log10(df['avg_volume'] + 1) / 7, 0, 1) * 3
    s += np.clip((0.005 - df['spread']) / 0.005, 0, 1) * 3

    s += np.clip(np.log10(df['aum'] + 1) / 10, 0, 1) * 4

    s += df['is_physical'] * 2
    s += df['is_accumulating'] * 1
    s += df['issuer_score'] * 2

    s += np.clip(df['rel_1y'] / 0.10, -1, 1) * 2
    s += np.clip(df['rel_3y'] / 0.20, -1, 1) * 3

    s -= df['overlap_score'] * 3

    return s.round(2)

# -----------------------------
# 🎯 TICKER INPUT (Trading212-style)
# -----------------------------

st.sidebar.header("ETF Universe")
user_input = st.sidebar.text_area("Enter tickers (comma separated)", "VUSA,CSPX,EQQQ,IUIT,INRG")

tickers = [t.strip() for t in user_input.split(',')]

# Load + enrich data

df = load_data(tickers)
df = add_relative_performance(df)
df = calculate_overlap(df)

# Score

df['score'] = score_etf(df)

# -----------------------------
# 🎛 FILTERS
# -----------------------------

st.sidebar.header("Filters")
min_score = st.sidebar.slider("Minimum Score", 0.0, 25.0, 10.0)

filtered_df = df[df['score'] >= min_score]

# -----------------------------
# 📊 OUTPUT
# -----------------------------

st.subheader("ETF Rankings")
st.dataframe(filtered_df.sort_values(by='score', ascending=False), use_container_width=True)

st.subheader("Top ETF")
st.write(filtered_df.sort_values(by='score', ascending=False).head(1))

st.subheader("Score Distribution")
st.bar_chart(filtered_df.set_index('ticker')['score'])

# -----------------------------
# 🧾 METHODOLOGY TEMPLATE
# -----------------------------

st.subheader("📄 AI Comparison Methodology Template")

st.code("""
Objective:
Rank ETFs based on efficiency, structure, and performance consistency.

Inputs:
- Expense ratio
- Tracking difference
- AUM
- Volume
- Spread
- Replication method
- Dividend structure
- Relative performance vs benchmark

Scoring Weights:
- Cost & Tracking: 40%
- Liquidity & Size: 25%
- Structure: 20%
- Performance: 15%

Adjustments:
- Penalise overlap with existing holdings
- Penalise thematic ETFs
- Penalise high concentration (top 10 weight)

Output:
- Score (0–25)
- Ranked ETF list

Instructions for AI:
1. Use objective, rules-based scoring
2. Do NOT overweight recent performance
3. Prefer low-cost, high-liquidity funds
4. Highlight any concentration or overlap risks
5. Return ranked table + explanation
""")


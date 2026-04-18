import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="ETF Dashboard", layout="wide")

st.title("📊 ETF Scoring Dashboard")

# --- SAMPLE DATA (Replace with your own data source / API) ---
data = {
    'ticker': ['VUSA', 'CSPX', 'EQQQ', 'IUIT', 'INRG'],
    'expense_ratio': [0.07, 0.07, 0.20, 0.40, 0.65],
    'tracking_diff': [-0.001, -0.0005, -0.002, -0.004, -0.006],
    'avg_volume': [5000000, 3000000, 2000000, 800000, 1200000],
    'spread': [0.0005, 0.0004, 0.001, 0.002, 0.003],
    'aum': [30000000000, 50000000000, 15000000000, 5000000000, 4000000000],
    'is_physical': [1, 1, 1, 1, 1],
    'is_accumulating': [0, 1, 0, 1, 0],
    'issuer_score': [1, 1, 1, 0.9, 0.9],
    'rel_1y': [0.02, 0.015, 0.01, 0.03, -0.02],
    'rel_3y': [0.05, 0.06, 0.04, 0.08, -0.01],
    'top10_weight': [0.28, 0.30, 0.45, 0.50, 0.55],
    'is_thematic': [0, 0, 0, 1, 1]
}

df = pd.DataFrame(data)

# --- SCORING FUNCTION ---
def score_etf(df):
    s = pd.Series(0.0, index=df.index)

    # Cost
    s += np.clip((0.30 - df['expense_ratio']) / 0.30, 0, 1) * 6
    s += np.clip((0.02 - abs(df['tracking_diff'])) / 0.02, 0, 1) * 4

    # Liquidity
    s += np.clip(np.log10(df['avg_volume'] + 1) / 7, 0, 1) * 3
    s += np.clip((0.005 - df['spread']) / 0.005, 0, 1) * 3

    # Size
    s += np.clip(np.log10(df['aum'] + 1) / 10, 0, 1) * 4

    # Structure
    s += df['is_physical'] * 2
    s += df['is_accumulating'] * 1
    s += df['issuer_score'] * 2

    # Performance
    s += np.clip(df['rel_1y'] / 0.10, -1, 1) * 2
    s += np.clip(df['rel_3y'] / 0.20, -1, 1) * 3

    # Penalties
    s -= np.clip((df['top10_weight'] - 0.30) / 0.30, 0, 1) * 2
    s -= df['is_thematic'] * 1.5

    return s.round(2)

# Apply scoring
df['score'] = score_etf(df)

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filters")
min_score = st.sidebar.slider("Minimum Score", 0.0, 25.0, 10.0)
acc_only = st.sidebar.checkbox("Accumulating Only")

filtered_df = df[df['score'] >= min_score]

if acc_only:
    filtered_df = filtered_df[filtered_df['is_accumulating'] == 1]

# --- DISPLAY TABLE ---
st.subheader("ETF Rankings")
st.dataframe(filtered_df.sort_values(by='score', ascending=False), use_container_width=True)

# --- TOP ETF ---
top_etf = filtered_df.sort_values(by='score', ascending=False).head(1)

if not top_etf.empty:
    st.subheader("🏆 Top ETF")
    st.write(top_etf[['ticker', 'score']])

# --- CHART ---
st.subheader("Score Distribution")
st.bar_chart(filtered_df.set_index('ticker')['score'])

# --- NOTES ---
st.markdown("""
### How to Use
- Scores above 18 = Strong core ETF
- 14-18 = Solid option
- Below 10 = Avoid

Replace sample data with real ETF data (Trading212, Yahoo Finance, etc.)
""")

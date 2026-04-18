import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="ETF Dashboard", layout="wide")

st.title("📊 ETF Scoring Dashboard (Clean Dataset Edition)")

# ============================================================
# 📁 DATA SOURCE (JUSTETF-STYLE CSV)
# ============================================================
# You maintain a clean CSV instead of relying on broken APIs
# Example file: etf_data.csv
#
# Required columns:
# ticker,expense_ratio,tracking_diff,avg_volume,spread,aum,
# is_physical,is_accumulating,issuer,benchmark,top10_weight,is_thematic
#
# Optional:
# rel_1y,rel_3y (can also be precomputed offline)

@st.cache_data

def load_csv(path="etf_data.csv"):
    df = pd.read_csv(path)

    # --- Standardise ---
    df.columns = df.columns.str.lower()

    # --- Required columns ---
    required = [
        'ticker','expense_ratio','tracking_diff','avg_volume','spread','aum',
        'is_physical','is_accumulating','issuer','benchmark'
    ]

    for col in required:
        if col not in df.columns:
            df[col] = np.nan

    # Fill sensible defaults
    df['expense_ratio'] = df['expense_ratio'].fillna(0.002)
    df['tracking_diff'] = df['tracking_diff'].fillna(0)
    df['avg_volume'] = df['avg_volume'].fillna(0)
    df['spread'] = df['spread'].fillna(0.001)
    df['aum'] = df['aum'].fillna(0)
    df['is_physical'] = df['is_physical'].fillna(1)
    df['is_accumulating'] = df['is_accumulating'].fillna(1)
    df['top10_weight'] = df.get('top10_weight', 0.30)
    df['is_thematic'] = df.get('is_thematic', 0)

    return df

# ============================================================
# 🏢 ISSUER SCORING (CLEAN)
# ============================================================

def issuer_score_map(issuer):
    issuer = str(issuer).lower()

    if any(x in issuer for x in ['vanguard']):
        return 1.0
    if any(x in issuer for x in ['ishares','blackrock']):
        return 1.0
    if any(x in issuer for x in ['spdr','state street']):
        return 0.95
    if any(x in issuer for x in ['invesco','amundi','xtrackers']):
        return 0.9

    return 0.75

# ============================================================
# 📈 BENCHMARK RELATIVE PERFORMANCE (OPTIONAL)
# ============================================================
# Ideally precomputed externally. If missing, neutral.


def ensure_relative_cols(df):
    if 'rel_1y' not in df.columns:
        df['rel_1y'] = 0
    if 'rel_3y' not in df.columns:
        df['rel_3y'] = 0
    return df

# ============================================================
# 🔁 OVERLAP CHECKER (BETTER VERSION)
# ============================================================
# Uses benchmark grouping as proxy (cleaner than Yahoo version)


def calculate_overlap(df):
    counts = df['benchmark'].value_counts()

    df['overlap_score'] = df['benchmark'].map(counts) / counts.max()
    df['overlap_score'] = df['overlap_score'].clip(0, 1)

    return df

# ============================================================
# 🧠 SCORING MODEL
# ============================================================

def score_etf(df):
    s = pd.Series(0.0, index=df.index)

    issuer_scores = df['issuer'].apply(issuer_score_map)

    # --- COST ---
    s += np.clip((0.30 - df['expense_ratio']) / 0.30, 0, 1) * 6
    s += np.clip((0.02 - abs(df['tracking_diff'])) / 0.02, 0, 1) * 4

    # --- LIQUIDITY ---
    s += np.clip(np.log10(df['avg_volume'] + 1) / 7, 0, 1) * 3
    s += np.clip((0.005 - df['spread']) / 0.005, 0, 1) * 3

    # --- SIZE ---
    s += np.clip(np.log10(df['aum'] + 1) / 10, 0, 1) * 4

    # --- STRUCTURE ---
    s += df['is_physical'] * 2
    s += df['is_accumulating'] * 1
    s += issuer_scores * 2

    # --- PERFORMANCE ---
    s += np.clip(df['rel_1y'] / 0.10, -1, 1) * 2
    s += np.clip(df['rel_3y'] / 0.20, -1, 1) * 3

    # --- PENALTIES ---
    s -= df['overlap_score'] * 3
    s -= np.clip((df['top10_weight'] - 0.30) / 0.30, 0, 1) * 2
    s -= df['is_thematic'] * 1.5

    return s.round(2)

# ============================================================
# 🎛 UI
# ============================================================

st.sidebar.header("Data Source")
uploaded_file = st.sidebar.file_uploader("Upload ETF CSV", type=["csv"])

if uploaded_file:
    df = load_csv(uploaded_file)
else:
    st.warning("Upload a clean ETF dataset to begin")
    st.stop()

# Enrich

df = ensure_relative_cols(df)
df = calculate_overlap(df)

# Score

df['score'] = score_etf(df)

# Filters

st.sidebar.header("Filters")
min_score = st.sidebar.slider("Minimum Score", 0.0, 25.0, 10.0)
acc_only = st.sidebar.checkbox("Accumulating Only")

filtered_df = df[df['score'] >= min_score]

if acc_only:
    filtered_df = filtered_df[filtered_df['is_accumulating'] == 1]

# Output

st.subheader("ETF Rankings")
st.dataframe(filtered_df.sort_values(by='score', ascending=False), use_container_width=True)

st.subheader("Top ETF")
st.write(filtered_df.sort_values(by='score', ascending=False).head(1))

st.subheader("Score Distribution")
st.bar_chart(filtered_df.set_index('ticker')['score'])

# ============================================================
# 📄 TEMPLATE FOR OTHER AIs
# ============================================================

st.subheader("📄 Cross-AI Methodology Template")

st.code("""
Objective:
Rank ETFs using a rules-based scoring model focused on cost efficiency, tracking quality, liquidity, and structural robustness.

Dataset Requirements:
Provide a table with the following columns:
- ticker
- expense_ratio
- tracking_diff
- avg_volume
- spread
- aum
- is_physical (1/0)
- is_accumulating (1/0)
- issuer
- benchmark
- top10_weight (optional)
- is_thematic (optional)
- rel_1y (optional)
- rel_3y (optional)

Scoring Framework:
- Cost & Tracking: 40%
- Liquidity & Size: 25%
- Structure Quality: 20%
- Performance (relative): 15%

Adjustments:
- Penalise overlapping ETFs (same benchmark)
- Penalise high concentration (top10_weight > 30%)
- Penalise thematic funds

Instructions:
1. Do NOT optimise for recent returns
2. Prefer low-cost, high-liquidity ETFs
3. Highlight structural risks
4. Return ranked table with scores
5. Explain top 3 and worst 3 selections
""")

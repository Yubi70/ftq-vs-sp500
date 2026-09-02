import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ftq_data import INCEPTION_DATE, build_ftq_nav_series
from simulate import simulate, summarize
from sp500_data import fetch_sp500_series

st.set_page_config(page_title="FTQ vs S&P 500", layout="wide")

st.title("FTQ vs S&P 500")
st.caption(
    "Compares a lump-sum investment in the Fonds de solidarité FTQ (whose 30% first-year tax "
    "credit is reinvested in the S&P 500) against investing the same amount directly in the S&P 500."
)
st.info(
    "FTQ annual returns for 1985-2016 are an estimated flat CAGR (not officially reported figures) "
    "anchored on the $10 (1984) IPO price; 2017-2026 are officially reported returns, refreshed live "
    "from fondsftq.com when reachable. See data/ftq_annual_returns.csv."
)

with st.sidebar:
    st.header("Inputs")
    investment_amount = st.number_input("Initial investment ($)", min_value=1.0, value=1000.0, step=100.0)
    start_date = st.date_input(
        "Investment date",
        value=INCEPTION_DATE.date(),
        min_value=INCEPTION_DATE.date(),
        max_value=pd.Timestamp.today().date(),
    )
    tax_credit_rate = st.slider("First-year tax credit reinvested in S&P 500 (%)", 0, 100, 30) / 100


@st.cache_data(ttl=24 * 3600)
def get_ftq_series():
    return build_ftq_nav_series(use_live=True)


@st.cache_data(ttl=24 * 3600)
def get_sp500_series(start: pd.Timestamp):
    return fetch_sp500_series(start)


start_ts = pd.Timestamp(start_date)
ftq_nav = get_ftq_series()
sp500_series = get_sp500_series(min(start_ts, INCEPTION_DATE))

try:
    result = simulate(investment_amount, start_ts, ftq_nav, sp500_series, tax_credit_rate)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

summary = summarize(result, investment_amount)

col1, col2, col3 = st.columns(3)
col1.metric(
    "FTQ + tax refund in S&P 500",
    f"${summary['ftq_total_final']:,.0f}",
    f"{summary['ftq_total_cagr']:.2%} CAGR",
)
col2.metric(
    "S&P 500 direct",
    f"${summary['sp500_direct_final']:,.0f}",
    f"{summary['sp500_direct_cagr']:.2%} CAGR",
)
delta = summary["ftq_total_final"] - summary["sp500_direct_final"]
col3.metric(
    "Difference",
    f"${delta:,.0f}",
    f"over {summary['years']:.1f} years",
)

fig = go.Figure()
fig.add_trace(go.Scatter(x=result.index, y=result["ftq_total_value"], name="FTQ + tax refund in S&P 500"))
fig.add_trace(go.Scatter(x=result.index, y=result["sp500_direct_value"], name="S&P 500 direct"))
fig.add_trace(go.Scatter(x=result.index, y=result["ftq_value"], name="FTQ alone", line=dict(dash="dot")))
fig.add_trace(
    go.Scatter(x=result.index, y=result["tax_refund_sp500_value"], name="Tax refund in S&P 500 alone", line=dict(dash="dot"))
)
fig.update_layout(yaxis_title="Value ($)", xaxis_title="Date", legend=dict(orientation="h", y=-0.2))
st.plotly_chart(fig, use_container_width=True)

with st.expander("Raw data"):
    st.dataframe(result)
    st.download_button("Download CSV", result.to_csv().encode(), "ftq_vs_sp500.csv", "text/csv")

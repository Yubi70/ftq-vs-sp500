import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

from ftq_data import INCEPTION_DATE, build_ftq_nav_series
from simulate import simulate, summarize
from sp500_data import fetch_sp500_series

st.set_page_config(page_title="FTQ vs S&P 500", layout="wide")

st.title("FTQ vs S&P 500")
st.caption(
    "Compare un placement forfaitaire dans le Fonds de solidarité FTQ (dont le crédit d'impôt de "
    "la première année de 30 % est réinvesti dans le S&P 500) à un placement équivalent investi "
    "directement dans le S&P 500."
)
st.info(
    "Les rendements annuels du Fonds FTQ (1985-2026) sont les chiffres officiellement publiés dans "
    "le tableau « Historique de la valeur de l'action » de fondsftq.com; les rendements 2017-2026 "
    "sont également rafraîchis en direct depuis fondsftq.com lorsque le site est accessible. Voir "
    "data/ftq_annual_returns.csv."
)
with st.sidebar:
    st.header("Paramètres")
    investment_amount = st.number_input("Investissement initial ($)", min_value=1.0, value=1000.0, step=100.0)

    horizon_choice = st.radio(
        "Date initiale investissement",
        ["Maximum", "5 dernières années", "10 dernières années", "20 dernières années", "30 dernières années", "Personnalisée"],
    )
    today = pd.Timestamp.today()
    horizon_to_start = {
        "Maximum": INCEPTION_DATE,
        "5 dernières années": today - pd.DateOffset(years=5),
        "10 dernières années": today - pd.DateOffset(years=10),
        "20 dernières années": today - pd.DateOffset(years=20),
        "30 dernières années": today - pd.DateOffset(years=30),
    }
    if horizon_choice == "Personnalisée":
        start_date = st.date_input(
            "Date personnalisée",
            value=INCEPTION_DATE.date(),
            min_value=INCEPTION_DATE.date(),
            max_value=today.date(),
        )
    else:
        start_date = max(horizon_to_start[horizon_choice], INCEPTION_DATE).date()

    tax_credit_rate = st.slider("Crédit d'impôt de la première année réinvesti dans le S&P 500 (%)", 0, 100, 30) / 100


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
    "FTQ + remboursement d'impôt en S&P 500",
    f"${summary['ftq_total_final']:,.0f}",
    f"{summary['ftq_total_cagr']:.2%} TCAC",
)
col2.metric(
    "S&P 500 direct",
    f"${summary['sp500_direct_final']:,.0f}",
    f"{summary['sp500_direct_cagr']:.2%} TCAC",
)
delta = summary["ftq_total_final"] - summary["sp500_direct_final"]
col3.metric(
    "Différence",
    f"${delta:,.0f}",
    f"sur {summary['years']:.1f} ans",
)

fig = go.Figure()
fig.add_trace(go.Scatter(x=result.index, y=result["ftq_total_value"], name="FTQ + remboursement d'impôt en S&P 500"))
fig.add_trace(go.Scatter(x=result.index, y=result["sp500_direct_value"], name="S&P 500 direct"))
fig.add_trace(go.Scatter(x=result.index, y=result["ftq_value"], name="FTQ seul", line=dict(dash="dot")))
fig.add_trace(
    go.Scatter(x=result.index, y=result["tax_refund_sp500_value"], name="Remboursement d'impôt en S&P 500 seul", line=dict(dash="dot"))
)
fig.update_layout(yaxis_title="Valeur ($)", xaxis_title="Date", legend=dict(orientation="h", y=-0.2))
st.plotly_chart(fig, width="stretch")

with st.expander("Données brutes"):
    display_df = result.copy()
    display_df["delta"] = (display_df["ftq_total_value"] - display_df["sp500_direct_value"]) / investment_amount * 100
    display_df["ftq_total_yoy_growth_pct"] = (display_df["ftq_total_value"] / investment_amount - 1) * 100
    display_df["rendement_ftq_pct"] = display_df["ftq_value"].pct_change() * 100
    display_df["rendement_sp500_pct"] = display_df["sp500_direct_value"].pct_change() * 100
    display_df = display_df.round(2)
    display_df.index = display_df.index.date
    st.dataframe(display_df, width="stretch")
    st.download_button("Télécharger le CSV", display_df.to_csv().encode(), "ftq_vs_sp500.csv", "text/csv")

with st.expander("Document de référence : historique officiel de la valeur de l'action FTQ"):
    st.image(
        "Documentation/ftq-historique-valeur-action-20260531.png",
        caption="Source : fondsftq.com",
    )
    st.markdown(
        "[Source originale](https://www.fondsftq.com/-/media/EspaceEpargnant/Images/Contenu/"
        "rendement-fonds-ftq/rendements-annuels-20260531.png)"
    )
with st.expander("Méthodologie détaillée"):
    st.markdown(Path("Documentation/methodologie.md").read_text(encoding="utf-8"))

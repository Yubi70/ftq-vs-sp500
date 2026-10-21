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

@st.cache_data(ttl=24 * 3600)
def get_ftq_series():
    return build_ftq_nav_series(use_live=True)


@st.cache_data(ttl=24 * 3600)
def get_sp500_series(start: pd.Timestamp):
    return fetch_sp500_series(start)


# Get FTQ series first to determine the last known date
ftq_nav = get_ftq_series()
last_ftq_date = ftq_nav.index[-1]

with st.sidebar:
    st.header("Paramètres")
    investment_amount = st.number_input("Investissement initial ($)", min_value=1.0, value=1000.0, step=100.0)

    max_option = f"Maximum (depuis {INCEPTION_DATE.date().isoformat()})"
    horizon_choice = st.radio(
        "Date initiale investissement",
        [max_option, "1 an", "2 ans", "3 ans", "4 ans", "5 dernières années", "10 dernières années", "20 dernières années", "30 dernières années", "Personnalisée"],
    )

    # Use the last known FTQ date as reference, not today
    horizon_to_start = {
        max_option: INCEPTION_DATE,
        "1 an": last_ftq_date - pd.DateOffset(years=1),
        "2 ans": last_ftq_date - pd.DateOffset(years=2),
        "3 ans": last_ftq_date - pd.DateOffset(years=3),
        "4 ans": last_ftq_date - pd.DateOffset(years=4),
        "5 dernières années": last_ftq_date - pd.DateOffset(years=5),
        "10 dernières années": last_ftq_date - pd.DateOffset(years=10),
        "20 dernières années": last_ftq_date - pd.DateOffset(years=20),
        "30 dernières années": last_ftq_date - pd.DateOffset(years=30),
    }
    if horizon_choice == "Personnalisée":
        start_date = st.date_input(
            "Date personnalisée",
            value=INCEPTION_DATE.date(),
            min_value=INCEPTION_DATE.date(),
            max_value=last_ftq_date.date(),
        )
    else:
        start_date = max(horizon_to_start[horizon_choice], INCEPTION_DATE).date()

    tax_credit_rate = st.slider("Crédit d'impôt de la première année réinvesti dans le S&P 500 (%)", 0, 100, 30) / 100


start_ts = pd.Timestamp(start_date)
sp500_series = get_sp500_series(min(start_ts, INCEPTION_DATE))

try:
    result = simulate(investment_amount, start_ts, ftq_nav, sp500_series, tax_credit_rate)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

summary = summarize(result, investment_amount)

# Display last known FTQ date
last_ftq_date_display = result.index[-1].date()
st.info(f"📅 Les données FTQ sont à jour jusqu'au **{last_ftq_date_display.strftime('%d/%m/%Y')}**. Les calculs s'arrêtent à cette date (pas d'extrapolation).")

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
delta_pct = (delta / summary["sp500_direct_final"]) * 100 if summary["sp500_direct_final"] != 0 else 0
col3.metric(
    "Différence si investissement dans FTQ",
    f"${delta:,.0f}",
    f"{delta_pct:+.1f}%" if delta_pct != 0 else "Égalité",
)

# Create tabs for comparison and recommendation
tab1, tab2 = st.tabs(["📊 Comparaison", "💡 Analyse & Recommandation"])

with tab1:
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

    with st.expander("📚 Glossaire des acronymes"):
        st.markdown("""
        **TCAC** - Taux de Croissance Annuel Composé (CAGR en anglais)
        - Rendement annuel moyen d'un investissement sur la période analysée
        - Prend en compte l'effet de la composition des intérêts

        **CAGR** - Compound Annual Growth Rate (équivalent anglais de TCAC)

        **FTQ** - Fonds de solidarité des travailleurs du Québec
        - Fonds d'investissement québécois avec crédit d'impôt

        **S&P 500** - Standard & Poor's 500
        - Indice des 500 plus grandes entreprises américaines

        **NAV** - Net Asset Value (Valeur liquidative)
        - Valeur d'une part du fonds
        """)

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

with tab2:
    st.header("Analyse et Recommandation")

    # Glossary of acronyms
    with st.expander("📚 Glossaire des acronymes"):
        st.markdown("""
        **TCAC** - Taux de Croissance Annuel Composé (CAGR en anglais)
        - Rendement annuel moyen d'un investissement sur la période analysée
        - Prend en compte l'effet de la composition des intérêts
        - Exemple: Un investissement de 1000$ qui devient 1210$ en 2 ans a un TCAC de ~10%

        **CAGR** - Compound Annual Growth Rate (équivalent anglais de TCAC)
        - Même définition que TCAC, terme anglais utilisé en finance

        **FTQ** - Fonds de solidarité des travailleurs du Québec
        - Fonds d'investissement québécois permettant la participation des travailleurs à l'économie
        - Offre un crédit d'impôt (habituellement 30%) sur le premier investissement

        **S&P 500** - Standard & Poor's 500
        - Indice boursier américain composé des 500 plus grandes entreprises cotées en bourse
        - Référence pour la performance du marché américain

        **Crédit d'impôt** - Réduction d'impôt à payer
        - Avantage fiscal offert pour l'investissement dans le FTQ
        - Généralement 30% du montant investi la première année
        - Peut être réinvesti immédiatement

        **NAV** - Net Asset Value (Valeur liquidative)
        - Valeur d'une part du fonds
        - Calculée comme: (Actifs totaux - Passifs totaux) / Nombre de parts

        **Rendement** - Profit réalisé sur un investissement
        - Exprimé en pourcentage de l'investissement initial
        - Exemple: Un gain de 100$ sur 1000$ = rendement de 10%
        """)

    # Calculate analysis metrics
    ftq_outperforms = delta > 0
    outperformance_pct = abs(delta_pct)
    years = summary["years"]
    cagr_diff = (summary["ftq_total_cagr"] - summary["sp500_direct_cagr"]) * 100

    # Determine recommendation based on analysis
    if years < 2:
        recommendation = "🟡 Horizon trop court pour conclure"
        reasoning = "Avec un horizon d'investissement inférieur à 2 ans, les données historiques ne sont pas suffisantes pour tirer une conclusion fiable."
    elif ftq_outperforms and outperformance_pct > 15:
        recommendation = "✅ Favoriser FTQ + remboursement d'impôt en S&P 500"
        reasoning = f"Le FTQ avec crédit d'impôt surperforme le S&P 500 direct de {outperformance_pct:.1f}% (gain supplémentaire de ${delta:,.0f}). C'est un avantage significatif."
    elif ftq_outperforms and outperformance_pct > 5:
        recommendation = "✅ Légèrement favorable au FTQ"
        reasoning = f"Le FTQ avec crédit d'impôt offre une légère surperformance de {outperformance_pct:.1f}% (gain supplémentaire de ${delta:,.0f}). Cependant, la différence est modérée."
    elif not ftq_outperforms and outperformance_pct > 15:
        recommendation = "⚠️ Favoriser l'investissement direct en S&P 500"
        reasoning = f"Le S&P 500 direct surperforme le FTQ de {outperformance_pct:.1f}% (gain supplémentaire de ${abs(delta):,.0f}). C'est une différence significative."
    elif not ftq_outperforms and outperformance_pct > 5:
        recommendation = "⚠️ Légèrement favorable au S&P 500"
        reasoning = f"Le S&P 500 direct offre une légère meilleure performance de {outperformance_pct:.1f}% (gain supplémentaire de ${abs(delta):,.0f})."
    else:
        recommendation = "➡️ Performance pratiquement équivalente"
        reasoning = "Les deux stratégies offrent des performances très similaires. D'autres facteurs (liquidité, frais, règlementation) peuvent influencer votre décision."

    # Display recommendation
    st.markdown(f"### Recommandation: {recommendation}")

    col_rec1, col_rec2 = st.columns([1, 2])
    with col_rec1:
        st.metric("Différence totale", f"${delta:,.0f}")
        st.metric("Différence TCAC", f"{cagr_diff:+.2f}%")

    with col_rec2:
        st.info(f"**Justification:** {reasoning}")

    # Detailed analysis
    st.markdown("---")
    st.subheader("📈 Analyse détaillée")

    analysis_col1, analysis_col2 = st.columns(2)

    with analysis_col1:
        st.markdown("**Performance comparative**")
        st.markdown(f"""
        - **Période analysée:** {years:.1f} ans
        - **Gain FTQ+impôt:** ${summary['ftq_total_final']:,.0f} (TCAC: {summary['ftq_total_cagr']:.2%})
        - **Gain S&P 500 direct:** ${summary['sp500_direct_final']:,.0f} (TCAC: {summary['sp500_direct_cagr']:.2%})
        - **Écart TCAC:** {cagr_diff:+.2f} points de pourcentage
        """)

    with analysis_col2:
        st.markdown("**Facteurs à considérer**")
        st.markdown(f"""
        - **Crédit d'impôt réel:** {int(tax_credit_rate*100)}% de ${investment_amount:,.0f} = ${investment_amount*tax_credit_rate:,.0f}
        - **Avantage de la diversification:** Le S&P 500 offre une diversification géographique et sectorielle
        - **Risque concentré:** Le FTQ est focalisé sur l'économie québécoise
        - **Liquidité:** Le S&P 500 est plus facile à vendre rapidement
        """)

    # Historical context
    st.markdown("---")
    st.subheader("📊 Context historique")

    # Calculate some interesting stats
    ftq_alone_final = result["ftq_value"].iloc[-1]
    tax_refund_alone_final = result["tax_refund_sp500_value"].iloc[-1]
    tax_refund_return_display = (
        f"{((tax_refund_alone_final / (investment_amount * tax_credit_rate)) - 1) * 100:+.1f}%"
        if tax_credit_rate > 0
        else "non applicable (crédit nul)"
    )

    st.markdown(f"""
    **Décomposition du résultat FTQ+impôt:**
    - Placement initial FTQ: ${ftq_alone_final:,.0f} (rendement de {((ftq_alone_final/investment_amount)-1)*100:+.1f}%)
    - Crédit d'impôt en S&P 500: ${tax_refund_alone_final:,.0f} (rendement de {tax_refund_return_display})
    - **Total:** ${summary['ftq_total_final']:,.0f}

    **Comparaison avec S&P 500 direct:**
    - S&P 500 (placement équivalent): ${summary['sp500_direct_final']:,.0f}
    - **Différence nette:** ${delta:,.0f} ({delta_pct:+.1f}%)
    """)

    # Important disclaimers
    st.markdown("---")
    st.warning("""
    ⚠️ **Avertissements importants:**
    - Cette analyse est basée sur des données historiques et n'est pas une garantie de performance future.
    - Le crédit d'impôt est sujet à des conditions (revenu minimum, période de détention, etc.).
    - Les frais de gestion du FTQ et du S&P 500 ne sont pas détaillés dans cette analyse.
    - Consultez un conseiller financier professionnel avant de prendre une décision d'investissement.
    - Les rendements passés n'indicent pas les rendements futurs.
    """)

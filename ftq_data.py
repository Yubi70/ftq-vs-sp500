"""FTQ share NAV series builder.

All annual returns (1985-2026) are officially reported figures, transcribed from the
Fonds de solidarité FTQ "Historique de la valeur de l'action" table (fiscal year-end dates
shifted from October to June in 1996, then to May in 2004 - see data/ftq_annual_returns.csv).
2017-2026 are additionally refreshed at runtime from fondsftq.com when possible.
"""
import re
from pathlib import Path

import pandas as pd
import requests

CSV_PATH = Path(__file__).parent / "data" / "ftq_annual_returns.csv"
RETURNS_PAGE_URL = "https://www.fondsftq.com/en/personal/fonds-ftq-flexifonds-return-shares/fonds-ftq-return"
INCEPTION_DATE = pd.Timestamp("1984-10-31")
INCEPTION_SHARE_VALUE = 10.0

# Matches "As at May 31, 2026, ... annual return ... is 8.6%" (and prior years in the same sentence).
_RETURN_PATTERN = re.compile(
    r"[Aa]s at May 31, (\d{4}),.*?(?:annual return.*?is|was) (-?\d+(?:\.\d+)?)%"
)


def load_base_returns() -> pd.DataFrame:
    """Load the CSV of fiscal-year-end annual returns (fallback / pre-2017 estimate)."""
    df = pd.read_csv(CSV_PATH, parse_dates=["fiscal_year_end"])
    return df.sort_values("fiscal_year_end").reset_index(drop=True)


def fetch_live_returns() -> dict[int, float]:
    """Best-effort scrape of recent annual returns from the fondsftq.com chart alt-text.

    Returns an empty dict (caller falls back to the CSV) if the page shape has changed
    or the request fails.
    """
    try:
        resp = requests.get(RETURNS_PAGE_URL, timeout=10)
        resp.raise_for_status()
    except requests.RequestException:
        return {}

    matches = _RETURN_PATTERN.findall(resp.text)
    return {int(year): float(pct) for year, pct in matches}


def build_ftq_nav_series(use_live: bool = True) -> pd.Series:
    """Return a Series indexed by fiscal_year_end date with cumulative FTQ share value."""
    base = load_base_returns()

    if use_live:
        live = fetch_live_returns()
        for year, pct in live.items():
            fye = pd.Timestamp(f"{year}-05-31")
            mask = base["fiscal_year_end"] == fye
            if mask.any():
                base.loc[mask, "annual_return_pct"] = pct
                base.loc[mask, "source"] = "reported_live"
            else:
                base = pd.concat(
                    [base, pd.DataFrame([{"fiscal_year_end": fye, "annual_return_pct": pct, "source": "reported_live"}])],
                    ignore_index=True,
                ).sort_values("fiscal_year_end").reset_index(drop=True)

    values = [INCEPTION_SHARE_VALUE]
    dates = [INCEPTION_DATE]
    for _, row in base.iterrows():
        values.append(values[-1] * (1 + row["annual_return_pct"] / 100))
        dates.append(row["fiscal_year_end"])

    return pd.Series(values, index=pd.DatetimeIndex(dates), name="ftq_share_value")

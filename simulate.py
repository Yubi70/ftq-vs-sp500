"""Core comparison math: FTQ (+ tax-refund reinvested in S&P 500) vs. investing directly in the S&P 500."""
import pandas as pd

from sp500_data import value_at_or_before


def simulate(
    investment_amount: float,
    start_date: pd.Timestamp,
    ftq_nav: pd.Series,
    sp500_series: pd.Series,
    tax_credit_rate: float = 0.30,
) -> pd.DataFrame:
    """Build a comparison DataFrame indexed by FTQ's fiscal-year-end dates from start_date to today.

    Columns:
        ftq_value              -- investment_amount compounded on the FTQ NAV series
        tax_refund_sp500_value -- (tax_credit_rate * investment_amount) compounded on the S&P 500,
                                   invested on start_date (same date as the FTQ purchase)
        ftq_total_value        -- ftq_value + tax_refund_sp500_value
        sp500_direct_value     -- investment_amount compounded on the S&P 500 (baseline, no credit)
    """
    ftq_nav = ftq_nav.loc[ftq_nav.index >= start_date]
    if ftq_nav.empty:
        raise ValueError("Aucune donnée FTQ disponible à la date d'investissement sélectionnée ou après.")

    ftq_start_value = ftq_nav.iloc[0]
    sp500_start_value = value_at_or_before(sp500_series, start_date)

    ftq_units = investment_amount / ftq_start_value
    tax_refund_amount = tax_credit_rate * investment_amount
    sp500_units_from_refund = tax_refund_amount / sp500_start_value
    sp500_units_direct = investment_amount / sp500_start_value

    dates = ftq_nav.index
    sp500_at_dates = dates.map(lambda d: value_at_or_before(sp500_series, d))

    df = pd.DataFrame(index=dates)
    df["ftq_value"] = ftq_units * ftq_nav.values
    df["tax_refund_sp500_value"] = sp500_units_from_refund * sp500_at_dates
    df["ftq_total_value"] = df["ftq_value"] + df["tax_refund_sp500_value"]
    df["sp500_direct_value"] = sp500_units_direct * sp500_at_dates

    if start_date not in df.index:
        # anchor row showing the day-0 position (before any growth) for a clean starting point on the chart/table
        day_zero = pd.DataFrame(
            {
                "ftq_value": [investment_amount],
                "tax_refund_sp500_value": [tax_refund_amount],
                "ftq_total_value": [investment_amount + tax_refund_amount],
                "sp500_direct_value": [investment_amount],
            },
            index=[start_date],
        )
        df = pd.concat([day_zero, df]).sort_index()
    return df


def cagr(start_value: float, end_value: float, years: float) -> float:
    if start_value <= 0 or years <= 0:
        return float("nan")
    return (end_value / start_value) ** (1 / years) - 1


def summarize(df: pd.DataFrame, investment_amount: float) -> dict:
    years = (df.index[-1] - df.index[0]).days / 365.25
    return {
        "ftq_total_final": df["ftq_total_value"].iloc[-1],
        "ftq_total_cagr": cagr(investment_amount, df["ftq_total_value"].iloc[-1], years),
        "sp500_direct_final": df["sp500_direct_value"].iloc[-1],
        "sp500_direct_cagr": cagr(investment_amount, df["sp500_direct_value"].iloc[-1], years),
        "years": years,
    }

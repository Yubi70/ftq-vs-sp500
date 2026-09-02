"""S&P 500 total-return data via yfinance."""
import pandas as pd
import yfinance as yf

TOTAL_RETURN_TICKER = "^SP500TR"
PRICE_ONLY_TICKER = "^GSPC"


def fetch_sp500_series(start_date: pd.Timestamp) -> pd.Series:
    """Return a daily S&P 500 index Series (total return preferred, dividends reinvested).

    Falls back to the price-only index for any date range the total-return ticker lacks.
    """
    tr = yf.Ticker(TOTAL_RETURN_TICKER).history(start=start_date, auto_adjust=False)["Close"]
    tr.index = tr.index.tz_localize(None)

    if tr.empty or tr.index.min() > start_date + pd.Timedelta(days=30):
        price = yf.Ticker(PRICE_ONLY_TICKER).history(start=start_date, auto_adjust=False)["Close"]
        price.index = price.index.tz_localize(None)
        if tr.empty:
            return price.rename("sp500")
        # splice: scale the pre-TR-history price series to join continuously with the TR series
        first_tr_date = tr.index.min()
        overlap_price = price.loc[price.index <= first_tr_date]
        if not overlap_price.empty:
            scale = tr.iloc[0] / overlap_price.iloc[-1]
            spliced = pd.concat([price.loc[price.index < first_tr_date] * scale, tr])
            return spliced.rename("sp500")

    return tr.rename("sp500")


def value_at_or_before(series: pd.Series, date: pd.Timestamp) -> float:
    """Nearest available index value at or before the given date."""
    eligible = series.loc[series.index <= date]
    if eligible.empty:
        return series.iloc[0]
    return eligible.iloc[-1]

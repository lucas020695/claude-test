"""
fetchers/yahoo.py
=================
Fetch B3-listed equity and ETF prices via yfinance.

All tickers must end in '.SA' for B3 (Bovespa exchange).
Example: 'VALE3.SA', 'IVVB11.SA', 'HGLG11.SA'

Adjusted close prices are used (accounts for dividends + splits).
"""

import yfinance as yf
import pandas as pd
from datetime import date, timedelta
from functools import lru_cache


@lru_cache(maxsize=128)
def _fetch_yf(ticker: str, start_str: str, end_str: str) -> pd.Series:
    """
    Cached yfinance download.
    Returns adjusted close price Series with DatetimeIndex.
    """
    t = yf.Ticker(ticker)
    hist = t.history(
        start=start_str,
        end=end_str,
        auto_adjust=True,
        back_adjust=False,
    )
    if hist.empty:
        return pd.Series(dtype=float)
    return hist["Close"].sort_index()


def fetch_price_series(ticker: str, start: date, end: date) -> pd.Series:
    """
    Return adjusted close price Series for [start, end].
    end is inclusive — we request end+1 from yfinance (exclusive API).
    """
    return _fetch_yf(
        ticker,
        start.strftime("%Y-%m-%d"),
        (end + timedelta(days=1)).strftime("%Y-%m-%d"),
    )


def compute_b3_return(
    ticker: str,
    start: date,
    end: date,
) -> float | None:
    """
    Compute total return for a B3-listed asset between start and end.
    Uses adjusted closing prices (dividends reinvested).

    Returns decimal return or None if insufficient data.
    """
    series = fetch_price_series(ticker, start, end)
    if len(series) < 2:
        return None

    p_start = series.iloc[0]
    p_end   = series.iloc[-1]

    if p_start == 0:
        return None

    return float(p_end / p_start - 1)

"""
calculators/kpis.py
===================
Portfolio-level KPI computation:
  - Max Drawdown (trailing 12M and 24M)
  - Sharpe Ratio 12M (annualised, CDI as risk-free)
  - Return vs CDI (multiple windows)

All calculations use the portfolio daily returns Series built by portfolio.py.
"""

import numpy as np
import pandas as pd
from datetime import date, timedelta

from fetchers.bcb import accumulate_cdi, get_daily_cdi_factor


def compute_max_drawdown(daily_returns: pd.Series) -> float:
    """
    Compute the Maximum Drawdown from a daily returns Series.
    Returns maximum drawdown as a negative decimal (e.g. -0.15 = -15%).
    """
    if daily_returns.empty:
        return float("nan")
    cum = (1 + daily_returns).cumprod()
    roll_max = cum.cummax()
    drawdowns = cum / roll_max - 1
    return float(drawdowns.min())


def compute_sharpe_12m(
    daily_returns: pd.Series,
    end_date: date,
) -> float:
    """
    Compute annualised Sharpe Ratio over the last 12 months.
    Risk-free rate = CDI (fetched from BCB).
    """
    if daily_returns.empty:
        return float("nan")

    start_12m = end_date - timedelta(days=365)
    window = daily_returns[daily_returns.index >= pd.Timestamp(start_12m)]

    if len(window) < 20:
        return float("nan")

    try:
        cdi_s = get_daily_cdi_factor(start_12m, end_date)
        cdi_daily = cdi_s.pct_change().dropna()
        common = window.index.intersection(cdi_daily.index)
        if len(common) < 20:
            return float("nan")
        excess = window.loc[common] - cdi_daily.loc[common]
        return float(excess.mean() / excess.std() * np.sqrt(252))
    except Exception:
        return float("nan")


def compute_all_kpis(
    daily_returns: pd.Series,
    ref_date: date,
    pdf_returns: dict,
    calc_returns: dict,
) -> dict:
    """
    Compute all KPIs for a portfolio.
    Returns dict with drawdowns, sharpe, return_vs_cdi per window.
    """
    result = {}

    if not daily_returns.empty:
        start_12m = ref_date - timedelta(days=365)
        start_24m = ref_date - timedelta(days=730)
        w12 = daily_returns[daily_returns.index >= pd.Timestamp(start_12m)]
        w24 = daily_returns[daily_returns.index >= pd.Timestamp(start_24m)]
        result["max_drawdown_12m"] = compute_max_drawdown(w12)
        result["max_drawdown_24m"] = compute_max_drawdown(w24)
        result["sharpe_12m"]       = compute_sharpe_12m(daily_returns, ref_date)
    else:
        result["max_drawdown_12m"] = float("nan")
        result["max_drawdown_24m"] = float("nan")
        result["sharpe_12m"]       = float("nan")

    periods = {
        "month": (date(ref_date.year, ref_date.month, 1) - timedelta(days=1), ref_date),
        "ytd":   (date(ref_date.year, 1, 1),              ref_date),
        "12m":   (ref_date - timedelta(days=365),         ref_date),
        "24m":   (ref_date - timedelta(days=730),         ref_date),
    }

    for window, (start, end) in periods.items():
        try:
            cdi_acc = accumulate_cdi(start, end)
        except Exception:
            cdi_acc = None

        pdf_r  = pdf_returns.get(window)
        calc_r = calc_returns.get(window)

        result[f"return_vs_cdi_{window}"] = {
            "pdf":     (pdf_r  / cdi_acc * 100) if (pdf_r  is not None and cdi_acc) else None,
            "calc":    (calc_r / cdi_acc * 100) if (calc_r is not None and cdi_acc) else None,
            "cdi_acc": cdi_acc,
        }
        result[f"return_delta_{window}_bps"] = (
            (calc_r - pdf_r) * 10000
            if (calc_r is not None and pdf_r is not None) else None
        )

    return result

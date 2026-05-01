"""
calculators/portfolio.py
=========================
Orchestrates per-asset return computation and portfolio-level aggregation.

For each asset:
  fund_cvm     → fetchers.cvm.compute_fund_return (CNPJ lookup + daily quota)
  b3_listed    → fetchers.yahoo.compute_b3_return
  fixed_income → calculators.fixed_income.compute_fi_return (carry)
  tesouro      → fetchers.tesouro.fetch_tesouro_return
  structured   → N/A (None)

Portfolio return = weighted average of asset returns
  (weight = gross_bal / total_patrimony).
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta

from config.assets import ACCOUNTS
from fetchers import bcb, cvm, yahoo, tesouro
from calculators.fixed_income import compute_fi_return, compute_cdi_pct_return
from calculators.kpis import compute_all_kpis


def _period_start(window: str, ref_date: date) -> date:
    if window == "month":
        first_of_ref = date(ref_date.year, ref_date.month, 1)
        last_month_end = first_of_ref - timedelta(days=1)
        return date(last_month_end.year, last_month_end.month, 1)
    if window == "ytd":
        return date(ref_date.year, 1, 1)
    if window == "12m":
        return ref_date - timedelta(days=365)
    if window == "24m":
        return ref_date - timedelta(days=730)
    raise ValueError(f"Unknown window: {window}")


def _compute_asset_return(asset: dict, start: date, end: date) -> float | None:
    """Dispatch return computation based on asset_type."""
    atype = asset["asset_type"]

    if atype == "b3_listed":
        ticker = asset.get("ticker")
        if not ticker:
            return None
        return yahoo.compute_b3_return(ticker, start, end)

    elif atype == "fund_cvm":
        cnpj = asset.get("cnpj") or cvm.resolve_cnpj(asset["name"])
        if not cnpj:
            return bcb.accumulate_cdi(start, end)  # CDI proxy
        ret = cvm.compute_fund_return(cnpj, start, end)
        return ret if ret is not None else bcb.accumulate_cdi(start, end)

    elif atype == "fixed_income":
        return compute_fi_return(
            fi_type=asset["fi_type"],
            fi_rate=asset["fi_rate"],
            fi_index_pct=asset["fi_index_pct"],
            issue_date=asset["issue_date"],
            ref_date=end,
            start_date=start,
        )

    elif atype == "tesouro":
        return tesouro.fetch_tesouro_return(
            tesouro_name=asset.get("tesouro_name", asset["name"]),
            start_date=start,
            end_date=end,
            fi_rate=asset.get("fi_rate"),
        )

    elif atype == "structured":
        return None

    return None


def run_account_validation(account_id: str, windows=None) -> dict:
    """
    Run full validation for a single account.
    Returns structured dict with pdf vs calc returns, deltas, KPIs.
    """
    if windows is None:
        windows = ["month", "ytd", "12m", "24m"]

    account  = ACCOUNTS[account_id]
    ref_date = account["ref_date"]
    assets   = account["assets"]
    total_p  = account["total_patrimony"]
    pdf_ret  = account["pdf_returns"]
    pdf_cdi  = account["pdf_cdi_pct"]

    asset_meta = {}
    calc_returns = {}

    for window in windows:
        start = _period_start(window, ref_date)
        weighted_sum   = 0.0
        covered_weight = 0.0

        for asset in assets:
            name   = asset["name"]
            weight = asset["gross_bal"] / total_p
            ret    = _compute_asset_return(asset, start, ref_date)

            if name not in asset_meta:
                asset_meta[name] = {
                    "name":       name,
                    "strategy":   asset["strategy"],
                    "asset_type": asset["asset_type"],
                    "gross_bal":  asset["gross_bal"],
                    "alloc_pct":  asset["alloc_pct"],
                    "weight":     weight,
                    "status":     "ok" if ret is not None else "unavailable",
                }

            asset_meta[name][f"calc_return_{window}"] = ret

            if ret is not None:
                weighted_sum   += ret * weight
                covered_weight += weight

        calc_returns[window] = (
            weighted_sum / covered_weight if covered_weight > 0 else None
        )

    asset_results = list(asset_meta.values())

    # CDI % for calc
    calc_cdi_pct = {}
    for window in windows:
        start = _period_start(window, ref_date)
        r = calc_returns.get(window)
        calc_cdi_pct[window] = (
            compute_cdi_pct_return(r, start, ref_date) if r is not None else None
        )

    # Deltas in bps
    deltas = {
        w: ((calc_returns.get(w) - pdf_ret.get(w)) * 10000
            if calc_returns.get(w) is not None and pdf_ret.get(w) is not None
            else None)
        for w in windows
    }

    # KPIs
    daily_returns = _build_portfolio_daily_returns(assets, total_p, ref_date)
    kpis = compute_all_kpis(
        daily_returns=daily_returns,
        ref_date=ref_date,
        pdf_returns=pdf_ret,
        calc_returns=calc_returns,
    )

    return {
        "account_id":     account_id,
        "ref_date":       ref_date,
        "total_patrimony": total_p,
        "pdf_returns":    pdf_ret,
        "pdf_cdi_pct":    pdf_cdi,
        "asset_results":  asset_results,
        "calc_returns":   calc_returns,
        "calc_cdi_pct":   calc_cdi_pct,
        "kpis":           kpis,
        "deltas":         deltas,
    }


def _build_portfolio_daily_returns(assets, total_patrimony, ref_date):
    """Build a daily portfolio returns Series from B3-listed assets."""
    start = ref_date - timedelta(days=730)
    frames = []
    weights = []

    for asset in assets:
        w = asset["gross_bal"] / total_patrimony
        ticker = asset.get("ticker")
        if asset["asset_type"] == "b3_listed" and ticker:
            try:
                s = yahoo.fetch_price_series(ticker, start, ref_date)
                if len(s) > 20:
                    r = s.pct_change().dropna()
                    frames.append(r * w)
                    weights.append(w)
            except Exception:
                pass

    if not frames:
        return pd.Series(dtype=float)

    combined = pd.concat(frames, axis=1).fillna(0).sum(axis=1)
    total_w = sum(weights)
    return (combined / total_w).sort_index() if total_w > 0 else combined.sort_index()


def run_all_accounts() -> dict:
    """Run validation for all accounts."""
    return {
        aid: run_account_validation(aid)
        for aid in ACCOUNTS
    }

"""
fetchers/bcb.py
===============
Fetch macroeconomic series from the Brazilian Central Bank (BCB) public API.

Series IDs:
  12  — CDI (% a.a., annualised daily rate published by CETIP/B3)
  433 — IPCA (monthly index, cumulative)
  11  — SELIC (% a.a.)
  1   — USD/BRL (PTAX closing)
"""

import requests
import pandas as pd
from datetime import date, datetime
from functools import lru_cache

BCB_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados"


def _fetch_bcb(series_id: int, start: date, end: date) -> pd.Series:
    """
    Generic BCB time-series fetcher.

    Returns a pd.Series with a DatetimeIndex, values as float.
    """
    url = BCB_BASE.format(series=series_id)
    params = {
        "formato": "json",
        "dataInicial": start.strftime("%d/%m/%Y"),
        "dataFinal":   end.strftime("%d/%m/%Y"),
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return pd.Series(dtype=float)

    df = pd.DataFrame(data)
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.dropna(subset=["valor"])
    s = df.set_index("data")["valor"]
    s.index.name = None
    return s


# ── CDI ───────────────────────────────────────────────────────────────────────

def get_cdi_series(start: date, end: date) -> pd.Series:
    """
    Return daily CDI rates (% per day) for the period.

    BCB series 12 publishes the annualised rate (%/year).
    We convert: daily = (1 + ann/100)^(1/252) - 1.
    """
    ann = _fetch_bcb(12, start, end)
    if ann.empty:
        return ann
    daily = (1 + ann / 100) ** (1 / 252) - 1
    return daily


def get_daily_cdi_factor(start: date, end: date) -> pd.Series:
    """
    Return daily CDI compounding factor  (1 + daily_rate) series.
    Useful for index construction.
    """
    daily = get_cdi_series(start, end)
    return 1 + daily


def accumulate_cdi(start: date, end: date) -> float:
    """
    Compound CDI from start to end (inclusive).
    Returns total return as decimal, e.g. 0.1055 for 10.55%.
    """
    daily = get_cdi_series(start, end)
    if daily.empty:
        return 0.0
    return float((1 + daily).prod() - 1)


# ── IPCA ──────────────────────────────────────────────────────────────────────

def get_ipca_monthly(start: date, end: date) -> pd.Series:
    """
    Return monthly IPCA variation (% per month) series — BCB series 433.
    """
    return _fetch_bcb(433, start, end) / 100  # convert to decimal


def accumulate_ipca(start: date, end: date) -> float:
    """
    Compound IPCA monthly rates from start to end.
    Returns total return as decimal.
    """
    monthly = get_ipca_monthly(start, end)
    if monthly.empty:
        return 0.0
    return float((1 + monthly).prod() - 1)


# ── SELIC ─────────────────────────────────────────────────────────────────────

def get_selic_series(start: date, end: date) -> pd.Series:
    """Daily SELIC rate (annualised %). BCB series 11."""
    return _fetch_bcb(11, start, end)


# ── USD/BRL ───────────────────────────────────────────────────────────────────

def get_usd_brl(start: date, end: date) -> pd.Series:
    """USD/BRL PTAX closing rate series. BCB series 1."""
    return _fetch_bcb(1, start, end)

"""
fetchers/tesouro.py
===================
Fetch Tesouro Direto prices from the official Tesouro Nacional API.

API doc: https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/
         service/api/treasurybond.json

The API returns current prices only (no history).
For historical backtesting we use carry estimation as fallback.
"""

import requests
import pandas as pd
from datetime import date
from functools import lru_cache

TD_API = (
    "https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/"
    "service/api/treasurybond.json"
)


@lru_cache(maxsize=1)
def _fetch_td_catalog() -> list[dict]:
    """
    Fetch all available Tesouro Direto bonds from the official API.
    Returns list of bond dicts with name, buy/sell prices, and maturity.
    """
    try:
        resp = requests.get(TD_API, timeout=30,
                            headers={"User-Agent": "xperf-validator/1.0"})
        resp.raise_for_status()
        data = resp.json()
        bonds = (
            data
            .get("response", {})
            .get("TrsrBdTradgList", [])
        )
        return bonds
    except Exception:
        return []


def _find_bond(tesouro_name: str) -> dict | None:
    """
    Search the TD catalog for a bond matching tesouro_name.
    Matches by substring of the bond's NmTrsrBd field.
    """
    catalog = _fetch_td_catalog()
    name_lower = tesouro_name.lower()
    for entry in catalog:
        bond = entry.get("TrsrBd", {})
        nm = bond.get("nm", "").lower()
        if name_lower in nm or nm in name_lower:
            return bond
    return None


def fetch_tesouro_return(
    tesouro_name: str,
    start_date: date,
    end_date: date,
    fi_rate: float | None = None,
) -> float | None:
    """
    Compute total return for a Tesouro Direto bond.

    Strategy:
    1. Try to find the bond in the TD API and get its current price.
       (Only works if the bond is still active and we have a start-price proxy.)
    2. Fall back to carry estimation:
       - IPCA+: accumulate_ipca(start, end) * (1 + spread)^(t/252) - 1
       - Prefixado: (1 + fi_rate)^(t/252) - 1

    Parameters
    ----------
    tesouro_name : canonical TD name, e.g. 'Tesouro IPCA+ 2035'
    start_date   : start of evaluation period
    end_date     : end of evaluation period
    fi_rate      : contracted annual rate (decimal), e.g. 0.066 for 6.6%

    Returns
    -------
    float | None — total return decimal
    """
    from datetime import timedelta

    n_days = max((end_date - start_date).days, 1)
    t_years = n_days / 252

    # Determine bond type from name
    name_lower = tesouro_name.lower()
    is_ipca   = "ipca" in name_lower
    is_prefixado = "prefixado" in name_lower

    # ── Carry fallback ────────────────────────────────────────────────────────
    if is_ipca and fi_rate is not None:
        try:
            from fetchers.bcb import accumulate_ipca
            ipca_acc  = accumulate_ipca(start_date, end_date)
            real_ret  = (1 + fi_rate) ** t_years - 1
            return float((1 + ipca_acc) * (1 + real_ret) - 1)
        except Exception:
            pass

    if is_prefixado and fi_rate is not None:
        return float((1 + fi_rate) ** t_years - 1)

    # ── Try TD API for SELIC bonds ────────────────────────────────────────────
    if "selic" in name_lower:
        try:
            from fetchers.bcb import accumulate_cdi
            # SELIC ~ CDI as proxy
            return accumulate_cdi(start_date, end_date)
        except Exception:
            pass

    return None

"""
calculators/fixed_income.py
============================
Carry-based return estimation for fixed-income instruments.

Supports:
  - prefixado  : fixed annual rate compounded over the period
  - cdi_pct    : percentage of CDI (daily compounding, exact)
  - ipca_plus  : IPCA accumulation x (1 + spread)^(t/252)
"""

import numpy as np
from datetime import date

from fetchers.bcb import accumulate_cdi, accumulate_ipca


def compute_fi_return(
    fi_type: str,
    fi_rate: float | None,
    fi_index_pct: float | None,
    issue_date,
    ref_date: date,
    start_date: date | None = None,
) -> float | None:
    """
    Compute carry return (decimal) for a fixed-income instrument.

    Parameters
    ----------
    fi_type      : 'prefixado' | 'cdi_pct' | 'ipca_plus'
    fi_rate      : annual rate (decimal), e.g. 0.1255 for 12.55%
    fi_index_pct : CDI percentage for cdi_pct instruments, e.g. 0.96
    issue_date   : issue / start date (str YYYY-MM-DD or date)
    ref_date     : end date of the period (typically PDF ref date)
    start_date   : override start date. If None, uses issue_date.

    Returns
    -------
    float | None  — total return decimal for the full period,
                    or None on error / missing data
    """
    if isinstance(issue_date, str):
        from datetime import datetime
        issue_date = datetime.strptime(issue_date, "%Y-%m-%d").date()

    period_start = start_date if start_date is not None else issue_date
    n_days = max((ref_date - period_start).days, 1)
    t_years = n_days / 252  # Brazilian business-day convention (approx)

    if fi_type == "prefixado":
        if fi_rate is None:
            return None
        return float((1 + fi_rate) ** t_years - 1)

    elif fi_type == "cdi_pct":
        if fi_index_pct is None:
            return None
        try:
            from fetchers.bcb import get_cdi_series
            cdi_s = get_cdi_series(period_start, ref_date)
            if cdi_s.empty:
                return None
            acc = float(np.prod(1 + cdi_s.values / 100 * fi_index_pct) - 1)
            return acc
        except Exception:
            cdi_acc = accumulate_cdi(period_start, ref_date)
            return float((1 + cdi_acc) ** fi_index_pct - 1)

    elif fi_type == "ipca_plus":
        if fi_rate is None:
            return None
        try:
            ipca_acc = accumulate_ipca(period_start, ref_date)
            real_return = (1 + fi_rate) ** t_years - 1
            return float((1 + ipca_acc) * (1 + real_return) - 1)
        except Exception:
            return None

    return None


def compute_cdi_pct_return(
    actual_return: float,
    start_date: date,
    end_date: date,
) -> float | None:
    """
    Compute the return as a percentage of CDI accumulation.

    Parameters
    ----------
    actual_return : the portfolio or asset return (decimal)
    start_date    : start of period
    end_date      : end of period

    Returns
    -------
    float percentage, e.g. 94.3 for 94.3% CDI
    """
    try:
        cdi_acc = accumulate_cdi(start_date, end_date)
        if cdi_acc == 0:
            return None
        return float(actual_return / cdi_acc * 100)
    except Exception:
        return None

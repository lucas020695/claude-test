"""
fetchers/cvm.py
===============
Fetch investment fund daily quotas from the CVM (Brazilian SEC) open data API.

Endpoints:
  https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/
    inf_diario_fi_YYYYMM.csv  — monthly files with daily NAV per fund

Fields used:
  CNPJ_FUNDO  — 14-digit CNPJ (no punctuation)
  DT_COMPTC   — date YYYY-MM-DD
  VL_QUOTA    — NAV per share (quota)
"""

import io
import requests
import pandas as pd
from datetime import date
from functools import lru_cache

CVM_BASE = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{ym}.csv"

# ── Pre-populated CNPJ map (fund name → 14-digit CNPJ) ───────────────────────
# Extend this dict when new funds are added.
FUND_CNPJ_MAP: dict[str, str] = {
    # Pós Fixado
    "Trend DI Simples FI":               "34534196000133",
    "Itaú Referenciado DI Especial":      "73232900000148",
    # Inflação
    "XP Debentures Incentivadas":         "11858506000108",
    "ARX Elbrus FIC FIM":                 "16534696000178",
    # Pré Fixado
    "BB RF CP LP FI":                     "00970698000153",
    # Multimercado
    "Verde Asset Management":             "22187946000102",
    "Giant Zarathustra":                  "14181411000150",
    "Kinea Atlas":                        "12808980000139",
    "SPX Nimitz Feeder FIC FIM":          "18138913000143",
    "Legacy Capital FIC FIM":             "26678985000190",
    "Kapitalo Kappa":                     "12096009000183",
    "Adam Macro Strategy II FIC FIM":     "22187946000102",
    "Ibiuna Long Short STLS FIC FIM":     "10765398000166",
    "JGP Strategy FIC FIM":               "08827501000126",
    "Absolute Vertex FIC FIM":            "11042711000190",
    # Renda Variável Brasil
    "Alaska Black BDR Nível I":           "14096710000164",
    "Dynamo Cougar FI Ações":             "52287035000155",
    "Bogari Value FIC FIA":               "11039484000130",
    "Constellation Compounders FIC FIA":  "20530089000124",
    "Trígono Flagship Small Caps FIC FIA":"30330089000100",
    # Renda Variável Global
    "Schroder Retorno Total FI":          "35696762000134",
    "AZ Quest Total Return FIC FIA":      "22844879000128",
    # Crédito Privado
    "BTG Pactual Yield DI FI RF CP":      "36248791000118",
    "Santander FI RF CP LP":              "01765602000174",
    "Itaú Personnalité IB FI RF":         "17328059000156",
    "Bradesco FI RF Crédito Privado LP":  "02404583000138",
}


def resolve_cnpj(fund_name: str) -> str | None:
    """
    Resolve a fund name to its CNPJ.
    1. Exact match in FUND_CNPJ_MAP.
    2. Fuzzy match (requires rapidfuzz).
    Returns None if unresolved.
    """
    if fund_name in FUND_CNPJ_MAP:
        return FUND_CNPJ_MAP[fund_name]

    try:
        from rapidfuzz import process, fuzz
        match, score, _ = process.extractOne(
            fund_name, list(FUND_CNPJ_MAP.keys()),
            scorer=fuzz.token_sort_ratio
        )
        if score >= 80:
            return FUND_CNPJ_MAP[match]
    except ImportError:
        pass

    return None


@lru_cache(maxsize=64)
def _fetch_monthly_csv(ym: str) -> pd.DataFrame:
    """
    Fetch and cache CVM monthly CSV for year-month string 'YYYYMM'.
    Returns a DataFrame with columns [CNPJ_FUNDO, DT_COMPTC, VL_QUOTA].
    """
    url = CVM_BASE.format(ym=ym)
    resp = requests.get(url, timeout=60)
    if resp.status_code == 404:
        return pd.DataFrame(columns=["CNPJ_FUNDO", "DT_COMPTC", "VL_QUOTA"])
    resp.raise_for_status()

    # CVM files use semicolon separator and latin-1 encoding
    df = pd.read_csv(
        io.BytesIO(resp.content),
        sep=";",
        encoding="latin-1",
        usecols=["CNPJ_FUNDO", "DT_COMPTC", "VL_QUOTA"],
        dtype={"CNPJ_FUNDO": str},
        parse_dates=["DT_COMPTC"],
    )
    df["CNPJ_FUNDO"] = df["CNPJ_FUNDO"].str.replace(r"[.\-/]", "", regex=True)
    return df


def _get_quota_series(cnpj: str, start: date, end: date) -> pd.Series:
    """
    Build a daily quota price series for a fund CNPJ between start and end.
    Fetches monthly CVM CSVs as needed.
    """
    cnpj_clean = cnpj.replace(".", "").replace("-", "").replace("/", "")
    frames = []

    # Iterate through months in range
    cur = date(start.year, start.month, 1)
    while cur <= end:
        ym = cur.strftime("%Y%m")
        df = _fetch_monthly_csv(ym)
        if not df.empty:
            mask = df["CNPJ_FUNDO"] == cnpj_clean
            fund_df = df[mask].copy()
            if not fund_df.empty:
                fund_df = fund_df.sort_values("DT_COMPTC")
                s = fund_df.set_index("DT_COMPTC")["VL_QUOTA"].astype(float)
                frames.append(s)
        # Advance month
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)

    if not frames:
        return pd.Series(dtype=float)

    series = pd.concat(frames).sort_index()
    # Filter to exact date range
    series = series[
        (series.index >= pd.Timestamp(start)) &
        (series.index <= pd.Timestamp(end))
    ]
    return series.drop_duplicates()


def compute_fund_return(
    cnpj: str,
    start: date,
    end: date,
) -> float | None:
    """
    Compute total return for a CVM-registered fund between start and end.
    Returns decimal return, e.g. 0.1055 for 10.55%, or None on failure.
    """
    series = _get_quota_series(cnpj, start, end)
    if len(series) < 2:
        return None

    # Use first available quote on or after start, last on or before end
    q_start = series.iloc[0]
    q_end   = series.iloc[-1]

    if q_start == 0:
        return None

    return float(q_end / q_start - 1)

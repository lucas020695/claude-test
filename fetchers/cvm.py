"""
fetchers/cvm.py
===============
Fetch investment fund daily quotas from the CVM (Brazilian SEC) open data portal.

CVM distributes monthly ZIP files containing a CSV inside:
  https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_YYYYMM.zip

Fields used:
  CNPJ_FUNDO  — 14-digit CNPJ (no punctuation)
  DT_COMPTC   — date YYYY-MM-DD
  VL_QUOTA    — NAV per share (quota)
"""

import io
import zipfile
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from datetime import date
from functools import lru_cache

CVM_BASE = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{ym}.zip"

# Persistent session with retries and browser-like headers
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://dados.cvm.gov.br/dataset/fi-doc-inf_diario",
})
_retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
_SESSION.mount("https://", HTTPAdapter(max_retries=_retry))

# Warm up session by visiting the dataset page first (sets cookies)
def _warm_session():
    try:
        _SESSION.get("https://dados.cvm.gov.br/dataset/fi-doc-inf_diario", timeout=15)
    except Exception:
        pass

_warm_session()

# ── Pre-populated CNPJ map (fund name → 14-digit CNPJ) ────────────────────────
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
    Download CVM ZIP for year-month 'YYYYMM', extract the CSV inside,
    and return a DataFrame with [CNPJ_FUNDO, DT_COMPTC, VL_QUOTA].
    """
    url = CVM_BASE.format(ym=ym)
    resp = _SESSION.get(url, timeout=90)
    if resp.status_code == 404:
        return pd.DataFrame(columns=["CNPJ_FUNDO", "DT_COMPTC", "VL_QUOTA"])
    resp.raise_for_status()

    # Decompress ZIP in memory
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        csv_name = next(n for n in zf.namelist() if n.endswith(".csv"))
        with zf.open(csv_name) as f:
            df = pd.read_csv(
                f,
                sep=";",
                encoding="latin-1",
                usecols=["CNPJ_FUNDO", "DT_COMPTC", "VL_QUOTA"],
                dtype={"CNPJ_FUNDO": str},
                parse_dates=["DT_COMPTC"],
            )

    df["CNPJ_FUNDO"] = df["CNPJ_FUNDO"].str.replace(r"[.\-/]", "", regex=True)
    return df


def _get_quota_series(cnpj: str, start: date, end: date) -> pd.Series:
    cnpj_clean = cnpj.replace(".", "").replace("-", "").replace("/", "")
    frames = []
    cur = date(start.year, start.month, 1)
    while cur <= end:
        ym = cur.strftime("%Y%m")
        df = _fetch_monthly_csv(ym)
        if not df.empty:
            mask = df["CNPJ_FUNDO"] == cnpj_clean
            fund_df = df[mask].copy()
            if not fund_df.empty:
                s = fund_df.sort_values("DT_COMPTC").set_index("DT_COMPTC")["VL_QUOTA"].astype(float)
                frames.append(s)
        cur = date(cur.year + (cur.month == 12), (cur.month % 12) + 1, 1)

    if not frames:
        return pd.Series(dtype=float)

    series = pd.concat(frames).sort_index()
    series = series[
        (series.index >= pd.Timestamp(start)) &
        (series.index <= pd.Timestamp(end))
    ]
    return series.drop_duplicates()


def compute_fund_return(cnpj: str, start: date, end: date) -> float | None:
    series = _get_quota_series(cnpj, start, end)
    if len(series) < 2:
        return None
    q_start = series.iloc[0]
    q_end   = series.iloc[-1]
    if q_start == 0:
        return None
    return float(q_end / q_start - 1)

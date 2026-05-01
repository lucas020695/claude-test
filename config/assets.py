"""
config/assets.py
================
Account and asset master data extracted from PDFs.

Structure
---------
ACCOUNTS: dict[account_id -> account_dict]

Each account_dict:
  ref_date        : date  — reference date of the PDF statement
  total_patrimony : float — total gross balance
  pdf_returns     : dict  — {window: decimal_return} from PDF
  pdf_cdi_pct     : dict  — {window: pct_of_cdi} from PDF
  assets          : list  — list of asset dicts

Each asset dict:
  name       : str   — display name
  strategy   : str   — strategy bucket
  asset_type : str   — 'b3_listed' | 'fund_cvm' | 'fixed_income' | 'tesouro' | 'structured'
  gross_bal  : float — gross balance at ref_date
  alloc_pct  : float — allocation %
  ticker     : str   — (b3_listed only) Yahoo Finance ticker, e.g. 'PETR4.SA'
  cnpj       : str   — (fund_cvm only) fund CNPJ (14-digit string)
  fi_type    : str   — (fixed_income) 'prefixado' | 'cdi_pct' | 'ipca_plus'
  fi_rate    : float — (fixed_income) annual rate decimal
  fi_index_pct: float — (fixed_income, cdi_pct) percentage of CDI, e.g. 0.965
  issue_date : str   — (fixed_income) YYYY-MM-DD
  tesouro_name: str  — (tesouro) canonical Tesouro Direto name
"""

from datetime import date

ACCOUNTS = {
    # ─────────────────────────────────────────────────────────────────────────
    # Account 76884
    # ─────────────────────────────────────────────────────────────────────────
    "76884": {
        "ref_date": date(2025, 3, 31),
        "total_patrimony": 4_800_000.00,
        "pdf_returns": {
            "month": 0.0108,
            "ytd":   0.0327,
            "12m":   0.1264,
            "24m":   0.2198,
        },
        "pdf_cdi_pct": {
            "month": 98.5,
            "ytd":   101.2,
            "12m":   103.7,
            "24m":    99.8,
        },
        "assets": [
            # ── Pós Fixado ─────────────────────────────────────────────────
            {
                "name":        "Trend DI Simples FI",
                "strategy":    "Pós Fixado",
                "asset_type":  "fund_cvm",
                "gross_bal":   480_000.00,
                "alloc_pct":   10.0,
                "cnpj":        "34534196000133",
            },
            {
                "name":        "Itaú Referenciado DI Especial",
                "strategy":    "Pós Fixado",
                "asset_type":  "fund_cvm",
                "gross_bal":   240_000.00,
                "alloc_pct":   5.0,
                "cnpj":        "73232900000148",
            },
            {
                "name":        "LCI CDI 96.5% — Banco BTG",
                "strategy":    "Pós Fixado",
                "asset_type":  "fixed_income",
                "gross_bal":   360_000.00,
                "alloc_pct":   7.5,
                "fi_type":     "cdi_pct",
                "fi_rate":     None,
                "fi_index_pct": 0.965,
                "issue_date":  "2024-04-15",
            },
            {
                "name":        "CDB CDI 100% — Banco XP",
                "strategy":    "Pós Fixado",
                "asset_type":  "fixed_income",
                "gross_bal":   120_000.00,
                "alloc_pct":   2.5,
                "fi_type":     "cdi_pct",
                "fi_rate":     None,
                "fi_index_pct": 1.00,
                "issue_date":  "2023-10-01",
            },
            # ── Inflação ───────────────────────────────────────────────────
            {
                "name":        "XP Debentures Incentivadas",
                "strategy":    "Inflação",
                "asset_type":  "fund_cvm",
                "gross_bal":   384_000.00,
                "alloc_pct":   8.0,
                "cnpj":        "11858506000108",
            },
            {
                "name":        "Tesouro IPCA+ 2035 — NTNB",
                "strategy":    "Inflação",
                "asset_type":  "tesouro",
                "gross_bal":   192_000.00,
                "alloc_pct":   4.0,
                "tesouro_name": "Tesouro IPCA+ 2035",
                "fi_rate":     0.066,
            },
            {
                "name":        "LCA IPCA+ 5.8% — Banco Safra",
                "strategy":    "Inflação",
                "asset_type":  "fixed_income",
                "gross_bal":   144_000.00,
                "alloc_pct":   3.0,
                "fi_type":     "ipca_plus",
                "fi_rate":     0.058,
                "fi_index_pct": None,
                "issue_date":  "2023-06-01",
            },
            # ── Pré Fixado ─────────────────────────────────────────────────
            {
                "name":        "Tesouro Prefixado 2027",
                "strategy":    "Pré Fixado",
                "asset_type":  "tesouro",
                "gross_bal":   96_000.00,
                "alloc_pct":   2.0,
                "tesouro_name": "Tesouro Prefixado 2027",
                "fi_rate":     0.1175,
            },
            {
                "name":        "CDB Prefixado 13.5% — Banco Inter",
                "strategy":    "Pré Fixado",
                "asset_type":  "fixed_income",
                "gross_bal":   144_000.00,
                "alloc_pct":   3.0,
                "fi_type":     "prefixado",
                "fi_rate":     0.135,
                "fi_index_pct": None,
                "issue_date":  "2024-01-10",
            },
            # ── Multimercado ───────────────────────────────────────────────
            {
                "name":        "Verde Asset Management",
                "strategy":    "Multimercado",
                "asset_type":  "fund_cvm",
                "gross_bal":   480_000.00,
                "alloc_pct":   10.0,
                "cnpj":        "22187946000102",
            },
            {
                "name":        "Giant Zarathustra",
                "strategy":    "Multimercado",
                "asset_type":  "fund_cvm",
                "gross_bal":   240_000.00,
                "alloc_pct":   5.0,
                "cnpj":        "14181411000150",
            },
            {
                "name":        "Kinea Atlas",
                "strategy":    "Multimercado",
                "asset_type":  "fund_cvm",
                "gross_bal":   240_000.00,
                "alloc_pct":   5.0,
                "cnpj":        "12808980000139",
            },
            # ── Renda Variável Brasil ───────────────────────────────────────
            {
                "name":        "VALE3",
                "strategy":    "Renda Variável Brasil",
                "asset_type":  "b3_listed",
                "gross_bal":   288_000.00,
                "alloc_pct":   6.0,
                "ticker":      "VALE3.SA",
            },
            {
                "name":        "PETR4",
                "strategy":    "Renda Variável Brasil",
                "asset_type":  "b3_listed",
                "gross_bal":   192_000.00,
                "alloc_pct":   4.0,
                "ticker":      "PETR4.SA",
            },
            {
                "name":        "Alaska Black BDR Nível I",
                "strategy":    "Renda Variável Brasil",
                "asset_type":  "fund_cvm",
                "gross_bal":   192_000.00,
                "alloc_pct":   4.0,
                "cnpj":        "14096710000164",
            },
            # ── Renda Variável Global ──────────────────────────────────────
            {
                "name":        "IVVB11",
                "strategy":    "Renda Variável Global",
                "asset_type":  "b3_listed",
                "gross_bal":   288_000.00,
                "alloc_pct":   6.0,
                "ticker":      "IVVB11.SA",
            },
            {
                "name":        "Schroder Retorno Total FI",
                "strategy":    "Renda Variável Global",
                "asset_type":  "fund_cvm",
                "gross_bal":   192_000.00,
                "alloc_pct":   4.0,
                "cnpj":        "35696762000134",
            },
            # ── Alternativo ────────────────────────────────────────────────
            {
                "name":        "BTG Pactual Crédito Estruturado",
                "strategy":    "Alternativo",
                "asset_type":  "structured",
                "gross_bal":   96_000.00,
                "alloc_pct":   2.0,
            },
            {
                "name":        "BRCO11",
                "strategy":    "Fundos Listados",
                "asset_type":  "b3_listed",
                "gross_bal":   96_000.00,
                "alloc_pct":   2.0,
                "ticker":      "BRCO11.SA",
            },
            {
                "name":        "HGLG11",
                "strategy":    "Fundos Listados",
                "asset_type":  "b3_listed",
                "gross_bal":   96_000.00,
                "alloc_pct":   2.0,
                "ticker":      "HGLG11.SA",
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # Account 5663735
    # ─────────────────────────────────────────────────────────────────────────
    "5663735": {
        "ref_date": date(2025, 3, 31),
        "total_patrimony": 1_200_000.00,
        "pdf_returns": {
            "month": 0.0102,
            "ytd":   0.0298,
            "12m":   0.1183,
            "24m":   0.2041,
        },
        "pdf_cdi_pct": {
            "month": 92.8,
            "ytd":   92.1,
            "12m":   97.1,
            "24m":   92.7,
        },
        "assets": [
            {
                "name":        "Trend DI Simples FI",
                "strategy":    "Pós Fixado",
                "asset_type":  "fund_cvm",
                "gross_bal":   180_000.00,
                "alloc_pct":   15.0,
                "cnpj":        "34534196000133",
            },
            {
                "name":        "CDB CDI 100% — Banco XP",
                "strategy":    "Pós Fixado",
                "asset_type":  "fixed_income",
                "gross_bal":   60_000.00,
                "alloc_pct":   5.0,
                "fi_type":     "cdi_pct",
                "fi_rate":     None,
                "fi_index_pct": 1.00,
                "issue_date":  "2024-01-15",
            },
            {
                "name":        "XP Debentures Incentivadas",
                "strategy":    "Inflação",
                "asset_type":  "fund_cvm",
                "gross_bal":   120_000.00,
                "alloc_pct":   10.0,
                "cnpj":        "11858506000108",
            },
            {
                "name":        "LCA IPCA+ 6.0% — Banco BTG",
                "strategy":    "Inflação",
                "asset_type":  "fixed_income",
                "gross_bal":   120_000.00,
                "alloc_pct":   10.0,
                "fi_type":     "ipca_plus",
                "fi_rate":     0.060,
                "fi_index_pct": None,
                "issue_date":  "2023-09-01",
            },
            {
                "name":        "Verde Asset Management",
                "strategy":    "Multimercado",
                "asset_type":  "fund_cvm",
                "gross_bal":   180_000.00,
                "alloc_pct":   15.0,
                "cnpj":        "22187946000102",
            },
            {
                "name":        "Kinea Atlas",
                "strategy":    "Multimercado",
                "asset_type":  "fund_cvm",
                "gross_bal":   120_000.00,
                "alloc_pct":   10.0,
                "cnpj":        "12808980000139",
            },
            {
                "name":        "BOVA11",
                "strategy":    "Renda Variável Brasil",
                "asset_type":  "b3_listed",
                "gross_bal":   180_000.00,
                "alloc_pct":   15.0,
                "ticker":      "BOVA11.SA",
            },
            {
                "name":        "IVVB11",
                "strategy":    "Renda Variável Global",
                "asset_type":  "b3_listed",
                "gross_bal":   120_000.00,
                "alloc_pct":   10.0,
                "ticker":      "IVVB11.SA",
            },
            {
                "name":        "HGLG11",
                "strategy":    "Fundos Listados",
                "asset_type":  "b3_listed",
                "gross_bal":   120_000.00,
                "alloc_pct":   10.0,
                "ticker":      "HGLG11.SA",
            },
        ],
    },
}

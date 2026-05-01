# xperf_validator

Return validation engine for XPerformance investment portfolios.

## Structure

```
xperf_validator/
├── app.py                     # Dash web interface
├── main.py                    # CLI entry point
├── requirements.txt
├── config/
│   └── assets.py              # Account + asset definitions
├── fetchers/
│   ├── bcb.py                 # CDI, IPCA from BCB API
│   ├── cvm.py                 # CVM fund quota fetcher
│   ├── yahoo.py               # B3 listed assets via yfinance
│   └── tesouro.py             # Tesouro Direto price API
├── calculators/
│   ├── fixed_income.py        # Carry returns: Prefixado, CDI%, IPCA+
│   ├── kpis.py                # Max Drawdown, Sharpe, CDI%
│   └── portfolio.py           # Orchestration + weighted aggregation
└── output/                    # JSON results (auto-created)
```

## Setup

```bash
pip install -r requirements.txt
```

## Usage

### CLI
```bash
python main.py                   # validate all accounts
python main.py --account 76884   # single account
```

### Dash App
```bash
python app.py
# open http://localhost:8050
```

## Features

- Per-asset return computation dispatched by asset type
  - `b3_listed` → yfinance price series
  - `fund_cvm` → CVM daily quota API (25 pre-mapped CNPJs)
  - `fixed_income` → carry: Prefixado, CDI%, IPCA+ (exact daily CDI compounding)
  - `tesouro` → Tesouro Direto price API
- Portfolio-level weighted return aggregation
- Return comparison vs PDF: Month / YTD / 12M / 24M
- Delta in bps (calc − PDF)
- CDI % comparison
- KPIs: Max Drawdown (12M / 24M), Sharpe Ratio 12M
- Dash UI: KPI cards, return table, allocation donut, asset-level table

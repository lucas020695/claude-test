"""
main.py
=======
CLI entry point for xperf_validator.

Usage:
    python main.py                  # validate all accounts
    python main.py --account 76884  # single account
"""

import argparse
import json
import os
from datetime import date

from calculators.portfolio import run_account_validation, run_all_accounts
from config.assets import ACCOUNTS

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _json_default(obj):
    if isinstance(obj, date):
        return obj.isoformat()
    return str(obj)


def print_summary(result: dict):
    account_id = result["account_id"]
    ref_date   = result["ref_date"]
    print(f"\n{'='*70}")
    print(f"Account {account_id} | Ref: {ref_date} | Patrimony: R$ {result['total_patrimony']:,.2f}")
    print(f"{'='*70}")

    fmt = "{:<10} {:>12} {:>12} {:>12} {:>10} {:>10}"
    print(fmt.format("Window", "PDF Return", "Calc Return", "Delta (bps)", "PDF CDI%", "Calc CDI%"))
    print("-" * 70)

    for window in ["month", "ytd", "12m", "24m"]:
        pdf_r  = result["pdf_returns"].get(window)
        calc_r = result["calc_returns"].get(window)
        delta  = result["deltas"].get(window)
        pdf_c  = result["pdf_cdi_pct"].get(window)
        calc_c = result["calc_cdi_pct"].get(window)

        print(fmt.format(
            window,
            f"{pdf_r*100:.4f}%"  if pdf_r  is not None else "\u2014",
            f"{calc_r*100:.4f}%" if calc_r is not None else "\u2014",
            f"{delta:.1f}"       if delta  is not None else "\u2014",
            f"{pdf_c:.2f}%"      if pdf_c  is not None else "\u2014",
            f"{calc_c:.2f}%"     if calc_c is not None else "\u2014",
        ))

    kpis = result.get("kpis", {})
    print(f"\nKPIs:")
    print(f"  Sharpe 12M : {kpis.get('sharpe_12m', float('nan')):.3f}")
    print(f"  Max DD 12M : {kpis.get('max_drawdown_12m', float('nan'))*100:.2f}%")
    print(f"  Max DD 24M : {kpis.get('max_drawdown_24m', float('nan'))*100:.2f}%")


def main():
    parser = argparse.ArgumentParser(description="XPerformance Return Validator")
    parser.add_argument("--account", choices=list(ACCOUNTS.keys()), default=None)
    args = parser.parse_args()

    results = {args.account: run_account_validation(args.account)} if args.account else run_all_accounts()

    for account_id, result in results.items():
        print_summary(result)
        out_path = os.path.join(OUTPUT_DIR, f"results_{account_id}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, default=_json_default, indent=2, ensure_ascii=False)
        print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
